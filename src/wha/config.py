"""Configuration management for WHA."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env if present
load_dotenv()


def get_db_path() -> Path:
    """Get the SQLite database path from environment or default."""
    path_str = os.environ.get("WHA_DB_PATH", "data/wha.sqlite")
    return Path(path_str)


def get_subject() -> str:
    """Get default subject ID."""
    return os.environ.get("WHA_SUBJECT", "me")


def get_timezone() -> str:
    """Get default timezone string."""
    return os.environ.get("WHA_TIMEZONE", "Asia/Singapore")


def get_data_dir() -> Path:
    """Get dataset directory root."""
    path_str = os.environ.get("WHA_DATA_DIR", "data/datasets")
    return Path(path_str)
