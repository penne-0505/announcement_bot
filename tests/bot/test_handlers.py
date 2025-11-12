import types
from datetime import datetime

import pytest

from app.repositories import ChannelNicknameRule
from bot.handlers import enforce_nickname_and_role


class FakeRole:
    def __init__(self, role_id: int = 1) -> None:
        self.id = role_id
        self.mention = f"<@&{role_id}>"


class FakeMember:
    def __init__(self, *, display_name: str = "Tester", member_id: int = 42) -> None:
        self.display_name = display_name
        self.global_name = None
        self.name = "tester"
        self.roles: list[FakeRole] = []
        self.id = member_id
        self.bot = False
        self.added: list[tuple[FakeRole, str | None]] = []

    async def add_roles(self, role: FakeRole, *, reason: str | None = None) -> None:
        self.roles.append(role)
        self.added.append((role, reason))


class FakeGuild:
    def __init__(self, guild_id: int = 1, role: FakeRole | None = None) -> None:
        self.id = guild_id
        self._role = role

    def get_role(self, role_id: int) -> FakeRole | None:
        if self._role and self._role.id == role_id:
            return self._role
        return None


class FakeMessage:
    def __init__(self, member: FakeMember, guild: FakeGuild) -> None:
        self.guild = guild
        self.author = member
        self.channel = types.SimpleNamespace(id=99)
        self.content = "original"
        self.edits: list[str] = []

    async def edit(self, *, content: str, allowed_mentions=None) -> None:  # noqa: D401 - discord 互換
        self.content = content
        self.edits.append(content)


@pytest.mark.asyncio
async def test_enforce_updates_message_and_assigns_role() -> None:
    role = FakeRole(role_id=50)
    member = FakeMember(display_name="NewNick")
    guild = FakeGuild(guild_id=777, role=role)
    message = FakeMessage(member, guild)
    rule = ChannelNicknameRule(
        guild_id=777,
        channel_id=99,
        role_id=50,
        updated_by=1,
        updated_at=datetime.now(),
    )

    await enforce_nickname_and_role(message, rule)

    assert message.content == "NewNick"
    assert member.roles[0] is role
    assert member.added[0][1] is not None


@pytest.mark.asyncio
async def test_enforce_skips_when_role_missing() -> None:
    member = FakeMember(display_name="Nick")
    guild = FakeGuild(guild_id=1, role=None)
    message = FakeMessage(member, guild)
    rule = ChannelNicknameRule(
        guild_id=1,
        channel_id=99,
        role_id=999,
        updated_by=1,
        updated_at=datetime.now(),
    )

    await enforce_nickname_and_role(message, rule)

    assert member.roles == []
    assert message.content == "Nick"
