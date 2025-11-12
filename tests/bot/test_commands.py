import types

import pytest

from bot import register_commands
from views import NicknameSyncSetupView, SendModalView


class FakeResponse:
    def __init__(self) -> None:
        self.deferred_ephemeral: bool | None = None
        self.sent: list[dict[str, object]] = []

    async def defer(self, *, ephemeral: bool = False) -> None:
        self.deferred_ephemeral = ephemeral

    async def send_message(self, content: str, *, view=None, ephemeral: bool = False) -> None:
        self.sent.append({"content": content, "view": view, "ephemeral": ephemeral})


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


@pytest.mark.asyncio
async def test_nickname_sync_setup_command_returns_view() -> None:
    tree = FakeCommandTree()
    client = types.SimpleNamespace(tree=tree)
    rule_store = object()

    await register_commands(client, rule_store=rule_store)
    assert "nickname_sync_setup" in tree.registered

    interaction = FakeInteraction(guild_id=999, user_id=123)
    await tree.registered["nickname_sync_setup"]["callback"](interaction)

    assert interaction.response.sent[0]["ephemeral"] is True
    view = interaction.response.sent[0]["view"]
    assert isinstance(view, NicknameSyncSetupView)
    assert view.executor_id == 123
    assert view.guild_id == 999
