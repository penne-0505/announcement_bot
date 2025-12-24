---
title: "一時VC作成計画"
domain: "bot"
status: "active"
version: "0.1.0"
created: "2025-11-14"
updated: "2025-11-14"
related_issues: []
related_prs: []
references:
  - "docs/draft/bot/temporary-voice-channels/draft.md"
  - "docs/reference/bot/master-spec/reference.md"
scope:
  - "ギルド管理者が Slash コマンドから一時VC用カテゴリを登録・更新できるようにし、未設定状態では作成リクエストを拒否する。"
  - "一般ユーザーが `/temporary_vc create` で 1 人 1 件の VC を作成でき、チャンネル名と権限上書きを自動付与する。"
  - "VoiceState 更新を監視して無人になったチャンネルを自動削除し、SQLite ファイル上の所有情報を同期する。"
  - "カテゴリ設定変更時に既存一時VCを破棄し、整合性の取れた状態で再作成に備える。"
non_goals:
  - "複数カテゴリや階層的なテンプレート管理。"
  - "Web ダッシュボード/外部 UI での設定編集。"
  - "複数ユーザー共同所有や権限カスタム UI。"
  - "TinyDB など別ストレージの導入（SQLite ファイルの `Database` をそのまま利用する）。"
requirements:
  functional:
    - "カテゴリ未設定時や削除済みの場合はエラーメッセージを返し、VC 作成を実行しない。"
    - "`/temporary_vc create` 実行者は既存管理対象 VC がある場合に Jump リンク付きで通知される。"
    - "作成される VC 名は `display_name` 由来（最大32文字、禁止文字は丸め）とし、所有者には `manage_channels` 権限を付与する。"
    - "Bot は起動時に DB と実チャンネルの差分を検出し、孤立レコードを削除する。"
    - "カテゴリ更新時は該当ギルドの一時VCを全削除＋レコードレベルでクリアする。"
  non_functional:
    - "DB 書き込みの整合性とエラーハンドリング（API 失敗時のロールバック）。"
  - "SQLite ファイルと Discord API のみで完結し、追加インフラを不要にする。"
    - "ログで主要イベント（作成・削除・失敗）を INFO/WARN で追跡できる。"
constraints:
  - "既存 `aiosqlite` ベースの `Database` を拡張し、外部 ORM/TinyDB は採用しない。"
  - "Slash コマンドは discord.py 2.6 系で提供される `app_commands` を利用する。"
  - "Bot には Voice State Intent を必須とし、Guild ごとの CategorySelect は Discord 標準コンポーネントに限定する。"
api_changes:
  - "Slash コマンド `/temporary_vc` を追加し、`category`（管理者向け設定）と `create`（一般ユーザー向け）サブコマンドを実装する。"
  - "必要に応じて `/temporary_vc reset` を追加し、ユーザーが自分の一時VCを手動破棄できるようにする。"
data_models:
  - "`temporary_vc_categories(guild_id PK, category_id, updated_by, updated_at)`"
  - "`temporary_voice_channels(guild_id, owner_user_id, channel_id, category_id, created_at, last_seen_at, PRIMARY KEY(guild_id, owner_user_id))`"
migrations:
  - "`Database._ensure_schema` に上記2テーブルの `CREATE TABLE IF NOT EXISTS` を追加。`temporary_voice_channels.channel_id` には `NULL` を許容し、作成完了後に `UPDATE` で反映する。"
rollout_plan:
  - "Phase 1: ローカル/開発ギルドでカテゴリ設定→VC作成→削除シーケンスを検証。"
  - "Phase 2: ステージング環境（ローカル/任意ホスト）で複数ユーザー同時操作を試験し、DB 一意制約エラーを観察。"
  - "Phase 3: 本番ギルドへデプロイし、監視ログで自動削除が問題なく動くか 1 週間モニタ。"
rollback:
  - "Bot を停止し、`temporary_voice_channels` と `temporary_vc_categories` を TRUNCATE して既存機能のみへ戻す。"
  - "Slash コマンド登録を削除し、`BotClient` の VoiceState ハンドラを revert すれば従来挙動へ戻る。"
test_plan:
  - "Repository の upsert/select/cleanup ユニットテスト。"
  - "VoiceState ハンドラのモックテスト（channel.members が空になったケース）。"
  - "Slash コマンド対話テスト（カテゴリ未設定、二重作成、正常作成）を pytest + discord モックで実施。"
observability:
  - "INFO: VC 作成成功/削除成功/カテゴリ更新。"
  - "WARN: Discord API 失敗、カテゴリ未設定、孤立チャンネル検出。"
  - "ERROR: DB 書き込み失敗や VoiceState イベント処理例外。"
security_privacy:
  - "DB 保存値は guild/channel/user IDs のみで、個人情報テキストを含めない。"
  - "Slash コマンド権限判定（Manage Channels）と View interaction_check で不正操作を防ぐ。"
performance_budget:
  - "VC 作成/削除はユーザーアクション単位で1回。VoiceState イベントは対象チャンネルのみを参照し、O(1) クエリに抑える。"
i18n_a11y:
  - "Slash コマンド説明・エラーメッセージは日本語で統一し、チャンネル/ロール mention を活用。"
acceptance_criteria:
  - "カテゴリ設定後、ユーザーが `/temporary_vc create` を実行すると指定カテゴリ直下に VC が作成され、所有者に `manage_channels` 権限が付与される。"
  - "所有一時VCが残っているユーザーは追加作成を拒否され、既存チャンネルのリンクが通知される。"
  - "対象VCが無人になると自動的にチャンネルが削除され、DB レコードもクリアされる。"
  - "カテゴリを変更すると旧カテゴリ配下の一時VCが全削除され、新カテゴリでの作成準備が整う。"
owners:
  - "announcement bot maintainers"
---

## 背景
- Clover サーバーではイベント時に少人数で会話できる一時的な VC のニーズがあり、現在は管理者が手動でカテゴリ作成と権限設定を行っている。
- 既存 Bot はテキストチャンネル操作とニックネーム同期機能のみを提供しており、VoiceState イベントは未活用。
- 要件に TinyDB が挙げられているが、プロジェクトは既に SQLite を前提に `Database`/`ChannelNicknameRuleRepository` を整備している。再起動後の整合性目的を満たすため、同じ技術基盤で一時VC情報も管理する。

## 目的
1. 管理者がギルドごとに一時VCカテゴリを明示的に設定し、未設定状態を防止する。
2. ユーザーが自分専用の VC をオンデマンドで作成できるようにし、Bot が権限上書きを自動化する。
3. VoiceState 監視により無人 VC を確実に削除し、DB と Discord 実体の不整合を解消する。
4. 設定変更や Bot 再起動時にゴミチャンネルが残らないよう、整合性チェックとクリーンアップ手段を提供する。

## アーキテクチャ概要
| コンポーネント | 役割 |
| --- | --- |
| `TemporaryVoiceCategoryRepository` | `temporary_vc_categories` の CRUD。カテゴリ未設定時のバリデーションに使用。 |
| `TemporaryVoiceChannelRepository` | ユーザー所有 VC を永続化し、作成→削除フローや起動時同期を担う。 |
| `TemporaryVoiceChannelService` | Slash コマンド・VoiceState ハンドラから呼び出されるドメインロジック（権限設定、名前生成、整合性処理）。 |
| `bot.commands` | `/temporary_vc category|create|reset` を登録し、ephemeral レスポンスで結果を通知。 |
| `bot.client.BotClient` | `on_voice_state_update` を override し、対象 VC の空判定と削除を実行。 |
| `app.database.Database` | スキーマ初期化に一時VCテーブルを追加し、既存 `aiosqlite` 接続を共有。 |

## Slash コマンド設計
- `/temporary_vc category`
  - **権限**: Manage Channels。
  - **挙動**: CategorySelect (または ID 入力) でカテゴリを選択し、`temporary_vc_categories` に upsert。旧カテゴリと紐づく VC を `TemporaryVoiceChannelService.purge_guild` で削除。
- `/temporary_vc create`
  - **権限**: デフォルト（誰でも可）。ギルド限定。
  - **挙動**: カテゴリ設定を参照し、既存レコードが無ければ `guild.create_voice_channel` を実行。`PermissionOverwrite` で所有者に `manage_channels=True` を付与。
  - **バリデーション**: 既存所有 VC がある場合は Jump リンク付きメッセージで案内。
- `/temporary_vc reset`（任意）
  - **挙動**: 所有者自ら VC を破棄する操作。自動削除待ちが長い場合の逃げ道。

## データフロー & 永続化
1. カテゴリ設定時に `temporary_vc_categories` を upsert。設定が存在しない状態で VC 作成を試みると即エラー。
2. `/temporary_vc create`:
   - `temporary_voice_channels` へ INSERT（`channel_id=NULL`）し、UNIQUE 制約で多重作成を防止。
   - Discord API で VC 作成→成功時に `channel_id` を UPDATE。失敗時はレコードを削除。
3. VoiceState 監視:
   - `before.channel` が管理対象でメンバー 0 になると `channel.delete`。成功後レコード削除。
   - `after.channel` が管理対象の新規 (owner 以外) 場合は `last_seen_at` を更新して活動ログに活用。
4. 起動時:
   - 参加中ギルド一覧 × `temporary_voice_channels` を突合し、欠損チャンネルや所属ギルド外レコードを削除。

## 実装ステップ
1. `app/repositories/temporary_voice.py`（仮）にカテゴリ/チャンネル用リポジトリを追加し、DB スキーマを拡張。
2. `TemporaryVoiceChannelService` を実装し、カテゴリ取得→作成→削除→同期 API を提供。
3. `bot/commands.py` に `/temporary_vc` サブコマンド群を追加。カテゴリ設定は View (CategorySelect) で UX を揃える。
4. `bot/client.py` に `on_voice_state_update` を追加し、Service を呼び出して自動削除を実装。
5. 起動時タスク（`BotClient.setup_hook` など）で `TemporaryVoiceChannelService.sync_all_guilds()` を実行。
6. README / guide / reference を更新し、利用方法と制限を追記。
7. pytest に Repository / Service / Command / VoiceState のテストを追加し、CI を通す。

## リスクと対応策
| リスク | 影響 | 対応 |
| --- | --- | --- |
| Discord API 失敗で DB と実チャンネルが不整合になる | チャンネルが残り続ける | 作成フェーズで try/except → 失敗時レコード削除。VoiceState 起動時同期で最終的に回復。 |
| カテゴリ削除後に作成コマンドが成功しない | ユーザー体験悪化 | `/temporary_vc create` 実行前にカテゴリ存在/権限をチェックし、具体的な再設定手順を案内。 |
| VoiceState Intent 無効化 | 自動削除が動作しない | デプロイ手順に Portal 設定確認を追加し、ログで Intent 不足を WARN。 |
| 1 ユーザー 1 件制限がバイパスされる（DB レース） | 重複VCが発生 | UNIQUE 制約 + エラーハンドリングで再試行時にも一意性を強制。 |

## 依存・前提
- discord.py 2.6.x, aiosqlite >=0.20.0, Python 3.12。
- Bot ロールが対象カテゴリへチャンネル作成・削除できる権限を保持していること。
- Intents: `Intents.voice_states` が True、Portal 側でも有効化済み。

## 今後の拡張余地
- 参加人数やステータスに応じた自動名前変更。
- VC 作成数や滞在時間をメトリクス化し、運用レポートを生成。
- 共同所有者設定や複数カテゴリ運用の検討（別 draft で扱う）。
