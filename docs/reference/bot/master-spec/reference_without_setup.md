---
title: "announcement_bot ニックネーム同期仕様"
domain: "bot"
status: "active"
version: "0.2.0"
created: "2025-11-12"
updated: "2025-11-23"
related_plan:
  - "docs/plan/bot/channel-nickname-role-sync/plan.md"
related_intents:
  - "docs/intent/bot/channel-nickname-role-sync/intent.md"
references:
  - "docs/guide/bot/channel-nickname-role-sync/guide.md"
---

## 目的
- Discord 上でニックネーム打刻チャンネルを自動化し、投稿本文をメンバーのニックネームへ反映しつつロールを自動付与する機能の確定仕様を記録する。

## システム構成
| モジュール | 役割 |
| --- | --- |
| `src/app/config.py` | `.env`/環境変数から `DISCORD_BOT_TOKEN` と `DATABASE_URL` を読み込み `AppConfig` を生成。 |
| `src/app/database.py` | asyncpg プールを管理し、`channel_nickname_rules` テーブルを自動作成。 |
| `src/app/container.py` | DB/リポジトリを初期化し、`BotClient` と Slash コマンド登録を完了させる。 |
| `src/bot/client.py` | Discord クライアント拡張。`on_ready` で `tree.sync()`、`on_message` でニックネーム同期処理を呼び出す。 |
| `src/bot/commands.py` | `/nickname_sync_setup` コマンドを登録し、View を返す。 |
| `src/views/nickname_sync_setup.py` | ChannelSelect + RoleSelect + 保存ボタンを持つ View を提供。 |
| `src/bot/handlers.py` | 監視対象チャンネルの投稿内容をニックネームとして適用し、ロールを付与する。 |

## 実行環境と依存
- Python 3.12 / Poetry 管理。
- 主要依存: `discord-py>=2.6.4`, `asyncpg`, `python-dotenv`。
- 実行: `poetry run announcement-bot` または `poetry run python -m src.main`。

## 設定
| 変数 | 必須 | 説明 |
| --- | --- | --- |
| `DISCORD_BOT_TOKEN` | ✅ | Discord Bot トークン。 |
| `DATABASE_URL` | ✅ | PostgreSQL 接続文字列 (Railway 等)。 |
- `.env.example` に両方記載。`load_config()` が `.env` を読み込んだ上で値を検証する。

## データモデル
### `channel_nickname_rules`
| カラム | 型 | 説明 |
| --- | --- | --- |
| `guild_id` | BIGINT | 対象ギルド ID |
| `channel_id` | BIGINT | 監視チャンネル ID |
| `role_id` | BIGINT | 自動付与ロール ID |
| `updated_by` | BIGINT | 設定実行者 ID |
| `updated_at` | TIMESTAMPTZ | `NOW()` デフォルト |
| 主キー | `(guild_id, channel_id)` |

`ChannelNicknameRuleRepository` (`src/app/repositories/channel_rules.py`)
- `upsert_rule` は ON CONFLICT でロール/更新者/更新日時を更新し dataclass を返す。
- `get_rule_for_channel` で監視設定を取得。

## Slash コマンド `/nickname_sync_setup`
| 項目 | 内容 |
| --- | --- |
| name | `nickname_sync_setup` |
| description | View を通じて監視チャンネルとロールを選択し、ニックネーム同期を設定する |
| default_permissions | Manage Roles + Manage Messages |
| guild_only | true |

### フロー
1. Slash コマンド実行時に `NicknameSyncSetupView` を添えた ephemeral メッセージを返す。
2. View には以下の UI 要素がある:
   - **ChannelSelect**: `discord.ChannelType.text/news` のチャンネルから 1 件選択。選択すると View 内部に保持。
   - **RoleSelect**: ギルドのロールから 1 件選択。
   - **設定を保存ボタン**: 両選択が揃っていなければ `ERROR_SELECT_REQUIRED` を表示。揃っていれば `ChannelNicknameRuleRepository.upsert_rule` を実行し、`SUCCESS_MESSAGE` で `<#channel>` と `<@&role>` を通知。
3. `interaction_check` は実行者以外の操作を拒否し `ERROR_UNAUTHORIZED` を返す。
4. 保存成功時は View を停止し、INFO ログに `guild/channel/role/executor` を残す。

## ニックネーム同期ハンドラ
`BotClient.on_message` → `enforce_nickname_and_role(message, rule)`

1. Bot 投稿や DM はスキップ。
2. `ChannelNicknameRuleRepository.get_rule_for_channel(guild_id, channel_id)` で設定を照会し、存在時のみ処理。
3. `enforce_nickname_and_role`:
   - メッセージ本文を `strip()` した値を新ニックネーム候補とし、空文字はスキップ、32文字超過は WARN + `❌` リアクションで通知。
   - 現在のニックネームと異なる場合に `member.edit(nick=new_nickname, reason="Nickname sync from message content")` を実行し、成功時は `✅` リアクションを付与。
   - ギルドからロールを取得し、未付与の場合に `member.add_roles(role, reason="Nickname guard auto assignment")`。
   - Forbidden/HTTPException を WARN ログで通知し、監視自体は継続。未知の例外は `LOGGER.exception` で記録。

## 権限・前提
- Bot ロール: **Manage Roles** / **Manage Messages** / **Send Messages**。付与対象ロールより上位に配置。
- アプリ設定: Intents は `discord.Intents.all()` を使用するため、ポータル側で Message Content Intent を有効化。
- `/nickname_sync_setup` は Manage Roles + Manage Messages 権限を持つメンバーしか実行できない。

## エラーハンドリング & ログ
- 設定読み込み/DB 初期化失敗: `app.runtime` が例外を捕捉し `LOGGER.exception("...初期化に失敗")` を出力。
- View 操作: 未選択や権限不足はすべて ephemeral メッセージでフィードバック。
- メッセージ処理: メッセージ編集・ロール付与失敗時に WARN、想定外例外は ERROR ログ。

## テスト
- `tests/bot/test_commands.py`: `/nickname_sync_setup` が View を返却し、ギルド/ユーザー情報を保持することを検証。
- `tests/views/test_nickname_sync_setup_view.py`: 選択必須・成功時 upsert・権限許可/拒否の双方をスタブで検証。
- `tests/bot/test_handlers.py`: ニックネーム同期処理の本文→ニックネーム反映、32文字バリデーション、ロール未設定/既存ロール時の挙動をモックで検証。
