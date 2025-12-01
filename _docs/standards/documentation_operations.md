# ドキュメント運用標準

## 目的
- `_docs/draft/` と `_docs/plan/` を中心に、ドキュメント種別ごとの役割と運用境界を明確化する。
- 昇格・更新・廃止フローとレビュープロセスを標準化し、全メンバーが同じ基準で扱えるようにする。
- Front-matter と Markdown テンプレートを連携させ、ドキュメント品質と可観測性を高める。
- 一時ドキュメント（`draft`/`plan`/`survey`）から `intent`、そして `_docs/archives/` への移行条件を厳格に定義し、棚卸しや監査を容易にする。

## 適用範囲
- 対象: `_docs/draft/`, `_docs/plan/`, `_docs/survey/`, およびそれらと連携する `intent/`, `guide/`, `reference/`, `archives/`。
- 適用範囲: ドキュメント作成・レビュー・承認・保守・自動化。
- 非対象: アプリケーションコードや API の実装規約（別 standards を参照）。

## ディレクトリの役割
| パス | 目的 | 主な利用者 | 備考 |
| --- | --- | --- | --- |
| `_docs/draft/` | アイデア、検討メモ、仮説、代替案等の一時保管 | 設計者・実装者・調査担当 | `updated_at` 基準で stale 管理。決定事項はここに残さない。 |
| `_docs/plan/` | 合意済み仕様・実施計画の単一参照点 | 施策オーナー・レビュア・実装担当 | `plan/<domain>/<slug>/plan.md` を基本。 |
| `_docs/intent/` | 設計判断・意思決定ログ | TL・設計レビュア | plan 更新時の根拠を格納。 |
| `_docs/survey/` | 調査・検証レポート | 調査担当・意思決定者 | plan/intent から根拠として参照。 |
| `_docs/guide/` / `_docs/reference/` | 実装済み機能の運用ガイド・リファレンス | 全メンバー | plan の結果を反映。議論や検討は含めない。 |
| `_docs/archives/` | intent 承認済みドキュメントの保管庫 | 監査担当・レビュア | intent 承認直後に移送。front-matter を保持したまま履歴保存。 |

## ライフサイクルと昇格ルール
1. **基本フロー**: `draft/survey → (survey) → plan → intent → (guide/reference) → archives`
2. **draft 運用**
   - 進行状況は Front-matter の `draft_status` で管理。
   - 意思決定前の仮説や代替案は `## Hypothesis`, `## Options` セクションに記述。
   - `updated_at` から一定期間（既定30日）更新がない場合、archiveに移管するレビューの対象となる。
3. **plan 運用**
   - 合意済み仕様のみ。抽象的な検討や議論は `intent/` へ移す。
   - 破壊的変更や方針転換時は `updated_at` を更新し、必要に応じて `status` を `proposed` に戻す。
   - 非推奨になった計画は `status: superseded` とし、後継 plan を本文内で明記。
4. **昇格ゲート (draft → plan)**
   - `## Scope` / `## Non-Goals` が網羅的に記載されている。
   - 影響範囲（API, データ, 移行, セキュリティ, パフォーマンス, i18n/a11y）が洗い出されている。
   - `## Test Plan`の方針が定義済み。
   - リスク分析と `## Rollback` 戦略が用意されている。
   - 関連 Issue / PR が front-matter で紐付いている。(存在する場合)

## 一時ドキュメントのアーカイブルール
- `draft`、`plan`、`survey` は「開発過程専用の一時ドキュメント」であり、正式な `intent` に昇格していない状態でのアーカイブを禁止する。
- 一時ドキュメントの移行フロー:
  1. 一時ドキュメントを `intent` テンプレートへ再構成し、レビュワーから承認を得る。
  2. `intent` がマージまたは承認された直後に、該当一時ドキュメントのアーカイブ移送を行う。
  3. アーカイブ移送時は、元ディレクトリから原本を取り除き、`_docs/archives/` へ同じ front-matter を保持したまま移す。
- 違反例:
  - `intent` 未承認のまま `_docs/archives/` へ移動する。
  - アーカイブ後も元ディレクトリに原本を残す。
  - PR 説明やレビューコメントで移行内容を報告しない。
- レビュー時は、`intent` の承認状況、アーカイブ作業の報告、移動後ディレクトリのクリーンアップを必ず確認する。

## アーカイブ実行チェックリスト
1. `intent` が承認済みであることを確認し、PR 説明欄にリンクを明記する。
2. アーカイブ対象ドキュメントの front-matter を保持したまま `_docs/archives/` へ移す。
3. 移行元ディレクトリのクリーンアップを差分で確認し、残骸がないことをレビュワーに示す。
4. アーカイブ対象と関連する `intent` を `references` フィールドに追記し、相互リンクを更新する。
5. 必要に応じて `CHANGELOG.md` や関連 Issue へ作業ログを残す。

## 必須front-matter（全ドキュメント共通）
全てのドキュメントは以下の6つのの必須 front-matter フィールドを持つ。

| フィールド | 説明 |
| --- | --- |
| `title` | 文書タイトル（英語推奨） |
| `status` | `proposed` \| `active` \| `superseded` |
| `draft_status` | `idea` \| `exploring` \| `paused` \| `n/a` |
| `created_at` | `YYYY-MM-DD` |
| `updated_at` | `YYYY-MM-DD` |
| `references` | 関連リンク配列（`[]` 許容） |
| `related_issues` | 関連Issueの番号配列 (ない場合は空配列 `[]`) |
| `related_prs` | 関連PRの番号配列 (ない場合は空配列 `[]`) |

## ドキュメント構造とテンプレート

Front-matterを簡素化する代わりに、ドキュメント種別ごとに推奨されるMarkdownの見出し構造（テンプレート）を定義する。
執筆者は以下の構造に従って本文を記述することで、必要な情報の網羅性を担保する。

### 共通セクション（全ドキュメント推奨）

注: **担当者名（Owners）の記述は不要。**

### Plan ドキュメントの構造例

計画書には、以前Front-matterで管理していたスコープや要件定義を本文として記述する。

```markdown
## Overview
概要を記述。

## Scope
- 実装する機能範囲
- 変更の影響範囲

## Non-Goals
- 今回のスコープに含まれないもの

## Requirements
- **Functional**: 機能要件
- **Non-Functional**: 非機能要件

## Tasks
- 実装タスク一覧

## Test Plan
- テスト戦略、観点

## Deployment / Rollout
- デプロイ手順、ロールバック方針
```

### Draft ドキュメントの構造例

```markdown
## Hypothesis
- 検証したい仮説

## Options / Alternatives
- 検討中の選択肢
- トレードオフの比較
```

**ただし、draft はあくまでメモ置き場であるため、必須セクションは特に定めない。plan ドキュメント昇格直前など、趣旨が一致する場合のみセクション名を踏襲すること。**

## コンプライアンス
- ドキュメントに秘密情報・個人情報を含めない。環境値は `.env.example` を参照。
- CI ログ出力にはマスク設定を適用し、機密情報が残らないようにする。
- 公開資料として扱える品質を前提に、OSS 化を想定した文言に統一する。
- intent 承認後のみアーカイブできるルールを遵守し、違反が確認された PR はレビュワーがブロックする。

---
