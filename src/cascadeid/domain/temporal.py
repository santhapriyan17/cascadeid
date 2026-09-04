"""
cascadeid.domain.temporal

TemporalWindow: a bounded time interval assigned to one wallet.
WindowKey: compact identifier for (wallet_id, window_index).

Window boundaries are determined entirely by configuration
(window_size, window_stride) and never by the data itself,
ensuring reproducibility and no look-ahead.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class WindowKey(BaseModel):
    """Compact, hashable identifier for a (wallet, window) pair."""

    wallet_id: str
    window_index: int  # 0-based, monotonically increasing

    model_config = {"frozen": True}

    def __str__(self) -> str:
        return f"{self.wallet_id}@w{self.window_index}"


class TemporalWindow(BaseModel):
    """
    A completed temporal window for one wallet.

    A window is 'complete' when its end boundary has passed and
    no further events can fall within it (enforced by the windowing engine).
    Incomplete windows are never used for correlation.
    """

    key: WindowKey

    # Boundaries (UTC, exclusive end)
    start_time: datetime
    end_time: datetime

    # Observation count within window
    transaction_count: int = Field(default=0, ge=0)

    # Whether this window meets minimum observation threshold
    is_valid: bool = Field(default=False)

    # Raw aggregates needed for feature calculation
    # (stored here so feature engine doesn't need to re-query transactions)
    total_value_eth: float = Field(default=0.0)
    unique_counterparties: int = Field(default=0)
    unique_contracts: int = Field(default=0)
    unique_tokens: int = Field(default=0)
    total_gas_fee_eth: float = Field(default=0.0)
    timestamps_seconds: list[float] = Field(default_factory=list)

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def end_after_start(self) -> "TemporalWindow":
        if self.end_time <= self.start_time:
            raise ValueError(
                f"Window end_time {self.end_time} must be after start_time {self.start_time}"
            )
        return self

    @property
    def duration_seconds(self) -> float:
        return (self.end_time - self.start_time).total_seconds()