---
title: "Railway + Supabase セットアップガイド"
domain: "ops"
status: "active"
version: "0.2.0"
created: "2025-11-15"
updated: "2025-12-26"
related_intents:
  - "docs/intent/bot/messaging-modal-port/intent.md"
  - "docs/intent/bot/channel-nickname-role-sync/intent.md"
  - "docs/intent/bot/temporary-voice-channels/intent.md"
references:
  - "README.md"
  - "docs/reference/bot/master-spec/reference.md"
  - "docs/guide/ops/database-setup/guide.md"
---

> **Note:** Railway で Bot を動かし、DB は Supabase Postgres を利用する前提の手順です。

## 概要
- 本ガイドは `announcement_bot` を Railway にデプロイすることを前提に、リポジトリのクローンから Slash コマンドが利用可能になるまでのセットアップ手順を網羅します。
- `/osi`・`/nickname_sync_setup`・`/temporary_vc` すべてを同一プロセスで運用する構成を想定しています。
- インフラ構成は Railway 上の Python 12.x サービス + Supabase Postgres を利用し、テーブルは Supabase の SQL Editor で事前作成します。

## 前提条件
### アカウント / 権限
- Discord Developer Portal で Bot を作成し、**MESSAGE CONTENT**・**SERVER MEMBERS**・**PRESENCE**・**VOICE STATE** Intents をすべて有効化する。
- Bot を配信する Discord サーバーに参加させ、Send Messages / Manage Messages / Manage Roles / Manage Channels 権限を付与する。
- Railway アカウント（Pro 以上推奨）を用意し、Bot 用の Web サービスを作成できるロールを持つ。

### ローカルツール
- Git / OpenSSL など標準 CLI。
- Python 3.12 系（`pyenv` や `asdf` などでインストール済みであること）。
- Poetry 1.8 系（例: `pipx install "poetry==1.8.3"`）。
- Railway CLI（`curl -sSL https://railway.app/install.sh | sh` で導入し、`railway login` 済み）。
- Discord Bot トークン (`DISCORD_BOT_TOKEN`) と Supabase の接続情報（後段で `SUPABASE_URL` / `SUPABASE_KEY` に設定）。

## リポジトリクローン〜ローカル検証
1. **クローン**
   ```bash
   git clone git@github.com:rin-products/clover_announcement_bot.git
   cd clover_announcement_bot
   ```
2. **依存関係の解決**  
   ```bash
   poetry install --no-root
   ```
3. **環境変数テンプレートを複製**  
   ```bash
   cp .env.example .env
   ```
   - `DISCORD_BOT_TOKEN=` に Bot トークン、`SUPABASE_URL=` と `SUPABASE_KEY=` に Supabase の値を設定。
4. **テーブル作成の確認**  
   - Supabase の SQL Editor で `channel_nickname_rules` / `temporary_vc_categories` / `temporary_voice_channels` が作成済みであることを確認。
5. **テスト実行（任意だが推奨）**
   ```bash
   PYTHONPATH=src poetry run pytest
   ```

## Railway プロジェクトの準備
1. **プロジェクト作成**  
   ```bash
   railway init
   ```
   - 既存プロジェクトに接続する場合は `railway link` を利用。
2. **Supabase プロジェクト作成**  
   - Supabase の Project Settings → API から `SUPABASE_URL` / `SUPABASE_KEY` を取得する。
3. **Railway サービス構成**  
   - `Services` に「Bot 本体」を追加し、ビルドパックは Railway の Python（Nixpacks）を利用する。

## 環境変数とビルド設定
Railway ダッシュボードまたは CLI (`railway variables set KEY=value`) で以下を設定します。

| 変数 | 値の例 / 説明 |
| --- | --- |
| `DISCORD_BOT_TOKEN` | Discord Developer Portal で発行した Bot トークン。rotate 時は即座に更新。 |
| `SUPABASE_URL` | Supabase プロジェクト URL。 |
| `SUPABASE_KEY` | Supabase API Key（サーバー用途は Service Role Key を推奨）。 |
| `PYTHON_VERSION` | `3.12` を明示してビルド環境を固定。 |
| `POETRY_VERSION` | `1.8.3` など。Nixpacks が Poetry をインストールする際のバージョン指定。 |
| `LOG_LEVEL` | `INFO` / `WARNING` / `ERROR` など。Bot のログレベルを上書きする場合に設定。 |
| `PORT` | Discord Bot は HTTP サーバーを開かないため未使用だが、Railway で必須の場合はデフォルトのままで問題なし。 |

**Start Command**: `poetry run announcement-bot`  
Railway の Service → Settings → Deploy → Start Command で上記を設定すると、Poetry のスクリプトエントリ（`app.runtime:main`）が実行されます。

## デプロイ手順
1. **初回デプロイ**  
   ```bash
   railway up
   ```
   - CLI が現在のディレクトリをビルド & アップロードし、Nixpacks が `poetry install` → `Start Command` 実行まで自動化します。
   - GitHub 連携で自動デプロイする場合は、Railway ダッシュボードで `Connect Repository` を有効化し、`dev` ブランチに Push → Build → Deploy の流れを構築します。
2. **ログ確認**  
   ```bash
   railway logs --service announcement-bot
   ```
   - `Discord クライアントの初期化が完了し、コマンドを登録しました。` ログが出たら Slash コマンド同期が完了しています。
3. **Discord 上での動作確認**  
- `/osi` を実行し、モーダルが開けば Slash コマンドが同期済み。
   - `/temporary_vc category set` → `/temporary_vc create` を実行してボイスチャンネルが生成されることを確認。
   - ニックネーム同期を使う場合は `/nickname_sync_setup` で監視チャンネルとロールを登録し、該当チャンネルに投稿して display_name への書き換えとロール付与が行われるかを確認。

## 運用・監視 Tips
- **Bot 停止時の再起動**: Railway の `Auto Restart` を有効にしておくと例外終了時に自動で再起動されます。DB 側でメンテナンスが走った場合も自動復旧できます。
- **Slash コマンド更新**: コマンド定義を変更した際は再デプロイ後に `discord.app_commands.CommandTree.sync()` が実行されるため、最大で数分待つだけで反映されます。
- **ログレベル**: `LOG_LEVEL` を設定しない場合は `INFO`。必要に応じて `LOG_LEVEL=WARNING` などで絞り込み可能です。
- **ログフォーマット**: `YYYY-MM-DD HH:MM:SS LEVEL [logger] message` 形式で出力されるため、時系列と責務が追いやすくなります。

## トラブルシューティング
| 症状 | 想定原因 | 対処 |
| --- | --- | --- |
| Bot がすぐ終了し、ログに `Discord bot token is not set` | `DISCORD_BOT_TOKEN` 未設定 | Railway の Variables を確認し、設定後に再デプロイ。 |
| `Database is not initialized` が出る | `SUPABASE_URL` / `SUPABASE_KEY` が無効 | Supabase の接続情報を再取得して更新。 |
| Slash コマンドが表示されない | Intents・権限不足、`tree.sync()` 未完了 | Discord Developer Portal で Intents を再確認し、Bot を再招待 or チャンネル権限を見直す。 |
| `/temporary_vc` で Forbidden エラー | Bot ロールが Manage Channels を持たない or ロール階層が低い | 管理者権限または十分なロール階層を付与する。 |

## 参考
- `README.md`: ローカルセットアップと基本コマンド。
- `docs/reference/bot/master-spec/reference.md`: 必須環境変数・データモデル・意図の詳細。Railway の運用上の注意点も記載されています。
