from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from app.repositories import ChannelNicknameRuleStore
from views import NicknameSyncSetupView, SendModalView

if TYPE_CHECKING:
    from bot.client import BotClient

LOGGER = logging.getLogger(__name__)


async def register_commands(client: "BotClient", *, rule_store: ChannelNicknameRuleStore) -> None:
    """クライアントのアプリケーションコマンドを登録する。"""

    tree = client.tree

    @tree.command(name="setup", description="メッセージ送信のセットアップを行います。")
    async def command_setup(
        interaction: discord.Interaction,
    ) -> None:  # pragma: no cover - Discord 実行時にテスト
        LOGGER.info("/setup コマンドを実行したユーザー: %s", interaction.user)
        await interaction.response.defer(ephemeral=True)
        view = SendModalView()
        await interaction.followup.send(
            "📨 下のボタンからメッセージ送信モーダルを開けます。",
            view=view,
            ephemeral=True,
        )

    @tree.command(
        name="nickname_sync_setup",
        description="ニックネーム同期チャンネルの設定ビューを表示します。",
    )
    @discord.app_commands.default_permissions(manage_roles=True, manage_messages=True)
    @discord.app_commands.guild_only()
    async def command_nickname_sync_setup(
        interaction: discord.Interaction,
    ) -> None:  # pragma: no cover - decorator により Discord 側で実行
        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(
                "サーバー内でコマンドを実行してください。",
                ephemeral=True,
            )
            return

        view = NicknameSyncSetupView(
            guild_id=guild_id,
            executor_id=interaction.user.id,
            rule_store=rule_store,
        )
        LOGGER.info(
            "/nickname_sync_setup コマンドを実行したユーザー: guild=%s user=%s",
            guild_id,
            interaction.user.id,
        )

        await interaction.response.send_message(
            "🛠 監視するチャンネルと付与ロールを以下の View から選択してください。",
            view=view,
            ephemeral=True,
        )


__all__ = ["register_commands"]
