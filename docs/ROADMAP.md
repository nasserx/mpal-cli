# FundLog Roadmap

The roadmap is intentionally phased. Items listed for later versions are outside the v0.1 implementation contract.

Work after the completed v0.1 portfolio and capital ledger is proceeding
incrementally through assets, symbols, and manual trades. Asset management,
income, buys, sells, moving-average Cost Basis, and Realized PnL are now
implemented, including asset summary output. The governing contract is
documented in `docs/ASSETS_SPEC.md`.

The final command hierarchy is designed in `docs/CLI_SPEC.md`. Its
implementation is a separate compatibility migration; the currently
implemented root commands remain unchanged until that work is explicitly
authorized.

## v0.1 — Capital ledger foundation

- Portfolios only.
- Capital entries only.
- `init`.
- Create a portfolio.
- Create a portfolio with initial capital.
- Record inflows.
- Record outflows with Cash validation.
- Show a portfolio summary.
- Show all portfolio summaries.
- Show a portfolio capital-entry log.
- Edit portfolio capital entries.
- Soft-delete portfolio capital entries.
- Reset a portfolio.
- Soft-delete a portfolio and its active entries.
- Use a local database.
- Maintain an audit-ready design.

## v0.2 — Record management

- Add symbol tracking through portfolio-owned assets.
- Add symbols to an existing portfolio.
- Soft-delete assets and their active transactions under audit-ready rules.
- Add asset-level lists, summaries, and logs.

## v0.3 — Investment operations

- Record manual buys.
- Record manual sells.
- Account for trade-associated fees within manual trade calculations.
- Record manual distributions or dividends.
- Calculate open-position book cost.
- Calculate realized PnL.
- Feed manual results into Cash, Positions, Book Value, Realized PnL, and Income.
- Use moving average cost as the initial cost basis method.
- Reject inexact minor-unit trade cash effects unless an explicit exact cash
  total is supplied.

FundLog will remain fully manual. Live prices, market APIs, market value, and unrealized PnL are not planned.

## v0.4 — Reporting and delivery

- Add richer reports.
- Add CSV import and export.
- Add stronger audit tools.
- Expand test coverage.
- Add packaging and release automation.

## Command hierarchy migration

- Add official `portfolio`, `capital`, and organized `asset` command groups.
- Portfolio-wide `asset summary <portfolio>` is implemented.
- Keep existing root commands as hidden compatibility aliases.
- `asset list` remains as a hidden alias for portfolio-wide asset summary.
- Show only official commands in help after implementation.
- Review alias retention or removal before stable v1.
