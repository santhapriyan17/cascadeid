# CascadeID — Architecture Overview

## Core Hypothesis
Wallets controlled by the same entity may exhibit similar behavioral transitions
at different (lagged) times. CascadeID detects this via lag-aware correlation.

## Data Flow

```
BLOCKCHAIN DATA
  ↓
INGESTION (BlockchainDataSource ABC)
  ↓
NORMALIZATION (NormalizedTransaction)
  ↓
STORAGE (PostgreSQL via repository pattern)
  ↓
TEMPORAL WINDOWING (configurable window/stride)
  ↓
BEHAVIORAL FEATURE EXTRACTION (5 feature families)
  ↓
BEHAVIORAL PROFILES (per wallet per window)
  ↓
BEHAVIORAL TRANSITIONS  ΔB_i(t)
  ↓
CANDIDATE GENERATION (blocking — not O(N²))
  ↓
LAG-AWARE CORRELATION  C_ij(τ), τ* = argmax
  ↓
INFORMATION WEIGHTING
  ↓
TEMPORAL FINGERPRINT (accumulated pair evidence)
  ↓
COORDINATION EDGE (if thresholds met)
  ↓
WALLET GRAPH (NetworkX)
  ↓
COMMUNITY DETECTION (Louvain)
  ↓
CLUSTER FEATURE ENGINE
  ↓
RISK ENGINE (rule-based + optional XGBoost)
  ↓
CONFIDENCE ENGINE (separate from risk)
  ↓
EVIDENCE EXPLAINER
  ↓
ALERT / API
  ↓
ANALYST FEEDBACK
  ↓
SHADOW EVALUATION → CALIBRATION → VERSIONED MODEL
```

## Layer Dependency Rules

```
domain         ← imports nothing internal
config         ← imports domain only
utils          ← imports domain, config
storage        ← imports domain, config, utils
features       ← imports domain, config, utils
temporal       ← imports domain, config, utils, features
correlation    ← imports domain, config, utils, features, temporal
candidates     ← imports domain, config, utils, temporal, features
graph          ← imports domain, config, utils, correlation
clustering     ← imports domain, config, utils, graph
risk           ← imports domain, config, utils, graph, clustering, correlation
confidence     ← imports domain, config, utils, risk
evidence       ← imports domain, config, utils, risk, confidence
feedback       ← imports domain, config, storage, evidence
models         ← imports domain, config, utils, risk
monitoring     ← imports domain, config, utils (no upward deps)
evaluation     ← imports everything below (experiment-only)
simulation     ← imports domain, config, utils, features (never imports detection)
replay         ← imports ingestion, services, monitoring
services       ← imports storage, features, temporal, correlation, candidates,
                 graph, clustering, risk, confidence, evidence, feedback
api            ← imports services, domain, config, monitoring
cli            ← imports services, api, evaluation, simulation, replay, config
```

## Key Architectural Decisions

### AD-1: Candidate Blocking (not O(N²))
Never compare all wallet pairs. Use cheap blocking strategies first.
Expensive lag correlation only on candidates.

### AD-2: Risk ≠ Confidence
Always computed and stored separately. High risk + low confidence = UNKNOWN.

### AD-3: Evidence-First
Every risk score is traceable to specific evidence items.
No black-box score accepted as final output.

### AD-4: Online Processing Constraint
Replay and live mode: future data must never be visible at time t.
Enforced in replay.clock and replay.engine.

### AD-5: Modular Community Detection
CommunityDetector ABC allows swapping algorithms without touching risk engine.

### AD-6: Optional ML
XGBoost layer is disabled by default. System works fully without it.

### AD-7: No Distributed Infrastructure
Modular monolith. FastAPI + PostgreSQL + NetworkX. No Kafka/Spark/Ray.

### AD-8: Simulation Never Imports Detection
simulation/ package imports only domain, config, utils, features.
Ground truth labels never leak into the detection pipeline.

### AD-9: Feedback Protected from Live Detector
Feedback goes through: queue → validator → store → shadow_eval → calibration_trigger.
Never directly modifies live thresholds.

### AD-10: Temporal Leakage Prevention
Evaluation uses temporal train/val/test splits.
leakage_guard.py enforces chronological ordering.
