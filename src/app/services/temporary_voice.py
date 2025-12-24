from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from typing import Sequence

import discord

from app.repositories import (
    TemporaryVoiceCategory,
    TemporaryVoiceCategoryRepository,
    TemporaryVoiceChannel,
    TemporaryVoiceChannelRepository,
)

LOGGER = logging.getLogger(__name__)
CATEGORY_RESET_REASON = "Temporary voice channel category updated"
TEMP_CHANNEL_CLEANUP_REASON = "Temporary voice channel expired"


class TemporaryVoiceError(RuntimeError):
    """一時VC関連の共通エラー。"""


class CategoryNotConfiguredError(TemporaryVoiceError):
    """カテゴリ未設定。"""


class TemporaryVoiceChannelExistsError(TemporaryVoiceError):
    def __init__(self, record: TemporaryVoiceChannel) -> None:
        super().__init__("temporary voice channel already exists")
        self.record = record


class TemporaryVoiceChannelNotFoundError(TemporaryVoiceError):
    """一時VCが見つからない。"""


class TemporaryVoiceChannelCreationError(TemporaryVoiceError):
    """Discord API 側のエラー。"""


@dataclass(slots=True)
class CategoryUpdateResult:
    category: TemporaryVoiceCategory
    deleted_channel_ids: list[int]
    missing_channel_ids: list[int]


class TemporaryVoiceChannelService:
    def __init__(
        self,
        *,
        category_repo: TemporaryVoiceCategoryRepository,
        channel_repo: TemporaryVoiceChannelRepository,
    ) -> None:
        self._category_repo = category_repo
        self._channel_repo = channel_repo

    async def ensure_category(self, guild_id: int) -> TemporaryVoiceCategory | None:
        return await self._category_repo.get_category(guild_id)

    async def configure_category(
        self,
        guild: discord.Guild,
        category: discord.CategoryChannel,
        executor_id: int,
    ) -> CategoryUpdateResult:
        deleted: list[int] = []
        missing: list[int] = []

        for record in await self._channel_repo.list_by_guild(guild.id):
            channel_id = record.channel_id
            if channel_id is None:
                missing.append(0)
                continue
            channel = guild.get_channel(channel_id)
            if isinstance(channel, discord.VoiceChannel):
                try:
                    await channel.delete(reason=CATEGORY_RESET_REASON)
                    LOGGER.info("既存の一時VCを削除しました: guild=%s channel=%s", guild.id, channel.id)
                    deleted.append(channel.id)
                except (discord.Forbidden, discord.HTTPException) as exc:
                    LOGGER.warning(
                        "一時VCの削除に失敗しました: guild=%s channel=%s error=%s",
                        guild.id,
                        channel_id,
                        exc,
                    )
            else:
                missing.append(channel_id)

        await self._channel_repo.purge_guild(guild.id)
        stored = await self._category_repo.upsert_category(guild.id, category.id, executor_id)
        LOGGER.info(
            "一時VCカテゴリを登録しました: guild=%s category=%s executor=%s",
            guild.id,
            category.id,
            executor_id,
        )
        return CategoryUpdateResult(category=stored, deleted_channel_ids=deleted, missing_channel_ids=missing)

    async def create_temporary_channel(self, member: discord.Member) -> discord.VoiceChannel:
        guild = member.guild
        if guild is None:
            raise CategoryNotConfiguredError("guild is required")

        category_entity, discord_category = await self._ensure_available_category(guild)
        existing = await self._channel_repo.get_by_owner(guild.id, member.id)
        if existing:
            raise TemporaryVoiceChannelExistsError(existing)

        try:
            record = await self._channel_repo.create_record(guild.id, member.id, category_entity.category_id)
        except sqlite3.IntegrityError as exc:
            existing_record = await self._channel_repo.get_by_owner(guild.id, member.id)
            if existing_record is not None:
                raise TemporaryVoiceChannelExistsError(existing_record) from exc
            raise TemporaryVoiceChannelCreationError("temporary voice channel already exists") from exc
        try:
            channel_name = self._build_channel_name(member)
            overwrites = {
                member: discord.PermissionOverwrite(
                    manage_channels=True,
                    move_members=True,
                    mute_members=True,
                    deafen_members=True,
                    connect=True,
                    speak=True,
                    stream=True,
                    use_voice_activation=True,
                    view_channel=True,
                )
            }
            channel = await guild.create_voice_channel(
                name=channel_name,
                category=discord_category,
                overwrites=overwrites,
                reason="Temporary VC requested",
            )
            await self._channel_repo.update_channel_id(guild.id, member.id, channel.id)
            LOGGER.info("一時VCを作成しました: guild=%s owner=%s channel=%s", guild.id, member.id, channel.id)
            return channel
        except (discord.Forbidden, discord.HTTPException) as exc:
            await self._channel_repo.delete_record(guild.id, member.id)
            LOGGER.error(
                "一時VCの作成に失敗したためレコードを削除しました: guild=%s owner=%s error=%s",
                guild.id,
                member.id,
                exc,
            )
            raise TemporaryVoiceChannelCreationError("failed to create voice channel") from exc

    async def reset_temporary_channel(self, member: discord.Member) -> None:
        guild = member.guild
        if guild is None:
            raise TemporaryVoiceChannelNotFoundError("guild is required")

        record = await self._channel_repo.get_by_owner(guild.id, member.id)
        if record is None:
            raise TemporaryVoiceChannelNotFoundError("temporary channel is not registered")

        await self._delete_channel_if_exists(guild, record)
        await self._channel_repo.delete_record(guild.id, member.id)
        LOGGER.info("一時VCのレコードを削除しました: guild=%s owner=%s", guild.id, member.id)

    async def cleanup_orphaned_channels(self, guilds: Sequence[discord.Guild]) -> None:
        guild_map = {guild.id: guild for guild in guilds}
        for record in await self._channel_repo.list_all():
            guild = guild_map.get(record.guild_id)
            if guild is None:
                LOGGER.warning("Bot が所属していないギルドのレコードを削除します: guild=%s", record.guild_id)
                await self._channel_repo.delete_record(record.guild_id, record.owner_user_id)
                continue

            if record.channel_id is None:
                LOGGER.warning("channel_id 未設定の一時VCを削除します: guild=%s owner=%s", record.guild_id, record.owner_user_id)
                await self._channel_repo.delete_record(record.guild_id, record.owner_user_id)
                continue

            channel = guild.get_channel(record.channel_id)
            if channel is None:
                LOGGER.warning(
                    "存在しないチャンネルのレコードを削除します: guild=%s channel=%s",
                    record.guild_id,
                    record.channel_id,
                )
                await self._channel_repo.delete_record(record.guild_id, record.owner_user_id)

    async def handle_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceChannel | None,
        after: discord.VoiceChannel | None,
    ) -> None:
        guild = member.guild
        if guild is None:
            return

        if before is not None:
            await self._cleanup_if_empty(guild, before)

        if after is not None:
            record = await self._channel_repo.get_by_channel(guild.id, after.id)
            if record is not None:
                await self._channel_repo.touch_last_seen(record.guild_id, record.owner_user_id)

    async def _cleanup_if_empty(self, guild: discord.Guild, channel: discord.VoiceChannel) -> None:
        record = await self._channel_repo.get_by_channel(guild.id, channel.id)
        if record is None:
            return

        if channel.members:
            return

        await self._delete_channel_if_exists(guild, record, reason=TEMP_CHANNEL_CLEANUP_REASON)
        await self._channel_repo.delete_record(record.guild_id, record.owner_user_id)
        LOGGER.info("無人一時VCを削除しました: guild=%s channel=%s", guild.id, channel.id)

    async def _delete_channel_if_exists(
        self,
        guild: discord.Guild,
        record: TemporaryVoiceChannel,
        *,
        reason: str | None = None,
    ) -> None:
        channel_id = record.channel_id
        if channel_id is None:
            return

        channel = guild.get_channel(channel_id)
        if isinstance(channel, discord.VoiceChannel):
            try:
                await channel.delete(reason=reason or CATEGORY_RESET_REASON)
            except (discord.Forbidden, discord.HTTPException) as exc:
                LOGGER.warning(
                    "一時VCの削除に失敗しました: guild=%s channel=%s error=%s",
                    guild.id,
                    channel_id,
                    exc,
                )

    async def _ensure_available_category(
        self, guild: discord.Guild
    ) -> tuple[TemporaryVoiceCategory, discord.CategoryChannel]:
        category = await self._category_repo.get_category(guild.id)
        if category is None:
            raise CategoryNotConfiguredError("temporary VC category is not configured")

        discord_category = guild.get_channel(category.category_id)
        if not isinstance(discord_category, discord.CategoryChannel):
            await self._category_repo.delete_category(guild.id)
            LOGGER.warning(
                "登録済みカテゴリが見つからないため設定を削除しました: guild=%s category=%s",
                guild.id,
                category.category_id,
            )
            raise CategoryNotConfiguredError("configured category is no longer available")

        return category, discord_category

    @staticmethod
    def _build_channel_name(member: discord.Member) -> str:
        source = (
            getattr(member, "display_name", None)
            or getattr(member, "global_name", None)
            or getattr(member, "name", None)
            or str(member.id)
        )
        sanitized = "".join(ch for ch in source if ch.isprintable())
        sanitized = sanitized.strip()
        if not sanitized:
            sanitized = f"temporary-{member.id}"
        return sanitized[:32]


__all__ = [
    "CategoryNotConfiguredError",
    "CategoryUpdateResult",
    "TemporaryVoiceChannelCreationError",
    "TemporaryVoiceChannelExistsError",
    "TemporaryVoiceChannelNotFoundError",
    "TemporaryVoiceChannelService",
]
