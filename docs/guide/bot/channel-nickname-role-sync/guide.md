---
title: "ニックネーム同期チャンネル運用ガイド"
domain: "bot"
status: "active"
version: "0.1.0"
created: "2025-11-12"
updated: "2025-11-12"
related_intents:
  - "docs/intent/bot/channel-nickname-role-sync/intent.md"
references:
  - "docs/reference/bot/channel-nickname-role-sync/reference.md"
---

## 概要
- `/nickname_guard` Slash コマンドで監視チャンネルとロールを登録すると、そのチャンネル内の投稿が自動で「投稿者ニックネームのみ」に書き換わり、指定ロールが付与される。
- 参加確認や名簿作成のハンドオフを Bot へ委譲し、作業漏れを防ぐ仕組み。

## 事前準備
1. Bot ロールに **Manage Roles** と **Send Messages / Manage Messages** 権限を付与する。ロール階層は付与対象ロールより上に配置する。
2. PostgreSQL の `DATABASE_URL` を `.env` に設定し、`poetry run announcement-bot` で起動する。初回起動時に `channel_nickname_rules` テーブルが自動作成される。
3. 監視対象ギルドで Bot が Text チャンネル閲覧・投稿できることを確認する。

## `/nickname_guard` の使い方
1. Discord で `/nickname_guard` を選択。以下 2 つの引数を入力する。
   - **channel**: ニックネーム打刻用の Text チャンネル。
   - **role**: 付与したいロール (例: `Verified`).
2. コマンドを実行すると、設定内容とサマリが ephemeral メッセージで返る。
3. 同じチャンネルに対してコマンドを再実行すると、ロール設定が上書きされる。

## 動作
1. 監視対象チャンネルでメンバーがメッセージを送信。
2. Bot が `message.author.display_name` を取得し、メッセージ本文が異なる場合に `message.edit` で上書きする。
3. `guild.get_role(role_id)` からロールを取得し、未付与の場合のみ `member.add_roles` を実行する。
4. いずれかの処理に失敗した場合は INFO/WARN ログが出力される。必要に応じて Bot 権限を確認する。

## 運用ヒント
- フローの冒頭に `/setup` モーダルで案内文を送信し、案内先チャンネルを `/nickname_guard` で紐付けるとスムーズ。
- 誤設定を防ぐため、ギルド管理者以上に `/nickname_guard` の実行権限を限定する。
- ロールを一時的に停止したい場合は `/nickname_guard` で別チャンネルに切り替えるか、DB の該当レコードを削除する。

## トラブルシューティング
| 症状 | 対処 |
| --- | --- |
| メッセージが編集されない | Bot に Manage Messages 権限があるか + チャンネルが正しく登録されているかを確認 |
| ロール付与に失敗 (ログに Forbidden) | Bot ロールの階層を付与対象より上に移動し、Manage Roles 権限を付与 |
| Slash コマンドが表示されない | `tree.sync()` 失敗の可能性があるため、Bot再起動ログを確認 |
