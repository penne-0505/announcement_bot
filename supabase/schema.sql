-- Supabase initialization schema for announcement-bot
-- Run this in Supabase SQL Editor before starting the bot.

CREATE TABLE IF NOT EXISTS channel_nickname_rules (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    updated_by BIGINT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS temporary_vc_categories (
    guild_id BIGINT PRIMARY KEY,
    category_id BIGINT NOT NULL,
    updated_by BIGINT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS temporary_voice_channels (
    guild_id BIGINT NOT NULL,
    owner_user_id BIGINT NOT NULL,
    channel_id BIGINT,
    category_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, owner_user_id)
);
