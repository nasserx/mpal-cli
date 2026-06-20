"""Focused tests for explicit CLI help examples."""

from pathlib import Path

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
        "fundlog create <portfolio> [--initial <amount>]",
        "fundlog summary <portfolio>",
        "fundlog summary --all",
        "fundlog delete <portfolio> <entry-number>",
        "fundlog delete <portfolio> --yes",
        "fundlog asset add <portfolio> <symbol> [symbol...]",
        "fundlog asset summary <portfolio>",
        "fundlog asset summary <portfolio>/<symbol>",
        "fundlog income <portfolio>/<symbol> <amount>",
        "fundlog buy <portfolio>/<symbol> --price <price> --quantity <quantity>",
        "fundlog sell <portfolio>/<symbol> --price <price> --quantity <quantity>",
    ):
        assert command_shape in result.output
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


def test_income_help_includes_explicit_command_shape(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["income", "--help"])

    assert result.exit_code == 0
    assert "fundlog income <portfolio>/<symbol> <amount>" in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_buy_help_includes_shape_and_option_meanings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["buy", "--help"])

    assert result.exit_code == 0
    assert (
        "fundlog buy <portfolio>/<symbol> --price <price> --quantity <quantity>"
        in result.output
    )
    assert "Exact unit price." in result.output
    assert "Exact quantity to buy." in result.output
    assert "Trade fee; defaults to 0.00." in result.output
    assert "Exact buy cash outflow including fees." in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_sell_help_includes_shape_and_option_meanings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["sell", "--help"])

    assert result.exit_code == 0
    assert (
        "fundlog sell <portfolio>/<symbol> --price <price> --quantity <quantity>"
        in result.output
    )
    assert "Exact unit price." in result.output
    assert "Exact quantity to sell." in result.output
    assert "Trade fee; defaults to 0.00." in result.output
    assert "Exact net sell proceeds after fees." in result.output
    assert not (data_dir / "fundlog.db").exists()
