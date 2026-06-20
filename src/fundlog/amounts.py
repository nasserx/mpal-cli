"""Exact monetary parsing and money-specific display formatting."""

from decimal import Decimal, InvalidOperation

from fundlog.errors import InvalidAmountError

MINOR_UNITS_PER_UNIT = 100


def parse_amount_minor(amount: str) -> int:
    """Parse a positive amount with at most two decimal places."""
    try:
        decimal_amount = Decimal(amount)
    except InvalidOperation as error:
        raise InvalidAmountError(f"Invalid amount: '{amount}'.") from error

    if not decimal_amount.is_finite():
        raise InvalidAmountError(f"Invalid amount: '{amount}'.")
    if decimal_amount <= 0:
        raise InvalidAmountError("Amount must be greater than zero.")
    if decimal_amount.as_tuple().exponent < -2:
        raise InvalidAmountError("Amount cannot have more than 2 decimal places.")

    minor_amount = decimal_amount * MINOR_UNITS_PER_UNIT
    if minor_amount != minor_amount.to_integral_value():
        raise InvalidAmountError("Amount cannot have more than 2 decimal places.")

    return int(minor_amount)


def format_money(amount_minor: int) -> str:
    """Format integer minor units as money with grouping and two places."""
    sign = "-" if amount_minor < 0 else ""
    whole, fraction = divmod(abs(amount_minor), MINOR_UNITS_PER_UNIT)
    return f"{sign}{whole:,}.{fraction:02d}"
