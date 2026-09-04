"""
cascadeid.domain.cluster

WalletCluster: a community detected in the coordination graph.
ClusterFeatures: aggregate statistics for a cluster.

A community is NOT automatically a Sybil cluster.
Classification requires additional evidence assessment.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from cascadeid.domain.enums import CoordinationStatus, DataQuality


class ClusterFeatures(BaseModel):
    """Aggregate feature statistics computed for a detected community."""

    cluster_id: str

    # Composition
    wallet_count: int = Field(..., ge=1)
    edge_count: int = Field(..., ge=0)
    graph_density: float | None = Field(default=None, ge=0.0, le=1.0)

    # Coordination evidence
    mean_coordination_score: float | None = Field(default=None)
    median_coordination_score: float | None = Field(default=None)
    min_coordination_score: float | None = Field(default=None)
    max_coordination_score: float | None = Field(default=None)

    # Temporal evidence
    dominant_lag: int | None = Field(default=None)
    lag_variance: float | None = Field(default=None)
    lag_stability: float | None = Field(default=None)
    repeated_alignment_total: int = Field(default=0, ge=0)
    mean_alignment_rate: float | None = Field(default=None)

    # Behavioral cohesion
    behavioral_cohesion: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Mean pairwise behavioral similarity within cluster"
    )

    # Quality
    mean_confidence: float | None = Field(default=None)
    data_quality: DataQuality = Field(default=DataQuality.MEDIUM)

    # Freshness
    evidence_age_seconds: float | None = Field(default=None)

    model_config = {"frozen": True}


class WalletCluster(BaseModel):
    """A community of wallets detected in the coordination graph."""

    cluster_id: str
    wallet_ids: list[str] = Field(default_factory=list)
    features: ClusterFeatures | None = Field(default=None)

    # Risk assessment
    coordination_risk: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    status: CoordinationStatus = Field(default=CoordinationStatus.UNKNOWN)

    # Metadata
    algorithm: str = Field(default="louvain")
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}