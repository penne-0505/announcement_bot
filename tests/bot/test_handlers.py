import types
from datetime import datetime

import pytest

from app.repositories import ChannelNicknameRule
from bot import handlers as handlers_module
from bot.handlers import enforce_nickname_and_role


class FakeRole:
    def __init__(self, role_id: int = 1) -> None:
        self.id = role_id
        self.mention = f"<@&{role_id}>"


class FakeMember:
    def __init__(self, *, display_name: str = "Tester", member_id: int = 42) -> None:
        self.display_name = display_name
        self.roles: list[FakeRole] = []
        self.id = member_id
        self.bot = False
        self.added: list[tuple[FakeRole, str | None]] = []
        self.edits: list[tuple[str | None, str | None]] = []

    async def add_roles(self, role: FakeRole, *, reason: str | None = None) -> None:
        self.roles.append(role)
        self.added.append((role, reason))

    async def edit(self, *, nick: str | None = None, reason: str | None = None) -> None:
        if nick is not None:
            self.display_name = nick
        self.edits.append((nick, reason))

# handlers モジュール内の isinstance チェックをテスト用スタブに通す
handlers_module.discord.Member = FakeMember  # type: ignore[attr-defined]


class FakeGuild:
    def __init__(self, guild_id: int = 1, role: FakeRole | None = None) -> None:
        self.id = guild_id
        self._role = role

    def get_role(self, role_id: int) -> FakeRole | None:
        if self._role and self._role.id == role_id:
            return self._role
        return None


class FakeMessage:
    def __init__(self, member: FakeMember, guild: FakeGuild, *, content: str = "original") -> None:
        self.guild = guild
        self.author = member
        self.channel = types.SimpleNamespace(id=99)
        self.content = content
        self.reactions: list[str] = []

    async def add_reaction(self, emoji: str) -> None:  # noqa: D401 - discord 互換
        self.reactions.append(emoji)


@pytest.mark.asyncio
async def test_enforce_updates_nickname_and_assigns_role() -> None:
    role = FakeRole(role_id=50)
    member = FakeMember(display_name="OldNick")
    guild = FakeGuild(guild_id=777, role=role)
    message = FakeMessage(member, guild, content="  NewNick  ")
    rule = ChannelNicknameRule(
        guild_id=777,
        channel_id=99,
        role_id=50,
        updated_by=1,
        updated_at=datetime.now(),
    )

    await enforce_nickname_and_role(message, rule)

    assert member.display_name == "NewNick"
    assert member.edits[0][0] == "NewNick"
    assert member.roles[0] is role
    assert member.added[0][1] is not None
    assert "✅" in message.reactions


@pytest.mark.asyncio
async def test_enforce_skips_when_role_missing() -> None:
    member = FakeMember(display_name="Nick")
    guild = FakeGuild(guild_id=1, role=None)
    message = FakeMessage(member, guild, content="NickName")
    rule = ChannelNicknameRule(
        guild_id=1,
        channel_id=99,
        role_id=999,
        updated_by=1,
        updated_at=datetime.now(),
    )

    await enforce_nickname_and_role(message, rule)

    assert member.roles == []
    assert member.display_name == "NickName"
    assert "✅" in message.reactions


@pytest.mark.asyncio
async def test_enforce_skips_nickname_change_when_already_matches() -> None:
    role = FakeRole(role_id=70)
    member = FakeMember(display_name="SameName")
    guild = FakeGuild(guild_id=2, role=role)
    message = FakeMessage(member, guild, content="SameName")
    rule = ChannelNicknameRule(
        guild_id=2,
        channel_id=99,
        role_id=70,
        updated_by=1,
        updated_at=datetime.now(),
    )

    await enforce_nickname_and_role(message, rule)

    assert member.edits == []
    assert member.roles[0] is role
    assert message.reactions == []


@pytest.mark.asyncio
async def test_enforce_skips_role_assignment_if_member_already_has_role() -> None:
    role = FakeRole(role_id=88)
    member = FakeMember(display_name="NewNick")
    member.roles.append(role)
    guild = FakeGuild(guild_id=5, role=role)
    message = FakeMessage(member, guild, content="NewNick")
    rule = ChannelNicknameRule(
        guild_id=5,
        channel_id=99,
        role_id=88,
        updated_by=1,
        updated_at=datetime.now(),
    )

    await enforce_nickname_and_role(message, rule)

    assert member.added == []
    assert message.reactions == []


@pytest.mark.asyncio
async def test_enforce_skips_when_message_too_long() -> None:
    role = FakeRole(role_id=101)
    member = FakeMember(display_name="Old")
    guild = FakeGuild(guild_id=9, role=role)
    message = FakeMessage(member, guild, content="x" * 33)
    rule = ChannelNicknameRule(
        guild_id=9,
        channel_id=99,
        role_id=101,
        updated_by=1,
        updated_at=datetime.now(),
    )

    await enforce_nickname_and_role(message, rule)

    assert member.display_name == "Old"
    assert "❌" in message.reactions
    assert member.roles[0] is role
