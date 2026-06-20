# FundLog Assets, Symbols, and Trades Design

## Status and scope

This document defines the proposed design for FundLog's next phase after the
v0.1 portfolio and capital ledger. It is a design contract only. Assets,
symbols, trades, fees, and income commands are not implemented.

The implemented v0.1 portfolio and capital behavior remains unchanged.

FundLog remains fully manual:

- No live or automatic prices.
- No market APIs or market-data integrations.
- No market value.
- No unrealized PnL.
- No broker integration or trade execution.
- No Python `float` for financial calculations.

All future results described here must be derived only from records entered by
the user.

## Terminology

### Symbol

A symbol is a user-entered ticker or code such as `AAPL`, `MSFT`, or `BTC`.

- Input is case-insensitive.
- Display is always uppercase.
- A symbol is one token, not a multi-word name.
- Symbols cannot contain spaces.
- `/` is reserved as the asset-reference path separator and cannot appear in a
  symbol.

The future validation contract should define the remaining allowed characters
and maximum length before implementation. Symbol normalization must be
deterministic so that case variants such as `aapl` and `AAPL` identify the same
symbol within one portfolio.

### Asset

An asset is a symbol inside a specific portfolio. For example, `AAPL` in the
`stocks` portfolio is one asset.

- Every asset belongs to exactly one portfolio.
- The same normalized symbol may exist in different portfolios as separate
  assets.
- The same normalized symbol must not identify multiple active assets in one
  portfolio.
- Assets are children of portfolios.
- Assets do not appear as rows in the portfolio summary.
- Derived asset and trade results feed the owning portfolio's summary totals.

### Asset reference

CLI commands identify an asset as:

```text
<portfolio>/<symbol>
```

Examples:

```text
stocks/AAPL
stocks/aapl
crypto/BTC
```

Symbol matching is case-insensitive. Display uses the uppercase symbol and the
portfolio's stored normalized or original display name. Asset-specific output
uses a title in symbol-first form:

```text
AAPL/stocks
```

The input reference and display title intentionally use different ordering:
input follows the ownership path, while the title leads with the subject of the
report.

Because `/` separates the two path components, symbols cannot contain `/`.
Portfolio names used in asset references must also have an unambiguous path
representation. The implementation phase must either confirm that active
portfolio-name validation excludes `/` or define an escaping policy before
these commands are implemented.

## Proposed CLI contract

The command shapes in this section are proposals for a later implementation.
They do not modify the implemented v0.1 CLI.

### Asset management

```console
fundlog asset add <portfolio> <symbol>
fundlog asset add <portfolio> <symbol> <symbol> ...
fundlog asset list <portfolio>
fundlog asset summary <portfolio>/<symbol>
fundlog asset log <portfolio>/<symbol>
fundlog asset delete <portfolio>/<symbol> --yes
```

`asset add` accepts one or more symbols. Each symbol is normalized for matching
and displayed uppercase. The operation should be atomic when multiple symbols
are supplied: either every valid, non-conflicting asset is added or none are.

The current proposed baseline is that buy, sell, and income operations require
an existing active asset. They should not silently auto-create one. This remains
an explicit open decision below and must be settled before implementation.

`asset delete` requires `--yes`. Its behavior when the asset has operation
history or an open quantity remains unresolved.

### Manual trading and income

```console
fundlog buy <portfolio>/<symbol> --price <price> --quantity <quantity> --fee <fee>
fundlog sell <portfolio>/<symbol> --price <price> --quantity <quantity> --fee <fee>
fundlog income <portfolio>/<symbol> <amount>
```

Documentation should prefer the long option names `--price`, `--quantity`, and
`--fee`. Short aliases such as `-p`, `-q`, and `-f` may be considered later but
are not part of the initial required design.

Future transaction records need an effective date and may support a note. If a
date is omitted, it should use the current local date. Any user-provided date
must use the shared `parse_transaction_date()` helper, accept strict ISO
`YYYY-MM-DD`, and reject dates later than the current local date. The exact
`--date` and `--note` command surface should be finalized before implementation.

All state-changing operations must be atomic and must reject invalid input
without leaving partial records or partially changed derived balances.

## Portfolio integration

The existing portfolio summary columns remain exactly:

`Portfolio | Capital | Cash | Positions | Book Value | Realized PnL | Income | Return`

Assets must not add rows to this table. Active manual records for all assets in
a portfolio contribute to the portfolio row:

- **Capital** = external capital only: inflows minus outflows.
- **Cash** = inflows minus outflows minus buy cash outflows plus sell cash
  inflows plus income.
- **Positions** = total open book cost of asset positions.
- **Book Value** = Cash plus Positions.
- **Realized PnL** = total realized profit or loss from manual sells.
- **Income** = total manually recorded asset income or distributions.
- **Return** = `(Realized PnL + Income) / Capital`.

If Capital is zero, Return must deterministically display `0.00%`.

These values are accounting results from manual records. Positions and Book
Value do not represent market value, and Return does not include unrealized
market movement.

## Asset list

Proposed command:

```console
fundlog asset list <portfolio>
```

Proposed columns:

| Symbol | Quantity | Cost Basis | Realized PnL | Income | Realized Return |
|---|---:|---:|---:|---:|---:|

Rules:

- `Symbol` is displayed uppercase.
- `Quantity` is the current open quantity and uses a future
  `format_quantity()`, never `format_money()`.
- `Cost Basis` is the open book cost of the current position.
- `Cost Basis`, `Realized PnL`, and `Income` use `format_money()`.
- `Realized Return` uses percent formatting and must describe realized results
  only.
- Profit and loss values use the semantic profit and loss styles when
  implemented.
- Income may use the existing informational soft-blue style only when it
  remains visually calm.
- Ordering must be deterministic. Alphabetical ordering by normalized symbol is
  the proposed default.

## Asset summary

Proposed command:

```console
fundlog asset summary <portfolio>/<symbol>
```

Proposed columns:

| Quantity | Cost Basis | Average Cost | Realized PnL | Income | Realized Return |
|---:|---:|---:|---:|---:|---:|

Rules:

- `Quantity` is the current open quantity.
- `Cost Basis` is the open book cost of the current position.
- `Average Cost = Cost Basis / Quantity` when Quantity is greater than zero.
- When Quantity is zero, Average Cost must use a deterministic nonnumeric
  placeholder such as `--`, not an invented zero-cost position.
- `Average Cost` uses the future price-formatting rules, not money formatting,
  because it is a per-unit value that may require precision beyond two decimal
  places.
- `Realized PnL` is realized profit or loss from sells.
- `Income` is manually recorded income or distributions for this asset.
- `Realized Return` is a realized-result percentage only. It must not imply
  market return and must not include unrealized PnL.

The denominator for asset-level Realized Return is not yet defined and is
listed as an open accounting question. It must be settled before this column is
implemented.

## Asset log

Proposed command:

```console
fundlog asset log <portfolio>/<symbol>
```

Proposed columns:

| # | Date | Type | Price | Quantity | Fee | Total | Note |
|---:|---|---|---:|---:|---:|---:|---|

Rules:

- `#` is stable and local to one asset log, similar to portfolio-local capital
  entry numbers.
- `Type` is `buy`, `sell`, or `income`.
- Buy and sell labels are normal operation types and must not be colored as
  profit or loss.
- `Price` uses future `format_price()`, never `format_money()`.
- `Quantity` uses future `format_quantity()`, never `format_money()`.
- `Fee` and `Total` use `format_money()`.
- For income rows, Price, Quantity, and Fee may display `--`; Total displays the
  income amount.
- Ordering must be deterministic by effective date and then asset-local entry
  number.

`Total` represents the cash effect for the row:

- Buy: gross buy cost plus fee, displayed as a positive outflow amount.
- Sell: gross proceeds minus fee, displayed as a positive inflow amount.
- Income: the income amount.

Direction remains explicit through `Type`; normal buy and sell Total cells do
not use profit/loss coloring.

## Manual accounting model

### Cost basis method

The proposed initial cost basis method is moving average cost.

Moving average is preferred over FIFO for the initial manual CLI because it
requires one aggregate open quantity and open cost basis per asset conceptually,
is easier for users to reconcile, and avoids exposing lot-selection behavior.
FIFO remains a valid alternative if lot-level reporting or tax-lot semantics
become a product requirement, but it is not the proposed initial method.

The implementation design must use decimal-safe or integer-safe arithmetic
throughout. Python `float` is prohibited.

### Buy

For a manual buy:

```text
gross buy cost = price × quantity
buy cash outflow = gross buy cost + fee
new open quantity = prior open quantity + bought quantity
new open cost basis = prior open cost basis + gross buy cost + fee
```

- Cash decreases by the buy cash outflow.
- Positions increases by the amount added to open cost basis.
- The buy fee is included in cost basis.
- Capital, Realized PnL, and Income do not change.

The resulting trade amount must be representable as integer minor-unit money
under the precision policy selected before implementation.

### Sell

For a manual sell:

```text
gross proceeds = price × quantity
net proceeds = gross proceeds - fee
relieved cost basis = sold quantity × current moving average cost
realized PnL = net proceeds - relieved cost basis
```

- Cash increases by net proceeds.
- Positions decreases by the relieved cost basis.
- Realized PnL increases or decreases by the realized PnL from the sell.
- The sell fee reduces realized PnL through net proceeds.
- Capital and Income do not change.
- A sell cannot exceed the current open quantity.

Cost-basis relief must preserve accounting invariants in integer minor units.
In particular, selling the entire remaining quantity must relieve the entire
remaining cost basis so no rounding residue remains. The precise allocation
and rounding rule for partial sells must be documented before implementation.

### Income

For manually recorded asset income:

```text
cash increase = income amount
income increase = income amount
```

- Cash increases by the income amount.
- Income increases by the income amount.
- Capital, Positions, and Realized PnL do not change.
- Income is not a market gain.
- Income is included in portfolio Return.

Whether income requires an existing active asset is an open decision. The
proposed baseline is yes, consistent with buy and sell.

## Precision and formatting

### Money

- Store money as integer minor units.
- Parse and calculate money without Python `float`.
- Display money with the existing `format_money()`.
- Display thousands separators and exactly two decimal places.
- Fees, trade cash totals, cost basis, realized PnL, and income are money.

### Quantity

Quantities must support values such as:

```text
3
0.0538
123456
123456.0543
```

A future `format_quantity()` must:

- Remain separate from `format_money()`.
- Add thousands separators only to the integer part.
- Preserve meaningful fractional precision.
- Not force exactly two decimal places.

Expected examples:

```text
123456      -> 123,456
123456.0543 -> 123,456.0543
0.0538      -> 0.0538
```

The implementation design must define accepted maximum precision, storage
representation, normalization of trailing zeros, and upper bounds before
quantity parsing is added.

### Price

Prices must support values such as:

```text
234.43
0.000533
```

A future `format_price()` must:

- Remain separate from `format_money()`.
- Preserve meaningful precision.
- Not force exactly two decimal places.
- Avoid Python `float`.

The implementation design must define accepted maximum precision, storage
representation, normalization of trailing zeros, and upper bounds before price
parsing is added.

### Percentages

Portfolio Return retains the existing percentage display behavior. Asset-level
Realized Return should use the same visual percent convention once its
accounting denominator is defined. Zero denominators must have deterministic
behavior and must never cause a runtime error.

## Output and theme

All future asset output must reuse the semantic theme from
`src/fundlog/output/theme.py`. Colors must not be hardcoded.

- Table headers use `TABLE_HEADER`.
- Table borders use `TABLE_BORDER`.
- Normal cells use `TABLE_CELL`.
- Profit values use `PROFIT`.
- Loss values use `LOSS`.
- Income values may use `INFO` when that remains subtle and readable.
- Buy and sell operation labels use normal cell styling.

Asset tables should include a small title or header above the table using the
existing CLI style or the closest clean Rich equivalent, for example:

```text
-- AAPL/stocks --------------------------------
```

Color must not be the only way meaning is communicated.

## Validation and error principles

The detailed error messages remain implementation work, but the future
behavior must follow these principles:

- Portfolio and asset references must resolve to active records.
- Symbol input is normalized case-insensitively and displayed uppercase.
- Symbols reject spaces and `/`.
- Monetary, price, and quantity input must be positive where the operation
  requires a positive value.
- Malformed, non-finite, zero, negative, unsupported-precision, and
  out-of-range numeric input must be rejected as applicable.
- Fees cannot make sell net proceeds negative unless an explicit later design
  permits and explains that behavior.
- Sells cannot exceed open quantity.
- User-provided transaction dates use the shared date helper and cannot be in
  the future.
- Failed commands exit nonzero and leave no partial changes.

## Open design questions

These questions must be resolved and incorporated into the relevant contracts
before implementation:

1. **Trade-total precision:** Should `price × quantity` be rounded to
   two-decimal money using a documented deterministic rounding mode, or should a
   trade be rejected when its exact total cannot be represented in integer
   minor units?
2. **Asset creation:** Should buy and sell require an explicitly existing asset,
   as currently proposed, or may the first buy auto-create it? Silent
   auto-creation increases convenience but weakens explicit asset management.
3. **Fees:** Must `--fee` be supplied for every buy and sell, or should it
   default to zero? If optional, output and stored records must still represent
   zero fees deterministically.
4. **Income ownership:** Must an asset already exist before income can be
   recorded? The current proposed baseline is yes.
5. **Asset deletion:** Should deletion be rejected when an asset has operation
   history or an open quantity, should it archive only the asset while
   preserving its records and derived accounting effects, or should it
   soft-delete the asset and its trades atomically? Removing historical effects
   would alter portfolio totals and needs particularly careful audit semantics.
6. **Partial-sell cost allocation:** Which deterministic minor-unit rounding
   rule should moving-average cost-basis relief use for a partial sell?
7. **Asset Realized Return:** What denominator should the asset-level
   `Realized Return` use? The numerator is realized PnL plus income, but possible
   denominators such as relieved cost basis or cumulative deployed cost have
   different meanings, especially for partially open positions.
8. **Transaction options:** Should buy, sell, and income all expose `--date` and
   `--note` in their first implementation? Regardless of command shape, all
   explicit dates must use the shared date helper.
9. **Reference grammar:** Should portfolio names containing `/` be prohibited
   before asset references are introduced, or should the CLI define escaping?

## Implementation sequence for a later phase

No part of this sequence is authorized by this design document. Once the open
questions are settled and implementation is explicitly requested, work can be
split into reviewable steps:

1. Finalize symbol/reference validation and numeric precision contracts.
2. Finalize moving-average allocation, trade-total rounding, return, and
   deletion semantics.
3. Design storage and migrations without changing existing v0.1 behavior.
4. Add separate exact parsers and formatters for quantity and price.
5. Add asset management behavior.
6. Add buy, sell, and income behavior with shared date validation.
7. Feed derived results into the unchanged portfolio summary columns.
8. Add themed asset list, summary, and log output.
9. Add focused unit, integration, accounting-invariant, and failure-atomicity
   tests.

