"""Smoke tests for the FundLog CLI scaffold."""

import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from fundlog import __version__
from fundlog.cli import PLACEHOLDER_MESSAGE, app

runner = CliRunner()

COMMANDS = {
    "init",
    "create",
    "inflow",
    "outflow",
    "summary",
    "log",
    "edit",
    "remove",
    "reset",
}


def test_cli_imports_successfully() -> None:
    assert app is not None


def test_help_exits_successfully() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Manually track portfolio capital" in result.output


def test_version_exits_successfully() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert f"FundLog {__version__}" in result.output


def test_placeholder_commands_are_registered() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in COMMANDS:
        assert command in result.output


def test_init_help_exits_successfully() -> None:
    result = runner.invoke(app, ["init", "--help"])

    assert result.exit_code == 0
    assert "Initialize FundLog's local data store" in result.output


def test_init_creates_database_and_expected_tables(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["init"])
    database_path = data_dir / "fundlog.db"

    assert result.exit_code == 0
    assert database_path.exists()
    assert "FundLog initialized at" in result.output

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        portfolio_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(portfolios)")
        }
        entry_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(capital_entries)")
        }

    assert tables == {"portfolios", "capital_entries"}
    assert portfolio_columns == {
        "id",
        "name",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert entry_columns == {
        "id",
        "portfolio_id",
        "entry_type",
        "amount_minor",
        "entry_date",
        "note",
        "created_at",
        "updated_at",
        "deleted_at",
    }


def test_init_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    first_result = runner.invoke(app, ["init"])
    database_path = data_dir / "fundlog.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("INSERT INTO portfolios (name) VALUES (?)", ("stocks",))

    second_result = runner.invoke(app, ["init"])

    assert first_result.exit_code == 0
    assert second_result.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        portfolio_count = connection.execute(
            "SELECT COUNT(*) FROM portfolios"
        ).fetchone()[0]

    assert portfolio_count == 1


def test_create_portfolio_after_init(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["create", "stocks"])

    assert result.exit_code == 0
    assert "Portfolio 'stocks' created." in result.output

    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        portfolios = connection.execute(
            "SELECT name, deleted_at FROM portfolios"
        ).fetchall()

    assert portfolios == [("stocks", None)]


def test_duplicate_active_portfolio_fails(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(app, ["create", "stocks"])

    assert result.exit_code == 1
    assert "An active portfolio named 'stocks' already exists." in result.output


def test_create_fails_before_init(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["create", "stocks"])

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_create_does_not_create_capital_entries(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["create", "stocks"])

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entry_count = connection.execute(
            "SELECT COUNT(*) FROM capital_entries"
        ).fetchone()[0]

    assert entry_count == 0


def test_create_rejects_empty_name(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["create", ""])

    assert result.exit_code == 1
    assert "Portfolio name cannot be empty." in result.output


def test_create_with_initial_is_not_implemented(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["create", "stocks", "--initial", "5000"])

    assert result.exit_code == 1
    assert "--initial option is not implemented yet." in result.output
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        portfolio_count = connection.execute(
            "SELECT COUNT(*) FROM portfolios"
        ).fetchone()[0]

    assert portfolio_count == 0


def test_non_create_command_remains_a_placeholder() -> None:
    result = runner.invoke(app, ["inflow", "stocks", "1000"])

    assert result.exit_code == 0
    assert PLACEHOLDER_MESSAGE in result.output
