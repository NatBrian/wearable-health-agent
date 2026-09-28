"""Configuration management for WHA."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

load_dotenv()


class Settings(BaseModel):
    """Immutable application settings with secret redaction."""

    model_config = ConfigDict(frozen=True)

    db_path: Path = Field(
        default_factory=lambda: Path(os.environ.get("WHA_DB_PATH", "data/wha.sqlite"))
    )
    subject: str = Field(default_factory=lambda: os.environ.get("WHA_SUBJECT", "me"))
    timezone: str = Field(default_factory=lambda: os.environ.get("WHA_TIMEZONE", "Asia/Singapore"))
    dashboard_origins: list[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.environ.get(
                "WHA_CORS_ALLOWED_ORIGINS",
                "http://127.0.0.1:8443,http://localhost:8443",
            ).split(",")
            if origin.strip()
        ],
        validate_default=True,
    )

    @field_validator("dashboard_origins")
    @classmethod
    def require_exact_dashboard_origins(cls, origins: list[str]) -> list[str]:
        if any("*" in origin for origin in origins):
            raise ValueError("Dashboard CORS origins must be explicit origins, never wildcards")
        return origins
    data_dir: Path = Field(
        default_factory=lambda: Path(os.environ.get("WHA_DATA_DIR", "data/datasets"))
    )
    model_cache_dir: Path = Field(
        default_factory=lambda: Path(os.environ.get("WHA_MODEL_CACHE_DIR", "data/model_cache"))
    )

    # LLM
    llm_provider: str = Field(
        default_factory=lambda: os.environ.get("WHA_LLM_PROVIDER", "cassette")
    )
    llm_model: str = Field(default_factory=lambda: os.environ.get("WHA_LLM_MODEL", "deepseek-v3.2"))
    llm_base_url: str | None = Field(default_factory=lambda: os.environ.get("WHA_LLM_BASE_URL"))
    llm_api_key: SecretStr | None = Field(
        default_factory=lambda: (
            SecretStr(os.environ["WHA_LLM_API_KEY"]) if "WHA_LLM_API_KEY" in os.environ else None
        )
    )

    # Telegram
    telegram_bot_token: SecretStr | None = Field(
        default_factory=lambda: (
            SecretStr(os.environ["WHA_TELEGRAM_BOT_TOKEN"])
            if "WHA_TELEGRAM_BOT_TOKEN" in os.environ
            else (
                SecretStr(os.environ["WHA_TELEGRAM_TOKEN"])
                if "WHA_TELEGRAM_TOKEN" in os.environ
                else None
            )
        )
    )
    telegram_chat_id: str | None = Field(
        default_factory=lambda: os.environ.get("WHA_TELEGRAM_CHAT_ID")
    )

    # Bridge
    bridge_url: str | None = Field(default_factory=lambda: os.environ.get("WHA_BRIDGE_URL"))
    bridge_token: SecretStr | None = Field(
        default_factory=lambda: (
            SecretStr(os.environ["WHA_BRIDGE_TOKEN"]) if "WHA_BRIDGE_TOKEN" in os.environ else None
        )
    )


_settings_instance: Settings | None = None


def get_settings(reload: bool = False) -> Settings:
    """Get global settings instance."""
    global _settings_instance
    if _settings_instance is None or reload:
        _settings_instance = Settings()
    return _settings_instance


def get_db_path() -> Path:
    return get_settings().db_path


def get_subject() -> str:
    return get_settings().subject


def get_timezone() -> str:
    return get_settings().timezone


def get_data_dir() -> Path:
    return get_settings().data_dir
