"""Semantic formatting helpers for financial result output."""

from decimal import ROUND_HALF_EVEN, Decimal

from rich.text import Text

from mpal.amounts import format_money, format_signed_money
from mpal.output.theme import (
    INCOME,
    LOSS,
    MUTED,
    PROFIT,
    RELATION_SEPARATOR,
    ROW_KEY,
    TABLE_CELL,
)


def format_asset_portfolio_header() -> Text:
    """Format the combined asset and portfolio column header."""
    return Text("Asset/Portfolio")


def format_asset_portfolio_label(symbol: str, portfolio_name: str) -> Text:
    """Format an asset/portfolio relationship label for display."""
    return _format_asset_portfolio_text(
        symbol.upper(),
        _display_portfolio_name(portfolio_name),
    )


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


def format_allocation_percent(
    book_value_minor: int,
    total_book_value_minor: int,
) -> str:
    """Format an unsigned allocation percentage from book value."""
    percentage = _percentage(book_value_minor, total_book_value_minor)
    return f"{percentage:.2f}%"


def format_income_money(amount_minor: int) -> Text:
    """Format income money with the shared calm income style."""
    return Text(format_money(amount_minor), style=INCOME)


def format_capital_entry_type(entry_type: str) -> Text:
    """Format an internal capital entry type for user-facing logs."""
    if entry_type == "outflow":
        return style_transaction_type("withdraw")
    return style_transaction_type("deposit")


def style_transaction_type(transaction_type: str) -> Text:
    """Style a user-facing Type column value by transaction semantics."""
    normalized = transaction_type.lower()
    if normalized in {"buy", "deposit"}:
        style = PROFIT
    elif normalized in {"sell", "withdraw"}:
        style = LOSS
    elif normalized == "income":
        style = INCOME
    else:
        style = TABLE_CELL
    return Text(transaction_type, style=style)


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


def _format_asset_portfolio_text(
    left: str,
    right: str,
    *,
    text_style: str | None = TABLE_CELL,
) -> Text:
    left_style = ROW_KEY if text_style == TABLE_CELL else text_style
    right_style = MUTED if text_style == TABLE_CELL else text_style
    text = Text(left, style=left_style)
    text.append(" ")
    text.append("•", style=RELATION_SEPARATOR)
    text.append(" ")
    text.append(right, style=right_style)
    return text


def _display_portfolio_name(portfolio_name: str) -> str:
    if not portfolio_name:
        return portfolio_name
    return f"{portfolio_name[0].upper()}{portfolio_name[1:]}"


def _percentage(result_minor: int, denominator_minor: int) -> Decimal:
    """Calculate a display percentage with deterministic zero handling."""
    if denominator_minor == 0:
        return Decimal("0.00")
    return (Decimal(result_minor) * Decimal(100) / Decimal(denominator_minor)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_EVEN
    )
