import types

import pytest

from views.nickname_sync_setup import NicknameSyncSetupView


class RuleStoreStub:
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


class ResponseStub:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def send_message(self, content: str, *, ephemeral: bool = False) -> None:
        self.messages.append({"content": content, "ephemeral": ephemeral})

    async def defer(self, *, ephemeral: bool = False) -> None:  # for select callbacks
        self.messages.append({"deferred": True, "ephemeral": ephemeral})


class InteractionStub:
    def __init__(self, *, user_id: int = 10) -> None:
        self.user = types.SimpleNamespace(id=user_id)
        self.response = ResponseStub()


@pytest.mark.asyncio
async def test_handle_submit_requires_selection() -> None:
    rule_store = RuleStoreStub()
    view = NicknameSyncSetupView(guild_id=1, executor_id=10, rule_store=rule_store)
    interaction = InteractionStub(user_id=10)

    await view._handle_submit(interaction)  # type: ignore[attr-defined]

    assert rule_store.calls == []
    assert interaction.response.messages[0]["content"] == view.ERROR_SELECT_REQUIRED


@pytest.mark.asyncio
async def test_handle_submit_persists_and_finishes() -> None:
    rule_store = RuleStoreStub()
    view = NicknameSyncSetupView(guild_id=123, executor_id=10, rule_store=rule_store)
    view._selected_channel = types.SimpleNamespace(id=50, mention="<#50>")
    view._selected_role = types.SimpleNamespace(id=77, mention="<@&77>")
    interaction = InteractionStub(user_id=10)

    await view._handle_submit(interaction)  # type: ignore[attr-defined]

    assert rule_store.calls[0] == {
        "guild_id": 123,
        "channel_id": 50,
        "role_id": 77,
        "updated_by": 10,
    }
    assert (
        interaction.response.messages[0]["content"]
        == view.SUCCESS_MESSAGE.format(channel="<#50>", role="<@&77>")
    )
    assert view.is_finished()


@pytest.mark.asyncio
async def test_interaction_check_blocks_other_users() -> None:
    rule_store = RuleStoreStub()
    view = NicknameSyncSetupView(guild_id=1, executor_id=10, rule_store=rule_store)
    interaction = InteractionStub(user_id=99)

    allowed = await view.interaction_check(interaction)

    assert allowed is False
    assert interaction.response.messages[0]["content"] == view.ERROR_UNAUTHORIZED
