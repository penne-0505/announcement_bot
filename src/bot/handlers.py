from __future__ import annotations

import logging

import discord

from app.repositories import ChannelNicknameRule

LOGGER = logging.getLogger(__name__)
ROLE_ASSIGN_REASON = "Nickname guard auto assignment"
NICKNAME_CHANGE_REASON = "Nickname sync from message content"


async def enforce_nickname_and_role(
    message: discord.Message, rule: ChannelNicknameRule
) -> None:
    """投稿本文をニックネームとして適用し、指定ロールを付与する。"""

    guild = message.guild
    author = message.author

    # ギルド外や Member でない場合（例: 退会済み）はスキップ
    if guild is None or not isinstance(author, discord.Member):
        return

    # --- ニックネーム変更 ---
    new_nickname = message.content.strip()

    if not new_nickname:
        LOGGER.warning(
            "空のメッセージのためニックネーム変更をスキップしました: user=%s", author.id
        )
    elif len(new_nickname) > 32:
        LOGGER.warning(
            "文字数超過のためニックネーム変更をスキップしました: user=%s length=%s",
            author.id,
            len(new_nickname),
        )
        try:
            await message.add_reaction("❌")
        except Exception:
            pass
    elif author.display_name != new_nickname:
        try:
            await author.edit(nick=new_nickname, reason=NICKNAME_CHANGE_REASON)
            LOGGER.info(
                "ニックネームを変更しました: guild=%s user=%s new_nick=%s",
                guild.id,
                author.id,
                new_nickname,
            )
            try:
                await message.add_reaction("✅")
            except Exception:
                pass
        except discord.Forbidden:
            LOGGER.warning(
                "ニックネーム変更権限がありません（対象ユーザーがBotより上位の可能性があります）: guild=%s user=%s",
                guild.id,
                author.id,
            )
        except discord.HTTPException as exc:
            LOGGER.error(
                "ニックネーム変更中にAPIエラーが発生しました: guild=%s user=%s error=%s",
                guild.id,
                author.id,
                exc,
            )

    # --- ロール付与（既存ロジックを踏襲） ---
    role = guild.get_role(rule.role_id)
    if role is None:
        LOGGER.warning(
            "付与対象ロールが見つかりません。設定を確認してください: guild=%s role_id=%s",
            guild.id,
            rule.role_id,
        )
        return

    if role in author.roles:
        return

    try:
        await author.add_roles(role, reason=ROLE_ASSIGN_REASON)
        LOGGER.info(
            "ロールを付与しました: guild=%s role=%s user=%s",
            guild.id,
            role.id,
            author.id,
        )
    except (discord.Forbidden, discord.HTTPException) as exc:
        LOGGER.warning(
            "ロール付与に失敗しました: guild=%s role=%s user=%s error=%s",
            guild.id,
            role.id,
            author.id,
            exc,
        )


__all__ = ["enforce_nickname_and_role"]
