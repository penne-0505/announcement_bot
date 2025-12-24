from __future__ import annotations

import logging

import discord
from discord.abc import Messageable

LOGGER = logging.getLogger(__name__)


class SendModalView(discord.ui.View):
    """セットアップメッセージに添付される送信モーダル用ビュー。"""

    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(_SendModalButton())


class _SendModalButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="メッセージ送信", style=discord.ButtonStyle.primary)

    async def callback(
        self, interaction: discord.Interaction
    ) -> None:  # pragma: no cover - UI コールバック
        await interaction.response.send_modal(SendMessageModal())


class SendMessageModal(discord.ui.Modal, title="メッセージ送信"):
    channel_id = discord.ui.TextInput(
        label="チャンネルID",
        placeholder="送信先チャンネルのIDを入力",
        required=True,
    )
    message = discord.ui.TextInput(
        label="本文",
        style=discord.TextStyle.paragraph,
        placeholder="メッセージ内容を入力",
        required=True,
    )

    ERROR_INVALID_ID = "チャンネルIDは有効な整数である必要があります。"
    ERROR_CHANNEL_NOT_FOUND = (
        "チャンネルが見つかりません。Botがアクセスできるか確認してください。"
    )
    SUCCESS_MESSAGE = "<#{channel_id}> にメッセージを送信しました。"
    ERROR_GENERAL = "エラー: {error}"

    async def on_submit(
        self, interaction: discord.Interaction
    ) -> None:  # pragma: no cover - UI コールバック
        await process_modal_submission(
            interaction,
            channel_id_value=self.channel_id.value,
            message_value=self.message.value,
        )


async def process_modal_submission(
    interaction: discord.Interaction,
    *,
    channel_id_value: str | None,
    message_value: str | None,
) -> None:
    """モーダルから渡された入力値を検証し、必要に応じて送信する。"""

    try:
        channel_id_int = int(channel_id_value or "")
    except ValueError:
        await interaction.response.send_message(
            SendMessageModal.ERROR_INVALID_ID, ephemeral=True
        )
        return

    try:
        channel = interaction.client.get_channel(channel_id_int)
        if channel is None:
            try:
                channel = await interaction.client.fetch_channel(channel_id_int)
            except discord.NotFound:
                await interaction.response.send_message(
                    SendMessageModal.ERROR_CHANNEL_NOT_FOUND,
                    ephemeral=True,
                )
                return
            except discord.HTTPException as exc:
                await interaction.response.send_message(
                    SendMessageModal.ERROR_GENERAL.format(error=str(exc)),
                    ephemeral=True,
                )
                return

        if not isinstance(channel, Messageable):
            await interaction.response.send_message(
                SendMessageModal.ERROR_CHANNEL_NOT_FOUND,
                ephemeral=True,
            )
            return

        color = await _resolve_embed_color(interaction, channel)
        embed = discord.Embed(
            description=message_value or "",
            color=color or discord.Color.default(),
        )

        await channel.send(embed=embed)
        await interaction.response.send_message(
            SendMessageModal.SUCCESS_MESSAGE.format(channel_id=channel.id),
            ephemeral=True,
        )
    except Exception as exc:  # pragma: no cover - 想定外エラーの通知
        LOGGER.exception("モーダル送信処理中にエラーが発生しました。")
        await interaction.response.send_message(
            SendMessageModal.ERROR_GENERAL.format(error=str(exc)),
            ephemeral=True,
        )


async def _resolve_embed_color(
    interaction: discord.Interaction,
    channel: Messageable,
) -> discord.Color | None:
    """ギルドIDを推定し、BotClient 経由でカラーを取得する。

    失敗時は None を返してデフォルトカラーにフォールバックする。
    """

    try:
        from bot.client import BotClient
    except Exception:
        return None

    client = interaction.client
    if not isinstance(client, BotClient) or client.color_assignment_service is None:
        return None

    guild_id = None

    channel_guild = getattr(channel, "guild", None)
    if channel_guild is not None:
        guild_id = getattr(channel_guild, "id", None)
    elif getattr(interaction, "guild", None) is not None:
        guild_id = getattr(interaction.guild, "id", None)
    elif getattr(interaction, "guild_id", None) is not None:
        guild_id = interaction.guild_id

    if guild_id is None:
        return None

    try:
        color_value = await client.color_assignment_service.get_or_assign_color(
            int(guild_id)
        )
        return discord.Color(color_value)
    except Exception:
        LOGGER.exception("ギルドカラーの取得に失敗しました: guild_id=%s", guild_id)
        return None


__all__ = ["SendModalView", "SendMessageModal"]
