from __future__ import annotations

import logging

import discord

from app.repositories import ChannelNicknameRule

LOGGER = logging.getLogger(__name__)
ROLE_ASSIGN_REASON = "Nickname guard auto assignment"


async def enforce_nickname_and_role(message: discord.Message, rule: ChannelNicknameRule) -> None:
    """メッセージをニックネームに揃え、指定ロールを付与する。"""

    guild = message.guild
    author = message.author

    if guild is None:
        return

    display_name = _resolve_display_name(author)
    if display_name and message.content != display_name:
        try:
            await message.edit(content=display_name, allowed_mentions=discord.AllowedMentions.none())
            LOGGER.info("メッセージをニックネームに更新しました: guild=%s channel=%s user=%s", guild.id, message.channel.id, author.id)
        except (discord.Forbidden, discord.HTTPException) as exc:
            LOGGER.warning(
                "メッセージ編集に失敗しました: guild=%s channel=%s user=%s error=%s",
                guild.id,
                message.channel.id,
                author.id,
                exc,
            )

    role = guild.get_role(rule.role_id)
    if role is None:
        LOGGER.warning(
            "ロールが見つかりません。設定を再確認してください: guild=%s role_id=%s",
            guild.id,
            rule.role_id,
        )
        return

    member_roles = getattr(author, "roles", [])
    if role in member_roles:
        return

    try:
        await author.add_roles(role, reason=ROLE_ASSIGN_REASON)
        LOGGER.info("ロールを付与しました: guild=%s role=%s user=%s", guild.id, role.id, author.id)
    except (discord.Forbidden, discord.HTTPException) as exc:
        LOGGER.warning(
            "ロール付与に失敗しました: guild=%s role=%s user=%s error=%s",
            guild.id,
            role.id,
            author.id,
            exc,
        )


def _resolve_display_name(member: discord.abc.User | discord.Member) -> str:
    return (
        getattr(member, "display_name", None)
        or getattr(member, "global_name", None)
        or getattr(member, "name", None)
        or ""
    )


__all__ = ["enforce_nickname_and_role"]
