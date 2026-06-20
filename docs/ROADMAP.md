# FundLog Roadmap

The roadmap is intentionally phased. Items listed for later versions are outside the v0.1 implementation contract.

The next planned phase after the completed v0.1 portfolio and capital ledger is
the design and later implementation of assets, symbols, and manual trades. Its
current design is documented in `docs/ASSETS_SPEC.md`; it is not yet an
implementation contract.

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
