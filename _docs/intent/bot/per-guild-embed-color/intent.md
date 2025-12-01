---
title: "Per-Guild Embed Color Intent"
domain: "bot"
status: "active"
version: "0.1.0"
created: "2025-12-01"
updated: "2025-12-01"
related_plan: "docs/plan/bot/per_guild_embed_color.md"
owners:
  - "announcement bot maintainers"
references:
  - "docs/plan/bot/per_guild_embed_color.md"
---

## 背景
- Bridge メッセージの Embed カラーが毎回ランダムに変わると、ギルド間の視認性が下がり、メッセージ元ギルドの判別が難しかった。
- plan `docs/plan/bot/per_guild_embed_color.md` で合意した要件に沿って、Guild ごとに安定したテーマカラーを自動採番・永続化する仕組みを導入する。

## 決定事項
1. **新テーブル `server_colors` を Database 初期化で自動作成**し、`guild_id` を主キーに `color_value` を 0xRRGGBB 整数で保存する。再実行に備えて `CREATE TABLE IF NOT EXISTS` で後方互換を維持する。
2. **Repository (`ServerColorRepository`) を新設**し、全件取得・単一取得・保存を提供する。保存は `ON CONFLICT (guild_id)` で上書き可能にし、冪等性を確保する。
3. **Domain Service (`ColorAssignmentService`) を追加**し、RGB ユークリッド距離が閾値（デフォルト 40）以上離れる色を再試行しながら生成する。最大 100 回試行で見つからない場合は `ColorGenerationError` を投げてログに残す。
4. **Bot 起動フックで自動割当**: `BotClient.on_ready` から `assign_colors_to_new_guilds(self.guilds)` を呼び、未登録 Guild のみを対象にカラーを永続化する。既存登録には手を触れず、副作用なく繰り返し実行できる。
5. **DI/起動構成を更新**: `app.container` で Repository と Service を組み立て、`BotClient` に依存注入する。テストは `python -m pytest` で 26 ケースを通過することを確認済み。

## トレードオフ
- 距離計算は O(n) の全探索で実装した。Guild 数増大時は閾値・上限を設定で調整する想定で、空間分割アルゴリズムは導入していない。
- カラーは完全ランダム生成とし、ブランドパレットや管理者指定 UI は提供しない。シンプルさと自動運用を優先した。
- 生成失敗時はフェイルファストして起動を中断させる方針。起動遅延よりも配色重複を避ける一貫性を重視した。

## 影響範囲
- コード: `src/app/database.py`, `src/app/repositories/server_colors.py`, `src/app/services/color_assignment.py`, `src/app/container.py`, `src/bot/client.py`, 追加テスト (`tests/app/*`).
- DB: 新テーブル `server_colors` を追加。既存テーブルには影響なし。
- 起動フロー: `on_ready` にカラー割り当て処理が加わり、初回起動で全 Guild にカラーが付与される。

## テスト / 観測
- `python -m pytest` で 26 ケースが成功（新規テスト含む）。色生成の再試行・上限超過・未登録ギルドのみへの保存がカバーされている。
- 生成失敗時は ERROR ログを出力し例外を送出。Railway ログで起動時に検知可能。

## フォローアップ
1. Embed 作成箇所で `ServerColorRepository.get_color` を利用し、橋渡しメッセージにギルド固有カラーを適用する。
2. カラーを管理者が確認・再割当できるスラッシュコマンドの需要調査（必要なら別 plan を起案）。
3. Guild 数が増えた場合の距離閾値・再試行上限の見直しと、より高速なサンプリングアルゴリズムの検討。
