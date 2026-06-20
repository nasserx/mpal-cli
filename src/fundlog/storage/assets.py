"""Asset persistence operations."""

from dataclasses import dataclass
from pathlib import Path

from fundlog.assets import normalize_symbol
from fundlog.errors import (
    AssetAlreadyExistsError,
    InvalidSymbolError,
    PortfolioNotFoundError,
)
from fundlog.storage.database import connect_database


@dataclass(frozen=True)
class Asset:
    """One active portfolio-owned asset."""

    symbol: str


def create_assets(
    portfolio_name: str,
    symbols: list[str],
    database_path: Path | None = None,
) -> list[str]:
    """Atomically create normalized active assets for one active portfolio."""
    if not symbols:
        raise InvalidSymbolError("At least one symbol is required.")
    normalized_symbols = [normalize_symbol(symbol) for symbol in symbols]
    if len(normalized_symbols) != len(set(normalized_symbols)):
        raise AssetAlreadyExistsError(
            "Duplicate symbols were provided in the same asset add command."
        )

    with connect_database(database_path) as connection:
        portfolio = connection.execute(
            "SELECT id FROM portfolios WHERE name = ? AND deleted_at IS NULL",
            (portfolio_name,),
        ).fetchone()
        if portfolio is None:
            raise PortfolioNotFoundError(
                f"Active portfolio '{portfolio_name}' does not exist."
            )

        placeholders = ", ".join("?" for _ in normalized_symbols)
        existing = connection.execute(
            f"""
            SELECT symbol
            FROM assets
            WHERE portfolio_id = ?
                AND deleted_at IS NULL
                AND symbol IN ({placeholders})
            ORDER BY symbol
            """,
            (portfolio[0], *normalized_symbols),
        ).fetchall()
        if existing:
            raise AssetAlreadyExistsError(
                f"Active asset '{existing[0][0]}' already exists in portfolio "
                f"'{portfolio_name}'."
            )

        connection.executemany(
            "INSERT INTO assets (portfolio_id, symbol) VALUES (?, ?)",
            [(portfolio[0], symbol) for symbol in normalized_symbols],
        )

    return normalized_symbols


def get_assets(
    portfolio_name: str,
    database_path: Path | None = None,
) -> list[Asset]:
    """Return active assets for one active portfolio ordered by symbol."""
    with connect_database(database_path) as connection:
        portfolio = connection.execute(
            "SELECT id FROM portfolios WHERE name = ? AND deleted_at IS NULL",
            (portfolio_name,),
        ).fetchone()
        if portfolio is None:
            raise PortfolioNotFoundError(
                f"Active portfolio '{portfolio_name}' does not exist."
            )

        rows = connection.execute(
            """
            SELECT symbol
            FROM assets
            WHERE portfolio_id = ? AND deleted_at IS NULL
            ORDER BY symbol ASC
            """,
            (portfolio[0],),
        ).fetchall()

    return [Asset(symbol=row[0]) for row in rows]
