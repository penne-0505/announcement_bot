---
title: "一時VC管理 Intent"
domain: "bot"
status: "active"
version: "0.1.0"
created: "2025-11-14"
updated: "2025-11-14"
related_plan: "docs/plan/bot/temporary-voice-channels/plan.md"
owners:
  - "announcement bot maintainers"
references:
  - "docs/reference/bot/temporary-voice-channels/reference.md"
  - "docs/guide/bot/temporary-voice-channels/guide.md"
---

## 背景
- Clover サーバーでは、配信用ルームやスタッフ控室などで即席のボイスチャンネル需要が増えているが、カテゴリ作成や権限設定を管理者が手動で行うと待ち時間が発生しがちだった。
- 既存 Bot はテキストチャンネル監視に限定されており、VoiceState Intent を活用した機能が存在しないため、plan (`docs/plan/bot/temporary-voice-channels/plan.md`) で定義した要件を実装する。
- 永続化には既存の SQLite/aiosqlite を継続利用し、ローカル/ホストベースの運用負荷を最小限に抑える。

## 決定事項
1. **Slash コマンド `/temporary_vc` を導入**し、`category`（Manage Channels 権限必須）、`create`、`reset` の 3 サブコマンドでカテゴリ登録～ユーザー自身の一時VC管理まで完結させる。カテゴリ更新時には旧 VC を全削除し、結果を INFO ログと応答メッセージで通知する。
2. **データモデル**: `temporary_vc_categories` と `temporary_voice_channels` の 2 テーブルを `Database._ensure_schema()` で自動作成する。`temporary_voice_channels` は `(guild_id, owner_user_id)` 主キーで 1 ユーザー 1 件を保証し、`channel_id` は作成完了後に更新する。
3. **サービス層**: `TemporaryVoiceChannelService` を新設し、カテゴリ整合性チェック、VC 作成/権限上書き、VoiceState 監視による自動削除、再起動時の孤立レコードクリーンアップを一元管理する。Discord API 失敗時はレコードをロールバックし WARN/ERROR を出力する。
4. **BotClient 拡張**: `on_ready` で一時VCレコードを同期し、`on_voice_state_update` でサービスへ処理を委譲する。これにより参加者が全員退出したチャンネルは自動削除され、DB と実態の乖離を防げる。
5. **ドキュメンテーション**: README / master spec / guide / reference を更新し、利用手順・API仕様・テーブル構造を公開する。plan の `status` を `active` とし、本 Intent をもって意思決定を確定した。

## トレードオフ
- View UI ではなく Slash コマンドでカテゴリを受け付けたため、操作はログベースで分かりやすい反面、「カテゴリを選択する GUI」は提供していない。将来的に需要があれば追加検討する。
- 永続層は `aiosqlite` + SQL 直書きのまま維持し、トランザクションを導入していない。作成フローは「INSERT → Discord API → UPDATE」で順次実行することで整合性を確保する。
- VoiceState 監視は `discord.Intents.all()` に依存する。Intent を細かく制限していないため、Bot 設定で VoiceState Intent を無効化すると機能しないが、ログで気付けるようにした。

## 影響範囲
- `src/app/database.py` にテーブル作成ロジックを追加し、`app.repositories` / `app.services` / `bot` 全体に変更が波及した。
- 新 Slash コマンドを README と master spec に追記。ユーザードキュメントとして `docs/guide/bot/temporary-voice-channels/guide.md`、仕様リファレンスとして `docs/reference/bot/temporary-voice-channels/reference.md` を追加した。
- デプロイ環境では VoiceState Intent が有効になっていることを再確認する運用が必要。

## テスト / 観測
- `tests/bot/test_commands.py` へ一時VCコマンドのモックテストを追加し、既存テストと合わせて `PYTHONPATH=src pytest` で 16 ケースを通過させた。
- サービス層の主要イベント（カテゴリ設定/作成/削除失敗）は `logging` で INFO/WARN/ERROR を出力し、ホストのログストリームで監視できるようにした。

## フォローアップ
1. カテゴリ未設定時の自動リマインドや UI 補助（Component ベース）の要望があれば draft を起こす。
2. 共同所有者や複数カテゴリなど plan の「今後の拡張余地」に記載した項目は別 Intent で扱う。
3. 長期的には VC 利用状況のメトリクス化やアーカイブレポートの出力を Observability plan に追加する。
