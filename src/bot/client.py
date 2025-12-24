from __future__ import annotations

import logging

import discord

from app.repositories import ChannelNicknameRuleStore
from app.services import ColorAssignmentService, TemporaryVoiceChannelService
from bot.handlers import enforce_nickname_and_role

LOGGER = logging.getLogger(__name__)


class BotClient(discord.Client):
    """Discord Client 拡張。コマンド登録と同期を担当する。"""

    def __init__(
        self,
        *,
        intents: discord.Intents | None = None,
        rule_store: ChannelNicknameRuleStore,
        temporary_voice_service: TemporaryVoiceChannelService,
        color_assignment_service: ColorAssignmentService | None = None,
        force_color_regeneration: bool = False,
    ) -> None:
        super().__init__(intents=intents or discord.Intents.all())
        self.tree = discord.app_commands.CommandTree(self)
        self.rule_store = rule_store
        self.temporary_voice_service = temporary_voice_service
        self.color_assignment_service = color_assignment_service
        self.force_color_regeneration = force_color_regeneration

    async def on_ready(self) -> None:
        if self.user is None:
            LOGGER.warning("クライアントユーザー情報を取得できませんでした。")
            return

        LOGGER.info("ログイン完了: %s (ID: %s)", self.user, self.user.id)
        await self.tree.sync()
        LOGGER.info("アプリケーションコマンドの同期が完了しました。")
        if self.color_assignment_service is not None:
            try:
                if self.force_color_regeneration:
                    await self.color_assignment_service.regenerate_colors(self.guilds)
                    LOGGER.info("Guild カラーの強制再生成を完了しました。")
                else:
                    await self.color_assignment_service.assign_colors_to_new_guilds(
                        self.guilds
                    )
                    LOGGER.info("Guild カラーの割り当てを完了しました。")
            except Exception:
                LOGGER.exception("Guild カラー割り当て処理でエラーが発生しました。")
        await self.temporary_voice_service.cleanup_orphaned_channels(self.guilds)
        LOGGER.info("一時VCレコードの同期を完了しました。")
        LOGGER.info("準備完了。")

    async def on_message(self, message: discord.Message) -> None:
        """監視対象チャンネルでの投稿を処理する。"""

        if message.guild is None or message.author.bot:
            return

        rule = await self.rule_store.get_rule_for_channel(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
        )
        if rule is None:
            return

        try:
            await enforce_nickname_and_role(message, rule)
        except Exception:  # pragma: no cover - 想定外の例外通知
            LOGGER.exception("ニックネーム同期処理でエラーが発生しました。")

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        before_channel = before.channel if before is not None else None
        after_channel = after.channel if after is not None else None
        try:
            await self.temporary_voice_service.handle_voice_state_update(
                member, before_channel, after_channel
            )
        except Exception:  # pragma: no cover - 想定外の例外通知
            LOGGER.exception("一時VCの VoiceState 処理でエラーが発生しました。")


__all__ = ["BotClient"]
