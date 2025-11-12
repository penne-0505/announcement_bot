import types

import pytest

from bot import register_commands
from views import SendModalView


class FakeResponse:
    def __init__(self) -> None:
        self.deferred_ephemeral: bool | None = None
        self.sent: list[dict[str, object]] = []

    async def defer(self, *, ephemeral: bool = False) -> None:
        self.deferred_ephemeral = ephemeral

    async def send_message(self, content: str, *, ephemeral: bool = False) -> None:
        self.sent.append({"content": content, "ephemeral": ephemeral})


class FakeFollowup:
    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []

    async def send(self, content: str, *, view=None, ephemeral: bool = False) -> None:
        self.sent.append({"content": content, "view": view, "ephemeral": ephemeral})


class FakeInteraction:
    def __init__(self, *, guild_id: int = 1, user_id: int = 10) -> None:
        self.user = types.SimpleNamespace(id=user_id)
        self.guild_id = guild_id
        self.response = FakeResponse()
        self.followup = FakeFollowup()


class FakeCommandTree:
    def __init__(self) -> None:
        self.registered: dict[str, dict[str, object]] = {}

    def command(self, *, name: str, description: str):  # noqa: D401 - discord 互換API
        def decorator(func):
            self.registered[name] = {"callback": func, "description": description}
            return func

        return decorator


@pytest.mark.asyncio
async def test_register_commands_registers_setup_and_sends_view() -> None:
    tree = FakeCommandTree()
    client = types.SimpleNamespace(tree=tree)
    rule_store = types.SimpleNamespace()

    await register_commands(client, rule_store=rule_store)
    assert "setup" in tree.registered

    interaction = FakeInteraction()
    await tree.registered["setup"]["callback"](interaction)

    assert interaction.response.deferred_ephemeral is True
    assert interaction.followup.sent[0]["ephemeral"] is True
    assert isinstance(interaction.followup.sent[0]["view"], SendModalView)


class FakeChannel:
    def __init__(self, guild_id: int = 1, channel_id: int = 50) -> None:
        self.id = channel_id
        self.guild = types.SimpleNamespace(id=guild_id)
        self.mention = f"<#{channel_id}>"


class FakeRole:
    def __init__(self, guild_id: int = 1, role_id: int = 70) -> None:
        self.id = role_id
        self.guild = types.SimpleNamespace(id=guild_id)
        self.mention = f"<@&{role_id}>"


class FakeRuleStore:
    def __init__(self) -> None:
        self.calls: list[dict[str, int]] = []

    async def upsert_rule(self, guild_id: int, channel_id: int, role_id: int, updated_by: int):
        self.calls.append(
            {
                "guild_id": guild_id,
                "channel_id": channel_id,
                "role_id": role_id,
                "updated_by": updated_by,
            }
        )


@pytest.mark.asyncio
async def test_nickname_guard_command_invokes_rule_store_and_replies_ephemeral() -> None:
    tree = FakeCommandTree()
    client = types.SimpleNamespace(tree=tree)
    rule_store = FakeRuleStore()

    await register_commands(client, rule_store=rule_store)

    interaction = FakeInteraction(guild_id=999, user_id=123)
    channel = FakeChannel(guild_id=999, channel_id=456)
    role = FakeRole(guild_id=999, role_id=777)

    await tree.registered["nickname_guard"]["callback"](interaction, channel, role)

    assert rule_store.calls[0] == {
        "guild_id": 999,
        "channel_id": 456,
        "role_id": 777,
        "updated_by": 123,
    }
    assert interaction.response.sent[0]["ephemeral"] is True
