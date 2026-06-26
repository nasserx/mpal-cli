"""Local persistence primitives."""

from mpal.storage.asset_logs import AssetTransaction, get_asset_transaction_log
from mpal.storage.asset_transactions import (
    calculate_buy_total_minor,
    calculate_sell_total_minor,
    delete_asset_transaction_entry,
    edit_asset_transaction_entry,
    record_buy,
    record_income,
    record_sell,
)
from mpal.storage.assets import (
    Asset,
    create_assets,
    delete_asset,
    get_all_assets,
    get_asset_summary,
    get_assets,
)
from mpal.storage.database import initialize_database
from mpal.storage.entries import (
    delete_capital_entry,
    edit_capital_entry,
    record_inflow,
    record_outflow,
    reset_portfolio_entries,
)
from mpal.storage.logs import (
    CapitalEntry,
    CapitalState,
    get_capital_entry_log,
    get_capital_state,
)
from mpal.storage.portfolios import (
    create_portfolio,
    create_portfolio_with_initial,
    delete_portfolio,
)
from mpal.storage.summaries import (
    PortfolioSummary,
    get_all_portfolio_summaries,
    get_portfolio_summary,
)

__all__ = [
    "Asset",
    "AssetTransaction",
    "CapitalEntry",
    "CapitalState",
    "PortfolioSummary",
    "create_assets",
    "create_portfolio",
    "create_portfolio_with_initial",
    "calculate_buy_total_minor",
    "calculate_sell_total_minor",
    "delete_capital_entry",
    "delete_asset",
    "delete_asset_transaction_entry",
    "delete_portfolio",
    "edit_asset_transaction_entry",
    "edit_capital_entry",
    "get_all_portfolio_summaries",
    "get_all_assets",
    "get_assets",
    "get_asset_summary",
    "get_asset_transaction_log",
    "get_capital_entry_log",
    "get_capital_state",
    "get_portfolio_summary",
    "initialize_database",
    "record_inflow",
    "record_buy",
    "record_income",
    "record_sell",
    "record_outflow",
    "reset_portfolio_entries",
]
