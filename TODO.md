# Project Task Management Rules

## 0. System Metadata

- **Current Max ID**: `Next ID No: 1` (※タスク追加時にインクリメント必須)
- **ID Source of Truth**: このファイルの `Next ID No` 行が、全プロジェクトにおける唯一の ID 発番元である。

## 1. Task Lifecycle (State Machine)

タスクは以下の順序で単方向に遷移する。逆行は原則禁止とする。

### Phase 0: Inbox (Human Write-only)

- **Location**: `# Inbox (Unsorted)` セクション
- **Description**: 人間がアイデアや依頼を書き殴る場所。フォーマット不問。ID 未付与。
- **Exit Condition**: LLM が内容を解析し、ID を付与して `Backlog` へ構造化移動する。

### Phase 1: Backlog (Structured)

- **Location**: `# Backlog` セクション
- **Status**: タスクとして認識済みだが、着手準備未完了。
- **Entry Criteria**:
  - ID が一意に採番されている。
  - 必須フィールド（Title, ID, Priority, Size, Area, Description）が埋まっている。
- **Exit Condition**: `Ready` の要件を満たす。

### Phase 2: Ready (Actionable)

- **Location**: `# Ready` セクション
- **Status**: いつでも着手可能な状態。
- **Entry Criteria**:
  - **Plan Requirement**:
    - `Size: M` 以上 (M, L, XL): `Plan` フィールドに有効な `_docs/plan/...` へのリンクが**必須**。
    - `Size: S` 以下 (XS, S): `Plan` は **None** でよい。
  - **Dependencies**: 解決済み（または明確化済み）である。
  - **Steps**: 具体的な実行手順（または Plan へのポインタ）が記述されている。
- **Exit Condition**: 作業者がタスクに着手する。

### Phase 3: In Progress

- **Location**: `# In Progress` セクション
- **Status**: 現在実行中。
- **Entry Criteria**: 作業者がアサインされている（または自律的に着手）。

### Phase 4: Done

- **Location**: なし（行削除）
- **Exit Action**: `Goal` 達成を確認後、リストから物理削除する。

## 2. Schema & Validation

各タスクは以下の厳格なスキーマに従うこと。

| Field            | Type       | Constraint / Value Set                                                    |
| :--------------- | :--------- | :------------------------------------------------------------------------ |
| **Title**        | `String`   | `[Category] Title` 形式。Category は後述の Enum 参照。                    |
| **ID**           | `String`   | `{Area}-{Category}-{Number}` 形式。不変の一意キー。                       |
| **Priority**     | `Enum`     | `P0` (Critical), `P1` (High), `P2` (Medium), `P3` (Low)                   |
| **Size**         | `Enum`     | `XS` (<0.5d), `S` (1d), `M` (2-3d), `L` (1w), `XL` (>2w)                  |
| **Area**         | `Enum`     | `_docs/plan/` 直下のディレクトリ名と一致する値。                          |
| **Dependencies** | `List<ID>` | 依存タスク ID の配列 `[Core-Feat-1, UI-Bug-2]`。なしは `[]`。             |
| **Goal**         | `String`   | 完了条件（Definition of Done）。                                          |
| **Steps**        | `Markdown` | 進行管理用のチェックリスト（詳細は後述）。                                |
| **Description**  | `String`   | タスクの詳細。                                                            |
| **Plan**         | `Path`     | `Size >= M` の場合必須。`_docs/plan/` へのパス。`Size < M` は `None` 可。 |

## 3. Field Usage Guidelines

### Area & Directory Mapping

- **Rule**: `Area` フィールドの値は、`_docs/plan/` 直下に実在するディレクトリ名（ドメイン）と一致させること。
- **New Area**: 新しい領域のタスクを作成する場合、まず `_docs/plan/` にディレクトリを作成してから、その名前を `Area` に指定する。
- **Example**: `Area: Core` -> implies existence of `_docs/plan/Core/`

### Steps vs Plan

タスクの規模に応じて `Steps` の記述方針を切り替えること。情報の二重管理を避ける。

- **Case A: Plan あり (Size >= M)**

  - `Steps` は **「Plan を実行するための進行管理チェックリスト」** として機能する。
  - 詳細な仕様やコードは Plan に記述し、Steps には複製しない。
  - 例: `1. [ ] Planの "DB Schema" セクションに従いマイグレーション作成`

- **Case B: Plan なし (Size < M)**
  - `Steps` に **「具体的な作業手順」** を直接記述する。
  - 例: `1. [ ] src/utils/format.ts の dateFormat 関数を修正`

## 4. Defined Enums

### Categories (Title & ID)

ID 生成およびタイトルのプレフィックスには以下のみを使用する。

- `Feat` (New Feature)
- `Enhance` (Improvement)
- `Bug` (Fix)
- `Refactor` (Code Structuring)
- `Perf` (Performance)
- `Doc` (Documentation)
- `Test` (Testing)
- `Chore` (Maintenance/Misc)

### Areas (Examples)

**※実際には `_docs/plan/` のディレクトリ構成に従う。**

- `Core`: 基盤ロジック
- `UI`: プレゼンテーション層
- `Docs`: ドキュメント整備自体
- `General`: 特定ドメインに属さない雑多なタスク
- `DevOps`: CI/CD, 環境構築

## 5. Operational Workflows (for LLM)

### [Action] Create Task from Inbox

1. `Next ID No` を読み取り、割り当て予定の ID を決定する。
2. `Next ID No` をインクリメントしてファイルを更新する。
3. Inbox の内容を解析し、最適な `Area` と `Category` を決定する。
4. ID を生成する（例: `Core-Feat-24`）。
5. タスクをフォーマットし、`Backlog` の末尾に追加する。
6. 元の Inbox 行を削除する。

### [Action] Promote to Ready

1. **Size check**:
   - `Size >= M` ならば、`Plan` フィールドが有効なリンクであることを検証する。リンク切れや未作成の場合は移動を拒否する。
   - `Size < M` ならば、`Plan` が `None` でも許容する。
2. **Steps check**: `Steps` が具体的か（あるいは Plan へのポインタとして機能しているか）確認する。
3. **Dependency check**: 依存タスクが完了済みか確認する。
4. 全てクリアした場合のみ `Ready` セクションへ移動する。

## 6. Task Definition Examples (Few-Shot)

以下の例を参考に、サイズ（Size）に応じた記述ルール（Plan の有無、Steps の粒度）を厳守すること。

### Case A: Feature Implementation (Size >= M)

**Rule**: `Plan` へのリンクが必須。`Steps` は Plan の参照ポインタとして記述する。

```markdown
- **Title**: [Feat] User Authentication Flow
- **ID**: Core-Feat-25
- **Priority**: P0
- **Size**: M
- **Area**: Core
- **Dependencies**: []
- **Goal**: ユーザーが Email/Password でサインアップおよびログインできる状態にする。
- **Steps**:
  1. [ ] Plan の "Schema Design" セクションに基づき、User テーブルのマイグレーションを作成・適用
  2. [ ] Plan の "API Specification" に従い、`/auth/login` エンドポイントを実装
  3. [ ] Plan の "Security" に記載された JWT 発行ロジックを実装
  4. [ ] E2E テストを実施し、ログインフローの疎通を確認
- **Description**: 新規サービスの基盤となる認証機能を実装する。
- **Plan**: `_docs/plan/Core/auth-feature.md`
```

### Case B: Small Fix / Maintenance (Size \< M)

**Rule**: `Plan` は `None` でよい。`Steps` に具体的なコード修正手順を記述する。

```markdown
- **Title**: [Bug] Fix typo in Submit button
- **ID**: UI-Bug-26
- **Priority**: P2
- **Size**: XS
- **Area**: UI
- **Dependencies**: []
- **Goal**: ログイン画面のボタンのラベルが "Subimt" から "Submit" に修正されている。
- **Steps**:
  1. [ ] `src/components/LoginForm.tsx` を開く
  2. [ ] Submit ボタンのラベル文字列を修正する
  3. [ ] ブラウザで表示を確認し、レイアウト崩れがないか確認
- **Description**: ユーザーから報告された誤字の修正。
- **Plan**: None
```

### Case C: New Area / Doc Task (Size S)

**Rule**: 新しい Area が必要な場合、ディレクトリ作成を含む。

```markdown
- **Title**: [Doc] Add Deployment Guide
- **ID**: DevOps-Doc-27
- **Priority**: P1
- **Size**: S
- **Area**: DevOps
- **Dependencies**: [Core-Feat-25]
- **Goal**: 新メンバー向けのデプロイ手順書が `_docs/guide/deployment.md` に作成されている。
- **Steps**:
  1. [ ] `_docs/plan/DevOps/` ディレクトリが存在しないため作成する (Area 定義用)
  2. [ ] `_docs/guide/deployment.md` を作成し、ステージング環境へのデプロイ手順を記述
- **Description**: オンボーディングコスト削減のため、暗黙知になっているデプロイ手順をドキュメント化する。
- **Plan**: None
```

---

## Inbox

---

## Backlog

---

## Ready

---

## In Progress
