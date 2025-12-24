---
title: "Database Connection Resiliency"
status: active
draft_status: n/a
created_at: 2025-12-02
updated_at: 2025-12-24
references: []
related_issues: []
related_prs: []
---

## Overview
- `asyncpg` の接続プールを利用して Supabase Postgres に接続するため、SQLite 特有のファイルロックは発生しない。
- スキーマは `CREATE TABLE IF NOT EXISTS` と `CURRENT_TIMESTAMP` を使って自動初期化され、再起動時の `temporary_voice_channels`・`channel_nickname_rules`・`server_colors` などの整合性を支援する。

## Symptoms
- ログ例: `asyncpg.InvalidPasswordError`（認証失敗）、`asyncpg.CannotConnectNowError`（DB 停止/メンテナンス）。
- VoiceState/コマンド処理の `fetchrow` で `asyncpg.PostgresError` が出てスキップされる。
- ネットワーク遅延や接続上限によりコマンド処理が遅延する。

## What Changed
- `Database` クラスは `asyncpg` の接続プールを生成し、クエリごとにコネクションを取得して実行する。
- 各操作は `CURRENT_TIMESTAMP` の `TIMESTAMPTZ` を使用する。
- スキーマ初期化は `CREATE TABLE IF NOT EXISTS` を順次実行し、失敗時はアプリ側で再起動する（自動リトライは行わない）。

## Operations / Tunables
- `DATABASE_URL` は Supabase の接続文字列を指定し、認証情報のローテーション時は即座に更新する。
- DB の負荷が高い場合は Supabase 側の接続上限とプール設定を見直す。
- `asyncpg.PostgresError` が頻出する場合は Supabase のステータスとネットワークを確認する。

## Rollback
- `src/app/database.py` の接続設定を Supabase から別の Postgres へ切り替える場合も、`schema` 自体は `CREATE TABLE IF NOT EXISTS` なので追加変更は不要。
