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
Heroku などの PaaS スリープ復帰・ネットワーク切断で PostgreSQL 接続が EOF になる事象に対し、Bot 側で接続の健全性チェックとプール再生成を入れた。これにより `SSL SYSCALL error: EOF detected` のような例外を拾って 1 回だけリトライし、壊れたコネクションを除去する。

## Symptoms
- ログ例: `psycopg pool: discarding closed connection`, `SSL SYSCALL error: EOF detected`
- イベントハンドラ初回クエリで `OperationalError` が発生し、処理がスキップされる。
- 長時間アイドル後やデプロイ直後のアクセスで再現しやすい。

## What Changed
- `Database` クラスで接続取得時に接続断を検知するとプールを再生成し、クエリを 1 回だけ再実行するリトライを追加。
- `asyncpg.create_pool` に `max_inactive_connection_lifetime=1800` と `timeout=10` を指定し、サーバのアイドルタイムアウト前にコネクションを自動リサイクル。
- プール生成・再生成はロックで直列化し、並列再接続を防止。

## Operations / Tunables
- `max_inactive_connection_lifetime`: 30 分でアイドル接続を破棄。DB 側の `idle_session_timeout` より短くするのが目安。
- リトライ回数: 内部固定 1 回。2 回目も失敗した場合は従来どおり例外を呼び出し側へ伝播させる。
- 監視: ログに `DB 接続エラーを検知しました。再試行します` が出ていないかを確認。頻発する場合はネットワーク/DB 設定を確認する。

## Rollback
- `src/app/database.py` の `_run_with_retry` / `_reset_pool` 呼び出しと `max_inactive_connection_lifetime` を元に戻すだけで挙動は従来に戻る（スキーマ変更なし）。
