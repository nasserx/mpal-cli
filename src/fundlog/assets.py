"""Asset symbol normalization and validation."""

import re

from fundlog.errors import InvalidAssetReferenceError, InvalidSymbolError

MAX_SYMBOL_LENGTH = 32
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]*$")


def normalize_symbol(symbol: str) -> str:
    """Return a validated uppercase asset symbol."""
    normalized = symbol.upper()
    if not normalized:
        raise InvalidSymbolError("Symbol cannot be empty.")
    if len(normalized) > MAX_SYMBOL_LENGTH:
        raise InvalidSymbolError(
            f"Symbol '{symbol}' cannot exceed {MAX_SYMBOL_LENGTH} characters."
        )
    if not SYMBOL_PATTERN.fullmatch(normalized):
        raise InvalidSymbolError(
            f"Invalid symbol '{symbol}'. Use letters, numbers, '.', '-', or '_'; "
            "start with a letter or number."
        )
    return normalized


def parse_asset_reference(reference: str) -> tuple[str, str]:
    """Return the portfolio name and normalized symbol from an asset reference."""
    if reference.count("/") != 1:
        raise InvalidAssetReferenceError(
            f"Invalid asset reference '{reference}'. "
            "Use <portfolio>/<symbol> with exactly one '/'."
        )

    portfolio_name, symbol = reference.split("/")
    if not portfolio_name or not symbol:
        raise InvalidAssetReferenceError(
            f"Invalid asset reference '{reference}'. "
            "Portfolio and symbol are both required."
        )

    return portfolio_name, normalize_symbol(symbol)
