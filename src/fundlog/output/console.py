"""Rich terminal output helpers."""

from rich.console import Console
from rich.table import Table
from rich.text import Text

from fundlog.amounts import format_money
from fundlog.output.theme import (
    ERROR,
    INFO,
    SUCCESS,
    TABLE_BORDER,
    TABLE_CELL,
    TABLE_HEADER,
    WARNING,
)
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
            "0.00%",
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
            "0",
            format_money(0),
            format_money(0),
            format_money(0),
            "0.00%",
        )
    Console().print(table)


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
