"""
Unit tests for domain models.

Tests verify:
- Model construction with valid data
- Rejection of invalid data (NaN, Inf, bad ranges)
- Immutability where required
- Key/hash behaviour for identifiers
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from cascadeid.domain.enums import (
    CoordinationStatus,
    Direction,
    EventType,
    FeedbackLabel,
    IngestionSource,
)
from cascadeid.domain.transaction import NormalizedTransaction
from cascadeid.domain.wallet import WalletIdentifier, WalletState
from cascadeid.domain.temporal import TemporalWindow, WindowKey
from cascadeid.domain.features import BehaviorProfile, BehaviorTransition
from cascadeid.domain.correlation import CorrelationResult, TemporalFingerprint
from cascadeid.domain.graph import CoordinationEdge, WalletNode
from cascadeid.domain.risk import EvidenceItem, ConfidenceResult, RiskResult
from cascadeid.domain.enums import DataQuality, EvidenceCategory, TemporalStabilityLevel


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def make_tx(**kwargs) -> NormalizedTransaction:
    defaults = dict(
        internal_id="abc123",
        chain_id=1,
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        from_address="0xabc",
        event_type=EventType.ETH_TRANSFER,
        source=IngestionSource.HISTORICAL_FILE,
    )
    defaults.update(kwargs)
    return NormalizedTransaction(**defaults)


def make_profile(**kwargs) -> BehaviorProfile:
    defaults = dict(wallet_id="w1", window_index=0)
    defaults.update(kwargs)
    return BehaviorProfile(**defaults)


# ─────────────────────────────────────────────────────────────────
# NormalizedTransaction
# ─────────────────────────────────────────────────────────────────

class TestNormalizedTransaction:
    def test_basic_construction(self):
        tx = make_tx()
        assert tx.chain_id == 1
        assert tx.from_address == "0xabc"  # lowercased

    def test_address_normalised_to_lowercase(self):
        tx = make_tx(from_address="0xABC", to_address="0XDEF")
        assert tx.from_address == "0xabc"
        assert tx.to_address == "0xdef"

    def test_hash_normalised_to_lowercase(self):
        tx = make_tx(transaction_hash="0XDEADBEEF")
        assert tx.transaction_hash == "0xdeadbeef"

    def test_none_fields_allowed(self):
        tx = make_tx(to_address=None, value_wei=None)
        assert tx.to_address is None
        assert tx.value_wei is None

    def test_immutability(self):
        tx = make_tx()
        with pytest.raises(Exception):
            tx.chain_id = 99  # type: ignore


# ─────────────────────────────────────────────────────────────────
# WalletIdentifier
# ─────────────────────────────────────────────────────────────────

class TestWalletIdentifier:
    def test_key_format(self):
        w = WalletIdentifier(chain_id=1, address="0xabc")
        assert w.key == "1:0xabc"

    def test_immutability(self):
        w = WalletIdentifier(chain_id=1, address="0xabc")
        with pytest.raises(Exception):
            w.chain_id = 2  # type: ignore

    def test_hashable(self):
        w1 = WalletIdentifier(chain_id=1, address="0xabc")
        w2 = WalletIdentifier(chain_id=1, address="0xabc")
        assert hash(w1) == hash(w2)


# ─────────────────────────────────────────────────────────────────
# TemporalWindow
# ─────────────────────────────────────────────────────────────────

class TestTemporalWindow:
    def _make_window(self, **kwargs):
        defaults = dict(
            key=WindowKey(wallet_id="w1", window_index=0),
            start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
        defaults.update(kwargs)
        return TemporalWindow(**defaults)

    def test_basic_construction(self):
        w = self._make_window()
        assert w.duration_seconds == 86400.0

    def test_end_before_start_rejected(self):
        with pytest.raises(ValueError):
            self._make_window(
                start_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )

    def test_equal_times_rejected(self):
        t = datetime(2024, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValueError):
            self._make_window(start_time=t, end_time=t)


# ─────────────────────────────────────────────────────────────────
# BehaviorProfile
# ─────────────────────────────────────────────────────────────────

class TestBehaviorProfile:
    def test_basic_construction(self):
        p = make_profile(transaction_count=10, total_volume_eth=1.5)
        assert p.transaction_count == 10

    def test_nan_rejected(self):
        with pytest.raises(ValueError):
            make_profile(activity_rate=float("nan"))

    def test_inf_rejected(self):
        with pytest.raises(ValueError):
            make_profile(total_volume_eth=float("inf"))

    def test_none_allowed_for_optional_float(self):
        p = make_profile(activity_rate=None)
        assert p.activity_rate is None

    def test_to_feature_vector_with_nones(self):
        import numpy as np
        p = make_profile(total_volume_eth=1.0, mean_value_eth=None)
        vec = p.to_feature_vector(["total_volume_eth", "mean_value_eth"])
        assert vec[0] == pytest.approx(1.0)
        assert np.isnan(vec[1])


# ─────────────────────────────────────────────────────────────────
# BehaviorTransition
# ─────────────────────────────────────────────────────────────────

class TestBehaviorTransition:
    def test_basic_construction(self):
        t = BehaviorTransition(
            wallet_id="w1",
            from_window_index=0,
            to_window_index=1,
            d_transaction_count=5,
            both_windows_valid=True,
        )
        assert t.d_transaction_count == 5
        assert t.both_windows_valid is True

    def test_none_deltas_allowed(self):
        t = BehaviorTransition(
            wallet_id="w1",
            from_window_index=0,
            to_window_index=1,
            both_windows_valid=False,
        )
        assert t.d_activity_rate is None


# ─────────────────────────────────────────────────────────────────
# CorrelationResult
# ─────────────────────────────────────────────────────────────────

class TestCorrelationResult:
    def test_sufficient_result(self):
        r = CorrelationResult(
            wallet_id_a="w1",
            wallet_id_b="w2",
            is_sufficient=True,
            best_correlation=0.75,
            best_lag=2,
            overlap_count=5,
        )
        assert r.best_correlation == pytest.approx(0.75)

    def test_insufficient_result(self):
        r = CorrelationResult(
            wallet_id_a="w1",
            wallet_id_b="w2",
            is_sufficient=False,
            overlap_count=1,
        )
        assert r.best_correlation is None
        assert r.is_sufficient is False

    def test_correlation_bounds(self):
        with pytest.raises(Exception):
            CorrelationResult(
                wallet_id_a="w1",
                wallet_id_b="w2",
                is_sufficient=True,
                best_correlation=1.5,  # out of range
                overlap_count=3,
            )


# ─────────────────────────────────────────────────────────────────
# CoordinationEdge
# ─────────────────────────────────────────────────────────────────

class TestCoordinationEdge:
    def test_edge_key_is_canonical(self):
        e = CoordinationEdge(
            wallet_id_a="wb",
            wallet_id_b="wa",
            coordination_score=0.8,
            confidence=0.6,
        )
        key = e.edge_key
        assert key == ("wa", "wb")  # sorted

    def test_score_bounds(self):
        with pytest.raises(Exception):
            CoordinationEdge(
                wallet_id_a="wa",
                wallet_id_b="wb",
                coordination_score=1.1,  # out of range
                confidence=0.5,
            )


# ─────────────────────────────────────────────────────────────────
# RiskResult
# ─────────────────────────────────────────────────────────────────

class TestRiskResult:
    def _make_confidence(self) -> ConfidenceResult:
        return ConfidenceResult(
            confidence_score=0.7,
            data_quality=DataQuality.MEDIUM,
            temporal_stability=TemporalStabilityLevel.STABLE,
        )

    def test_basic_risk_result(self):
        r = RiskResult(
            subject_id="cluster-1",
            subject_type="cluster",
            coordination_risk=0.9,
            confidence_result=self._make_confidence(),
            status=CoordinationStatus.HIGH_COORDINATION_RISK,
        )
        assert r.coordination_risk == pytest.approx(0.9)
        assert r.status == CoordinationStatus.HIGH_COORDINATION_RISK

    def test_risk_bounds(self):
        with pytest.raises(Exception):
            RiskResult(
                subject_id="c1",
                subject_type="cluster",
                coordination_risk=1.5,  # invalid
                confidence_result=self._make_confidence(),
                status=CoordinationStatus.UNKNOWN,
            )


# ─────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────

class TestSettings:
    def test_default_settings_load(self):
        from cascadeid.config.settings import get_settings
        get_settings.cache_clear()
        s = get_settings()
        assert s.temporal.window_size_seconds > 0
        assert s.lag.tau_max_windows > 0
        assert 0.0 < s.risk.exit_threshold <= s.risk.entry_threshold

    def test_exit_threshold_cannot_exceed_entry(self):
        from cascadeid.config.settings import RiskConfig
        with pytest.raises(Exception):
            RiskConfig(entry_threshold=0.70, exit_threshold=0.85)

    def test_settings_cached(self):
        from cascadeid.config.settings import get_settings
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2