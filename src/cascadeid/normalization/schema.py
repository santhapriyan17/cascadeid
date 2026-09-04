"""
cascadeid.normalization.schema

Canonical field documentation for the normalized transaction schema.
This module has no runtime logic — it is the authoritative reference
for what each field means and what sources provide it.

Imported by: normalizer, validators, documentation generators.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class FieldSpec:
    name: str
    python_type: str
    required: bool
    source_availability: dict[str, bool]  # source_name → available
    description: str
    validation_notes: str = ""


CANONICAL_FIELDS: list[FieldSpec] = [
    FieldSpec(
        name="internal_id",
        python_type="str",
        required=True,
        source_availability={"file": True, "rpc": True, "websocket": True},
        description="Deterministic dedup key computed from chain+hash+log_index",
    ),
    FieldSpec(
        name="chain_id",
        python_type="int",
        required=True,
        source_availability={"file": True, "rpc": True, "websocket": True},
        description="EIP-155 chain ID (1=Ethereum mainnet)",
    ),
    FieldSpec(
        name="block_number",
        python_type="int | None",
        required=False,
        source_availability={"file": True, "rpc": True, "websocket": True},
        description="Block number. None for pending transactions.",
    ),
    FieldSpec(
        name="transaction_hash",
        python_type="str | None",
        required=False,
        source_availability={"file": True, "rpc": True, "websocket": True},
        description="0x-prefixed 32-byte transaction hash",
        validation_notes="Normalized to lowercase. Must match ^0x[0-9a-f]{64}$",
    ),
    FieldSpec(
        name="timestamp",
        python_type="datetime",
        required=True,
        source_availability={"file": True, "rpc": True, "websocket": True},
        description="Block timestamp as timezone-aware UTC datetime",
        validation_notes="Must be timezone-aware. Naive datetimes rejected.",
    ),
    FieldSpec(
        name="from_address",
        python_type="str",
        required=True,
        source_availability={"file": True, "rpc": True, "websocket": True},
        description="Sender address (checksummed, stored lowercase)",
        validation_notes="Must match ^0x[0-9a-f]{40}$",
    ),
    FieldSpec(
        name="to_address",
        python_type="str | None",
        required=False,
        source_availability={"file": True, "rpc": True, "websocket": True},
        description="Recipient. None for contract creation transactions.",
    ),
    FieldSpec(
        name="value_wei",
        python_type="int | None",
        required=False,
        source_availability={"file": True, "rpc": True, "websocket": True},
        description="ETH value transferred in wei",
    ),
    FieldSpec(
        name="gas_used",
        python_type="int | None",
        required=False,
        source_availability={"file": True, "rpc": True, "websocket": False},
        description="Gas actually consumed. Not available from WebSocket subscription.",
    ),
    FieldSpec(
        name="contract_address",
        python_type="str | None",
        required=False,
        source_availability={"file": True, "rpc": True, "websocket": True},
        description="Contract address for token transfers and contract calls",
    ),
    FieldSpec(
        name="token_address",
        python_type="str | None",
        required=False,
        source_availability={"file": True, "rpc": True, "websocket": True},
        description="ERC-20/ERC-721 token contract address",
    ),
    FieldSpec(
        name="token_amount",
        python_type="Decimal | None",
        required=False,
        source_availability={"file": True, "rpc": True, "websocket": True},
        description="Token amount in token-native units (raw, not decimal-adjusted)",
    ),
]

FIELD_NAMES: list[str] = [f.name for f in CANONICAL_FIELDS]
REQUIRED_FIELD_NAMES: list[str] = [f.name for f in CANONICAL_FIELDS if f.required]