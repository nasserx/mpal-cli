"""Application metadata and default local paths."""

import os
from pathlib import Path

APP_NAME = "mpal"
CLI_NAME = "mpal"
DISTRIBUTION_NAME = "mpal-cli"
DATABASE_FILENAME = "mpal.db"


def get_data_dir() -> Path:
    """Return mpal's local data directory.

    ``MPAL_DATA_DIR`` is supported as a small explicit override, primarily
    for isolated environments and tests.
    """
    override = os.environ.get("MPAL_DATA_DIR")
    if override:
        return Path(override).expanduser()

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_NAME

    return Path.home() / ".local" / "share" / CLI_NAME


def get_database_path() -> Path:
    """Return the default SQLite database path."""
    return get_data_dir() / DATABASE_FILENAME
