"""Tests for exact quantity and price parsing and formatting."""

from decimal import Decimal

import pytest

from fundlog.errors import InvalidPriceError, InvalidQuantityError
from fundlog.numbers import (
    format_price,
    format_quantity,
    parse_price,
    parse_quantity,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("3", Decimal("3")),
        ("3.5000", Decimal("3.5")),
        ("0.0538", Decimal("0.0538")),
        ("123456", Decimal("123456")),
        ("123456.0543", Decimal("123456.0543")),
        ("0003.5000", Decimal("3.5")),
        (
            "999999999999999999.123456789012345678",
            Decimal("999999999999999999.123456789012345678"),
        ),
    ],
)
def test_parse_quantity_accepts_and_normalizes_valid_values(
    value: str,
    expected: Decimal,
) -> None:
    assert parse_quantity(value) == expected
    assert str(parse_quantity(value)) == str(expected)


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "abc",
        "NaN",
        "Infinity",
        "1e3",
        "1E-3",
        "+1",
        "-1",
        "0",
        "0.000",
        ".5",
        "1.",
        "1,000",
        "1234567890123456789",
        "1.1234567890123456789",
    ],
)
def test_parse_quantity_rejects_invalid_values(value: str) -> None:
    with pytest.raises(InvalidQuantityError):
        parse_quantity(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("3"), "3"),
        ("3.5000", "3.5"),
        (Decimal("0.0538"), "0.0538"),
        ("123456", "123,456"),
        (Decimal("123456.0543"), "123,456.0543"),
        (Decimal("0"), "0"),
    ],
)
def test_format_quantity_preserves_precision_and_groups_integer_part(
    value: Decimal | str,
    expected: str,
) -> None:
    assert format_quantity(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("234.43", Decimal("234.43")),
        ("0.000533", Decimal("0.000533")),
        ("123456.0543", Decimal("123456.0543")),
        ("000234.4300", Decimal("234.43")),
        (
            "999999999999999999.123456789012345678",
            Decimal("999999999999999999.123456789012345678"),
        ),
    ],
)
def test_parse_price_accepts_and_normalizes_valid_values(
    value: str,
    expected: Decimal,
) -> None:
    assert parse_price(value) == expected
    assert str(parse_price(value)) == str(expected)


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "abc",
        "NaN",
        "Infinity",
        "1e3",
        "1E-3",
        "+1",
        "-1",
        "0",
        "0.000",
        ".5",
        "1.",
        "1,000",
        "1234567890123456789",
        "1.1234567890123456789",
    ],
)
def test_parse_price_rejects_invalid_values(value: str) -> None:
    with pytest.raises(InvalidPriceError):
        parse_price(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("234.43"), "234.43"),
        ("0.000533", "0.000533"),
        (Decimal("123456.0543"), "123,456.0543"),
        ("000234.4300", "234.43"),
    ],
)
def test_format_price_preserves_high_precision_and_groups_integer_part(
    value: Decimal | str,
    expected: str,
) -> None:
    assert format_price(value) == expected


def test_formatters_reject_python_float() -> None:
    with pytest.raises(TypeError):
        format_quantity(0.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        format_price(0.5)  # type: ignore[arg-type]
