# FundLog Contributor and Agent Guide

## Project overview

- Project: FundLog
- CLI command: `fundlog`
- Distribution/package name: `fundlog-cli`
- Python import package: `fundlog`
- Supported Python: 3.11+

FundLog is a local, fully manual terminal application for tracking portfolio capital. It calculates results only from records entered by the user.

Before changing behavior, read:

- `README.md`
- `docs/PRODUCT_SPEC.md`
- `docs/CLI_SPEC.md`
- `docs/FINANCIAL_MODEL.md`
- `docs/DATA_MODEL.md`
- `docs/ROADMAP.md`

## Product scope

v0.1 covers portfolio and capital-entry management only.

The asset foundation implements `fundlog asset add`, `fundlog asset list`,
`fundlog asset log <portfolio>/<symbol>`,
`fundlog asset delete <portfolio>/<symbol> --yes`, asset-reference parsing,
symbol normalization, and the `assets` and `asset_transactions` tables.
`fundlog income` creates income transactions and feeds active income into asset
lists and portfolio Cash, Book Value, Income, and Return. `fundlog buy` records
exact manual buys and feeds quantity, Cost Basis, Cash, and Positions.
`fundlog sell` records exact manual sells, applies moving-average cost-basis
relief, and feeds quantity, Cost Basis, Cash, Positions, and Realized PnL.
`fundlog asset summary` reports active asset accounting totals, including
price-formatted Average Cost and asset-level Realized Return.

Do not introduce the following into v0.1:

- Symbols.
- Trades or positions created from trades.
- Portfolio-level fees.
- Income or distribution commands.
- Currencies.
- Live prices or automatic prices.
- Market APIs or other market-data integrations.
- Market value.
- Unrealized PnL.

FundLog is manual-only now and in its intended future. Future features may support manually recorded symbols and trading operations, but they must not introduce live pricing or automatic market valuation.

Future asset work must reuse the shared CLI theme, `parse_transaction_date()`,
and `format_money()`. Future quantity input/display must use
`parse_quantity()`/`format_quantity()`, and unit-price input/display must use
`parse_price()`/`format_price()` from `src/fundlog/numbers.py`. These helpers
are precision-aware and must not be replaced with the money formatter. Future
trade calculations must not silently round cash effects that are not exactly
representable in integer minor units. Quantity and price use exact `Decimal`
representations, never Python `float`. `/` is reserved for future
`<portfolio>/<symbol>` references and is not escaped. Live prices, market APIs,
market value, and unrealized PnL remain prohibited.

## Implemented commands

- `fundlog init`
- `fundlog create <portfolio>`
- `fundlog create <portfolio> --initial <amount>`
- `fundlog inflow <portfolio> <amount>`
- `fundlog outflow <portfolio> <amount>`
- `fundlog summary <portfolio>`
- `fundlog summary --all`
- `fundlog log <portfolio>`
- `fundlog edit <portfolio> <entry-number>`
- `fundlog delete <portfolio> <entry-number>`
- `fundlog reset <portfolio> --yes`
- `fundlog delete <portfolio> --yes`
- `fundlog asset add <portfolio> <symbol> [symbol...]`
- `fundlog asset list <portfolio>`
- `fundlog asset summary <portfolio>/<symbol>`
- `fundlog asset log <portfolio>/<symbol>`
- `fundlog asset delete <portfolio>/<symbol> --yes`
- `fundlog income <portfolio>/<symbol> <amount>`
- `fundlog buy <portfolio>/<symbol> --price <price> --quantity <quantity>`
- `fundlog sell <portfolio>/<symbol> --price <price> --quantity <quantity>`

Preserve existing command arguments, options, validation, output, and exit behavior unless a task explicitly changes the CLI contract.

## Official command hierarchy design

The final organized hierarchy is documented in `docs/CLI_SPEC.md` and is not
implemented yet:

- Root: `fundlog init`
- Portfolio: `portfolio create`, `portfolio summary`, `portfolio reset`,
  `portfolio delete`
- Capital: `capital inflow`, `capital outflow`, `capital log`, `capital edit`,
  `capital delete`
- Asset: `asset add`, `asset summary`, `asset log`, `asset delete`,
  `asset income`, `asset buy`, `asset sell`

`asset summary <portfolio>` is planned to show every active asset summary in a
portfolio. `asset summary <portfolio>/<symbol>` continues to show one asset.

When implementation is explicitly authorized:

- Official grouped commands should be visible in help and documentation.
- Existing root commands should remain temporarily as hidden compatibility
  aliases and delegate to the same handlers/services.
- Do not duplicate accounting or persistence logic for aliases.
- `asset list <portfolio>` may become a hidden alias for
  `asset summary <portfolio>`; make that choice explicitly during
  implementation.
- Do not remove compatibility aliases before a separate pre-v1 decision.

Until that migration is implemented, preserve the current executable command
structure and do not update runtime help to advertise unavailable commands.

## Financial model

Never use Python `float` for money.

- Monetary amounts are stored as integer minor units.
- Use `parse_amount_minor()` for monetary input and `format_money()` for
  monetary display from `src/fundlog/amounts.py`.
- Do not duplicate monetary parsing or formatting logic in command handlers.
- `format_money()` accepts integer minor units and displays thousands separators
  with exactly two decimal places.
- Do not use `format_money()` for quantities or unit prices. Future quantity and
  price features require separate precision-aware formatting helpers.

Base portfolio calculations plus implemented income, buys, and sells:

- Capital = active inflows - active outflows.
- Cash = active inflows - active outflows + active income - buy cash outflows
  + sell net proceeds.
- Positions = active buy and sell position effects.
- Book Value = Cash + Positions.
- Realized PnL = active sell realized-PnL effects.
- Income = active asset income.
- Return = `(Realized PnL + Income) / Capital`, or `0.00%` when Capital is zero.

Sell cost-basis relief uses moving-average book cost and deterministic
round-half-even allocation to integer minor units. A full close relieves all
remaining Cost Basis. This is book accounting and must not introduce live
market prices.

## Portfolio summary contract

The summary columns must remain exactly:

`Portfolio | Capital | Cash | Positions | Book Value | Realized PnL | Income | Return`

Do not reintroduce:

- Internal `id` in portfolio summary output.
- `Invested`.
- Generic `Value`.
- Generic `PnL`.
- `Market Value`.
- `Unrealized PnL`.

Book Value is a manual book/accounting value. It is not market value.

## Data and deletion rules

FundLog uses a local SQLite database named `fundlog.db`.

Database path resolution:

1. `FUNDLOG_DATA_DIR` when set. Tests use this override.
2. Windows: `%LOCALAPPDATA%\FundLog\fundlog.db`.
3. Fallback: `~/.local/share/fundlog/fundlog.db`.

Current tables are `portfolios`, `capital_entries`, `assets`, and
`asset_transactions`.

Capital entries have a stable, portfolio-local `entry_no` used by `log`, `edit`, and entry `delete`. Numbering starts at 1 for each portfolio row and never reuses numbers after soft delete or reset. Internal database IDs are not part of the CLI contract.

Asset transactions have stable, asset-local `entry_no` values. Numbering starts
at 1 for each asset row and never reuses numbers after soft delete. The current
asset log is read-only, and internal transaction IDs are not part of the CLI
contract.

Every normal storage connection verifies the initialized schema and applies pending idempotent migrations before querying or writing data. `fundlog init` also applies migrations. Do not add command-specific migration calls.

Soft delete is the default deletion model:

- `delete <portfolio> <entry-number>` soft-deletes one capital entry.
- `reset` soft-deletes all active entries for one portfolio while preserving the portfolio.
- `delete <portfolio> --yes` soft-deletes a portfolio and its active entries.
- `asset delete <portfolio>/<symbol> --yes` soft-deletes one active asset row.

Do not hard-delete rows unless a future task explicitly designs and authorizes a hard-delete feature. Multi-record changes must be atomic. Queries and calculations normally operate on active rows only.

Portfolio names are unique among active portfolios. A name may be reused after its previous portfolio is soft-deleted.

## Project structure

- `src/fundlog/cli.py`: Typer command definitions and CLI-level validation/output flow.
- `src/fundlog/amounts.py`: Exact monetary parsing and formatting.
- `src/fundlog/assets.py`: Asset symbol normalization and validation.
- `src/fundlog/numbers.py`: Exact quantity and unit-price parsing and formatting.
- `src/fundlog/dates.py`: Strict transaction-date parsing and future-date validation.
- `src/fundlog/config.py`: Application metadata and local database path resolution.
- `src/fundlog/errors.py`: Expected application exception types.
- `src/fundlog/storage/`: SQLite initialization and portfolio, entry, log, and summary persistence operations.
- `src/fundlog/storage/assets.py`: Asset creation and active-asset listing.
- `src/fundlog/storage/asset_logs.py`: Read-only active asset transaction logs.
- `src/fundlog/storage/asset_transactions.py`: Manual income, buy, and sell persistence.
- `src/fundlog/output/`: Rich console, semantic theme, and table rendering.
- `tests/test_cli.py`: CLI integration and behavior tests using Typer's test runner.
- `tests/test_amounts.py`: Focused exact money display-formatting tests.
- `tests/test_dates.py`: Focused shared transaction-date validation tests.
- `tests/test_assets.py`: Focused asset symbol validation tests.
- `tests/test_asset_cli.py`: Asset foundation CLI and persistence tests.
- `tests/test_asset_log.py`: Asset transaction migration and read-only log tests.
- `tests/test_income.py`: Income command, aggregation, and deletion tests.
- `tests/test_buy.py`: Buy exact-total, aggregation, and deletion tests.
- `tests/test_sell.py`: Sell exact-total, cost allocation, aggregation, and deletion tests.
- `tests/test_numbers.py`: Focused quantity and unit-price helper tests.
- `docs/`: Product, CLI, financial, data-model, and roadmap specifications.
- `pyproject.toml`: Packaging, dependencies, pytest, and Ruff configuration.

Keep persistence and business validation out of Rich output helpers. Keep command handlers thin and use the existing storage and amount helpers.

All user-provided transaction dates must use `parse_transaction_date()` from
`src/fundlog/dates.py`. Dates must be strict ISO `YYYY-MM-DD` values and cannot
be later than the current local date. Future symbols, trades, buys, sells, and
income features must reuse this helper instead of implementing local date
validation.

## CLI theme

Use the shared semantic palette in `src/fundlog/output/theme.py` for all Rich
output. Future assets, symbols, trades, positions, and reports must reuse this
theme instead of defining local colors.

- Use `TABLE_HEADER` for table headers.
- Use `TABLE_BORDER` for table borders.
- Use `TABLE_CELL` for every normal table body cell, including names, numbers,
  dates, types, amounts, notes, and summary values.
- Use `MUTED` only for secondary text outside normal table cells.
- Reserve `SUCCESS`, `ERROR`, and `WARNING` for status messages.
- Use `INFO` for informational messages where appropriate.
- Use `PROFIT` and `LOSS` only for values with clear profit, loss, or return
  semantics. Never use them for normal inflow or outflow rows.
- Use `INCOME` for income/distribution values, including income totals in asset
  logs. Buy and sell totals remain normal table cells.
- Realized PnL and return output uses explicit signs for nonzero values:
  positive values include `+`, negative values include `-`, and zero remains
  unsigned.
- Keep colors subtle and preserve readable text labels; color must not carry
  meaning by itself.
- Do not assign a different color to every table column or financial field.

## Development workflow

Install the project with development dependencies:

```console
python -m pip install -e ".[dev]"
```

Run tests:

```console
python -m pytest
```

Run Ruff lint:

```console
python -m ruff check .
```

Check formatting:

```console
python -m ruff format --check .
```

Apply formatting:

```console
python -m ruff format .
```

Before handing off a change, run tests, lint, formatting checks, and `git diff --check`.

## Coding guidelines

- Keep changes small and focused.
- Inspect the documentation before changing behavior.
- Preserve CLI behavior unless the task explicitly changes it.
- Add or update tests for every behavior change.
- Keep output and ordering deterministic.
- Prefer boring, explicit code over abstraction without a current need.
- Use transactions for atomic multi-record writes.
- Preserve soft-delete filtering and active-portfolio checks.
- Do not expand scope opportunistically.
- Do not add dependencies without a clear requirement.

## Testing guidance

- Use isolated temporary data directories through `FUNDLOG_DATA_DIR`.
- Never run tests against the user's real local FundLog database.
- Preserve existing tests.
- Add focused tests close to the changed behavior.
- Test failure paths and verify failed atomic operations leave data unchanged.
- Verify soft-deleted records are excluded where required while their rows remain stored.
- Avoid tests that depend on nondeterministic ordering or real external services.
