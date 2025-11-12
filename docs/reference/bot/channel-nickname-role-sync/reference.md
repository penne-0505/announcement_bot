---
title: "ニックネーム同期チャンネル リファレンス"
domain: "bot"
status: "beta"
version: "0.1.0"
created: "2025-11-12"
updated: "2025-11-12"
related_plan: "docs/plan/bot/channel-nickname-role-sync/plan.md"
related_intents:
  - "docs/intent/bot/channel-nickname-role-sync/intent.md"
---

## Slash コマンド `/nickname_sync_setup`
| 項目 | 内容 |
| --- | --- |
| name | `nickname_sync_setup` |
| description | `View を通じて監視チャンネルとロールを選択し、自動ニックネーム同期を有効化します。` |
| options | なし（View から選択） |
| default_permissions | `discord.Permissions(manage_roles=True, manage_messages=True)` |
| 応答 | View を含む ephemeral メッセージ |

### バリデーション
- DM からの実行は禁止 (`interaction.guild_id is None`)。
- View の interaction は実行者以外には受け付けず、権限を持たないメンバーが操作してもエラーを返す。
- チャンネル/ロール選択後に「設定を保存」ボタンを押すと `channel_nickname_rules` へ upsert し、結果ログを `INFO` で出力。
- ChannelSelect は Text/Announcement チャンネルのみ選択可能、RoleSelect は 1 件のみ選択可能。

## `views.nickname_sync_setup.NicknameSyncSetupView`
- `ChannelSelect` と `RoleSelect` を 1 つずつ提供し、選択結果を View に保存する。
- `interaction_check` でコマンド実行者以外の操作をブロックし、エラーを ephemeral で返す。
- `Confirm` ボタン押下時に選択が揃っていなければエラーを返し、揃っていれば `ChannelNicknameRuleRepository.upsert_rule` を呼び出す。
- 成功時は `<#channel>`/`<@&role>` を含むメッセージを返信し、View を停止する。

## データモデル: `channel_nickname_rules`
| カラム | 型 | 説明 |
| --- | --- | --- |
| `guild_id` | BIGINT | ギルド ID |
| `channel_id` | BIGINT | 監視対象チャンネル ID |
| `role_id` | BIGINT | 付与するロール ID |
| `updated_by` | BIGINT | Slash コマンド実行者のユーザー ID |
| `updated_at` | TIMESTAMPTZ | 最終更新日時 (デフォルト `now()`) |
| PK | `(guild_id, channel_id)` |

## `app.database.Database`
- `connect()` で asyncpg プールを生成し、`CREATE TABLE IF NOT EXISTS channel_nickname_rules ...` を実行する。
- `fetchrow(query, *args)` / `execute(query, *args)` を提供し、コネクションはコンテキストで自動解放。
- `close()` でプールを破棄し、Bot シャットダウン時に呼び出される。

## `ChannelNicknameRuleRepository`
- `upsert_rule(guild_id, channel_id, role_id, updated_by)` → `ChannelNicknameRule`
- `get_rule_for_channel(guild_id, channel_id)` → Optional[`ChannelNicknameRule`]
- asyncpg の `Record` を dataclass へ詰め替えて返却。

## メッセージ処理
1. `BotClient.on_message` が以下条件で `enforce_nickname_and_role` を呼ぶ:
   - `message.guild` が存在し、`message.author.bot` が False
   - `channel_nickname_rules` に一致する設定がある
2. `enforce_nickname_and_role` の処理:
   - `display_name` (無ければ `global_name` → `name`) を求め、本文と異なれば `message.edit(content=display_name)` を実行
   - `guild.get_role(role_id)` でロール取得し、`role not in member.roles` の場合に `member.add_roles(role, reason="Nickname guard auto assign")`
   - Forbidden/HTTPException は警告ログで通知し、失敗時もチャンネル監視は継続

## エラーハンドリング
- Slash コマンド: 入力不備や権限不足は `interaction.response.send_message(..., ephemeral=True)` で即時通知。
- DB: 接続エラーは `LOGGER.exception` 後にアプリ起動を中断。
- メッセージ処理: 期待ロールが見つからない場合は WARN ログで設定の再登録を促す。
