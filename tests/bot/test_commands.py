import types
from datetime import datetime

import pytest

from bot import register_commands
from app.repositories import TemporaryVoiceCategory
from app.services import (
    CategoryNotConfiguredError,
    CategoryUpdateResult,
    TemporaryVoiceChannelNotFoundError,
)
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
        self.guild = types.SimpleNamespace(id=guild_id)
        self.response = FakeResponse()
        self.followup = FakeFollowup()


class FakeCommandTree:
    def __init__(self) -> None:
        self.registered: dict[str, dict[str, object]] = {}
        self.groups: dict[str, object] = {}

    def command(self, *, name: str, description: str):  # noqa: D401 - discord 互換API
        def decorator(func):
            self.registered[name] = {"callback": func, "description": description}
            return func

        return decorator

    def add_command(self, command) -> None:  # noqa: D401 - discord 互換API
        self.groups[command.name] = command


class FakeTemporaryVoiceService:
    def __init__(self) -> None:
        self.category_calls: list[tuple[object, object, int]] = []
        self.create_calls: list[object] = []
        self.reset_calls: list[object] = []
        self.create_error: Exception | None = None
        self.reset_error: Exception | None = None
        self.create_result = types.SimpleNamespace(mention="<#999>")

    async def configure_category(self, guild, category, executor_id: int) -> CategoryUpdateResult:
        self.category_calls.append((guild, category, executor_id))
        entity = TemporaryVoiceCategory(
            guild_id=guild.id,
            category_id=category.id,
            updated_by=executor_id,
            updated_at=datetime.now(),
        )
        return CategoryUpdateResult(category=entity, deleted_channel_ids=[1, 2], missing_channel_ids=[])

    async def create_temporary_channel(self, member):
        self.create_calls.append(member)
        if self.create_error is not None:
            error = self.create_error
            self.create_error = None
            raise error
        return self.create_result

    async def reset_temporary_channel(self, member):
        self.reset_calls.append(member)
        if self.reset_error is not None:
            error = self.reset_error
            self.reset_error = None
            raise error


@pytest.mark.asyncio
async def test_register_commands_registers_setup_and_sends_view() -> None:
    tree = FakeCommandTree()
    client = types.SimpleNamespace(tree=tree)
    rule_store = types.SimpleNamespace()
    voice_service = FakeTemporaryVoiceService()

    await register_commands(client, rule_store=rule_store, temporary_voice_service=voice_service)
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
    voice_service = FakeTemporaryVoiceService()

    await register_commands(client, rule_store=rule_store, temporary_voice_service=voice_service)
    assert "nickname_sync_setup" in tree.registered

    interaction = FakeInteraction(guild_id=999, user_id=123)
    await tree.registered["nickname_sync_setup"]["callback"](interaction)

    assert interaction.response.sent[0]["ephemeral"] is True
    view = interaction.response.sent[0]["view"]
    assert isinstance(view, NicknameSyncSetupView)
    assert view.executor_id == 123
    assert view.guild_id == 999


def _get_group_command(tree: FakeCommandTree, name: str):
    group = tree.groups.get("temporary_vc")
    assert group is not None
    for command in group.commands:
        if command.name == name:
            return command
    raise AssertionError(f"command {name} not found")


@pytest.mark.asyncio
async def test_temporary_vc_category_command_configures_category() -> None:
    tree = FakeCommandTree()
    client = types.SimpleNamespace(tree=tree)
    voice_service = FakeTemporaryVoiceService()

    await register_commands(client, rule_store=types.SimpleNamespace(), temporary_voice_service=voice_service)

    command = _get_group_command(tree, "category")
    interaction = FakeInteraction(guild_id=5, user_id=42)
    category = types.SimpleNamespace(id=50, mention="<#50>")

    await command.callback(interaction, category)

    assert interaction.response.deferred_ephemeral is True
    assert interaction.followup.sent[0]["ephemeral"] is True
    assert voice_service.category_calls[0][2] == 42


@pytest.mark.asyncio
async def test_temporary_vc_create_command_handles_success() -> None:
    tree = FakeCommandTree()
    client = types.SimpleNamespace(tree=tree)
    voice_service = FakeTemporaryVoiceService()
    await register_commands(client, rule_store=types.SimpleNamespace(), temporary_voice_service=voice_service)

    command = _get_group_command(tree, "create")
    interaction = FakeInteraction(guild_id=5, user_id=77)

    await command.callback(interaction)

    assert interaction.response.sent[0]["content"].startswith("✅")
    assert len(voice_service.create_calls) == 1


@pytest.mark.asyncio
async def test_temporary_vc_create_command_handles_missing_category() -> None:
    tree = FakeCommandTree()
    client = types.SimpleNamespace(tree=tree)
    voice_service = FakeTemporaryVoiceService()
    voice_service.create_error = CategoryNotConfiguredError("missing")
    await register_commands(client, rule_store=types.SimpleNamespace(), temporary_voice_service=voice_service)

    command = _get_group_command(tree, "create")
    interaction = FakeInteraction(guild_id=5, user_id=77)

    await command.callback(interaction)

    assert "カテゴリ" in interaction.response.sent[0]["content"]


@pytest.mark.asyncio
async def test_temporary_vc_reset_handles_not_found() -> None:
    tree = FakeCommandTree()
    client = types.SimpleNamespace(tree=tree)
    voice_service = FakeTemporaryVoiceService()
    voice_service.reset_error = TemporaryVoiceChannelNotFoundError("not found")
    await register_commands(client, rule_store=types.SimpleNamespace(), temporary_voice_service=voice_service)

    command = _get_group_command(tree, "reset")
    interaction = FakeInteraction(guild_id=5, user_id=77)

    await command.callback(interaction)

    assert "登録されていません" in interaction.response.sent[0]["content"]
