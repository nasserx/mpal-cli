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

Preserve existing command arguments, options, validation, output, and exit behavior unless a task explicitly changes the CLI contract.

## Financial model

Never use Python `float` for money.

- Monetary amounts are stored as integer minor units.
- Use `parse_amount_minor()` and `format_amount_minor()` from `src/fundlog/amounts.py`.
- Do not duplicate monetary parsing or formatting logic in command handlers.

v0.1 calculations:

- Capital = active inflows - active outflows.
- Cash = active inflows - active outflows.
- Positions = `0.00`.
- Book Value = Cash + Positions.
- Realized PnL = `0.00`.
- Income = `0.00`.
- Return = `0.00%`.

Future manual trading features may feed calculated results into Cash, Positions, Realized PnL, and Income. They must not introduce live market prices.

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

Current tables are `portfolios` and `capital_entries`.

Capital entries have a stable, portfolio-local `entry_no` used by `log`, `edit`, and entry `delete`. Numbering starts at 1 for each portfolio row and never reuses numbers after soft delete or reset. Internal database IDs are not part of the CLI contract.

Every normal storage connection verifies the initialized schema and applies pending idempotent migrations before querying or writing data. `fundlog init` also applies migrations. Do not add command-specific migration calls.

Soft delete is the default deletion model:

- `delete <portfolio> <entry-number>` soft-deletes one capital entry.
- `reset` soft-deletes all active entries for one portfolio while preserving the portfolio.
- `delete <portfolio> --yes` soft-deletes a portfolio and its active entries.

Do not hard-delete rows unless a future task explicitly designs and authorizes a hard-delete feature. Multi-record changes must be atomic. Queries and calculations normally operate on active rows only.

Portfolio names are unique among active portfolios. A name may be reused after its previous portfolio is soft-deleted.

## Project structure

- `src/fundlog/cli.py`: Typer command definitions and CLI-level validation/output flow.
- `src/fundlog/amounts.py`: Exact monetary parsing and formatting.
- `src/fundlog/config.py`: Application metadata and local database path resolution.
- `src/fundlog/errors.py`: Expected application exception types.
- `src/fundlog/storage/`: SQLite initialization and portfolio, entry, log, and summary persistence operations.
- `src/fundlog/output/`: Rich console and table rendering.
- `tests/test_cli.py`: CLI integration and behavior tests using Typer's test runner.
- `docs/`: Product, CLI, financial, data-model, and roadmap specifications.
- `pyproject.toml`: Packaging, dependencies, pytest, and Ruff configuration.

Keep persistence and business validation out of Rich output helpers. Keep command handlers thin and use the existing storage and amount helpers.

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
