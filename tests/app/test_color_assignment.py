import types
from datetime import datetime, timezone

import pytest

from app.repositories.server_colors import ServerColor
from app.services.color_assignment import (
    ColorAssignmentService,
    ColorGenerationConfig,
    ColorGenerationError,
)


class SequenceRandom:
    def __init__(self, values):
        self._values = list(values)

    def randint(self, a: int, b: int) -> int:  # noqa: D401 - random 互換API
        if not self._values:
            raise AssertionError("randint was called more times than expected")
        return self._values.pop(0)


class FakeServerColorRepo:
    def __init__(self, preset=None):
        self._store = {color.guild_id: color for color in (preset or [])}
        self.saved: list[ServerColor] = []

    async def get_all_colors(self):
        return list(self._store.values())

    async def get_color(self, guild_id: int):
        return self._store.get(guild_id)

    async def save_color(self, guild_id: int, color_value: int):
        record = ServerColor(guild_id=guild_id, color_value=color_value, created_at=datetime.now(timezone.utc))
        self._store[guild_id] = record
        self.saved.append(record)
        return record


@pytest.mark.asyncio
async def test_generate_unique_color_skips_close_colors():
    repo = FakeServerColorRepo()
    config = ColorGenerationConfig(distance_threshold=10, max_attempts=5)
    rng = SequenceRandom([0x000001, 0x000005, 0x123456])
    service = ColorAssignmentService(repo, config=config, rng=rng)

    result = service.generate_unique_color([0x000000, 0x00000A])

    assert result == 0x123456


@pytest.mark.asyncio
async def test_generate_unique_color_raises_after_max_attempts():
    repo = FakeServerColorRepo()
    config = ColorGenerationConfig(distance_threshold=500.0, max_attempts=3)
    rng = SequenceRandom([0x000000, 0x000000, 0x000000])
    service = ColorAssignmentService(repo, config=config, rng=rng)

    with pytest.raises(ColorGenerationError):
        service.generate_unique_color([0x000000])


@pytest.mark.asyncio
async def test_assign_colors_to_new_guilds_adds_only_missing():
    existing = ServerColor(guild_id=1, color_value=0x112233, created_at=datetime.now(timezone.utc))
    repo = FakeServerColorRepo([existing])
    config = ColorGenerationConfig(distance_threshold=20, max_attempts=5)
    rng = SequenceRandom([0x112240, 0x334455, 0x556677])
    service = ColorAssignmentService(repo, config=config, rng=rng)

    guilds = [types.SimpleNamespace(id=1), types.SimpleNamespace(id=2), types.SimpleNamespace(id=3)]
    assigned = await service.assign_colors_to_new_guilds(guilds)

    assert assigned[1] == 0x112233
    assert assigned[2] != assigned[3]
    assert all(record.guild_id in (2, 3) for record in repo.saved)
