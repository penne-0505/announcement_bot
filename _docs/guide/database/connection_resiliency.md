---
title: "Database Connection Resiliency"
status: active
draft_status: n/a
created_at: 2025-12-02
updated_at: 2025-12-25
references: []
related_issues: []
related_prs: []
---

## Overview

- Supabase Python SDK の PostgREST API 経由で接続するため、SQLite 特有のファイルロックは発生しない。
- スキーマは Supabase 側で事前に作成し、アプリ側は CRUD のみ実行する。

## Symptoms

- ログ例: PostgREST の認証エラー / 5xx エラー。
- VoiceState/コマンド処理の `execute` で Supabase エラーが出てスキップされる。
- ネットワーク遅延や接続上限によりコマンド処理が遅延する。

## What Changed

- `Database` クラスは Supabase SDK の async client を生成し、PostgREST リクエストを実行する。
- 各操作は Supabase 側で `TIMESTAMPTZ` を保持し、更新時はアプリ側で `updated_at` / `last_seen_at` を補完する。
- スキーマ初期化は行わず、失敗時はアプリ側で再起動する（自動リトライは行わない）。

## Operations / Tunables

- `SUPABASE_URL` / `SUPABASE_KEY` を指定し、認証情報のローテーション時は即座に更新する。
- DB の負荷が高い場合は Supabase のレート制限と API ステータスを確認する。
- Supabase エラーが頻出する場合は Supabase のステータスとネットワークを確認する。

## Rollback

- `src/app/database.py` の接続設定を Supabase から別の PostgREST 互換 API へ切り替える場合は、同じテーブルスキーマが必要になる。
