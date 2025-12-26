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
        LOGGER.warning(
            "モーダルのチャンネルIDが不正です: guild=%s user=%s value=%s",
            interaction.guild_id,
            interaction.user.id,
            channel_id_value,
        )
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
                LOGGER.warning(
                    "モーダル送信先チャンネルが見つかりません: guild=%s user=%s channel=%s",
                    interaction.guild_id,
                    interaction.user.id,
                    channel_id_int,
                )
                await interaction.response.send_message(
                    SendMessageModal.ERROR_CHANNEL_NOT_FOUND,
                    ephemeral=True,
                )
                return
            except discord.HTTPException as exc:
                LOGGER.warning(
                    "モーダル送信先チャンネル取得に失敗しました: guild=%s user=%s channel=%s error=%s",
                    interaction.guild_id,
                    interaction.user.id,
                    channel_id_int,
                    exc,
                )
                await interaction.response.send_message(
                    SendMessageModal.ERROR_GENERAL.format(error=str(exc)),
                    ephemeral=True,
                )
                return

        if not isinstance(channel, Messageable):
            LOGGER.warning(
                "モーダル送信先がMessageableではありません: guild=%s user=%s channel=%s",
                interaction.guild_id,
                interaction.user.id,
                channel_id_int,
            )
            await interaction.response.send_message(
                SendMessageModal.ERROR_CHANNEL_NOT_FOUND,
                ephemeral=True,
            )
            return

        message_body = message_value or ""
        await channel.send(message_body)
        await interaction.response.send_message(
            SendMessageModal.SUCCESS_MESSAGE.format(channel_id=channel.id),
            ephemeral=True,
        )
        LOGGER.info(
            "モーダル送信が完了しました: guild=%s user=%s channel=%s length=%s",
            interaction.guild_id,
            interaction.user.id,
            channel.id,
            len(message_body),
        )
    except Exception as exc:  # pragma: no cover - 想定外エラーの通知
        LOGGER.exception("モーダル送信処理中にエラーが発生しました。")
        await interaction.response.send_message(
            SendMessageModal.ERROR_GENERAL.format(error=str(exc)),
            ephemeral=True,
        )


__all__ = ["SendModalView", "SendMessageModal"]
