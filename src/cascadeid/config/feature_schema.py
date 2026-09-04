"""
cascadeid.config.feature_schema

Versioned feature schema: the canonical list of feature names used
across profiles and transitions, their types, and version.

All modules that need feature names import from here — no scattered
string literals across the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class FeatureDefinition:
    name: str
    dtype: Literal["float", "int"]
    description: str
    family: str  # activity | economic | interaction | temporal
    is_transition_feature: bool = True  # included in ΔB vector


# ── Canonical feature definitions ─────────────────────────────────────────

PROFILE_FEATURES: list[FeatureDefinition] = [
    # Activity
    FeatureDefinition("activity_rate", "float", "Transactions per second", "activity"),
    FeatureDefinition("active_window_fraction", "float", "Fraction of windows active", "activity"),
    # Economic
    FeatureDefinition("total_volume_eth", "float", "Total ETH volume in window", "economic"),
    FeatureDefinition("mean_value_eth", "float", "Mean ETH per transaction", "economic"),
    FeatureDefinition("median_value_eth", "float", "Median ETH per transaction", "economic"),
    FeatureDefinition("value_variance_eth", "float", "Variance of ETH value", "economic"),
    FeatureDefinition("total_gas_fee_eth", "float", "Total gas fees paid (ETH)", "economic"),
    FeatureDefinition("mean_gas_used", "float", "Mean gas units used", "economic"),
    # Interaction
    FeatureDefinition("unique_counterparty_count", "int", "Distinct counterparties", "interaction"),
    FeatureDefinition("counterparty_entropy", "float", "Shannon entropy of counterparties", "interaction"),
    FeatureDefinition("unique_contract_count", "int", "Distinct contracts called", "interaction"),
    FeatureDefinition("contract_diversity", "float", "Contract diversity score", "interaction"),
    FeatureDefinition("unique_token_count", "int", "Distinct token types", "interaction"),
    FeatureDefinition("token_diversity", "float", "Token diversity score", "interaction"),
    # Temporal
    FeatureDefinition("mean_interarrival_seconds", "float", "Mean time between tx", "temporal"),
    FeatureDefinition("median_interarrival_seconds", "float", "Median interarrival time", "temporal"),
    FeatureDefinition("interarrival_variance", "float", "Variance of interarrival times", "temporal"),
    FeatureDefinition("burstiness", "float", "Burstiness: (σ-μ)/(σ+μ) of interarrivals", "temporal"),
    FeatureDefinition("hour_entropy", "float", "Shannon entropy of hour-of-day distribution", "temporal"),
    FeatureDefinition("active_window_entropy", "float", "Entropy of active window distribution", "temporal"),
]

TRANSITION_FEATURE_NAMES: list[str] = [
    f"d_{feat.name}"
    for feat in PROFILE_FEATURES
    if feat.is_transition_feature
]

PROFILE_FEATURE_NAMES: list[str] = [feat.name for feat in PROFILE_FEATURES]

SCHEMA_VERSION = "0.1.0"


def get_feature_names_by_family(family: str) -> list[str]:
    return [f.name for f in PROFILE_FEATURES if f.family == family]


def get_transition_feature_names() -> list[str]:
    return TRANSITION_FEATURE_NAMES