"""Focused tests for explicit CLI help examples."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from fundlog.cli import app

runner = CliRunner()


def test_top_level_help_includes_common_command_shapes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command_shape in (
        "fundlog init",
        "fundlog portfolio create <portfolio> [--initial <amount>]",
        "fundlog portfolio summary <portfolio>",
        "fundlog portfolio summary --all",
        "fundlog capital inflow <portfolio> <amount>",
        "fundlog capital outflow <portfolio> <amount>",
        "fundlog capital log <portfolio>",
        "fundlog capital edit <portfolio> <entry-number>",
        "fundlog capital delete <portfolio> <entry-number>",
        "fundlog asset add <portfolio> <symbol> [symbol...]",
        "fundlog asset summary <portfolio>",
        "fundlog asset summary <portfolio>/<symbol>",
        "fundlog asset income <portfolio>/<symbol> <amount>",
        (
            "fundlog asset buy <portfolio>/<symbol> "
            "--price <price> --quantity <quantity>"
        ),
        (
            "fundlog asset sell <portfolio>/<symbol> "
            "--price <price> --quantity <quantity>"
        ),
    ):
        assert command_shape in result.output
    for legacy in (
        "create",
        "inflow",
        "outflow",
        "summary",
        "log",
        "edit",
        "reset",
        "delete",
        "income",
        "buy",
        "sell",
    ):
        assert f"│ {legacy} " not in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_asset_help_includes_subcommand_examples(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["asset", "--help"])

    assert result.exit_code == 0
    for command_shape in (
        "fundlog asset add <portfolio> <symbol> [symbol...]",
        "fundlog asset summary <portfolio>",
        "fundlog asset log <portfolio>/<symbol>",
        "fundlog asset summary <portfolio>/<symbol>",
        "fundlog asset delete <portfolio>/<symbol> --yes",
    ):
        assert command_shape in result.output
    assert "fundlog asset list <portfolio>" not in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_portfolio_help_includes_official_examples() -> None:
    result = runner.invoke(app, ["portfolio", "--help"])

    assert result.exit_code == 0
    assert "fundlog portfolio create <portfolio>" in result.output
    assert "fundlog portfolio summary <portfolio>" in result.output
    assert "fundlog portfolio summary --all" in result.output
    assert "fundlog portfolio reset <portfolio> --yes" in result.output
    assert "fundlog portfolio delete <portfolio> --yes" in result.output


def test_portfolio_summary_help_includes_both_forms() -> None:
    result = runner.invoke(app, ["portfolio", "summary", "--help"])

    assert result.exit_code == 0
    assert "fundlog portfolio summary <portfolio>" in result.output
    assert "fundlog portfolio summary --all" in result.output


def test_capital_help_includes_official_examples() -> None:
    result = runner.invoke(app, ["capital", "--help"])

    assert result.exit_code == 0
    assert "fundlog capital inflow <portfolio> <amount>" in result.output
    assert "fundlog capital outflow <portfolio> <amount>" in result.output
    assert "fundlog capital log <portfolio>" in result.output
    assert "fundlog capital edit <portfolio> <entry-number>" in result.output
    assert "fundlog capital delete <portfolio> <entry-number>" in result.output


def test_group_help_lists_only_its_own_commands() -> None:
    portfolio = runner.invoke(app, ["portfolio", "--help"])
    capital = runner.invoke(app, ["capital", "--help"])
    asset = runner.invoke(app, ["asset", "--help"])

    assert portfolio.exit_code == 0
    assert capital.exit_code == 0
    assert asset.exit_code == 0

    for command in ("create", "summary", "reset", "delete"):
        assert f"│ {command} " in portfolio.output
    for command in ("inflow", "outflow", "log", "edit"):
        assert f"│ {command} " not in portfolio.output
    for command in ("add", "income", "buy", "sell"):
        assert f"│ {command} " not in portfolio.output

    for command in ("inflow", "outflow", "log", "edit", "delete"):
        assert f"│ {command} " in capital.output
    for command in ("create", "summary", "reset", "add", "income", "buy", "sell"):
        assert f"│ {command} " not in capital.output

    for command in ("add", "summary", "log", "delete", "income", "buy", "sell"):
        assert f"│ {command} " in asset.output
    for command in ("list", "create", "reset", "inflow", "outflow", "edit"):
        assert f"│ {command} " not in asset.output


@pytest.mark.parametrize(
    "arguments",
    [
        ["portfolio", "create"],
        ["portfolio", "summary"],
        ["portfolio", "reset"],
        ["portfolio", "delete"],
        ["capital", "inflow"],
        ["capital", "outflow"],
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
def test_official_command_help_is_registered_without_database(
    tmp_path: Path,
    monkeypatch,
    arguments: list[str],
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, [*arguments, "--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "Traceback" not in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_asset_income_help_includes_explicit_command_shape(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["asset", "income", "--help"])

    assert result.exit_code == 0
    assert "fundlog asset income <portfolio>/<symbol> <amount>" in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_asset_buy_help_includes_shape_and_option_meanings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["asset", "buy", "--help"])

    assert result.exit_code == 0
    assert (
        "fundlog asset buy <portfolio>/<symbol> "
        "--price <price> --quantity <quantity>" in result.output
    )
    assert "Exact unit price." in result.output
    assert "Exact quantity to buy." in result.output
    assert "Trade fee; defaults to 0.00." in result.output
    assert "Exact buy cash outflow including fees." in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_asset_sell_help_includes_shape_and_option_meanings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["asset", "sell", "--help"])

    assert result.exit_code == 0
    assert (
        "fundlog asset sell <portfolio>/<symbol> "
        "--price <price> --quantity <quantity>" in result.output
    )
    assert "Exact unit price." in result.output
    assert "Exact quantity to sell." in result.output
    assert "Trade fee; defaults to 0.00." in result.output
    assert "Exact net sell proceeds after fees." in result.output
    assert not (data_dir / "fundlog.db").exists()
