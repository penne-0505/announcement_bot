from __future__ import annotations

import asyncio
import logging
import os

from .container import build_discord_app
from .config import load_config

LOGGER = logging.getLogger(__name__)
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


async def run_bot() -> None:
    """設定を読み込み、Discord クライアントを起動する。"""

    LOGGER.info("Bot ランタイムを開始します。")
    try:
        config = load_config()
    except Exception:  # pragma: no cover - 設定エラーは稀
        LOGGER.exception("設定ファイルの読み込みに失敗しました。")
        return

    try:
        app = await build_discord_app(config)
    except Exception:  # pragma: no cover - 起動時例外は稀
        LOGGER.exception("Discord アプリケーションの初期化に失敗しました。")
        return
    try:
        await app.run()
    except Exception:  # pragma: no cover - discord クライアント実行時例外は稀
        LOGGER.exception("Bot ランタイムで予期しないエラーが発生しました。")
    finally:
        LOGGER.info("Bot ランタイムを終了しました。")


def main() -> None:
    """エントリーポイント。"""

    raw_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    resolved_level = logging.getLevelName(raw_level)
    if not isinstance(resolved_level, int):
        logging.basicConfig(
            level=logging.INFO, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT
        )
        LOGGER.warning("LOG_LEVEL が不正です。INFO にフォールバックします: %s", raw_level)
    else:
        logging.basicConfig(
            level=resolved_level, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT
        )
    LOGGER.info(
        "ログ設定を初期化しました: level=%s",
        logging.getLevelName(logging.getLogger().level),
    )
    asyncio.run(run_bot())


__all__ = ["main", "run_bot"]
