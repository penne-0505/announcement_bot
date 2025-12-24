# AGENTS.md

このファイルは、LLM/AIエージェントがリポジトリを扱う際の最小限のガイダンスです。

## 原則
- ユーザーとは**日本語**で会話する(思考は英語で行う)。
- 使用可能なツールをフル活用する。
- **徹底的にに現状実装・ドキュメントを参照、分析してから実装を行う。**
- **`git rm`や`rm`などのファイル削除は禁止**（ユーザーに提案し、実行は待つ）
- **[@_docs/standards/documentation_guidelines.md](_docs/standards/documentation_guidelines.md)と[@_docs/standards/documentation_operations.md](_docs/standards/documentation_operations.md)に従い、積極的にドキュメント運用・記述を行う**
- 日付確認には`date`コマンドを使用する。


## 開発ルール
- **Git**:  
  - コミットメッセージは英語、形式例: `feat: add analytics screen`  
  - ブランチ: `feature/`, `fix/`, `chore/`（ベースは`dev`）  
  - PRタイトルも同形式、説明に目的・影響を記載  

- **ドキュメンテーション**:
  - ドキュメントを基軸として開発・運用を行う
  - **すべての新機能・変更は関連ドキュメントを更新する**
  - draft | survey -> plan -> intent -> (guide | reference) の流れを遵守する