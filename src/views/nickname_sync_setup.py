from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from app.repositories import ChannelNicknameRuleStore

if TYPE_CHECKING:
    from discord.ui import ChannelSelect, RoleSelect

LOGGER = logging.getLogger(__name__)


class NicknameSyncSetupView(discord.ui.View):
    """チャンネル/ロール選択用の View。"""

    ERROR_SELECT_REQUIRED = "チャンネルとロールを両方選択してから保存してください。"
    ERROR_UNAUTHORIZED = "この View はコマンド実行者のみが操作できます。"
    SUCCESS_MESSAGE = "{channel} を監視対象に設定し、{role} を自動付与します。"

    def __init__(
        self,
        *,
        guild_id: int,
        executor_id: int,
        rule_store: ChannelNicknameRuleStore,
        timeout: float | None = 300,
    ) -> None:
        super().__init__(timeout=timeout)
        self.guild_id = guild_id
        self.executor_id = executor_id
        self.rule_store = rule_store
        self._selected_channel: discord.abc.GuildChannel | None = None
        self._selected_role: discord.Role | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.executor_id:
            await interaction.response.send_message(self.ERROR_UNAUTHORIZED, ephemeral=True)
            return False
        return True

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text, discord.ChannelType.news],
        placeholder="監視チャンネルを選択",
        min_values=1,
        max_values=1,
        row=0,
    )
    async def select_channel(
        self,
        interaction: discord.Interaction,
        select: "ChannelSelect",
    ) -> None:
        self._selected_channel = select.values[0]
        await interaction.response.defer(ephemeral=True)

    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="自動付与するロールを選択",
        min_values=1,
        max_values=1,
        row=1,
    )
    async def select_role(
        self,
        interaction: discord.Interaction,
        select: "RoleSelect",
    ) -> None:
        self._selected_role = select.values[0]
        await interaction.response.defer(ephemeral=True)

    @discord.ui.button(label="設定を保存", style=discord.ButtonStyle.primary, row=2)
    async def submit_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._handle_submit(interaction)

    async def _handle_submit(self, interaction: discord.Interaction) -> None:
        if self._selected_channel is None or self._selected_role is None:
            await interaction.response.send_message(self.ERROR_SELECT_REQUIRED, ephemeral=True)
            return

        await self.rule_store.upsert_rule(
            guild_id=self.guild_id,
            channel_id=self._selected_channel.id,
            role_id=self._selected_role.id,
            updated_by=interaction.user.id,
        )
        await interaction.response.send_message(
            self.SUCCESS_MESSAGE.format(
                channel=self._selected_channel.mention,
                role=self._selected_role.mention,
            ),
            ephemeral=True,
        )
        LOGGER.info(
            "ニックネーム同期設定を保存しました: guild=%s channel=%s role=%s executor=%s",
            self.guild_id,
            self._selected_channel.id,
            self._selected_role.id,
            interaction.user.id,
        )
        self.stop()


__all__ = ["NicknameSyncSetupView"]
