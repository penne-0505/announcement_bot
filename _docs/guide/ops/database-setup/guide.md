---
title: "Supabase Postgres セットアップガイド"
domain: "ops"
status: "active"
version: "0.3.0"
created: "2025-11-15"
updated: "2025-12-25"
related_intents:
  - "docs/intent/bot/messaging-modal-port/intent.md"
  - "docs/intent/bot/channel-nickname-role-sync/intent.md"
  - "docs/intent/bot/temporary-voice-channels/intent.md"
references:
  - "README.md"
  - "docs/reference/bot/master-spec/reference.md"
  - "docs/guide/ops/railway-setup/guide.md"
---

## 概要

- `announcement_bot` は Supabase の PostgREST API へ接続し、Python SDK 経由で CRUD を実行する。
- 本ガイドでは Supabase 側で取得する `SUPABASE_URL` / `SUPABASE_KEY` の設定方法と、テーブル作成の確認ポイントをまとめる。
- 開発環境とプロダクションでは `SUPABASE_URL` / `SUPABASE_KEY` を切り替えるだけで運用できる。

## 役割と要件

- 必須環境変数: `SUPABASE_URL`, `SUPABASE_KEY`。未設定時は起動に失敗する。
- Supabase の接続情報は Project Settings → API から取得する。
- テーブルは Supabase の SQL Editor で事前作成し、アプリは CRUD のみを実行する。

## 前提準備

1. リポジトリで `poetry install` を実行し、`discord-py`, `supabase`, `python-dotenv` などの依存を取得する。
2. Supabase でプロジェクトを作成し、Project Settings → API から `SUPABASE_URL` と `SUPABASE_KEY` を取得する。
3. Supabase の SQL Editor で `supabase/schema.sql` を実行し、テーブルを作成する。
4. `.env`（あるいはホストの環境変数）で `DISCORD_BOT_TOKEN` と `SUPABASE_URL` / `SUPABASE_KEY` を設定する。

## Supabase 接続設定

- `SUPABASE_URL` は `https://<project>.supabase.co` 形式。
- `SUPABASE_KEY` はサーバー用途の場合 Service Role Key を推奨。
- 複数インスタンス運用でも同一 DB を共有できる（PostgREST 経由で同時書き込み可能）。

## アプリによる初期化フロー

1. `.env` またはホストの環境で `SUPABASE_URL` / `SUPABASE_KEY` を読み込む。
2. `poetry run announcement-bot` などでアプリを起動し、`Database.connect()` が Supabase client を初期化する。
3. ログに以下のメッセージが連続して出力されることを確認する:
   - `Supabase (<url>) への接続を開始します。`
   - `Supabase クライアントの初期化が完了しました。`
4. `channel_nickname_rules`, `temporary_vc_categories`, `temporary_voice_channels` テーブルが Supabase に作成済みであることを SQL Editor で確認する。

## 手動検証・保守コマンド例

| 目的                 | 実行例                                                                                |
| -------------------- | ------------------------------------------------------------------------------------- |
| テーブル一覧確認     | `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';`     |
| ルール件数確認       | `SELECT COUNT(*) FROM channel_nickname_rules;`                                        |
| 一時 VC レコード調査 | `SELECT guild_id, channel_id FROM temporary_voice_channels WHERE channel_id IS NULL;` |
| データバックアップ   | Supabase のバックアップ/スナップショット機能を利用                                    |

## 運用チェックリスト

- [ ] `SUPABASE_URL` / `SUPABASE_KEY` が正しい。
- [ ] Bot の起動ログで `Supabase ... への接続を開始します。` / `Supabase クライアントの初期化が完了しました。` が出力されている。
- [ ] Supabase の SQL Editor でテーブルが作成されていることを確認する。
- [ ] `temporary_voice_channels` の `last_seen_at` が更新されていることを検証する（VoiceState イベントの受信ログ）。

## トラブルシューティング

| 症状               | 原因                            | 対応                                                                         |
| ------------------ | ------------------------------- | ---------------------------------------------------------------------------- |
| PostgREST エラー   | API キー誤り / RLS / ルール違反 | Supabase の API Key と RLS 設定を確認し、Service Role Key の利用を検討する。 |
| タイムアウト / 5xx | Supabase 停止/メンテナンス      | Supabase のステータスを確認し、復旧後に再起動。                              |

## 関連ドキュメント

- `README.md`: `.env` 設定と起動手順。
- `docs/reference/bot/master-spec/reference.md`: テーブル構造と永続化挙動。
- `docs/guide/ops/railway-setup/guide.md`: Railway から Supabase を利用する場合のセットアップ手順。
