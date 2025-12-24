from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.database import Database
from app.repositories._helpers import ensure_utc_timestamp


@dataclass(frozen=True, slots=True)
class ChannelNicknameRule:
    guild_id: int
    channel_id: int
    role_id: int
    updated_by: int
    updated_at: datetime


class ChannelNicknameRuleStore(Protocol):
    async def upsert_rule(self, guild_id: int, channel_id: int, role_id: int, updated_by: int) -> ChannelNicknameRule: ...

    async def get_rule_for_channel(self, guild_id: int, channel_id: int) -> ChannelNicknameRule | None: ...


class ChannelNicknameRuleRepository:
    """チャンネル監視設定を PostgreSQL に保存するリポジトリ。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def upsert_rule(self, guild_id: int, channel_id: int, role_id: int, updated_by: int) -> ChannelNicknameRule:
        query = """
        INSERT INTO channel_nickname_rules (guild_id, channel_id, role_id, updated_by)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (guild_id, channel_id)
        DO UPDATE SET role_id = excluded.role_id, updated_by = excluded.updated_by, updated_at = CURRENT_TIMESTAMP
        RETURNING guild_id, channel_id, role_id, updated_by, updated_at
        """
        row = await self._database.fetchrow(query, guild_id, channel_id, role_id, updated_by)
        assert row is not None  # RETURNING があるため None にならない
        return self._to_entity(row)

    async def get_rule_for_channel(self, guild_id: int, channel_id: int) -> ChannelNicknameRule | None:
        query = """
        SELECT guild_id, channel_id, role_id, updated_by, updated_at
        FROM channel_nickname_rules
        WHERE guild_id = ? AND channel_id = ?
        """
        row = await self._database.fetchrow(query, guild_id, channel_id)
        if row is None:
            return None
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
