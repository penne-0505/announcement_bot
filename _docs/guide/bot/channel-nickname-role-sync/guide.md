---
title: "ニックネーム同期チャンネル運用ガイド"
domain: "bot"
status: "active"
version: "0.1.0"
created: "2025-11-12"
updated: "2025-11-23"
related_intents:
  - "docs/intent/bot/channel-nickname-role-sync/intent.md"
references:
  - "docs/reference/bot/channel-nickname-role-sync/reference.md"
---

## 概要
- `/nickname_sync_setup` Slash コマンドで監視チャンネルとロールを登録すると、そのチャンネル内の投稿内容をメンバーのニックネームに設定し（32文字まで）、指定ロールを付与する。
- 参加確認や名簿作成のハンドオフを Bot へ委譲し、作業漏れを防ぐ仕組み。

## 事前準備
1. Bot ロールに **Manage Roles** と **Send Messages / Manage Messages** 権限を付与する。ロール階層は付与対象ロールより上に配置する。
2. SQLite ファイルパス（例: `sqlite:///./data/announcement_bot.sqlite3`）を `.env` の `DATABASE_URL` に設定し、`poetry install` で依存 (`discord-py`, `aiosqlite`, `python-dotenv` など) を整える。`poetry run announcement-bot` を最初に起動すると `channel_nickname_rules` テーブルが自動作成される。
3. 監視対象ギルドで Bot が Text チャンネル閲覧・投稿できることを確認する。

## `/nickname_sync_setup` の使い方
1. Discord で `/nickname_sync_setup` を実行すると、ephemeral メッセージに View が表示される。
2. View の **チャンネル選択** で監視対象チャンネルを 1 つ選ぶ。
3. **ロール選択** で付与したいロールを 1 つ選び、必要なら再選択で上書きする。
4. 「設定を保存」ボタンを押すと、選択内容が PostgreSQL に保存され、結果が ephemeral メッセージで返る。
5. 同じチャンネルで再度保存するとロール設定が上書きされる。

## 動作
1. 監視対象チャンネルでメンバーがメッセージを送信。
2. Bot がメッセージ本文を取得し、投稿者のニックネームをその内容に変更する（空文字・32文字超過はスキップ）。
3. `guild.get_role(role_id)` からロールを取得し、未付与の場合のみ `member.add_roles` を実行する。
4. いずれかの処理に失敗した場合は INFO/WARN ログが出力される。必要に応じて Bot 権限を確認する。

## 運用ヒント
- フローの冒頭に `/setup` モーダルで案内文を送信し、案内先チャンネルを `/nickname_sync_setup` で紐付けるとスムーズ。
- 誤設定を防ぐため、ギルド管理者以上に `/nickname_sync_setup` の実行権限を限定する。
- ロールを一時的に停止したい場合は `/nickname_sync_setup` で別チャンネルに切り替えるか、DB の該当レコードを削除する。

## トラブルシューティング
| 症状 | 対処 |
| --- | --- |
| ニックネームが変わらない | 投稿内容が32文字以内か確認し、Botより上位権限のユーザー（サーバー所有者等）でないかをチェック |
| メッセージが編集されない | Bot に Manage Messages 権限があるか + チャンネルが正しく登録されているかを確認 |
| ロール付与に失敗 (ログに Forbidden) | Bot ロールの階層を付与対象より上に移動し、Manage Roles 権限を付与 |
| Slash コマンドが表示されない | `tree.sync()` 失敗の可能性があるため、Bot再起動ログを確認 |
