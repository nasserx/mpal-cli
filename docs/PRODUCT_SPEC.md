# FundLog Product Specification

## Product identity

- Project name: FundLog
- CLI command: `fundlog`
- Package/distribution name: `fundlog-cli`
- Repository/folder name: `fundlog`

FundLog is a fully manual, local-first, terminal-based capital management and portfolio tracking tool. It stores manual portfolio records locally and derives calculations deterministically from those records. It does not use live prices or market APIs.

## Goals

- Provide a clear manual ledger for capital entering and leaving portfolios.
- Support multiple independent portfolios.
- Store all user data in a local database.
- Calculate portfolio summaries only from recorded operations.
- Establish maintainable concepts and audit-ready behavior for future extensions.
- Require decimal-safe financial logic when implementation begins.

## Non-goals

FundLog is not intended to:

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

### Capital inflow

A recorded amount added to a portfolio. An inflow increases both Capital and Cash.

### Capital outflow

A recorded amount withdrawn from a portfolio. An outflow decreases both Capital and Cash and is rejected when the portfolio has insufficient Cash.

### Cash

The amount available inside a portfolio and not tied to open positions. In v0.1, Cash equals active inflows minus active outflows. Future manual trading operations may feed calculated buy costs, sell proceeds, and income into Cash.

### Positions

The book cost of currently open positions. Positions is not market value, live value, or unrealized value. It is `0.00` in v0.1 because symbols and manual trading operations are not implemented.

### Book Value

Cash plus Positions. Book Value is an accounting value derived only from manual records and must not imply market value. In v0.1, Book Value equals Cash.

### Realized PnL

Profit or loss realized by future closed or partially closed manual positions. Capital inflows and outflows do not produce Realized PnL. It is `0.00` in v0.1.

### Income

Cash income from future manually recorded distributions or dividends. Income is `0.00` in v0.1.

### Return

Return is based on realized results only. The future formula is `(Realized PnL + Income) / Capital`. It is `0.00%` in v0.1, including when Capital is zero.

## v0.1 scope

v0.1 is limited to:

- Initializing local storage.
- Creating empty portfolios.
- Recording an initial inflow during portfolio creation.
- Recording inflows.
- Recording outflows.
- Showing one-portfolio or all-portfolio summaries.
- Showing a portfolio's capital entry log.
- Editing capital entries.
- Soft-removing capital entries.
- Resetting a portfolio's operations while retaining the portfolio.

v0.1 contains portfolios and capital entries only. Future manual trading operations may feed calculated results into Cash, Positions, Realized PnL, and Income. Live pricing, market APIs, market valuation, unrealized PnL, and price-based calculations are not part of FundLog.
