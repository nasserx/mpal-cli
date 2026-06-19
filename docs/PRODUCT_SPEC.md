# FundLog Product Specification

## Product identity

- Project name: FundLog
- CLI command: `fundlog`
- Package/distribution name: `fundlog-cli`
- Repository/folder name: `fundlog`

FundLog is a local-first, terminal-based capital management and portfolio tracking tool. It stores manual portfolio records locally and derives calculations deterministically from those records.

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
- Retrieve market data or track prices.
- Automatically value portfolios.
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

The amount available in a portfolio after applying its active recorded operations. In v0.1, only inflows and outflows change Cash.

### Invested

The amount committed to investments. Invested is `0` in v0.1 because investment operations are not implemented.

### Value

The sum of Cash and Invested. Value is derived; users do not enter it directly.

### PnL

The result produced by future investment operations. Capital inflows and outflows do not produce PnL. PnL is `0` or shown as not available in v0.1.

### Return

PnL divided by total inflows. In v0.1, Return is `0` or shown as not available, consistently with the chosen PnL presentation and denominator availability.

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

v0.1 contains portfolios and capital entries only. Investment records, market valuation, and price-based calculations are outside v0.1.
