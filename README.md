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

## v0.1 examples

```console
fundlog init

fundlog create stocks
fundlog create stocks --initial 5000

fundlog inflow stocks 1000
fundlog outflow stocks 250 --date 2026-06-19 --note "withdrawal"

fundlog summary stocks
fundlog summary --all
fundlog log stocks

fundlog edit stocks 2 --amount 500
fundlog delete stocks 2

fundlog reset stocks --yes
fundlog delete stocks --yes

fundlog asset add stocks AAPL AMZN MSFT
fundlog asset list stocks
fundlog asset log stocks/AAPL
fundlog asset delete stocks/AAPL --yes
```

Entry numbers shown by `fundlog log` are stable, portfolio-local numbers. Internal database IDs are not part of the CLI contract.

Explicit transaction dates must use `YYYY-MM-DD` and cannot be in the future. If
`--date` is omitted, FundLog uses the current local date.

v0.1 covers initialization, portfolio creation, optional initial capital,
inflows, outflows, summaries, logs, capital-entry correction and deletion,
portfolio reset, and soft deletion of portfolios. The initial asset foundation
adds manual symbol creation, listing, and soft deletion under existing
portfolios. The read-only asset log and its transaction storage foundation are
also present, but no command records trades or income. Trading and asset
accounting are not implemented.

## Planned capabilities

Later releases are planned to extend portfolio tracking, record management, calculations, reporting, backup, import and export, audit tooling, and release automation.

See [the roadmap](docs/ROADMAP.md) for the phased plan.

## Financial advice disclaimer

FundLog is a record-keeping and calculation tool. It does not provide financial, investment, tax, or legal advice. Users are responsible for verifying their records and decisions.
