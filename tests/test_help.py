"""Help-output tests for the official mpal CLI."""

import pytest
from typer.testing import CliRunner

from mpal.cli import app

runner = CliRunner()


def test_top_level_help_lists_only_official_root_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Multi-Portfolio Asset Ledger" in result.output
    for command in ("init", "summary", "portfolio", "capital", "asset"):
        assert f"│ {command} " in result.output
    for command in (
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
    ):
        assert f"│ {command} " not in result.output
    assert "mpal " in result.output
    assert " fl " not in result.output
    assert "<portfolio>/<symbol>" not in result.output
    assert "mpal asset add <symbol> [symbol...] -p <portfolio>" in result.output


def test_all_help_output_excludes_the_previous_product_name() -> None:
    old_name = "fund" + "log"
    help_commands = [
        [],
        ["portfolio"],
        ["capital"],
        ["asset"],
        ["init"],
        ["summary"],
        ["portfolio", "create"],
        ["portfolio", "list"],
        ["portfolio", "reset"],
        ["portfolio", "delete"],
        ["capital", "show"],
        ["capital", "deposit"],
        ["capital", "withdraw"],
        ["capital", "log"],
        ["capital", "entry"],
        ["capital", "entry", "edit"],
        ["capital", "entry", "delete"],
        ["asset", "add"],
        ["asset", "list"],
        ["asset", "log"],
        ["asset", "delete"],
        ["asset", "entry"],
        ["asset", "entry", "delete"],
        ["asset", "entry", "edit"],
        ["asset", "income"],
        ["asset", "buy"],
        ["asset", "sell"],
    ]

    for arguments in help_commands:
        result = runner.invoke(app, [*arguments, "--help"])
        assert result.exit_code == 0
        assert old_name not in result.output.lower()


def test_group_help_lists_only_current_commands_and_examples() -> None:
    portfolio = runner.invoke(app, ["portfolio", "--help"])
    capital = runner.invoke(app, ["capital", "--help"])
    asset = runner.invoke(app, ["asset", "--help"])

    assert portfolio.exit_code == capital.exit_code == asset.exit_code == 0
    for command in ("create", "list", "delete", "reset"):
        assert f"│ {command} " in portfolio.output
    assert "│ show " not in portfolio.output
    for command in ("show", "deposit", "withdraw", "log", "entry"):
        assert f"│ {command} " in capital.output
    for command in ("edit", "delete"):
        assert f"│ {command} " not in capital.output
    entry = runner.invoke(app, ["capital", "entry", "--help"])
    assert entry.exit_code == 0
    for command in ("edit", "delete"):
        assert f"│ {command} " in entry.output
    for command in (
        "add",
        "list",
        "log",
        "delete",
        "entry",
        "income",
        "buy",
        "sell",
    ):
        assert f"│ {command} " in asset.output
    asset_entry = runner.invoke(app, ["asset", "entry", "--help"])
    assert asset_entry.exit_code == 0
    for command in ("edit", "delete"):
        assert f"│ {command} " in asset_entry.output
    for removed_command in ("show", "summary", "edit", "delete-entry"):
        assert f"│ {removed_command} " not in asset.output
    assert "│ summary " not in asset.output
    assert "mpal capital show -p <portfolio>" in capital.output
    assert "mpal capital deposit <amount> -p <portfolio>" in capital.output
    assert "mpal capital entry edit <entry-number> -p <portfolio>" in capital.output
    assert "mpal asset add <symbol> [symbol...] -p <portfolio>" in asset.output
    assert "mpal asset list -p <portfolio>" in asset.output
    assert "mpal asset show <symbol> -p <portfolio>" not in asset.output
    assert "mpal summary -p <portfolio> -a <asset>" not in asset.output
    assert "mpal asset entry edit <symbol> <entry-number> -p <portfolio>" in (
        asset.output
    )
    assert "<portfolio>/<symbol>" not in asset.output


@pytest.mark.parametrize(
    "arguments",
    [
        ["portfolio", "create"],
        ["summary"],
        ["portfolio", "list"],
        ["portfolio", "reset"],
        ["portfolio", "delete"],
        ["capital", "show"],
        ["capital", "deposit"],
        ["capital", "withdraw"],
        ["capital", "log"],
        ["capital", "entry"],
        ["capital", "entry", "edit"],
        ["capital", "entry", "delete"],
        ["asset", "add"],
        ["asset", "list"],
        ["asset", "log"],
        ["asset", "delete"],
        ["asset", "entry"],
        ["asset", "entry", "delete"],
        ["asset", "entry", "edit"],
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
        ["capital", "show", "--help"],
        ["capital", "deposit", "--help"],
        ["capital", "withdraw", "--help"],
        ["capital", "log", "--help"],
        ["capital", "entry", "edit", "--help"],
        ["capital", "entry", "delete", "--help"],
        ["asset", "add", "--help"],
        ["asset", "list", "--help"],
        ["asset", "log", "--help"],
        ["asset", "delete", "--help"],
        ["asset", "entry", "delete", "--help"],
        ["asset", "entry", "edit", "--help"],
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
