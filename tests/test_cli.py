"""Smoke tests for the FundLog CLI scaffold."""

import sqlite3
from datetime import date
from pathlib import Path

import pytest
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


def test_inflow_creates_capital_entry(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(app, ["inflow", "stocks", "1000"])

    assert result.exit_code == 0
    assert "Inflow recorded for portfolio 'stocks'." in result.output
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entry = connection.execute(
            """
            SELECT p.name, e.entry_type, e.amount_minor, e.entry_date, e.note
            FROM capital_entries AS e
            JOIN portfolios AS p ON p.id = e.portfolio_id
            """
        ).fetchone()

    assert entry == ("stocks", "inflow", 100000, date.today().isoformat(), None)


def test_inflow_stores_decimal_amount_as_minor_units(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(
        app,
        [
            "inflow",
            "stocks",
            "1000.50",
            "--date",
            "2026-06-19",
            "--note",
            "initial deposit",
        ],
    )

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entry = connection.execute(
            "SELECT amount_minor, entry_date, note FROM capital_entries"
        ).fetchone()

    assert entry == (100050, "2026-06-19", "initial deposit")


def test_inflow_rejects_zero_amount(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(app, ["inflow", "stocks", "0"])

    assert result.exit_code == 1
    assert "Amount must be greater than zero." in result.output


def test_inflow_rejects_negative_amount(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(app, ["inflow", "stocks", "-10"])

    assert result.exit_code == 1
    assert "Amount must be greater than zero." in result.output


def test_inflow_rejects_invalid_amount(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(app, ["inflow", "stocks", "not-a-number"])

    assert result.exit_code == 1
    assert "Invalid amount: 'not-a-number'." in result.output


def test_inflow_rejects_more_than_two_decimal_places(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(app, ["inflow", "stocks", "10.001"])

    assert result.exit_code == 1
    assert "Amount cannot have more than 2 decimal places." in result.output


def test_inflow_fails_before_init(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["inflow", "stocks", "1000"])

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_inflow_fails_for_unknown_portfolio(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["inflow", "stocks", "1000"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_inflow_fails_for_soft_deleted_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        connection.execute(
            "UPDATE portfolios SET deleted_at = CURRENT_TIMESTAMP WHERE name = ?",
            ("stocks",),
        )

    result = runner.invoke(app, ["inflow", "stocks", "1000"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_outflow_creates_capital_entry(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])

    result = runner.invoke(app, ["outflow", "stocks", "250"])

    assert result.exit_code == 0
    assert "Outflow recorded for portfolio 'stocks'." in result.output
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entry = connection.execute(
            """
            SELECT entry_type, amount_minor, entry_date, note
            FROM capital_entries
            WHERE entry_type = 'outflow'
            """
        ).fetchone()

    assert entry == ("outflow", 25000, date.today().isoformat(), None)


def test_outflow_stores_decimal_amount_as_minor_units(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])

    result = runner.invoke(
        app,
        [
            "outflow",
            "stocks",
            "250.50",
            "--date",
            "2026-06-19",
            "--note",
            "withdrawal",
        ],
    )

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entry = connection.execute(
            """
            SELECT amount_minor, entry_date, note
            FROM capital_entries
            WHERE entry_type = 'outflow'
            """
        ).fetchone()

    assert entry == (25050, "2026-06-19", "withdrawal")


@pytest.mark.parametrize(
    ("amount", "message"),
    [
        ("0", "Amount must be greater than zero."),
        ("-10", "Amount must be greater than zero."),
        ("not-a-number", "Invalid amount: 'not-a-number'."),
        ("10.001", "Amount cannot have more than 2 decimal places."),
    ],
)
def test_outflow_rejects_invalid_amounts(
    tmp_path: Path,
    monkeypatch,
    amount: str,
    message: str,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])

    result = runner.invoke(app, ["outflow", "stocks", amount])

    assert result.exit_code == 1
    assert message in result.output


def test_outflow_fails_before_init(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["outflow", "stocks", "250"])

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_outflow_fails_for_unknown_portfolio(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["outflow", "stocks", "250"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_outflow_fails_when_cash_is_insufficient(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "100"])

    result = runner.invoke(app, ["outflow", "stocks", "100.01"])

    assert result.exit_code == 1
    assert "Insufficient cash in portfolio 'stocks'." in result.output
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        outflow_count = connection.execute(
            "SELECT COUNT(*) FROM capital_entries WHERE entry_type = 'outflow'"
        ).fetchone()[0]

    assert outflow_count == 0


def test_outflow_succeeds_when_cash_is_exactly_enough(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "250.50"])

    result = runner.invoke(app, ["outflow", "stocks", "250.50"])

    assert result.exit_code == 0


def test_outflow_cash_check_includes_prior_active_outflows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "500"])
    runner.invoke(app, ["outflow", "stocks", "400"])

    result = runner.invoke(app, ["outflow", "stocks", "100.01"])

    assert result.exit_code == 1
    assert "Insufficient cash in portfolio 'stocks'." in result.output


def test_outflow_cash_check_ignores_soft_deleted_entries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "500"])
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        connection.execute(
            """
            UPDATE capital_entries
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE entry_type = 'inflow'
            """
        )

    result = runner.invoke(app, ["outflow", "stocks", "1"])

    assert result.exit_code == 1
    assert "Insufficient cash in portfolio 'stocks'." in result.output


def test_summary_for_portfolio_with_no_entries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(app, ["summary", "stocks"])

    assert result.exit_code == 0
    for heading in (
        "Portfolio",
        "Capital",
        "Cash",
        "Positions",
        "Book Value",
        "Realized PnL",
        "Income",
        "Return",
    ):
        assert heading in result.output
    assert "stocks" in result.output
    assert result.output.count("0.00") >= 6
    assert "0.00%" in result.output


def test_summary_after_inflow(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000.50"])

    result = runner.invoke(app, ["summary", "stocks"])

    assert result.exit_code == 0
    assert result.output.count("1000.50") == 3


def test_summary_after_inflow_and_outflow(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["outflow", "stocks", "250.25"])

    result = runner.invoke(app, ["summary", "stocks"])

    assert result.exit_code == 0
    assert result.output.count("749.75") == 3


def test_summary_ignores_soft_deleted_entries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["inflow", "stocks", "250"])
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        connection.execute(
            """
            UPDATE capital_entries
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE amount_minor = 25000
            """
        )

    result = runner.invoke(app, ["summary", "stocks"])

    assert result.exit_code == 0
    assert result.output.count("1000.00") == 3
    assert "1250.00" not in result.output


def test_summary_ignores_soft_deleted_outflow(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["outflow", "stocks", "250"])
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        connection.execute(
            """
            UPDATE capital_entries
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE entry_type = 'outflow'
            """
        )

    result = runner.invoke(app, ["summary", "stocks"])

    assert result.exit_code == 0
    assert result.output.count("1000.00") == 3
    assert "750.00" not in result.output


def test_summary_fails_before_init(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["summary", "stocks"])

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_summary_fails_for_unknown_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["summary", "stocks"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_summary_formats_money_with_two_decimal_places(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1.2"])

    result = runner.invoke(app, ["summary", "stocks"])

    assert result.exit_code == 0
    assert result.output.count("1.20") == 3
    assert "0.00" in result.output
    assert "0.00%" in result.output


def test_summary_hides_internal_and_ambiguous_columns(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(app, ["summary", "stocks"])

    assert result.exit_code == 0
    assert "│ id " not in result.output
    assert "Invested" not in result.output
    assert "│ Value " not in result.output
    assert "│ PnL " not in result.output


def test_summary_v01_book_fields_are_deterministic(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["outflow", "stocks", "250"])

    result = runner.invoke(app, ["summary", "stocks"])

    assert result.exit_code == 0
    assert result.output.count("750.00") == 3
    assert "Positions" in result.output
    assert "Book Value" in result.output
    assert "Realized PnL" in result.output
    assert "Income" in result.output
    assert result.output.count("0.00") >= 4
    assert "0.00%" in result.output


def test_summary_all_is_not_implemented() -> None:
    result = runner.invoke(app, ["summary", "--all"])

    assert result.exit_code == 1
    assert "--all option is not implemented yet." in result.output


def test_log_fails_before_init(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["log", "stocks"])

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_log_fails_for_unknown_portfolio(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["log", "stocks"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_log_for_empty_portfolio(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(app, ["log", "stocks"])

    assert result.exit_code == 0
    assert "No active capital entries for portfolio 'stocks'." in result.output


def test_log_shows_inflow_entry_with_date_note_and_amount(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(
        app,
        [
            "inflow",
            "stocks",
            "1000.5",
            "--date",
            "2026-06-19",
            "--note",
            "initial deposit",
        ],
    )

    result = runner.invoke(app, ["log", "stocks"])

    assert result.exit_code == 0
    for heading in ("id", "Date", "Type", "Amount", "Note"):
        assert heading in result.output
    assert "2026-06-19" in result.output
    assert "inflow" in result.output
    assert "1000.50" in result.output
    assert "initial deposit" in result.output


def test_log_shows_outflow_entry(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "500"])
    runner.invoke(
        app,
        [
            "outflow",
            "stocks",
            "250",
            "--date",
            "2026-06-20",
            "--note",
            "withdrawal",
        ],
    )

    result = runner.invoke(app, ["log", "stocks"])

    assert result.exit_code == 0
    assert "outflow" in result.output
    assert "250.00" in result.output
    assert "2026-06-20" in result.output
    assert "withdrawal" in result.output


def test_log_ignores_soft_deleted_entries(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(
        app,
        ["inflow", "stocks", "100", "--note", "keep this"],
    )
    runner.invoke(
        app,
        ["inflow", "stocks", "200", "--note", "hide this"],
    )
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        connection.execute(
            """
            UPDATE capital_entries
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE note = 'hide this'
            """
        )

    result = runner.invoke(app, ["log", "stocks"])

    assert result.exit_code == 0
    assert "keep this" in result.output
    assert "hide this" not in result.output


def test_log_only_shows_selected_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["create", "crypto"])
    runner.invoke(app, ["inflow", "stocks", "100", "--note", "stock entry"])
    runner.invoke(app, ["inflow", "crypto", "200", "--note", "crypto entry"])

    result = runner.invoke(app, ["log", "stocks"])

    assert result.exit_code == 0
    assert "stock entry" in result.output
    assert "crypto entry" not in result.output


def test_log_ordering_is_date_then_id(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(
        app,
        ["inflow", "stocks", "300", "--date", "2026-06-20", "--note", "third"],
    )
    runner.invoke(
        app,
        ["inflow", "stocks", "100", "--date", "2026-06-19", "--note", "first"],
    )
    runner.invoke(
        app,
        ["inflow", "stocks", "200", "--date", "2026-06-19", "--note", "second"],
    )

    result = runner.invoke(app, ["log", "stocks"])

    assert result.exit_code == 0
    assert result.output.index("first") < result.output.index("second")
    assert result.output.index("second") < result.output.index("third")


def test_edit_remains_a_placeholder() -> None:
    result = runner.invoke(app, ["edit", "stocks", "1", "--amount", "100"])

    assert result.exit_code == 0
    assert PLACEHOLDER_MESSAGE in result.output
