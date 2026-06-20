"""CLI tests for the initial asset foundation."""

import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from fundlog.cli import app

runner = CliRunner()


def _initialize_with_portfolio(
    tmp_path: Path,
    monkeypatch,
    portfolio: str = "stocks",
) -> Path:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["create", portfolio]).exit_code == 0
    return data_dir / "fundlog.db"


def test_asset_help_lists_add_and_list() -> None:
    result = runner.invoke(app, ["asset", "--help"])

    assert result.exit_code == 0
    assert "add" in result.output
    assert "list" in result.output


def test_asset_add_requires_initialized_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["asset", "add", "stocks", "AAPL"])

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_asset_add_requires_active_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["asset", "add", "stocks", "AAPL"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_asset_add_creates_normalized_asset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_with_portfolio(tmp_path, monkeypatch)

    result = runner.invoke(app, ["asset", "add", "stocks", "aapl"])

    assert result.exit_code == 0
    assert "Asset 'AAPL' added to portfolio 'stocks'." in result.output
    with sqlite3.connect(database_path) as connection:
        assets = connection.execute("SELECT symbol, deleted_at FROM assets").fetchall()

    assert assets == [("AAPL", None)]


def test_asset_add_creates_multiple_assets_atomically(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_with_portfolio(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["asset", "add", "stocks", "aapl", "AMZN", "msft"],
    )

    assert result.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        symbols = connection.execute(
            "SELECT symbol FROM assets ORDER BY symbol"
        ).fetchall()

    assert symbols == [("AAPL",), ("AMZN",), ("MSFT",)]


def test_asset_add_rejects_duplicate_active_asset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_with_portfolio(tmp_path, monkeypatch)
    runner.invoke(app, ["asset", "add", "stocks", "AAPL"])

    result = runner.invoke(app, ["asset", "add", "stocks", "aapl"])

    assert result.exit_code == 1
    assert "Active asset 'AAPL' already exists" in result.output
    with sqlite3.connect(database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM assets").fetchone()[0]

    assert count == 1


def test_asset_add_rejects_duplicate_symbols_in_same_command(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_with_portfolio(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["asset", "add", "stocks", "AAPL", "aapl"],
    )

    assert result.exit_code == 1
    assert "Duplicate symbols were provided" in result.output
    with sqlite3.connect(database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM assets").fetchone()[0]

    assert count == 0


def test_failed_multi_asset_add_creates_no_assets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_with_portfolio(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["asset", "add", "stocks", "AAPL", "INVALID/SYMBOL", "MSFT"],
    )

    assert result.exit_code == 1
    assert "Invalid symbol 'INVALID/SYMBOL'" in result.output
    with sqlite3.connect(database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM assets").fetchone()[0]

    assert count == 0


def test_multi_asset_add_with_existing_duplicate_creates_none(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_with_portfolio(tmp_path, monkeypatch)
    runner.invoke(app, ["asset", "add", "stocks", "AAPL"])

    result = runner.invoke(
        app,
        ["asset", "add", "stocks", "MSFT", "aapl"],
    )

    assert result.exit_code == 1
    with sqlite3.connect(database_path) as connection:
        symbols = connection.execute(
            "SELECT symbol FROM assets ORDER BY symbol"
        ).fetchall()

    assert symbols == [("AAPL",)]


def test_soft_deleted_symbol_can_be_added_again(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_with_portfolio(tmp_path, monkeypatch)
    runner.invoke(app, ["asset", "add", "stocks", "AAPL"])
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE assets SET deleted_at = CURRENT_TIMESTAMP WHERE symbol = 'AAPL'"
        )

    result = runner.invoke(app, ["asset", "add", "stocks", "aapl"])

    assert result.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        assets = connection.execute(
            "SELECT symbol, deleted_at FROM assets ORDER BY id"
        ).fetchall()

    assert assets[0][0] == "AAPL"
    assert assets[0][1] is not None
    assert assets[1] == ("AAPL", None)


def test_multi_asset_add_rolls_back_if_insert_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_with_portfolio(tmp_path, monkeypatch)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_msft_asset
            BEFORE INSERT ON assets
            WHEN NEW.symbol = 'MSFT'
            BEGIN
                SELECT RAISE(ABORT, 'forced asset failure');
            END
            """
        )

    result = runner.invoke(
        app,
        ["asset", "add", "stocks", "AAPL", "MSFT"],
    )

    assert result.exit_code == 1
    with sqlite3.connect(database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM assets").fetchone()[0]

    assert count == 0


def test_asset_list_requires_initialized_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["asset", "list", "stocks"])

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output


def test_asset_list_requires_active_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["asset", "list", "stocks"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_asset_list_prints_empty_message(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_with_portfolio(tmp_path, monkeypatch)

    result = runner.invoke(app, ["asset", "list", "stocks"])

    assert result.exit_code == 0
    assert "No active assets for portfolio 'stocks'." in result.output


def test_asset_list_shows_uppercase_symbols_in_order(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_with_portfolio(tmp_path, monkeypatch)
    runner.invoke(
        app,
        ["asset", "add", "stocks", "msft", "aapl", "BRK.B"],
    )

    result = runner.invoke(app, ["asset", "list", "stocks"])

    assert result.exit_code == 0
    assert result.output.index("AAPL") < result.output.index("BRK.B")
    assert result.output.index("BRK.B") < result.output.index("MSFT")


def test_asset_list_uses_foundation_columns_and_zero_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_with_portfolio(tmp_path, monkeypatch)
    runner.invoke(app, ["asset", "add", "stocks", "AAPL"])

    result = runner.invoke(app, ["asset", "list", "stocks"])

    assert result.exit_code == 0
    for column in (
        "Symbol",
        "Quantity",
        "Cost Basis",
        "Realized PnL",
        "Income",
        "Realized Return",
    ):
        assert column in result.output
    assert "0.00" in result.output
    assert "0.00%" in result.output
    asset_row = next(line for line in result.output.splitlines() if "AAPL" in line)
    assert " 0 " in asset_row
    assert " id " not in result.output.lower()


def test_adding_assets_does_not_change_portfolio_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "1000"])
    before = runner.invoke(app, ["summary", "stocks"])

    add_result = runner.invoke(app, ["asset", "add", "stocks", "AAPL", "MSFT"])
    after = runner.invoke(app, ["summary", "stocks"])

    assert add_result.exit_code == 0
    assert before.exit_code == 0
    assert after.exit_code == 0
    assert after.output == before.output


def test_normal_command_migrates_assets_table_for_legacy_database(
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
            INSERT INTO portfolios (id, name) VALUES (1, 'stocks');
            """
        )

    result = runner.invoke(app, ["asset", "add", "stocks", "AAPL"])

    assert result.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        asset = connection.execute("SELECT portfolio_id, symbol FROM assets").fetchone()
        indexes = {row[1] for row in connection.execute("PRAGMA index_list(assets)")}

    assert asset == (1, "AAPL")
    assert "uq_active_asset_symbol" in indexes
