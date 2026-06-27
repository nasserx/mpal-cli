"""Focused tests for semantic financial output formatting."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from rich.console import Console
from typer.testing import CliRunner

from mpal.cli import app
from mpal.output import console as console_output
from mpal.output.formatting import (
    format_asset_portfolio_header,
    format_asset_portfolio_label,
    format_capital_entry_amount,
    format_capital_entry_type,
    format_income_money,
    format_profit_loss_money,
    format_profit_loss_percent,
    format_signed_percent,
    style_transaction_type,
)
from mpal.output.theme import (
    BORDER,
    ERROR,
    HEADER,
    INCOME,
    INFO,
    LOSS,
    MUTED,
    PROFIT,
    RELATION_SEPARATOR,
    ROW_KEY,
    ROW_SEPARATOR,
    SUCCESS,
    TABLE_BORDER,
    TABLE_BOX,
    TABLE_CELL,
    TABLE_HEADER,
    VALUE,
    WARNING,
)
from mpal.storage.asset_logs import AssetTransaction
from mpal.storage.assets import Asset
from mpal.storage.logs import CapitalEntry, CapitalState
from mpal.storage.summaries import GlobalSummary, PortfolioSummary

runner = CliRunner()


def _initialize_asset(
    tmp_path: Path,
    monkeypatch,
    *,
    initial: str = "1000",
) -> None:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert (
        runner.invoke(
            app,
            ["portfolio", "create", "stocks", "--initial", initial],
        ).exit_code
        == 0
    )
    assert runner.invoke(app, ["asset", "add", "AAPL", "-p", "stocks"]).exit_code == 0


def _buy(*, price: str, quantity: str, total: str | None = None) -> None:
    args = [
        "asset",
        "buy",
        "AAPL",
        "-p",
        "stocks",
        "--price",
        price,
        "--quantity",
        quantity,
    ]
    if total is not None:
        args.extend(["--total", total])
    result = runner.invoke(app, args)
    assert result.exit_code == 0


def _sell(*, price: str, quantity: str) -> None:
    result = runner.invoke(
        app,
        [
            "asset",
            "sell",
            "AAPL",
            "-p",
            "stocks",
            "--price",
            price,
            "--quantity",
            quantity,
        ],
    )
    assert result.exit_code == 0


def test_asset_outputs_omit_standalone_title_and_keep_tables(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(price="100", quantity="1")

    log_result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])
    summary_result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    for result in (log_result, summary_result):
        assert result.exit_code == 0
        assert "AAPL/stocks" not in result.output

    assert "Date" in log_result.output
    assert "Type" in log_result.output
    assert "100.00" in log_result.output
    assert "Quantity" in summary_result.output
    assert "Cost Basis" in summary_result.output
    assert "100.00" in summary_result.output


def test_positive_profit_and_returns_show_explicit_plus_sign(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(price="100", quantity="1")
    _sell(price="150", quantity="1")

    asset_list = runner.invoke(app, ["asset", "list", "-p", "stocks"])
    asset_summary = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])
    portfolio = runner.invoke(app, ["summary", "-p", "stocks"])

    assert "+50.00" in asset_list.output
    assert "+50.00%" in asset_list.output
    assert "+50.00" in asset_summary.output
    assert "+50.00%" in asset_summary.output
    assert "+50.00" in portfolio.output
    assert "+5.00%" in portfolio.output


def test_negative_profit_and_returns_keep_minus_sign(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(price="100", quantity="1")
    _sell(price="80", quantity="1")

    asset_summary = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])
    portfolio = runner.invoke(app, ["summary", "-p", "stocks"])

    assert "-20.00" in asset_summary.output
    assert "-20.00%" in asset_summary.output
    assert "-20.00" in portfolio.output
    assert "-2.00%" in portfolio.output


def test_zero_profit_and_returns_remain_unsigned(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(price="100", quantity="1")

    asset_summary = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])
    portfolio = runner.invoke(app, ["summary", "-p", "stocks"])

    assert "+0.00" not in asset_summary.output
    assert "+0.00%" not in asset_summary.output
    assert "+0.00" not in portfolio.output
    assert "+0.00%" not in portfolio.output
    assert "0.00%" in asset_summary.output
    assert "0.00%" in portfolio.output


def test_semantic_result_helpers_use_reusable_theme_styles() -> None:
    assert format_profit_loss_money(1).style == PROFIT
    assert format_profit_loss_money(-1).style == LOSS
    assert format_profit_loss_money(0).style == TABLE_CELL
    assert format_profit_loss_percent(1, 100).style == PROFIT
    assert format_profit_loss_percent(-1, 100).style == LOSS
    assert format_profit_loss_percent(0, 100).style == TABLE_CELL
    assert format_profit_loss_percent(1, -100).style == LOSS
    assert format_profit_loss_percent(-1, -100).style == PROFIT
    assert format_income_money(1).style == INCOME


def test_theme_uses_documented_dark_terminal_palette() -> None:
    assert HEADER == "#B39DDB"
    assert SUCCESS == "#81C784"
    assert PROFIT == "#81C784"
    assert ERROR == "#E57373"
    assert LOSS == "#E57373"
    assert INFO == "#64B5F6"
    assert INCOME == "#60A5FA"
    assert ROW_KEY == "#EFAE83"
    assert WARNING == "#FFD54F"
    assert BORDER == "#4B5563"
    assert MUTED == "#9CA3AF"
    assert VALUE == "#D1D5DB"
    assert TABLE_HEADER == HEADER
    assert TABLE_BORDER == BORDER
    assert TABLE_CELL == VALUE
    assert ROW_SEPARATOR == f"dim {MUTED}"
    assert RELATION_SEPARATOR == INFO


def test_shared_table_helper_uses_theme_styles() -> None:
    table = console_output._make_table()

    assert table.box == TABLE_BOX
    assert table.header_style == TABLE_HEADER
    assert table.border_style == TABLE_BORDER
    assert table.style == TABLE_CELL
    assert table.row_separator_style == ROW_SEPARATOR
    assert table.show_lines is False
    assert table.min_width == console_output.STANDARD_TABLE_WIDTH
    assert table.layout == "default"


def test_shared_table_helper_styles_first_column_values_as_row_keys() -> None:
    table = console_output._make_table()
    table.add_column("Portfolio")
    table.add_column("Value", justify="right")
    table.add_row("stocks", "1")

    assert table.columns[0].header == "Portfolio"
    assert table.columns[0].style == ROW_KEY
    assert table.columns[1].style == ""
    assert table.header_style == TABLE_HEADER
    assert table.columns[0]._cells[0].style == ROW_KEY


def test_shared_table_helper_applies_central_column_alignment_policy() -> None:
    table = console_output._make_table()
    table.add_column("#", justify="right")
    table.add_column("Date")
    table.add_column("Type")
    table.add_column("Note")
    table.add_column("Amount")
    table.add_column("Return")

    assert [column.justify for column in table.columns] == [
        "left",
        "left",
        "left",
        "left",
        "right",
        "right",
    ]


def test_default_table_layout_keeps_financial_columns_right_aligned() -> None:
    table = console_output._make_table()
    table.add_column("TOTAL CAPITAL")
    table.add_column("TOTAL CASH")
    table.add_column("POSITIONS")
    table.add_column("BOOK VALUE")
    table.add_column("TOTAL INCOME")
    table.add_column("REALIZED P&L")
    table.add_column("RETURN")

    assert [column.justify for column in table.columns] == [
        "right",
        "right",
        "right",
        "right",
        "right",
        "right",
        "right",
    ]


def test_spread_table_layout_is_opt_in() -> None:
    default_table = console_output._make_table()
    spread_table = console_output._make_table(layout="spread")
    for table in (default_table, spread_table):
        table.add_column("TOTAL CAPITAL")
        table.add_column("TOTAL CASH")
        table.add_column("POSITIONS")
        table.add_column("BOOK VALUE")
        table.add_column("TOTAL INCOME")
        table.add_column("REALIZED P&L")
        table.add_column("RETURN")

    assert default_table.layout == "default"
    assert spread_table.layout == "spread"
    assert [column.justify for column in default_table.columns] == [
        "right",
        "right",
        "right",
        "right",
        "right",
        "right",
        "right",
    ]
    assert [column.justify for column in spread_table.columns] == [
        "left",
        "center",
        "center",
        "center",
        "center",
        "center",
        "right",
    ]


def test_summary_table_uses_spread_layout(monkeypatch) -> None:
    tables = []

    def record_table(table):
        tables.append(table)

    monkeypatch.setattr(console_output, "_print_table", record_table)

    console_output.print_global_summary(
        GlobalSummary(
            capital_minor=4_000_000,
            cash_minor=4_033_000,
            positions_minor=110_000,
            book_value_minor=4_143_000,
            income_minor=18_000,
            realized_pnl_minor=125_000,
        )
    )

    table = tables[0]

    assert table.layout == "spread"
    assert [column.header for column in table.columns] == [
        "TOTAL CAPITAL",
        "TOTAL CASH",
        "POSITIONS",
        "BOOK VALUE",
        "TOTAL INCOME",
        "REALIZED P&L",
        "RETURN",
    ]
    assert [column.justify for column in table.columns] == [
        "left",
        "center",
        "center",
        "center",
        "center",
        "center",
        "right",
    ]
    assert table.columns[0]._cells[0] == "40,000.00"
    assert table.columns[1]._cells[0] == "40,330.00"
    assert table.columns[2]._cells[0] == "1,100.00"
    assert table.columns[3]._cells[0] == "41,430.00"
    assert table.columns[4]._cells[0].plain == "180.00"
    assert table.columns[5]._cells[0].plain == "+1,250.00"
    assert table.columns[6]._cells[0].plain == "+3.58%"


def test_spread_summary_output_places_edges_near_table_edges(monkeypatch) -> None:
    rendered_tables: list[str] = []

    def record_table(table):
        output_console = Console(width=140, record=True)
        output_console.print(table)
        rendered_tables.append(output_console.export_text())

    monkeypatch.setattr(console_output, "_print_table", record_table)

    console_output.print_global_summary(
        GlobalSummary(
            capital_minor=4_000_000,
            cash_minor=4_033_000,
            positions_minor=110_000,
            book_value_minor=4_143_000,
            income_minor=18_000,
            realized_pnl_minor=125_000,
        )
    )

    lines = rendered_tables[0].splitlines()
    header_line = next(line for line in lines if "TOTAL CAPITAL" in line)
    value_line = next(line for line in lines if "40,000.00" in line)

    assert header_line.index("TOTAL CAPITAL") <= 3
    assert value_line.index("40,000.00") <= 3
    assert header_line.rstrip().endswith("RETURN │")
    assert value_line.rstrip().endswith("+3.58% │")


def test_shared_table_helper_limits_row_key_style_to_identity_headers() -> None:
    table = console_output._make_table()
    table.add_column("Name")
    table.add_column("Value", justify="right")
    table.add_row("alpha", "1")

    assert table.columns[0].style == ""
    assert table.columns[0]._cells[0] == "alpha"


def test_user_facing_tables_style_first_column_as_row_keys(monkeypatch) -> None:
    tables = []

    def record_table(table):
        tables.append(table)

    monkeypatch.setattr(console_output, "_print_table", record_table)

    console_output.print_capital_entry_log(
        [
            CapitalEntry(
                entry_no=1,
                entry_date=date.today().isoformat(),
                entry_type="inflow",
                amount_minor=100_000,
                note=None,
            )
        ]
    )
    console_output.print_assets(
        [
            Asset(
                portfolio_name="stocks",
                symbol="AAPL",
                quantity=Decimal("1"),
                cost_basis_minor=10_000,
                realized_pnl_minor=0,
                income_minor=0,
                total_buy_cost_minor=10_000,
                price_display_scale=2,
            )
        ]
    )
    console_output.print_portfolio_summary(
        PortfolioSummary(
            portfolio_name="stocks",
            capital_minor=100_000,
            cash_minor=90_000,
            positions_minor=10_000,
            book_value_minor=100_000,
            realized_pnl_minor=0,
            income_minor=0,
        )
    )

    assert [table.columns[0].style for table in tables] == [
        ROW_KEY,
        ROW_KEY,
        ROW_KEY,
    ]
    assert tables[0].columns[2].style == ""
    assert tables[1].columns[4].style == ""
    assert tables[2].columns[0]._cells[0].style == ROW_KEY


def test_shared_table_helper_expands_small_tables_to_standard_width() -> None:
    output_console = Console(width=140, record=True)
    table = console_output._make_table()
    table.add_column("Name")
    table.add_column("Value", justify="right")
    table.add_row("alpha", "1")

    output_console.print(table)
    rendered = output_console.export_text()
    top_border = rendered.splitlines()[0]

    assert len(top_border) == console_output.STANDARD_TABLE_WIDTH


def test_shared_table_helper_does_not_exceed_narrow_console_width() -> None:
    output_console = Console(width=80, record=True)
    table = console_output._make_table()
    table.add_column("Name")
    table.add_column("Value", justify="right")
    table.add_row("alpha", "1")

    output_console.print(table)
    rendered = output_console.export_text()

    assert max(len(line) for line in rendered.splitlines()) <= 80


def test_current_state_tables_share_standard_width_policy(
    monkeypatch,
) -> None:
    rendered_tables: list[str] = []

    def record_table(table):
        output_console = Console(width=140, record=True)
        output_console.print(table)
        rendered_tables.append(output_console.export_text())

    monkeypatch.setattr(console_output, "_print_table", record_table)

    console_output.print_portfolio_summary(
        PortfolioSummary(
            portfolio_name="stocks",
            capital_minor=100_000,
            cash_minor=90_000,
            positions_minor=10_000,
            book_value_minor=100_000,
            realized_pnl_minor=0,
            income_minor=0,
        )
    )
    console_output.print_capital_state(
        CapitalState(
            portfolio_name="stocks",
            deposits_minor=100_000,
            withdrawals_minor=0,
            net_capital_minor=100_000,
        )
    )
    console_output.print_asset_summary(
        "stocks",
        Asset(
            portfolio_name="stocks",
            symbol="AAPL",
            quantity=Decimal("1"),
            cost_basis_minor=10_000,
            total_buy_cost_minor=10_000,
            realized_pnl_minor=0,
            income_minor=0,
            price_display_scale=2,
        ),
    )

    top_border_widths = [len(rendered.splitlines()[0]) for rendered in rendered_tables]

    assert top_border_widths == [console_output.STANDARD_TABLE_WIDTH] * 3


def test_asset_portfolio_label_uses_bullet_separator_style() -> None:
    header = format_asset_portfolio_header()
    label = format_asset_portfolio_label("etha", "etfs")

    assert header.plain == "Asset/Portfolio"
    assert label.plain == "ETHA • Etfs"
    assert label.spans[0].style == RELATION_SEPARATOR
    assert "/" not in label.plain


def test_asset_portfolio_label_uses_row_key_style_in_key_column(monkeypatch) -> None:
    tables = []

    def record_table(table):
        tables.append(table)

    monkeypatch.setattr(console_output, "_print_table", record_table)

    console_output.print_assets(
        [
            Asset(
                portfolio_name="etfs",
                symbol="etha",
                quantity=Decimal("1"),
                cost_basis_minor=10_000,
                realized_pnl_minor=0,
                income_minor=0,
                total_buy_cost_minor=10_000,
                price_display_scale=2,
            )
        ]
    )

    label = tables[0].columns[0]._cells[0]

    assert tables[0].columns[0].header.plain == "Asset/Portfolio"
    assert tables[0].columns[0].header.style != ROW_KEY
    assert label.plain == "ETHA • Etfs"
    assert label.style == ROW_KEY
    assert any(span.style == RELATION_SEPARATOR for span in label.spans)
    assert "/" not in label.plain


def test_shared_table_helper_renders_connected_solid_row_separators() -> None:
    output_console = Console(width=80, record=True)
    table = console_output._make_table()
    table.add_column("Name")
    table.add_column("Value", justify="right")
    table.add_row("alpha", "1")
    table.add_row("beta", "2")

    output_console.print(table)
    rendered = output_console.export_text()
    lines = rendered.splitlines()
    separator_indexes = [
        index
        for index, line in enumerate(lines)
        if line.startswith("├") and "──" in line
    ]
    separator = lines[separator_indexes[1]]

    assert "╭" in rendered
    assert "╮" in rendered
    assert "╰" in rendered
    assert "╯" in rendered
    assert separator.startswith("├─")
    assert separator.endswith("─┤")
    assert "- -" not in separator
    assert "┼" not in separator
    assert "┬" not in separator
    assert "┴" not in separator
    assert separator.count("│") == 0
    assert len(separator_indexes) == 2
    assert (
        lines.index(next(line for line in lines if "alpha" in line))
        < (separator_indexes[1])
    )
    beta_row = next(line for line in lines if "beta" in line)
    assert separator_indexes[1] < lines.index(beta_row)


def test_table_output_uses_rounded_row_oriented_layout(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(price="100", quantity="1")

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 0
    assert "╭" in result.output
    assert "╮" in result.output
    assert "╰" in result.output
    assert "╯" in result.output
    assert "┬" not in result.output
    assert "┼" not in result.output
    assert "┴" not in result.output
    row = next(line for line in result.output.splitlines() if "100.00" in line)
    assert row.count("│") == 2


def test_capital_log_styles_type_and_withdrawal_amount() -> None:
    assert format_capital_entry_type("outflow").plain == "withdraw"
    assert format_capital_entry_type("outflow").style == LOSS
    assert format_capital_entry_amount("outflow", 25_000).plain == "250.00"
    assert format_capital_entry_amount("outflow", 25_000).style == LOSS

    assert format_capital_entry_type("inflow").plain == "deposit"
    assert format_capital_entry_type("inflow").style == PROFIT
    assert format_capital_entry_amount("inflow", 100_000).plain == "1,000.00"
    assert format_capital_entry_amount("inflow", 100_000).style == TABLE_CELL


def test_type_column_values_use_transaction_semantic_styles() -> None:
    assert style_transaction_type("deposit").plain == "deposit"
    assert style_transaction_type("deposit").style == PROFIT
    assert style_transaction_type("Deposit").plain == "Deposit"
    assert style_transaction_type("Deposit").style == PROFIT
    assert style_transaction_type("withdraw").style == LOSS
    assert style_transaction_type("Withdraw").style == LOSS
    assert style_transaction_type("buy").style == PROFIT
    assert style_transaction_type("Buy").style == PROFIT
    assert style_transaction_type("sell").style == LOSS
    assert style_transaction_type("Sell").style == LOSS
    assert style_transaction_type("income").style == INCOME
    assert style_transaction_type("Income").style == INCOME


def test_signed_percent_uses_exact_formula_and_neutral_zero() -> None:
    assert format_signed_percent(1700, 10_000) == "+17.00%"
    assert format_signed_percent(-1700, 10_000) == "-17.00%"
    assert format_signed_percent(0, 10_000) == "0.00%"
    assert format_signed_percent(1700, 0) == "0.00%"


def test_asset_log_styles_only_income_total_as_income(
    monkeypatch,
) -> None:
    styled_amounts: list[int] = []

    def record_income_style(amount_minor: int):
        styled_amounts.append(amount_minor)
        return format_income_money(amount_minor)

    monkeypatch.setattr(console_output, "format_income_money", record_income_style)
    transactions = [
        AssetTransaction(
            1, date.today().isoformat(), "buy", "100", "1", 0, 10_000, None
        ),
        AssetTransaction(
            2, date.today().isoformat(), "sell", "110", "1", 0, 11_000, None
        ),
        AssetTransaction(
            3, date.today().isoformat(), "income", None, None, 0, 500, None
        ),
    ]

    console_output.print_asset_transaction_log("stocks", "AAPL", transactions)

    assert styled_amounts == [500]


def test_asset_log_styles_type_column_values(
    monkeypatch,
) -> None:
    styled_types: list[str] = []

    def record_type_style(transaction_type: str):
        styled_types.append(transaction_type)
        return style_transaction_type(transaction_type)

    monkeypatch.setattr(console_output, "style_transaction_type", record_type_style)
    transactions = [
        AssetTransaction(
            1, date.today().isoformat(), "buy", "100", "1", 0, 10_000, None
        ),
        AssetTransaction(
            2, date.today().isoformat(), "sell", "110", "1", 0, 11_000, None
        ),
        AssetTransaction(
            3, date.today().isoformat(), "income", None, None, 0, 500, None
        ),
    ]

    console_output.print_asset_transaction_log("stocks", "AAPL", transactions)

    assert styled_types == ["buy", "sell", "income"]


def test_buy_sell_income_formulas_remain_correct_with_signed_display(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(price="100", quantity="10")
    _sell(price="150", quantity="3")
    assert (
        runner.invoke(app, ["asset", "income", "AAPL", "20", "-p", "stocks"]).exit_code
        == 0
    )

    asset_summary = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])
    portfolio = runner.invoke(app, ["summary", "-p", "stocks"])

    assert "+150.00" in asset_summary.output
    assert "20.00" in asset_summary.output
    assert "+17.00%" in asset_summary.output
    assert "+150.00" in portfolio.output
    assert "20.00" in portfolio.output
    assert "+17.00%" in portfolio.output


def test_asset_log_price_display_preserves_two_decimal_price_style(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(price="1.30", quantity="3")

    result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])

    assert result.exit_code == 0
    row = next(line for line in result.output.splitlines() if "buy" in line)
    assert "1.30" in row
    assert " 3 " in row
    assert "3.000000000000000000" not in row


def test_asset_log_tiny_price_display_preserves_inferred_precision(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(price="0.00334", quantity="1000")

    result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])

    assert result.exit_code == 0
    assert "0.00334" in result.output


def test_fractional_quantity_display_is_dynamic_without_padding(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(price="100", quantity="0.0433")

    log_result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])
    summary_result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert log_result.exit_code == 0
    assert summary_result.exit_code == 0
    assert "0.0433" in log_result.output
    assert "0.0433" in summary_result.output
    assert "0.043300000000000000" not in log_result.output
    assert "0.043300000000000000" not in summary_result.output


def test_asset_summary_average_cost_does_not_show_raw_decimal_tail(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(price="1.00", quantity="1")
    _buy(price="1.31", quantity="2")

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 0
    assert "1.21" in result.output
    assert "1.206666" not in result.output
