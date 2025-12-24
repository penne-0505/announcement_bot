from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence

from app.database import Database
from app.repositories._helpers import ensure_utc_timestamp


@dataclass(frozen=True, slots=True)
class ServerColor:
    guild_id: int
    color_value: int
    created_at: datetime


class ServerColorStore(Protocol):
    async def get_all_colors(self) -> Sequence[ServerColor]: ...

    async def get_color(self, guild_id: int) -> ServerColor | None: ...

    async def save_color(self, guild_id: int, color_value: int) -> ServerColor: ...


class ServerColorRepository:
    """Guild ごとの Embed カラーを PostgreSQL に保存するリポジトリ。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def get_all_colors(self) -> Sequence[ServerColor]:
        rows = await self._database.fetch(
            """
            SELECT guild_id, color_value, created_at
            FROM server_colors
            ORDER BY created_at ASC
            """
        )
        return [self._from_row(row) for row in rows]

    async def get_color(self, guild_id: int) -> ServerColor | None:
        row = await self._database.fetchrow(
            """
            SELECT guild_id, color_value, created_at
            FROM server_colors
            WHERE guild_id = ?
            """,
            guild_id,
        )
        if row is None:
            return None
        return self._from_row(row)

    async def save_color(self, guild_id: int, color_value: int) -> ServerColor:
        row = await self._database.fetchrow(
            """
            INSERT INTO server_colors (guild_id, color_value)
            VALUES (?, ?)
            ON CONFLICT (guild_id)
            DO UPDATE SET color_value = excluded.color_value
            RETURNING guild_id, color_value, created_at
            """,
            guild_id,
            color_value,
        )
        assert row is not None
        return self._from_row(row)

    @staticmethod
    def _from_row(row) -> ServerColor:
        return ServerColor(
            guild_id=int(row["guild_id"]),
            color_value=int(row["color_value"]),
            created_at=ensure_utc_timestamp(row["created_at"]),
        )


__all__ = ["ServerColor", "ServerColorRepository", "ServerColorStore"]
