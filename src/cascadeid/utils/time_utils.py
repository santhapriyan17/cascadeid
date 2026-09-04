"""
cascadeid.utils.time_utils

Timestamp and window-boundary utilities.

All functions work with timezone-aware datetimes (UTC).
Naive datetimes are rejected to prevent subtle bugs in replay mode.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta


def utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime) -> datetime:
    """
    Ensure a datetime is timezone-aware (UTC).
    Raises ValueError for naive datetimes.
    """
    if dt.tzinfo is None:
        raise ValueError(
            f"Naive datetime received: {dt!r}. "
            "All timestamps must be timezone-aware (UTC)."
        )
    return dt.astimezone(timezone.utc)


def floor_to_window(
    timestamp: datetime,
    window_size_seconds: int,
    epoch: datetime | None = None,
) -> datetime:
    """
    Floor a timestamp to the start of its containing window.

    Args:
        timestamp: The event timestamp (timezone-aware).
        window_size_seconds: Window duration in seconds.
        epoch: Reference start point (default: 2015-07-30 UTC, Ethereum genesis).

    Returns:
        The window start time (timezone-aware UTC).
    """
    if epoch is None:
        epoch = datetime(2015, 7, 30, tzinfo=timezone.utc)  # Ethereum genesis

    ts = ensure_utc(timestamp)
    ep = ensure_utc(epoch)

    elapsed = (ts - ep).total_seconds()
    if elapsed < 0:
        raise ValueError(
            f"Timestamp {ts} is before epoch {ep}. "
            "Check chain and timestamp configuration."
        )

    window_index = int(elapsed // window_size_seconds)
    window_start = ep + timedelta(seconds=window_index * window_size_seconds)
    return window_start


def window_index_of(
    timestamp: datetime,
    window_size_seconds: int,
    epoch: datetime | None = None,
) -> int:
    """
    Return the 0-based window index for a given timestamp.

    Args:
        timestamp: Event timestamp (timezone-aware).
        window_size_seconds: Window duration in seconds.
        epoch: Reference epoch (default: Ethereum genesis).

    Returns:
        Non-negative integer window index.
    """
    if epoch is None:
        epoch = datetime(2015, 7, 30, tzinfo=timezone.utc)

    ts = ensure_utc(timestamp)
    ep = ensure_utc(epoch)

    elapsed = (ts - ep).total_seconds()
    if elapsed < 0:
        raise ValueError(f"Timestamp {ts} is before epoch {ep}")

    return int(elapsed // window_size_seconds)


def window_boundaries(
    window_index: int,
    window_size_seconds: int,
    epoch: datetime | None = None,
) -> tuple[datetime, datetime]:
    """
    Return (start, end) boundaries for a given window index.
    End is exclusive (the start of the next window).
    """
    if epoch is None:
        epoch = datetime(2015, 7, 30, tzinfo=timezone.utc)

    ep = ensure_utc(epoch)
    start = ep + timedelta(seconds=window_index * window_size_seconds)
    end = start + timedelta(seconds=window_size_seconds)
    return start, end


def elapsed_seconds(t_start: datetime, t_end: datetime) -> float:
    """
    Elapsed time between two timezone-aware datetimes in seconds.
    Returns a non-negative float.
    """
    ts = ensure_utc(t_start)
    te = ensure_utc(t_end)
    delta = (te - ts).total_seconds()
    return max(delta, 0.0)


def windows_between(
    t_start: datetime,
    t_end: datetime,
    window_size_seconds: int,
    epoch: datetime | None = None,
) -> list[int]:
    """
    Return all window indices that overlap with [t_start, t_end).
    Useful for determining which windows are affected by a batch of events.
    """
    start_idx = window_index_of(t_start, window_size_seconds, epoch)
    # t_end is exclusive, so subtract 1 second to get last inclusive idx
    end_inclusive = t_end - timedelta(seconds=1)
    end_idx = window_index_of(end_inclusive, window_size_seconds, epoch)
    return list(range(start_idx, end_idx + 1))