"""Help-output tests for the official FundLog CLI."""

import pytest
from typer.testing import CliRunner

from fundlog.cli import app

runner = CliRunner()


def test_top_level_help_lists_only_official_root_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ("init", "portfolio", "capital", "asset"):
        assert f"│ {command} " in result.output
    for command in (
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
    ):
        assert f"│ {command} " not in result.output
    assert "fundlog " in result.output
    assert " fl " not in result.output
    assert "<portfolio>/<symbol>" not in result.output


def test_group_help_lists_only_current_commands_and_examples() -> None:
    portfolio = runner.invoke(app, ["portfolio", "--help"])
    capital = runner.invoke(app, ["capital", "--help"])
    asset = runner.invoke(app, ["asset", "--help"])

    assert portfolio.exit_code == capital.exit_code == asset.exit_code == 0
    for command in ("create", "list", "show", "delete", "reset"):
        assert f"│ {command} " in portfolio.output
    for command in ("deposit", "withdraw", "log", "edit", "delete"):
        assert f"│ {command} " in capital.output
    for command in ("add", "summary", "log", "delete", "income", "buy", "sell"):
        assert f"│ {command} " in asset.output
    assert "│ list " not in asset.output
    assert "fundlog capital deposit <amount> -p <portfolio>" in capital.output
    assert "fundlog asset summary <symbol> -p <portfolio>" in asset.output
    assert "<portfolio>/<symbol>" not in asset.output


@pytest.mark.parametrize(
    "arguments",
    [
        ["portfolio", "create"],
        ["portfolio", "list"],
        ["portfolio", "show"],
        ["portfolio", "reset"],
        ["portfolio", "delete"],
        ["capital", "deposit"],
        ["capital", "withdraw"],
        ["capital", "log"],
        ["capital", "edit"],
        ["capital", "delete"],
        ["asset", "add"],
        ["asset", "summary"],
        ["asset", "log"],
        ["asset", "delete"],
        ["asset", "income"],
        ["asset", "buy"],
        ["asset", "sell"],
    ],
)
def test_official_command_help_is_registered(arguments: list[str]) -> None:
    result = runner.invoke(app, [*arguments, "--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    "arguments",
    [
        ["capital", "deposit", "--help"],
        ["capital", "withdraw", "--help"],
        ["capital", "log", "--help"],
        ["capital", "edit", "--help"],
        ["capital", "delete", "--help"],
        ["asset", "add", "--help"],
        ["asset", "summary", "--help"],
        ["asset", "log", "--help"],
        ["asset", "delete", "--help"],
        ["asset", "income", "--help"],
        ["asset", "buy", "--help"],
        ["asset", "sell", "--help"],
    ],
)
def test_portfolio_scoped_help_shows_long_and_short_options(
    arguments: list[str],
) -> None:
    result = runner.invoke(app, arguments)

    assert result.exit_code == 0
    assert "--portfolio" in result.output
    assert "-p" in result.output
