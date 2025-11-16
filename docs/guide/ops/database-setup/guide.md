---
title: "PostgreSQL セットアップガイド"
domain: "ops"
status: "active"
version: "0.1.0"
created: "2025-11-15"
updated: "2025-11-15"
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
- `announcement_bot` は PostgreSQL を単一の永続ストアとして利用し、ニックネーム同期設定と一時ボイスチャンネル情報を保持します。
- 本ガイドは Railway デプロイを前提に、PostgreSQL の作成・接続・初期化・運用までを手順化します。ローカル開発／ステージング環境も同じ `DATABASE_URL` 形式で統一します。
- テーブルスキーマはアプリ起動時に `src/app/database.py` の `Database._ensure_schema()` が `CREATE TABLE IF NOT EXISTS` で自動適用するため、追加のマイグレーションツールは不要です。

## 役割と要件
- 必須環境変数: `DATABASE_URL`（例: `postgresql://user:pass@host:5432/dbname`）。未設定時は起動前に `ValueError` を送出し Bot が停止します。
- 使用テーブル:
  - `channel_nickname_rules (guild_id, channel_id, role_id, updated_by, updated_at)`
  - `temporary_vc_categories (guild_id, category_id, updated_by, updated_at)`
  - `temporary_voice_channels (guild_id, owner_user_id, channel_id, category_id, created_at, last_seen_at)`
- 推奨バージョン: PostgreSQL 16 系（Railway のマネージドサービス既定値）。
- 1 プロジェクト 1 DB を基本とし、複数 Bot で共有しないこと。Slash コマンド設定と結び付いたデータを壊さないよう、DDL/DML は `app.repositories` 経由を原則とします。

## 前提準備
1. Railway アカウントでプロジェクトを作成済みであること（`railway init`/`railway link` 参照）。
2. ローカル開発環境では `poetry install` 済みで、`.env` に `DATABASE_URL` を記述できること。
3. PostgreSQL クライアント (`psql`) または Railway CLI の `railway connect` が利用できること。

## Railway での PostgreSQL 構築
1. **サービス作成**  
   - ダッシュボード: 「New」→「Database」→「PostgreSQL」。プロジェクト直下に `postgresql-<hash>` サービスが作成されます。
   - CLI: `railway add --plugin postgresql` でも同様に作成可能。
2. **接続文字列の取得**  
   ```bash
   railway variables --service postgresql
   ```
   - `DATABASE_URL` が自動で出力されます。形式は `postgresql://USER:PASSWORD@HOST:PORT/railway`。
3. **Bot サービスへの共有**  
   - ダッシュボード > Variables > Shared Variables で `DATABASE_URL` を Bot サービスに共有、または CLI で `railway variables --service announcement-bot set DATABASE_URL="$RAILWAY_DATABASE_URL"`。
4. **権限/ネットワーク**  
   - Railway 内のサービス間通信はデフォルトで許可済み。追加の VPC 設定は不要です。
5. **バックアップ**  
   - Pro プラン以上では自動バックアップが有効。Free プランの場合は手動で `railway download --service postgresql` を実行し、ダンプを取得してください。

## ローカル開発用 PostgreSQL
### Docker を利用する場合
```bash
docker run -d \
  --name clover-postgres \
  -e POSTGRES_USER=clover \
  -e POSTGRES_PASSWORD=secretpass \
  -e POSTGRES_DB=announcement_bot \
  -p 5432:5432 \
  postgres:16
```
- `.env` の `DATABASE_URL` を `postgresql://clover:secretpass@localhost:5432/announcement_bot` に設定。
- 停止/削除は `docker stop clover-postgres` → `docker rm clover-postgres`。データを永続化したい場合は `-v clover-pg:/var/lib/postgresql/data` を追加。

### Railway DB を開発でも共用する場合
1. `railway connect --service postgresql` でトンネルを作成。
2. 出力されるローカルポート（例: `5433`）を使って `DATABASE_URL=postgresql://USER:PASSWORD@127.0.0.1:5433/railway` を `.env` に記述。
3. 作業終了後は `Ctrl+C` でトンネルを閉じ、不要な書き込みがないかを確認。

## アプリによる初期化フロー
1. `.env` または Railway Variables に `DATABASE_URL` を設定。
2. `poetry run announcement-bot`（または Railway デプロイ）を実行。
3. ログに以下が並んで出力されることを確認。
   - `PostgreSQL への接続を開始します。`
   - `PostgreSQL との接続とテーブル初期化が完了しました。`
4. これにより上記 3 テーブルが自動作成されるため、手動で DDL を発行する必要はありません。

## 手動検証・保守コマンド例
| 目的 | コマンド |
| --- | --- |
| テーブル一覧確認 | `psql "$DATABASE_URL" -c "\dt"` |
| ルール件数確認 | `psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM channel_nickname_rules;"` |
| 一時VC孤児レコードの調査 | `psql "$DATABASE_URL" -c "SELECT * FROM temporary_voice_channels WHERE channel_id IS NULL;"` |
| ローカル→Railway へのデータコピー | `pg_dump "$LOCAL_URL" | psql "$RAILWAY_URL"` |

- 直接 `DELETE/UPDATE` を行う場合は必ず事前に `pg_dump` でバックアップを取得し、GitHub Issue/PR で操作ログを共有してください。

## 運用チェックリスト
- [ ] Railway Variables に `DATABASE_URL` が存在し、Bot サービスに共有されている。
- [ ] `channel_nickname_rules` の主キー `(guild_id, channel_id)` がユニークであることを `\d channel_nickname_rules` で確認。
- [ ] Bot 再起動後、`temporary_voice_channels` の `last_seen_at` が更新される（VoiceState イベントが届いている）ことを定期的に確認。
- [ ] 障害発生時は Railway ログで `asyncpg` 例外を確認し、DB 側のメンテナンス状況と突き合わせる。

## トラブルシューティング
| 症状 | 原因 | 対応 |
| --- | --- | --- |
| `ValueError: DATABASE_URL is not set` | 環境変数未設定 | `.env` / Railway Variables を設定し再起動。 |
| `asyncpg.exceptions.InvalidPasswordError` | ユーザー/パスが不一致 | Railway サービスのパスワードを再発行し、`DATABASE_URL` を更新。 |
| `connection attempt failed` | ネットワーク遮断 / DB 停止 | Railway ステータスを確認し、必要に応じて DB サービスを再起動。 |
| `duplicate key value violates unique constraint` | 同一ギルド+チャンネルで多重登録 | `channel_nickname_rules` を確認し、古い行を `DELETE`。再登録時は `/nickname_sync_setup` を使う。 |

## 関連ドキュメント
- `README.md`: `.env` 設定と起動手順。
- `docs/reference/bot/master-spec/reference.md`: データモデルの詳細とエラーハンドリング。
- `docs/guide/ops/railway-setup/guide.md`: Railway サービス全体のセットアップ。DB ガイドと合わせて参照してください。
