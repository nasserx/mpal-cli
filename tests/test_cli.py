"""Smoke tests for the FundLog CLI scaffold."""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fundlog import __version__
from fundlog.cli import app

runner = CliRunner()

COMMANDS = {
    "asset",
    "init",
    "create",
    "inflow",
    "outflow",
    "summary",
    "log",
    "edit",
    "reset",
    "delete",
}


def test_cli_imports_successfully() -> None:
    assert app is not None


def test_help_exits_successfully() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Manually track portfolio capital" in result.output
    assert "Examples:" in result.output
    assert "fundlog create stocks --initial 5000" in result.output
    assert "fundlog delete stocks --yes" in result.output


def test_version_exits_successfully() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert f"FundLog {__version__}" in result.output


def test_commands_are_registered() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in COMMANDS:
        assert command in result.output


@pytest.mark.parametrize("command", sorted(COMMANDS))
def test_command_help_exits_successfully(command: str) -> None:
    result = runner.invoke(app, [command, "--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "Traceback" not in result.output


def test_remove_command_is_not_supported() -> None:
    result = runner.invoke(app, ["remove", "stocks", "1"])

    assert result.exit_code == 2
    assert "No such command 'remove'" in result.output


def test_delete_rejects_entry_number_with_yes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "1000"])

    result = runner.invoke(app, ["delete", "stocks", "1", "--yes"])

    assert result.exit_code == 1
    assert "Do not combine an entry number with --yes." in result.output


def test_init_help_exits_successfully() -> None:
    result = runner.invoke(app, ["init", "--help"])

    assert result.exit_code == 0
    assert "Initialize FundLog's local database" in result.output


def test_edit_help_references_portfolio_log_entry_number() -> None:
    result = runner.invoke(app, ["edit", "--help"])

    assert result.exit_code == 0
    assert "Edit a capital entry by its number in the portfolio log." in result.output
    assert "Entry number shown by 'fundlog log" in result.output
    assert "<portfolio>'." in result.output


def test_delete_help_explains_entry_and_portfolio_soft_delete() -> None:
    result = runner.invoke(app, ["delete", "--help"])

    assert result.exit_code == 0
    assert "Delete an entry, or delete a portfolio with --yes." in result.output
    assert "Entry number shown by 'fundlog log" in result.output
    assert "<portfolio>'." in result.output
    assert "Soft-delete the entire portfolio and its entries." in result.output


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

    assert tables == {
        "portfolios",
        "capital_entries",
        "assets",
        "asset_transactions",
    }
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
        "entry_no",
        "entry_type",
        "amount_minor",
        "entry_date",
        "note",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    with sqlite3.connect(database_path) as connection:
        asset_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(assets)")
        }
        transaction_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(asset_transactions)")
        }

    assert asset_columns == {
        "id",
        "portfolio_id",
        "symbol",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert transaction_columns == {
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


def test_init_reports_unusable_data_directory_without_traceback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_path = tmp_path / "not-a-directory"
    data_path.write_text("occupied", encoding="utf-8")
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_path))

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 1
    assert "FundLog could not initialize the local database." in result.output
    assert "Traceback" not in result.output


def test_init_migrates_and_backfills_portfolio_entry_numbers(
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
                entry_type TEXT NOT NULL,
                amount_minor INTEGER NOT NULL,
                entry_date TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TEXT
            );
            INSERT INTO portfolios (id, name) VALUES (10, 'stocks'), (20, 'crypto');
            INSERT INTO capital_entries (
                id, portfolio_id, entry_type, amount_minor, entry_date
            )
            VALUES
                (5, 10, 'inflow', 100000, '2026-06-18'),
                (9, 10, 'outflow', 25000, '2026-06-19'),
                (12, 20, 'inflow', 50000, '2026-06-20');
            """
        )

    first_result = runner.invoke(app, ["init"])
    second_result = runner.invoke(app, ["init"])

    assert first_result.exit_code == 0
    assert second_result.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(capital_entries)")
        }
        entries = connection.execute(
            """
            SELECT portfolio_id, id, entry_no
            FROM capital_entries
            ORDER BY portfolio_id, id
            """
        ).fetchall()
        indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(capital_entries)")
        }

    assert "entry_no" in columns
    assert entries == [(10, 5, 1), (10, 9, 2), (20, 12, 1)]
    assert "uq_portfolio_entry_no" in indexes
    log_result = runner.invoke(app, ["log", "stocks"])
    assert log_result.exit_code == 0
    assert "│ 1 │" in log_result.output
    assert "│ 2 │" in log_result.output
    assert "│ 5 │" not in log_result.output
    assert "│ 9 │" not in log_result.output


def test_normal_commands_migrate_legacy_entry_numbers_without_traceback(
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
                entry_type TEXT NOT NULL,
                amount_minor INTEGER NOT NULL,
                entry_date TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TEXT
            );
            INSERT INTO portfolios (id, name) VALUES (10, 'stocks'), (20, 'crypto');
            INSERT INTO capital_entries (
                id, portfolio_id, entry_type, amount_minor, entry_date, note
            )
            VALUES
                (5, 10, 'inflow', 100000, '2026-06-18', 'deposit'),
                (9, 10, 'outflow', 25000, '2026-06-19', 'withdrawal'),
                (12, 20, 'inflow', 50000, '2026-06-20', 'crypto deposit');
            """
        )

    first_log = runner.invoke(app, ["log", "stocks"])
    second_log = runner.invoke(app, ["log", "stocks"])
    summary_result = runner.invoke(app, ["summary", "stocks"])
    duplicate_result = runner.invoke(app, ["create", "stocks"])
    edit_result = runner.invoke(
        app,
        ["edit", "stocks", "1", "--amount", "1250"],
    )
    delete_result = runner.invoke(app, ["delete", "stocks", "2"])
    final_log = runner.invoke(app, ["log", "stocks"])

    for result in (
        first_log,
        second_log,
        summary_result,
        edit_result,
        delete_result,
        final_log,
    ):
        assert result.exit_code == 0
        assert "Traceback" not in result.output

    assert "│ 1 │" in first_log.output
    assert "│ 2 │" in first_log.output
    assert "│ 5 │" not in first_log.output
    assert "│ 9 │" not in first_log.output
    assert "750.00" in summary_result.output
    assert "1,250.00" in final_log.output
    assert "withdrawal" not in final_log.output
    assert duplicate_result.exit_code == 1
    assert "An active portfolio named 'stocks' already exists." in (
        duplicate_result.output
    )
    assert "Traceback" not in duplicate_result.output

    with sqlite3.connect(database_path) as connection:
        entries = connection.execute(
            """
            SELECT portfolio_id, id, entry_no, amount_minor, deleted_at
            FROM capital_entries
            ORDER BY portfolio_id, id
            """
        ).fetchall()
        portfolio_indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(portfolios)")
        }

    assert entries[0][0:4] == (10, 5, 1, 125000)
    assert entries[0][4] is None
    assert entries[1][0:3] == (10, 9, 2)
    assert entries[1][4] is not None
    assert entries[2][0:4] == (20, 12, 1, 50000)
    assert "uq_active_portfolio_name" in portfolio_indexes


def test_schema_errors_are_concise_without_traceback(
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
                deleted_at TEXT
            );
            CREATE TABLE capital_entries (
                id INTEGER PRIMARY KEY,
                portfolio_id INTEGER NOT NULL
            );
            INSERT INTO portfolios (id, name) VALUES (1, 'stocks');
            """
        )

    result = runner.invoke(app, ["log", "stocks"])

    assert result.exit_code == 1
    assert "FundLog could not access the local database safely." in result.output
    assert "Traceback" not in result.output
    assert "sqlite3." not in result.output


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


def test_create_with_initial_creates_portfolio_and_inflow(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["create", "stocks", "--initial", "5000"])

    assert result.exit_code == 0
    assert "Portfolio 'stocks' created with initial capital." in result.output
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        portfolio = connection.execute(
            "SELECT id, name, deleted_at FROM portfolios"
        ).fetchone()
        entries = connection.execute(
            """
            SELECT
                portfolio_id,
                entry_no,
                entry_type,
                amount_minor,
                entry_date,
                deleted_at
            FROM capital_entries
            """
        ).fetchall()

    assert portfolio[1:] == ("stocks", None)
    assert entries == [
        (portfolio[0], 1, "inflow", 500000, date.today().isoformat(), None)
    ]


def test_create_with_initial_supports_decimal_amount(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["create", "stocks", "--initial", "5000.50"])

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        amount_minor = connection.execute(
            "SELECT amount_minor FROM capital_entries"
        ).fetchone()[0]

    assert amount_minor == 500050


@pytest.mark.parametrize(
    ("amount", "message"),
    [
        ("0", "Amount must be greater than zero."),
        ("-10", "Amount must be greater than zero."),
        ("not-a-number", "Invalid amount: 'not-a-number'."),
        ("10.001", "Amount cannot have more than 2 decimal places."),
        ("NaN", "Invalid amount: 'NaN'."),
        ("Infinity", "Invalid amount: 'Infinity'."),
    ],
)
def test_create_with_initial_rejects_invalid_amount(
    tmp_path: Path,
    monkeypatch,
    amount: str,
    message: str,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["create", "stocks", "--initial", amount])

    assert result.exit_code == 1
    assert message in result.output
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        portfolio_count = connection.execute(
            "SELECT COUNT(*) FROM portfolios"
        ).fetchone()[0]
        entry_count = connection.execute(
            "SELECT COUNT(*) FROM capital_entries"
        ).fetchone()[0]

    assert portfolio_count == 0
    assert entry_count == 0


def test_create_with_initial_fails_before_init(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["create", "stocks", "--initial", "5000"])

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_duplicate_create_with_initial_creates_no_extra_entry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "5000"])

    result = runner.invoke(app, ["create", "stocks", "--initial", "1000"])

    assert result.exit_code == 1
    assert "An active portfolio named 'stocks' already exists." in result.output
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        portfolio_count = connection.execute(
            "SELECT COUNT(*) FROM portfolios"
        ).fetchone()[0]
        entries = connection.execute(
            "SELECT entry_type, amount_minor FROM capital_entries"
        ).fetchall()

    assert portfolio_count == 1
    assert entries == [("inflow", 500000)]


def test_create_with_initial_rolls_back_if_entry_insert_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_initial_entry
            BEFORE INSERT ON capital_entries
            BEGIN
                SELECT RAISE(ABORT, 'forced entry failure');
            END
            """
        )

    result = runner.invoke(app, ["create", "stocks", "--initial", "5000"])

    assert result.exit_code == 1
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        portfolio_count = connection.execute(
            "SELECT COUNT(*) FROM portfolios"
        ).fetchone()[0]
        entry_count = connection.execute(
            "SELECT COUNT(*) FROM capital_entries"
        ).fetchone()[0]

    assert portfolio_count == 0
    assert entry_count == 0


def test_summary_reflects_create_initial(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "5000.50"])

    result = runner.invoke(app, ["summary", "stocks"])

    assert result.exit_code == 0
    assert result.output.count("5,000.50") == 3
    assert result.output.count("0.00") >= 4
    assert "0.00%" in result.output


def test_log_reflects_create_initial(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "5000.50"])

    result = runner.invoke(app, ["log", "stocks"])

    assert result.exit_code == 0
    assert "inflow" in result.output
    assert "5,000.50" in result.output
    assert date.today().isoformat() in result.output


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


def test_inflow_accepts_past_date(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    past_date = date.today() - timedelta(days=1)

    result = runner.invoke(
        app,
        ["inflow", "stocks", "1000", "--date", past_date.isoformat()],
    )

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entry_date = connection.execute(
            "SELECT entry_date FROM capital_entries"
        ).fetchone()[0]
    assert entry_date == past_date.isoformat()


def test_inflow_accepts_today(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    today = date.today()

    result = runner.invoke(
        app,
        ["inflow", "stocks", "1000", "--date", today.isoformat()],
    )

    assert result.exit_code == 0


def test_inflow_rejects_future_date(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    future_date = date.today() + timedelta(days=1)

    result = runner.invoke(
        app,
        ["inflow", "stocks", "1000", "--date", future_date.isoformat()],
    )

    assert result.exit_code == 1
    assert "Date cannot be in the future." in result.output


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


def test_outflow_rejects_future_date(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "1000"])
    future_date = date.today() + timedelta(days=1)

    result = runner.invoke(
        app,
        ["outflow", "stocks", "250", "--date", future_date.isoformat()],
    )

    assert result.exit_code == 1
    assert "Date cannot be in the future." in result.output


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
    assert result.output.count("1,000.50") == 3


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
    assert result.output.count("1,000.00") == 3
    assert "1,250.00" not in result.output


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
    assert result.output.count("1,000.00") == 3
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


def test_summary_all_fails_before_init(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["summary", "--all"])

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_summary_all_with_no_portfolios(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["summary", "--all"])

    assert result.exit_code == 0
    assert "No active portfolios." in result.output


def test_summary_all_lists_multiple_active_portfolios(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["create", "crypto"])

    result = runner.invoke(app, ["summary", "--all"])

    assert result.exit_code == 0
    assert "stocks" in result.output
    assert "crypto" in result.output


def test_summary_all_uses_exact_documented_columns(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(app, ["summary", "--all"])

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
    assert "│ id " not in result.output
    assert "Invested" not in result.output
    assert "│ Value " not in result.output
    assert "│ PnL " not in result.output


def test_summary_all_derives_each_portfolio_independently(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["create", "crypto"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["outflow", "stocks", "250"])
    runner.invoke(app, ["inflow", "crypto", "500.50"])

    result = runner.invoke(app, ["summary", "--all"])

    assert result.exit_code == 0
    assert result.output.count("750.00") == 3
    assert result.output.count("500.50") == 3


def test_summary_all_ignores_soft_deleted_entries(
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
            "UPDATE capital_entries SET deleted_at = CURRENT_TIMESTAMP WHERE id = 2"
        )

    result = runner.invoke(app, ["summary", "--all"])

    assert result.exit_code == 0
    assert result.output.count("1,000.00") == 3
    assert "1,250.00" not in result.output


def test_summary_all_ignores_soft_deleted_portfolios(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["create", "crypto"])
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        connection.execute(
            "UPDATE portfolios SET deleted_at = CURRENT_TIMESTAMP WHERE name = ?",
            ("crypto",),
        )

    result = runner.invoke(app, ["summary", "--all"])

    assert result.exit_code == 0
    assert "stocks" in result.output
    assert "crypto" not in result.output


def test_summary_all_ordering_is_name_ascending(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["create", "crypto"])
    runner.invoke(app, ["create", "gold"])

    result = runner.invoke(app, ["summary", "--all"])

    assert result.exit_code == 0
    assert result.output.index("crypto") < result.output.index("gold")
    assert result.output.index("gold") < result.output.index("stocks")


def test_summary_rejects_portfolio_with_all_flag(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(app, ["summary", "stocks", "--all"])

    assert result.exit_code == 1
    assert "A portfolio name cannot be combined with --all." in result.output


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
    for heading in ("#", "Date", "Type", "Amount", "Note"):
        assert heading in result.output
    assert "│ id " not in result.output
    assert "2026-06-19" in result.output
    assert "inflow" in result.output
    assert "1,000.50" in result.output
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


def test_entry_numbers_start_at_one_for_each_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["create", "crypto"])
    runner.invoke(app, ["inflow", "stocks", "100"])
    runner.invoke(app, ["inflow", "crypto", "200"])

    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entries = connection.execute(
            """
            SELECT p.name, e.entry_no
            FROM capital_entries AS e
            JOIN portfolios AS p ON p.id = e.portfolio_id
            ORDER BY p.name
            """
        ).fetchall()

    assert entries == [("crypto", 1), ("stocks", 1)]


def test_new_entries_increment_portfolio_entry_numbers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "1000"])
    runner.invoke(app, ["inflow", "stocks", "250"])
    runner.invoke(app, ["outflow", "stocks", "100"])

    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entries = connection.execute(
            "SELECT entry_no, entry_type FROM capital_entries ORDER BY entry_no"
        ).fetchall()

    assert entries == [(1, "inflow"), (2, "inflow"), (3, "outflow")]


def test_deleted_and_reset_entries_do_not_reuse_entry_numbers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "1000"])
    runner.invoke(app, ["inflow", "stocks", "250"])
    runner.invoke(app, ["delete", "stocks", "2"])
    runner.invoke(app, ["inflow", "stocks", "300"])
    runner.invoke(app, ["reset", "stocks", "--yes"])
    runner.invoke(app, ["inflow", "stocks", "400"])

    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entries = connection.execute(
            "SELECT entry_no, deleted_at FROM capital_entries ORDER BY entry_no"
        ).fetchall()

    assert [entry[0] for entry in entries] == [1, 2, 3, 4]
    assert entries[3][1] is None


def test_reused_portfolio_name_starts_entry_numbers_at_one(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "1000"])
    runner.invoke(app, ["delete", "stocks", "--yes"])
    runner.invoke(app, ["create", "stocks", "--initial", "500"])

    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entries = connection.execute(
            """
            SELECT p.id, p.deleted_at, e.entry_no
            FROM portfolios AS p
            JOIN capital_entries AS e ON e.portfolio_id = p.id
            ORDER BY p.id
            """
        ).fetchall()

    assert entries[0][1] is not None
    assert entries[0][2] == 1
    assert entries[1][1] is None
    assert entries[1][2] == 1


def test_log_ordering_is_date_then_entry_number(
    tmp_path: Path,
    monkeypatch,
) -> None:
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


def test_edit_amount(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])

    result = runner.invoke(app, ["edit", "stocks", "1", "--amount", "500.50"])

    assert result.exit_code == 0
    assert "Capital entry 1 updated for portfolio 'stocks'." in result.output
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entry = connection.execute(
            "SELECT entry_type, amount_minor FROM capital_entries WHERE id = 1"
        ).fetchone()

    assert entry == ("inflow", 50050)


def test_edit_date(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])

    result = runner.invoke(
        app,
        ["edit", "stocks", "1", "--date", "2026-06-19"],
    )

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entry_date = connection.execute(
            "SELECT entry_date FROM capital_entries WHERE id = 1"
        ).fetchone()[0]

    assert entry_date == "2026-06-19"


def test_edit_note(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000", "--note", "original"])

    result = runner.invoke(
        app,
        ["edit", "stocks", "1", "--note", "corrected deposit"],
    )

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        note = connection.execute(
            "SELECT note FROM capital_entries WHERE id = 1"
        ).fetchone()[0]

    assert note == "corrected deposit"


def test_edit_multiple_fields_atomically(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])

    result = runner.invoke(
        app,
        [
            "edit",
            "stocks",
            "1",
            "--amount",
            "750.25",
            "--date",
            "2026-06-19",
            "--note",
            "corrected deposit",
        ],
    )

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entry = connection.execute(
            """
            SELECT entry_type, amount_minor, entry_date, note
            FROM capital_entries
            WHERE id = 1
            """
        ).fetchone()

    assert entry == ("inflow", 75025, "2026-06-19", "corrected deposit")


def test_edit_multiple_fields_roll_back_together_on_cash_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(
        app,
        [
            "outflow",
            "stocks",
            "250",
            "--date",
            "2026-06-18",
            "--note",
            "original",
        ],
    )

    result = runner.invoke(
        app,
        [
            "edit",
            "stocks",
            "2",
            "--amount",
            "1000.01",
            "--date",
            "2026-06-19",
            "--note",
            "changed",
        ],
    )

    assert result.exit_code == 1
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entry = connection.execute(
            """
            SELECT amount_minor, entry_date, note
            FROM capital_entries
            WHERE id = 2
            """
        ).fetchone()

    assert entry == (25000, "2026-06-18", "original")


def test_edit_fails_before_init(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["edit", "stocks", "1", "--amount", "500"])

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_edit_fails_for_unknown_portfolio(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["edit", "stocks", "1", "--amount", "500"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_edit_fails_for_unknown_entry(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(app, ["edit", "stocks", "99", "--amount", "500"])

    assert result.exit_code == 1
    assert "Capital entry 99 does not exist in portfolio 'stocks'." in result.output


def test_edit_fails_when_entry_belongs_to_another_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["create", "crypto"])
    runner.invoke(app, ["inflow", "crypto", "1000"])

    result = runner.invoke(app, ["edit", "stocks", "1", "--amount", "500"])

    assert result.exit_code == 1
    assert "Capital entry 1 does not exist in portfolio 'stocks'." in result.output


def test_edit_targets_portfolio_local_entry_number(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["create", "crypto"])
    runner.invoke(app, ["inflow", "crypto", "200"])
    runner.invoke(app, ["inflow", "stocks", "100"])

    result = runner.invoke(app, ["edit", "stocks", "1", "--amount", "150"])

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entries = connection.execute(
            """
            SELECT p.name, e.entry_no, e.amount_minor
            FROM capital_entries AS e
            JOIN portfolios AS p ON p.id = e.portfolio_id
            ORDER BY p.name
            """
        ).fetchall()

    assert entries == [("crypto", 1, 20000), ("stocks", 1, 15000)]


def test_edit_fails_for_soft_deleted_entry(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        connection.execute(
            "UPDATE capital_entries SET deleted_at = CURRENT_TIMESTAMP WHERE id = 1"
        )

    result = runner.invoke(app, ["edit", "stocks", "1", "--amount", "500"])

    assert result.exit_code == 1
    assert "Capital entry 1 is not active." in result.output


def test_edit_fails_without_edit_options(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])

    result = runner.invoke(app, ["edit", "stocks", "1"])

    assert result.exit_code == 1
    assert "Provide at least one of --amount, --date, or --note." in result.output


@pytest.mark.parametrize(
    ("amount", "message"),
    [
        ("0", "Amount must be greater than zero."),
        ("-10", "Amount must be greater than zero."),
        ("not-a-number", "Invalid amount: 'not-a-number'."),
        ("10.001", "Amount cannot have more than 2 decimal places."),
    ],
)
def test_edit_rejects_invalid_amount(
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

    result = runner.invoke(app, ["edit", "stocks", "1", "--amount", amount])

    assert result.exit_code == 1
    assert message in result.output


def test_edit_rejects_invalid_date(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])

    result = runner.invoke(
        app,
        ["edit", "stocks", "1", "--date", "19-06-2026"],
    )

    assert result.exit_code == 1
    assert "Date must be a valid ISO date in YYYY-MM-DD format." in result.output


def test_edit_rejects_compact_date_format(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])

    result = runner.invoke(
        app,
        ["edit", "stocks", "1", "--date", "20260619"],
    )

    assert result.exit_code == 1
    assert "Date must be a valid ISO date in YYYY-MM-DD format." in result.output


def test_edit_rejects_future_date(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "1000"])
    future_date = date.today() + timedelta(days=1)

    result = runner.invoke(
        app,
        ["edit", "stocks", "1", "--date", future_date.isoformat()],
    )

    assert result.exit_code == 1
    assert "Date cannot be in the future." in result.output


def test_edit_outflow_cannot_make_cash_negative(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["outflow", "stocks", "250"])

    result = runner.invoke(
        app,
        ["edit", "stocks", "2", "--amount", "1000.01"],
    )

    assert result.exit_code == 1
    assert "Edit would make portfolio cash negative." in result.output
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        amount_minor = connection.execute(
            "SELECT amount_minor FROM capital_entries WHERE id = 2"
        ).fetchone()[0]

    assert amount_minor == 25000


def test_edit_inflow_downward_cannot_make_cash_negative(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["outflow", "stocks", "750"])

    result = runner.invoke(app, ["edit", "stocks", "1", "--amount", "500"])

    assert result.exit_code == 1
    assert "Edit would make portfolio cash negative." in result.output
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        amount_minor = connection.execute(
            "SELECT amount_minor FROM capital_entries WHERE id = 1"
        ).fetchone()[0]

    assert amount_minor == 100000


def test_edit_cash_validation_ignores_soft_deleted_entries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["outflow", "stocks", "900"])
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        connection.execute(
            "UPDATE capital_entries SET deleted_at = CURRENT_TIMESTAMP WHERE id = 2"
        )

    result = runner.invoke(app, ["edit", "stocks", "1", "--amount", "100"])

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        amount_minor = connection.execute(
            "SELECT amount_minor FROM capital_entries WHERE id = 1"
        ).fetchone()[0]

    assert amount_minor == 10000


def test_summary_reflects_edited_amount(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["edit", "stocks", "1", "--amount", "1250.50"])

    result = runner.invoke(app, ["summary", "stocks"])

    assert result.exit_code == 0
    assert result.output.count("1,250.50") == 3


def test_log_reflects_edited_fields(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000", "--note", "original"])
    runner.invoke(
        app,
        [
            "edit",
            "stocks",
            "1",
            "--amount",
            "500.25",
            "--date",
            "2026-06-19",
            "--note",
            "corrected deposit",
        ],
    )

    result = runner.invoke(app, ["log", "stocks"])

    assert result.exit_code == 0
    assert "500.25" in result.output
    assert "2026-06-19" in result.output
    assert "corrected deposit" in result.output
    assert "original" not in result.output


def test_delete_entry_soft_deletes_active_entry(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])

    result = runner.invoke(app, ["delete", "stocks", "1"])

    assert result.exit_code == 0
    assert "Capital entry 1 deleted from portfolio 'stocks'." in result.output
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        row = connection.execute(
            "SELECT id, deleted_at FROM capital_entries WHERE id = 1"
        ).fetchone()

    assert row[0] == 1
    assert row[1] is not None


def test_deleted_entry_is_hidden_from_log(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000", "--note", "removed entry"])
    runner.invoke(app, ["delete", "stocks", "1"])

    result = runner.invoke(app, ["log", "stocks"])

    assert result.exit_code == 0
    assert "No active capital entries for portfolio 'stocks'." in result.output
    assert "removed entry" not in result.output


def test_deleted_entry_is_ignored_by_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["inflow", "stocks", "250"])
    runner.invoke(app, ["delete", "stocks", "2"])

    result = runner.invoke(app, ["summary", "stocks"])

    assert result.exit_code == 0
    assert result.output.count("1,000.00") == 3
    assert "1,250.00" not in result.output


def test_delete_entry_fails_before_init(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["delete", "stocks", "1"])

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_delete_entry_fails_for_unknown_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["delete", "stocks", "1"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_delete_entry_fails_for_unknown_entry(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(app, ["delete", "stocks", "99"])

    assert result.exit_code == 1
    assert "Capital entry 99 does not exist in portfolio 'stocks'." in result.output


def test_delete_entry_number_in_another_portfolio_is_not_found(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["create", "crypto"])
    runner.invoke(app, ["inflow", "crypto", "1000"])

    result = runner.invoke(app, ["delete", "stocks", "1"])

    assert result.exit_code == 1
    assert "Capital entry 1 does not exist in portfolio 'stocks'." in result.output


def test_delete_targets_portfolio_local_entry_number(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["create", "crypto"])
    runner.invoke(app, ["inflow", "crypto", "200"])
    runner.invoke(app, ["inflow", "stocks", "100"])

    result = runner.invoke(app, ["delete", "stocks", "1"])

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entries = connection.execute(
            """
            SELECT p.name, e.entry_no, e.deleted_at
            FROM capital_entries AS e
            JOIN portfolios AS p ON p.id = e.portfolio_id
            ORDER BY p.name
            """
        ).fetchall()

    assert entries[0] == ("crypto", 1, None)
    assert entries[1][0:2] == ("stocks", 1)
    assert entries[1][2] is not None


def test_delete_entry_fails_for_already_soft_deleted_entry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["delete", "stocks", "1"])

    result = runner.invoke(app, ["delete", "stocks", "1"])

    assert result.exit_code == 1
    assert "Capital entry 1 is not active." in result.output


def test_deleting_outflow_succeeds_and_increases_cash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["outflow", "stocks", "750"])

    delete_result = runner.invoke(app, ["delete", "stocks", "2"])
    summary_result = runner.invoke(app, ["summary", "stocks"])

    assert delete_result.exit_code == 0
    assert summary_result.exit_code == 0
    assert summary_result.output.count("1,000.00") == 3
    assert "250.00" not in summary_result.output


def test_deleting_inflow_fails_if_cash_would_be_negative(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["outflow", "stocks", "750"])

    result = runner.invoke(app, ["delete", "stocks", "1"])

    assert result.exit_code == 1
    assert "Delete would make portfolio cash negative." in result.output


def test_failed_delete_entry_keeps_entry_active(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["outflow", "stocks", "750"])

    result = runner.invoke(app, ["delete", "stocks", "1"])

    assert result.exit_code == 1
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        deleted_at = connection.execute(
            "SELECT deleted_at FROM capital_entries WHERE id = 1"
        ).fetchone()[0]

    assert deleted_at is None


def test_delete_entry_cash_validation_ignores_soft_deleted_entries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["outflow", "stocks", "900"])
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        connection.execute(
            "UPDATE capital_entries SET deleted_at = CURRENT_TIMESTAMP WHERE id = 2"
        )

    result = runner.invoke(app, ["delete", "stocks", "1"])

    assert result.exit_code == 0


def test_reset_requires_initialized_database(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["reset", "stocks", "--yes"])

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_reset_fails_for_unknown_portfolio(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["reset", "stocks", "--yes"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_reset_requires_yes(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(app, ["reset", "stocks"])

    assert result.exit_code == 1
    assert "Reset requires the --yes confirmation flag." in result.output


def test_reset_without_yes_does_not_change_entries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])

    result = runner.invoke(app, ["reset", "stocks"])

    assert result.exit_code == 1
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        deleted_at = connection.execute(
            "SELECT deleted_at FROM capital_entries WHERE id = 1"
        ).fetchone()[0]

    assert deleted_at is None


def test_reset_soft_deletes_all_active_entries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["outflow", "stocks", "250"])

    result = runner.invoke(app, ["reset", "stocks", "--yes"])

    assert result.exit_code == 0
    assert "Portfolio 'stocks' reset." in result.output
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entries = connection.execute(
            "SELECT id, deleted_at FROM capital_entries ORDER BY id"
        ).fetchall()

    assert [entry[0] for entry in entries] == [1, 2]
    assert all(entry[1] is not None for entry in entries)


def test_reset_preserves_already_soft_deleted_timestamp(
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
            "UPDATE capital_entries SET deleted_at = ? WHERE id = 2",
            ("2000-01-01 00:00:00",),
        )

    result = runner.invoke(app, ["reset", "stocks", "--yes"])

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entries = connection.execute(
            "SELECT id, deleted_at FROM capital_entries ORDER BY id"
        ).fetchall()

    assert entries[0][1] is not None
    assert entries[1] == (2, "2000-01-01 00:00:00")


def test_reset_does_not_affect_other_portfolios(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["create", "crypto"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["inflow", "crypto", "500"])

    result = runner.invoke(app, ["reset", "stocks", "--yes"])

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        rows = connection.execute(
            """
            SELECT p.name, e.deleted_at
            FROM capital_entries AS e
            JOIN portfolios AS p ON p.id = e.portfolio_id
            ORDER BY p.name
            """
        ).fetchall()

    assert rows[0] == ("crypto", None)
    assert rows[1][0] == "stocks"
    assert rows[1][1] is not None


def test_log_is_empty_after_reset(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["reset", "stocks", "--yes"])

    result = runner.invoke(app, ["log", "stocks"])

    assert result.exit_code == 0
    assert "No active capital entries for portfolio 'stocks'." in result.output


def test_summary_is_zero_after_reset(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])
    runner.invoke(app, ["outflow", "stocks", "250"])
    runner.invoke(app, ["reset", "stocks", "--yes"])

    result = runner.invoke(app, ["summary", "stocks"])

    assert result.exit_code == 0
    assert result.output.count("0.00") >= 6
    assert "0.00%" in result.output
    assert "750.00" not in result.output


def test_portfolio_still_exists_after_reset(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["inflow", "stocks", "1000"])

    reset_result = runner.invoke(app, ["reset", "stocks", "--yes"])
    summary_result = runner.invoke(app, ["summary", "stocks"])

    assert reset_result.exit_code == 0
    assert summary_result.exit_code == 0
    assert "stocks" in summary_result.output
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        portfolio = connection.execute(
            "SELECT name, deleted_at FROM portfolios WHERE name = 'stocks'"
        ).fetchone()

    assert portfolio == ("stocks", None)


def test_delete_requires_initialized_database(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["delete", "stocks", "--yes"])

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_delete_fails_for_unknown_portfolio(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["delete", "stocks", "--yes"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_delete_requires_yes(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "1000"])

    result = runner.invoke(app, ["delete", "stocks"])

    assert result.exit_code == 1
    assert "Delete requires the --yes confirmation flag." in result.output


def test_delete_without_yes_does_not_change_data(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "1000"])

    result = runner.invoke(app, ["delete", "stocks"])

    assert result.exit_code == 1
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        portfolio_deleted_at = connection.execute(
            "SELECT deleted_at FROM portfolios WHERE name = 'stocks'"
        ).fetchone()[0]
        entry_deleted_at = connection.execute(
            "SELECT deleted_at FROM capital_entries"
        ).fetchone()[0]

    assert portfolio_deleted_at is None
    assert entry_deleted_at is None


def test_delete_soft_deletes_portfolio_and_active_entries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "1000"])
    runner.invoke(app, ["outflow", "stocks", "250"])

    result = runner.invoke(app, ["delete", "stocks", "--yes"])

    assert result.exit_code == 0
    assert "Portfolio 'stocks' deleted." in result.output
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        portfolios = connection.execute(
            "SELECT name, deleted_at FROM portfolios"
        ).fetchall()
        entries = connection.execute(
            "SELECT id, deleted_at FROM capital_entries ORDER BY id"
        ).fetchall()

    assert len(portfolios) == 1
    assert portfolios[0][0] == "stocks"
    assert portfolios[0][1] is not None
    assert [entry[0] for entry in entries] == [1, 2]
    assert all(entry[1] is not None for entry in entries)


def test_delete_preserves_existing_soft_deleted_entry_timestamp(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "1000"])
    runner.invoke(app, ["inflow", "stocks", "250"])
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        connection.execute(
            "UPDATE capital_entries SET deleted_at = ? WHERE id = 2",
            ("2000-01-01 00:00:00",),
        )

    result = runner.invoke(app, ["delete", "stocks", "--yes"])

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        entries = connection.execute(
            "SELECT id, deleted_at FROM capital_entries ORDER BY id"
        ).fetchall()

    assert entries[0][1] is not None
    assert entries[1] == (2, "2000-01-01 00:00:00")


def test_delete_does_not_affect_other_portfolios(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "1000"])
    runner.invoke(app, ["create", "crypto", "--initial", "500"])

    result = runner.invoke(app, ["delete", "stocks", "--yes"])

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        rows = connection.execute(
            """
            SELECT p.name, p.deleted_at, e.deleted_at
            FROM portfolios AS p
            JOIN capital_entries AS e ON e.portfolio_id = p.id
            ORDER BY p.name
            """
        ).fetchall()

    assert rows[0] == ("crypto", None, None)
    assert rows[1][0] == "stocks"
    assert rows[1][1] is not None
    assert rows[1][2] is not None


def test_deleted_portfolio_disappears_from_summary_all(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])
    runner.invoke(app, ["create", "crypto"])
    runner.invoke(app, ["delete", "stocks", "--yes"])

    result = runner.invoke(app, ["summary", "--all"])

    assert result.exit_code == 0
    assert "crypto" in result.output
    assert "stocks" not in result.output


@pytest.mark.parametrize(
    "arguments",
    [
        ["summary", "stocks"],
        ["log", "stocks"],
        ["inflow", "stocks", "100"],
        ["outflow", "stocks", "100"],
        ["edit", "stocks", "1", "--note", "changed"],
        ["delete", "stocks", "1"],
        ["reset", "stocks", "--yes"],
    ],
)
def test_deleted_portfolio_rejects_portfolio_commands(
    tmp_path: Path,
    monkeypatch,
    arguments: list[str],
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "1000"])
    runner.invoke(app, ["delete", "stocks", "--yes"])

    result = runner.invoke(app, arguments)

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_deleted_portfolio_name_can_be_reused(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "1000"])
    runner.invoke(app, ["delete", "stocks", "--yes"])

    result = runner.invoke(app, ["create", "stocks", "--initial", "500"])

    assert result.exit_code == 0
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        portfolios = connection.execute(
            "SELECT name, deleted_at FROM portfolios ORDER BY id"
        ).fetchall()
        active_entries = connection.execute(
            """
            SELECT e.amount_minor
            FROM capital_entries AS e
            JOIN portfolios AS p ON p.id = e.portfolio_id
            WHERE p.deleted_at IS NULL AND e.deleted_at IS NULL
            """
        ).fetchall()

    assert portfolios[0][0] == "stocks"
    assert portfolios[0][1] is not None
    assert portfolios[1] == ("stocks", None)
    assert active_entries == [(50000,)]


def test_delete_is_atomic_if_portfolio_update_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "1000"])
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_portfolio_delete
            BEFORE UPDATE OF deleted_at ON portfolios
            WHEN NEW.deleted_at IS NOT NULL
            BEGIN
                SELECT RAISE(ABORT, 'forced portfolio failure');
            END
            """
        )

    result = runner.invoke(app, ["delete", "stocks", "--yes"])

    assert result.exit_code == 1
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        portfolio_deleted_at = connection.execute(
            "SELECT deleted_at FROM portfolios WHERE name = 'stocks'"
        ).fetchone()[0]
        entry_deleted_at = connection.execute(
            "SELECT deleted_at FROM capital_entries"
        ).fetchone()[0]

    assert portfolio_deleted_at is None
    assert entry_deleted_at is None


def test_delete_keeps_portfolio_active_if_entry_update_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks", "--initial", "1000"])
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_entry_delete
            BEFORE UPDATE OF deleted_at ON capital_entries
            WHEN NEW.deleted_at IS NOT NULL
            BEGIN
                SELECT RAISE(ABORT, 'forced entry failure');
            END
            """
        )

    result = runner.invoke(app, ["delete", "stocks", "--yes"])

    assert result.exit_code == 1
    with sqlite3.connect(data_dir / "fundlog.db") as connection:
        portfolio_deleted_at = connection.execute(
            "SELECT deleted_at FROM portfolios WHERE name = 'stocks'"
        ).fetchone()[0]
        entry_deleted_at = connection.execute(
            "SELECT deleted_at FROM capital_entries"
        ).fetchone()[0]

    assert portfolio_deleted_at is None
    assert entry_deleted_at is None
