from __future__ import annotations

import asyncio
import logging
from typing import Sequence

import asyncpg

LOGGER = logging.getLogger(__name__)


class Database:
    """asyncpg ベースで PostgreSQL への永続化を管理する。"""

    def __init__(
        self,
        dsn: str,
        *,
        min_size: int = 1,
        max_size: int = 5,
        timeout: float = 5.0,
    ) -> None:
        self._dsn = dsn
        self._min_size = min_size
        self._max_size = max_size
        self._timeout = timeout
        self._pool: asyncpg.Pool | None = None
        self._connect_lock = asyncio.Lock()

    async def connect(self) -> None:
        """PostgreSQL への接続を初期化し、テーブルを作成する。"""

        if self._pool is not None:
            return

        async with self._connect_lock:
            if self._pool is not None:
                return

            LOGGER.info("PostgreSQL (%s) への接続を開始します。", self._dsn)
            self._pool = await asyncpg.create_pool(
                dsn=self._dsn,
                min_size=self._min_size,
                max_size=self._max_size,
                command_timeout=self._timeout,
            )
            await self._ensure_schema()
            LOGGER.info("PostgreSQL テーブルの初期化が完了しました。")

    async def close(self) -> None:
        """接続をクローズする。"""

        if self._pool is None:
            return

        async with self._connect_lock:
            if self._pool is None:
                return

            await self._pool.close()
            self._pool = None
            LOGGER.info("PostgreSQL 接続をクローズしました。")

    async def fetchrow(self, query: str, *params: object) -> asyncpg.Record | None:
        """1 行取得する。"""

        pool = await self._require_pool()
        async with pool.acquire() as connection:
            return await connection.fetchrow(query, *params)

    async def fetch(self, query: str, *params: object) -> Sequence[asyncpg.Record]:
        """複数行取得する。"""

        pool = await self._require_pool()
        async with pool.acquire() as connection:
            return await connection.fetch(query, *params)

    async def execute(self, query: str, *params: object) -> int:
        """書き込み系クエリを実行する。"""

        pool = await self._require_pool()
        async with pool.acquire() as connection:
            result = await connection.execute(query, *params)
            try:
                return int(result.split()[-1])
            except (ValueError, IndexError):
                return 0

    async def _ensure_schema(self) -> None:
        """初回起動時にテーブルを作成する。"""

        schema_statements = [
            """
            CREATE TABLE IF NOT EXISTS channel_nickname_rules (
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                role_id BIGINT NOT NULL,
                updated_by BIGINT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, channel_id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS temporary_vc_categories (
                guild_id BIGINT PRIMARY KEY,
                category_id BIGINT NOT NULL,
                updated_by BIGINT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS temporary_voice_channels (
                guild_id BIGINT NOT NULL,
                owner_user_id BIGINT NOT NULL,
                channel_id BIGINT,
                category_id BIGINT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, owner_user_id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS server_colors (
                guild_id BIGINT PRIMARY KEY,
                color_value BIGINT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """,
        ]

        pool = await self._require_pool()
        async with pool.acquire() as connection:
            for statement in schema_statements:
                await connection.execute(statement)

    async def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database is not initialized. call connect() first.")
        return self._pool


__all__ = ["Database"]
