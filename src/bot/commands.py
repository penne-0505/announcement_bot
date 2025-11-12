from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from app.repositories import ChannelNicknameRuleStore
from views import SendModalView

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
        name="nickname_guard",
        description="監視チャンネルを登録し、投稿内容をニックネームに揃えます。",
    )
    @discord.app_commands.describe(
        channel="監視対象のチャンネル",
        role="自動付与するロール",
    )
    @discord.app_commands.default_permissions(manage_roles=True, manage_messages=True)
    @discord.app_commands.guild_only()
    async def command_nickname_guard(
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        role: discord.Role,
    ) -> None:  # pragma: no cover - decorator により Discord 側で実行
        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(
                "サーバー内でコマンドを実行してください。",
                ephemeral=True,
            )
            return

        if channel.guild is None or channel.guild.id != guild_id:
            await interaction.response.send_message(
                "同じサーバー内のチャンネルを指定してください。",
                ephemeral=True,
            )
            return

        if role.guild is None or role.guild.id != guild_id:
            await interaction.response.send_message(
                "同じサーバー内のロールを指定してください。",
                ephemeral=True,
            )
            return

        await rule_store.upsert_rule(
            guild_id=guild_id,
            channel_id=channel.id,
            role_id=role.id,
            updated_by=interaction.user.id,
        )
        LOGGER.info(
            "ニックネーム同期設定を更新しました: guild=%s channel=%s role=%s executor=%s",
            guild_id,
            channel.id,
            role.id,
            interaction.user.id,
        )

        await interaction.response.send_message(
            f"{channel.mention} を監視対象に設定し、{role.mention} を自動付与します。",
            ephemeral=True,
        )


__all__ = ["register_commands"]
