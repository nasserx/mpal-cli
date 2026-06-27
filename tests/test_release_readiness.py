"""Release-readiness regressions for cross-ledger validation rules."""

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mpal.cli import app

runner = CliRunner()


def _initialize_asset(tmp_path: Path, monkeypatch) -> Path:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert (
        runner.invoke(
            app,
            ["portfolio", "create", "stocks", "--initial", "1000"],
        ).exit_code
        == 0
    )
    assert runner.invoke(app, ["asset", "add", "AAPL", "-p", "stocks"]).exit_code == 0
    return data_dir / "mpal.db"


def _buy(quantity: str = "8") -> None:
    result = runner.invoke(
        app,
        [
            "asset",
            "buy",
            "AAPL",
            "-p",
            "stocks",
            "--price",
            "100",
            "--quantity",
            quantity,
        ],
    )
    assert result.exit_code == 0


def test_outflow_validation_includes_active_asset_cash_effects(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy()

    result = runner.invoke(app, ["withdraw", "300", "-p", "stocks"])

    assert result.exit_code == 1
    assert "Insufficient cash in portfolio 'stocks'." in result.output
    with sqlite3.connect(database_path) as connection:
        outflow_count = connection.execute(
            "SELECT COUNT(*) FROM capital_entries WHERE entry_type = 'outflow'"
        ).fetchone()[0]
    assert outflow_count == 0


def test_outflow_validation_includes_asset_income_and_sell_proceeds(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="10")
    assert (
        runner.invoke(
            app,
            [
                "asset",
                "sell",
                "AAPL",
                "-p",
                "stocks",
                "--price",
                "150",
                "--quantity",
                "1",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(app, ["asset", "income", "AAPL", "20", "-p", "stocks"]).exit_code
        == 0
    )

    result = runner.invoke(app, ["withdraw", "170", "-p", "stocks"])

    assert result.exit_code == 0


def test_outflow_validation_excludes_deleted_asset_cash_effects(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy()
    assert (
        runner.invoke(
            app,
            ["asset", "delete", "AAPL", "-p", "stocks", "--yes"],
        ).exit_code
        == 0
    )

    result = runner.invoke(app, ["withdraw", "1000", "-p", "stocks"])

    assert result.exit_code == 0


def test_edit_validation_includes_active_asset_cash_effects(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy()

    result = runner.invoke(
        app,
        ["capital", "entry", "edit", "1", "-p", "stocks", "--amount", "700"],
    )

    assert result.exit_code == 1
    assert "Edit would make portfolio cash negative." in result.output
    with sqlite3.connect(database_path) as connection:
        amount_minor = connection.execute(
            "SELECT amount_minor FROM capital_entries WHERE entry_no = 1"
        ).fetchone()[0]
    assert amount_minor == 100_000


def test_delete_validation_includes_active_asset_cash_effects(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy()

    result = runner.invoke(app, ["capital", "entry", "delete", "1", "-p", "stocks"])

    assert result.exit_code == 1
    assert "Delete would make portfolio cash negative." in result.output
    with sqlite3.connect(database_path) as connection:
        deleted_at = connection.execute(
            "SELECT deleted_at FROM capital_entries WHERE entry_no = 1"
        ).fetchone()[0]
    assert deleted_at is None


@pytest.mark.parametrize(
    "arguments",
    [
        ["portfolio", "create", "stocks/growth"],
        ["portfolio", "create", "stocks/growth", "--initial", "1000"],
        ["portfolio", "create", "stocks/growth"],
        ["portfolio", "create", "stocks/growth", "--initial", "1000"],
    ],
)
def test_portfolio_creation_rejects_asset_reference_separator(
    tmp_path: Path,
    monkeypatch,
    arguments: list[str],
) -> None:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    assert runner.invoke(app, ["init"]).exit_code == 0

    result = runner.invoke(app, arguments)

    assert result.exit_code == 1
    assert "Portfolio name cannot contain '/'." in result.output
