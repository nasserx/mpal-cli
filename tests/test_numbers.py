"""Tests for exact quantity and price parsing and formatting."""

from decimal import Decimal

import pytest

from mpal.errors import InvalidPriceError, InvalidQuantityError
from mpal.numbers import (
    format_price,
    format_price_display,
    format_quantity,
    infer_price_display_scale,
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


@pytest.mark.parametrize(
    ("value", "scale", "expected"),
    [
        ("1.3", 2, "1.30"),
        ("123456.0543", 5, "123,456.05430"),
        (Decimal("22.039460953697304768"), 2, "22.04"),
        ("0.003335", 5, "0.00334"),
    ],
)
def test_format_price_display_uses_fixed_scale_with_grouping(
    value: Decimal | str,
    scale: int,
    expected: str,
) -> None:
    assert format_price_display(value, scale) == expected


def test_format_price_display_rounds_half_even() -> None:
    assert format_price_display("1.225", 2) == "1.22"
    assert format_price_display("1.235", 2) == "1.24"


def test_infer_price_display_scale_uses_asset_prices_with_two_place_minimum() -> None:
    assert infer_price_display_scale([None]) == 2
    assert infer_price_display_scale(["1"]) == 2
    assert infer_price_display_scale(["1.3"]) == 2
    assert infer_price_display_scale(["1.3", "0.00334"]) == 5


def test_formatters_reject_python_float() -> None:
    with pytest.raises(TypeError):
        format_quantity(0.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        format_price(0.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        format_price_display(0.5, 2)  # type: ignore[arg-type]
