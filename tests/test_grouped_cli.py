"""Integration tests for the official FundLog command hierarchy."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from fundlog.cli import app

runner = CliRunner()


def _initialize(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(tmp_path / "fundlog-data"))
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

    assert "AAPL" in runner.invoke(app, ["asset", "summary", "-p", "stocks"]).output
    assert (
        "150.00"
        in runner.invoke(app, ["asset", "summary", "AAPL", "-p", "stocks"]).output
    )
    assert "sell" in runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"]).output
    assert "stocks" in runner.invoke(app, ["portfolio", "list"]).output
    assert "stocks" in runner.invoke(app, ["portfolio", "show", "stocks"]).output


@pytest.mark.parametrize(
    "arguments",
    [
        ["capital", "deposit", "100"],
        ["capital", "withdraw", "100"],
        ["capital", "log"],
        ["capital", "edit", "1", "--note", "changed"],
        ["capital", "delete", "1"],
        ["asset", "add", "AAPL"],
        ["asset", "summary"],
        ["asset", "log", "AAPL"],
        ["asset", "delete", "AAPL", "--yes"],
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
def test_legacy_root_commands_are_removed(command: str) -> None:
    result = runner.invoke(app, [command, "--help"])

    assert result.exit_code == 2
    assert f"No such command '{command}'" in result.output


@pytest.mark.parametrize(
    "arguments",
    [
        ["asset", "list", "stocks"],
        ["asset", "summary", "stocks/AAPL"],
        ["asset", "log", "stocks/AAPL"],
        [
            "asset",
            "buy",
            "stocks/AAPL",
            "--price",
            "1",
            "--quantity",
            "1",
        ],
        [
            "asset",
            "sell",
            "stocks/AAPL",
            "--price",
            "1",
            "--quantity",
            "1",
        ],
        ["asset", "income", "stocks/AAPL", "1"],
        ["asset", "delete", "stocks/AAPL", "--yes"],
    ],
)
def test_legacy_asset_command_shapes_are_removed(arguments: list[str]) -> None:
    result = runner.invoke(app, arguments)

    assert result.exit_code == 2
