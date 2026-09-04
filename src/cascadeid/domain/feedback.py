"""
cascadeid.domain.feedback

AnalystFeedback: validated analyst label on a detection result.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

from cascadeid.domain.enums import FeedbackLabel

_now = lambda: datetime.now(timezone.utc)


class AnalystFeedback(BaseModel):
    feedback_id: str

    cluster_id: str | None = Field(default=None)
    wallet_ids: list[str] = Field(default_factory=list)

    label: FeedbackLabel
    reason: str = Field(default="", max_length=1024)
    notes: str = Field(default="", max_length=2048)

    evidence_snapshot: dict = Field(default_factory=dict)
    feature_snapshot: dict = Field(default_factory=dict)
    temporal_fingerprint_snapshot: dict = Field(default_factory=dict)

    detector_version: str = Field(default="0.1.0")
    configuration_version: str = Field(default="0.1.0")

    analyst_id: str | None = Field(default=None)
    submitted_at: datetime = Field(default_factory=_now)

    is_validated: bool = Field(default=False)
    validation_notes: str = Field(default="")

    model_config = {"frozen": True}

    @field_validator("reason", "notes", mode="before")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v