# CascadeID

**CascadeID — A Time-Delayed Behavioral Correlation Framework for Graph-Based
Detection of Coordinated Sybil Wallets in Blockchain Networks**

## Status: Phase 0 — Architecture Skeleton

This repository contains the complete architecture skeleton for CascadeID.
No business logic is implemented yet. Implementation begins in Phase 1.

## Quick Start (after implementation)

```bash
cp .env.example .env
# Edit .env with your database/provider credentials
make install
make setup-db
make seed          # synthetic data
make run-api
```

## Architecture

See `docs/architecture.md`.

## Configuration

See `docs/configuration.md` and `configs/`.

## Running Experiments

```bash
python -m cascadeid.cli.main experiment --config configs/experiment.yaml
```

## Research Note

CascadeID detects *likely coordinated wallet behavior based on observable
on-chain evidence*. It does not identify real-world identities or prove malicious intent.
----------------------------------------------------------------------------------------------------------------------------------------------------------------
