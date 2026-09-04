"""
Unit tests for utility modules.

Covers: numerical, time_utils, address, hashing, serialization.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import numpy as np
import pytest

from cascadeid.utils.numerical import (
    safe_divide,
    safe_log,
    safe_sqrt,
    safe_mean,
    safe_std,
    safe_median,
    safe_normalize,
    check_finite,
    clip_to_finite,
    has_sufficient_variance,
    shannon_entropy,
    pearson_correlation,
    weighted_pearson_correlation,
    count_finite,
)
from cascadeid.utils.time_utils import (
    ensure_utc,
    floor_to_window,
    window_index_of,
    window_boundaries,
    elapsed_seconds,
    windows_between,
)
from cascadeid.utils.address import (
    is_valid_address,
    normalize_address,
    is_zero_address,
    safe_normalize as addr_safe_normalize,
)
from cascadeid.utils.hashing import (
    sha256_hex,
    transaction_internal_id,
    wallet_id,
    candidate_pair_key,
)
from cascadeid.utils.serialization import to_json, from_json, SafeJSONEncoder


# ─────────────────────────────────────────────────────────────────
# numerical.py
# ─────────────────────────────────────────────────────────────────

class TestSafeDivide:
    def test_normal(self):
        assert safe_divide(10.0, 2.0) == pytest.approx(5.0)

    def test_zero_denominator(self):
        assert math.isnan(safe_divide(10.0, 0.0))

    def test_custom_fallback(self):
        assert safe_divide(1.0, 0.0, fallback=-1.0) == -1.0

    def test_nan_numerator(self):
        assert math.isnan(safe_divide(float("nan"), 2.0))

    def test_inf_denominator(self):
        assert math.isnan(safe_divide(1.0, float("inf")))


class TestSafeLog:
    def test_natural_log(self):
        assert safe_log(math.e) == pytest.approx(1.0)

    def test_log_base_10(self):
        assert safe_log(100.0, base=10.0) == pytest.approx(2.0)

    def test_zero_input(self):
        assert math.isnan(safe_log(0.0))

    def test_negative_input(self):
        assert math.isnan(safe_log(-1.0))

    def test_nan_input(self):
        assert math.isnan(safe_log(float("nan")))


class TestSafeMean:
    def test_simple(self):
        arr = np.array([1.0, 2.0, 3.0])
        assert safe_mean(arr) == pytest.approx(2.0)

    def test_empty_array(self):
        assert math.isnan(safe_mean(np.array([])))

    def test_ignores_nan(self):
        arr = np.array([1.0, np.nan, 3.0])
        assert safe_mean(arr) == pytest.approx(2.0)

    def test_all_nan(self):
        arr = np.array([np.nan, np.nan])
        assert math.isnan(safe_mean(arr))


class TestSafeStd:
    def test_simple(self):
        arr = np.array([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
        # safe_std uses ddof=1 (sample std). Population std=2.0, sample std≈2.138.
        assert safe_std(arr) == pytest.approx(2.138089935299395, rel=1e-5)

    def test_single_element(self):
        # ddof=1 with single element → insufficient observations → nan
        assert math.isnan(safe_std(np.array([5.0])))

    def test_two_identical(self):
        arr = np.array([3.0, 3.0])
        assert safe_std(arr) == pytest.approx(0.0)

    def test_empty(self):
        assert math.isnan(safe_std(np.array([])))


class TestSafeMedian:
    def test_odd_count(self):
        arr = np.array([1.0, 3.0, 5.0])
        assert safe_median(arr) == pytest.approx(3.0)

    def test_with_nan(self):
        arr = np.array([1.0, np.nan, 5.0])
        assert safe_median(arr) == pytest.approx(3.0)

    def test_empty(self):
        assert math.isnan(safe_median(np.array([])))


class TestSafeNormalize:
    def test_unit_vector(self):
        arr = np.array([3.0, 4.0])
        result = safe_normalize(arr)
        assert np.linalg.norm(result) == pytest.approx(1.0)

    def test_zero_vector(self):
        arr = np.array([0.0, 0.0])
        result = safe_normalize(arr)
        assert all(math.isnan(v) for v in result)

    def test_empty(self):
        arr = np.array([])
        assert len(safe_normalize(arr)) == 0


class TestCheckFinite:
    def test_passes_finite(self):
        arr = np.array([1.0, 2.0, 3.0])
        check_finite(arr)  # should not raise

    def test_raises_on_nan(self):
        with pytest.raises(ValueError, match="non-finite"):
            check_finite(np.array([1.0, np.nan]))

    def test_raises_on_inf(self):
        with pytest.raises(ValueError, match="non-finite"):
            check_finite(np.array([float("inf")]))


class TestHasSufficientVariance:
    def test_varied(self):
        assert has_sufficient_variance(np.array([1.0, 2.0, 3.0]))

    def test_constant(self):
        assert not has_sufficient_variance(np.array([5.0, 5.0, 5.0]))

    def test_single(self):
        assert not has_sufficient_variance(np.array([1.0]))

    def test_empty(self):
        assert not has_sufficient_variance(np.array([]))


class TestShannonEntropy:
    def test_uniform_two(self):
        # Equal split → log(2)
        counts = np.array([1.0, 1.0])
        assert shannon_entropy(counts) == pytest.approx(math.log(2))

    def test_deterministic(self):
        counts = np.array([1.0, 0.0])
        assert shannon_entropy(counts) == pytest.approx(0.0)

    def test_zero_counts(self):
        assert math.isnan(shannon_entropy(np.array([0.0, 0.0])))

    def test_empty(self):
        assert math.isnan(shannon_entropy(np.array([])))


class TestPearsonCorrelation:
    def test_perfect_positive(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        assert pearson_correlation(x, x) == pytest.approx(1.0)

    def test_perfect_negative(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = -x
        assert pearson_correlation(x, y) == pytest.approx(-1.0)

    def test_no_correlation(self):
        rng = np.random.default_rng(42)
        x = rng.standard_normal(1000)
        y = rng.standard_normal(1000)
        corr = pearson_correlation(x, y)
        assert abs(corr) < 0.1

    def test_constant_vector(self):
        x = np.array([1.0, 1.0, 1.0])
        y = np.array([1.0, 2.0, 3.0])
        assert math.isnan(pearson_correlation(x, y))

    def test_mismatched_length(self):
        with pytest.raises(ValueError):
            pearson_correlation(np.array([1.0, 2.0]), np.array([1.0]))

    def test_too_short(self):
        assert math.isnan(pearson_correlation(np.array([1.0]), np.array([2.0])))

    def test_with_nan_values(self):
        x = np.array([1.0, np.nan, 3.0, 4.0, 5.0])
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        corr = pearson_correlation(x, y)
        assert np.isfinite(corr)


class TestWeightedPearson:
    def test_equal_weights_matches_pearson(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        w = np.ones(5)
        assert weighted_pearson_correlation(x, y, w) == pytest.approx(1.0)

    def test_zero_weights_excluded(self):
        x = np.array([1.0, 2.0, 999.0])
        y = np.array([1.0, 2.0, -999.0])
        w = np.array([1.0, 1.0, 0.0])
        result = weighted_pearson_correlation(x, y, w)
        assert result == pytest.approx(1.0)


# ─────────────────────────────────────────────────────────────────
# time_utils.py
# ─────────────────────────────────────────────────────────────────

_EPOCH = datetime(2015, 7, 30, tzinfo=timezone.utc)
_WINDOW = 86400  # 1 day


class TestEnsureUtc:
    def test_aware_datetime_passes(self):
        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        result = ensure_utc(dt)
        assert result.tzinfo is not None

    def test_naive_raises(self):
        with pytest.raises(ValueError, match="Naive datetime"):
            ensure_utc(datetime(2024, 1, 1))


class TestFloorToWindow:
    def test_exact_epoch_start(self):
        result = floor_to_window(_EPOCH, _WINDOW, epoch=_EPOCH)
        assert result == _EPOCH

    def test_mid_window(self):
        ts = _EPOCH + timedelta(hours=12)
        result = floor_to_window(ts, _WINDOW, epoch=_EPOCH)
        assert result == _EPOCH

    def test_second_window(self):
        ts = _EPOCH + timedelta(days=1, hours=6)
        result = floor_to_window(ts, _WINDOW, epoch=_EPOCH)
        assert result == _EPOCH + timedelta(days=1)

    def test_before_epoch_raises(self):
        ts = _EPOCH - timedelta(days=1)
        with pytest.raises(ValueError, match="before epoch"):
            floor_to_window(ts, _WINDOW, epoch=_EPOCH)


class TestWindowIndex:
    def test_epoch_is_zero(self):
        assert window_index_of(_EPOCH, _WINDOW, epoch=_EPOCH) == 0

    def test_next_day_is_one(self):
        ts = _EPOCH + timedelta(days=1)
        assert window_index_of(ts, _WINDOW, epoch=_EPOCH) == 1

    def test_fractional_day(self):
        ts = _EPOCH + timedelta(hours=36)
        assert window_index_of(ts, _WINDOW, epoch=_EPOCH) == 1


class TestWindowBoundaries:
    def test_window_zero(self):
        start, end = window_boundaries(0, _WINDOW, epoch=_EPOCH)
        assert start == _EPOCH
        assert end == _EPOCH + timedelta(days=1)

    def test_window_one(self):
        start, end = window_boundaries(1, _WINDOW, epoch=_EPOCH)
        assert start == _EPOCH + timedelta(days=1)


class TestElapsedSeconds:
    def test_one_day(self):
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 1, 2, tzinfo=timezone.utc)
        assert elapsed_seconds(t1, t2) == pytest.approx(86400.0)

    def test_reversed_returns_zero(self):
        t1 = datetime(2024, 1, 2, tzinfo=timezone.utc)
        t2 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert elapsed_seconds(t1, t2) == 0.0


class TestWindowsBetween:
    def test_single_window(self):
        t1 = _EPOCH
        t2 = _EPOCH + timedelta(hours=12)
        result = windows_between(t1, t2, _WINDOW, epoch=_EPOCH)
        assert result == [0]

    def test_two_windows(self):
        t1 = _EPOCH + timedelta(hours=12)
        t2 = _EPOCH + timedelta(hours=36)
        result = windows_between(t1, t2, _WINDOW, epoch=_EPOCH)
        assert 0 in result
        assert 1 in result


# ─────────────────────────────────────────────────────────────────
# address.py
# ─────────────────────────────────────────────────────────────────

class TestAddressUtils:
    def test_valid_address(self):
        assert is_valid_address("0x" + "a" * 40)

    def test_invalid_too_short(self):
        assert not is_valid_address("0x" + "a" * 39)

    def test_none(self):
        assert not is_valid_address(None)

    def test_normalize_lowercases(self):
        result = normalize_address("0x" + "A" * 40)
        assert result == "0x" + "a" * 40

    def test_normalize_invalid_raises(self):
        with pytest.raises(ValueError):
            normalize_address("not-an-address")

    def test_zero_address(self):
        assert is_zero_address("0x" + "0" * 40)

    def test_safe_normalize_none(self):
        assert addr_safe_normalize(None) is None

    def test_safe_normalize_invalid(self):
        assert addr_safe_normalize("garbage") is None


# ─────────────────────────────────────────────────────────────────
# hashing.py
# ─────────────────────────────────────────────────────────────────

class TestHashing:
    def test_sha256_deterministic(self):
        h1 = sha256_hex("test")
        h2 = sha256_hex("test")
        assert h1 == h2

    def test_sha256_different_inputs(self):
        assert sha256_hex("a") != sha256_hex("b")

    def test_transaction_id_deterministic(self):
        kwargs = dict(
            chain_id=1,
            transaction_hash="0x" + "a" * 64,
            log_index=0,
            from_address="0x" + "b" * 40,
            block_number=100,
            timestamp_unix=1234567890,
        )
        assert transaction_internal_id(**kwargs) == transaction_internal_id(**kwargs)

    def test_transaction_id_different_hashes(self):
        base = dict(
            chain_id=1,
            transaction_hash="0x" + "a" * 64,
            log_index=0,
            from_address="0x" + "b" * 40,
            block_number=100,
            timestamp_unix=1234567890,
        )
        alt = {**base, "transaction_hash": "0x" + "c" * 64}
        assert transaction_internal_id(**base) != transaction_internal_id(**alt)

    def test_wallet_id_format(self):
        assert wallet_id(1, "0xABC") == "1:0xabc"

    def test_candidate_pair_key_sorted(self):
        k1 = candidate_pair_key("wb", "wa")
        k2 = candidate_pair_key("wa", "wb")
        assert k1 == k2

    def test_candidate_pair_key_different(self):
        assert candidate_pair_key("wa", "wb") != candidate_pair_key("wa", "wc")


# ─────────────────────────────────────────────────────────────────
# serialization.py
# ─────────────────────────────────────────────────────────────────

class TestSerialization:
    def test_nan_becomes_null(self):
        result = to_json({"value": float("nan")})
        parsed = from_json(result)
        assert parsed["value"] is None

    def test_inf_becomes_null(self):
        result = to_json({"value": float("inf")})
        parsed = from_json(result)
        assert parsed["value"] is None

    def test_neg_inf_becomes_null(self):
        result = to_json({"value": float("-inf")})
        parsed = from_json(result)
        assert parsed["value"] is None

    def test_datetime_serialized(self):
        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        result = to_json({"ts": dt})
        assert "2024-01-01" in result

    def test_decimal_serialized(self):
        result = to_json({"amount": Decimal("1.23456789")})
        assert "1.23456789" in result

    def test_numpy_int(self):
        result = to_json({"n": np.int64(42)})
        data = from_json(result)
        assert data["n"] == 42

    def test_numpy_float(self):
        result = to_json({"x": np.float64(3.14)})
        data = from_json(result)
        assert abs(data["x"] - 3.14) < 0.001

    def test_numpy_nan_becomes_null(self):
        result = to_json({"v": np.float64(float("nan"))})
        parsed = from_json(result)
        assert parsed["v"] is None

    def test_nan_in_list(self):
        result = to_json([1.0, float("nan"), 3.0])
        parsed = from_json(result)
        assert parsed == [1.0, None, 3.0]

    def test_nan_nested(self):
        result = to_json({"outer": {"inner": float("nan")}})
        parsed = from_json(result)
        assert parsed["outer"]["inner"] is None

    def test_round_trip(self):
        original = {"a": 1, "b": "hello", "c": [1, 2, 3]}
        assert from_json(to_json(original)) == original