# announcement_bot

Discord 上で告知メッセージを安全に配信するための最小限の Slash コマンド `/setup` とメッセージ送信モーダルを提供します。

## セットアップ
1. 依存関係をインストールします。
   ```bash
   poetry install
   ```
2. `.env.example` をコピーして Discord Bot トークンと PostgreSQL 接続情報を設定します。
   ```bash
   cp .env.example .env
   # DISCORD_BOT_TOKEN=xxx
   # DATABASE_URL=postgresql://user:password@host:5432/dbname
   ```
3. Bot を起動します。
   ```bash
   poetry run announcement-bot
   # もしくは
   poetry run python -m src.main
   ```

## Slash コマンド `/setup`
- `/setup` を実行すると、フォローアップで「メッセージ送信」ボタン付きの View が返り、モーダルから任意チャンネルへ本文を投稿できます。
- 正常に送信できた場合は `<#channel_id>` への送信結果を ephemeral メッセージで通知します。
- 無効なチャンネル ID や権限不足時はエラーメッセージを ephemeral で返します。

## Slash コマンド `/nickname_guard`
- 監視対象チャンネルと付与ロールを指定し、対象チャンネルでの投稿を「投稿者のニックネーム」に書き換えつつ、同時にロールを自動付与します。
- チャンネル／ロールは同一ギルド内のもののみ選択可能です。結果はすべて ephemeral メッセージで返ります。
- Railway の PostgreSQL (`DATABASE_URL`) に設定が保存されるため、再起動後も設定が維持されます。
- 監視対象チャンネルでのメッセージ編集・ロール付与失敗時は INFO/WARN ログに記録されるので、Railway ログで状況を確認してください。

## テスト
- モーダルの検証ロジックと Slash コマンド登録を `pytest` + `pytest-asyncio` でカバーしています。
- 実行例:
  ```bash
  poetry run pytest
  ```

## ドキュメント
- 計画: `docs/plan/bot/messaging-modal-port/plan.md`
- Intent: `docs/intent/bot/messaging-modal-port/intent.md`
- 利用ガイド: `docs/guide/bot/messaging-modal-port/guide.md`
- リファレンス: `docs/reference/bot/messaging-modal-port/reference.md`
