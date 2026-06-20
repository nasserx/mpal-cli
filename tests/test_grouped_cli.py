"""Compatibility tests for the official grouped command hierarchy."""

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fundlog.cli import app

runner = CliRunner()


def _initialize(tmp_path: Path, monkeypatch) -> Path:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    assert runner.invoke(app, ["init"]).exit_code == 0
    return data_dir / "fundlog.db"


def _invoke(*arguments: str):
    result = runner.invoke(app, list(arguments))
    assert result.exit_code == 0, result.output
    return result


def _entry_rows(database_path: Path, portfolio: str) -> list[tuple]:
    with sqlite3.connect(database_path) as connection:
        return connection.execute(
            """
            SELECT e.entry_no, e.entry_type, e.amount_minor, e.entry_date,
                   e.note, e.deleted_at IS NOT NULL
            FROM capital_entries AS e
            JOIN portfolios AS p ON p.id = e.portfolio_id
            WHERE p.name = ?
            ORDER BY e.entry_no
            """,
            (portfolio,),
        ).fetchall()


def _transaction_rows(database_path: Path, portfolio: str) -> list[tuple]:
    with sqlite3.connect(database_path) as connection:
        return connection.execute(
            """
            SELECT t.entry_no, t.transaction_type, t.price_text, t.quantity_text,
                   t.fee_minor, t.total_minor, t.cash_effect_minor,
                   t.position_effect_minor, t.realized_pnl_minor,
                   t.income_minor, t.deleted_at IS NOT NULL
            FROM asset_transactions AS t
            JOIN assets AS a ON a.id = t.asset_id
            JOIN portfolios AS p ON p.id = a.portfolio_id
            WHERE p.name = ? AND a.symbol = 'AAPL'
            ORDER BY t.entry_no
            """,
            (portfolio,),
        ).fetchall()


def test_grouped_portfolio_create_and_summaries_match_legacy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize(tmp_path, monkeypatch)
    _invoke("portfolio", "create", "stocks", "--initial", "1000")
    _invoke("create", "legacy", "--initial", "500")

    grouped = _invoke("portfolio", "summary", "stocks")
    legacy = _invoke("summary", "stocks")
    grouped_all = _invoke("portfolio", "summary", "--all")
    legacy_all = _invoke("summary", "--all")

    assert grouped.output == legacy.output
    assert grouped_all.output == legacy_all.output
    assert "1,000.00" in grouped.output
    assert "legacy" in grouped_all.output
    assert "stocks" in grouped_all.output


def test_grouped_portfolio_reset_matches_legacy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize(tmp_path, monkeypatch)
    _invoke("portfolio", "create", "grouped", "--initial", "1000")
    _invoke("create", "legacy", "--initial", "1000")
    _invoke("portfolio", "reset", "grouped", "--yes")
    _invoke("reset", "legacy", "--yes")

    assert _entry_rows(database_path, "grouped")[0][-1] == 1
    assert _entry_rows(database_path, "legacy")[0][-1] == 1


def test_grouped_portfolio_delete_matches_legacy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize(tmp_path, monkeypatch)
    _invoke("portfolio", "create", "grouped", "--initial", "1000")
    _invoke("create", "legacy", "--initial", "1000")
    _invoke("portfolio", "delete", "grouped", "--yes")
    _invoke("delete", "legacy", "--yes")

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT name, deleted_at IS NOT NULL
            FROM portfolios
            ORDER BY name
            """
        ).fetchall()
    assert rows == [("grouped", 1), ("legacy", 1)]


def test_grouped_capital_commands_match_legacy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize(tmp_path, monkeypatch)
    _invoke("portfolio", "create", "grouped", "--initial", "1000")
    _invoke("create", "legacy", "--initial", "1000")

    _invoke("capital", "inflow", "grouped", "200", "--note", "deposit")
    _invoke("inflow", "legacy", "200", "--note", "deposit")
    _invoke("capital", "outflow", "grouped", "100", "--note", "withdrawal")
    _invoke("outflow", "legacy", "100", "--note", "withdrawal")

    assert (
        _invoke("capital", "log", "grouped").output == _invoke("log", "grouped").output
    )

    _invoke("capital", "edit", "grouped", "2", "--amount", "250")
    _invoke("edit", "legacy", "2", "--amount", "250")
    _invoke("capital", "delete", "grouped", "3")
    _invoke("delete", "legacy", "3")

    assert _entry_rows(database_path, "grouped") == _entry_rows(
        database_path,
        "legacy",
    )


def test_grouped_asset_income_buy_and_sell_match_legacy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize(tmp_path, monkeypatch)
    _invoke("portfolio", "create", "grouped", "--initial", "2000")
    _invoke("create", "legacy", "--initial", "2000")
    _invoke("asset", "add", "grouped", "AAPL")
    _invoke("asset", "add", "legacy", "AAPL")

    _invoke(
        "asset",
        "buy",
        "grouped/AAPL",
        "--price",
        "100",
        "--quantity",
        "10",
    )
    _invoke(
        "buy",
        "legacy/AAPL",
        "--price",
        "100",
        "--quantity",
        "10",
    )
    _invoke(
        "asset",
        "sell",
        "grouped/AAPL",
        "--price",
        "150",
        "--quantity",
        "3",
    )
    _invoke(
        "sell",
        "legacy/AAPL",
        "--price",
        "150",
        "--quantity",
        "3",
    )
    _invoke("asset", "income", "grouped/AAPL", "20")
    _invoke("income", "legacy/AAPL", "20")

    assert _transaction_rows(database_path, "grouped") == _transaction_rows(
        database_path,
        "legacy",
    )
    assert (
        _invoke("asset", "summary", "grouped/AAPL").output
        == _invoke(
            "asset",
            "summary",
            "legacy/AAPL",
        ).output
    )


@pytest.mark.parametrize(
    "command",
    [
        "create",
        "summary",
        "reset",
        "delete",
        "inflow",
        "outflow",
        "log",
        "edit",
        "income",
        "buy",
        "sell",
    ],
)
def test_legacy_root_command_help_remains_callable(command: str) -> None:
    result = runner.invoke(app, [command, "--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
