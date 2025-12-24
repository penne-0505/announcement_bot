from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Sequence, Callable, Awaitable, Any

import aiosqlite

LOGGER = logging.getLogger(__name__)


class Database:
    """aiosqlite ベースで SQLite ファイルへの永続化を管理する。"""

    def __init__(self, path: Path | str, *, timeout: float = 5.0) -> None:
        self._path = Path(path)
        self._timeout = timeout
        self._connection: aiosqlite.Connection | None = None
        self._connect_lock = asyncio.Lock()
        self._operation_lock = asyncio.Lock()

    async def connect(self) -> None:
        """SQLite への接続を初期化し、テーブルを作成する。"""

        if self._connection is not None:
            return

        async with self._connect_lock:
            if self._connection is not None:
                return

            if not self._is_memory_database:
                self._path.parent.mkdir(parents=True, exist_ok=True)

            LOGGER.info("SQLite (%s) への接続を開始します。", self._path)
            self._connection = await aiosqlite.connect(
                str(self._path), timeout=self._timeout
            )
            self._connection.row_factory = aiosqlite.Row
            await self._connection.execute("PRAGMA foreign_keys = ON")
            await self._connection.commit()
            await self._ensure_schema()
            LOGGER.info("SQLite テーブルの初期化が完了しました。")

    async def close(self) -> None:
        """接続をクローズする。"""

        if self._connection is None:
            return

        async with self._connect_lock:
            if self._connection is None:
                return

            await self._connection.close()
            self._connection = None
            LOGGER.info("SQLite 接続をクローズしました。")

    async def fetchrow(self, query: str, *params: object) -> aiosqlite.Row | None:
        """1 行取得する。"""

        return await self._run_operation(self._fetch_row, query, params)

    async def fetch(self, query: str, *params: object) -> Sequence[aiosqlite.Row]:
        """複数行取得する。"""

        return await self._run_operation(self._fetch_all, query, params)

    async def execute(self, query: str, *params: object) -> int:
        """書き込み系クエリを実行する。"""

        return await self._run_operation(self._execute, query, params)

    async def _ensure_schema(self) -> None:
        """初回起動時にテーブルを作成する。"""

        schema_sql = """
        CREATE TABLE IF NOT EXISTS channel_nickname_rules (
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            updated_by INTEGER NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, channel_id)
        );

        CREATE TABLE IF NOT EXISTS temporary_vc_categories (
            guild_id INTEGER PRIMARY KEY,
            category_id INTEGER NOT NULL,
            updated_by INTEGER NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS temporary_voice_channels (
            guild_id INTEGER NOT NULL,
            owner_user_id INTEGER NOT NULL,
            channel_id INTEGER,
            category_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, owner_user_id)
        );

        CREATE TABLE IF NOT EXISTS server_colors (
            guild_id INTEGER PRIMARY KEY,
            color_value INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """

        connection = await self._require_connection()
        async with self._operation_lock:
            await connection.executescript(schema_sql)
            await connection.commit()

    async def _run_operation(
        self, handler: Callable[[aiosqlite.Connection, str, tuple[object, ...]], Awaitable[Any]], query: str, params: tuple[object, ...]
    ) -> Any:
        connection = await self._require_connection()
        async with self._operation_lock:
            return await handler(connection, query, params)

    async def _fetch_row(
        self, connection: aiosqlite.Connection, query: str, params: tuple[object, ...]
    ) -> aiosqlite.Row | None:
        cursor = await connection.execute(query, params)
        row = await cursor.fetchone()
        await cursor.close()
        return row

    async def _fetch_all(
        self, connection: aiosqlite.Connection, query: str, params: tuple[object, ...]
    ) -> Sequence[aiosqlite.Row]:
        cursor = await connection.execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()
        return rows

    async def _execute(
        self, connection: aiosqlite.Connection, query: str, params: tuple[object, ...]
    ) -> int:
        cursor = await connection.execute(query, params)
        await connection.commit()
        rowcount = cursor.rowcount
        await cursor.close()
        return rowcount

    async def _require_connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise RuntimeError("Database is not initialized. call connect() first.")
        return self._connection

    @property
    def _is_memory_database(self) -> bool:
        return self._path == Path(":memory:")


__all__ = ["Database"]
