"""
cascadeid.domain.graph

WalletNode: a wallet as it appears in the coordination graph.
CoordinationEdge: an evidence-bearing edge between two wallets.

Edges are only created when evidence meets configured thresholds.
They carry all the evidence that justifies their existence.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from cascadeid.domain.enums import Direction


class WalletNode(BaseModel):
    """Graph node representing a wallet."""

    wallet_id: str
    address: str
    chain_id: int

    # Denormalised for graph rendering
    transaction_count: int = Field(default=0)
    current_status: str = Field(default="UNKNOWN")
    current_risk: float | None = Field(default=None)
    current_confidence: float | None = Field(default=None)

    model_config = {"frozen": True}


class CoordinationEdge(BaseModel):
    """
    Evidence-bearing directed edge between wallet_id_a and wallet_id_b.

    This edge only exists because specific computed evidence justifies it.
    All evidence attributes are populated from actual correlation results —
    never fabricated defaults.
    """

    wallet_id_a: str
    wallet_id_b: str

    # Core evidence
    coordination_score: float = Field(..., ge=0.0, le=1.0)
    best_lag: int | None = Field(default=None)
    lag_stability: float | None = Field(default=None, ge=0.0, le=1.0)
    repeated_alignment: int = Field(default=0, ge=0)
    direction: Direction = Field(default=Direction.UNDETERMINED)

    # Supporting evidence
    behavioral_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    overlap_count: int = Field(default=0, ge=0)
    information_score: float | None = Field(default=None)

    # Quality
    confidence: float = Field(..., ge=0.0, le=1.0)
    data_quality: str = Field(default="MEDIUM")

    # Freshness
    evidence_age_seconds: float | None = Field(default=None)
    first_observed: datetime | None = Field(default=None)
    last_observed: datetime | None = Field(default=None)

    model_config = {"frozen": True}

    @property
    def edge_key(self) -> tuple[str, str]:
        """Canonical edge key: (min_id, max_id) for undirected lookup."""
        return (min(self.wallet_id_a, self.wallet_id_b),
                max(self.wallet_id_a, self.wallet_id_b))