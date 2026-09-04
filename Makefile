.PHONY: install test lint type-check setup-db seed run-api run-replay

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=src/cascadeid --cov-report=term-missing

lint:
	ruff check src/ tests/ experiments/

type-check:
	mypy src/cascadeid

setup-db:
	python scripts/setup_db.py

seed:
	python scripts/seed_synthetic.py

run-api:
	uvicorn cascadeid.api.app:create_app --factory --reload --host 0.0.0.0 --port 8000

run-replay:
	python scripts/run_replay.py

benchmark:
	python scripts/benchmark.py
