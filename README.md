# FundLog

FundLog is a local-first CLI for manually recording capital movements across portfolios.

The CLI command is `fundlog`. The package/distribution name is `fundlog-cli`.

## What FundLog is

- A manual capital ledger.
- A portfolio tracker.
- A deterministic, record-based calculator.
- A local database-backed CLI.
- A foundation for future extensions.

FundLog calculates its results from recorded operations. It does not accept a manually entered portfolio value.

## Scope

FundLog is intentionally simple. It does not fetch market data, calculate live prices, connect to external services, or provide financial advice.

FundLog only works with the records you enter manually.

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
fundlog remove stocks 2

fundlog reset stocks --yes
```

v0.1 covers initialization, portfolio creation, optional initial capital, inflows, outflows, summaries, logs, capital-entry correction, soft removal, and portfolio reset.

## Planned capabilities

Later releases are planned to extend portfolio tracking, record management, calculations, reporting, backup, import and export, audit tooling, and release automation.

See [the roadmap](docs/ROADMAP.md) for the phased plan.

## Financial advice disclaimer

FundLog is a record-keeping and calculation tool. It does not provide financial, investment, tax, or legal advice. Users are responsible for verifying their records and decisions.
