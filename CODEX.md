# FundLog Contributor and Agent Guide

## Project identity

- Project: FundLog
- Official CLI command: `fundlog`
- Distribution: `fundlog-cli`
- Python package: `fundlog`
- Supported Python: 3.11+

FundLog is a local-first, fully manual portfolio ledger. It derives results
only from user-entered records.

Before changing behavior, read `README.md`, `docs/PRODUCT_SPEC.md`,
`docs/CLI_SPEC.md`, `docs/ASSETS_SPEC.md`, `docs/FINANCIAL_MODEL.md`,
`docs/DATA_MODEL.md`, and `docs/ROADMAP.md`.

## Current CLI contract

Root help exposes only:

- `fundlog init`
- `fundlog portfolio`
- `fundlog capital`
- `fundlog asset`

Implemented portfolio commands:

- `fundlog portfolio create <portfolio> [--initial <amount>]`
- `fundlog portfolio list`
- `fundlog portfolio show <portfolio>`
- `fundlog portfolio reset <portfolio> --yes`
- `fundlog portfolio delete <portfolio> --yes`

Implemented capital commands:

- `fundlog capital deposit <amount> -p <portfolio>`
- `fundlog capital withdraw <amount> -p <portfolio>`
- `fundlog capital log -p <portfolio>`
- `fundlog capital edit <entry-number> -p <portfolio>`
- `fundlog capital delete <entry-number> -p <portfolio>`

Implemented asset commands:

- `fundlog asset add <symbol> [symbol...] -p <portfolio>`
- `fundlog asset summary -p <portfolio>`
- `fundlog asset summary <symbol> -p <portfolio>`
- `fundlog asset log <symbol> -p <portfolio>`
- `fundlog asset delete <symbol> -p <portfolio> --yes`
- `fundlog asset income <symbol> <amount> -p <portfolio>`
- `fundlog asset buy <symbol> -p <portfolio> --price <price> --quantity <quantity>`
- `fundlog asset sell <symbol> -p <portfolio> --price <price> --quantity <quantity>`

The long `--portfolio` option is equivalent to `-p` and is required for every
capital and asset operation. There is no default portfolio.

This branch intentionally removes the earlier root commands, `asset list`, and
the old combined `<portfolio>/<symbol>` argument. There are no hidden or
compatibility aliases. Do not reintroduce them without a new explicit product
decision.

Use `fundlog` in help, docs, tests, and examples. User shell shortcuts are not
part of the product interface.

## Product boundaries

Implemented asset behavior includes symbol management, income, exact buys,
exact sells, moving-average Cost Basis, Realized PnL, summaries, logs, and
portfolio integration.

Do not introduce:

- live or automatic prices
- market APIs or external market-data services
- market value
- unrealized PnL
- automatic trading or broker synchronization
- Python `float` in financial calculations

## Financial model

Money is stored as integer minor units. Use `parse_amount_minor()` for money
input and `format_money()` for display.

Price and quantity use exact `Decimal` helpers from
`src/fundlog/numbers.py`. Do not use the money formatter for price or quantity.
Trade cash effects must be exact in minor units or require the statement
`--total`; never silently round.

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

FundLog uses local SQLite storage in `fundlog.db`.

Database path order:

1. `FUNDLOG_DATA_DIR`
2. Windows `%LOCALAPPDATA%\FundLog\fundlog.db`
3. `~/.local/share/fundlog/fundlog.db`

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

- capital delete marks one active entry deleted
- portfolio reset marks active capital entries deleted and keeps the portfolio
- portfolio delete preserves the existing portfolio/capital soft-delete
  behavior
- asset delete atomically marks the asset and active transactions deleted

Do not hard-delete records. Multi-record writes must remain atomic. Read models
and validation normally use active rows only.

## Shared validation and output

- Dates use `parse_transaction_date()`, strict `YYYY-MM-DD`, and cannot be in
  the future.
- Symbols use `normalize_symbol()` and are stored uppercase.
- Expected user errors are concise and omit tracebacks.
- Keep storage and accounting logic out of Rich rendering helpers.
- Reuse the semantic palette in `src/fundlog/output/theme.py`.
- Positive PnL/returns show `+`, negative values show `-`, and zero is
  unsigned.

## Project structure

- `src/fundlog/cli.py`: Typer command tree and CLI routing
- `src/fundlog/amounts.py`: exact money parsing/formatting
- `src/fundlog/assets.py`: symbol validation
- `src/fundlog/numbers.py`: exact price/quantity parsing/formatting
- `src/fundlog/dates.py`: transaction date validation
- `src/fundlog/storage/`: database, portfolio, capital, asset, log, and summary
  operations
- `src/fundlog/output/`: Rich rendering and theme
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

Use isolated `FUNDLOG_DATA_DIR` values in tests. Never run tests against the
user's real FundLog database.
