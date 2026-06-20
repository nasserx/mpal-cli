"""Tests for exact monetary parsing and display formatting."""

import pytest

from fundlog.amounts import format_money, format_signed_money


@pytest.mark.parametrize(
    ("amount_minor", "expected"),
    [
        (0, "0.00"),
        (10_000, "100.00"),
        (100_000, "1,000.00"),
        (500_050, "5,000.50"),
        (123_456_789, "1,234,567.89"),
        (-123_456, "-1,234.56"),
    ],
)
def test_format_money(amount_minor: int, expected: str) -> None:
    assert format_money(amount_minor) == expected


@pytest.mark.parametrize(
    ("amount_minor", "expected"),
    [
        (1_000, "+10.00"),
        (-1_000, "-10.00"),
        (0, "0.00"),
    ],
)
def test_format_signed_money(amount_minor: int, expected: str) -> None:
    assert format_signed_money(amount_minor) == expected
