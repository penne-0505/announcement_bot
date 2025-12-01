#### **1. 概要 (Overview)**

本機能は、Botが参加している各サーバー（Guild）に対し、ユニークかつ視覚的に識別可能な「テーマカラー」を自動的に割り当て、データベースに永続化するものです。この色はEmbedメッセージの装飾などに使用され、サーバーごとのアイデンティティを確立します。

#### **2. データモデル (Data Model)**

既存のデータベースに新しいテーブル `server_colors` を追加し、ギルドIDと色情報を紐付けます。

**Schema Definition:**

```sql
CREATE TABLE IF NOT EXISTS server_colors (
    guild_id BIGINT PRIMARY KEY,
    color_value INTEGER NOT NULL, -- 0xRRGGBB 形式の整数
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### **3. 色生成・検証アルゴリズム (Algorithm)**

色はランダムに生成されますが、既存の色との「重複」および「近接」を防ぐため、以下の数学的検証を行います。

  * **色空間**: RGB色空間 $(R, G, B)$ ここで $0 \le R, G, B \le 255$
  * **距離定義**: 2つの色 $C_1, C_2$ 間のユークリッド距離 $d$ を使用します。
    $$d(C_1, C_2) = \sqrt{(R_1 - R_2)^2 + (G_1 - G_2)^2 + (B_1 - B_2)^2}$$
  * **制約条件**:
      * **重複禁止**: $d \neq 0$
      * **近接禁止**: 閾値 $T$ (例: $T=40 \approx \text{総距離の10\%}$) に対し、すべての既存色 $C_{exist}$ との間で $d(C_{new}, C_{exist}) \ge T$ が成立すること。

**生成プロセス:**

1.  DBから既存の全ての色リストを取得する。
    2\.  ランダムなRGB値を生成する。
    3\.  既存リスト内の全ての色との距離を計算する。
    4\.  制約条件を満たせば採用しDBへ保存。満たさなければ再試行する（最大試行回数 $N=100$）。

#### **4. 実装コンポーネント (Architecture)**

**A. Repository Layer (`src/app/repositories/server_colors.py`)**

  * `ServerColorRepository`:
      * `get_all_colors() -> list[int]`: 衝突判定用。
      * `get_color(guild_id) -> int | None`: 個別取得用。
      * `save_color(guild_id, color_value) -> None`: 保存用。

**B. Domain Service Layer (`src/app/services/color_assignment.py`)**

  * `ColorAssignmentService`:
      * `generate_unique_color(existing_colors: list[int]) -> int`: 上記アルゴリズムの実装。
      * `assign_colors_to_new_guilds(guilds: list[discord.Guild])`: 起動時に呼ばれるメインロジック。
          * 参加ギルド一覧とDB登録済みギルドを照合。
          * 未登録ギルドに対してループ処理で色を生成・保存。

**C. Application Hook (`src/bot/client.py`)**

  * `BotClient.on_ready`:
      * 起動完了直後、`ColorAssignmentService.assign_colors_to_new_guilds(self.guilds)` を実行。

#### **5. タスクリスト (Task List)**

  * [ ] **Database**: `app/database.py` の `_ensure_schema` に `server_colors` 作成SQLを追加。
  * [ ] **Repository**: `src/app/repositories/server_colors.py` を作成し、DB操作を実装。
  * [ ] **Service**: `src/app/services/color_assignment.py` を作成し、色生成と距離計算ロジックを実装。
      * 数学的処理（平方根、二乗和）を含む。
  * [ ] **Container**: `src/app/container.py` (未提示ファイルだが推測) でServiceとRepositoryの依存解決を設定。
  * [ ] **Client**: `src/bot/client.py` の `on_ready` イベントに呼び出し処理を追加。
  * [ ] **Test**: 色の衝突回避ロジックの単体テストを作成。