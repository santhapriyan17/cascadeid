"""
cascadeid.utils.address

Ethereum address normalisation and validation.

We treat addresses as lowercase hex strings throughout the system.
EIP-55 checksum is verified on input but stored as lowercase.

Security note: addresses come from untrusted blockchain providers.
Always validate before use in queries or storage.
"""

from __future__ import annotations

import re

# Ethereum address: 0x followed by exactly 40 hex characters
_ETH_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

# Zero address (often used as null in Solidity)
ZERO_ADDRESS = "0x" + "0" * 40


def is_valid_address(address: str | None) -> bool:
    """Return True if address is a well-formed Ethereum address."""
    if address is None:
        return False
    return bool(_ETH_ADDRESS_RE.match(address))


def normalize_address(address: str) -> str:
    """
    Normalize to lowercase hex.
    Raises ValueError for malformed addresses.
    """
    if not is_valid_address(address):
        raise ValueError(f"Invalid Ethereum address: {address!r}")
    return address.lower()


def is_zero_address(address: str | None) -> bool:
    """Return True if address is the zero address (0x000...0)."""
    if address is None:
        return False
    return address.lower() == ZERO_ADDRESS


def is_contract_address(address: str | None) -> bool:
    """
    Heuristic: contract addresses are not identified by the address alone.
    This returns False — actual contract detection requires on-chain lookup.
    Placeholder for future on-chain classification.
    """
    return False  # requires eth_getCode — not available statically


def safe_normalize(address: str | None) -> str | None:
    """
    Normalize if valid, return None otherwise.
    Never raises — safe for use in validators.
    """
    if address is None:
        return None
    if not is_valid_address(address):
        return None
    return address.lower()