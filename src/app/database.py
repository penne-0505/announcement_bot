from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Sequence, TypeVar

import asyncpg

LOGGER = logging.getLogger(__name__)
T = TypeVar("T")


class Database:
    """asyncpg ベースの接続プールを管理する。"""

    def __init__(self, dsn: str, *, min_size: int = 1, max_size: int = 4) -> None:
        self._dsn = dsn
        self._min_size = min_size
        self._max_size = max_size
        self._pool: asyncpg.Pool | None = None
        self._pool_lock = asyncio.Lock()

    async def connect(self) -> None:
        """接続プールを初期化し、必要なテーブルを作成する。"""

        if self._pool is not None:
            return

        async with self._pool_lock:
            if self._pool is not None:
                return

            LOGGER.info("PostgreSQL への接続を開始します。")
            self._pool = await self._create_pool_with_retry()
            await self._ensure_schema()
            LOGGER.info("PostgreSQL との接続とテーブル初期化が完了しました。")

    async def close(self) -> None:
        """接続プールを閉じる。"""

        if self._pool is not None:
            async with self._pool_lock:
                if self._pool is not None:
                    await self._pool.close()
                    self._pool = None
                    LOGGER.info("PostgreSQL との接続をクローズしました。")

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        """1 行を取得する。"""

        return await self._run_with_retry(lambda conn: conn.fetchrow(query, *args))

    async def fetch(self, query: str, *args: Any) -> Sequence[asyncpg.Record]:
        """複数行を取得する。"""

        return await self._run_with_retry(lambda conn: conn.fetch(query, *args))

    async def execute(self, query: str, *args: Any) -> str:
        """書き込み系クエリを実行する。"""

        return await self._run_with_retry(lambda conn: conn.execute(query, *args))

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

        CREATE TABLE IF NOT EXISTS temporary_vc_categories (
            guild_id BIGINT PRIMARY KEY,
            category_id BIGINT NOT NULL,
            updated_by BIGINT NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS temporary_voice_channels (
            guild_id BIGINT NOT NULL,
            owner_user_id BIGINT NOT NULL,
            channel_id BIGINT,
            category_id BIGINT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (guild_id, owner_user_id)
        );

        CREATE TABLE IF NOT EXISTS server_colors (
            guild_id BIGINT PRIMARY KEY,
            color_value INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
        await self.execute(schema_sql)

    async def _create_pool_with_retry(
        self,
        *,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
    ) -> asyncpg.Pool:
        """PaaS のスリープ復帰を考慮し、接続プールをリトライ付きで作成する。"""

        attempt = 1
        while True:
            try:
                return await asyncpg.create_pool(
                    dsn=self._dsn,
                    min_size=self._min_size,
                    max_size=self._max_size,
                    # サーバー側の idle timeout より短くコネクションをリサイクルし、
                    # スリープ復帰やネットワーク断で切られたコネクションを早期に除去する。
                    max_inactive_connection_lifetime=1800,
                    timeout=10,
                )
            except Exception as exc:  # pragma: no cover - 実際の接続失敗は環境依存
                if attempt >= max_attempts:
                    LOGGER.error(
                        "PostgreSQL への接続に失敗しました (%d/%d 回目)。再試行を断念します。",
                        attempt,
                        max_attempts,
                        exc_info=exc,
                    )
                    raise

                delay = min(max_delay, base_delay * 2 ** (attempt - 1))
                LOGGER.warning(
                    "PostgreSQL への接続に失敗しました (%d/%d 回目: %s)。%.1f 秒後に再試行します。",
                    attempt,
                    max_attempts,
                    exc.__class__.__name__,
                    delay,
                )
                attempt += 1
                await asyncio.sleep(delay)

    async def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized. call connect() first.")
        return self._pool

    async def _reset_pool(self, cause: Exception | None = None) -> None:
        """接続断検知時にプールを再生成する。"""

        async with self._pool_lock:
            if self._pool is not None:
                try:
                    await self._pool.close()
                except Exception as exc:  # pragma: no cover - close 失敗はログのみ
                    LOGGER.warning("接続プールのクローズに失敗しました: %s", exc)
            self._pool = await self._create_pool_with_retry()
            if cause is not None:
                LOGGER.info("接続プールを再生成しました (原因: %s)", cause.__class__.__name__)

    async def _run_with_retry(self, op: Callable[[asyncpg.Connection], Awaitable[T]], *, attempts: int = 2) -> T:
        """接続断を検知したらプールを再生成して1回だけリトライする。"""

        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            pool = await self._require_pool()
            try:
                async with pool.acquire() as conn:
                    return await op(conn)
            except (
                asyncpg.InterfaceError,
                asyncpg.ConnectionDoesNotExistError,
                asyncpg.PostgresConnectionError,
                ConnectionResetError,
                OSError,
            ) as exc:
                last_exc = exc
                LOGGER.warning(
                    "DB 接続エラーを検知しました。再試行します (%d/%d): %s",
                    attempt,
                    attempts,
                    exc.__class__.__name__,
                )
                await self._reset_pool(exc)
        assert last_exc is not None  # for type checker
        raise last_exc


__all__ = ["Database"]
