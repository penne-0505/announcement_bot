from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DiscordSettings:
    """Discord Bot に必要な設定値を保持する。"""

    token: str


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    """PostgreSQL 接続情報を保持する。"""

    url: str


@dataclass(frozen=True, slots=True)
class FeatureFlags:
    """アプリの実験的/運用フラグを保持する。"""

    force_color_regeneration: bool = False


@dataclass(frozen=True, slots=True)
class AppConfig:
    """アプリケーション全体の設定値をまとめる。"""

    discord: DiscordSettings
    database: DatabaseSettings
    feature_flags: FeatureFlags


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
    """Database URL を検証し整形する。"""

    if raw_url is None or raw_url.strip() == "":
        raise ValueError("DATABASE_URL is not set in environment variables.")
    return raw_url.strip()


def _prepare_force_color_regeneration(raw_flag: str | None) -> bool:
    """強制カラー再生成フラグを環境変数から取得する。"""

    if raw_flag is None or raw_flag.strip() == "":
        return False

    normalized = raw_flag.strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def load_config(env_file: str | Path | None = None) -> AppConfig:
    """環境変数と .env から設定を読み込む。"""

    _load_env_file(env_file)

    token = _prepare_client_token(raw_token=os.getenv("DISCORD_BOT_TOKEN"))
    database_url = _prepare_database_url(raw_url=os.getenv("DATABASE_URL"))
    force_color_regeneration = _prepare_force_color_regeneration(
        raw_flag=os.getenv("FORCE_REGENERATE_COLORS")
    )

    LOGGER.info("設定の読み込みが完了しました。")

    return AppConfig(
        discord=DiscordSettings(token=token),
        database=DatabaseSettings(url=database_url),
        feature_flags=FeatureFlags(force_color_regeneration=force_color_regeneration),
    )


__all__ = [
    "AppConfig",
    "DiscordSettings",
    "DatabaseSettings",
    "FeatureFlags",
    "load_config",
]
