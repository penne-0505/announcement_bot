---
title: "一時ボイスチャンネル運用ガイド"
domain: "bot"
status: "active"
version: "0.1.0"
created: "2025-11-14"
updated: "2025-12-25"
related_intents:
  - "docs/intent/bot/temporary-voice-channels/intent.md"
references:
  - "docs/reference/bot/temporary-voice-channels/reference.md"
---

## 概要
- `/temporary_vc` Slash コマンドは、参加者が自分専用のボイスチャンネルをオンデマンドで確保するための仕組みです。
- 管理者がカテゴリを 1 つ登録すると、一般メンバーは `/temporary_vc create` で VC を生成し、退出して無人になれば自動的に削除されます。
- 本ガイドではカテゴリ設定からユーザー操作、トラブル対応までをまとめます。

## 事前準備
1. Bot に **Manage Channels**, **Connect**, **View Channel**, **Move Members**, **Mute Members** を含むロール権限を与え、対象カテゴリにも同等の権限を付与します。
2. `DISCORD_BOT_TOKEN` と Supabase 用の `SUPABASE_URL` / `SUPABASE_KEY` を `.env` に記述し、`pyproject.toml` に揃った依存関係（`discord.py`, `supabase`, `python-dotenv` など）を `poetry install` で準備します。
3. Discord 開発者ポータルで Voice State Intent を有効化しておきます。Bot クライアントでは `discord.Intents.all()` を利用しているため、Portal 側で無効化されていると VoiceState イベントを受信できません。

## カテゴリ設定 (`/temporary_vc category`)
1. Manage Channels 権限を持つメンバーがギルド内で `/temporary_vc category` を実行します。
2. Slash コマンドのパラメータでカテゴリを 1 つ指定します。コマンド送信後、Bot が直近の一時VCを全削除し、新カテゴリで再作成できる状態に更新します。
3. 応答には「削除済み件数 / 不存在件数」が表示されるため、不要なチャンネルが残っていないか確認してください。
4. カテゴリを変更した場合は、運用中のメンバーへ事前告知しておくと混乱を防げます。

## ユーザー操作 (`/temporary_vc create`, `/temporary_vc reset`)
1. 任意のメンバーが `/temporary_vc create` を実行すると、Bot が `display_name` を元にした VC をカテゴリ配下に作成します。所有者には `manage_channels=True` の権限上書きが付与されるため、参加人数に応じた名前変更や移動が可能です。
2. 既に管理対象 VC が残っている場合は `<#channel>` へのジャンプリンク付きで通知され、二重作成はできません。
3. `/temporary_vc reset` を使うと、自分の一時VCを即座に削除できます。自動削除を待たずに片付けたい場合に利用してください。

## 自動削除の仕組み
- `BotClient.on_voice_state_update` がメンバーの入退室を検知し、対象 VC の `channel.members` が空になったタイミングで `TemporaryVoiceChannelService` が削除します。
- Bot 再起動時には DB 上のレコードとギルド内チャンネルを突き合わせ、孤立レコードを削除して整合性を保ちます。

## トラブルシューティング
| 症状 | 対応 |
| --- | --- |
| `/temporary_vc create` でカテゴリ未設定エラー | `/temporary_vc category` を再実行してカテゴリを登録する。カテゴリ自体が削除されていないかも確認する。 |
| VC 作成に失敗した (❌ メッセージ) | Bot にカテゴリ作成/削除権限があるか、Discord API 障害が発生していないかを確認。再試行しても失敗する場合はログを参照する。 |
| 退出後も VC が残る | Voice State Intent が無効化されていないか、Bot が当該ギルドから追放されていないか確認。`/temporary_vc reset` で手動削除も可能。 |

## 運用ヒント
- VC 名の先頭にステータスを付けたい場合は、所有者自身が Manage Channels 権限でリネームしてください。
- 大規模イベント前にカテゴリ設定を一度リセットしておくと、古いレコードや残存チャンネルの掃除が容易です。
- 監視ログは INFO/WARN/ERROR レベルで出力されるため、ホスト先のログストリームをダッシュボード化すると異常検知が素早く行えます。
