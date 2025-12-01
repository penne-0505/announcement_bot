---
title: "一時VC作成ドラフト"
domain: "bot"
status: "draft"
version: "0.1.0"
created: "2025-11-14"
updated: "2025-11-14"
related_issues: []
related_prs: []
references:
  - "docs/reference/bot/master-spec/reference.md"
  - "docs/plan/bot/channel-nickname-role-sync/plan.md"
state: "exploring"
hypothesis:
  - "VC を自力で作成したい利用者の多くは、管理者の代わりに柔軟なチャンネル管理権限を一時的に求めている。"
  - "既存 PostgreSQL 永続化を流用すれば、TinyDB などの追加依存なしで所有情報を復元できる。"
options:
  - "Slash コマンド `/temporary_vc` (サブコマンド: `configure_category`, `create`, `reset`) を追加し、View なしでギルド専用操作を完結させる。"
  - "既存 `/setup` の View を流用し、ボタン押下で VC セットアップ Dialog を表示する。→ UI 一貫性は高いが、情報入力欄が増えて複雑化する。"
open_questions:
  - "1 ギルド内で複数カテゴリを使い分ける需要があるか。要件上は 1 つだが柔軟性を持たせるべきか。"
  - "VC 名に表示名を使う場合、サロゲートペアや 100 文字超のケースをどこまで許容するか。"
  - "カテゴリ切り替え時に既存 VC を即時削除するのか、参加者がいなくなるまで猶予を持たせるのか。"
next_action_by: "announcement bot maintainers"
review_due: "2025-11-28"
ttl_days: 30
---

## 背景整理
- 既存 Bot は `/setup` と `/nickname_sync_setup` を中心にテキストチャンネルの操作とニックネーム監視を提供しており、`BotClient` は `discord.Intents.all()` を有効化済み (`src/bot/client.py:16-48`)。
- `Database` / `ChannelNicknameRuleRepository` が asyncpg で永続化を担うため、追加ドメインでも PostgreSQL を使った方が実装コストが低く、デプロイも Railway のみで完結する。
- `docs/reference/bot/master-spec/reference.md` ではデータアクセスの単一窓口を `app.repositories` にまとめる前提が示されている。TinyDB 前提の要件があるが、既存意図 (`docs/intent/bot/channel-nickname-role-sync/intent.md`) でも「後続機能で必要時に導入」と記載されており、今回も Postgres で代替して整合性を保つ。

## 現状実装との対応づけ
| 要件 | 現状 | 読み替え / 影響 |
| --- | --- | --- |
| ギルドごとに一時VCカテゴリを事前設定 | カテゴリ設定機構は未実装。Slash コマンドの実装例は `/nickname_sync_setup` | `ChannelSelect` (category) やサブコマンドで `temporary_vc_categories` テーブルへ upsert する。設定がなければ作成拒否レスポンスを返す。 |
| 1 ユーザー 1 件まで | 永続化は 1 チャンネル単位の監視用のみ | `temporary_voice_channels` テーブルに `UNIQUE(guild_id, owner_user_id)` 制約を設け、DB レベルで二重作成を防止。 |
| `ユーザー名のVC` + manage_channels 付与 | ハンドラはテキスト編集/ロール付与のみ | `discord.Guild.create_voice_channel` と `discord.PermissionOverwrite`（Context7参照: Permission Overwrite 設定可）で所有者へ `manage_channels=True` を付与。名前は display_name を 32 文字程度にトリムする。 |
| TinyDB で所有情報を復元 | プロジェクトは PostgreSQL 駆動 | TinyDB の要求は「再起動後に復元できる永続層」の意図と捉え、PostgreSQL + 既存 Database を流用。`TinyDB` 導入は非互換性が高いため採用しない旨をドラフトに残す。 |
| 音声ステート監視で無人 VC 自動削除 | 現在 `on_message` のみ実装 | `BotClient.on_voice_state_update` を override。`voice_state.channel` が空 or 無人になったら `TemporaryVoiceChannelService.cleanup_if_empty()` を呼ぶ。 |
| カテゴリ設定変更時の既存 VC 破棄 | 設定概念なし | カテゴリ更新時に `temporary_voice_channels` を SELECT し、該当ギルドのチャンネルを削除 → レコード削除。結果をログで通知し、ユーザーにも ephemeral で案内する。 |

## 機能ブロック案
1. **設定フェーズ**
   - Slash コマンド `/temporary_vc category`（Manage Channels 権限要求）を追加し、View もしくは `app_commands.choices` でカテゴリを登録。
   - DB: `temporary_vc_categories(guild_id PK, category_id, updated_by, updated_at)` を追加。
   - 設定変更後は既存一時VCを `delete_channel` + レコード削除して整合性を確保。
2. **作成フェーズ**
   - `/temporary_vc create` (guild only) でユーザーが自分の VC をリクエスト。カテゴリ未設定 or 既存レコードありの場合はエラーメッセージ。
   - `TemporaryVoiceChannelService` が DB トランザクションのかわりに INSERT → channel 作成 → UPDATE (channel_id) の順で整合性を担保。途中で Discord API が失敗した場合はロールバックとしてレコード削除。
3. **監視フェーズ**
   - `BotClient.on_voice_state_update` が `before.channel` / `after.channel` を参照し、対象ギルドの管理テーブルから `channel_id` を探索。
   - `channel.members` が空なら `await channel.delete(reason="Temporary VC expired")` し、DB から紐付きを削除。
   - 再起動直後には `TemporaryVoiceChannelRepository.list_all()` → 実チャンネル存在チェック（カテゴリ内）を行い、ゴーストレコードを整理する。

## データモデル叩き台
```text
temporary_vc_categories (
    guild_id BIGINT PRIMARY KEY,
    category_id BIGINT NOT NULL,
    updated_by BIGINT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)

temporary_voice_channels (
    guild_id BIGINT NOT NULL,
    owner_user_id BIGINT NOT NULL,
    channel_id BIGINT,
    category_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (guild_id, owner_user_id)
)
```
- `channel_id` は作成完了後に更新。失敗時は `DELETE`。
- `last_seen_at` は VoiceState を受け取るたびに更新しておき、異常終了後の再起動時に stale 判定へ活用。

## VoiceState 監視・整合性
- `discord.Client` で `on_voice_state_update(member, before, after)` を override。`Intents.voice_states` は `Intents.all()` に含まれるため追加設定不要だが、Bot ポータルで Voice State Intent を有効化済みか確認するタスクを plan に含める。
- 監視の粒度:
  1. **参加時**: 所有チャンネルへ join したら `last_seen_at` を更新。別チャンネル join 時は何もしない。
  2. **退出時**: `before.channel` が所有チャンネルで `len(before.channel.members) == 0` の場合に削除。`discord.HTTPException` は WARN ログ。
- 起動直後に `TemporaryVoiceChannelRepository.sync_with_guild(guild)` を呼び、存在しない channel_id は削除扱いにする。ギルド未参加 (Bot が抜けた) のレコードもクリーンアップ。

## カテゴリ変更時のフロー
1. 管理者が `/temporary_vc category` を再設定すると、旧カテゴリに紐づく `temporary_voice_channels` を全件取得。
2. 取得した channel_id を `guild.get_channel` で取得し、存在すれば `delete()`。存在しないものはログのみ。
3. レコード削除後に `temporary_vc_categories` を更新し、カテゴリ変更通知を slash 応答で共有。
4. 併せて `TemporaryVoiceChannelRepository.purge_guild(guild_id)` を追加しておくと実装が単純になる。

## エラーハンドリングと通知方針
- 作成要求時:
  - カテゴリ未設定 → 「管理者に `/temporary_vc category` 実行を依頼してください。」
  - 既に管理対象 VC が残っている → 該当チャンネルの Jump リンクを提示してユーザーに退出＆削除待ちを促す。
  - Discord API 失敗 → エラーログ + ephemeral で「チャンネル作成に失敗しました。時間をおいて再試行してください。」。
- 自動削除時:
  - `channel.delete` 成功で INFO ログ。HTTPException は WARN とし `temporary_voice_channels` レコード削除は成功/失敗を別ログで追跡。

## 今後の計画に向けた ToDo
- Command/View 設計、Repository 実装、BotClient 変更の粒度で plan を分割し、`docs/plan/bot/temporary-voice-channels/plan.md` を後続で作成する。
- `tests/bot` へ VoiceState 監視のモックテストを追加する際の戦略（`asyncio` で `channel.members` をスタブする）が必要。
- README と guide/reference へ機能説明を追記する下準備として、Draft から requirement breakdown を plan へ昇格させる。
