"""
cascadeid.utils.hashing

Deterministic hashing for internal IDs.

Used by:
- Idempotency guard (dedup of ingested events)
- Candidate signature generation
- Deterministic wallet_id from (chain_id, address)

All hashes are hex strings (SHA-256 truncated or full).
Never use Python's built-in hash() — it is not deterministic across runs.
"""

from __future__ import annotations

import hashlib


def sha256_hex(data: str) -> str:
    """Full SHA-256 hex digest of a UTF-8 string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def transaction_internal_id(
    chain_id: int,
    transaction_hash: str | None,
    log_index: int | None,
    from_address: str,
    block_number: int | None,
    timestamp_unix: int,
) -> str:
    """
    Deterministic internal ID for a normalized transaction.

    This is used by the idempotency guard to detect duplicate ingestion.
    The ID is stable across restarts and ingestion sources.

    Priority:
    1. If tx_hash + log_index are available: use them (strongest dedup).
    2. Otherwise fall back to (chain_id, from_address, block_number, timestamp).
    """
    if transaction_hash and transaction_hash not in ("", "0x"):
        key_parts = [
            str(chain_id),
            transaction_hash.lower(),
            str(log_index if log_index is not None else ""),
        ]
    else:
        # Fallback for sources without tx hash
        key_parts = [
            str(chain_id),
            from_address.lower(),
            str(block_number if block_number is not None else ""),
            str(timestamp_unix),
        ]
    raw = ":".join(key_parts)
    return sha256_hex(raw)[:32]  # 32-char prefix is sufficient for dedup


def wallet_id(chain_id: int, address: str) -> str:
    """
    Deterministic wallet identifier: "{chain_id}:{address_lowercase}".
    Used as the primary key throughout the system.
    """
    return f"{chain_id}:{address.lower()}"


def candidate_pair_key(wallet_id_a: str, wallet_id_b: str) -> str:
    """
    Canonical key for a (wallet_a, wallet_b) candidate pair.
    Always sorted so (a, b) and (b, a) produce the same key.
    """
    a, b = sorted([wallet_id_a, wallet_id_b])
    return f"{a}|{b}"


def behavioral_signature(feature_vector_repr: str) -> str:
    """
    Coarse signature from a feature vector string representation.
    Used by the behavioral-signature blocker for cheap near-match detection.
    Returns first 16 hex chars of SHA-256.
    """
    return sha256_hex(feature_vector_repr)[:16]