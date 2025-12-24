from datetime import datetime, timezone

import pytest

from app.repositories.server_colors import ServerColorRepository


class FakeDatabase:
    def __init__(self):
        self.data: dict[int, dict[str, object]] = {}

    async def fetchrow(self, query: str, *args):
        if "INSERT INTO server_colors" in query:
            guild_id, color_value = args
            record = {
                "guild_id": guild_id,
                "color_value": color_value,
                "created_at": datetime.now(timezone.utc),
            }
            self.data[guild_id] = record
            return record
        if "WHERE guild_id" in query:
            guild_id = args[0]
            return self.data.get(guild_id)
        raise AssertionError("unexpected fetchrow query")

    async def fetch(self, query: str, *args):
        if "FROM server_colors" in query:
            return list(self.data.values())
        raise AssertionError("unexpected fetch query")

    async def execute(self, query: str, *args):
        return "OK"


@pytest.mark.asyncio
async def test_save_and_get_color_roundtrip():
    repo = ServerColorRepository(FakeDatabase())

    saved = await repo.save_color(10, 0xABCDEF)
    fetched = await repo.get_color(10)

    assert saved.guild_id == 10
    assert saved.color_value == 0xABCDEF
    assert fetched is not None
    assert fetched.color_value == saved.color_value


@pytest.mark.asyncio
async def test_get_all_colors_returns_sorted_records():
    db = FakeDatabase()
    repo = ServerColorRepository(db)
    await repo.save_color(2, 0x010101)
    await repo.save_color(1, 0x020202)

    all_colors = await repo.get_all_colors()

    assert [c.guild_id for c in all_colors] == [2, 1]
