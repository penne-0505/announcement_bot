from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DiscordSettings:
    """Discord Bot に必要な設定値を保持する。"""

    token: str


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    """Supabase 接続情報を保持する。"""

    url: str
    key: str


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


def _prepare_supabase_url(raw_url: str | None) -> str:
    """`SUPABASE_URL` を検証する。"""

    if raw_url is None or raw_url.strip() == "":
        raise ValueError("SUPABASE_URL is not set in environment variables.")

    normalized = raw_url.strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("SUPABASE_URL must be a valid HTTP(S) URL.")
    if not parsed.hostname:
        raise ValueError("SUPABASE_URL is invalid; host component is missing.")
    return normalized


def _prepare_supabase_key(raw_key: str | None) -> str:
    """`SUPABASE_KEY` を検証する。"""

    if raw_key is None or raw_key.strip() == "":
        raise ValueError("SUPABASE_KEY is not set in environment variables.")
    return raw_key.strip()


def load_config(env_file: str | Path | None = None) -> AppConfig:
    """環境変数と .env から設定を読み込む。"""

    _load_env_file(env_file)

    token = _prepare_client_token(raw_token=os.getenv("DISCORD_BOT_TOKEN"))
    database_url = _prepare_supabase_url(raw_url=os.getenv("SUPABASE_URL"))
    database_key = _prepare_supabase_key(raw_key=os.getenv("SUPABASE_KEY"))

    LOGGER.info("設定の読み込みが完了しました。")

    return AppConfig(
        discord=DiscordSettings(token=token),
        database=DatabaseSettings(url=database_url, key=database_key),
    )


__all__ = ["AppConfig", "DiscordSettings", "DatabaseSettings", "load_config"]
