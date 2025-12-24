from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DiscordSettings:
    """Discord Bot に必要な設定値を保持する。"""

    token: str


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    """PostgreSQL 接続先 DSN を保持する。"""

    dsn: str


@dataclass(frozen=True, slots=True)
class AppConfig:
    """アプリケーション全体の設定値をまとめる。"""

    discord: DiscordSettings
    database: DatabaseSettings


def _load_env_file(env_file: str | Path | None) -> None:
    """`.env` ファイルを読み込む。"""

    if env_file is None:
        load_dotenv()
        return

    path = Path(env_file)
    if path.is_file():
        load_dotenv(dotenv_path=path)
        return

    raise FileNotFoundError(f".env file not found at: {path}")


def _prepare_client_token(raw_token: str | None) -> str:
    """Discord Bot トークンを検証して整形する。"""

    if raw_token is None or raw_token.strip() == "":
        raise ValueError("Discord bot token is not set in environment variables.")
    return raw_token.strip()


def _prepare_database_url(raw_url: str | None) -> str:
    """`DATABASE_URL` を PostgreSQL DSN として検証する。"""

    if raw_url is None or raw_url.strip() == "":
        raise ValueError("DATABASE_URL is not set in environment variables.")

    normalized = raw_url.strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError(
            "DATABASE_URL must be a Postgres URL (e.g. postgresql://user:pass@host:5432/db)"
        )
    if not parsed.hostname:
        raise ValueError("DATABASE_URL is invalid; host component is missing.")
    return normalized


def load_config(env_file: str | Path | None = None) -> AppConfig:
    """環境変数と .env から設定を読み込む。"""

    _load_env_file(env_file)

    token = _prepare_client_token(raw_token=os.getenv("DISCORD_BOT_TOKEN"))
    database_dsn = _prepare_database_url(raw_url=os.getenv("DATABASE_URL"))
    force_color_regeneration = _prepare_force_color_regeneration(
        raw_flag=os.getenv("FORCE_REGENERATE_COLORS")
    )

    LOGGER.info("設定の読み込みが完了しました。")

    return AppConfig(
        discord=DiscordSettings(token=token),
        database=DatabaseSettings(dsn=database_dsn),
        feature_flags=FeatureFlags(force_color_regeneration=force_color_regeneration),
    )


__all__ = ["AppConfig", "DiscordSettings", "DatabaseSettings", "load_config"]
