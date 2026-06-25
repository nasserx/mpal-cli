# mpal

mpal — Multi-Portfolio Asset Ledger — is a minimal CLI tool for manual asset
tracking and capital management.

The CLI command is `mpal`. The package/distribution name is `mpal-cli`.

## Installation

mpal requires Python 3.11 or later. From a project checkout:

```console
python -m pip install -e .
mpal --help
```

## What mpal is

- A manual capital ledger.
- A portfolio tracker.
- A deterministic, record-based calculator.
- A local database-backed CLI.
- A foundation for future extensions.

mpal calculates its results only from manually recorded operations.

## Scope

mpal is intentionally simple. It does not fetch market data, calculate live prices, connect to market APIs or other external services, or provide financial advice.

mpal only works with the records you enter manually.

Portfolio summaries use book/accounting values. Book Value is derived from manual records and is not market value.

## Official command hierarchy

mpal groups commands by the records they manage:

```console
mpal init

mpal portfolio create stocks
mpal portfolio create stocks --initial 5000
mpal portfolio list
mpal portfolio show stocks
mpal portfolio reset stocks --yes
mpal portfolio delete stocks --yes

mpal capital deposit 1000 -p stocks
mpal capital withdraw 250 --portfolio stocks --date 2026-06-19 --note "withdrawal"
mpal capital log -p stocks
mpal capital edit 2 -p stocks --amount 500
mpal capital delete 2 -p stocks

mpal asset add AAPL AMZN MSFT -p stocks
mpal asset summary -p stocks
mpal asset summary AAPL -p stocks
mpal asset log AAPL -p stocks
mpal asset delete AAPL -p stocks --yes
mpal asset delete-entry AAPL 2 -p stocks --yes
mpal asset income AAPL 32 -p stocks --date 2026-06-20 --note "Distribution"
mpal asset buy AAPL -p stocks --price 234.43 --quantity 3 --fee 2.30
mpal asset sell AAPL -p stocks --price 235.50 --quantity 1 --fee 1.25
```

Portfolio-scoped capital and asset operations require `--portfolio` or `-p`.
The previous root commands, `asset list`, and the old combined
portfolio/symbol argument form have been removed. No compatibility aliases are
kept in this CLI redesign.

Entry numbers shown by `mpal capital log` are stable, portfolio-local
numbers. Internal database IDs are not part of the CLI contract.

Explicit transaction dates must use `YYYY-MM-DD` and cannot be in the future. If
`--date` is omitted, mpal uses the current local date.

v0.1 covers initialization, portfolio creation, optional initial capital,
deposits, withdrawals, summaries, logs, capital-entry correction and deletion,
portfolio reset, and soft deletion of portfolios. The asset foundation adds
manual symbol creation, summaries, and soft deletion under existing
portfolios. The read-only asset log and its transaction storage foundation are
also present. Manual asset income updates asset and portfolio summaries.
Manual buys update open quantity, Cost Basis, portfolio Cash, and Positions.
Manual sells use moving-average book cost and update open quantity, Cost Basis,
Cash, Positions, and Realized PnL. Individual asset transactions can be
soft-deleted by asset-local entry number, with remaining active transactions
replayed before commit. Asset summary reports current open quantity, Cost
Basis, Average Cost, Realized PnL, Income, and Realized Return from active
manual transactions.

## Planned capabilities

Later releases are planned to extend portfolio tracking, record management, calculations, reporting, backup, import and export, audit tooling, and release automation.

See [the roadmap](docs/ROADMAP.md) for the phased plan.

## Financial advice disclaimer

mpal is a record-keeping and calculation tool. It does not provide financial, investment, tax, or legal advice. Users are responsible for verifying their records and decisions.
