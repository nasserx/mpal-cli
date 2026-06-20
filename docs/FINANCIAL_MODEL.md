# FundLog v0.1 Financial Model

## Principles

FundLog is fully manual. It derives financial results only from active recorded operations and does not use live prices, market APIs, automatic valuation, market value, or unrealized PnL.

v0.1 records only portfolio capital inflows and outflows. Financial amounts use integer minor units in storage and decimal-safe logic in application code; binary floating point is not used.

## Summary table

The summary output has exactly these columns:

| Portfolio | Capital | Cash | Positions | Book Value | Realized PnL | Income | Return |
|---|---:|---:|---:|---:|---:|---:|---:|

The internal portfolio database ID is not part of summary output.

### Capital

External capital only.

In v0.1:

`Capital = total active inflows - total active outflows`

### Cash

Available cash inside the portfolio that is not tied to open positions.

In v0.1:

`Cash = total active inflows - total active outflows`

Future manual trading operations may feed calculated buy costs, sell proceeds, and income or distributions into Cash. Those operations are not implemented in v0.1.

### Positions

The book cost of currently open positions. Positions is not market value, live value, or unrealized value.

In v0.1, no symbols or manual trading positions exist:

`Positions = 0.00`

### Book Value

`Book Value = Cash + Positions`

Book Value is a book/accounting value based only on manual records. It must not imply market value.

In v0.1:

`Book Value = Cash`

### Realized PnL

Profit or loss realized from future closed or partially closed manual trading positions.

In v0.1:

`Realized PnL = 0.00`

### Income

Cash income from future manually recorded distributions or dividends.

In v0.1:

`Income = 0.00`

### Return

Return is based on realized results only, not unrealized market movement.

The future formula is:

`Return = (Realized PnL + Income) / Capital`

In v0.1, Return is always `0.00%`. If Capital is zero, Return is also displayed as `0.00%`.

## Capital entry rules

- An inflow increases Capital and Cash by the same amount.
- An outflow decreases Capital and Cash by the same amount.
- An outflow is rejected if Cash is insufficient.
- An outflow does not affect Realized PnL or Income.
- Active entries alone contribute to current calculations.
- Soft-deleted entries do not contribute.
- Portfolio reset soft-deletes portfolio entries.
- Entry deletions, portfolio deletions, and resets retain rows and timestamps.
  Edits update the existing row timestamp; full before-and-after audit history is
  future work.
- FundLog must not invent market value or use price-based valuation.
- Fees are not a portfolio-level summary field. If supported later, they belong within manual symbol trading calculations.

## Example scenarios

### Empty portfolio

| Portfolio | Capital | Cash | Positions | Book Value | Realized PnL | Income | Return |
|---|---:|---:|---:|---:|---:|---:|---:|
| stocks | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% |

### Add an inflow

```console
fundlog inflow stocks 1000
```

Capital, Cash, and Book Value become `1000.00`. Positions, Realized PnL, and Income remain `0.00`; Return remains `0.00%`.

### Add an outflow

```console
fundlog outflow stocks 250
```

After the preceding inflow, Capital, Cash, and Book Value become `750.00`. The other v0.1 summary values remain zero.

### Attempt an outflow with insufficient Cash

```console
fundlog outflow stocks 1000
```

With only `750.00` Cash available, the command fails, creates no entry, and leaves the summary unchanged.
