"""Rich terminal output helpers."""

from decimal import ROUND_HALF_EVEN, Decimal

from rich.console import Console
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from fundlog.amounts import format_money
from fundlog.numbers import format_price, format_quantity
from fundlog.output.theme import (
    ERROR,
    INFO,
    SUCCESS,
    TABLE_BORDER,
    TABLE_CELL,
    TABLE_HEADER,
    WARNING,
)
from fundlog.storage.asset_logs import AssetTransaction
from fundlog.storage.assets import Asset
from fundlog.storage.logs import CapitalEntry
from fundlog.storage.summaries import PortfolioSummary


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
            format_money(summary.realized_pnl_minor),
            format_money(summary.income_minor),
            _format_return(
                summary.realized_pnl_minor + summary.income_minor,
                summary.capital_minor,
            ),
        )
    Console(width=120).print(table)


def print_assets(assets: list[Asset]) -> None:
    """Print active assets using the initial asset-foundation columns."""
    table = Table(
        header_style=TABLE_HEADER,
        border_style=TABLE_BORDER,
        style=TABLE_CELL,
    )
    table.add_column("Symbol")
    table.add_column("Quantity", justify="right")
    table.add_column("Cost Basis", justify="right")
    table.add_column("Realized PnL", justify="right")
    table.add_column("Income", justify="right")
    table.add_column("Realized Return", justify="right")
    for asset in assets:
        table.add_row(
            asset.symbol,
            format_quantity(asset.quantity),
            format_money(asset.cost_basis_minor),
            format_money(asset.realized_pnl_minor),
            format_money(asset.income_minor),
            _format_return(
                asset.realized_pnl_minor + asset.income_minor,
                asset.total_buy_cost_minor,
            ),
        )
    Console().print(table)


def print_asset_transaction_log(
    portfolio_name: str,
    symbol: str,
    transactions: list[AssetTransaction],
) -> None:
    """Print one asset's active transactions using the documented columns."""
    console = Console(width=120)
    title = Text(f"{symbol}/{portfolio_name}", style=TABLE_HEADER)
    console.print(Rule(title, style=TABLE_BORDER))

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
    for transaction in transactions:
        table.add_row(
            str(transaction.entry_no),
            transaction.transaction_date,
            transaction.transaction_type,
            (
                "--"
                if transaction.price_text is None
                else format_price(transaction.price_text)
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
            format_money(transaction.total_minor),
            transaction.note or "",
        )
    console.print(table)


def _format_return(result_minor: int, capital_minor: int) -> str:
    """Format realized return with deterministic zero-capital behavior."""
    if capital_minor == 0:
        return "0.00%"
    percentage = (
        Decimal(result_minor) * Decimal(100) / Decimal(capital_minor)
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    return f"{percentage:.2f}%"


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
            entry.entry_type,
            format_money(entry.amount_minor),
            entry.note or "",
        )
    Console().print(table)
