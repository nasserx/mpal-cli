# FundLog Assets, Symbols, and Manual Trades Design

## Scope

This document defines the future design contract for assets, symbols, manual
trades, fees, and asset income after the completed v0.1 portfolio and capital
ledger.

This is documentation only. None of the commands, storage, calculations, or
tables described here are implemented. The implemented v0.1 portfolio and
capital behavior must remain unchanged until asset implementation is explicitly
requested.

FundLog remains fully manual. Every future result described here must be derived
only from records entered by the user.

## Explicit non-goals

The asset phase must not introduce:

- Live, delayed, or automatic prices.
- Market APIs or other market-data integrations.
- Broker integration or trade execution.
- Market value.
- Unrealized PnL.
- Automatic asset creation during buy, sell, or income operations.
- Portfolio-level fee commands or fee summary columns.
- Python `float` for financial parsing or calculations.
- Hard deletion or purge behavior.

Positions and Book Value remain book/accounting values. Realized Return is not
market return.

## Terminology

### Symbol

A symbol is a user-entered ticker or code such as `AAPL`, `MSFT`, or `BTC`.

- Input matching is case-insensitive.
- Display is always uppercase.
- A symbol is one token, not a multi-word name.
- A symbol cannot contain spaces.
- A symbol cannot contain `/`.
- `/` is reserved as the asset-reference separator.

Normalization must be deterministic so that case variants such as `aapl` and
`AAPL` identify the same symbol within one portfolio. The remaining allowed
character set, maximum length, and numeric storage limits must be finalized
before implementation.

### Asset

An asset is a symbol inside a specific portfolio. For example, `AAPL` in the
`stocks` portfolio is one asset.

- Every asset belongs to exactly one portfolio.
- The same normalized symbol may exist in different portfolios as separate
  assets.
- One portfolio cannot contain multiple active assets with the same normalized
  symbol.
- Assets are children of portfolios.
- Assets do not appear as rows in the portfolio summary.
- Active asset transactions feed the owning portfolio's summary totals.

### Asset reference

Commands identify an asset using:

```text
<portfolio>/<symbol>
```

Examples:

```text
stocks/AAPL
stocks/aapl
crypto/BTC
```

Symbol matching is case-insensitive. Output displays the symbol uppercase and
uses the portfolio's stored normalized or original display name.

Asset-specific output may use a symbol-first title:

```text
AAPL/stocks
```

The input reference follows the ownership path. The display title leads with
the subject of the report.

Portfolio names used in asset references also need an unambiguous path
representation. Before implementation, FundLog must either reject `/` in
portfolio names or define an escaping rule.

## Commands

The commands in this section are future contracts only.

### Asset management

```console
fundlog asset add <portfolio> <symbol>
fundlog asset add <portfolio> <symbol> <symbol> ...
fundlog asset list <portfolio>
fundlog asset summary <portfolio>/<symbol>
fundlog asset log <portfolio>/<symbol>
fundlog asset delete <portfolio>/<symbol> --yes
```

`asset add` accepts one or more symbols. Symbols are normalized for matching and
displayed uppercase. A multi-symbol add must be atomic: either all supplied
symbols are added or none are.

### Manual trading and income

```console
fundlog buy <portfolio>/<symbol> --price <price> --quantity <quantity> [--fee <fee>]
fundlog sell <portfolio>/<symbol> --price <price> --quantity <quantity> [--fee <fee>]
fundlog income <portfolio>/<symbol> <amount>
```

- Buy, sell, and income require an existing active asset.
- These operations never auto-create an asset. This prevents a typo such as
  `APPL` from silently creating a different asset.
- `--fee` is optional and defaults to zero.
- Documentation uses the long options `--price`, `--quantity`, and `--fee`.
  Short aliases may be considered later but are not required.
- Fees belong only to manual asset trades. They use money parsing and money
  formatting.

Buy, sell, and income records need an effective date and may include a note.
The initial command contract should provide optional `--date` and `--note`
options for all three operations. An omitted date uses the current local date.
Every explicit date must use the shared `parse_transaction_date()` helper,
accept strict ISO `YYYY-MM-DD`, and reject a date later than the current local
date.

Buy and sell also need a future exact-cash-total override for broker statements
and otherwise unrepresentable calculated totals. `--total` is the working name,
but the exact option name may be finalized during CLI implementation design.
Its accounting semantics are fixed in the precision section below.

All state-changing commands must be atomic. Invalid input must not leave partial
records or partially changed derived balances.

## Tables

All future tables must reuse the semantic theme from
`src/fundlog/output/theme.py`. Colors must not be hardcoded.

- Headers use `TABLE_HEADER`.
- Borders use `TABLE_BORDER`.
- Normal cells use `TABLE_CELL`.
- Profit values use `PROFIT`.
- Loss values use `LOSS`.
- Income may use `INFO` when the result remains visually calm.
- Buy and sell operation labels use normal cell styling, not profit/loss
  styling.

Asset tables should include a small title above the table using the existing
CLI style or the closest clean Rich equivalent:

```text
-- AAPL/stocks --------------------------------
```

Color must not be the only way meaning is communicated.

### Asset list

Command:

```console
fundlog asset list <portfolio>
```

Columns:

| Symbol | Quantity | Cost Basis | Realized PnL | Income | Realized Return |
|---|---:|---:|---:|---:|---:|

Rules:

- Symbol is displayed uppercase.
- Quantity is the current open quantity and uses future `format_quantity()`.
- Cost Basis is the current open book cost.
- Cost Basis, Realized PnL, and Income use `format_money()`.
- Realized Return uses percent formatting and the asset-level formula defined
  below.
- Normal cells use the unified table-cell style.
- Ordering is deterministic. Alphabetical ordering by normalized symbol is the
  initial design.

### Asset log

Command:

```console
fundlog asset log <portfolio>/<symbol>
```

Columns:

| # | Date | Type | Price | Quantity | Fee | Total | Note |
|---:|---|---|---:|---:|---:|---:|---|

Rules:

- `#` is stable and local to one asset log.
- Buy, sell, and income records all receive local entry numbers.
- Entry numbers start at 1 for each asset row and are never reused after soft
  deletion.
- Type is `buy`, `sell`, or `income`.
- Price uses future `format_price()`.
- Quantity uses future `format_quantity()`.
- Fee and Total use `format_money()`.
- For income rows, Price, Quantity, and Fee may display `--`; Total displays the
  income amount.
- Ordering is deterministic by effective date and then asset-local entry
  number.
- Buy and sell types and totals are normal operations and do not use
  profit/loss coloring.

Total is the final cash effect represented as a positive displayed amount:

- Buy: total buy cash outflow.
- Sell: net sell proceeds.
- Income: income amount.

Direction is communicated by Type.

### Asset summary

Command:

```console
fundlog asset summary <portfolio>/<symbol>
```

Columns:

| Quantity | Cost Basis | Average Cost | Realized PnL | Income | Realized Return |
|---:|---:|---:|---:|---:|---:|

Rules:

- Quantity is the current open quantity.
- Cost Basis is the current open book cost.
- `Average Cost = Cost Basis / Quantity` when Quantity is greater than zero.
- When Quantity is zero, Average Cost displays `--`.
- Average Cost uses future price formatting because it is a per-unit value that
  may require more than two decimal places.
- Realized PnL contains realized sell results only.
- Income contains manually recorded income or distributions for this asset.
- Realized Return uses the asset-level formula below.
- The table contains no market value or unrealized PnL.

## Accounting rules

### Cost basis method

The initial cost basis method is moving average cost.

Moving average fits a manual CLI because it maintains one aggregate open
quantity and open cost basis per asset, is straightforward to reconcile, and
does not require lot selection. FIFO may be considered later if FundLog adds
lot-level or tax-lot requirements, but FIFO is not the initial method.

All calculations use exact decimal or integer arithmetic. Python `float` is
prohibited.

### Buy

```text
gross buy cost = price × quantity
buy fee = fee
total buy cash outflow = gross buy cost + buy fee
new open quantity = prior open quantity + bought quantity
new open cost basis = prior open cost basis + total buy cash outflow
```

- Fee defaults to zero.
- Buy fee is included in cost basis.
- Portfolio Cash decreases by total buy cash outflow.
- Portfolio Positions increases by total buy cash outflow.
- Capital, Realized PnL, and Income do not change.
- Cumulative Total Buy Cost increases by total buy cash outflow.

If an exact-cash-total override is supplied, that money amount is the total buy
cash outflow and the amount added to Cost Basis, Positions, and cumulative Total
Buy Cost. Price, quantity, and fee remain recorded transaction details, but the
override controls the final cash accounting.

### Sell

```text
gross sell proceeds = price × quantity
sell fee = fee
net sell proceeds = gross sell proceeds - sell fee
relieved cost basis = moving-average cost allocated to sold quantity
realized PnL = net sell proceeds - relieved cost basis
```

- Fee defaults to zero.
- Sell fee reduces net proceeds and therefore reduces Realized PnL.
- Portfolio Cash increases by net sell proceeds.
- Portfolio Positions decreases by relieved cost basis.
- Portfolio Realized PnL changes by realized PnL.
- Capital and Income do not change.
- A sell cannot exceed the current open quantity.
- A sell must have positive net proceeds.

If an exact-cash-total override is supplied, that money amount is net sell
proceeds. Price, quantity, and fee remain recorded transaction details, but the
override controls the final cash accounting and realized PnL calculation.

For a partial sell:

```text
exact allocation =
    prior open cost basis × sold quantity / prior open quantity
```

The relieved cost basis is the exact allocation rounded to the nearest integer
minor unit using round-half-even. This is a documented internal cost allocation,
not silent rounding of a trade cash effect. A sale of the entire remaining
quantity always relieves the entire remaining Cost Basis so no residual remains.

### Income

```text
cash increase = income amount
income increase = income amount
```

- Income requires an existing active asset.
- Portfolio Cash increases by the income amount.
- Portfolio Income increases by the income amount.
- Income does not affect Cost Basis, Positions, Capital, or Realized PnL.
- Income is included in asset and portfolio return calculations.
- Income is not a market gain.

### Asset-level Realized Return

```text
Realized Return = (Realized PnL + Income) / Total Buy Cost
```

Total Buy Cost is the cumulative total of active buy cash outflows for the
asset, including buy fees and any exact-cash-total overrides. Sells do not
reduce Total Buy Cost.

If Total Buy Cost is zero, Realized Return displays `0.00%`.

This is a realized accounting result. It does not include market value,
unrealized PnL, or market movement.

## Precision and formatting

### Money

- Money is stored as integer minor units.
- Monetary input and calculations never use Python `float`.
- Money displays through the existing `format_money()`.
- Money displays thousands separators and exactly two decimal places.
- Fees, final trade cash totals, Cost Basis, Income, and Realized PnL are money.

### Exact trade cash effects

Price and quantity are future exact Decimal-like values. Multiplication must
remain exact through validation.

FundLog must not silently round a calculated buy or sell cash effect:

```text
buy cash effect = price × quantity + fee
sell cash effect = price × quantity - fee
```

Without an exact-cash-total override, the final calculated cash effect must be
exactly representable as integer minor units. If it is not, the operation is
rejected.

With the future exact-cash-total override:

- The supplied total must itself be valid integer-minor-unit money.
- For a buy, it represents total buy cash outflow after fees.
- For a sell, it represents net sell proceeds after fees.
- It is authoritative for Cash, Cost Basis or Realized PnL, Positions, the log
  Total column, and Total Buy Cost where applicable.
- Price, quantity, and fee remain recorded for audit and display.

This supports broker-statement totals without hiding sub-cent discrepancies
from values such as `0.000533 × 0.0538`.

### Fees

- Fees belong to buy and sell operations only.
- `--fee` is optional and defaults to zero.
- Fees are valid nonnegative money amounts in integer minor units.
- Fees use money parsing and `format_money()`.
- Fees never use price or quantity parsing or formatting.

### Quantity

Quantities must support:

```text
3
0.0538
123456
123456.0543
```

Future `format_quantity()` must:

- Be separate from `format_money()` and `format_price()`.
- Add thousands separators only to the integer part.
- Preserve meaningful fractional precision.
- Not force two decimal places.

Examples:

```text
123456      -> 123,456
123456.0543 -> 123,456.0543
0.0538      -> 0.0538
```

The accepted maximum precision, storage representation, trailing-zero
normalization, and upper bounds must be finalized before implementation.

### Price

Prices must support:

```text
234.43
0.000533
```

Future `format_price()` must:

- Be separate from `format_money()` and `format_quantity()`.
- Preserve meaningful precision.
- Not force two decimal places.
- Never use Python `float`.

The accepted maximum precision, storage representation, trailing-zero
normalization, and upper bounds must be finalized before implementation.

### Percentages

Asset Realized Return and portfolio Return use the existing visual percent
convention. A zero denominator displays `0.00%` and never causes a runtime
error.

## Portfolio integration

The portfolio summary columns remain exactly:

`Portfolio | Capital | Cash | Positions | Book Value | Realized PnL | Income | Return`

Assets never appear as additional rows in the portfolio summary. Active asset
transactions contribute to the owning portfolio row:

- **Capital** = external inflows minus external outflows.
- **Cash** = inflows minus outflows minus buy cash outflows plus sell net
  proceeds plus income.
- **Positions** = total open Cost Basis across active assets.
- **Book Value** = Cash plus Positions.
- **Realized PnL** = total realized profit or loss from active manual sells.
- **Income** = total active manually recorded asset income.
- **Return** = `(Realized PnL + Income) / Capital`.

If Capital is zero, Return displays `0.00%`.

These are accounting results from manual records. Positions and Book Value are
not market value, and Return excludes unrealized market movement.

## Deletion rules

```console
fundlog asset delete <portfolio>/<symbol> --yes
```

- `--yes` is mandatory.
- Asset deletion is a soft delete.
- The operation atomically soft-deletes the asset and all its active buy, sell,
  and income transactions.
- Database rows and audit-ready metadata are preserved.
- Soft-deleted asset transactions no longer contribute to Cash, Positions,
  Book Value, Realized PnL, Income, Total Buy Cost, or returns.
- The operation therefore removes all active accounting effects of the asset
  from its portfolio summary.
- Asset-local entry numbers from the deleted asset row are not reused.
- Hard delete and purge remain future work.

The implementation must validate the resulting portfolio state before
committing the deletion. If removing the asset's active transaction effects
would violate a portfolio invariant such as nonnegative Cash, the deletion must
fail atomically and leave the asset and transactions active.

## Validation principles

- Portfolio and asset references resolve only to active records.
- Buy, sell, and income require an existing active asset.
- Symbol input is matched case-insensitively and displayed uppercase.
- Symbols reject spaces and `/`.
- Prices and quantities are positive exact decimal values.
- Income amounts are positive money values.
- Fees are nonnegative money values and default to zero.
- Malformed, non-finite, unsupported-precision, and out-of-range numeric input
  is rejected.
- Sells cannot exceed open quantity.
- Sell net proceeds must be positive.
- Calculated trade cash effects that are not exact minor-unit money are rejected
  unless an exact-cash-total override is supplied.
- Explicit transaction dates use the shared date helper and cannot be in the
  future.
- Failed commands exit nonzero and leave no partial changes.

## Remaining open questions

The accounting direction and command behavior are resolved. These bounded
representation details remain for implementation design:

1. What exact allowed-character set and maximum length should symbols use
   beyond the fixed no-space and no-`/` rules?
2. What maximum precision, storage representation, trailing-zero policy, and
   numeric bounds should price and quantity use?
3. Should `/` be prohibited in portfolio names before asset references are
   implemented, or should references define escaping?
4. Should the exact-cash-total option keep the working name `--total`, or use a
   more explicit name? Its accounting semantics are already fixed above.

## Future implementation sequence

This document does not authorize implementation. After the remaining
representation details are finalized and implementation is explicitly
requested, work can proceed in reviewable steps:

1. Finalize symbol/reference grammar and exact price/quantity representation.
2. Design storage and migrations without changing existing v0.1 behavior.
3. Add separate exact parsers and formatters for quantity and price.
4. Add asset management and soft-deletion behavior.
5. Add buy, sell, and income behavior with shared date validation.
6. Add exact-total validation and moving-average accounting.
7. Feed active asset results into the unchanged portfolio summary columns.
8. Add themed asset list, summary, and log output.
9. Add focused unit, integration, accounting-invariant, and atomicity tests.
