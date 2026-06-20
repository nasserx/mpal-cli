# FundLog Assets, Symbols, and Manual Trades Design

## Scope

This document defines the design contract for assets, symbols, manual trades,
fees, and asset income after the completed v0.1 portfolio and capital ledger.

The initial asset foundation is implemented:

- `fundlog asset add <portfolio> <symbol> [symbol...]`
- `fundlog asset list <portfolio>`
- `fundlog asset log <portfolio>/<symbol>`
- `fundlog asset delete <portfolio>/<symbol> --yes`
- `fundlog income <portfolio>/<symbol> <amount> [--date <date>] [--note <text>]`
- `fundlog buy <portfolio>/<symbol> --price <price> --quantity <quantity> ...`
- Normalized symbol validation.
- Asset-reference parsing.
- The portfolio-owned `assets` table.
- The `asset_transactions` storage foundation.

Buy, sell, and income transaction creation are implemented. Sell accounting
uses moving-average cost-basis relief and produces realized PnL. Asset summary
is implemented from active transactions.

FundLog remains fully manual. Every future result described here must be derived
only from records entered by the user.

## Explicit non-goals

The asset phase must not introduce:

- Live, delayed, or automatic prices.
- Market APIs or other market-data integrations.
- Broker integration or trade execution.
- Automatic valuation.
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
- A symbol cannot be empty or contain whitespace.
- A symbol cannot contain `/`.
- `/` is reserved as the asset-reference separator.
- After uppercasing, a symbol must match:

  ```text
  ^[A-Z0-9][A-Z0-9._-]*$
  ```

- A symbol has a maximum length of 32 characters after normalization.
- Letters, numbers, `.`, `-`, and `_` are allowed.
- A symbol cannot start with `.`, `-`, or `_`.

Normalization must be deterministic so that case variants such as `aapl` and
`AAPL` identify the same symbol within one portfolio. These rules support common
identifiers such as `BRK.B`, `BTC-USD`, and user-defined symbols while keeping
asset references readable and unambiguous.

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

Symbol matching is case-insensitive. Output displays symbols uppercase where
they appear as table data.

An asset reference splits on exactly one `/`:

- The left side is the portfolio name.
- The right side is the symbol.
- A missing portfolio or symbol is invalid.
- More than one `/` is invalid.
- The symbol side is normalized uppercase and validated by the symbol rules.
- The portfolio side uses the existing portfolio lookup behavior.

`/` is reserved and is not escaped or handled through quoted path parsing.
Once the asset phase begins, new portfolio names must reject `/`. Existing
portfolio names containing `/`, if any, are legacy edge cases and cannot be
used with asset-reference commands until the portfolio is renamed or recreated.

## Commands

`asset add`, `asset list`, `asset summary`, `asset log`, and `asset delete` are
implemented. Manual income, buy, and sell commands are also implemented.

### Asset management

```console
fundlog asset add <portfolio> <symbol>
fundlog asset add <portfolio> <symbol> <symbol> ...
fundlog asset list <portfolio>
fundlog asset summary <portfolio>/<symbol>
fundlog asset log <portfolio>/<symbol>
fundlog asset delete <portfolio>/<symbol> --yes
```

Implemented foundation commands:

- `asset add` validates and normalizes every symbol before writing.
- Multi-symbol creation is atomic.
- Duplicate symbols in one command are rejected.
- An active duplicate in the portfolio is rejected.
- `asset list` returns active assets ordered by symbol.
- `asset summary` returns one active asset's derived accounting totals.
- `asset log` is read-only and returns active transaction rows ordered by date
  and asset-local entry number.
- `asset delete` requires `--yes`, parses exactly one `/`, normalizes the
  symbol, and soft-deletes the active asset row and its active transactions.
- Quantity, Cost Basis, Realized PnL, Income, and Realized Return are derived
  from active buy, sell, and income transactions.

`asset add` accepts one or more symbols. Symbols are normalized for matching and
displayed uppercase. A multi-symbol add is atomic: either all supplied symbols
are added or none are.

### Manual trading and income

```console
fundlog buy <portfolio>/<symbol> --price <price> --quantity <quantity> [--fee <fee>] [--total <amount>] [--date <date>] [--note <text>]
fundlog sell <portfolio>/<symbol> --price <price> --quantity <quantity> [--fee <fee>] [--total <amount>] [--date <date>] [--note <text>]
fundlog income <portfolio>/<symbol> <amount> [--date <date>] [--note <text>]
```

- Buy, sell, and income require an existing active asset.
- These operations never auto-create an asset. This prevents a typo such as
  `APPL` from silently creating a different asset.
- `--fee` is optional and defaults to `0.00`.
- Documentation uses the long options `--price`, `--quantity`, and `--fee`.
  Short aliases may be considered later but are not required.
- Fees belong only to manual asset trades. They use money parsing and money
  formatting.
- Income amount uses the money parser and must be greater than zero.

Buy, sell, and income records need an effective date and may include a note.
All three implement optional `--date` and `--note`. An omitted date uses the
current local date. Every explicit
date uses the shared `parse_transaction_date()` helper, accepts strict ISO
`YYYY-MM-DD`, and rejects a date later than the current local date.

Buy and sell implement `--total` as an exact-cash-total override.

All state-changing commands must be atomic. Invalid input must not leave partial
records or partially changed derived balances.

## Tables

All tables must reuse the semantic theme from
`src/fundlog/output/theme.py`. Colors must not be hardcoded.

- Headers use `TABLE_HEADER`.
- Borders use `TABLE_BORDER`.
- Normal cells use `TABLE_CELL`.
- Profit values use `PROFIT`.
- Loss values use `LOSS`.
- Income values use the calm `INCOME` style.
- Buy and sell operation labels use normal cell styling, not profit/loss
  styling.

Asset log and summary output does not repeat the asset reference as a separate
title above the table.

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
- Quantity is the current open quantity and uses `format_quantity()`.
- Cost Basis is the current open book cost.
- Cost Basis and Income use money formatting. Realized PnL uses signed money
  formatting: positive values include `+`, negative values include `-`, and
  zero remains unsigned.
- Realized Return uses percent formatting and the asset-level formula defined
  below. Positive and negative nonzero returns include their sign.
- Normal cells use the unified table-cell style.
- Ordering is deterministic. Alphabetical ordering by normalized symbol is the
  initial design.

### Asset log

Command:

```console
fundlog asset log <portfolio>/<symbol>
```

The read-only command and its storage table are implemented. Income, buy, and
sell create log rows.

Columns:

| # | Date | Type | Price | Quantity | Fee | Total | Note |
|---:|---|---|---:|---:|---:|---:|---|

Rules:

- `#` is stable and local to one asset log.
- Buy, sell, and income records all receive local entry numbers.
- Entry numbers start at 1 for each asset row and are never reused after soft
  deletion.
- Type is `buy`, `sell`, or `income`.
- Price uses `format_price()`.
- Quantity uses `format_quantity()`.
- Fee and Total use `format_money()`.
- For income rows, Price, Quantity, and Fee may display `--`; Total displays the
  income amount using the `INCOME` style.
- Ordering is deterministic by effective date and then asset-local entry
  number.
- Only active transaction rows are displayed.
- Internal transaction IDs are never displayed.
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
- Average Cost uses price formatting because it is a per-unit value that may
  require more than two decimal places. Derived repeating values are rounded
  half-even to at most 18 fractional places for display only.
- Realized PnL contains realized sell results only.
- Income contains manually recorded income or distributions for this asset.
- Realized PnL and Realized Return display explicit signs for nonzero values.
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

This buy behavior is implemented. Active sells reduce Quantity and Cost Basis.

If `--total` is supplied, that money amount is the total buy
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

If `--total` is supplied, that money amount is net sell
proceeds. Price, quantity, and fee remain recorded transaction details, but the
override controls the final cash accounting and realized PnL calculation.

For a partial sell:

```text
exact allocation =
    prior open cost basis × sold quantity / prior open quantity
```

Moving average cost determines the average book cost immediately before the
sell. The relieved cost basis is the exact allocation rounded to the nearest
integer minor unit using round-half-even when the exact result contains a
fractional minor unit. The remaining open Cost Basis is then:

```text
remaining open cost basis =
    previous open cost basis - relieved cost basis
```

This guarantees:

```text
previous open cost basis =
    relieved cost basis + remaining open cost basis
```

This is a deterministic allocation of book cost, not silent rounding of a trade
cash effect and not market valuation. A sale of the entire remaining quantity
always relieves the entire remaining Cost Basis so no residual remains. Future
changes must preserve the tested partial-sale and final-sale invariants.

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

This behavior is implemented. Income rows use null Price and Quantity, zero Fee,
positive Total and cash effect, zero position and realized-PnL effects, and a
positive Income field.

### Asset-level Realized Return

```text
Realized Return = (Realized PnL + Income) / Total Buy Cost
```

Total Buy Cost is the cumulative total of active buy cash outflows for the
asset, including buy fees and any `--total` overrides. Sells do not
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
- Money input supports at most two decimal places under the existing money
  parser contract.

### Exact trade cash effects

Price and quantity are future exact Decimal-like values. Multiplication must
remain exact through validation.

FundLog must not silently round a calculated buy or sell cash effect:

```text
buy cash effect = price × quantity + fee
sell cash effect = price × quantity - fee
```

Without `--total`, the final calculated cash effect must be
exactly representable as integer minor units. If it is not, the operation is
rejected.

With `--total`:

- The supplied total must itself be valid integer-minor-unit money.
- It is parsed with the existing money parser.
- It must be greater than zero.
- For a buy, it represents total buy cash outflow after fees.
- For a sell, it represents net sell proceeds after fees.
- It is authoritative for Cash, Cost Basis or Realized PnL, Positions, the log
  Total column, and Total Buy Cost where applicable.
- Price, quantity, and fee remain recorded for audit and display.
- The calculated value from price, quantity, and fee remains available for
  validation and audit, but it does not override the explicitly supplied total.
- If the calculated value is exactly representable as minor-unit money, it must
  match `--total`.
- If the calculated value is not exactly representable as minor-unit money, a
  different `--total` is accepted because matching the broker or exchange
  statement is the purpose of the option.
- The implementation must preserve enough information to make that difference
  explicit and auditable rather than silently replacing an input.

This supports broker-statement totals without hiding sub-cent discrepancies
from values such as `0.000533 × 0.0538`.

### Fees

- Fees belong to buy and sell operations only.
- `--fee` is optional and defaults to zero.
- Fees are valid nonnegative money amounts in integer minor units.
- Fees use the existing money parser and `format_money()`.
- Fees never use price or quantity parsing or formatting.

### Quantity

Quantities must support:

```text
3
0.0538
123456
123456.0543
```

The implemented `parse_quantity()` and `format_quantity()` helpers:

- Be separate from `format_money()` and `format_price()`.
- Add thousands separators only to the integer part.
- Preserve meaningful fractional precision.
- Not force two decimal places.
- Use exact `Decimal` values and never Python `float`.
- Normalize parsed values before returning them.

Examples:

```text
123456      -> 123,456
123456.0543 -> 123,456.0543
0.0538      -> 0.0538
```

The accepted maximum precision, storage representation, trailing-zero
normalization, and upper bounds are:

- Input uses plain decimal notation only.
- Scientific notation is rejected.
- A buy or sell quantity must be greater than zero.
- Derived current open quantity may be zero.
- Input supports at most 18 digits before the decimal point and 18 digits after
  it.
- Quantity is stored as normalized decimal text in SQLite.
- Normalization removes unnecessary leading zeros, removes trailing fractional
  zeros, and removes the decimal point when no fractional digits remain.
- Zero is normalized as `0`.
- Quantity is parsed into an exact decimal type for validation and arithmetic.
- Quantity is never stored or calculated as binary floating point.

### Price

Prices must support:

```text
234.43
0.000533
```

The implemented `parse_price()` and `format_price()` helpers:

- Be separate from `format_money()` and `format_quantity()`.
- Preserve meaningful precision.
- Not force two decimal places.
- Never use Python `float`.
- Normalize parsed values before returning them.

The accepted maximum precision, storage representation, trailing-zero
normalization, and upper bounds are:

- Input uses plain decimal notation only.
- Scientific notation is rejected.
- Buy and sell prices must be greater than zero.
- Input supports at most 18 digits before the decimal point and 18 digits after
  it.
- User-entered price is stored as normalized decimal text in SQLite.
- Normalization removes unnecessary leading zeros, removes trailing fractional
  zeros, and removes the decimal point when no fractional digits remain.
- Price is parsed into an exact decimal type for validation and arithmetic.
- Price is never stored or calculated as binary floating point.

### Percentages

Asset Realized Return and portfolio Return use the existing visual percent
convention. Positive values display `+`, negative values display `-`, and zero
remains unsigned. A zero denominator displays `0.00%` and never causes a
runtime error.

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
- The operation atomically soft-deletes the active asset row and all its active
  transaction rows.
- Database rows and audit-ready metadata are preserved.
- The deleted asset is excluded from active asset lists and lookups.
- Other assets and portfolios are unaffected.
- The same symbol may be added again as a new active row because uniqueness
  applies only to active assets.
- Hard delete and purge remain future work.

Soft-deleted buy, sell, and income transactions stop contributing to asset
lists, asset logs, and portfolio summaries. Database rows remain preserved.

## Validation principles

- Portfolio and asset references resolve only to active records.
- Buy, sell, and income require an existing active asset.
- Symbol input is matched case-insensitively and displayed uppercase.
- Symbols must match `^[A-Z0-9][A-Z0-9._-]*$` after uppercasing and cannot
  exceed 32 characters.
- Asset references contain exactly one `/` with nonempty portfolio and symbol
  sides.
- Portfolio names containing `/` cannot be used with asset references.
- Prices and quantities are positive exact decimal values.
- Income amounts are positive money values.
- Fees are nonnegative money values and default to `0.00`.
- Malformed, non-finite, unsupported-precision, and out-of-range numeric input
  is rejected.
- Scientific notation is rejected for price and quantity.
- Sells cannot exceed open quantity.
- Sell net proceeds must be positive.
- Calculated trade cash effects that are not exact minor-unit money are rejected
  unless `--total` is supplied.
- Explicit transaction dates use the shared date helper and cannot be in the
  future.
- Failed commands exit nonzero and leave no partial changes.

## Remaining open questions

There are no known open questions blocking the initial asset implementation
design. Schema shape, command error wording, and internal module boundaries
remain implementation-planning details rather than unresolved product rules.

## Future implementation sequence

The implemented foundation does not authorize later features. Future work can
proceed in reviewable steps only when explicitly requested:

1. Add transaction correction workflows only when explicitly designed.
2. Add further reporting without market valuation or unrealized PnL.
