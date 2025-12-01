---
title: "Per-Guild Embed Color Plan"
status: active
draft_status: n/a
created_at: 2025-12-01
updated_at: 2025-12-01
references: []
related_issues: []
related_prs: []
---

## Overview
Bot が参加している各 Guild に対して、Embed に使用するテーマカラーを一意に割り当て、データベースへ永続化する。起動時に未登録 Guild を検出して自動付与し、メッセージ装飾の視認性と識別性を高める。

## Scope
- 新規テーブル `server_colors` を追加し、Guild ごとのカラーを永続化する。
- ランダム生成した色が既存色と重複・近接しないよう検証し、ユニークなカラーを決定する。
- 起動時（`on_ready`）に未登録 Guild を走査し、必要に応じてカラーを発行・保存する。
- Embed などでカラーを取得できる Repository/API を用意する。

## Non-Goals
- 管理者が手動でカラーを指定・編集する UI / コマンド提供。
- 既存 Embed カラーの一括移行や再配色の運用（今回は新規 Guild 登録時のみ）。
- パレット制約（ブランドカラーセットなど）の導入。

## Requirements
### Functional
- `server_colors (guild_id BIGINT PRIMARY KEY, color_value INTEGER, created_at TIMESTAMPTZ)` を作成し、0xRRGGBB 整数で保存する。
- 既存 Guild 一覧を取得し、テーブル未登録の Guild にのみカラーを割り当てる。
- 生成カラーは既存色と距離 `d >= T`（想定閾値 40）を満たすまで再試行する（最大試行回数 N=100）。
- Repository 経由で特定 Guild のカラー取得、および全カラー一覧取得が可能である。
- Bot 起動時に `ColorAssignmentService.assign_colors_to_new_guilds` を実行し、処理は冪等である。

### Non-Functional
- 色生成の再試行上限に達した場合、エラーログを残しフェイルファストする。
- 生成アルゴリズムは O(n) 距離計算を許容し、Guild 数増加に備えて閾値や上限を設定可能にする。
- DB スキーマ変更は後方互換（既存テーブルへの影響なし）で、再実行しても安全である。

## Architecture
- **Repository (`src/app/repositories/server_colors.py`)**: `get_all_colors()`, `get_color(guild_id)`, `save_color(guild_id, color_value)` を提供。
- **Domain Service (`src/app/services/color_assignment.py`)**: 距離計算付きの `generate_unique_color(existing_colors)` と起動時処理 `assign_colors_to_new_guilds(guilds)` を実装。
- **Application Hook (`src/bot/client.py`)**: `on_ready` 内で Service を呼び出し、Guild 一覧を渡す。

### Color Generation
- 色空間: RGB (0–255)。
- 距離: ユークリッド距離 `sqrt((ΔR)^2 + (ΔG)^2 + (ΔB)^2)`。
- 制約: 重複禁止 (`d != 0`)、近接禁止 (`d >= T`)。

## Tasks
- [x] DB: `app/database.py` の `_ensure_schema` に `server_colors` 作成 SQL を追加。
- [x] Repository: `src/app/repositories/server_colors.py` を追加し、CRUD を実装。
- [x] Service: `src/app/services/color_assignment.py` を追加し、色生成・距離判定と未登録 Guild への割当てを実装。
- [x] Container: `src/app/container.py` で Service / Repository の依存注入を設定。
- [x] Client: `src/bot/client.py` の `on_ready` で Service を呼び出す。
- [x] Test: 距離計算と再試行ロジックの単体テスト、起動時フローの統合テストを追加。

## Test Plan
- 単体: `generate_unique_color` が重複・近接色を排除し、再試行上限で失敗を返すかを検証。
- 単体: Repository が DB へ正しく保存・取得できることを検証（スキーマ初期化含む）。
- 統合: `assign_colors_to_new_guilds` が未登録 Guild にのみ挿入し、既存登録には影響しないことを確認。
- 回帰: Bot 起動時フックが 2 回目以降でも副作用なく動くことを確認。

## Deployment / Rollout
- スキーマは `_ensure_schema` で自動適用されるため追加マイグレーション不要。
- デプロイ後の初回起動で全 Guild にカラーが割り当てられる。以降の再起動は冪等。
- ロールバック時は新テーブルを未使用に戻すだけで動作に影響しない（必要なら手動でテーブル削除を検討）。
