# mpal Contributor and Agent Guide

## Project identity

- Project: Multi-Portfolio Asset Ledger (`mpal`)
- Official CLI command: `mpal`
- Distribution: `mpal-cli`
- Python package: `mpal`
- Supported Python: 3.11+

mpal is a local-first, fully manual portfolio ledger. It derives results
only from user-entered records.

Before changing behavior, read `README.md`, `docs/PRODUCT_SPEC.md`,
`docs/CLI_SPEC.md`, `docs/ASSETS_SPEC.md`, `docs/FINANCIAL_MODEL.md`,
`docs/DATA_MODEL.md`, and `docs/ROADMAP.md`.

## Current CLI Contract

Root help exposes only:

- `mpal init`
- `mpal portfolio`
- `mpal capital`
- `mpal asset`

Implemented portfolio commands:

- `mpal portfolio create <portfolio> [--initial <amount>]`
- `mpal portfolio list`
- `mpal portfolio show <portfolio>`
- `mpal portfolio reset <portfolio> --yes`
- `mpal portfolio delete <portfolio> --yes`

Implemented capital commands:

- `mpal capital show -p <portfolio>`
- `mpal capital deposit <amount> -p <portfolio>`
- `mpal capital withdraw <amount> -p <portfolio>`
- `mpal capital log -p <portfolio>`
- `mpal capital entry edit <entry-number> -p <portfolio>`
- `mpal capital entry delete <entry-number> -p <portfolio>`

Implemented asset commands:

- `mpal asset add <symbol> [symbol...] -p <portfolio>`
- `mpal asset list`
- `mpal asset list -p <portfolio>`
- `mpal asset show <symbol> -p <portfolio>`
- `mpal asset log <symbol> -p <portfolio>`
- `mpal asset delete <symbol> -p <portfolio> --yes`
- `mpal asset entry edit <symbol> <entry-number> -p <portfolio> [options...]`
- `mpal asset entry delete <symbol> <entry-number> -p <portfolio> --yes`
- `mpal asset income <symbol> <amount> -p <portfolio>`
- `mpal asset buy <symbol> -p <portfolio> --price <price> --quantity <quantity>`
- `mpal asset sell <symbol> -p <portfolio> --price <price> --quantity <quantity>`

The long `--portfolio` option is equivalent to `-p`. There is no default
portfolio. `-p` remains required when an operation targets one specific
portfolio. Global views, such as `mpal asset list`, may omit `-p`.

This branch intentionally removes the earlier root commands and the old
combined `<portfolio>/<symbol>` argument. `asset summary`, `asset edit`,
`asset delete-entry`, `capital edit`, and `capital delete` are already removed
without hidden or compatibility aliases.

Command vocabulary rule:

- `list` shows a collection of current things.
- `show` shows current state/details of one thing.
- `log` shows historical entries or transactions.
- `entry edit` and `entry delete` edit or delete one historical log entry.
- `delete` deletes a whole entity.

`summary` may remain in output titles, such as `Portfolio Summary` or `Asset
Summary`, but is not a command name.

Use `mpal` in help, docs, tests, and examples. User shell shortcuts are not
part of the product interface.

## Product boundaries

Implemented asset behavior includes symbol management, income, exact buys,
exact sells, moving-average Cost Basis, Realized PnL, current-state output,
logs, portfolio integration, and individual transaction correction with replay.

Individual asset transaction correction uses asset-local entry numbers from
`mpal asset log`. Transaction edit keeps transaction type immutable.
Transaction deletion is soft-delete only. Both correction commands replay active
transactions in asset-local `entry_no` order before committing. Asset log
display may remain sorted by date then entry number. Do not expose internal
database IDs or introduce hard delete, restore, purge, market value, or
unrealized PnL.

Do not introduce:

- live or automatic prices
- market APIs or external market-data services
- market value
- unrealized PnL
- automatic trading or broker synchronization
- Python `float` in financial calculations

## Financial model

Money is stored as integer minor units. Use `parse_amount_minor()` for money
input and `format_money()` for display. User-facing money output uses
thousands separators and exactly two decimal places.

Price and quantity use exact `Decimal` helpers from
`src/mpal/numbers.py`. Do not use the money formatter for price or quantity.
Trade cash effects must be exact in minor units or require the statement
`--total`; never silently round.

User-facing quantity output must use the quantity formatter so integer
quantities and meaningful fractions do not show padded Decimal tails.
User-facing price output must use the price display helper when a fixed display
scale is needed. `Average Cost` is a price-like display value: calculate it
exactly, then display it with the active asset's inferred price scale instead
of exposing raw Decimal division output.

Current portfolio formulas:

- Capital = active deposits - active withdrawals
- Cash = Capital + active asset cash effects
- Positions = active asset position effects
- Book Value = Cash + Positions
- Realized PnL = active sell realized-PnL effects
- Income = active income effects
- Return = `(Realized PnL + Income) / Capital`, or `0.00%` for zero Capital

Sell cost relief uses moving-average book cost and deterministic half-even
minor-unit allocation. A full close relieves all remaining Cost Basis.

Portfolio summary columns remain exactly:

`Portfolio | Capital | Cash | Positions | Book Value | Realized PnL | Income | Return`

Do not add internal IDs, market value, unrealized PnL, or renamed generic value
columns.

## Data and deletion

mpal uses local SQLite storage in `mpal.db`.

Database path order:

1. `MPAL_DATA_DIR`
2. Windows `%LOCALAPPDATA%\mpal\mpal.db`
3. `~/.local/share/mpal/mpal.db`

Current tables:

- `portfolios`
- `capital_entries`
- `assets`
- `asset_transactions`

Capital entries have stable portfolio-local `entry_no` values. Asset
transactions have stable asset-local `entry_no` values. Internal row IDs are
not CLI identifiers.

Normal connections verify the initialized schema and apply existing
idempotent migrations. Do not add command-specific migration calls.

Deletion is soft:

- capital entry delete marks one active entry deleted
- portfolio reset marks active capital entries deleted and keeps the portfolio
- portfolio delete preserves the existing portfolio/capital soft-delete
  behavior
- asset delete atomically marks the asset and active transactions deleted
- asset entry edit atomically updates one active transaction after replaying
  active transaction effects
- asset entry delete atomically marks one active transaction deleted after
  replaying and updating remaining active transaction effects

Do not hard-delete records. Multi-record writes must remain atomic. Read models
and validation normally use active rows only.

## Shared validation and output

- Dates use `parse_transaction_date()`, strict `YYYY-MM-DD`, and cannot be in
  the future.
- Symbols use `normalize_symbol()` and are stored uppercase.
- Expected user errors are concise and omit tracebacks.
- Keep storage and accounting logic out of Rich rendering helpers.
- Do not pass raw `Decimal` values directly into Rich tables; format money,
  quantity, price, and average-cost values explicitly first.
- Reuse the centralized semantic palette in `src/mpal/output/theme.py`.
- Tables should use the shared row-oriented Rich table helper, with rounded
  borders, themed headers and borders, and no internal vertical column
  dividers.
- Positive PnL/returns show `+`, negative values show `-`, and zero is
  unsigned.

## Project structure

- `src/mpal/cli.py`: Typer command tree and CLI routing
- `src/mpal/amounts.py`: exact money parsing/formatting
- `src/mpal/assets.py`: symbol validation
- `src/mpal/numbers.py`: exact price/quantity parsing/formatting
- `src/mpal/dates.py`: transaction date validation
- `src/mpal/storage/`: database, portfolio, capital, asset, log, and summary
  operations
- `src/mpal/output/`: Rich rendering and theme
- `tests/`: CLI, persistence, accounting, precision, and output regressions
- `docs/`: product and technical specifications

Keep command handlers thin and reuse storage services. Preserve accounting,
schema, migration, precision, and soft-delete behavior unless a task
explicitly changes those contracts.

## Development workflow

```console
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
git diff --check
python -m build
```

Use isolated `MPAL_DATA_DIR` values in tests. Never run tests against the
user's real mpal database.
