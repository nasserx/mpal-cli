# mpal v0.1 Financial Model

## Principles

mpal is fully manual. It derives financial results only from active recorded operations and does not use live prices, market APIs, automatic valuation, market value, or unrealized PnL.

The completed v0.1 capital ledger records portfolio deposits and withdrawals. The
current asset milestone also records manual asset income, buys, and sells.
Financial amounts use integer minor units in storage and decimal-safe logic in
application code; binary floating point is not used.

Displayed monetary values use thousands separators and exactly two decimal
places. This display rule is specific to money and does not define formatting
for quantities, unit prices, or price-like derived values.

Manual asset calculations use exact decimal arithmetic for price
and quantity and integer minor units for every cash effect. Price and quantity
accept plain decimal notation with at most 18 integer digits and 18 fractional
digits; scientific notation and Python `float` are prohibited. A calculated
trade cash effect must be exactly representable in minor units or the trade must
use the exact-money `--total` override described in
`docs/ASSETS_SPEC.md`.

The reusable `parse_quantity()`, `format_quantity()`, `parse_price()`,
`format_price()`, and `format_price_display()` helpers implement the exact
input and display contract. Quantity and price formatting remain separate from
`format_money()`. Quantity display removes unnecessary trailing zeros. Price
display for user-facing tables uses an asset-level fixed scale inferred from
active buy/sell price text, with a minimum of two decimal places and a cap at
the parser-supported precision.

## Summary table

The summary output has exactly these columns:

| Portfolio | Capital | Cash | Positions | Book Value | Realized PnL | Income | Return |
|---|---:|---:|---:|---:|---:|---:|---:|

The internal portfolio database ID is not part of summary output.

`mpal summary` is the unified summary/reporting command. With no options, it
uses one aggregate row across active portfolios:

| TOTAL CAPITAL | TOTAL INCOME | REALIZED P&L | RETURN |
|---:|---:|---:|---:|

`TOTAL CAPITAL` is the sum of active portfolio Capital. `TOTAL INCOME` is the
sum of active asset Income. `REALIZED P&L` is the sum of active realized sell
PnL. Global `RETURN` is `(TOTAL INCOME + REALIZED P&L) / TOTAL CAPITAL`, or
`0.00%` when total capital is zero. Global return is computed from global
totals, not by averaging portfolio returns. It does not use live prices,
market value, or unrealized PnL.

`mpal summary -p <portfolio>` uses the portfolio summary columns above for one
active portfolio. `mpal summary -p <portfolio> -a <asset>` uses the existing
single-asset reporting view for one active asset within one active portfolio.
`summary -a` requires `-p`.

### Capital

External capital only.

In v0.1:

`Capital = total active deposits - total active withdrawals`

### Cash

Available cash inside the portfolio that is not tied to open positions.

In v0.1:

`Cash = total active deposits - total active withdrawals`

Implemented manual asset income increases Cash. Buys decrease Cash by exact
total cash outflow, and sells increase Cash by exact net proceeds.

### Positions

The book cost of currently open positions. Positions is not market value, live value, or unrealized value.

Implemented buys increase Positions by total buy cash outflow, including buy
fees. Implemented sells decrease Positions by moving-average relieved book
cost.

### Book Value

`Book Value = Cash + Positions`

Book Value is a book/accounting value based only on manual records. It must not imply market value.

Book Value remains `Cash + Positions`. A buy transfers book value from Cash to
Positions. A sell transfers relieved book cost from Positions to Cash and
changes Book Value only by its realized profit or loss.

### Realized PnL

Profit or loss realized from closed or partially closed manual positions:

`Realized PnL = sell net proceeds - moving-average relieved Cost Basis`

Active sell realized-PnL effects are summed for asset and portfolio output.

### Income

Cash income from manually recorded asset distributions or dividends.

Implemented income transactions increase both Cash and Income. Soft-deleted
transactions and transactions belonging to soft-deleted assets do not
contribute.

### Return

Return is based on realized results only, not unrealized market movement.

The formula is:

`Return = (Realized PnL + Income) / Capital`

Return reflects active Realized PnL plus Income divided by Capital. If Capital
is zero, Return displays `0.00%`.

Asset-level Realized Return uses:

`Asset Realized Return = (Asset Realized PnL + Asset Income) / Total Buy Cost`

Total Buy Cost is cumulative buy cash outflow including buy fees. If Total Buy
Cost is zero, asset Realized Return is `0.00%`.

The asset current-state output displays `Average Cost = Cost Basis / Quantity` when
open Quantity is positive. The calculation remains exact internally, and the
result is displayed as a price-like value using the asset's inferred price
display scale. Raw Decimal division output is never displayed. Zero Quantity
displays `--`.

Realized PnL and return values use signed display formatting: positive values
include `+`, negative values include `-`, and zero remains unsigned. This is
display-only and does not change stored accounting values or formulas.

Partial sells use moving average book cost. Fractional-minor-unit cost
allocations are rounded half-even to integer minor units, and remaining book
cost is calculated as previous book cost minus relieved book cost so the ledger
remains balanced. This is book cost allocation, not market valuation.

## Asset accounting replay

Asset buys, sells, and income are append-style manual records. Current
portfolio and asset values are derived from active transaction effects.
`asset entry edit` and `asset entry delete` recalculate those effects by
replaying the active transaction history for one asset from scratch.

The correction replay order is asset-local `entry_no` order, not transaction
date. Transaction date remains the effective date shown in logs and may be used
for display sorting. This keeps accounting tied to the user's stable ledger
sequence even if a corrected date moves a row earlier or later in the displayed
asset log.

Replay validation rejects any entry edit or entry delete that would make the
ledger invalid. A replay step is invalid if it creates negative quantity, sells
more than the open quantity, produces an invalid exact cash effect, or leaves
residual Cost Basis after a full sell. Failed replay leaves existing rows and
accounting effects unchanged. A successful entry edit updates the selected
active row in place. A successful entry delete soft-deletes the selected row.
Both commands update active transaction accounting fields affected by
moving-average Cost Basis.

## Capital entry rules

- A deposit increases Capital and Cash by the same amount.
- A withdrawal decreases Capital and Cash by the same amount.
- A withdrawal is rejected if Cash is insufficient.
- A withdrawal does not affect Realized PnL or Income.
- Manual asset income increases Cash and Income by the same amount.
- Income does not affect Capital, Positions, Cost Basis, or Realized PnL.
- A manual buy decreases Cash and increases Positions by the same exact total.
- Buy fees are included in Cost Basis.
- A buy does not affect Capital, Income, Realized PnL, or portfolio Return.
- A manual sell increases Cash by exact net proceeds and decreases Positions by
  moving-average relieved Cost Basis.
- Sell fees reduce net proceeds and therefore reduce Realized PnL.
- A full-position sell relieves all remaining Cost Basis.
- A sell does not affect Capital or Income.
- Active entries alone contribute to current calculations.
- Soft-deleted entries do not contribute.
- Portfolio reset soft-deletes portfolio entries.
- Entry deletions, portfolio deletions, and resets retain rows and timestamps.
  Edits update the existing row timestamp; full before-and-after audit history is
  future work.
- mpal must not invent market value or use price-based valuation.
- Fees are not a portfolio-level summary field. If supported later, they belong within manual symbol trading calculations.

## Example scenarios

### Empty portfolio

| Portfolio | Capital | Cash | Positions | Book Value | Realized PnL | Income | Return |
|---|---:|---:|---:|---:|---:|---:|---:|
| stocks | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% |

### Add a deposit

```console
mpal deposit 1000 -p stocks
```

Capital, Cash, and Book Value become `1,000.00`. Positions, Realized PnL, and Income remain `0.00`; Return remains `0.00%`.

### Add a withdrawal

```console
mpal withdraw 250 -p stocks
```

After the preceding deposit, Capital, Cash, and Book Value become `750.00`. The other v0.1 summary values remain zero.

### Attempt a withdrawal with insufficient Cash

```console
mpal withdraw 1000 -p stocks
```

With only `750.00` Cash available, the command fails, creates no entry, and leaves the summary unchanged.
