# FundLog Roadmap

The roadmap is intentionally phased. Items listed for later versions are outside the v0.1 implementation contract.

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

- Add symbol tracking.
- Add symbols to an existing portfolio.
- Remove symbols.
- Rename symbols.
- Add symbol-level summaries.

## v0.3 — Investment operations

- Record manual buys.
- Record manual sells.
- Account for trade-associated fees within manual trade calculations.
- Record manual distributions or dividends.
- Calculate open-position book cost.
- Calculate realized PnL.
- Feed manual results into Cash, Positions, Book Value, Realized PnL, and Income.

FundLog will remain fully manual. Live prices, market APIs, market value, and unrealized PnL are not planned.

## v0.4 — Reporting and delivery

- Add richer reports.
- Add CSV import and export.
- Add stronger audit tools.
- Expand test coverage.
- Add packaging and release automation.
