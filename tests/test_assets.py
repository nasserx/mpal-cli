"""Tests for asset symbol normalization."""

import pytest

from fundlog.assets import normalize_symbol
from fundlog.errors import InvalidSymbolError


@pytest.mark.parametrize(
    ("symbol", "normalized"),
    [
        ("AAPL", "AAPL"),
        ("aapl", "AAPL"),
        ("BRK.B", "BRK.B"),
        ("BTC-USD", "BTC-USD"),
        ("CUSTOM_1", "CUSTOM_1"),
    ],
)
def test_normalize_symbol_accepts_valid_symbols(
    symbol: str,
    normalized: str,
) -> None:
    assert normalize_symbol(symbol) == normalized


@pytest.mark.parametrize(
    "symbol",
    [
        "",
        "A APL",
        "AAPL ",
        "AAPL/MSFT",
        ".AAPL",
        "-AAPL",
        "_AAPL",
        "A" * 33,
        "AAPL$",
    ],
)
def test_normalize_symbol_rejects_invalid_symbols(symbol: str) -> None:
    with pytest.raises(InvalidSymbolError):
        normalize_symbol(symbol)
