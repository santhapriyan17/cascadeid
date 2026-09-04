"""
cascadeid.domain.features

BehaviorProfile: full feature vector for one wallet in one window.
BehaviorTransition: the delta between two consecutive BehaviorProfiles (ΔB_i(t)).

BehaviorTransition is the primary signal for CascadeID.
Wallets that undergo similar transitions at different times
are candidates for coordination detection.
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, Field, model_validator


class BehaviorProfile(BaseModel):
    """
    Complete feature vector for wallet w in window t.

    All float fields are finite real numbers.
    NaN and Inf are rejected at construction (enforced by validator).
    None indicates the feature could not be computed (e.g. single observation).
    """

    wallet_id: str
    window_index: int
    feature_schema_version: str = Field(default="0.1.0")

    # ── Activity ──────────────────────────────────────────────────────────
    transaction_count: int = Field(default=0, ge=0)
    activity_rate: float | None = Field(default=None)          # tx / second
    active_window_fraction: float | None = Field(default=None) # [0, 1]

    # ── Economic ──────────────────────────────────────────────────────────
    total_volume_eth: float = Field(default=0.0)
    mean_value_eth: float | None = Field(default=None)
    median_value_eth: float | None = Field(default=None)
    value_variance_eth: float | None = Field(default=None)
    total_gas_fee_eth: float = Field(default=0.0)
    mean_gas_used: float | None = Field(default=None)

    # ── Interaction ────────────────────────────────────────────────────────
    unique_counterparty_count: int = Field(default=0, ge=0)
    counterparty_entropy: float | None = Field(default=None)
    unique_contract_count: int = Field(default=0, ge=0)
    contract_diversity: float | None = Field(default=None)
    unique_token_count: int = Field(default=0, ge=0)
    token_diversity: float | None = Field(default=None)

    # ── Temporal ──────────────────────────────────────────────────────────
    mean_interarrival_seconds: float | None = Field(default=None)
    median_interarrival_seconds: float | None = Field(default=None)
    interarrival_variance: float | None = Field(default=None)
    burstiness: float | None = Field(default=None)
    hour_entropy: float | None = Field(default=None)
    active_window_entropy: float | None = Field(default=None)

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def no_nan_inf(self) -> "BehaviorProfile":
        """Reject NaN and Inf in any float field."""
        for name, value in self.__dict__.items():
            if isinstance(value, float) and not np.isfinite(value):
                raise ValueError(
                    f"BehaviorProfile field '{name}' contains non-finite value: {value}"
                )
        return self

    def to_feature_vector(self, feature_names: list[str]) -> np.ndarray:
        """
        Export a subset of features as a numpy array.
        None values are represented as np.nan — callers must handle sparsity.
        """
        result = []
        for name in feature_names:
            val = getattr(self, name, None)
            result.append(float(val) if val is not None else np.nan)
        return np.array(result, dtype=np.float64)


class BehaviorTransition(BaseModel):
    """
    ΔB_i(t) = B_i(t) - B_i(t-1)

    The behavioral transition vector is the primary signal used
    for lag-aware correlation in CascadeID.

    A transition is only meaningful when BOTH windows are valid
    (meet minimum observation threshold).
    """

    wallet_id: str
    from_window_index: int  # t-1
    to_window_index: int    # t

    feature_schema_version: str = Field(default="0.1.0")

    # ── Transition magnitudes (can be negative) ────────────────────────────
    d_transaction_count: int | None = Field(default=None)
    d_activity_rate: float | None = Field(default=None)
    d_total_volume_eth: float | None = Field(default=None)
    d_mean_value_eth: float | None = Field(default=None)
    d_value_variance_eth: float | None = Field(default=None)
    d_total_gas_fee_eth: float | None = Field(default=None)
    d_unique_counterparty_count: int | None = Field(default=None)
    d_counterparty_entropy: float | None = Field(default=None)
    d_unique_contract_count: int | None = Field(default=None)
    d_contract_diversity: float | None = Field(default=None)
    d_unique_token_count: int | None = Field(default=None)
    d_token_diversity: float | None = Field(default=None)
    d_mean_interarrival_seconds: float | None = Field(default=None)
    d_interarrival_variance: float | None = Field(default=None)
    d_burstiness: float | None = Field(default=None)
    d_hour_entropy: float | None = Field(default=None)

    # Validity
    both_windows_valid: bool = Field(default=False)

    model_config = {"frozen": True}

    def to_vector(self, feature_names: list[str]) -> np.ndarray:
        """
        Export transition deltas as a numpy array.
        None values become np.nan — callers handle sparsity.
        """
        result = []
        for name in feature_names:
            val = getattr(self, name, None)
            result.append(float(val) if val is not None else np.nan)
        return np.array(result, dtype=np.float64)