---
title: "Database Connection Resiliency"
status: active
draft_status: n/a
created_at: 2025-12-02
updated_at: 2025-12-02
references: []
related_issues: []
related_prs: []
---

## Overview
- `aiosqlite` 接続はシングル `Connection` を再利用するため、IO 操作が一部ブロッキングするケースがある。`Database` は `asyncio.Lock` で操作を直列化し、`sqlite3.OperationalError`（`database is locked` など）を適切に捕捉することで、データ整合性を保ちながら `SQLite` ファイルへのアクセスを継続する。
- スキーマは `CREATE TABLE IF NOT EXISTS` で `CURRENT_TIMESTAMP` デフォルトを使って自動初期化され、再起動時の `temporary_voice_channels`・`channel_nickname_rules`・`server_colors` などがある程度の整合性を保つことを支援する。

## Symptoms
- ログ例: `aiosqlite.OperationalError: unable to open database file`（パスエラー）、`aiosqlite.OperationalError: database is locked`（並列アクセス）。
- VoiceState/コマンド処理の `fetchrow` で `aiosqlite.DatabaseError` が出てスキップされる。
- SQLite ファイルへの書き込み権限がない、または別プロセスで排他ロックされた状態が長く続くと、処理が遅延してバックログが発生する。

## What Changed
- `Database` クラスはシングル接続を `aiosqlite.connect()` で生成し、`_operation_lock` を介して fetch/execute を直列化する。
- 各操作は `await connection.commit()` を伴い、`CURRENT_TIMESTAMP` を使って列を更新することで `PostgreSQL` の `TIMESTAMPTZ` の代替とする。
- スキーマ初期化は `executescript` で一括実行し、`sqlite3` ファイルのロックエラーが出た場合はアプリ側で再起動することでリカバリする（自動リトライは行わない）。

## Operations / Tunables
- `DATABASE_URL` に指定するファイルパスの権限チェック（書き込み可・ディレクトリ存在）をデプロイ前チェックリストに追加する。
- `:memory:` モードを使う場合は永続性がないため、ステージング/テスト用途に限定。戻す場合はファイルパスを指定して安定化する。
- `aiosqlite.OperationalError` が頻出する場合は、ホストのファイルシステムロック状況や、複数プロセスで同じファイルを共有していないかを確認する。

## Rollback
- `src/app/database.py` を以前の `asyncpg` プール実装に戻せば PostgreSQL 方式に戻る。`schema` 自体は `CREATE TABLE IF NOT EXISTS` なので追加変更は不要。
