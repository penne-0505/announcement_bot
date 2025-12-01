# Documentation Guide

**必読:** ドキュメントのアーカイブ運用・承認フローに関する最新ルールは、常に `_docs/standards/documentation_operations.md` を参照して遵守してください。

## このガイドの位置づけ
- このプロジェクトでドキュメントを作成・更新する際のルールについて、よく使われる要点だけをまとめたクイックリファレンスです。`
- 迷ったときは、まず本ファイルから関連ドキュメントを辿り、必須ポリシーを確認してください。
- 詳細な執筆・レビュー手順は `_docs/standards/documentation_guidelines.md`、アーカイブ運用や承認プロセスは `_docs/standards/documentation_operations.md` を必ず確認します。

## 参照すべき中核ドキュメント
1. **`_docs/standards/documentation_operations.md`**
   - 一時ドキュメント (`draft`/`plan`/`survey`) から `intent` への移行、`_docs/archives/` へのアーカイブ手順、違反時の対処までを規定し
   ています。
   - `intent` 承認前のアーカイブ禁止など、レビュープロセスで必須となるルールが整理されています。
2. **`_docs/standards/documentation_guidelines.md`**
   - ドキュメント体系、各ディレクトリの役割、front-matter の必須項目をまとめた実務ガイドラインです。
   - 執筆時のテンプレートやレビュー観点を確認する際に参照してください。

## 利用者へのお願い
- 新しいドキュメントを追加するときは、上記 2 文書を読み、運用・レビューの前提条件に矛盾がないかを確認してください。
- `intent` 承認後にアーカイブを行う場合は、PR の説明欄で対象ドキュメントと移行先を明示し、レビュワーにも周知してください。
- ガイドラインに改善点を見つけた場合は、`_docs/draft/` で議論を開始し、合意形成後に標準ドキュメントを更新してください。

## 最終更新の扱い
- 本ファイルを更新した場合は、`_docs/standards/documentation_operations.md` と `_docs/standards/documentation_guidelines.md` の整合性を確認してください。

## Front-matter クイックリファレンス

ドキュメントを作成・更新する際に必要な front-matter フィールドを素早く確認できるよう、本セクションにまとめました。
詳細な定義や背景については、`_docs/standards/documentation_operations.md` の「Front-matter Schema」セクションを参照してください。

### 必須front-matter 一覧

全てのドキュメントで以下の6つのfront-matter フィールドが必須です。

| フィールド | 説明 |
| --- | --- |
| `title` | ドキュメントのタイトル |
| `status` | `proposed` (提案段階) \| `active` (実装段階) \| `superseded` (廃止段階) |
| `draft_status` | ドラフトの進行状態 (`idea` (機能や修正のアイデア) \| `exploring` (検討段階) \| `paused` (一時停止中) \| `n/a` (該当なし)) |
| `created_at` | 作成日 (`YYYY-MM-DD`) |
| `updated_at` | 更新日 (`YYYY-MM-DD`) |
| `references` | 関連ドキュメントへのリンク配列（ない場合は空配列 `[]`） |
| `related_issues` | 関連Issueの番号配列 (ない場合は空配列 `[]`) |
| `related_prs` | 関連PRの番号配列 (ない場合は空配列 `[]`) |


### よくある更新パターン

#### 1. draft を作成する
```yaml
title: New Feature Idea
status: proposed
draft_status: idea
created_at: 2023-11-23
updated_at: 2023-11-23
references: []
related_issues: []
related_prs: []
```

#### 2. draft で検討を進める
```yaml
# draft_status を更新
draft_status: exploring
updated_at: 2023-11-25
```
(更新部分のみ記載)

#### 3. draft から plan へ昇格
- `_docs/plan/` に移動
- `draft_status` を `n/a` に変更

```yaml
title: Feature Implementation Plan
status: proposed
draft_status: n/a
created_at: 2023-11-23
updated_at: 2023-11-30
references: []
related_issues: []
related_prs: []
```

#### 4. plan 実装完了時
```yaml
status: active
updated_at: 2023-12-10
```

#### 5. plan から intent へ移行
- `_docs/intent/` に新しいドキュメントを作成
- `references` に plan へのリンクを追加

```yaml
title: Feature Architecture Decision
status: active
draft_status: n/a
created_at: 2023-12-15
updated_at: 2023-12-15
references:
  - ../plan/feature-plan.md
related_issues: []
related_prs: []
```

#### 6. ドキュメント廃止・置き換え
```yaml
status: superseded
updated_at: 2024-01-20
related_issues: []
related_prs: []
```

### Status の遷移ルール

```
提案段階    実装段階     廃止段階
   ↓         ↓           ↓
proposed → active → superseded
   ↑                     ↑
   └─────────────────────┘
  （計画見直し時に戻る可能性あり）
```

- **proposed**: 初期状態。検討中または昇格待ち
- **active**: 正式決定済み。実装中または実装完了
- **superseded**: 新しいドキュメントに置き換わった/廃止された

### トラブルシューティング

| 状況 | 対応 |
| --- | --- |
| draft が 30 日以上更新されていない | 昇格 / 延長 / クローズを判断 |
| plan 承認前にアーカイブしてしまった | **ルール違反**。intent 承認後に改めて実行。PR で指摘されます |
| 複数の plan が同じ機能を記述している | 最新の plan をメインに、古い版は `superseded` に設定。archives へ移送 |
| guide/reference が古い情報を含んでいる | reference は `status: active` の plan/intent のみ反映。古い版との同期ズレは修正 PR で対応 |

```
