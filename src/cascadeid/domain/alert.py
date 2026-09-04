"""
cascadeid.domain.alert

Alert: a detection result that crosses the configured risk threshold.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from cascadeid.domain.enums import AlertStatus, CoordinationStatus

_now = lambda: datetime.now(timezone.utc)


class Alert(BaseModel):
    alert_id: str
    subject_id: str
    subject_type: str

    status: AlertStatus = Field(default=AlertStatus.OPEN)
    coordination_risk: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    coordination_status: CoordinationStatus

    evidence_snapshot: list[dict] = Field(default_factory=list)

    wallet_count: int | None = Field(default=None)
    dominant_lag: int | None = Field(default=None)
    lag_stability: float | None = Field(default=None)
    repeated_alignment: int | None = Field(default=None)

    detector_version: str = Field(default="0.1.0")

    created_at: datetime = Field(default_factory=_now)
    closed_at: datetime | None = Field(default=None)
    reviewed_at: datetime | None = Field(default=None)
    reviewed_by: str | None = Field(default=None)

    model_config = {"frozen": False}