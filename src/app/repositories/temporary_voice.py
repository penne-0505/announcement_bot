from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence
import logging

from app.database import Database
from app.repositories._helpers import ensure_utc_timestamp

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TemporaryVoiceCategory:
    guild_id: int
    category_id: int
    updated_by: int
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class TemporaryVoiceChannel:
    guild_id: int
    owner_user_id: int
    channel_id: int | None
    category_id: int
    created_at: datetime
    last_seen_at: datetime


class TemporaryVoiceCategoryStore(Protocol):
    async def upsert_category(
        self, guild_id: int, category_id: int, updated_by: int
    ) -> TemporaryVoiceCategory: ...

    async def get_category(self, guild_id: int) -> TemporaryVoiceCategory | None: ...


class TemporaryVoiceChannelStore(Protocol):
    async def create_record(
        self, guild_id: int, owner_user_id: int, category_id: int
    ) -> TemporaryVoiceChannel: ...

    async def update_channel_id(
        self, guild_id: int, owner_user_id: int, channel_id: int
    ) -> TemporaryVoiceChannel: ...

    async def get_by_owner(
        self, guild_id: int, owner_user_id: int
    ) -> TemporaryVoiceChannel | None: ...

    async def get_by_channel(
        self, guild_id: int, channel_id: int
    ) -> TemporaryVoiceChannel | None: ...

    async def delete_record(self, guild_id: int, owner_user_id: int) -> None: ...

    async def delete_by_channel(self, guild_id: int, channel_id: int) -> None: ...

    async def list_by_guild(self, guild_id: int) -> Sequence[TemporaryVoiceChannel]: ...

    async def list_all(self) -> Sequence[TemporaryVoiceChannel]: ...

    async def purge_guild(self, guild_id: int) -> None: ...

    async def touch_last_seen(self, guild_id: int, owner_user_id: int) -> None: ...


class TemporaryVoiceCategoryRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def upsert_category(
        self, guild_id: int, category_id: int, updated_by: int
    ) -> TemporaryVoiceCategory:
        query = """
        INSERT INTO temporary_vc_categories (guild_id, category_id, updated_by)
        VALUES ($1, $2, $3)
        ON CONFLICT (guild_id)
        DO UPDATE SET category_id = excluded.category_id, updated_by = excluded.updated_by, updated_at = CURRENT_TIMESTAMP
        RETURNING guild_id, category_id, updated_by, updated_at
        """
        row = await self._database.fetchrow(query, guild_id, category_id, updated_by)
        assert row is not None
        LOGGER.debug("Upserted temporary voice category: %s", row)
        return self._category_from_row(row)

    async def get_category(self, guild_id: int) -> TemporaryVoiceCategory | None:
        query = """
        SELECT guild_id, category_id, updated_by, updated_at
        FROM temporary_vc_categories
        WHERE guild_id = $1
        """
        row = await self._database.fetchrow(query, guild_id)
        if row is None:
            return None
        LOGGER.debug("Fetched temporary voice category: %s", row)
        return self._category_from_row(row)

    async def delete_category(self, guild_id: int) -> None:
        LOGGER.debug("Deleting temporary voice category for guild_id=%d", guild_id)
        await self._database.execute(
            "DELETE FROM temporary_vc_categories WHERE guild_id = $1", guild_id
        )

    @staticmethod
    def _category_from_row(row) -> TemporaryVoiceCategory:
        return TemporaryVoiceCategory(
            guild_id=int(row["guild_id"]),
            category_id=int(row["category_id"]),
            updated_by=int(row["updated_by"]),
            updated_at=ensure_utc_timestamp(row["updated_at"]),
        )


class TemporaryVoiceChannelRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def create_record(
        self, guild_id: int, owner_user_id: int, category_id: int
    ) -> TemporaryVoiceChannel:
        query = """
        INSERT INTO temporary_voice_channels (guild_id, owner_user_id, category_id)
        VALUES ($1, $2, $3)
        RETURNING guild_id, owner_user_id, channel_id, category_id, created_at, last_seen_at
        """
        row = await self._database.fetchrow(query, guild_id, owner_user_id, category_id)
        assert row is not None
        LOGGER.debug("Created temporary voice channel record: %s", row)
        return self._channel_from_row(row)

    async def update_channel_id(
        self, guild_id: int, owner_user_id: int, channel_id: int
    ) -> TemporaryVoiceChannel:
        query = """
        UPDATE temporary_voice_channels
        SET channel_id = $1, last_seen_at = CURRENT_TIMESTAMP
        WHERE guild_id = $2 AND owner_user_id = $3
        RETURNING guild_id, owner_user_id, channel_id, category_id, created_at, last_seen_at
        """
        row = await self._database.fetchrow(query, channel_id, guild_id, owner_user_id)
        if row is None:
            raise ValueError("temporary voice channel record not found for update")
        LOGGER.debug("Updated temporary voice channel record: %s", row)
        return self._channel_from_row(row)

    async def get_by_owner(
        self, guild_id: int, owner_user_id: int
    ) -> TemporaryVoiceChannel | None:
        query = """
        SELECT guild_id, owner_user_id, channel_id, category_id, created_at, last_seen_at
        FROM temporary_voice_channels
        WHERE guild_id = $1 AND owner_user_id = $2
        """
        row = await self._database.fetchrow(query, guild_id, owner_user_id)
        if row is None:
            return None
        LOGGER.debug("Fetched temporary voice channel record by owner: %s", row)
        return self._channel_from_row(row)

    async def get_by_channel(
        self, guild_id: int, channel_id: int
    ) -> TemporaryVoiceChannel | None:
        query = """
        SELECT guild_id, owner_user_id, channel_id, category_id, created_at, last_seen_at
        FROM temporary_voice_channels
        WHERE guild_id = $1 AND channel_id = $2
        """
        row = await self._database.fetchrow(query, guild_id, channel_id)
        if row is None:
            return None
        LOGGER.debug("Fetched temporary voice channel record by channel: %s", row)
        return self._channel_from_row(row)

    async def delete_record(self, guild_id: int, owner_user_id: int) -> None:
        await self._database.execute(
            "DELETE FROM temporary_voice_channels WHERE guild_id = $1 AND owner_user_id = $2",
            guild_id,
            owner_user_id,
        )
        LOGGER.debug(
            "Deleted temporary voice channel record for guild_id=%d, owner_user_id=%d",
            guild_id,
            owner_user_id,
        )

    async def delete_by_channel(self, guild_id: int, channel_id: int) -> None:
        await self._database.execute(
            "DELETE FROM temporary_voice_channels WHERE guild_id = $1 AND channel_id = $2",
            guild_id,
            channel_id,
        )
        LOGGER.debug(
            "Deleted temporary voice channel record for guild_id=%d, channel_id=%d",
            guild_id,
            channel_id,
        )

    async def list_by_guild(self, guild_id: int) -> Sequence[TemporaryVoiceChannel]:
        query = """
        SELECT guild_id, owner_user_id, channel_id, category_id, created_at, last_seen_at
        FROM temporary_voice_channels
        WHERE guild_id = $1
        """
        rows = await self._database.fetch(query, guild_id)
        LOGGER.debug(
            "Listed temporary voice channel records for guild_id=%d: %d records",
            guild_id,
            len(rows),
        )
        return [self._channel_from_row(row) for row in rows]

    async def list_all(self) -> Sequence[TemporaryVoiceChannel]:
        query = """
        SELECT guild_id, owner_user_id, channel_id, category_id, created_at, last_seen_at
        FROM temporary_voice_channels
        """
        rows = await self._database.fetch(query)
        LOGGER.debug(
            "Listed all temporary voice channel records: %d records", len(rows)
        )
        return [self._channel_from_row(row) for row in rows]

    async def purge_guild(self, guild_id: int) -> None:
        await self._database.execute(
            "DELETE FROM temporary_voice_channels WHERE guild_id = $1", guild_id
        )
        LOGGER.debug("Purged temporary voice channel records for guild_id=%d", guild_id)

    async def touch_last_seen(self, guild_id: int, owner_user_id: int) -> None:
        await self._database.execute(
            "UPDATE temporary_voice_channels SET last_seen_at = CURRENT_TIMESTAMP WHERE guild_id = $1 AND owner_user_id = $2",
            guild_id,
            owner_user_id,
        )
        LOGGER.debug(
            "Updated last_seen_at for guild_id=%d, owner_user_id=%d",
            guild_id,
            owner_user_id,
        )

    @staticmethod
    def _channel_from_row(row) -> TemporaryVoiceChannel:
        channel_id = row["channel_id"]
        return TemporaryVoiceChannel(
            guild_id=int(row["guild_id"]),
            owner_user_id=int(row["owner_user_id"]),
            channel_id=int(channel_id) if channel_id is not None else None,
            category_id=int(row["category_id"]),
            created_at=ensure_utc_timestamp(row["created_at"]),
            last_seen_at=ensure_utc_timestamp(row["last_seen_at"]),
        )


__all__ = [
    "TemporaryVoiceCategory",
    "TemporaryVoiceCategoryRepository",
    "TemporaryVoiceCategoryStore",
    "TemporaryVoiceChannel",
    "TemporaryVoiceChannelRepository",
    "TemporaryVoiceChannelStore",
]
