# Multi-Portfolio Asset Ledger Product Specification

## Product identity

- Project name: Multi-Portfolio Asset Ledger (`mpal`)
- CLI command: `mpal`
- Package/distribution name: `mpal-cli`
- Repository/folder name: `mpal-cli`

mpal is a fully manual, local-first, terminal-based capital management and portfolio tracking tool. It stores manual portfolio records locally and derives calculations deterministically from those records. It does not use live prices or market APIs.

## Goals

- Provide a clear manual ledger for capital entering and leaving portfolios.
- Support multiple independent portfolios.
- Store all user data in a local database.
- Calculate portfolio summaries only from recorded operations.
- Establish maintainable concepts and audit-ready behavior for future extensions.
- Use decimal-safe financial logic for all implemented calculations.

## Non-goals

mpal is not intended to:

- Execute trades or integrate with brokers.
- Retrieve market data, live prices, or real-time prices.
- Connect to market APIs or automatically value portfolios.
- Provide financial advice.
- Support multi-currency accounting.
- Store currencies, company names, or asset types.
- Accept a manually entered portfolio value in v0.1.

## Core concepts

### Portfolio

A user-managed ledger boundary, such as `stocks`, `etfs`, `crypto`, or `gold`. A portfolio owns its capital entries. Multiple portfolios may exist independently.

### Capital deposit

A recorded amount added to a portfolio. A deposit increases both Capital and Cash.

### Capital withdrawal

A recorded amount withdrawn from a portfolio. A withdrawal decreases both
Capital and Cash and is rejected when the portfolio has insufficient Cash.

### Cash

The amount available inside a portfolio and not tied to open positions. Cash is
active external capital plus active asset cash effects: income and sell
proceeds increase it, while buy cash outflows decrease it.

### Positions

The book cost of currently open manual positions. Buys increase Positions and
sells reduce it by moving-average relieved Cost Basis. Positions is not market
value, live value, or unrealized value.

### Book Value

Cash plus Positions. Book Value is an accounting value derived only from manual
records and must not imply market value.

### Realized PnL

Profit or loss from closed or partially closed manual positions. It is sell net
proceeds minus moving-average relieved Cost Basis. Capital deposits and withdrawals
do not produce Realized PnL.

### Income

Cash income from manually recorded asset distributions or dividends.

### Return

Return is based on realized results only:
`(Realized PnL + Income) / Capital`. It displays `0.00%` when Capital is zero.

## Implemented scope

The completed capital ledger and current asset milestone include:

- Initializing local storage.
- Creating empty portfolios.
- Recording an initial deposit during portfolio creation.
- Recording deposits.
- Recording withdrawals.
- Showing one-portfolio or all-portfolio summaries.
- Showing a portfolio's capital entry log.
- Editing capital entries.
- Soft-deleting capital entries by stable portfolio-local entry number.
- Resetting a portfolio's operations while retaining the portfolio.
- Soft-deleting a portfolio and its active capital entries.
- Adding and soft-deleting portfolio-owned assets.
- Showing portfolio-wide and single-asset summaries.
- Showing active asset transaction logs.
- Recording manual asset income, buys, and sells.
- Applying moving-average Cost Basis and Realized PnL.
- Feeding active asset effects into portfolio Cash, Positions, Book Value,
  Realized PnL, Income, and Return.

Live pricing, market APIs, market valuation, and unrealized PnL are not part of
mpal.
