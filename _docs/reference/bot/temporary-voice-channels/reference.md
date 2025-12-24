---
title: "一時ボイスチャンネル リファレンス"
domain: "bot"
status: "beta"
version: "0.1.0"
created: "2025-11-14"
updated: "2025-11-14"
related_plan: "docs/plan/bot/temporary-voice-channels/plan.md"
related_intents:
  - "docs/intent/bot/temporary-voice-channels/intent.md"
references:
  - "docs/guide/bot/temporary-voice-channels/guide.md"
---

## Slash コマンド `/temporary_vc`
| サブコマンド | 目的 | 権限 | 応答 |
| --- | --- | --- | --- |
| `category` | 一時VCの作成先カテゴリを登録/更新 | `Manage Channels` | 削除済み件数・未発見件数付きの ephemeral メッセージ |
| `create` | 自分専用の VC をカテゴリ配下に作成 | 既定 (guild only) | 成功時: `<#channel>` メンション / 失敗時: カテゴリ未設定 or 既存VC案内 |
| `reset` | 自分の一時VCを手動削除 | 既定 (guild only) | 削除結果を ephemeral で通知 |

### `category`
- Slash コマンドのパラメータとして `discord.CategoryChannel` を受け取り、`TemporaryVoiceChannelService.configure_category()` を実行する。
- 既存レコード（`temporary_voice_channels`）を列挙し、`channel.delete(reason="Temporary voice channel category updated")` を発行。存在しなかった ID は `missing_channel_ids` に分類される。
- 応答例:
  ```text
  📁 一時VCカテゴリを <#1234567890> に設定しました。
  🧹 削除済み: 3 件 / 不存在: 1 件
  ```

### `create`
- `TemporaryVoiceChannelService.create_temporary_channel(member)` を呼び出し、`guild.create_voice_channel` で VC を生成する。
- チャンネル名は `member.display_name` を最大 32 文字でトリムし、所有者には `PermissionOverwrite(manage_channels=True, move_members=True, mute_members=True, deafen_members=True, connect=True, speak=True, stream=True, use_voice_activation=True, view_channel=True)` を付与する。
- 既存レコードがあれば `<#channel>` メンションを提示し（`channel_id` がまだ NULL で取得中でも既存扱い）、カテゴリ未設定時は `/temporary_vc category` を促す。

### `reset`
- `TemporaryVoiceChannelService.reset_temporary_channel(member)` が `temporary_voice_channels` レコードを削除し、実チャンネルが残っていれば `channel.delete(reason="Temporary voice channel category updated")` を実行する。
- 対象レコードが見つからない場合は「管理対象の一時VCは登録されていません。」と通知する。

## データモデル
- SQLite ファイルに `aiosqlite` で接続し、`Database._ensure_schema()` による `CREATE TABLE IF NOT EXISTS` でスキーマが自動準備される。

### `temporary_vc_categories`
| カラム | 型 | 説明 |
| --- | --- | --- |
| `guild_id` | INTEGER | ギルド ID（PK） |
| `category_id` | INTEGER | 一時VCを作成するカテゴリの ID |
| `updated_by` | INTEGER | 設定変更を実行したユーザー ID |
| `updated_at` | TEXT | 最終更新日時（`CURRENT_TIMESTAMP` デフォルト、ISO8601 文字列） |

### `temporary_voice_channels`
| カラム | 型 | 説明 |
| --- | --- | --- |
| `guild_id` | INTEGER | ギルド ID |
| `owner_user_id` | INTEGER | VC 所有者 (Slash 実行者) |
| `channel_id` | INTEGER | 作成済み VC の ID（作成中は NULL） |
| `category_id` | INTEGER | 作成当時のカテゴリ ID |
| `created_at` | TEXT | レコード作成日時（`CURRENT_TIMESTAMP` デフォルト） |
| `last_seen_at` | TEXT | VoiceState 受信日時（`CURRENT_TIMESTAMP` デフォルト、`touch_last_seen` で更新） |
| PK | `(guild_id, owner_user_id)` |

## サービス挙動
- `TemporaryVoiceChannelService.configure_category()` はカテゴリ更新後に `purge_guild()` でレコードをクリアし、新カテゴリを `upsert_category()` で保存する。
- `create_temporary_channel()` は `temporary_voice_channels` に仮レコードを作成 → Discord API で VC 作成 → `update_channel_id()` で `channel_id` を記録する。API 失敗時はレコードを削除してロールバックする。作成直前に `get_by_owner()` で存在チェックし、`sqlite3.IntegrityError`（ユニーク制約違反）を `TemporaryVoiceChannelExistsError` に置き換えて制御されたエラー応答とするため、二重送信でも Discord API 側の汎用エラーにならない。
- `handle_voice_state_update(member, before_channel, after_channel)`:
  - `before_channel.members` が空になった場合に `channel.delete(reason="Temporary voice channel expired")` を実行し、レコードも削除。
  - `after_channel` が管理対象なら `touch_last_seen()` で滞在を更新。
- `cleanup_orphaned_channels(guilds)` は起動時に全レコードを走査し、Bot が参加していないギルドや存在しない `channel_id` のレコードを削除する。

## ログ / エラー
- INFO
  - 一時VC作成成功: `guil`, `owner`, `channel`
  - カテゴリ登録/削除件数
  - 無人チャンネル削除
- WARN
  - チャンネル削除・作成時の `discord.Forbidden` / `discord.HTTPException`
  - 登録済みカテゴリが既に削除されていた場合
- ERROR
  - Discord API 失敗でレコードをロールバックした場合 (`TemporaryVoiceChannelCreationError`)

## テスト
- `tests/bot/test_commands.py` が `/temporary_vc category/create/reset` の応答をモック検証する。
- 既存テストと合わせて `PYTHONPATH=src pytest` で 16 テストが成功する。
