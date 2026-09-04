"""
Unit tests for the normalization layer.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cascadeid.domain.enums import EventType, IngestionSource
from cascadeid.domain.transaction import RawEvent
from cascadeid.normalization.normalizer import Normalizer
from cascadeid.normalization.validators import (
    ValidationError,
    validate_address,
    validate_timestamp,
    validate_wei_value,
    validate_tx_hash,
    validate_block_number,
)


# ─────────────────────────────────────────────────────────────────
# validators.py
# ─────────────────────────────────────────────────────────────────

class TestValidateAddress:
    def test_valid(self):
        assert validate_address("0x" + "a" * 40) == "0x" + "a" * 40

    def test_uppercase_accepted_and_normalised_to_lowercase(self):
        # validate_address normalises to lowercase
        assert validate_address("0x" + "A" * 40) == "0x" + "a" * 40

    def test_none_raises(self):
        with pytest.raises(ValidationError):
            validate_address(None)

    def test_too_short_raises(self):
        with pytest.raises(ValidationError):
            validate_address("0x" + "a" * 39)

    def test_no_prefix_raises(self):
        with pytest.raises(ValidationError):
            validate_address("a" * 40)

    def test_non_hex_raises(self):
        with pytest.raises(ValidationError):
            validate_address("0x" + "g" * 40)


class TestValidateTimestamp:
    def test_unix_int(self):
        ts = validate_timestamp(1609459200)  # 2021-01-01 UTC
        assert ts.tzinfo is not None
        assert ts.year == 2021

    def test_datetime_aware(self):
        dt = datetime(2022, 6, 1, tzinfo=timezone.utc)
        ts = validate_timestamp(dt)
        assert ts == dt

    def test_datetime_naive_accepted_as_utc(self):
        dt = datetime(2022, 6, 1)
        ts = validate_timestamp(dt)
        assert ts.tzinfo is not None

    def test_before_genesis_raises(self):
        with pytest.raises(ValidationError, match="genesis"):
            validate_timestamp(0)  # Unix epoch = 1970, before Ethereum

    def test_none_raises(self):
        with pytest.raises(ValidationError):
            validate_timestamp(None)


class TestValidateWei:
    def test_zero(self):
        assert validate_wei_value(0) == 0

    def test_positive(self):
        assert validate_wei_value(1_000_000_000) == 1_000_000_000

    def test_none(self):
        assert validate_wei_value(None) is None

    def test_negative_raises(self):
        with pytest.raises(ValidationError):
            validate_wei_value(-1)

    def test_string_convertible(self):
        assert validate_wei_value("500") == 500


class TestValidateTxHash:
    def test_valid_hash(self):
        h = "0x" + "a" * 64
        assert validate_tx_hash(h) == h

    def test_none_returns_none(self):
        assert validate_tx_hash(None) is None

    def test_empty_returns_none(self):
        assert validate_tx_hash("") is None

    def test_wrong_length(self):
        with pytest.raises(ValidationError):
            validate_tx_hash("0x" + "a" * 63)


# ─────────────────────────────────────────────────────────────────
# normalizer.py
# ─────────────────────────────────────────────────────────────────

def _make_file_event(row: dict) -> RawEvent:
    return RawEvent(source=IngestionSource.HISTORICAL_FILE, raw_data=row)


def _make_rpc_event(row: dict) -> RawEvent:
    return RawEvent(source=IngestionSource.RPC, raw_data=row)


_BASE_ROW = {
    "from_address": "0x" + "a" * 40,
    "to_address": "0x" + "b" * 40,
    "timestamp": 1609459200,  # 2021-01-01 UTC
    "block_number": 11565020,
    "hash": "0x" + "c" * 64,
    "value_wei": 1_000_000_000_000_000_000,
    "gas_used": 21000,
    "gas_price": 100_000_000_000,
    "chain_id": 1,
}


class TestNormalizerFileSource:
    def setup_method(self):
        self.norm = Normalizer(default_chain_id=1)

    def test_success(self):
        result = self.norm.normalize(_make_file_event(_BASE_ROW))
        assert result.success
        assert result.transaction is not None
        assert result.transaction.chain_id == 1
        assert result.transaction.from_address == "0x" + "a" * 40

    def test_missing_from_address_fails(self):
        row = {**_BASE_ROW}
        del row["from_address"]
        result = self.norm.normalize(_make_file_event(row))
        assert not result.success
        assert result.transaction is None

    def test_missing_timestamp_fails(self):
        row = {**_BASE_ROW}
        del row["timestamp"]
        result = self.norm.normalize(_make_file_event(row))
        assert not result.success

    def test_invalid_address_fails(self):
        row = {**_BASE_ROW, "from_address": "not-an-address"}
        result = self.norm.normalize(_make_file_event(row))
        assert not result.success

    def test_none_optional_fields_allowed(self):
        row = {**_BASE_ROW, "to_address": None, "gas_used": None}
        result = self.norm.normalize(_make_file_event(row))
        assert result.success
        assert result.transaction.to_address is None
        assert result.transaction.gas_used is None

    def test_eth_transfer_event_type(self):
        row = {**_BASE_ROW}
        result = self.norm.normalize(_make_file_event(row))
        assert result.transaction.event_type == EventType.ETH_TRANSFER

    def test_token_transfer_event_type(self):
        row = {**_BASE_ROW, "token_address": "0x" + "d" * 40}
        result = self.norm.normalize(_make_file_event(row))
        assert result.transaction.event_type == EventType.TOKEN_TRANSFER

    def test_dedup_id_deterministic(self):
        r1 = self.norm.normalize(_make_file_event(_BASE_ROW))
        r2 = self.norm.normalize(_make_file_event(_BASE_ROW))
        assert r1.transaction.internal_id == r2.transaction.internal_id

    def test_dedup_id_differs_on_different_hash(self):
        row_a = _BASE_ROW
        row_b = {**_BASE_ROW, "hash": "0x" + "e" * 64}
        r1 = self.norm.normalize(_make_file_event(row_a))
        r2 = self.norm.normalize(_make_file_event(row_b))
        assert r1.transaction.internal_id != r2.transaction.internal_id

    def test_value_eth_computed(self):
        result = self.norm.normalize(_make_file_event(_BASE_ROW))
        from decimal import Decimal
        assert result.transaction.value_eth == Decimal("1")

    def test_gas_fee_computed(self):
        result = self.norm.normalize(_make_file_event(_BASE_ROW))
        assert result.transaction.gas_fee_eth is not None
        assert result.transaction.gas_fee_eth > 0


class TestNormalizerRPCSource:
    def setup_method(self):
        self.norm = Normalizer(default_chain_id=1)

    def _rpc_row(self):
        return {
            "from": "0x" + "a" * 40,
            "to": "0x" + "b" * 40,
            "timestamp": 1609459200,
            "blockNumber": "0xb0420c",
            "hash": "0x" + "c" * 64,
            "value": "0xde0b6b3a7640000",  # 1 ETH in hex
            "gasUsed": "0x5208",
            "gasPrice": "0x174876e800",
        }

    def test_rpc_success(self):
        result = self.norm.normalize(_make_rpc_event(self._rpc_row()))
        assert result.success
        assert result.transaction is not None

    def test_hex_values_decoded(self):
        result = self.norm.normalize(_make_rpc_event(self._rpc_row()))
        tx = result.transaction
        assert tx.block_number == 0xB0420C
        assert tx.gas_used == 0x5208