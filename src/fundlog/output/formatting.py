"""Semantic formatting helpers for financial result output."""

from decimal import ROUND_HALF_EVEN, Decimal

from rich.text import Text

from fundlog.amounts import format_money, format_signed_money
from fundlog.output.theme import INCOME, LOSS, PROFIT, TABLE_CELL


def format_signed_percent(result_minor: int, denominator_minor: int) -> str:
    """Format a return percentage with signed nonzero values."""
    percentage = _percentage(result_minor, denominator_minor)
    if percentage > 0:
        return f"+{percentage:.2f}%"
    return f"{percentage:.2f}%"


def format_profit_loss_money(amount_minor: int) -> Text:
    """Format and style realized profit or loss money."""
    return Text(format_signed_money(amount_minor), style=result_style(amount_minor))


def format_profit_loss_percent(
    result_minor: int,
    denominator_minor: int,
) -> Text:
    """Format and style a realized return percentage."""
    percentage = _percentage(result_minor, denominator_minor)
    return Text(
        (f"+{percentage:.2f}%" if percentage > 0 else f"{percentage:.2f}%"),
        style=result_style(percentage),
    )


def format_income_money(amount_minor: int) -> Text:
    """Format income money with the shared calm income style."""
    return Text(format_money(amount_minor), style=INCOME)


def format_capital_entry_type(entry_type: str) -> Text:
    """Format an internal capital entry type for user-facing logs."""
    if entry_type == "outflow":
        return Text("withdraw", style=LOSS)
    return Text("deposit", style=TABLE_CELL)


def format_capital_entry_amount(entry_type: str, amount_minor: int) -> Text:
    """Format capital-entry money with withdrawal-only loss styling."""
    style = LOSS if entry_type == "outflow" else TABLE_CELL
    return Text(format_money(amount_minor), style=style)


def result_style(value: int | Decimal) -> str:
    """Return the semantic style for a signed financial result."""
    if value > 0:
        return PROFIT
    if value < 0:
        return LOSS
    return TABLE_CELL


def _percentage(result_minor: int, denominator_minor: int) -> Decimal:
    """Calculate a display percentage with deterministic zero handling."""
    if denominator_minor == 0:
        return Decimal("0.00")
    return (Decimal(result_minor) * Decimal(100) / Decimal(denominator_minor)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_EVEN
    )
