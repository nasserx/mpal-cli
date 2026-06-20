"""SQLite database initialization for FundLog."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fundlog.config import get_database_path
from fundlog.errors import DatabaseNotInitializedError, StorageError

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
    entry_no INTEGER NOT NULL CHECK (entry_no > 0),
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

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY,
    portfolio_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_asset_symbol
ON assets (portfolio_id, symbol)
WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS asset_transactions (
    id INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL,
    entry_no INTEGER NOT NULL CHECK (entry_no > 0),
    transaction_type TEXT NOT NULL
        CHECK (transaction_type IN ('buy', 'sell', 'income')),
    transaction_date TEXT NOT NULL
        CHECK (
            length(transaction_date) = 10
            AND transaction_date GLOB
                '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        ),
    price_text TEXT,
    quantity_text TEXT,
    fee_minor INTEGER NOT NULL DEFAULT 0
        CHECK (typeof(fee_minor) = 'integer' AND fee_minor >= 0),
    total_minor INTEGER NOT NULL
        CHECK (typeof(total_minor) = 'integer' AND total_minor > 0),
    cash_effect_minor INTEGER NOT NULL
        CHECK (typeof(cash_effect_minor) = 'integer'),
    position_effect_minor INTEGER NOT NULL
        CHECK (typeof(position_effect_minor) = 'integer'),
    realized_pnl_minor INTEGER NOT NULL DEFAULT 0
        CHECK (typeof(realized_pnl_minor) = 'integer'),
    income_minor INTEGER NOT NULL DEFAULT 0
        CHECK (typeof(income_minor) = 'integer' AND income_minor >= 0),
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY (asset_id) REFERENCES assets (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_asset_transaction_entry_no
ON asset_transactions (asset_id, entry_no);
"""


def next_entry_no(connection: sqlite3.Connection, portfolio_id: int) -> int:
    """Return the next stable entry number for a portfolio."""
    return connection.execute(
        """
        SELECT COALESCE(MAX(entry_no), 0) + 1
        FROM capital_entries
        WHERE portfolio_id = ?
        """,
        (portfolio_id,),
    ).fetchone()[0]


def next_asset_transaction_no(
    connection: sqlite3.Connection,
    asset_id: int,
) -> int:
    """Return the next stable transaction number for an asset."""
    return connection.execute(
        """
        SELECT COALESCE(MAX(entry_no), 0) + 1
        FROM asset_transactions
        WHERE asset_id = ?
        """,
        (asset_id,),
    ).fetchone()[0]


def _ensure_entry_numbers(connection: sqlite3.Connection) -> None:
    """Add and backfill portfolio-local entry numbers when needed."""
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(capital_entries)")
    }
    if "entry_no" not in columns:
        connection.execute("ALTER TABLE capital_entries ADD COLUMN entry_no INTEGER")

    rows = connection.execute(
        """
        SELECT id, portfolio_id, entry_no
        FROM capital_entries
        ORDER BY portfolio_id ASC, id ASC
        """
    ).fetchall()
    next_numbers: dict[int, int] = {}
    for _, portfolio_id, entry_no in rows:
        if entry_no is not None:
            next_numbers[portfolio_id] = max(
                next_numbers.get(portfolio_id, 1),
                entry_no + 1,
            )

    for internal_id, portfolio_id, entry_no in rows:
        if entry_no is not None:
            continue
        assigned_no = next_numbers.get(portfolio_id, 1)
        connection.execute(
            "UPDATE capital_entries SET entry_no = ? WHERE id = ?",
            (assigned_no, internal_id),
        )
        next_numbers[portfolio_id] = assigned_no + 1

    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_portfolio_entry_no
        ON capital_entries (portfolio_id, entry_no)
        """
    )


def _ensure_active_portfolio_names(connection: sqlite3.Connection) -> None:
    """Ensure active portfolio names remain unique on legacy databases."""
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_active_portfolio_name
        ON portfolios (name)
        WHERE deleted_at IS NULL
        """
    )


def _ensure_assets(connection: sqlite3.Connection) -> None:
    """Create the initial asset table and active-symbol index when missing."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY,
            portfolio_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios (id)
        )
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_active_asset_symbol
        ON assets (portfolio_id, symbol)
        WHERE deleted_at IS NULL
        """
    )


def _ensure_asset_transactions(connection: sqlite3.Connection) -> None:
    """Create the asset transaction table and stable local-number index."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS asset_transactions (
            id INTEGER PRIMARY KEY,
            asset_id INTEGER NOT NULL,
            entry_no INTEGER NOT NULL CHECK (entry_no > 0),
            transaction_type TEXT NOT NULL
                CHECK (transaction_type IN ('buy', 'sell', 'income')),
            transaction_date TEXT NOT NULL
                CHECK (
                    length(transaction_date) = 10
                    AND transaction_date GLOB
                        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                ),
            price_text TEXT,
            quantity_text TEXT,
            fee_minor INTEGER NOT NULL DEFAULT 0
                CHECK (typeof(fee_minor) = 'integer' AND fee_minor >= 0),
            total_minor INTEGER NOT NULL
                CHECK (typeof(total_minor) = 'integer' AND total_minor > 0),
            cash_effect_minor INTEGER NOT NULL
                CHECK (typeof(cash_effect_minor) = 'integer'),
            position_effect_minor INTEGER NOT NULL
                CHECK (typeof(position_effect_minor) = 'integer'),
            realized_pnl_minor INTEGER NOT NULL DEFAULT 0
                CHECK (typeof(realized_pnl_minor) = 'integer'),
            income_minor INTEGER NOT NULL DEFAULT 0
                CHECK (typeof(income_minor) = 'integer' AND income_minor >= 0),
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT,
            FOREIGN KEY (asset_id) REFERENCES assets (id)
        )
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_asset_transaction_entry_no
        ON asset_transactions (asset_id, entry_no)
        """
    )


def _require_initialized_schema(connection: sqlite3.Connection) -> None:
    """Require the existing FundLog v0.1 base tables."""
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if not {"portfolios", "capital_entries"}.issubset(tables):
        raise DatabaseNotInitializedError(
            "FundLog is not initialized. Run 'fundlog init' first."
        )


@contextmanager
def connect_database(
    database_path: Path | None = None,
) -> Iterator[sqlite3.Connection]:
    """Open an initialized database and apply pending migrations."""
    path = database_path if database_path is not None else get_database_path()
    if not path.is_file():
        raise DatabaseNotInitializedError(
            "FundLog is not initialized. Run 'fundlog init' first."
        )

    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(path)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        _require_initialized_schema(connection)
        _ensure_active_portfolio_names(connection)
        _ensure_entry_numbers(connection)
        _ensure_assets(connection)
        _ensure_asset_transactions(connection)
        yield connection
    except sqlite3.Error as error:
        if connection is not None:
            connection.rollback()
        raise StorageError(
            "FundLog could not access the local database safely. "
            "Run 'fundlog init' and try again."
        ) from error
    except Exception:
        if connection is not None:
            connection.rollback()
        raise
    else:
        connection.commit()
    finally:
        if connection is not None:
            connection.close()


def initialize_database(database_path: Path | None = None) -> Path:
    """Create the local database and v0.1 tables if they do not exist."""
    path = database_path if database_path is not None else get_database_path()

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(SCHEMA)
            connection.execute("BEGIN IMMEDIATE")
            _ensure_active_portfolio_names(connection)
            _ensure_entry_numbers(connection)
            _ensure_assets(connection)
            _ensure_asset_transactions(connection)
    except (OSError, sqlite3.Error) as error:
        raise StorageError(
            "FundLog could not initialize the local database."
        ) from error

    return path
