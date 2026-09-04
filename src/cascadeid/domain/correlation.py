"""
cascadeid.domain.correlation

CorrelationResult: output of a single lag-aware correlation computation.
TemporalFingerprint: accumulated per-pair evidence over multiple windows.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from cascadeid.domain.enums import Direction

_now = lambda: datetime.now(timezone.utc)


class CorrelationResult(BaseModel):
    wallet_id_a: str
    wallet_id_b: str

    is_sufficient: bool = Field(
        ..., description="False → caller must treat as INSUFFICIENT_EVIDENCE"
    )
    best_correlation: float | None = Field(default=None, ge=-1.0, le=1.0)
    best_lag: int | None = Field(default=None)

    lag_correlations: dict[int, float] = Field(default_factory=dict)
    overlap_count: int = Field(default=0, ge=0)

    has_zero_variance: bool = Field(default=False)
    has_constant_vector: bool = Field(default=False)

    computed_at: datetime = Field(default_factory=_now)
    feature_schema_version: str = Field(default="0.1.0")
    lag_range: tuple[int, int] = Field(default=(-5, 5))

    model_config = {"frozen": True}


class TemporalFingerprint(BaseModel):
    wallet_id_a: str
    wallet_id_b: str

    dominant_lag: int | None = Field(default=None)
    lag_variance: float | None = Field(default=None)
    lag_stability: float | None = Field(default=None, ge=0.0, le=1.0)

    alignment_count: int = Field(default=0, ge=0)
    alignment_rate: float | None = Field(default=None)
    repeated_alignment: int = Field(default=0, ge=0)

    direction: Direction = Field(default=Direction.UNDETERMINED)
    direction_consistency: float | None = Field(default=None)

    observation_count: int = Field(default=0, ge=0)
    evidence_age_seconds: float | None = Field(default=None)
    decayed_score: float | None = Field(default=None)

    first_observed: datetime | None = Field(default=None)
    last_observed: datetime | None = Field(default=None)
    last_updated: datetime = Field(default_factory=_now)

    model_config = {"frozen": False}