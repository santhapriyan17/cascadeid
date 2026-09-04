"""
cascadeid.domain.wallet

WalletIdentifier and WalletState with timezone-aware datetime.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, Field

_now = lambda: datetime.now(timezone.utc)


class WalletIdentifier(BaseModel):
    chain_id: int
    address: str

    model_config = {"frozen": True}

    def __str__(self) -> str:
        return f"{self.chain_id}:{self.address}"

    @property
    def key(self) -> str:
        return str(self)


class WalletState(BaseModel):
    wallet_id: str
    chain_id: int
    address: str

    transaction_count: int = Field(default=0)
    active_window_count: int = Field(default=0)

    total_volume_eth: Decimal = Field(default=Decimal("0"))
    mean_value_eth: Decimal | None = Field(default=None)
    median_value_eth: Decimal | None = Field(default=None)
    value_variance_eth: Decimal | None = Field(default=None)

    total_gas_fee_eth: Decimal = Field(default=Decimal("0"))
    mean_gas_used: float | None = Field(default=None)

    unique_counterparty_count: int = Field(default=0)
    unique_contract_count: int = Field(default=0)
    unique_token_count: int = Field(default=0)

    first_seen: datetime | None = Field(default=None)
    last_seen: datetime | None = Field(default=None)
    mean_interarrival_seconds: float | None = Field(default=None)
    interarrival_variance: float | None = Field(default=None)
    burstiness: float | None = Field(default=None)

    current_coordination_risk: float | None = Field(default=None)
    current_confidence: float | None = Field(default=None)
    current_status: str = Field(default="UNKNOWN")

    last_updated: datetime = Field(default_factory=_now)
    feature_schema_version: str = Field(default="0.1.0")

    model_config = {"frozen": False}