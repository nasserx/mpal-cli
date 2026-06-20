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
fundlog portfolio summary stocks
fundlog portfolio summary --all
fundlog portfolio reset stocks --yes
fundlog portfolio delete stocks --yes

fundlog capital inflow stocks 1000
fundlog capital outflow stocks 250 --date 2026-06-19 --note "withdrawal"
fundlog capital log stocks
fundlog capital edit stocks 2 --amount 500
fundlog capital delete stocks 2

fundlog asset add stocks AAPL AMZN MSFT
fundlog asset summary stocks
fundlog asset summary stocks/AAPL
fundlog asset log stocks/AAPL
fundlog asset delete stocks/AAPL --yes
fundlog asset income stocks/AAPL 32 --date 2026-06-20 --note "Dividend"
fundlog asset buy stocks/AAPL --price 234.43 --quantity 3 --fee 2.30
fundlog asset sell stocks/AAPL --price 235.50 --quantity 1 --fee 1.25
```

The earlier root commands remain callable as hidden compatibility aliases so
existing scripts do not break abruptly. Official help and examples use the
grouped commands. `fundlog asset summary stocks`
shows all active asset summaries in the portfolio, while
`fundlog asset summary stocks/AAPL` shows one asset. The older
`fundlog asset list stocks` spelling remains callable as a hidden compatibility
alias for the portfolio-wide summary.

Entry numbers shown by `fundlog capital log` are stable, portfolio-local
numbers. Internal database IDs are not part of the CLI contract.

Explicit transaction dates must use `YYYY-MM-DD` and cannot be in the future. If
`--date` is omitted, FundLog uses the current local date.

v0.1 covers initialization, portfolio creation, optional initial capital,
inflows, outflows, summaries, logs, capital-entry correction and deletion,
portfolio reset, and soft deletion of portfolios. The initial asset foundation
adds manual symbol creation, listing, and soft deletion under existing
portfolios. The read-only asset log and its transaction storage foundation are
also present. Manual asset income updates the asset list and portfolio summary.
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
