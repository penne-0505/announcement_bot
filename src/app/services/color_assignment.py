from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from typing import Sequence

import discord

from app.repositories import ServerColorRepository, ServerColorStore

LOGGER = logging.getLogger(__name__)

DEFAULT_DISTANCE_THRESHOLD = 40.0
DEFAULT_MAX_ATTEMPTS = 100


class ColorGenerationError(RuntimeError):
    """閾値を満たすカラーが生成できない場合のエラー。"""


@dataclass(frozen=True, slots=True)
class ColorGenerationConfig:
    distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD
    max_attempts: int = DEFAULT_MAX_ATTEMPTS


class ColorAssignmentService:
    """Guild ごとにユニークな Embed カラーを割り当てるサービス。"""

    def __init__(
        self,
        repository: ServerColorRepository | ServerColorStore,
        *,
        config: ColorGenerationConfig | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._repository = repository
        self._config = config or ColorGenerationConfig()
        self._rng = rng or random.Random()

    def generate_unique_color(self, existing_colors: Sequence[int]) -> int:
        """既存カラーと十分に離れた色を生成する。"""

        attempts = 0
        threshold = self._config.distance_threshold
        max_attempts = self._config.max_attempts

        while attempts < max_attempts:
            candidate = self._rng.randint(0x000000, 0xFFFFFF)
            if all(self._distance(candidate, color) >= threshold for color in existing_colors):
                return candidate
            attempts += 1

        LOGGER.error(
            "十分に離れたカラーを %d 回試行しましたが生成できませんでした。(threshold=%s)",
            max_attempts,
            threshold,
        )
        raise ColorGenerationError("unique color could not be generated within max_attempts")

    async def assign_colors_to_new_guilds(self, guilds: Sequence[discord.Guild]) -> dict[int, int]:
        """既存登録を尊重しつつ未登録 Guild にカラーを割り当てる。"""

        stored = await self._repository.get_all_colors()
        assigned: dict[int, int] = {color.guild_id: color.color_value for color in stored}
        existing_values = [color.color_value for color in stored]

        for guild in guilds:
            if guild.id in assigned:
                continue
            color_value = self.generate_unique_color(existing_values)
            await self._repository.save_color(guild.id, color_value)
            assigned[guild.id] = color_value
            existing_values.append(color_value)
            LOGGER.info("Guild %s にカラー 0x%06X を割り当てました。", guild.id, color_value)

        return assigned

    @staticmethod
    def _distance(color_a: int, color_b: int) -> float:
        ra, ga, ba = ColorAssignmentService._to_rgb(color_a)
        rb, gb, bb = ColorAssignmentService._to_rgb(color_b)
        return math.sqrt((ra - rb) ** 2 + (ga - gb) ** 2 + (ba - bb) ** 2)

    @staticmethod
    def _to_rgb(value: int) -> tuple[int, int, int]:
        value = max(0, min(0xFFFFFF, value))
        r = (value >> 16) & 0xFF
        g = (value >> 8) & 0xFF
        b = value & 0xFF
        return r, g, b


__all__ = [
    "ColorAssignmentService",
    "ColorGenerationConfig",
    "ColorGenerationError",
    "DEFAULT_DISTANCE_THRESHOLD",
    "DEFAULT_MAX_ATTEMPTS",
]
