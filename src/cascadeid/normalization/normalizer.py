"""
cascadeid.normalization.normalizer

Converts a RawEvent from any ingestion source into a NormalizedTransaction.

Design principles:
- All field validation goes through normalization/validators.py
- ValidationError is caught and converted to a structured result
- Missing fields are explicitly None — never fabricated
- The normalizer never makes network calls
- Source-specific mappings are in separate methods

Supported sources (Phase 2):
- HistoricalFile: CSV/Parquet row as dict
- RPC: eth_getTransactionByHash / eth_getBlockByNumber response dict
- WebSocket: newPendingTransactions / logs subscription message

Future sources extend this class.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from cascadeid.domain.enums import EventType, IngestionSource
from cascadeid.domain.transaction import NormalizedTransaction, RawEvent
from cascadeid.normalization.validators import (
    ValidationError,
    validate_address,
    validate_block_number,
    validate_chain_id,
    validate_decimal_amount,
    validate_gas,
    validate_optional_address,
    validate_timestamp,
    validate_tx_hash,
    validate_wei_value,
)
from cascadeid.utils.hashing import transaction_internal_id

logger = logging.getLogger(__name__)

_WEI_PER_ETH = Decimal("1000000000000000000")  # 10^18


@dataclass
class NormalizationResult:
    """
    Result of a normalization attempt.

    success=True  → transaction is populated, errors is empty
    success=False → transaction is None, errors contains field-level messages
    """
    success: bool
    transaction: NormalizedTransaction | None
    errors: list[str]
    source: IngestionSource
    raw_internal_id: str | None = None


class Normalizer:
    """
    Converts RawEvents into NormalizedTransactions.

    Each ingestion source has its own _from_* method that maps
    provider-specific field names to the canonical schema.
    """

    def __init__(self, default_chain_id: int = 1) -> None:
        self._chain_id = default_chain_id

    # ──────────────────────────────────────────────────────────────────────
    # Public interface
    # ──────────────────────────────────────────────────────────────────────

    def normalize(self, event: RawEvent) -> NormalizationResult:
        """
        Normalize a RawEvent into a NormalizedTransaction.

        Returns NormalizationResult with success=False if validation fails.
        Never raises — all errors are captured in the result.
        """
        try:
            if event.source == IngestionSource.HISTORICAL_FILE:
                return self._from_file_row(event)
            elif event.source == IngestionSource.RPC:
                return self._from_rpc(event)
            elif event.source == IngestionSource.WEBSOCKET:
                return self._from_websocket(event)
            else:
                return NormalizationResult(
                    success=False,
                    transaction=None,
                    errors=[f"Unsupported source: {event.source}"],
                    source=event.source,
                )
        except Exception as e:
            logger.warning("Unexpected normalization error: %s", e, exc_info=True)
            return NormalizationResult(
                success=False,
                transaction=None,
                errors=[f"Unexpected error: {e}"],
                source=event.source,
            )

    # ──────────────────────────────────────────────────────────────────────
    # Source-specific mappings
    # ──────────────────────────────────────────────────────────────────────

    def _from_file_row(self, event: RawEvent) -> NormalizationResult:
        """
        Normalize a CSV/Parquet row.

        Expected field names (flexible — missing fields → None):
          from_address, to_address, hash / transaction_hash,
          block_number, timestamp / block_timestamp,
          value / value_wei, gas_used, gas_price,
          contract_address, token_address, token_amount,
          chain_id (optional, falls back to default)
        """
        row: dict[str, Any] = event.raw_data
        errors: list[str] = []

        # Chain ID
        raw_chain = row.get("chain_id", self._chain_id)
        try:
            chain_id = validate_chain_id(raw_chain)
        except ValidationError as e:
            chain_id = self._chain_id
            errors.append(str(e))

        # Timestamp — accept multiple common field names
        raw_ts = (
            row.get("timestamp")
            or row.get("block_timestamp")
            or row.get("ts")
        )
        try:
            timestamp = validate_timestamp(raw_ts)
        except ValidationError as e:
            errors.append(str(e))
            return NormalizationResult(
                success=False, transaction=None,
                errors=errors, source=event.source
            )

        # From address (required)
        try:
            from_address = validate_address(
                row.get("from_address") or row.get("from"), "from_address"
            )
        except ValidationError as e:
            errors.append(str(e))
            return NormalizationResult(
                success=False, transaction=None,
                errors=errors, source=event.source
            )

        # Optional fields
        to_address = _safe(validate_optional_address,
                           row.get("to_address") or row.get("to"), errors, "to_address")
        tx_hash = _safe(validate_tx_hash,
                        row.get("hash") or row.get("transaction_hash"), errors, "transaction_hash")
        block_number = _safe(validate_block_number,
                             row.get("block_number"), errors, "block_number")
        value_wei = _safe(validate_wei_value,
                          row.get("value_wei") or row.get("value"), errors, "value_wei")
        gas_used = _safe(validate_gas, row.get("gas_used"), errors, "gas_used")
        gas_price = _safe(validate_gas, row.get("gas_price"), errors, "gas_price_wei")
        contract_address = _safe(validate_optional_address,
                                 row.get("contract_address"), errors, "contract_address")
        token_address = _safe(validate_optional_address,
                              row.get("token_address"), errors, "token_address")
        token_amount = _safe(validate_decimal_amount,
                             row.get("token_amount"), errors, "token_amount")
        log_index = _safe_int(row.get("log_index"))

        # Compute derived fields
        value_eth = _wei_to_eth(value_wei)
        gas_fee_eth = _compute_gas_fee(gas_used, gas_price)

        event_type = _infer_event_type(
            to_address, contract_address, token_address, value_wei
        )

        internal_id = transaction_internal_id(
            chain_id=chain_id,
            transaction_hash=tx_hash,
            log_index=log_index,
            from_address=from_address,
            block_number=block_number,
            timestamp_unix=int(timestamp.timestamp()),
        )

        tx = NormalizedTransaction(
            internal_id=internal_id,
            chain_id=chain_id,
            block_number=block_number,
            transaction_hash=tx_hash,
            log_index=log_index,
            transaction_index=_safe_int(row.get("transaction_index")),
            timestamp=timestamp,
            from_address=from_address,
            to_address=to_address,
            value_wei=value_wei,
            value_eth=value_eth,
            gas_used=gas_used,
            gas_price_wei=gas_price,
            gas_fee_eth=gas_fee_eth,
            contract_address=contract_address,
            token_address=token_address,
            token_amount=token_amount,
            token_symbol=row.get("token_symbol"),
            event_type=event_type,
            source=event.source,
        )
        return NormalizationResult(
            success=True,
            transaction=tx,
            errors=errors,  # may contain non-fatal warnings
            source=event.source,
        )

    def _from_rpc(self, event: RawEvent) -> NormalizationResult:
        """
        Normalize an eth_getTransactionByHash / block response.
        RPC field names follow the Ethereum JSON-RPC spec.
        """
        row: dict[str, Any] = event.raw_data
        errors: list[str] = []

        chain_id = self._chain_id  # RPC response doesn't always include chainId
        raw_chain = row.get("chainId")
        if raw_chain is not None:
            try:
                chain_id = validate_chain_id(int(raw_chain, 16) if isinstance(raw_chain, str) else raw_chain)
            except (ValidationError, ValueError):
                pass  # use default

        # RPC timestamps are unix ints in block metadata
        raw_ts = row.get("timestamp") or row.get("blockTimestamp")
        if isinstance(raw_ts, str) and raw_ts.startswith("0x"):
            raw_ts = int(raw_ts, 16)
        try:
            timestamp = validate_timestamp(raw_ts)
        except ValidationError as e:
            errors.append(str(e))
            return NormalizationResult(
                success=False, transaction=None,
                errors=errors, source=event.source
            )

        try:
            from_address = validate_address(row.get("from", ""), "from")
        except ValidationError as e:
            errors.append(str(e))
            return NormalizationResult(
                success=False, transaction=None,
                errors=errors, source=event.source
            )

        tx_hash = _safe(validate_tx_hash, row.get("hash"), errors, "hash")
        to_address = _safe(validate_optional_address, row.get("to"), errors, "to")

        # RPC values are hex-encoded
        value_wei = _hex_to_int(row.get("value"))
        gas_used = _hex_to_int(row.get("gasUsed") or row.get("gas"))
        gas_price = _hex_to_int(row.get("gasPrice"))
        block_number = _hex_to_int(row.get("blockNumber"))
        log_index = _hex_to_int(row.get("logIndex") or row.get("transactionIndex"))

        contract_address = _safe(validate_optional_address,
                                 row.get("contractAddress") or row.get("address"),
                                 errors, "contractAddress")
        token_address = _safe(validate_optional_address,
                               row.get("tokenAddress"), errors, "tokenAddress")
        token_amount = _safe(validate_decimal_amount,
                              row.get("tokenAmount"), errors, "tokenAmount")

        value_eth = _wei_to_eth(value_wei)
        gas_fee_eth = _compute_gas_fee(gas_used, gas_price)
        event_type = _infer_event_type(to_address, contract_address, token_address, value_wei)

        internal_id = transaction_internal_id(
            chain_id=chain_id,
            transaction_hash=tx_hash,
            log_index=log_index,
            from_address=from_address,
            block_number=block_number,
            timestamp_unix=int(timestamp.timestamp()),
        )

        tx = NormalizedTransaction(
            internal_id=internal_id,
            chain_id=chain_id,
            block_number=block_number,
            transaction_hash=tx_hash,
            log_index=log_index,
            timestamp=timestamp,
            from_address=from_address,
            to_address=to_address,
            value_wei=value_wei,
            value_eth=value_eth,
            gas_used=gas_used,
            gas_price_wei=gas_price,
            gas_fee_eth=gas_fee_eth,
            contract_address=contract_address,
            token_address=token_address,
            token_amount=token_amount,
            event_type=event_type,
            source=event.source,
        )
        return NormalizationResult(
            success=True, transaction=tx,
            errors=errors, source=event.source
        )

    def _from_websocket(self, event: RawEvent) -> NormalizationResult:
        """
        Normalize a WebSocket subscription message.
        WebSocket messages often lack gas_used (receipt not yet available).
        Delegates to _from_rpc after field aliasing.
        """
        # WebSocket subscription responses use the same field structure as RPC
        # but may be missing receipt fields (gas_used, contract_address).
        # We reuse _from_rpc with the understanding that missing fields → None.
        aliased = RawEvent(
            source=IngestionSource.RPC,  # temporarily alias for _from_rpc
            raw_data=event.raw_data,
            received_at=event.received_at,
        )
        result = self._from_rpc(aliased)
        if result.transaction:
            # Rebuild with correct source
            tx = result.transaction.model_copy(
                update={"source": IngestionSource.WEBSOCKET}
            )
            return NormalizationResult(
                success=result.success,
                transaction=tx,
                errors=result.errors,
                source=IngestionSource.WEBSOCKET,
            )
        return NormalizationResult(
            success=result.success,
            transaction=None,
            errors=result.errors,
            source=IngestionSource.WEBSOCKET,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────────────────────────────────────

def _safe(validate_fn, value: Any, errors: list[str], field: str):
    """Call validate_fn; on ValidationError append to errors and return None."""
    try:
        return validate_fn(value, field)
    except ValidationError as e:
        errors.append(str(e))
        return None
    except Exception as e:
        errors.append(f"Unexpected error for {field}: {e}")
        return None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _hex_to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 16) if value.startswith("0x") else int(value)
        except ValueError:
            return None
    return None


def _wei_to_eth(value_wei: int | None) -> Decimal | None:
    if value_wei is None:
        return None
    return Decimal(value_wei) / _WEI_PER_ETH


def _compute_gas_fee(gas_used: int | None, gas_price: int | None) -> Decimal | None:
    if gas_used is None or gas_price is None:
        return None
    return Decimal(gas_used * gas_price) / _WEI_PER_ETH


def _infer_event_type(
    to_address: str | None,
    contract_address: str | None,
    token_address: str | None,
    value_wei: int | None,
) -> EventType:
    """
    Infer event type from available fields.
    This is a heuristic — actual classification may require on-chain data.
    """
    if token_address is not None:
        return EventType.TOKEN_TRANSFER
    if to_address is None:
        return EventType.CONTRACT_CREATION
    if contract_address is not None:
        return EventType.CONTRACT_CALL
    if value_wei and value_wei > 0:
        return EventType.ETH_TRANSFER
    return EventType.UNKNOWN