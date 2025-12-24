---
title: "ニックネーム自動同期チャンネル計画"
domain: "bot"
status: "draft"
version: "0.2.0"
created: "2025-11-12"
updated: "2025-12-24"
related_issues: []
related_prs: []
references:
  - "docs/guide/bot/channel-nickname-role-sync/guide.md"
  - "docs/reference/bot/channel-nickname-role-sync/reference.md"
scope:
  - "Slash コマンド実行後に View(UI) を介してチャンネルとロールを選択し、ニックネーム同期対象として登録できるようにする"
  - "登録情報を Supabase Postgres へ永続化し、`DATABASE_URL` を切り替えてローカル/本番を共通化する"
  - "対象チャンネルで投稿されたメッセージを検知し、投稿者のニックネームでメッセージ本文を上書きする"
  - "同時に指定ロールを投稿者へ自動付与する"
non_goals:
  - "複数ロール同時付与やテンプレート編集などの高度な自動化"
  - "ギルド横断の一括設定 UI や Web 管理画面"
  - "Postgres 以外のストレージを新たに導入しない"
requirements:
  - "`CURRENT_TIMESTAMP` を含む構文が必要で、起動時に自動でテーブルが初期化される"
  - "Slash コマンドはギルド内でのみ実行可能で、結果は ephemeral メッセージで通知される"
  - "チャンネル監視時は Bot が自分の編集でループしないよう配慮する"
constraints:
  - "`DATABASE_URL` で指定した Supabase Postgres を利用する。明示的なマイグレーションツールは導入しない"
  - "discord.py 2.6 系の API に沿って Message Intent を有効化しておく必要がある"
api_changes:
  - "Slash コマンド `/setup` に加えて、設定用の `/nickname_sync_setup` を追加し、View でチャンネル/ロールを取得する"
data_models:
  - "`channel_nickname_rules` テーブル (guild_id, channel_id, role_id, updated_by, updated_at)"
migrations:
  - "アプリ起動時に `CREATE TABLE IF NOT EXISTS` を実行してスキーマを用意する"
rollout_plan:
  - "ローカルで Supabase 接続を指定してテーブル作成を確認後、本番でも同じ `DATABASE_URL` 形式で起動"
  - "本番ギルドで `/nickname_sync_setup` を実行し、View から設定 → メッセージ編集・ロール付与を検証"
rollback:
  - "Bot を停止し、`channel_nickname_rules` を空にすれば既存 `/setup` のみの状態へ戻る"
  - "コード面では該当モジュールを revert すれば既存 `/setup` のみの状態へ戻せる"
test_plan:
  - "Slash コマンド登録と View 付与を確認するユニットテスト (モック interaction)"
  - "メッセージ編集・ロール付与ロジックのユニットテスト (スタブ message/member)"
  - "DB リポジトリは最小限の統合テストではなく、接続失敗時のログ確認に留める"
observability:
  - "設定登録・メッセージ編集失敗・ロール付与失敗を INFO/ERROR ログへ出力する"
security_privacy:
  - "環境変数に含まれる `DATABASE_URL` は `.env` のみで管理しログに出力しない"
  - "DB にはチャンネル ID/ロール ID/更新者 ID のみ保存し、個人情報に該当する内容は含めない"
performance_budget:
  - "対象チャンネル投稿時のみ 1 件の SELECT を実行。監視対象が少ないため許容"
i18n_a11y:
  - "コマンド説明・エラーメッセージは日本語で統一し、ロール・チャンネル Mention を利用して視認性を確保"
acceptance_criteria:
  - "`/nickname_sync_setup` → View からチャンネル/ロールを選択して登録すると成功メッセージが戻る"
  - "対象チャンネルに投稿するとメッセージが投稿者ニックネームに上書きされる"
  - "投稿者に指定ロールが自動付与される (既に付与済みならスキップ)"
owners:
  - "announcement bot maintainers"
---

## 背景
- Clover 内でアナウンス前に本人確認を行うフローとして、特定チャンネルにニックネームを打刻→ロール付与する手運用が存在する。
- 手操作だとメッセージ整形やロール付与ミスが発生するため、自動化して誤りと作業コストを削減したい。

## 目的
1. Slash コマンドで対象チャンネル/ロールを設定し、運用担当者が GUI から安全に切り替えられるようにする。
2. Bot が対象チャンネルの投稿をフックし、投稿者ニックネーム → メッセージ本文反映＋ロール付与までを自動化する。
3. 設定は Supabase Postgres へ保存し、`DATABASE_URL` を切り替えるだけでローカル/他ホスト問わず永続化されるようにする。

## アーキテクチャ概要
| 層 | 役割 |
| --- | --- |
| `app.config` | `DATABASE_URL` を含む設定値を読み込む |
| `app.database` | `asyncpg` 接続を管理し、起動時にテーブルを自動作成 |
| `app.repositories.channel_rules` | `channel_nickname_rules` テーブルへの Upsert/Select を提供 |
| `bot.client` | `BotClient` がリポジトリを保持し、`on_message` で設定参照 |
| `bot.commands` | `/nickname_sync_setup` コマンドを登録し、ギルド限定で View を返す |
| `bot.handlers` (新設) | メッセージ編集とロール付与ロジックを切り出し、テストを容易にする |

## 実装ステップ
1. `pyproject` へ `asyncpg` を追加し、`.env.example` / README に `DATABASE_URL` を追記する。
2. `app.config` に Database 設定を追加し、`app.database` でプール初期化＋テーブル作成を行う。
3. `app.repositories.channel_rules` を新設し、`upsert_rule`・`get_rule_for_channel` を実装する。
4. `BotClient` にリポジトリとメッセージハンドラを紐付け、`register_commands` へ新 Slash コマンドを追加する。
5. `/nickname_sync_setup` の View (ChannelSelect / RoleSelect + ボタン) を実装し、ギルド限定で動作させる。
6. メッセージ監視ロジックをユニットテストし、Slash コマンドのモックテストを追加する。
7. README / docs (intent, guide, reference) を更新し、Rollout/検証手順を追記する。

## リスクと対応策
| リスク | 影響 | 対応 |
| --- | --- | --- |
| DB 接続失敗で Bot 起動不可 | Slash コマンド含め全停止 | 接続エラー時は `LOGGER.exception` を出力・プロセスを再起動し、`Postgres` 接続ログを監視する |
| 自動編集ループ | Bot の編集が再検知 → API ループ | Bot 投稿は `message.author.bot` で即 return し、編集前後が同じ場合は edit をスキップ |
| 権限不足でロール付与失敗 | 運用想定を満たせない | Forbidden/HTTPException をログ出力し、運用ガイドで Bot ロール位置要件を明記 |
| Slash コマンド乱用 | 意図しないチャンネルが上書きされる | 役職 `Manage Roles` 権限者のみ実行可能にし、結果を必ず ephemeral で通知 |
