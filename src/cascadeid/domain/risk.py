"""
cascadeid.domain.risk

RiskResult, ConfidenceResult, EvidenceItem.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from cascadeid.domain.enums import (
    CoordinationStatus,
    DataQuality,
    EvidenceCategory,
    TemporalStabilityLevel,
)

_now = lambda: datetime.now(timezone.utc)


class EvidenceItem(BaseModel):
    category: EvidenceCategory
    description: str = Field(..., max_length=512)
    supporting_value: float | None = Field(default=None)
    weight: float = Field(default=1.0, ge=0.0)
    wallet_ids_involved: list[str] = Field(default_factory=list)
    observed_at: datetime | None = Field(default=None)

    model_config = {"frozen": True}


class ConfidenceResult(BaseModel):
    confidence_score: float = Field(..., ge=0.0, le=1.0)

    observation_sufficiency: float | None = Field(default=None, ge=0.0, le=1.0)
    temporal_coverage: float | None = Field(default=None, ge=0.0, le=1.0)
    feature_completeness: float | None = Field(default=None, ge=0.0, le=1.0)
    graph_support: float | None = Field(default=None, ge=0.0, le=1.0)

    data_quality: DataQuality = Field(default=DataQuality.MEDIUM)
    temporal_stability: TemporalStabilityLevel = Field(
        default=TemporalStabilityLevel.INSUFFICIENT
    )

    model_config = {"frozen": True}


class RiskResult(BaseModel):
    subject_id: str
    subject_type: str

    coordination_risk: float = Field(..., ge=0.0, le=1.0)
    confidence_result: ConfidenceResult

    status: CoordinationStatus = Field(default=CoordinationStatus.UNKNOWN)
    evidence_items: list[EvidenceItem] = Field(default_factory=list)

    behavioral_score: float | None = Field(default=None)
    temporal_score: float | None = Field(default=None)
    graph_score: float | None = Field(default=None)
    information_score: float | None = Field(default=None)

    previous_status: CoordinationStatus | None = Field(default=None)
    status_changed: bool = Field(default=False)

    model_version: str = Field(default="0.1.0")
    computed_at: datetime = Field(default_factory=_now)

    model_config = {"frozen": True}