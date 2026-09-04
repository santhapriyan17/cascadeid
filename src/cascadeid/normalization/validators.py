"""
cascadeid.normalization.validators

Input validation for raw blockchain data.

External data is untrusted. Every field must be validated before
entering the system. Validation failures produce structured errors,
not silent data corruption.

Security note: Do NOT execute or evaluate any string content from
blockchain metadata. Treat all string fields as opaque data.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

_TX_HASH_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

# Ethereum genesis: 2015-07-30. No valid tx can predate this.
_ETHEREUM_GENESIS = datetime(2015, 7, 30, tzinfo=timezone.utc)

# Sanity ceiling: reject timestamps > 10 years from now
_MAX_FUTURE_SECONDS = 10 * 365 * 24 * 3600

# Max reasonable wei value: 1 billion ETH in wei
_MAX_WEI = 10**9 * 10**18


class ValidationError(ValueError):
    """Structured validation error with field context."""

    def __init__(self, field: str, value: Any, reason: str) -> None:
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Validation failed for '{field}': {reason} (got {value!r})")


def validate_address(value: Any, field: str = "address") -> str:
    """
    Validate and normalize an Ethereum address.
    Returns lowercase address on success.
    Raises ValidationError on failure.
    """
    if value is None:
        raise ValidationError(field, value, "address must not be None")
    if not isinstance(value, str):
        raise ValidationError(field, value, "address must be a string")
    if not _ADDRESS_RE.match(value):
        raise ValidationError(field, value, "must match ^0x[0-9a-fA-F]{40}$")
    return value.lower()


def validate_optional_address(value: Any, field: str = "address") -> str | None:
    """Validate address if not None. Returns None for None input."""
    if value is None:
        return None
    return validate_address(value, field)


def validate_tx_hash(value: Any, field: str = "transaction_hash") -> str | None:
    """Validate a transaction hash. Returns None for None/empty input."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValidationError(field, value, "transaction_hash must be a string")
    if not _TX_HASH_RE.match(value):
        raise ValidationError(field, value, "must match ^0x[0-9a-fA-F]{64}$")
    return value.lower()


def validate_timestamp(value: Any, field: str = "timestamp") -> datetime:
    """
    Validate and return a timezone-aware UTC datetime.
    Accepts: datetime (with or without tz), int/float (unix seconds).
    Rejects: dates before Ethereum genesis, unreasonably far future.
    """
    if value is None:
        raise ValidationError(field, value, "timestamp must not be None")

    if isinstance(value, (int, float)):
        try:
            dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OSError, OverflowError, ValueError) as e:
            raise ValidationError(field, value, f"invalid unix timestamp: {e}")
    elif isinstance(value, datetime):
        dt = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    else:
        raise ValidationError(field, value, f"unsupported timestamp type: {type(value)}")

    now_utc = datetime.now(timezone.utc)
    if dt < _ETHEREUM_GENESIS:
        raise ValidationError(field, value, f"timestamp {dt} predates Ethereum genesis")
    if (dt - now_utc).total_seconds() > _MAX_FUTURE_SECONDS:
        raise ValidationError(field, value, f"timestamp {dt} is too far in the future")

    return dt


def validate_wei_value(value: Any, field: str = "value_wei") -> int | None:
    """Validate a wei value. Must be a non-negative integer."""
    if value is None:
        return None
    try:
        v = int(value)
    except (ValueError, TypeError):
        raise ValidationError(field, value, "must be convertible to int")
    if v < 0:
        raise ValidationError(field, value, "wei value must be non-negative")
    if v > _MAX_WEI:
        raise ValidationError(field, value, f"wei value {v} exceeds sanity limit {_MAX_WEI}")
    return v


def validate_gas(value: Any, field: str = "gas") -> int | None:
    """Validate gas_used or gas_price. Must be a non-negative integer."""
    if value is None:
        return None
    try:
        v = int(value)
    except (ValueError, TypeError):
        raise ValidationError(field, value, "must be convertible to int")
    if v < 0:
        raise ValidationError(field, value, "gas value must be non-negative")
    return v


def validate_block_number(value: Any, field: str = "block_number") -> int | None:
    """Validate a block number. Must be a non-negative integer."""
    if value is None:
        return None
    try:
        v = int(value)
    except (ValueError, TypeError):
        raise ValidationError(field, value, "must be convertible to int")
    if v < 0:
        raise ValidationError(field, value, "block_number must be non-negative")
    return v


def validate_chain_id(value: Any, field: str = "chain_id") -> int:
    """Validate a chain ID. Must be a positive integer."""
    if value is None:
        raise ValidationError(field, value, "chain_id must not be None")
    try:
        v = int(value)
    except (ValueError, TypeError):
        raise ValidationError(field, value, "must be convertible to int")
    if v <= 0:
        raise ValidationError(field, value, "chain_id must be positive")
    return v


def validate_decimal_amount(value: Any, field: str = "amount") -> Decimal | None:
    """Validate a token amount as Decimal. Must be non-negative."""
    if value is None:
        return None
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        raise ValidationError(field, value, "must be convertible to Decimal")
    if d < 0:
        raise ValidationError(field, value, "amount must be non-negative")
    return d