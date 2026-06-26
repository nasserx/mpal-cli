"""Asset persistence operations."""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from mpal.assets import normalize_symbol
from mpal.errors import (
    AssetAlreadyExistsError,
    AssetNotFoundError,
    InvalidSymbolError,
    PortfolioNotFoundError,
)
from mpal.numbers import infer_price_display_scale
from mpal.storage.database import connect_database


@dataclass(frozen=True)
class Asset:
    """One active portfolio-owned asset."""

    portfolio_name: str
    symbol: str
    quantity: Decimal
    cost_basis_minor: int
    realized_pnl_minor: int
    income_minor: int
    total_buy_cost_minor: int
    price_display_scale: int


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

        asset_rows = connection.execute(
            """
            SELECT a.id, a.symbol
            FROM assets AS a
            WHERE a.portfolio_id = ? AND a.deleted_at IS NULL
            ORDER BY a.symbol ASC
            """,
            (portfolio[0],),
        ).fetchall()

        assets: list[Asset] = []
        for asset_id, symbol in asset_rows:
            transactions = _get_active_transactions(connection, asset_id)
            assets.append(_aggregate_asset(portfolio_name, symbol, transactions))

    return assets


def get_all_assets(database_path: Path | None = None) -> list[Asset]:
    """Return active assets across all active portfolios."""
    with connect_database(database_path) as connection:
        asset_rows = connection.execute(
            """
            SELECT a.id, p.name, a.symbol
            FROM assets AS a
            JOIN portfolios AS p ON p.id = a.portfolio_id
            WHERE a.deleted_at IS NULL
                AND p.deleted_at IS NULL
            ORDER BY p.name ASC, a.symbol ASC
            """
        ).fetchall()

        assets: list[Asset] = []
        for asset_id, portfolio_name, symbol in asset_rows:
            transactions = _get_active_transactions(connection, asset_id)
            assets.append(_aggregate_asset(portfolio_name, symbol, transactions))

    return assets


def get_asset_summary(
    portfolio_name: str,
    symbol: str,
    database_path: Path | None = None,
) -> Asset:
    """Return derived summary values for one active asset."""
    with connect_database(database_path) as connection:
        portfolio = connection.execute(
            "SELECT id FROM portfolios WHERE name = ? AND deleted_at IS NULL",
            (portfolio_name,),
        ).fetchone()
        if portfolio is None:
            raise PortfolioNotFoundError(
                f"Active portfolio '{portfolio_name}' does not exist."
            )

        asset = connection.execute(
            """
            SELECT id, symbol
            FROM assets
            WHERE portfolio_id = ?
                AND symbol = ?
                AND deleted_at IS NULL
            """,
            (portfolio[0], symbol),
        ).fetchone()
        if asset is None:
            raise AssetNotFoundError(
                f"Active asset '{symbol}' does not exist in portfolio "
                f"'{portfolio_name}'."
            )

        transactions = _get_active_transactions(connection, asset[0])

    return _aggregate_asset(portfolio_name, asset[1], transactions)


def _get_active_transactions(
    connection,
    asset_id: int,
) -> list[tuple[str, str | None, str | None, int, int, int, int]]:
    """Return the active transaction fields used by asset aggregations."""
    return connection.execute(
        """
        SELECT
            transaction_type,
            price_text,
            quantity_text,
            position_effect_minor,
            realized_pnl_minor,
            income_minor,
            total_minor
        FROM asset_transactions
        WHERE asset_id = ? AND deleted_at IS NULL
        """,
        (asset_id,),
    ).fetchall()


def _aggregate_asset(
    portfolio_name: str,
    symbol: str,
    transactions: list[tuple[str, str | None, str | None, int, int, int, int]],
) -> Asset:
    """Aggregate active transactions into current asset accounting values."""
    quantity = sum(
        (
            (Decimal(row[2]) if row[0] == "buy" else -Decimal(row[2]))
            for row in transactions
            if row[0] in {"buy", "sell"} and row[2] is not None
        ),
        Decimal(0),
    )
    return Asset(
        portfolio_name=portfolio_name,
        symbol=symbol,
        quantity=quantity,
        cost_basis_minor=sum(row[3] for row in transactions),
        realized_pnl_minor=sum(row[4] for row in transactions if row[0] == "sell"),
        income_minor=sum(row[5] for row in transactions),
        total_buy_cost_minor=sum(row[6] for row in transactions if row[0] == "buy"),
        price_display_scale=infer_price_display_scale(
            [row[1] for row in transactions if row[0] in {"buy", "sell"}]
        ),
    )


def delete_asset(
    portfolio_name: str,
    symbol: str,
    database_path: Path | None = None,
) -> None:
    """Soft-delete one active asset from an active portfolio."""
    with connect_database(database_path) as connection:
        portfolio = connection.execute(
            "SELECT id FROM portfolios WHERE name = ? AND deleted_at IS NULL",
            (portfolio_name,),
        ).fetchone()
        if portfolio is None:
            raise PortfolioNotFoundError(
                f"Active portfolio '{portfolio_name}' does not exist."
            )

        asset = connection.execute(
            """
            SELECT id
            FROM assets
            WHERE portfolio_id = ?
                AND symbol = ?
                AND deleted_at IS NULL
            """,
            (portfolio[0], symbol),
        ).fetchone()
        if asset is None:
            raise AssetNotFoundError(
                f"Active asset '{symbol}' does not exist in portfolio "
                f"'{portfolio_name}'."
            )

        connection.execute(
            """
            UPDATE asset_transactions
            SET deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE asset_id = ? AND deleted_at IS NULL
            """,
            (asset[0],),
        )
        connection.execute(
            """
            UPDATE assets
            SET deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND deleted_at IS NULL
            """,
            (asset[0],),
        )
