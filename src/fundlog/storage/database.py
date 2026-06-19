"""SQLite database initialization for FundLog."""

import sqlite3
from pathlib import Path

from fundlog.config import get_database_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolios (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_portfolio_name
ON portfolios (name)
WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS capital_entries (
    id INTEGER PRIMARY KEY,
    portfolio_id INTEGER NOT NULL,
    entry_type TEXT NOT NULL CHECK (entry_type IN ('inflow', 'outflow')),
    amount_minor INTEGER NOT NULL
        CHECK (typeof(amount_minor) = 'integer' AND amount_minor > 0),
    entry_date TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios (id)
);
"""


def initialize_database(database_path: Path | None = None) -> Path:
    """Create the local database and v0.1 tables if they do not exist."""
    path = database_path if database_path is not None else get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA)

    return path
