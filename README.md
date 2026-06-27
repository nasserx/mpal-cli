# mpal

mpal — Multi-Portfolio Asset Ledger — is a minimal CLI tool for manual asset
tracking and capital management.

The CLI command is `mpal`. The package/distribution name is `mpal-cli`.

## Installation

mpal requires Python 3.11 or later.

For a future PyPI release:

```console
python -m pip install mpal-cli
mpal --help
```

From a project checkout:

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

mpal is intentionally simple. It does not fetch market data, calculate live
prices, calculate market value, calculate unrealized PnL, connect to market
APIs or other external services, or provide financial advice.

mpal only works with the records you enter manually.

Portfolio summaries use book/accounting values. Book Value is derived from manual records and is not market value.

## Quick Start

```console
mpal init
mpal summary
mpal portfolio create stocks
mpal capital deposit 1000 -p stocks
mpal capital show -p stocks
mpal asset add AAPL -p stocks
mpal asset buy AAPL -p stocks --price 234.43 --quantity 3 --fee 2.30
mpal asset list
mpal summary -p stocks -a AAPL
mpal asset log AAPL -p stocks
```

## Command Hierarchy

mpal groups commands by the records they manage:

```console
mpal init

mpal summary
mpal summary -p stocks
mpal summary -p stocks -a AAPL

mpal portfolio create stocks
mpal portfolio create stocks --initial 5000
mpal portfolio list
mpal portfolio reset stocks --yes
mpal portfolio delete stocks --yes

mpal capital show -p stocks
mpal capital deposit 1000 -p stocks
mpal capital withdraw 250 --portfolio stocks --date 2026-06-19 --note "withdrawal"
mpal capital log -p stocks
mpal capital entry edit 2 -p stocks --amount 500
mpal capital entry delete 2 -p stocks

mpal asset add AAPL AMZN MSFT -p stocks
mpal asset list
mpal asset list -p stocks
mpal asset log AAPL -p stocks
mpal asset delete AAPL -p stocks --yes
mpal asset entry edit AAPL 2 -p stocks --price 234.50 --quantity 3
mpal asset entry delete AAPL 2 -p stocks --yes
mpal asset income AAPL 32 -p stocks --date 2026-06-20 --note "Distribution"
mpal asset buy AAPL -p stocks --price 234.43 --quantity 3 --fee 2.30
mpal asset sell AAPL -p stocks --price 235.50 --quantity 1 --fee 1.25
```

`mpal summary` is the unified summary/reporting command. With no options it
shows a global dashboard summary across all active portfolios. `mpal summary
-p <portfolio>` summarizes one active portfolio. `mpal summary -p <portfolio>
-a <asset>` summarizes one active asset within one active portfolio; `-a`
requires `-p`. Summary views aggregate active portfolio capital, active asset
income, and active realized PnL without live prices, market value, or
unrealized PnL. Global return is computed from global totals, not by averaging
portfolio returns.

Portfolio-scoped capital and asset operations require `--portfolio` or `-p`.
Global collection views such as `mpal summary` and `mpal asset list` do not
require `-p`. No compatibility aliases are kept in this CLI redesign.

Asset list output uses an `Asset/Portfolio` column. Combined labels display
as `<SYMBOL> • <Portfolio>`, such as `AAPL • Stocks`; portfolio capitalization
there is display-only, and command syntax still uses `-p <portfolio>`.

Entry numbers shown by `mpal capital log` are stable, portfolio-local
numbers. Internal database IDs are not part of the CLI contract.
Capital entry correction is under `mpal capital entry edit/delete`; `mpal
capital log` remains the historical entry view, and `mpal capital show` is the
capital-only current-state view.

Explicit transaction dates must use `YYYY-MM-DD` and cannot be in the future. If
`--date` is omitted, mpal uses the current local date.

The current release covers initialization, portfolio creation, optional initial capital,
deposits, withdrawals, summaries, logs, capital-entry correction and deletion,
portfolio reset, and soft deletion of portfolios. The asset foundation adds
manual symbol creation, current-state views, and soft deletion under existing
portfolios. The read-only asset log and its transaction storage foundation are
also present. Manual asset income updates asset and portfolio summaries.
Manual buys update open quantity, Cost Basis, portfolio Cash, and Positions.
Manual sells use moving-average book cost and update open quantity, Cost Basis,
Cash, Positions, and Realized PnL. Individual asset transactions can be edited
or soft-deleted by asset-local entry number, with active transactions replayed
before commit. `asset list` is the current asset collection view, and
`summary -p <portfolio> -a <asset>` reports current open quantity, Cost Basis,
Average Cost, Realized PnL, Income, and Realized Return for one asset from
active manual transactions.
Asset transaction correction is under `mpal asset entry edit/delete`; `mpal
asset log` remains the historical transaction view.

`portfolio show` and `asset show` were removed before public release because
`summary` now owns all summary/reporting views.

## Planned capabilities

Later releases are planned to extend portfolio tracking, record management, calculations, reporting, backup, import and export, audit tooling, and release automation.

See [the roadmap](docs/ROADMAP.md) for the phased plan.

## Financial advice disclaimer

mpal is a record-keeping and calculation tool. It does not provide financial, investment, tax, or legal advice. Users are responsible for verifying their records and decisions.
