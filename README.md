# FundLog

FundLog is a fully manual, local-first CLI for recording capital movements across portfolios.

The CLI command is `fundlog`. The package/distribution name is `fundlog-cli`.

## Installation

FundLog requires Python 3.11 or later. From a project checkout:

```console
python -m pip install -e .
fundlog --help
```

## What FundLog is

- A manual capital ledger.
- A portfolio tracker.
- A deterministic, record-based calculator.
- A local database-backed CLI.
- A foundation for future extensions.

FundLog calculates its results only from manually recorded operations.

## Scope

FundLog is intentionally simple. It does not fetch market data, calculate live prices, connect to market APIs or other external services, or provide financial advice.

FundLog only works with the records you enter manually.

Portfolio summaries use book/accounting values. Book Value is derived from manual records and is not market value.

## Official command hierarchy

FundLog groups commands by the records they manage:

```console
fundlog init

fundlog portfolio create stocks
fundlog portfolio create stocks --initial 5000
fundlog portfolio list
fundlog portfolio show stocks
fundlog portfolio reset stocks --yes
fundlog portfolio delete stocks --yes

fundlog capital deposit 1000 -p stocks
fundlog capital withdraw 250 --portfolio stocks --date 2026-06-19 --note "withdrawal"
fundlog capital log -p stocks
fundlog capital edit 2 -p stocks --amount 500
fundlog capital delete 2 -p stocks

fundlog asset add AAPL AMZN MSFT -p stocks
fundlog asset summary -p stocks
fundlog asset summary AAPL -p stocks
fundlog asset log AAPL -p stocks
fundlog asset delete AAPL -p stocks --yes
fundlog asset income AAPL 32 -p stocks --date 2026-06-20 --note "Distribution"
fundlog asset buy AAPL -p stocks --price 234.43 --quantity 3 --fee 2.30
fundlog asset sell AAPL -p stocks --price 235.50 --quantity 1 --fee 1.25
```

Portfolio-scoped capital and asset operations require `--portfolio` or `-p`.
The previous root commands, `asset list`, and the old combined
portfolio/symbol argument form have been removed. No compatibility aliases are
kept in this CLI redesign.

Entry numbers shown by `fundlog capital log` are stable, portfolio-local
numbers. Internal database IDs are not part of the CLI contract.

Explicit transaction dates must use `YYYY-MM-DD` and cannot be in the future. If
`--date` is omitted, FundLog uses the current local date.

v0.1 covers initialization, portfolio creation, optional initial capital,
deposits, withdrawals, summaries, logs, capital-entry correction and deletion,
portfolio reset, and soft deletion of portfolios. The asset foundation adds
manual symbol creation, summaries, and soft deletion under existing
portfolios. The read-only asset log and its transaction storage foundation are
also present. Manual asset income updates asset and portfolio summaries.
Manual buys update open quantity, Cost Basis, portfolio Cash, and Positions.
Manual sells use moving-average book cost and update open quantity, Cost Basis,
Cash, Positions, and Realized PnL. Asset summary reports current open quantity,
Cost Basis, Average Cost, Realized PnL, Income, and Realized Return from active
manual transactions.

## Planned capabilities

Later releases are planned to extend portfolio tracking, record management, calculations, reporting, backup, import and export, audit tooling, and release automation.

See [the roadmap](docs/ROADMAP.md) for the phased plan.

## Financial advice disclaimer

FundLog is a record-keeping and calculation tool. It does not provide financial, investment, tax, or legal advice. Users are responsible for verifying their records and decisions.
