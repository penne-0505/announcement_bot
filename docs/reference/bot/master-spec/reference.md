---
title: "announcement_bot 確定仕様"
domain: "bot"
status: "active"
version: "0.2.0"
created: "2025-11-12"
updated: "2025-11-12"
related_plan:
  - "docs/plan/bot/messaging-modal-port/plan.md"
  - "docs/plan/bot/channel-nickname-role-sync/plan.md"
related_intents:
  - "docs/intent/bot/messaging-modal-port/intent.md"
  - "docs/intent/bot/channel-nickname-role-sync/intent.md"
references:
  - "docs/guide/bot/messaging-modal-port/guide.md"
  - "docs/guide/bot/channel-nickname-role-sync/guide.md"
---

## 目的
- Clover 発表用 Discord サーバーで安全に告知文を投稿する `/setup` モーダル機能と、本人確認チャンネルのニックネーム同期 + ロール自動付与機能を恒久運用する。
- 本書は 2025-11-12 時点のマスター仕様を定義し、コード・ドキュメントの整合性確認の基準とする。

## システム構成
| モジュール | 役割 |
| --- | --- |
| `src/app/config.py` | `.env`/環境変数から `DISCORD_BOT_TOKEN` と `DATABASE_URL` を読み込み、`AppConfig` を返す。 |
| `src/app/database.py` | asyncpg プールを管理し、`channel_nickname_rules` テーブルを `CREATE TABLE IF NOT EXISTS` で自動作成する。 |
| `src/app/container.py` | `Database` + `ChannelNicknameRuleRepository` を初期化し、`BotClient` とコマンド登録をセットで返す。 |
| `src/app/runtime.py` / `src/main.py` | ログ初期化の上で `build_discord_app` → `DiscordApplication.run()` を実行する CLI エントリポイント。 |
| `src/bot/client.py` | `discord.Client` 拡張。`on_ready` で `tree.sync()`、`on_message` で監視チャンネルのハンドラを実行。 |
| `src/bot/commands.py` | Slash コマンド `/setup` と `/nickname_sync_setup` を登録。 |
| `src/views/view.py` | `/setup` フローで利用する `SendModalView` / `SendMessageModal` を提供。 |
| `src/views/nickname_sync_setup.py` | `/nickname_sync_setup` から呼び出す `NicknameSyncSetupView`（ChannelSelect + RoleSelect + 保存ボタン）。 |
| `src/bot/handlers.py` | 監視対象チャンネル投稿をニックネームへ上書きし、ロールを付与する共通ロジック。 |

## 実行環境と依存
- Python 3.12 系 (`pyproject.toml`)。
- 主要ライブラリ: `discord-py>=2.6.4`, `python-dotenv>=1.1.0`, `asyncpg>=0.29.0`, `pytest`, `pytest-asyncio`。
- CLI 起動方法:
  - `poetry run announcement-bot`
  - `poetry run python -m src.main`

## 設定
| 変数 | 必須 | 説明 |
| --- | --- | --- |
| `DISCORD_BOT_TOKEN` | ✅ | Discord Bot のトークン。未設定時は `ValueError` を投げ、runtime で例外ログを出して終了 (`src/app/config.py:50-78`, `src/app/runtime.py:12-27`)。 |
| `DATABASE_URL` | ✅ | Railway Postgres 等の接続文字列。未設定時は `ValueError` (`src/app/config.py:58-79`)。 |
- `.env.example` に両変数を記載済み。`load_config()` は `dotenv` による `.env` 読み込み→環境変数優先の挙動。

## データモデル
`channel_nickname_rules`（`src/app/database.py:64-77`）

| カラム | 型 | 説明 |
| --- | --- | --- |
| `guild_id` | BIGINT | 設定対象ギルド ID |
| `channel_id` | BIGINT | 監視対象チャンネル ID |
| `role_id` | BIGINT | 自動付与するロール ID |
| `updated_by` | BIGINT | 設定を保存したユーザー ID |
| `updated_at` | TIMESTAMPTZ | `NOW()` デフォルト。リポジトリ更新時に上書き |
| 主キー | `(guild_id, channel_id)` |

`ChannelNicknameRuleRepository` (`src/app/repositories/channel_rules.py:25-62`)
- `upsert_rule(...)` は ON CONFLICT で role/updated_by/updated_at を更新。戻り値は dataclass。
- `get_rule_for_channel(...)` でギルド + チャンネル単位の設定を取得。

## Slash コマンド仕様
| name | 目的 | 権限 | 実装 |
| --- | --- | --- | --- |
| `/setup` | モーダル経由で任意チャンネルへ告知メッセージを送信 | 既定 (DM 不可) | `src/bot/commands.py:22-33` |
| `/nickname_sync_setup` | 監視チャンネル/ロールを GUI で選択し、ニックネーム同期設定を保存 | Manage Roles + Manage Messages (guild only) | `src/bot/commands.py:35-67` |

### `/setup`
1. `interaction.response.defer(ephemeral=True)` で応答ウィンドウ確保。
2. `SendModalView`（`src/views/view.py:12-34`）をフォローアップで返却。
3. `SendMessageModal` (`src/views/view.py:36-109`) がチャンネル ID + 本文を入力させ、`process_modal_submission` (`src/views/view.py:59-108`) で検証。
4. 正常時は `<#channel>` 宛に `channel.send()`・成功メッセージ ephemeral。エラー時は `ERROR_*` を表示、例外はログ + 汎用メッセージ。

### `/nickname_sync_setup`
1. コマンド実行と同時に `NicknameSyncSetupView` を含む ephemeral メッセージを返却。
2. View 構成 (`src/views/nickname_sync_setup.py`):
   - ChannelSelect: Text/Announcement チャンネルのみ選択可能、1 件必須。
   - RoleSelect: 1 件必須。
   - 保存ボタン: 両方揃っていなければ `ERROR_SELECT_REQUIRED`。揃っていれば `ChannelNicknameRuleRepository.upsert_rule()` を呼び出し、結果を `SUCCESS_MESSAGE` で通知。
3. `interaction_check` で実行者以外の操作を拒否し、`ERROR_UNAUTHORIZED` を表示。
4. 保存成功で View を停止 (`View.stop()`)、ログに `guild/channel/role/executor` を INFO で残す。

## モーダル / View 仕様
| コンポーネント | ファイル | 要点 |
| --- | --- | --- |
| `SendModalView` | `src/views/view.py:12-21` | `/setup` 経由でモーダルボタンを表示。 |
| `SendMessageModal` | `src/views/view.py:36-108` | チャンネル ID/本文の入力欄。バリデーションおよび `interaction.response.send_message(..., ephemeral=True)` を実行。 |
| `NicknameSyncSetupView` | `src/views/nickname_sync_setup.py:16-105` | ChannelSelect + RoleSelect + 保存ボタン。executor 固定、成功時に DB へ永続化。 |

## メッセージ監視フロー
1. `BotClient` (`src/bot/client.py:13-53`) は `on_ready` で `self.tree.sync()` を実行し、`on_message` で以下を実施。
2. 投稿がギルド外 or Bot 投稿の場合はスキップ。
3. `ChannelNicknameRuleRepository.get_rule_for_channel()` を呼んで設定が存在すれば `enforce_nickname_and_role()` を await。
4. `enforce_nickname_and_role` (`src/bot/handlers.py:13-58`):
   - 表示名 (`display_name`→`global_name`→`name`) と本文が異なる場合は `message.edit(content=display_name, allowed_mentions=AllowedMentions.none())`。
   - ギルドから対象ロールを取得し、未付与なら `member.add_roles(role, reason="Nickname guard auto assignment")`。
   - Forbidden/HTTPException は WARN ログを残し処理継続。

## 権限・前提
- Bot には **Send Messages / Manage Messages / Manage Roles** 権限、かつ付与対象ロールより上位のロール階層が必要。
- `/nickname_sync_setup` は Manage Roles + Manage Messages 権限を持つメンバーのみ実行可能 (`@discord.app_commands.default_permissions`)。
- Intents は `discord.Intents.all()` で初期化しているため、Bot ポータル側でも Message Content Intent を有効化する。

## エラーハンドリング & ログ
- 設定読み込み失敗は `src/app/runtime.py:12-27` で例外ログを出して終了。
- DB 接続/テーブル作成に失敗すると `Database.connect()` 内で例外が送出され、上位で捕捉→ログ (`src/app/runtime.py:18-27`)。
- Slash コマンド／View／ハンドラはすべてエラーを `interaction.response.send_message(..., ephemeral=True)` で通知し、詳細は LOGGER(INFO/WARNING/ERROR) へ記録。

## テストカバレッジ
| テスト | 対象 | 概要 |
| --- | --- | --- |
| `tests/views/test_send_message_modal.py` | モーダルの入力検証 | ID 変換、フェッチ成功/失敗、非 Messageable 判定など。 |
| `tests/bot/test_commands.py` | Slash コマンド | `/setup` の View 返却と `/nickname_sync_setup` の View パラメータ検証。 |
| `tests/views/test_nickname_sync_setup_view.py` | View 単体 | 選択必須、成功時 upsert、他ユーザー拒否。 |
| `tests/bot/test_handlers.py` | ニックネーム同期処理 | メッセージ編集 + ロール付与成功/失敗パターン。 |

## 運用メモ
- Railway では `DATABASE_URL` を環境変数で提供し、Postgres 停止時は Bot を再起動して再接続する（自動リトライは未実装）。
- ログ監視で Forbidden/HTTPException を検知した場合は、権限・ロール階層・対象チャンネルのアクセス設定を確認する。
