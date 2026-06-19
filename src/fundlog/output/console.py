"""Rich terminal output helpers."""

from rich.console import Console
from rich.table import Table

from fundlog.amounts import format_amount_minor
from fundlog.storage.logs import CapitalEntry
from fundlog.storage.summaries import PortfolioSummary


def print_message(message: str) -> None:
    """Print a plain message through Rich."""
    Console().print(message)


def print_portfolio_summary(summary: PortfolioSummary) -> None:
    """Print one portfolio summary using the documented columns."""
    table = Table()
    table.add_column("id", justify="right")
    table.add_column("Portfolio")
    table.add_column("Capital", justify="right")
    table.add_column("Cash", justify="right")
    table.add_column("Invested", justify="right")
    table.add_column("Value", justify="right")
    table.add_column("PnL", justify="right")
    table.add_column("Return", justify="right")
    table.add_row(
        str(summary.portfolio_id),
        summary.portfolio_name,
        format_amount_minor(summary.capital_minor),
        format_amount_minor(summary.cash_minor),
        format_amount_minor(summary.invested_minor),
        format_amount_minor(summary.value_minor),
        "0.00",
        "0.00%",
    )
    Console().print(table)


def print_capital_entry_log(entries: list[CapitalEntry]) -> None:
    """Print active capital entries using the documented log columns."""
    table = Table()
    table.add_column("id", justify="right")
    table.add_column("Date")
    table.add_column("Type")
    table.add_column("Amount", justify="right")
    table.add_column("Note")
    for entry in entries:
        table.add_row(
            str(entry.entry_id),
            entry.entry_date,
            entry.entry_type,
            format_amount_minor(entry.amount_minor),
            entry.note or "",
        )
    Console().print(table)
