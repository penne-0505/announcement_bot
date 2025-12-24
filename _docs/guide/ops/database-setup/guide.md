---
title: "Supabase Postgres セットアップガイド"
domain: "ops"
status: "active"
version: "0.3.0"
created: "2025-11-15"
updated: "2025-12-24"
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
- `announcement_bot` は Supabase の Postgres へ接続し、`Database._ensure_schema()` が起動時に `CREATE TABLE IF NOT EXISTS` を実行する。
- 本ガイドでは Supabase 側で取得する `DATABASE_URL`（Postgres DSN）の設定方法と、テーブル初期化の確認ポイントをまとめる。
- 開発環境とプロダクションでは `DATABASE_URL` を切り替えるだけで運用できる。

## 役割と要件
- 必須環境変数: `DATABASE_URL`（例: `postgresql://user:pass@host:5432/db`）。未設定時は起動に失敗する。
- Supabase の接続情報は Project Settings → Database から取得する。
- `asyncpg` を使った接続プールで運用し、起動時にテーブルが自動作成される。

## 前提準備
1. リポジトリで `poetry install` を実行し、`discord-py`, `asyncpg`, `python-dotenv` などの依存を取得する。
2. Supabase でプロジェクトを作成し、Database から接続文字列（`postgresql://...`）を取得する。
3. `.env`（あるいはホストの環境変数）で `DISCORD_BOT_TOKEN` と `DATABASE_URL` を設定し、`FORCE_REGENERATE_COLORS` などのフラグは必要に応じて設定する。

## Supabase 接続設定
- `DATABASE_URL` は Supabase の `Connection string` を使用する。
- `postgresql://` 形式で `host`, `user`, `password`, `db` を含める。
- 複数インスタンス運用でも同一 DB を共有できる（Postgres なので同時書き込み可能）。

## アプリによる初期化フロー
1. `.env` またはホストの環境で `DATABASE_URL` を読み込む。
2. `poetry run announcement-bot` などでアプリを起動し、`Database.connect()` が Postgres 接続を確立する。
3. ログに以下のメッセージが連続して出力されることを確認する:
   - `PostgreSQL (<dsn>) への接続を開始します。`
   - `PostgreSQL テーブルの初期化が完了しました。`
4. 上記により `channel_nickname_rules`, `temporary_vc_categories`, `temporary_voice_channels`, `server_colors` テーブルが自動作成される。必要があれば Supabase の SQL Editor で `SELECT` を実行して確認する。

## 手動検証・保守コマンド例
| 目的 | 実行例 |
| --- | --- |
| テーブル一覧確認 | `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';` |
| ルール件数確認 | `SELECT COUNT(*) FROM channel_nickname_rules;` |
| 一時VCレコード調査 | `SELECT guild_id, channel_id FROM temporary_voice_channels WHERE channel_id IS NULL;` |
| データバックアップ | Supabase のバックアップ/スナップショット機能を利用 |

## 運用チェックリスト
- [ ] `DATABASE_URL` が正しい Supabase Postgres DSN である。
- [ ] Bot の起動ログで `PostgreSQL ... への接続を開始します。` / `PostgreSQL テーブルの初期化が完了しました。` が出力されている。
- [ ] Supabase の SQL Editor でテーブルが作成されていることを確認する。
- [ ] `temporary_voice_channels` の `last_seen_at` が適宜 `UPDATE ... CURRENT_TIMESTAMP` で更新されていることを検証する（VoiceState イベントの受信ログ）。

## トラブルシューティング
| 症状 | 原因 | 対応 |
| --- | --- | --- |
| `asyncpg.InvalidPasswordError` | 接続情報が誤り | Supabase の接続文字列を再確認し、Variables を更新。 |
| `asyncpg.CannotConnectNowError` | DB 停止/メンテナンス | Supabase のステータスを確認し、復旧後に再起動。 |
| `asyncpg.UniqueViolationError` | 一意制約違反（同じ guild_id + channel_id など） | 重複レコードを `DELETE` → `INSERT` で修正するか、Bot を再起動して仮レコードを上書き。|

## 関連ドキュメント
- `README.md`: `.env` 設定と起動手順。
- `docs/reference/bot/master-spec/reference.md`: テーブル構造と永続化挙動。
- `docs/guide/ops/railway-setup/guide.md`: Railway から Supabase を利用する場合のセットアップ手順。
