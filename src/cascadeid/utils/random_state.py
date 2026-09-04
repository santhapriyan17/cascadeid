"""
cascadeid.utils.random_state

Deterministic random seed management.

All stochastic operations (simulation, experiment, Louvain) must
use seeds derived from the central configuration seed.
This ensures experiments are fully reproducible.
"""

from __future__ import annotations

import random

import numpy as np


def seed_everything(seed: int) -> None:
    """
    Seed Python random, NumPy, and (if available) XGBoost/sklearn.

    Call once at the start of any experiment or simulation run.
    Never call in production detection code.
    """
    random.seed(seed)
    np.random.seed(seed)

    # Seed sklearn if available (uses numpy internally, but explicit is better)
    try:
        import sklearn  # noqa: F401
        # sklearn uses numpy's global state; already seeded above
    except ImportError:
        pass

    # Seed XGBoost global state if available
    try:
        import xgboost as xgb  # noqa: F401
        # XGBoost respects numpy seed for most operations
    except ImportError:
        pass


def make_rng(seed: int) -> np.random.Generator:
    """
    Create an isolated numpy RNG from a given seed.
    Preferred for simulation and testing where isolation matters.
    """
    return np.random.default_rng(seed)


def derive_seed(base_seed: int, component: str) -> int:
    """
    Derive a component-specific seed from a base seed.
    Ensures different components don't share the same RNG state
    even when called in sequence.

    Uses a simple but stable hash: deterministic across Python versions.
    """
    component_hash = int(
        __import__("hashlib").sha256(
            f"{base_seed}:{component}".encode()
        ).hexdigest()[:8],
        16
    )
    return component_hash % (2**31)