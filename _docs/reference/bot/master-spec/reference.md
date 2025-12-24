---
title: "announcement_bot 確定仕様"
domain: "bot"
status: "active"
version: "0.2.0"
created: "2025-11-12"
updated: "2025-11-23"
related_plan:
  - "docs/plan/bot/messaging-modal-port/plan.md"
  - "docs/plan/bot/channel-nickname-role-sync/plan.md"
  - "docs/plan/bot/temporary-voice-channels/plan.md"
related_intents:
  - "docs/intent/bot/messaging-modal-port/intent.md"
  - "docs/intent/bot/channel-nickname-role-sync/intent.md"
  - "docs/intent/bot/temporary-voice-channels/intent.md"
references:
  - "docs/guide/bot/messaging-modal-port/guide.md"
  - "docs/guide/bot/channel-nickname-role-sync/guide.md"
  - "docs/guide/bot/temporary-voice-channels/guide.md"
---

## 目的

- Clover 発表用 Discord サーバーで安全に告知文を投稿する `/setup` モーダル機能、本人確認チャンネルのニックネーム同期 + ロール自動付与機能、一時的なボイスチャンネル (`/temporary_vc`) を恒久運用する。
- 本書は 2025-11-12 時点のマスター仕様を定義し、コード・ドキュメントの整合性確認の基準とする。

## システム構成

| モジュール                                | 役割                                                                                                                                                                 |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/app/config.py`                       | `.env`/環境変数から `DISCORD_BOT_TOKEN` と `DATABASE_URL` を読み込み、`AppConfig` を返す。                                                                           |
| `src/app/database.py`                     | asyncpg プールを管理し、`channel_nickname_rules` / `temporary_vc_categories` / `temporary_voice_channels` を `CREATE TABLE IF NOT EXISTS` で自動作成する。           |
| `src/app/container.py`                    | `Database` + 各 Repository を初期化し、`BotClient` とコマンド登録を `TemporaryVoiceChannelService` と合わせて返す。                                                  |
| `src/app/runtime.py` / `src/main.py`      | ログ初期化の上で `build_discord_app` → `DiscordApplication.run()` を実行する CLI エントリポイント。                                                                  |
| `src/bot/client.py`                       | `discord.Client` 拡張。`on_ready` で `tree.sync()` + 一時 VC レコード同期、`on_message` で監視チャンネルハンドラ、`on_voice_state_update` で一時 VC 自動削除を行う。 |
| `src/bot/commands.py`                     | Slash コマンド `/setup`, `/nickname_sync_setup`, `/temporary_vc` を登録。                                                                                            |
| `src/views/view.py`                       | `/setup` フローで利用する `SendModalView` / `SendMessageModal` を提供。                                                                                              |
| `src/views/nickname_sync_setup.py`        | `/nickname_sync_setup` から呼び出す `NicknameSyncSetupView`（ChannelSelect + RoleSelect + 保存ボタン）。                                                             |
| `src/bot/handlers.py`                     | 監視対象チャンネルの投稿内容をニックネームとしてメンバーに適用し、ロールを付与する共通ロジック。                                                                     |
| `src/app/repositories/temporary_voice.py` | 一時 VC カテゴリ/チャンネルの永続化を行う。                                                                                                                          |
| `src/app/services/temporary_voice.py`     | カテゴリ設定、VC 作成・削除、VoiceState 監視を統括する。                                                                                                             |

## 実行環境と依存

- Python 3.12 系 (`pyproject.toml`)。
- 主要ライブラリ: `discord-py>=2.6.4`, `python-dotenv>=1.1.0`, `asyncpg>=0.29.0`, `pytest`。
- テストランナー設定: ルートの `conftest.py` で最小イベントループハンドラを提供し、`pytest.mark.asyncio` テストを外部プラグイ
  ンなしで実行できる。
- CLI 起動方法:
  - `poetry run announcement-bot`
  - `poetry run python -m src.main`

## 設定

| 変数                      | 必須 | 説明                                                                                                                                             |
| ------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `DISCORD_BOT_TOKEN`       | ✅   | Discord Bot のトークン。未設定時は `ValueError` を投げ、runtime で例外ログを出して終了 (`src/app/config.py:50-78`, `src/app/runtime.py:12-27`)。 |
| `DATABASE_URL`            | ✅   | Railway Postgres 等の接続文字列。未設定時は `ValueError` (`src/app/config.py:58-79`)。                                                           |
| `FORCE_REGENERATE_COLORS` | 任意 | `true/1/yes/on` のいずれかで **起動時に全 Guild の Embed カラーを再生成** する。未指定/空文字は通常モード（未登録 Guild のみ割当）。             |

- `.env.example` に両変数を記載済み。`load_config()` は `dotenv` による `.env` 読み込み → 環境変数優先の挙動。

## データモデル

`channel_nickname_rules`（`src/app/database.py:64-94`）

| カラム       | 型                       | 説明                                         |
| ------------ | ------------------------ | -------------------------------------------- |
| `guild_id`   | BIGINT                   | 設定対象ギルド ID                            |
| `channel_id` | BIGINT                   | 監視対象チャンネル ID                        |
| `role_id`    | BIGINT                   | 自動付与するロール ID                        |
| `updated_by` | BIGINT                   | 設定を保存したユーザー ID                    |
| `updated_at` | TIMESTAMPTZ              | `NOW()` デフォルト。リポジトリ更新時に上書き |
| 主キー       | `(guild_id, channel_id)` |

`ChannelNicknameRuleRepository` (`src/app/repositories/channel_rules.py:25-62`)

- `upsert_rule(...)` は ON CONFLICT で role/updated_by/updated_at を更新。戻り値は dataclass。
- `get_rule_for_channel(...)` でギルド + チャンネル単位の設定を取得。

`temporary_vc_categories` / `temporary_voice_channels` (`src/app/database.py:80-98`)

| テーブル                   | 目的                             | 主なカラム                                                                                             |
| -------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `temporary_vc_categories`  | ギルドごとの一時 VC カテゴリ設定 | `guild_id PK`, `category_id`, `updated_by`, `updated_at`                                               |
| `temporary_voice_channels` | ユーザーごとの一時 VC 所有情報   | `guild_id`, `owner_user_id` (PK), `channel_id (NULL許容)`, `category_id`, `created_at`, `last_seen_at` |

`TemporaryVoiceCategoryRepository` はカテゴリの upsert/get/delete を行い、`TemporaryVoiceChannelRepository` は VC レコードの `create_record` / `update_channel_id` / `get_by_owner` / `get_by_channel` / `purge_guild` / `touch_last_seen` を提供する。

## Slash コマンド仕様

| name                   | 目的                                                             | 権限                                        | 実装                         |
| ---------------------- | ---------------------------------------------------------------- | ------------------------------------------- | ---------------------------- |
| `/setup`               | モーダル経由で任意チャンネルへ告知メッセージを送信               | 既定 (DM 不可)                              | `src/bot/commands.py:22-33`  |
| `/nickname_sync_setup` | 監視チャンネル/ロールを GUI で選択し、ニックネーム同期設定を保存 | Manage Roles + Manage Messages (guild only) | `src/bot/commands.py:35-67`  |
| `/temporary_vc`        | 一時 VC カテゴリ設定/作成/削除をサブコマンドで提供               | Manage Channels (`category` のみ)           | `src/bot/commands.py:70-155` |

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

### `/temporary_vc`

1. `temporary_vc category`: Manage Channels 権限必須。カテゴリを 1 つ指定して `TemporaryVoiceChannelService.configure_category()` を実行し、既存一時 VC を削除した上で `temporary_vc_categories` を更新する。
2. `temporary_vc create`: 一般メンバーが自分専用 VC をリクエスト。カテゴリ未設定時は警告、既存 VC がある場合は `<#channel>` を案内。新規作成時は `guild.create_voice_channel()` で所有者に `PermissionOverwrite(manage_channels=True, move_members=True, mute_members=True, deafen_members=True, connect=True, speak=True, stream=True, use_voice_activation=True, view_channel=True)` を付与する。
3. `temporary_vc reset`: 所有者が self-service で VC とレコードを削除。見つからない場合は対象なしメッセージを返す。
4. すべて guild-only コマンドで、応答は ephemeral。作成/削除結果は INFO/WARN/ERROR ログに出力される。

## モーダル / View 仕様

| コンポーネント          | ファイル                                  | 要点                                                                                                               |
| ----------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `SendModalView`         | `src/views/view.py:12-21`                 | `/setup` 経由でモーダルボタンを表示。                                                                              |
| `SendMessageModal`      | `src/views/view.py:36-108`                | チャンネル ID/本文の入力欄。バリデーションおよび `interaction.response.send_message(..., ephemeral=True)` を実行。 |
| `NicknameSyncSetupView` | `src/views/nickname_sync_setup.py:16-105` | ChannelSelect + RoleSelect + 保存ボタン。executor 固定、成功時に DB へ永続化。                                     |

## メッセージ監視フロー

1. `BotClient` (`src/bot/client.py`) は `on_ready` で `tree.sync()` を実行し、`TemporaryVoiceChannelService.cleanup_orphaned_channels(self.guilds)` でレコードと実チャンネルの整合性を取る。
2. `on_message` ではギルド外/Bot 投稿を除外し、`ChannelNicknameRuleRepository.get_rule_for_channel()` が見つかれば `enforce_nickname_and_role()` を実行。
3. `enforce_nickname_and_role` (`src/bot/handlers.py:13-92`):
   - `message.content.strip()` を新ニックネーム候補とし、空/32 文字超過はスキップ（後者は `❌` リアクション）。
   - 異なる場合のみ `member.edit(nick=new_nickname, reason="Nickname sync from message content")` を実行し、成功時は `✅` リアクションを付与。`discord.Forbidden` は WARN、`discord.HTTPException` は ERROR。
   - ギルドから対象ロールを取得し、未付与なら `member.add_roles(role, reason="Nickname guard auto assignment")`。
4. `on_voice_state_update` は `TemporaryVoiceChannelService.handle_voice_state_update(member, before.channel, after.channel)` を呼び、
   - `before.channel` の `members` が空で管理対象レコードがあれば `channel.delete(reason="Temporary voice channel expired")` → レコード削除。
   - `after.channel` が管理対象なら `touch_last_seen()` で滞在情報を更新。

## 権限・前提

- Bot には **Send Messages / Manage Messages / Manage Roles** 権限、かつ付与対象ロールより上位のロール階層が必要。
- `/nickname_sync_setup` は Manage Roles + Manage Messages 権限を持つメンバーのみ実行可能 (`@discord.app_commands.default_permissions`)。
- `/temporary_vc category` は Manage Channels 権限を要求し、Voice State Intent が Bot/Portal の両方で有効になっている必要がある。`create`/`reset` はギルド内であれば誰でも実行できる。
- Intents は `discord.Intents.all()` で初期化しているため、Bot ポータル側でも Message Content Intent/Voice State Intent を有効化する。

## エラーハンドリング & ログ

- 設定読み込み失敗は `src/app/runtime.py:12-27` で例外ログを出して終了。
- DB 接続/テーブル作成に失敗すると `Database.connect()` 内で例外が送出され、上位で捕捉 → ログ (`src/app/runtime.py:18-27`)。
- Slash コマンド／View／ハンドラはすべてエラーを `interaction.response.send_message(..., ephemeral=True)` で通知し、詳細は LOGGER(INFO/WARNING/ERROR) へ記録。
- 一時 VC では Discord API 失敗時にレコードを削除してロールバックし、カテゴリが削除されていた場合は WARN ログで再設定を促す。

## テストカバレッジ

| テスト                                         | 対象                 | 概要                                                                                           |
| ---------------------------------------------- | -------------------- | ---------------------------------------------------------------------------------------------- |
| `tests/views/test_send_message_modal.py`       | モーダルの入力検証   | ID 変換、キャッシュ済み/フェッチ経路での送信成功、各種エラー、非 Messageable 判定。            |
| `tests/bot/test_commands.py`                   | Slash コマンド       | `/setup` の View 返却と `/nickname_sync_setup` の View パラメータ検証。                        |
| `tests/views/test_nickname_sync_setup_view.py` | View 単体            | 選択必須、成功時 upsert、操作権限の許可/拒否パターン。                                         |
| `tests/bot/test_handlers.py`                   | ニックネーム同期処理 | 投稿本文からのニックネーム設定、32 文字バリデーション、ロール未設定/既存ロール時の分岐を確認。 |

## 運用メモ

- Railway では `DATABASE_URL` を環境変数で提供し、Postgres 停止時は Bot を再起動して再接続する（自動リトライは未実装）。
- ログ監視で Forbidden/HTTPException を検知した場合は、権限・ロール階層・対象チャンネルのアクセス設定を確認する。
