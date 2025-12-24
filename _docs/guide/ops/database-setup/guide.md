---
title: "SQLite セットアップガイド"
domain: "ops"
status: "active"
version: "0.2.0"
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
- `announcement_bot` は `aiosqlite` を介してローカル/ホスト上の SQLite ファイルへデータを永続化する。`Database._ensure_schema()` が起動時に `CREATE TABLE IF NOT EXISTS` を呼び出すため、マイグレーションツールは不要。
- 本ガイドでは `DATABASE_URL` に設定する SQLite パスの形式・ファイル配置・運用時のチェックポイントをまとめ、既存の `channel_nickname_rules` / `temporary_vc_categories` / `temporary_voice_channels` / `server_colors` テーブルを無事に初期化する方法を提示する。
- 開発環境とプロダクションではパスのみを切り替えればよく、`DATABASE_URL` を環境変数で切り替えることでホスト構成ごとの柔軟性を担保する。

## 役割と要件
- 推奨環境変数: `DATABASE_URL`（例: `sqlite:///./data/announcement_bot.sqlite3`、`:memory:`、`/var/lib/app/db/announcement_bot.sqlite3`）。未設定の場合は `./data/announcement_bot.sqlite3` にフォールバックする。
- `DATABASE_URL` がファイルパスの場合、Bot は起動時に親ディレクトリと SQLite ファイルを自動作成する。権限や SELinux/ファイルシステムの制限を考慮して `announcement_bot` ユーザーが書き込み可能であることを確認する。
- `aiosqlite` の接続は単一 `Connection` を再利用する設計だが、`asyncio.Lock` で直列化されているため高頻度アクセスでも整合性が保たれる。トランザクションは自動コミット方式（`connection.commit()`）であり、必要に応じてアプリ側で明示的に操作する。

## 前提準備
1. リポジトリで `poetry install` を実行し、`discord-py`, `aiosqlite`, `python-dotenv` などの依存を取得する。
2. `DATABASE_URL` で指定したパスに Bot が書き込めることを確認する（ディレクトリと SQLite ファイルは起動時に自動作成される）。`sqlite:///` 形式では先頭の `///` に続くパスが絶対パスになるため、`/var/lib/app/db` などを指定する場合は権限を事前に調整する。
3. `.env`（あるいはホストの環境変数）で `DISCORD_BOT_TOKEN` と `DATABASE_URL` を設定し、`FORCE_REGENERATE_COLORS` などのフラグは必要に応じて設定する。

## SQLite ファイル設定
- `DATABASE_URL` には `sqlite:///absolute/path/to/db.sqlite3` や `sqlite:///./relative/path.db`（起動ディレクトリ基準）を指定できる。`sqlite:///:memory:` を指定するとインメモリで起動するためテスト用途に向く。
- `DATABASE_URL` を省略した場合は `./data/announcement_bot.sqlite3` が使用される。
- 相対パスを使う場合は `.env` を置くディレクトリと Bot 起動位置を一致させる。ディレクトリやファイルは自動作成されるが、権限不足だと `aiosqlite.OperationalError: unable to open database file` になるため注意する。
- 複数インスタンスを動かす場合は `DATABASE_URL` をインスタンスごとに分け、ファイルを共有しない設計とする（SQLite は複数書き込みに制約がある）。

## アプリによる初期化フロー
1. `.env` またはホストの環境で `DATABASE_URL` を読み込む。
2. `poetry run announcement-bot` などでアプリを起動し、`Database.connect()` が `aiosqlite.connect()` を呼ぶ。
3. ログに以下のメッセージが連続して出力されることを確認する:
   - `SQLite (<path>) への接続を開始します。`
   - `SQLite テーブルの初期化が完了しました。`
4. 上記により `channel_nickname_rules`, `temporary_vc_categories`, `temporary_voice_channels`, `server_colors` テーブルが自動作成される。必要があれば `sqlite3 $DATABASE_URL` で `SELECT name FROM sqlite_schema` を実行して確認する。

## 手動検証・保守コマンド例
| 目的 | コマンド |
| --- | --- |
| テーブル一覧確認 | `sqlite3 "$DATABASE_URL" ".tables"` |
| ルール件数確認 | `sqlite3 "$DATABASE_URL" "SELECT COUNT(*) FROM channel_nickname_rules;"` |
| 一時VCレコード調査 | `sqlite3 "$DATABASE_URL" "SELECT guild_id, channel_id FROM temporary_voice_channels WHERE channel_id IS NULL;"` |
| ファイルの整合性チェック | `file "$DATABASE_URL"` / `ls -l "$DATABASE_URL"`（パーミッション・サイズの確認） |

### ファイルのバックアップ/復元
- `sqlite3 "$DATABASE_URL" ".backup /tmp/announcement_bot_backup.sqlite3"` でホットバックアップ。復元は `sqlite3 /tmp/backup ".restore $DATABASE_URL"`。
- `:memory:` モードを使っている場合はバックアップできないため、暫定的に `sqlite3` でダンプを取得しておく。

## 運用チェックリスト
- [ ] `DATABASE_URL` が正しいパスを指しており、ファイルが存在・書き込み可能である。
- [ ] Bot の起動ログで `SQLite ... への接続を開始します。` / `SQLite テーブルの初期化が完了しました。` が出力されている。
- [ ] テーブル数・カラム（`sqlite3 "$DATABASE_URL" "PRAGMA table_info(channel_nickname_rules);"` など）を定期的に確認し、データ構造変更が反映されているか監査する。
- [ ] `temporary_voice_channels` の `last_seen_at` が適宜 `UPDATE ... CURRENT_TIMESTAMP` で更新されていることを検証する（VoiceState イベントの受信ログ）。
- [ ] ファイルのサイズが急激に増えていないか、`du -h` などで観察する（ログや一時データが残らないよう定期クリアを考慮）。

## トラブルシューティング
| 症状 | 原因 | 対応 |
| --- | --- | --- |
| `aiosqlite.OperationalError: unable to open database file` | 権限不足/パス不正 | `DATABASE_URL` のパスを確認し、ディレクトリのオーナーとパーミッション (`chmod 755` など) を設定。 |
| `aiosqlite.DatabaseError: database disk image is malformed` | DB ファイルが破損 | バックアップから復元するか、空ファイルに差し替え。復元後も従来のレコードが必要な場合は `sqlite3` で `SELECT` して確認する。 |
| `sqlite3.IntegrityError: UNIQUE constraint failed` | 一意制約違反（同じ guild_id + channel_id など） | 重複レコードを `DELETE` → `INSERT` で修正するか、Bot を再起動して仮レコードを上書き。|

## 関連ドキュメント
- `README.md`: `.env` 設定と起動手順。
- `docs/reference/bot/master-spec/reference.md`: テーブル構造と永続化挙動。
- `docs/guide/ops/railway-setup/guide.md`: 旧 Railway/PostgreSQL ガイド（現在は SQLite に移行中で、必要に応じて内容をご参照ください）。
