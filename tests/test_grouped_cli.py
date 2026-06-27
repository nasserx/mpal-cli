"""Integration tests for the official mpal command hierarchy."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mpal.cli import app

runner = CliRunner()


def _initialize(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MPAL_DATA_DIR", str(tmp_path / "mpal-data"))
    assert runner.invoke(app, ["init"]).exit_code == 0


def test_official_portfolio_capital_and_asset_workflow(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize(tmp_path, monkeypatch)

    commands = (
        ["portfolio", "create", "stocks", "--initial", "2000"],
        ["capital", "deposit", "100", "-p", "stocks"],
        ["capital", "withdraw", "50", "--portfolio", "stocks"],
        ["asset", "add", "AAPL", "MSFT", "-p", "stocks"],
        [
            "asset",
            "buy",
            "AAPL",
            "-p",
            "stocks",
            "--price",
            "100",
            "--quantity",
            "10",
        ],
        ["asset", "income", "AAPL", "20", "--portfolio", "stocks"],
        [
            "asset",
            "sell",
            "AAPL",
            "-p",
            "stocks",
            "--price",
            "150",
            "--quantity",
            "3",
        ],
    )
    for arguments in commands:
        result = runner.invoke(app, arguments)
        assert result.exit_code == 0, result.output

    asset_list = runner.invoke(app, ["asset", "list", "-p", "stocks"])
    asset_show = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])
    asset_log = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])
    capital_show = runner.invoke(app, ["capital", "show", "-p", "stocks"])
    capital_log = runner.invoke(app, ["capital", "log", "-p", "stocks"])
    portfolio_list = runner.invoke(app, ["portfolio", "list"])
    portfolio_show = runner.invoke(app, ["summary", "-p", "stocks"])

    for result in (
        asset_list,
        asset_show,
        asset_log,
        capital_show,
        capital_log,
        portfolio_list,
        portfolio_show,
    ):
        assert result.exit_code == 0
        assert "Market Value" not in result.output
        assert "Unrealized PnL" not in result.output

    asset_row = next(line for line in asset_list.output.splitlines() if "AAPL" in line)
    assert " 7 " in asset_row
    assert "700.00" in asset_row
    assert "100.00" in asset_row
    assert "150.00" in asset_row
    assert "20.00" in asset_row
    assert "+17.00%" in asset_row

    for transaction_type in ("buy", "income", "sell"):
        assert transaction_type in asset_log.output
    assert "deposit" in capital_log.output
    assert "withdraw" in capital_log.output
    assert "inflow" not in capital_log.output
    assert "outflow" not in capital_log.output
    capital_row = next(
        line for line in capital_show.output.splitlines() if "stocks" in line
    )
    assert "2,100.00" in capital_row
    assert "50.00" in capital_row
    assert "2,050.00" in capital_row

    list_row = next(
        line for line in portfolio_list.output.splitlines() if "stocks" in line
    )
    show_row = next(
        line for line in portfolio_show.output.splitlines() if "stocks" in line
    )
    assert list_row == show_row
    for value in ("2,050.00", "1,520.00", "700.00", "2,220.00", "150.00"):
        assert value in show_row
    assert "20.00" in show_row
    assert "+8.29%" in show_row


@pytest.mark.parametrize(
    "arguments",
    [
        ["capital", "deposit", "100"],
        ["capital", "withdraw", "100"],
        ["capital", "show"],
        ["capital", "log"],
        ["capital", "entry", "edit", "1", "--note", "changed"],
        ["capital", "entry", "delete", "1"],
        ["asset", "add", "AAPL"],
        ["asset", "log", "AAPL"],
        ["asset", "delete", "AAPL", "--yes"],
        ["asset", "entry", "delete", "AAPL", "1", "--yes"],
        ["asset", "entry", "edit", "AAPL", "1", "--note", "changed"],
        ["asset", "income", "AAPL", "10"],
        ["asset", "buy", "AAPL", "--price", "1", "--quantity", "1"],
        ["asset", "sell", "AAPL", "--price", "1", "--quantity", "1"],
    ],
)
def test_portfolio_option_is_required(arguments: list[str]) -> None:
    result = runner.invoke(app, arguments)

    assert result.exit_code == 2
    assert "Missing option" in result.output
    assert "--portfolio" in result.output


@pytest.mark.parametrize(
    "command",
    [
        "create",
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
def test_legacy_root_commands_are_removed(command: str) -> None:
    result = runner.invoke(app, [command])

    assert result.exit_code == 2
    assert f"No such command '{command}'" in result.output


@pytest.mark.parametrize(
    "arguments",
    [
        ["asset", "list", "stocks"],
        ["asset", "summary", "stocks/MSFT"],
        ["asset", "log", "stocks/MSFT"],
        [
            "asset",
            "buy",
            "stocks/MSFT",
            "--price",
            "1",
            "--quantity",
            "1",
        ],
        [
            "asset",
            "sell",
            "stocks/MSFT",
            "--price",
            "1",
            "--quantity",
            "1",
        ],
        ["asset", "income", "stocks/MSFT", "1"],
        ["asset", "delete", "stocks/MSFT", "--yes"],
        ["asset", "entry", "delete", "stocks/MSFT", "1", "--yes"],
        ["asset", "entry", "edit", "stocks/MSFT", "1", "--note", "changed"],
    ],
)
def test_legacy_asset_command_shapes_are_removed(arguments: list[str]) -> None:
    result = runner.invoke(app, arguments)

    assert result.exit_code == 2


@pytest.mark.parametrize(
    "arguments",
    [
        ["asset", "summary"],
        ["asset", "summary", "AAPL", "-p", "stocks"],
        ["asset", "show", "AAPL", "-p", "stocks"],
        ["asset", "edit", "AAPL", "1", "-p", "stocks", "--note", "changed"],
        ["asset", "delete-entry", "AAPL", "1", "-p", "stocks", "--yes"],
    ],
)
def test_legacy_asset_entry_commands_are_removed(arguments: list[str]) -> None:
    result = runner.invoke(app, arguments)

    assert result.exit_code == 2


def test_removed_portfolio_show_command_is_invalid() -> None:
    result = runner.invoke(app, ["portfolio", "show", "stocks"])

    assert result.exit_code == 2
    assert "No such command 'show'" in result.output


@pytest.mark.parametrize(
    "arguments",
    [
        ["capital", "edit", "1", "-p", "stocks", "--note", "changed"],
        ["capital", "delete", "1", "-p", "stocks"],
    ],
)
def test_legacy_capital_command_shapes_are_removed(arguments: list[str]) -> None:
    result = runner.invoke(app, arguments)

    assert result.exit_code == 2
