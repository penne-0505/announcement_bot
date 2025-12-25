from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

import discord

from app.repositories import ChannelNicknameRuleStore
from app.services import (
    CategoryNotConfiguredError,
    TemporaryVoiceChannelCreationError,
    TemporaryVoiceChannelExistsError,
    TemporaryVoiceChannelNotFoundError,
    TemporaryVoiceChannelService,
)
from views import NicknameSyncSetupView, SendModalView

if TYPE_CHECKING:
    from bot.client import BotClient

LOGGER = logging.getLogger(__name__)


async def register_commands(
    client: "BotClient",
    *,
    rule_store: ChannelNicknameRuleStore,
    temporary_voice_service: TemporaryVoiceChannelService,
) -> None:
    """クライアントのアプリケーションコマンドを登録する。"""

    tree = client.tree

    @tree.command(
        name="osi", description="指定したチャンネルにメッセージを送信します。"
    )
    async def command_osi(
        interaction: discord.Interaction,
    ) -> None:  # pragma: no cover - Discord 実行時にテスト
        LOGGER.info("/osi コマンドを実行したユーザー: %s", interaction.user)
        await interaction.response.defer(ephemeral=True)
        view = SendModalView()
        await interaction.followup.send(
            "📨 下のボタンからメッセージ送信モーダルを開けます。",
            view=view,
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

    temporary_vc_group = discord.app_commands.Group(
        name="temporary_vc",
        description="一時ボイスチャンネルを管理します。",
    )

    @temporary_vc_group.command(
        name="category", description="一時VC用カテゴリを登録します。"
    )
    @discord.app_commands.describe(category="一時VCの作成先にするカテゴリ")
    @discord.app_commands.default_permissions(manage_channels=True)
    @discord.app_commands.guild_only()
    async def command_temporary_vc_category(
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
    ) -> None:  # pragma: no cover - Discord 実行時
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "サーバー内で実行してください。", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        result = await temporary_voice_service.configure_category(
            guild, category, interaction.user.id
        )
        deleted_count = len(result.deleted_channel_ids)
        missing_count = len(result.missing_channel_ids)
        LOGGER.info(
            "/temporary_vc category: guild=%s executor=%s category=%s deleted=%s missing=%s",
            guild.id,
            interaction.user.id,
            category.id,
            deleted_count,
            missing_count,
        )
        await interaction.followup.send(
            (
                f"📁 一時VCカテゴリを {category.mention} に設定しました。\n"
                f"🧹 削除済み: {deleted_count} 件 / 不存在: {missing_count} 件"
            ),
            ephemeral=True,
        )

    @temporary_vc_group.command(
        name="create", description="自分専用の一時VCを作成します。"
    )
    @discord.app_commands.guild_only()
    async def command_temporary_vc_create(
        interaction: discord.Interaction,
    ) -> None:  # pragma: no cover
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "サーバー内で実行してください。", ephemeral=True
            )
            return

        member = cast(discord.Member, interaction.user)

        try:
            channel = await temporary_voice_service.create_temporary_channel(member)
        except CategoryNotConfiguredError:
            await interaction.response.send_message(
                "⚠️ 一時VC用カテゴリが未設定です。管理者に `/temporary_vc category` を依頼してください。",
                ephemeral=True,
            )
            return
        except TemporaryVoiceChannelExistsError as exc:
            jump = (
                f"<#{exc.record.channel_id}>" if exc.record.channel_id else "登録済み"
            )
            await interaction.response.send_message(
                f"ℹ️ 既に管理対象の一時VCがあります: {jump}",
                ephemeral=True,
            )
            return
        except TemporaryVoiceChannelCreationError:
            await interaction.response.send_message(
                "❌ チャンネルの作成に失敗しました。時間をおいて再試行してください。",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"✅ 一時VCを作成しました: {channel.mention}",
            ephemeral=True,
        )

    @temporary_vc_group.command(
        name="reset", description="自分の一時VCを手動削除します。"
    )
    @discord.app_commands.guild_only()
    async def command_temporary_vc_reset(
        interaction: discord.Interaction,
    ) -> None:  # pragma: no cover
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "サーバー内で実行してください。", ephemeral=True
            )
            return

        member = cast(discord.Member, interaction.user)

        try:
            await temporary_voice_service.reset_temporary_channel(member)
        except TemporaryVoiceChannelNotFoundError:
            await interaction.response.send_message(
                "ℹ️ 管理対象の一時VCは登録されていません。",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "🗑️ 一時VCを削除しました。", ephemeral=True
        )

    tree.add_command(temporary_vc_group)


__all__ = ["register_commands"]
