"""
cascadeid.domain.enums

All shared enumeration types used across the CascadeID system.
Centralised here so every module imports from one place and
no string literals are scattered through the codebase.
"""

from enum import Enum, auto


class CoordinationStatus(str, Enum):
    """
    Final classification state of a wallet or cluster.
    NEVER force every wallet into NORMAL or SYBIL.
    """
    NORMAL = "NORMAL"
    HIGH_COORDINATION_RISK = "HIGH_COORDINATION_RISK"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class DataQuality(str, Enum):
    """Quality of data available for a wallet or cluster."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


class TemporalStabilityLevel(str, Enum):
    """How consistently a coordination signal persists across windows."""
    STABLE = "STABLE"
    UNSTABLE = "UNSTABLE"
    INSUFFICIENT = "INSUFFICIENT"


class Direction(str, Enum):
    """
    Observed temporal precedence between two wallets.
    Does NOT imply command/control — only repeated temporal ordering.
    """
    A_BEFORE_B = "A_BEFORE_B"
    B_BEFORE_A = "B_BEFORE_A"
    SYMMETRIC = "SYMMETRIC"
    UNDETERMINED = "UNDETERMINED"


class FeedbackLabel(str, Enum):
    """Analyst labels for a detection result."""
    CONFIRMED_COORDINATION = "CONFIRMED_COORDINATION"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    UNCERTAIN = "UNCERTAIN"
    NEW_BEHAVIOR = "NEW_BEHAVIOR"
    LEGITIMATE_AUTOMATION = "LEGITIMATE_AUTOMATION"
    OTHER = "OTHER"


class AlertStatus(str, Enum):
    """Lifecycle state of an alert."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    REVIEWED = "REVIEWED"
    SUPPRESSED = "SUPPRESSED"


class RunMode(str, Enum):
    """Operating mode of the system."""
    LOCAL = "LOCAL"
    EXPERIMENT = "EXPERIMENT"
    REPLAY = "REPLAY"
    LIVE = "LIVE"


class EvidenceCategory(str, Enum):
    """Categories of evidence that can explain a high-risk result."""
    TEMPORAL_ALIGNMENT = "TEMPORAL_ALIGNMENT"
    BEHAVIORAL_TRANSITION_SIMILARITY = "BEHAVIORAL_TRANSITION_SIMILARITY"
    REPEATED_LAG = "REPEATED_LAG"
    GRAPH_COHESION = "GRAPH_COHESION"
    INTERACTION_SIMILARITY = "INTERACTION_SIMILARITY"
    BEHAVIORAL_RARITY = "BEHAVIORAL_RARITY"
    EVIDENCE_FRESHNESS = "EVIDENCE_FRESHNESS"
    LAG_STABILITY = "LAG_STABILITY"


class WeightingStrategy(str, Enum):
    """Information weighting strategy for feature importance."""
    INVERSE_FREQUENCY = "inverse_frequency"
    DISCRIMINATIVE = "discriminative"
    LEARNED = "learned"
    UNIFORM = "uniform"


class AttackLevel(str, Enum):
    """Adversarial attack difficulty level."""
    L1_IDENTICAL = "L1"
    L2_FIXED_DELAY = "L2"
    L3_RANDOM_DELAY = "L3"
    L4_AMOUNT_VARIATION = "L4"
    L5_ACTIVITY_VARIATION = "L5"
    L6_CONTRACT_VARIATION = "L6"
    L7_NOISE_INJECTION = "L7"
    L8_COMBINED_EVASION = "L8"


class IngestionSource(str, Enum):
    """Source type for blockchain data ingestion."""
    HISTORICAL_FILE = "historical_file"
    RPC = "rpc"
    WEBSOCKET = "websocket"
    BIGQUERY = "bigquery"


class EventType(str, Enum):
    """Normalized blockchain event type."""
    ETH_TRANSFER = "eth_transfer"
    TOKEN_TRANSFER = "token_transfer"
    CONTRACT_CALL = "contract_call"
    CONTRACT_CREATION = "contract_creation"
    UNKNOWN = "unknown"


class CandidateBlockerType(str, Enum):
    """Type identifier for candidate blocking strategies."""
    ACTIVITY_REGIME = "activity_regime"
    TEMPORAL_OVERLAP = "temporal_overlap"
    BEHAVIORAL_SIGNATURE = "behavioral_signature"