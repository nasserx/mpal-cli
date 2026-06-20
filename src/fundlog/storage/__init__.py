"""Local persistence primitives."""

from fundlog.storage.assets import Asset, create_assets, delete_asset, get_assets
from fundlog.storage.database import initialize_database
from fundlog.storage.entries import (
    delete_capital_entry,
    edit_capital_entry,
    record_inflow,
    record_outflow,
    reset_portfolio_entries,
)
from fundlog.storage.logs import CapitalEntry, get_capital_entry_log
from fundlog.storage.portfolios import (
    create_portfolio,
    create_portfolio_with_initial,
    delete_portfolio,
)
from fundlog.storage.summaries import (
    PortfolioSummary,
    get_all_portfolio_summaries,
    get_portfolio_summary,
)

__all__ = [
    "Asset",
    "CapitalEntry",
    "PortfolioSummary",
    "create_assets",
    "create_portfolio",
    "create_portfolio_with_initial",
    "delete_capital_entry",
    "delete_asset",
    "delete_portfolio",
    "edit_capital_entry",
    "get_all_portfolio_summaries",
    "get_assets",
    "get_capital_entry_log",
    "get_portfolio_summary",
    "initialize_database",
    "record_inflow",
    "record_outflow",
    "reset_portfolio_entries",
]
