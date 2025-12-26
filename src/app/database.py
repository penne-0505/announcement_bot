from __future__ import annotations

import asyncio
import logging
from typing import Any

from supabase import AsyncClient, create_async_client

LOGGER = logging.getLogger(__name__)


class Database:
    """Supabase Python SDK を使って PostgreSQL への永続化を管理する。"""

    def __init__(
        self,
        url: str,
        key: str,
    ) -> None:
        self._url = url
        self._key = key
        self._client: AsyncClient | None = None
        self._connect_lock = asyncio.Lock()

    async def connect(self) -> None:
        """Supabase への接続を初期化する。"""

        if self._client is not None:
            return

        async with self._connect_lock:
            if self._client is not None:
                return

            LOGGER.info("Supabase (%s) への接続を開始します。", self._url)
            self._client = await create_async_client(self._url, self._key)
            LOGGER.info("Supabase クライアントの初期化が完了しました。")

    async def close(self) -> None:
        """接続をクローズする。"""

        if self._client is None:
            return

        async with self._connect_lock:
            if self._client is None:
                return

            client = self._client
            self._client = None
            close_fn = getattr(client, "aclose", None) or getattr(client, "close", None)
            if callable(close_fn):
                result = close_fn()
                if asyncio.iscoroutine(result):
                    await result
                LOGGER.info("Supabase 接続をクローズしました。")
            else:
                LOGGER.info(
                    "Supabase クライアントは明示的な close を持たないため参照を破棄しました。"
                )

    async def execute(self, request) -> list[dict[str, Any]]:
        """Supabase リクエストを実行し、データを返す。"""

        response = await request.execute()
        error = getattr(response, "error", None)
        if error is not None:
            LOGGER.error("Supabase クエリエラーが発生しました: %s", error)
            raise RuntimeError(f"Supabase query failed: {error}")
        data = getattr(response, "data", None)
        if data is None:
            return []
        if isinstance(data, list):
            return data
        return [data]

    async def execute_one(self, request) -> dict[str, Any] | None:
        """Supabase リクエストを実行し、1件だけ返す。"""

        data = await self.execute(request)
        if not data:
            return None
        return data[0]

    def table(self, name: str):
        """テーブルアクセス用のクエリビルダーを返す。"""

        return self._require_client().table(name)

    def _require_client(self) -> AsyncClient:
        if self._client is None:
            raise RuntimeError("Database is not initialized. call connect() first.")
        return self._client


__all__ = ["Database"]
