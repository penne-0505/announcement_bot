---
title: "Rename /setup to /osi"
status: "active"
draft_status: "n/a"
created_at: "2025-12-25"
updated_at: "2025-12-25"
references:
  - "_docs/reference/bot/master-spec/reference.md"
  - "_docs/reference/bot/messaging-modal-port/reference.md"
  - "_docs/guide/bot/messaging-modal-port/guide.md"
  - "_docs/guide/ops/railway-setup/guide.md"
related_issues: []
related_prs: []
---

## Background
- `/setup` は用途に対して一般的すぎるため、運用時の意図が伝わりづらかった。

## Decision
- Slash コマンド名を `/setup` から `/osi` へ改名する。
- コマンド説明は「指定したチャンネルにメッセージを送信します。」に統一する。
- ドキュメントとテストを `/osi` に合わせて更新する。

## Impact
- 既存の `/setup` は利用できなくなるため、運用手順は `/osi` へ切り替える必要がある。
- デプロイ後の `tree.sync()` により、Discord 側の Slash コマンド一覧が更新される。

## Rollout
- デプロイ後に `/osi` が利用できることを確認し、既存手順を順次差し替える。
