"""
cascadeid.config.settings

Central configuration using Pydantic BaseSettings.
All values come from environment variables or YAML config files —
never from hard-coded literals in business logic.

Usage:
    from cascadeid.config.settings import get_settings
    settings = get_settings()
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from cascadeid.domain.enums import RunMode, WeightingStrategy


class TemporalConfig(BaseSettings):
    """Temporal windowing configuration."""
    window_size_seconds: int = Field(default=86400, gt=0)   # 1 day
    window_stride_seconds: int = Field(default=43200, gt=0)  # 12 hours
    history_windows: int = Field(default=30, gt=0)
    min_observations_per_window: int = Field(default=3, ge=1)

    model_config = SettingsConfigDict(env_prefix="TEMPORAL_")


class LagConfig(BaseSettings):
    """Lag-aware correlation configuration."""
    tau_max_windows: int = Field(default=5, gt=0)
    min_overlap_windows: int = Field(default=3, ge=1)
    min_correlation_threshold: float = Field(default=0.35, ge=0.0, le=1.0)

    model_config = SettingsConfigDict(env_prefix="LAG_")


class CandidateConfig(BaseSettings):
    """Candidate generation configuration."""
    strategies: list[str] = Field(
        default=["activity_regime", "temporal_overlap"]
    )
    max_pairs_per_wallet: int = Field(default=500, gt=0)

    model_config = SettingsConfigDict(env_prefix="CANDIDATE_")


class GraphConfig(BaseSettings):
    """Graph construction configuration."""
    min_coordination_score: float = Field(default=0.40, ge=0.0, le=1.0)
    min_repeated_alignment: int = Field(default=2, ge=0)
    min_confidence: float = Field(default=0.30, ge=0.0, le=1.0)

    model_config = SettingsConfigDict(env_prefix="GRAPH_")


class RiskConfig(BaseSettings):
    """Risk engine configuration."""
    entry_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    exit_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    decay_lambda: float = Field(default=0.05, ge=0.0)
    weighting_strategy: WeightingStrategy = Field(
        default=WeightingStrategy.INVERSE_FREQUENCY
    )

    model_config = SettingsConfigDict(env_prefix="RISK_")

    @field_validator("exit_threshold")
    @classmethod
    def exit_below_entry(cls, v: float, info) -> float:
        entry = info.data.get("entry_threshold", 0.85)
        if v > entry:
            raise ValueError(
                f"exit_threshold ({v}) must be ≤ entry_threshold ({entry})"
            )
        return v


class ClusteringConfig(BaseSettings):
    """Clustering configuration."""
    algorithm: str = Field(default="louvain")
    resolution: float = Field(default=1.0, gt=0.0)
    min_cluster_size: int = Field(default=2, ge=2)

    model_config = SettingsConfigDict(env_prefix="CLUSTERING_")


class DatabaseConfig(BaseSettings):
    """Database connection configuration."""
    url: str = Field(
        default="postgresql+psycopg2://cascadeid:password@localhost:5432/cascadeid"
    )
    pool_size: int = Field(default=10, gt=0)
    max_overflow: int = Field(default=5, ge=0)
    echo: bool = Field(default=False)

    model_config = SettingsConfigDict(env_prefix="DATABASE_")


class EthereumConfig(BaseSettings):
    """Ethereum provider configuration."""
    rpc_url: str | None = Field(default=None)
    ws_url: str | None = Field(default=None)
    chain_id: int = Field(default=1)
    request_timeout_seconds: int = Field(default=30, gt=0)
    max_retries: int = Field(default=3, ge=0)

    model_config = SettingsConfigDict(env_prefix="ETH_")


class APIConfig(BaseSettings):
    """API server configuration."""
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, gt=0, le=65535)
    secret_key: str = Field(default="change-me-in-production")
    cors_origins: list[str] = Field(default=["http://localhost:3000"])

    model_config = SettingsConfigDict(env_prefix="API_")


class EvaluationConfig(BaseSettings):
    """Evaluation and experiment configuration."""
    random_seed: int = Field(default=42)
    temporal_split_ratio: tuple[float, float, float] = Field(
        default=(0.6, 0.2, 0.2)
    )

    model_config = SettingsConfigDict(env_prefix="EVAL_")


class Settings(BaseSettings):
    """
    Top-level settings object.

    Nested configs are loaded from env-prefixed variables or
    can be overridden from YAML via config.loader.
    """

    mode: RunMode = Field(default=RunMode.LOCAL)

    enable_xgboost: bool = Field(default=False)
    enable_redis_cache: bool = Field(default=False)

    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    # Nested configs — each pulls from its own env prefix
    temporal: TemporalConfig = Field(default_factory=TemporalConfig)
    lag: LagConfig = Field(default_factory=LagConfig)
    candidates: CandidateConfig = Field(default_factory=CandidateConfig)
    graph: GraphConfig = Field(default_factory=GraphConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    clustering: ClusteringConfig = Field(default_factory=ClusteringConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    ethereum: EthereumConfig = Field(default_factory=EthereumConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CASCADEID_",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the singleton Settings instance.
    Cached after first load; call get_settings.cache_clear() in tests.
    """
    return Settings()