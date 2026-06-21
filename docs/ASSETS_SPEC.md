# FundLog Assets Specification

## Scope

FundLog assets are portfolio-owned, manually managed symbols. The implemented
asset model supports:

- symbol creation and soft deletion
- portfolio-wide and single-asset summaries
- read-only transaction logs
- manual income
- manual buys
- manual sells
- moving-average Cost Basis
- Realized PnL
- portfolio Cash, Positions, Book Value, Income, and Return integration

FundLog does not use live prices, market APIs, market value, automatic
valuation, or unrealized PnL.

## CLI contract

Every asset command requires `--portfolio` / `-p`; there is no default
portfolio.

```console
fundlog asset add <symbol> [symbol...] -p <portfolio>
fundlog asset summary -p <portfolio>
fundlog asset summary <symbol> -p <portfolio>
fundlog asset log <symbol> -p <portfolio>
fundlog asset delete <symbol> -p <portfolio> --yes
fundlog asset income <symbol> <amount> -p <portfolio> [--date <date>] [--note <text>]
fundlog asset buy <symbol> -p <portfolio> --price <price> --quantity <quantity> [--fee <fee>] [--total <amount>] [--date <date>] [--note <text>]
fundlog asset sell <symbol> -p <portfolio> --price <price> --quantity <quantity> [--fee <fee>] [--total <amount>] [--date <date>] [--note <text>]
```

The long `--portfolio` spelling is equivalent to `-p`.

The previous combined portfolio/symbol argument form is removed from the
current CLI. `asset list` is also removed. No compatibility or hidden aliases
are retained.

## Symbols and ownership

- Symbols normalize to uppercase.
- Symbols use letters, numbers, `.`, `-`, and `_`, begin with a letter or
  number, and have a maximum length of 32 characters.
- One active normalized symbol may exist in a portfolio.
- The same symbol may exist in different portfolios.
- Multi-symbol add is atomic.
- A symbol may be reused after its earlier asset row is soft-deleted.
- Internal asset IDs are never exposed.

## Persistence

The implemented tables are `assets` and `asset_transactions`.

An asset stores its portfolio owner, normalized symbol, timestamps, and
soft-delete state. Quantities and accounting totals are derived from active
transactions rather than stored on the asset row.

An asset transaction stores:

- asset-local entry number
- type: `buy`, `sell`, or `income`
- effective date
- exact normalized price and quantity text where applicable
- fee and total in integer minor units
- signed Cash effect
- signed Positions/Cost Basis effect
- Realized PnL effect
- Income effect
- optional note
- timestamps and soft-delete state

Transaction numbers are stable within one asset row and are not reused after
soft deletion. Internal row IDs are not part of the CLI.

## Exact numeric rules

- Money uses integer minor units.
- Price and quantity use exact `Decimal` values and normalized decimal text.
- Python `float` is prohibited.
- Scientific notation is rejected.
- Price and quantity permit at most 18 integer and 18 fractional digits.
- Fees are nonnegative money values.
- Income and trade totals are positive money values.
- Explicit dates use strict `YYYY-MM-DD`, cannot be in the future, and default
  to the current local date.

### Buy total

`buy total = price × quantity + fee`

If the calculated value is exactly representable in minor units, FundLog uses
it and requires a supplied `--total` to match. If it is not exactly
representable, the command requires an exact statement value through
`--total`. FundLog does not silently round.

### Sell total

`sell total = price × quantity - fee`

Net proceeds must be positive. The same exact-representation and `--total`
matching rules apply.

## Accounting effects

### Income

An income transaction:

- increases Cash by the amount
- increases Income by the amount
- does not change Capital
- does not change Quantity, Cost Basis, Positions, or Realized PnL

The command name is `income` because assets are generic. A separate dividend
command is not implemented.

### Buy

A buy transaction:

- increases open Quantity
- decreases Cash by exact total cash outflow
- increases Cost Basis and Positions by the same total
- includes buy fees in Cost Basis
- does not change Capital, Income, or Realized PnL

A buy transfers Book Value from Cash to Positions and therefore does not by
itself change Book Value or portfolio Return.

### Sell

A sell transaction:

- requires sufficient open Quantity
- increases Cash by exact net proceeds
- decreases Quantity
- relieves moving-average Cost Basis from Positions
- records `Realized PnL = net proceeds - relieved Cost Basis`
- does not change Capital or Income

For a partial sell:

`relieved Cost Basis = open Cost Basis × sold Quantity / open Quantity`

Fractional-minor-unit allocation uses deterministic round-half-even. A full
sell relieves all remaining Cost Basis so no residual remains.

## Asset summaries

Portfolio-wide summary:

```console
fundlog asset summary -p stocks
```

Columns:

`Asset | Quantity | Cost Basis | Average Cost | Realized PnL | Income | Realized Return`

Single-asset summary:

```console
fundlog asset summary AAPL -p stocks
```

Columns:

`Quantity | Cost Basis | Average Cost | Realized PnL | Income | Realized Return`

Derived values:

- `Quantity = active buys - active sells`
- `Cost Basis = sum of active position effects`
- `Average Cost = Cost Basis / Quantity` when Quantity is positive
- zero Quantity displays `--` for Average Cost
- `Realized PnL = sum of active sell realized-PnL effects`
- `Income = sum of active income effects`
- `Realized Return = (Realized PnL + Income) / Total Buy Cost`
- zero Total Buy Cost displays `0.00%`

Portfolio-wide rows are ordered by normalized symbol.

## Asset log

```console
fundlog asset log AAPL -p stocks
```

Columns:

`# | Date | Type | Price | Quantity | Fee | Total | Note`

Rows order by transaction date and then asset-local entry number. Income rows
display placeholders for Price, Quantity, and Fee.

## Deletion

```console
fundlog asset delete AAPL -p stocks --yes
```

Deletion is soft and atomic:

- the active asset row receives a deletion timestamp
- its active transaction rows receive deletion timestamps
- rows are not physically removed
- deleted effects disappear from asset and portfolio read models
- other assets and portfolios remain unchanged

The command fails without `--yes`.

## Portfolio integration

Active asset transactions contribute to portfolio summaries:

- Cash includes income, buy outflows, and sell proceeds
- Positions includes active buy cost and sell cost relief
- Book Value remains `Cash + Positions`
- Realized PnL includes active sell effects
- Income includes active income effects
- Return remains `(Realized PnL + Income) / Capital`

Assets never appear as extra rows in the portfolio summary. Portfolio
withdrawal and capital-entry edit/delete validation use Cash including active
asset transaction effects.

Soft-deleted assets and transactions do not contribute to current values.

## Non-goals

The asset model does not provide:

- live or automatic prices
- market APIs
- market value
- unrealized PnL
- automatic dividends
- broker synchronization
- currency conversion
- tax-lot selection
- FIFO or LIFO cost basis
