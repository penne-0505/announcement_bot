---
title: "ニックネーム自動同期 Intent"
domain: "bot"
status: "active"
version: "0.2.0"
created: "2025-11-12"
updated: "2025-11-23"
related_plan: "docs/plan/bot/channel-nickname-role-sync/plan.md"
owners:
  - "announcement bot maintainers"
---

## 背景
- Clover サーバーでは参加者が所定チャンネルにニックネームを投稿 → スタッフが手動で内容確認・ロール付与していた。
- 手作業ゆえ入力揺れや付与漏れが起き、ロール更新まで時間がかかる課題があった。
- 既存 `/setup` はモーダル送信のみで、チャンネル監視やロール操作の仕組みがなかった。

## 決定事項
1. **Slash コマンド**: `/nickname_sync_setup` を追加し、ギルド内で View (ChannelSelect + RoleSelect) を通じて監視チャンネルと付与ロールを設定できるようにした。実行者には Manage Roles 権限を要求し、結果を ephemeral で通知する。
2. **永続化**: PostgreSQL (Railway) に `channel_nickname_rules` テーブルを作成し、`guild_id + channel_id` 主キーで設定を upsert する。asyncpg プールは `app.database.Database` が管理する。
3. **メッセージ処理**: `bot.handlers.enforce_nickname_and_role` で投稿本文をそのままメンバーのニックネームに設定する（32文字超過はスキップし、成功/失敗をリアクションで示す）。指定ロールは従来通り自動付与し、Bot 自身の投稿や同一ニックネームはスキップする。
4. **エラーハンドリング**: メッセージ編集・ロール付与が Forbidden / HTTPException の場合はロガーに警告を出す。ロール未取得時も WARN ログで気づけるようにする。
5. **ドキュメント**: 新機能専用の plan/intent/guide/reference を追加し、README と `.env.example` へ `DATABASE_URL` と Railway デプロイ手順を追記した。

## トレードオフ
- ORM ではなく生 SQL + asyncpg を選択し、依存を最小化した。複雑なマイグレーションが必要になった場合に Alembic を導入する。
- 設定は 1 チャンネルにつき 1 ロールに限定し、複数ロール付与や条件分岐は次段の intent で検討する。
- DB 接続はアプリ起動時に 1 度初期化し、異常時は Bot を停止させる実装にした。再接続の自動リトライは入れていないため、Railway でプロセス再起動を行う想定。

## 影響範囲
- `pyproject`, `.env.example`, README, docs を含む複数ファイルを更新。
- Bot 起動には PostgreSQL が必須となり、`DATABASE_URL` 未設定時は起動前にログ出力して終了する。

## テスト/観測
- Slash コマンドとメッセージ処理は pytest でモック検証し、CI で自動実行する。
- ログには設定登録/編集完了、チャンネル監視での成功/失敗が INFO/WARN/ERROR で出力され、Railway ログで可視化可能。

## フォローアップ
1. 複数ロール付与やテンプレート整形ニーズが発生したら新たな draft/survey を作成する。
2. ログ監視やメトリクス出力を要望する場合は Observability plan を追加検討する。
