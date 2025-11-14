# announcement_bot

Discord 上で告知メッセージ送信 (`/setup`)、ニックネーム同期 + ロール自動付与 (`/nickname_sync_setup`)、一時ボイスチャンネル作成 (`/temporary_vc`) を提供する Bot です。

## 主な機能
- `/setup`: チャンネル ID + 本文を入力できるモーダルを提供し、任意のテキストチャンネルへ告知文を投稿します。無効な ID やアクセス権限不足は ephemeral メッセージで即時通知されます。
- `/nickname_sync_setup`: ChannelSelect + RoleSelect の View から監視対象チャンネルと付与ロールを登録。登録済みチャンネルへの投稿は投稿者の `display_name` に書き換えられ、ロール未付与時は指定ロールを自動付与します。ログには成功・警告・例外のいずれも出力されます。
- `/temporary_vc`: 管理者がカテゴリを登録し、一般メンバーは `/temporary_vc create` で即席 VC を生成できます。VoiceState を監視して無人チャンネルは自動削除されます。

## セットアップ
1. 依存関係をインストールします。
   ```bash
   poetry install
   ```
2. `.env.example` をコピーして環境変数（`DISCORD_BOT_TOKEN` / `DATABASE_URL`）を設定します。
   ```bash
   cp .env.example .env
   # DISCORD_BOT_TOKEN=bot-token
   # DATABASE_URL=postgresql://user:password@host:5432/dbname
   ```
   - `DATABASE_URL` は asyncpg で利用する PostgreSQL 接続文字列です。起動時に `channel_nickname_rules(guild_id, channel_id, role_id, updated_by, updated_at)` テーブルを `CREATE TABLE IF NOT EXISTS` で自動作成します。
3. Bot を起動します。
   ```bash
   poetry run announcement-bot
   # または
   poetry run python -m src.main
   ```

## システム構成の補足
- `src/app/config.py` で `.env` を読み込み `AppConfig(discord.token, database.url)` を構築。
- `src/app/database.py` が asyncpg プールをさばき、`channel_nickname_rules` のスキーマを初期化・クエリを提供。
- `src/app/container.py` で `Database` + `ChannelNicknameRuleRepository` + `BotClient` を組み合わせて `DiscordApplication` を構成。
- `src/bot/commands.py` で `/setup`・`/nickname_sync_setup` を登録し、`src/views/*` の modal/View を返す。
- `src/bot/client.py` の `on_message` でルールを取得し、`src/bot/handlers.py` の `enforce_nickname_and_role` で本文編集・ロール付与を実行。

## テスト
- `pytest` + `pytest-asyncio` でモーダル・View・Slash コマンド・ハンドラ・一時VCコマンドのユニットをカバーしています。
- モジュール解決のため `PYTHONPATH=src` を付与して実行してください。
  ```bash
  PYTHONPATH=src pytest
  ```

## ドキュメント
- **メッセージ送信モーダル (`/setup`)**
  - 計画: `docs/plan/bot/messaging-modal-port/plan.md`
  - Intent: `docs/intent/bot/messaging-modal-port/intent.md`
  - 利用ガイド: `docs/guide/bot/messaging-modal-port/guide.md`
  - リファレンス: `docs/reference/bot/messaging-modal-port/reference.md`
- **ニックネーム同期 + ロール付与 (`/nickname_sync_setup`)**
  - 計画: `docs/plan/bot/channel-nickname-role-sync/plan.md`
  - Intent: `docs/intent/bot/channel-nickname-role-sync/intent.md`
  - 利用ガイド: `docs/guide/bot/channel-nickname-role-sync/guide.md`
  - リファレンス: `docs/reference/bot/channel-nickname-role-sync/reference.md`
- **一時ボイスチャンネル (`/temporary_vc`)**
  - 計画: `docs/plan/bot/temporary-voice-channels/plan.md`
  - Intent: `docs/intent/bot/temporary-voice-channels/intent.md`
  - 利用ガイド: `docs/guide/bot/temporary-voice-channels/guide.md`
  - リファレンス: `docs/reference/bot/temporary-voice-channels/reference.md`
