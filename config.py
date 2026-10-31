"""Central application configuration."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    app_name: str = os.getenv("APP_NAME", "AgentGuard")
    environment: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("APP_DEBUG", "false").strip().lower() in {"1", "true", "yes"}


settings = Settings()
