# FundLog v0.1 Financial Model

## Principles

FundLog is fully manual. It derives financial results only from active recorded operations and does not use live prices, market APIs, automatic valuation, market value, or unrealized PnL.

v0.1 records only portfolio capital inflows and outflows. Financial amounts use integer minor units in storage and decimal-safe logic in application code; binary floating point is not used.

Displayed monetary values use thousands separators and exactly two decimal
places. This display rule is specific to money and does not define formatting
for future quantities or unit prices.

Future manual asset calculations must use exact decimal arithmetic for price
and quantity and integer minor units for every cash effect. Price and quantity
accept plain decimal notation with at most 18 integer digits and 18 fractional
digits; scientific notation and Python `float` are prohibited. A calculated
trade cash effect must be exactly representable in minor units or the trade must
use the planned exact-money `--total` override described in
`docs/ASSETS_SPEC.md`.

The reusable `parse_quantity()`, `format_quantity()`, `parse_price()`, and
`format_price()` helpers implement the exact input and display contract.
Quantity and price formatting remain separate from `format_money()` and do not
force two decimal places.

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

Implemented manual asset income increases Cash. Implemented buys decrease Cash
by exact total cash outflow. Future sells may add net proceeds.

### Positions

The book cost of currently open positions. Positions is not market value, live value, or unrealized value.

Implemented buys increase Positions by total buy cash outflow, including buy
fees. No sell currently reduces Positions.

### Book Value

`Book Value = Cash + Positions`

Book Value is a book/accounting value based only on manual records. It must not imply market value.

With buys implemented, Book Value remains `Cash + Positions`. A buy transfers
book value from Cash to Positions and does not create profit or loss.

### Realized PnL

Profit or loss realized from future closed or partially closed manual trading positions.

In v0.1:

`Realized PnL = 0.00`

### Income

Cash income from manually recorded asset distributions or dividends.

Implemented income transactions increase both Cash and Income. Soft-deleted
transactions and transactions belonging to soft-deleted assets do not
contribute.

### Return

Return is based on realized results only, not unrealized market movement.

The formula is:

`Return = (Realized PnL + Income) / Capital`

With income implemented and Realized PnL still zero, Return reflects active
Income divided by Capital. If Capital is zero, Return displays `0.00%`.

Future asset-level Realized Return uses:

`Asset Realized Return = (Asset Realized PnL + Asset Income) / Total Buy Cost`

Total Buy Cost is cumulative buy cash outflow including buy fees. If Total Buy
Cost is zero, asset Realized Return is `0.00%`.

Future partial sells use moving average book cost. Fractional-minor-unit cost
allocations are rounded half-even to integer minor units, and remaining book
cost is calculated as previous book cost minus relieved book cost so the ledger
remains balanced. This is book cost allocation, not market valuation.

## Capital entry rules

- An inflow increases Capital and Cash by the same amount.
- An outflow decreases Capital and Cash by the same amount.
- An outflow is rejected if Cash is insufficient.
- An outflow does not affect Realized PnL or Income.
- Manual asset income increases Cash and Income by the same amount.
- Income does not affect Capital, Positions, Cost Basis, or Realized PnL.
- A manual buy decreases Cash and increases Positions by the same exact total.
- Buy fees are included in Cost Basis.
- A buy does not affect Capital, Income, Realized PnL, or portfolio Return.
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

Capital, Cash, and Book Value become `1,000.00`. Positions, Realized PnL, and Income remain `0.00`; Return remains `0.00%`.

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
