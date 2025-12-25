from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
import logging

from app.database import Database
from app.repositories._helpers import ensure_utc_timestamp

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ChannelNicknameRule:
    guild_id: int
    channel_id: int
    role_id: int
    updated_by: int
    updated_at: datetime


class ChannelNicknameRuleStore(Protocol):
    async def upsert_rule(
        self, guild_id: int, channel_id: int, role_id: int, updated_by: int
    ) -> ChannelNicknameRule: ...

    async def get_rule_for_channel(
        self, guild_id: int, channel_id: int
    ) -> ChannelNicknameRule | None: ...


class ChannelNicknameRuleRepository:
    """チャンネル監視設定を PostgreSQL に保存するリポジトリ。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def upsert_rule(
        self, guild_id: int, channel_id: int, role_id: int, updated_by: int
    ) -> ChannelNicknameRule:
        now = datetime.now(timezone.utc).isoformat()
        row = await self._database.execute_one(
            self._database.table("channel_nickname_rules")
            .upsert(
                {
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "role_id": role_id,
                    "updated_by": updated_by,
                    "updated_at": now,
                },
                on_conflict="guild_id,channel_id",
            )
        )
        assert row is not None  # RETURNING があるため None にならない
        LOGGER.debug("Upserted channel nickname rule: %s", row)
        return self._to_entity(row)

    async def get_rule_for_channel(
        self, guild_id: int, channel_id: int
    ) -> ChannelNicknameRule | None:
        row = await self._database.execute_one(
            self._database.table("channel_nickname_rules")
            .select("guild_id, channel_id, role_id, updated_by, updated_at")
            .eq("guild_id", guild_id)
            .eq("channel_id", channel_id)
        )
        if row is None:
            return None
        LOGGER.debug("Fetched channel nickname rule: %s", row)
        return self._to_entity(row)

    @staticmethod
    def _to_entity(row) -> ChannelNicknameRule:
        return ChannelNicknameRule(
            guild_id=int(row["guild_id"]),
            channel_id=int(row["channel_id"]),
            role_id=int(row["role_id"]),
            updated_by=int(row["updated_by"]),
            updated_at=ensure_utc_timestamp(row["updated_at"]),
        )


__all__ = [
    "ChannelNicknameRule",
    "ChannelNicknameRuleRepository",
    "ChannelNicknameRuleStore",
]
