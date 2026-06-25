"""Rich terminal output helpers."""

from decimal import Decimal, localcontext

from rich.console import Console
from rich.table import Table
from rich.text import Text

from mpal.amounts import format_money
from mpal.numbers import (
    format_price_display,
    format_quantity,
    infer_price_display_scale,
)
from mpal.output.formatting import (
    format_capital_entry_amount,
    format_capital_entry_type,
    format_income_money,
    format_profit_loss_money,
    format_profit_loss_percent,
)
from mpal.output.theme import (
    ERROR,
    INFO,
    SUCCESS,
    TABLE_BORDER,
    TABLE_CELL,
    TABLE_HEADER,
    WARNING,
)
from mpal.storage.asset_logs import AssetTransaction
from mpal.storage.assets import Asset
from mpal.storage.logs import CapitalEntry
from mpal.storage.summaries import PortfolioSummary


def print_message(message: str) -> None:
    """Print a normal text message through Rich."""
    _print_styled_message(message, TABLE_CELL)


def print_success(message: str) -> None:
    """Print a successful operation message."""
    _print_styled_message(message, SUCCESS)


def print_error(message: str) -> None:
    """Print an expected user-facing error."""
    _print_styled_message(message, ERROR, stderr=True)


def print_info(message: str) -> None:
    """Print secondary informational output."""
    _print_styled_message(message, INFO)


def print_warning(message: str) -> None:
    """Print a warning or confirmation-related error."""
    _print_styled_message(message, WARNING, stderr=True)


def _print_styled_message(
    message: str,
    style: str,
    *,
    stderr: bool = False,
) -> None:
    """Print literal message text with one semantic style."""
    Console(stderr=stderr).print(Text(message, style=style))


def print_portfolio_summary(summary: PortfolioSummary) -> None:
    """Print one portfolio summary using the documented columns."""
    print_portfolio_summaries([summary])


def print_portfolio_summaries(summaries: list[PortfolioSummary]) -> None:
    """Print portfolio summaries using the documented columns."""
    table = Table(
        header_style=TABLE_HEADER,
        border_style=TABLE_BORDER,
        style=TABLE_CELL,
    )
    table.add_column("Portfolio")
    table.add_column("Capital", justify="right")
    table.add_column("Cash", justify="right")
    table.add_column("Positions", justify="right")
    table.add_column("Book Value", justify="right")
    table.add_column("Realized PnL", justify="right")
    table.add_column("Income", justify="right")
    table.add_column("Return", justify="right")
    for summary in summaries:
        table.add_row(
            summary.portfolio_name,
            format_money(summary.capital_minor),
            format_money(summary.cash_minor),
            format_money(summary.positions_minor),
            format_money(summary.book_value_minor),
            format_profit_loss_money(summary.realized_pnl_minor),
            format_income_money(summary.income_minor),
            format_profit_loss_percent(
                summary.realized_pnl_minor + summary.income_minor,
                summary.capital_minor,
            ),
        )
    Console(width=120).print(table)


def print_assets(assets: list[Asset]) -> None:
    """Print portfolio-wide active asset summaries."""
    table = Table(
        header_style=TABLE_HEADER,
        border_style=TABLE_BORDER,
        style=TABLE_CELL,
    )
    table.add_column("Asset")
    table.add_column("Quantity", justify="right")
    table.add_column("Cost Basis", justify="right")
    table.add_column("Average Cost", justify="right")
    table.add_column("Realized PnL", justify="right")
    table.add_column("Income", justify="right")
    table.add_column("Realized Return", justify="right")
    for asset in assets:
        table.add_row(
            asset.symbol,
            format_quantity(asset.quantity),
            format_money(asset.cost_basis_minor),
            _format_average_cost(
                asset.cost_basis_minor,
                asset.quantity,
                asset.price_display_scale,
            ),
            format_profit_loss_money(asset.realized_pnl_minor),
            format_income_money(asset.income_minor),
            format_profit_loss_percent(
                asset.realized_pnl_minor + asset.income_minor,
                asset.total_buy_cost_minor,
            ),
        )
    Console(width=120).print(table)


def print_asset_summary(portfolio_name: str, asset: Asset) -> None:
    """Print one active asset's derived accounting summary."""
    console = Console(width=120)

    table = Table(
        header_style=TABLE_HEADER,
        border_style=TABLE_BORDER,
        style=TABLE_CELL,
    )
    table.add_column("Quantity", justify="right")
    table.add_column("Cost Basis", justify="right")
    table.add_column("Average Cost", justify="right")
    table.add_column("Realized PnL", justify="right")
    table.add_column("Income", justify="right")
    table.add_column("Realized Return", justify="right")
    table.add_row(
        format_quantity(asset.quantity),
        format_money(asset.cost_basis_minor),
        _format_average_cost(
            asset.cost_basis_minor,
            asset.quantity,
            asset.price_display_scale,
        ),
        format_profit_loss_money(asset.realized_pnl_minor),
        format_income_money(asset.income_minor),
        format_profit_loss_percent(
            asset.realized_pnl_minor + asset.income_minor,
            asset.total_buy_cost_minor,
        ),
    )
    console.print(table)


def print_asset_transaction_log(
    portfolio_name: str,
    symbol: str,
    transactions: list[AssetTransaction],
) -> None:
    """Print one asset's active transactions using the documented columns."""
    console = Console(width=120)

    table = Table(
        header_style=TABLE_HEADER,
        border_style=TABLE_BORDER,
        style=TABLE_CELL,
    )
    table.add_column("#", justify="right")
    table.add_column("Date")
    table.add_column("Type")
    table.add_column("Price", justify="right")
    table.add_column("Quantity", justify="right")
    table.add_column("Fee", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Note")
    price_display_scale = infer_price_display_scale(
        [transaction.price_text for transaction in transactions]
    )
    for transaction in transactions:
        table.add_row(
            str(transaction.entry_no),
            transaction.transaction_date,
            transaction.transaction_type,
            (
                "--"
                if transaction.price_text is None
                else format_price_display(
                    transaction.price_text,
                    price_display_scale,
                )
            ),
            (
                "--"
                if transaction.quantity_text is None
                else format_quantity(transaction.quantity_text)
            ),
            (
                "--"
                if transaction.transaction_type == "income"
                else format_money(transaction.fee_minor)
            ),
            (
                format_income_money(transaction.total_minor)
                if transaction.transaction_type == "income"
                else format_money(transaction.total_minor)
            ),
            transaction.note or "",
        )
    console.print(table)


def _format_average_cost(
    cost_basis_minor: int,
    quantity: Decimal,
    price_display_scale: int,
) -> str:
    """Format derived unit book cost with deterministic price precision."""
    if quantity == 0:
        return "--"
    with localcontext() as context:
        context.prec = 80
        average_cost = Decimal(cost_basis_minor) / Decimal(100) / quantity
    return format_price_display(average_cost, price_display_scale)


def print_capital_entry_log(entries: list[CapitalEntry]) -> None:
    """Print active capital entries using the documented log columns."""
    table = Table(
        header_style=TABLE_HEADER,
        border_style=TABLE_BORDER,
        style=TABLE_CELL,
    )
    table.add_column("#", justify="right")
    table.add_column("Date")
    table.add_column("Type")
    table.add_column("Amount", justify="right")
    table.add_column("Note")
    for entry in entries:
        table.add_row(
            str(entry.entry_no),
            entry.entry_date,
            format_capital_entry_type(entry.entry_type),
            format_capital_entry_amount(entry.entry_type, entry.amount_minor),
            entry.note or "",
        )
    Console().print(table)
