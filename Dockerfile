FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY src/ ./src/
COPY configs/ ./configs/
COPY scripts/ ./scripts/

ENV PYTHONPATH=/app/src

CMD ["uvicorn", "cascadeid.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
