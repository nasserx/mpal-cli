"""CLI and migration tests for the read-only asset transaction log."""

import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from fundlog.cli import app

runner = CliRunner()


def _initialize_asset(
    tmp_path: Path,
    monkeypatch,
    portfolio: str = "stocks",
    symbol: str = "AAPL",
) -> Path:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["portfolio", "create", portfolio]).exit_code == 0
    assert runner.invoke(app, ["asset", "add", symbol, "-p", portfolio]).exit_code == 0
    return data_dir / "fundlog.db"


def _asset_id(database_path: Path, portfolio: str, symbol: str) -> int:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT a.id
            FROM assets AS a
            JOIN portfolios AS p ON p.id = a.portfolio_id
            WHERE p.name = ? AND a.symbol = ?
            """,
            (portfolio, symbol),
        ).fetchone()
    assert row is not None
    return row[0]


def _insert_transaction(
    database_path: Path,
    *,
    asset_id: int,
    entry_no: int,
    transaction_date: str,
    transaction_type: str = "buy",
    price_text: str | None = "234.4300",
    quantity_text: str | None = "3.5000",
    fee_minor: int = 125,
    total_minor: int = 82_176,
    note: str | None = None,
    deleted: bool = False,
) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO asset_transactions (
                asset_id,
                entry_no,
                transaction_type,
                transaction_date,
                price_text,
                quantity_text,
                fee_minor,
                total_minor,
                cash_effect_minor,
                position_effect_minor,
                realized_pnl_minor,
                income_minor,
                note,
                deleted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?)
            """,
            (
                asset_id,
                entry_no,
                transaction_type,
                transaction_date,
                price_text,
                quantity_text,
                fee_minor,
                total_minor,
                -total_minor if transaction_type == "buy" else total_minor,
                total_minor if transaction_type == "buy" else 0,
                note,
                "2000-01-01 00:00:00" if deleted else None,
            ),
        )


def test_init_creates_asset_transactions_schema(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(asset_transactions)")
        }
        indexes = {
            row[1]
            for row in connection.execute("PRAGMA index_list(asset_transactions)")
        }

    assert {
        "id",
        "asset_id",
        "entry_no",
        "transaction_type",
        "transaction_date",
        "price_text",
        "quantity_text",
        "fee_minor",
        "total_minor",
        "cash_effect_minor",
        "position_effect_minor",
        "realized_pnl_minor",
        "income_minor",
        "note",
        "created_at",
        "updated_at",
        "deleted_at",
    } == columns
    assert "uq_asset_transaction_entry_no" in indexes


def test_asset_transaction_migration_is_idempotent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    asset_id = _asset_id(database_path, "stocks", "AAPL")
    _insert_transaction(
        database_path,
        asset_id=asset_id,
        entry_no=1,
        transaction_date="2026-06-19",
    )

    first = runner.invoke(app, ["init"])
    second = runner.invoke(app, ["init"])

    assert first.exit_code == 0
    assert second.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 1


def test_normal_command_migrates_asset_transactions_for_legacy_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    data_dir.mkdir()
    database_path = data_dir / "fundlog.db"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE portfolios (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TEXT
            );
            CREATE TABLE capital_entries (
                id INTEGER PRIMARY KEY,
                portfolio_id INTEGER NOT NULL,
                entry_no INTEGER,
                entry_type TEXT NOT NULL,
                amount_minor INTEGER NOT NULL,
                entry_date TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TEXT
            );
            CREATE TABLE assets (
                id INTEGER PRIMARY KEY,
                portfolio_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TEXT
            );
            INSERT INTO portfolios (id, name) VALUES (1, 'stocks');
            INSERT INTO assets (id, portfolio_id, symbol)
            VALUES (10, 1, 'AAPL');
            """
        )

    result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])

    assert result.exit_code == 0
    assert (
        "No active transactions for asset 'AAPL' in portfolio 'stocks'."
        in result.output
    )
    with sqlite3.connect(database_path) as connection:
        table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'asset_transactions'
            """
        ).fetchone()
    assert table == ("asset_transactions",)


def test_asset_log_requires_initialized_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output
    assert "Traceback" not in result.output


def test_asset_log_rejects_invalid_reference(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)

    for symbol in ("/AAPL", "AAPL/", "AAPL/extra"):
        result = runner.invoke(app, ["asset", "log", symbol, "-p", "stocks"])
        assert result.exit_code == 1
        assert "Invalid symbol" in result.output


def test_asset_log_requires_active_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_asset_log_requires_active_asset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["portfolio", "create", "stocks"])

    result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])

    assert result.exit_code == 1
    assert "Active asset 'AAPL' does not exist in portfolio 'stocks'." in (
        result.output
    )


def test_asset_log_shows_deterministic_empty_message(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(app, ["asset", "log", "aapl", "-p", "stocks"])

    assert result.exit_code == 0
    assert (
        "No active transactions for asset 'AAPL' in portfolio 'stocks'."
        in result.output
    )


def test_asset_log_displays_title_columns_and_formatted_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    asset_id = _asset_id(database_path, "stocks", "AAPL")
    _insert_transaction(
        database_path,
        asset_id=asset_id,
        entry_no=7,
        transaction_date="2026-06-19",
        price_text="123456.054300",
        quantity_text="3.5000",
        fee_minor=125,
        total_minor=43_209,
        note="manual fixture",
    )

    result = runner.invoke(app, ["asset", "log", "aapl", "-p", "stocks"])

    assert result.exit_code == 0
    assert "AAPL/stocks" not in result.output
    for column in ("#", "Date", "Type", "Price", "Quantity", "Fee", "Total", "Note"):
        assert column in result.output
    assert "123,456.0543" in result.output
    assert "3.5" in result.output
    assert "1.25" in result.output
    assert "432.09" in result.output
    assert "manual fixture" in result.output
    assert " id " not in result.output.lower()


def test_asset_log_income_row_uses_placeholders(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    asset_id = _asset_id(database_path, "stocks", "AAPL")
    _insert_transaction(
        database_path,
        asset_id=asset_id,
        entry_no=1,
        transaction_date="2026-06-19",
        transaction_type="income",
        price_text=None,
        quantity_text=None,
        fee_minor=0,
        total_minor=5_000,
    )

    result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])

    assert result.exit_code == 0
    assert result.output.count("--") >= 2
    assert "0.00" in result.output
    assert "50.00" in result.output


def test_asset_log_orders_by_date_then_entry_number_and_hides_deleted_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    asset_id = _asset_id(database_path, "stocks", "AAPL")
    _insert_transaction(
        database_path,
        asset_id=asset_id,
        entry_no=3,
        transaction_date="2026-06-20",
        note="third",
    )
    _insert_transaction(
        database_path,
        asset_id=asset_id,
        entry_no=2,
        transaction_date="2026-06-19",
        note="second",
    )
    _insert_transaction(
        database_path,
        asset_id=asset_id,
        entry_no=1,
        transaction_date="2026-06-19",
        note="first",
    )
    _insert_transaction(
        database_path,
        asset_id=asset_id,
        entry_no=4,
        transaction_date="2026-06-18",
        note="deleted",
        deleted=True,
    )

    result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])

    assert result.exit_code == 0
    assert result.output.index("first") < result.output.index("second")
    assert result.output.index("second") < result.output.index("third")
    assert "deleted" not in result.output


def test_asset_transaction_entry_numbers_are_unique_per_asset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    asset_id = _asset_id(database_path, "stocks", "AAPL")
    _insert_transaction(
        database_path,
        asset_id=asset_id,
        entry_no=1,
        transaction_date="2026-06-19",
        deleted=True,
    )

    try:
        _insert_transaction(
            database_path,
            asset_id=asset_id,
            entry_no=1,
            transaction_date="2026-06-20",
        )
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("Deleted transaction entry numbers must not be reused.")
