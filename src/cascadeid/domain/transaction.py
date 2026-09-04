"""
cascadeid.domain.transaction

Canonical internal representation of a blockchain event after normalization.
All ingestion sources map to NormalizedTransaction before any processing.

Missing fields are represented explicitly as None — never silently fabricated.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from cascadeid.domain.enums import EventType, IngestionSource


class NormalizedTransaction(BaseModel):
    """
    Canonical representation of a single blockchain event.

    Every ingestion source (file, RPC, WebSocket) normalizes into this
    model before entering the processing pipeline.  Fields that cannot
    be populated from a given source are left as None — they are never
    synthesized.
    """

    # Internal identifier (deterministic hash of chain_id + tx_hash + log_index)
    internal_id: str = Field(..., description="Deterministic dedup key")

    # Chain
    chain_id: int = Field(..., description="EIP-155 chain identifier")

    # Block / transaction coordinates
    block_number: int | None = Field(None, description="Block number")
    transaction_hash: str | None = Field(None, description="0x-prefixed tx hash")
    log_index: int | None = Field(None, description="Log index within block (for events)")
    transaction_index: int | None = Field(None, description="Tx position in block")

    # Timing
    timestamp: datetime = Field(..., description="Block timestamp (UTC)")

    # Addresses — stored lowercase for consistent lookup
    from_address: str = Field(..., description="Sender address (checksummed)")
    to_address: str | None = Field(None, description="Recipient address (checksummed)")

    # Value
    value_wei: int | None = Field(None, description="ETH value in wei (native transfer)")
    value_eth: Decimal | None = Field(None, description="ETH value as Decimal")

    # Gas
    gas_used: int | None = Field(None)
    gas_price_wei: int | None = Field(None)
    gas_fee_eth: Decimal | None = Field(None)

    # Contract / token
    contract_address: str | None = Field(None)
    token_address: str | None = Field(None)
    token_amount: Decimal | None = Field(None)
    token_symbol: str | None = Field(None)

    # Classification
    event_type: EventType = Field(default=EventType.UNKNOWN)
    source: IngestionSource = Field(..., description="Which source produced this event")

    # Dedup / replay safety
    is_duplicate: bool = Field(default=False, description="Flagged by idempotency guard")

    model_config = {"frozen": True}

    @field_validator("from_address", "to_address", "contract_address",
                     "token_address", mode="before")
    @classmethod
    def normalise_address(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.lower().strip()

    @field_validator("transaction_hash", mode="before")
    @classmethod
    def normalise_hash(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.lower().strip()


class RawEvent(BaseModel):
    """
    Unvalidated event from an ingestion source.
    Passed to the Normalizer, never used downstream directly.
    All fields are permissive to accommodate different providers.
    """

    source: IngestionSource
    raw_data: dict  # provider-specific payload
    received_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": True}