from __future__ import annotations

from datetime import datetime, timezone


def ensure_utc_timestamp(value: str | datetime | None) -> datetime:
    """Convert stored timestamps into timezone-aware UTC datetimes."""

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    if value is None:
        return datetime.now(timezone.utc)

    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
