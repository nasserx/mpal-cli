"""Exact parsing and display formatting for asset quantities and prices."""

import re
from decimal import ROUND_HALF_EVEN, Decimal

from mpal.errors import InvalidPriceError, InvalidQuantityError

MAX_INTEGER_DIGITS = 18
MAX_FRACTIONAL_DIGITS = 18
PLAIN_DECIMAL_PATTERN = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")


def parse_quantity(value: str) -> Decimal:
    """Parse and normalize a positive transaction quantity."""
    return _parse_positive_decimal(value, "Quantity", InvalidQuantityError)


def format_quantity(value: Decimal | str) -> str:
    """Format an exact quantity without money-specific precision rules."""
    return _format_decimal(value, "Quantity", InvalidQuantityError, allow_zero=True)


def parse_price(value: str) -> Decimal:
    """Parse and normalize a positive unit price."""
    return _parse_positive_decimal(value, "Price", InvalidPriceError)


def format_price(value: Decimal | str) -> str:
    """Format an exact unit price without money-specific precision rules."""
    return _format_decimal(value, "Price", InvalidPriceError, allow_zero=False)


def format_price_display(value: Decimal | str, scale: int) -> str:
    """Format a price-like value with a fixed display scale."""
    if isinstance(value, float):
        raise TypeError("Price formatting does not accept Python float.")
    if scale < 0 or scale > MAX_FRACTIONAL_DIGITS:
        raise InvalidPriceError(
            f"Price display scale must be between 0 and {MAX_FRACTIONAL_DIGITS}."
        )

    text = format(value, "f") if isinstance(value, Decimal) else value
    if not isinstance(text, str) or PLAIN_DECIMAL_PATTERN.fullmatch(text) is None:
        raise InvalidPriceError(f"Invalid price: '{text}'. Use plain decimal notation.")

    decimal_value = Decimal(text)
    if not decimal_value.is_finite():
        raise InvalidPriceError(f"Invalid price: '{text}'.")
    if decimal_value < 0:
        raise InvalidPriceError("Price must be nonnegative.")

    quantum = Decimal("1") if scale == 0 else Decimal(f"1e-{scale}")
    rounded = decimal_value.quantize(quantum, rounding=ROUND_HALF_EVEN)
    integer_part, _, fractional_part = f"{rounded:f}".partition(".")
    grouped_integer = f"{int(integer_part):,}"
    if scale == 0:
        return grouped_integer
    return f"{grouped_integer}.{fractional_part.ljust(scale, '0')}"


def infer_price_display_scale(
    price_texts: list[str | None] | tuple[str | None, ...],
    *,
    minimum: int = 2,
) -> int:
    """Infer a user-facing price display scale from stored price text values."""
    max_scale = minimum
    for price_text in price_texts:
        if price_text is None:
            continue
        _, separator, fractional_part = price_text.partition(".")
        if separator:
            max_scale = max(max_scale, len(fractional_part))
    return min(max_scale, MAX_FRACTIONAL_DIGITS)


def _parse_positive_decimal(
    value: str,
    label: str,
    error_type: type[InvalidQuantityError] | type[InvalidPriceError],
) -> Decimal:
    if not value or PLAIN_DECIMAL_PATTERN.fullmatch(value) is None:
        raise error_type(
            f"Invalid {label.lower()}: '{value}'. Use plain decimal notation."
        )

    integer_part, separator, fractional_part = value.partition(".")
    if len(integer_part) > MAX_INTEGER_DIGITS:
        raise error_type(
            f"{label} cannot have more than {MAX_INTEGER_DIGITS} digits "
            "before the decimal point."
        )
    if separator and len(fractional_part) > MAX_FRACTIONAL_DIGITS:
        raise error_type(
            f"{label} cannot have more than {MAX_FRACTIONAL_DIGITS} decimal places."
        )

    decimal_value = Decimal(value)
    if not decimal_value.is_finite():
        raise error_type(f"Invalid {label.lower()}: '{value}'.")
    if decimal_value <= 0:
        raise error_type(f"{label} must be greater than zero.")

    return Decimal(_normalize_decimal_text(value))


def _format_decimal(
    value: Decimal | str,
    label: str,
    error_type: type[InvalidQuantityError] | type[InvalidPriceError],
    *,
    allow_zero: bool,
) -> str:
    if isinstance(value, float):
        raise TypeError(f"{label} formatting does not accept Python float.")

    text = format(value, "f") if isinstance(value, Decimal) else value
    if not isinstance(text, str) or PLAIN_DECIMAL_PATTERN.fullmatch(text) is None:
        raise error_type(
            f"Invalid {label.lower()}: '{text}'. Use plain decimal notation."
        )

    integer_part, separator, fractional_part = text.partition(".")
    if len(integer_part) > MAX_INTEGER_DIGITS:
        raise error_type(
            f"{label} cannot have more than {MAX_INTEGER_DIGITS} digits "
            "before the decimal point."
        )
    if separator and len(fractional_part) > MAX_FRACTIONAL_DIGITS:
        raise error_type(
            f"{label} cannot have more than {MAX_FRACTIONAL_DIGITS} decimal places."
        )

    decimal_value = Decimal(text)
    if not decimal_value.is_finite():
        raise error_type(f"Invalid {label.lower()}: '{text}'.")
    if decimal_value < 0 or (decimal_value == 0 and not allow_zero):
        comparison = "nonnegative" if allow_zero else "greater than zero"
        raise error_type(f"{label} must be {comparison}.")

    normalized = _normalize_decimal_text(text)
    normalized_integer, separator, normalized_fraction = normalized.partition(".")
    grouped_integer = f"{int(normalized_integer):,}"
    if not separator:
        return grouped_integer
    return f"{grouped_integer}.{normalized_fraction}"


def _normalize_decimal_text(value: str) -> str:
    integer_part, separator, fractional_part = value.partition(".")
    normalized_integer = integer_part.lstrip("0") or "0"
    normalized_fraction = fractional_part.rstrip("0") if separator else ""
    if not normalized_fraction:
        return normalized_integer
    return f"{normalized_integer}.{normalized_fraction}"
