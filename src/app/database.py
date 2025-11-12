from __future__ import annotations

import logging
from typing import Any, Sequence

import asyncpg

LOGGER = logging.getLogger(__name__)


class Database:
    """asyncpg ベースの接続プールを管理する。"""

    def __init__(self, dsn: str, *, min_size: int = 1, max_size: int = 4) -> None:
        self._dsn = dsn
        self._min_size = min_size
        self._max_size = max_size
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """接続プールを初期化し、必要なテーブルを作成する。"""

        if self._pool is not None:
            return

        LOGGER.info("PostgreSQL への接続を開始します。")
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            min_size=self._min_size,
            max_size=self._max_size,
        )
        await self._ensure_schema()
        LOGGER.info("PostgreSQL との接続とテーブル初期化が完了しました。")

    async def close(self) -> None:
        """接続プールを閉じる。"""

        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            LOGGER.info("PostgreSQL との接続をクローズしました。")

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        """1 行を取得する。"""

        pool = await self._require_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch(self, query: str, *args: Any) -> Sequence[asyncpg.Record]:
        """複数行を取得する。"""

        pool = await self._require_pool()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        """書き込み系クエリを実行する。"""

        pool = await self._require_pool()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def _ensure_schema(self) -> None:
        """必要なテーブルを作成する。"""

        schema_sql = """
        CREATE TABLE IF NOT EXISTS channel_nickname_rules (
            guild_id BIGINT NOT NULL,
            channel_id BIGINT NOT NULL,
            role_id BIGINT NOT NULL,
            updated_by BIGINT NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (guild_id, channel_id)
        );
        """
        await self.execute(schema_sql)

    async def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized. call connect() first.")
        return self._pool


__all__ = ["Database"]
