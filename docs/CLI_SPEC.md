# Multi-Portfolio Asset Ledger CLI Specification

## Command identity

The official executable name is `mpal`. Documentation, help, tests, and
examples must use `mpal`; shell shortcuts are not part of the interface.

mpal is local-first and fully manual. Commands do not fetch prices, call
market APIs, calculate market value, or calculate unrealized PnL.

## Root hierarchy

`mpal --help` exposes only:

- `init`
- `summary`
- `deposit`
- `withdraw`
- `portfolio`
- `capital`
- `asset`

This is a breaking CLI redesign. Earlier root commands are removed, hidden
aliases are removed, and no compatibility aliases are retained.

## Command vocabulary

The command hierarchy standardizes command names around the shape of the data
being shown or modified:

- `list` shows a collection of current things.
- `show` is not used for summary/reporting views; current capital is the
  default `capital -p` view.
- `log` shows historical entries or transactions.
- `entry edit` and `entry delete` edit or delete one historical log entry.
- `delete` deletes a whole entity.

`summary` is the unified summary/reporting command. It is not used inside
`portfolio`, `capital`, or `asset` command groups.

This is a breaking local CLI cleanup. Old command names are removed rather
than retained as compatibility aliases.

## Official commands

### Initialization

```console
mpal init
```

Creates or upgrades the local SQLite database using the existing idempotent
schema checks.

### Summary

```console
mpal summary
mpal summary --portfolio <portfolio>
mpal summary -p <portfolio>
mpal summary --portfolio <portfolio> --asset <asset>
mpal summary -p <portfolio> -a <asset>
```

With no options, shows one global summary table across all active portfolios.
Deleted portfolios and soft-deleted entries or transactions do not contribute.
The command uses existing active-only portfolio summary behavior and does not
display portfolio names or internal database IDs.

Global summary columns are uppercase:

`TOTAL CAPITAL | TOTAL INCOME | REALIZED P&L | RETURN`

Definitions:

- `TOTAL CAPITAL` is active deposits minus active withdrawals across active
  portfolios.
- `TOTAL INCOME` is active asset income across active portfolios.
- `REALIZED P&L` is active realized sell PnL across active portfolios.
- `RETURN` is `(TOTAL INCOME + REALIZED P&L) / TOTAL CAPITAL`, or `0.00%`
  when total capital is zero.

Global return is computed from global totals, not by averaging portfolio
returns. The command does not use live prices, market value, or unrealized
PnL.

`mpal summary -p <portfolio>` shows one active portfolio using the standard
portfolio summary columns:

`Portfolio | Capital | Cash | Positions | Book Value | Realized PnL | Income | Return`

`mpal summary -p <portfolio> -a <asset>` shows one active asset within one
active portfolio using the single-asset summary columns:

`Quantity | Cost Basis | Average Cost | Realized PnL | Income | Realized Return`

Option order is flexible where the CLI parser supports it, so `mpal summary
-a <asset> -p <portfolio>` is valid. `--asset` / `-a` requires `--portfolio` /
`-p`; `mpal summary -a <asset>` fails clearly.

### Portfolio

```console
mpal portfolio create <portfolio> [--initial <amount>]
mpal portfolio list
mpal portfolio delete <portfolio> --yes
mpal portfolio reset <portfolio> --yes
```

- `create` creates an active portfolio. `--initial` atomically creates its
  first capital deposit using the current local date.
- `list` shows every active portfolio using the standard portfolio financial
  summary columns.
- One-portfolio summary output is provided by `mpal summary -p <portfolio>`.
- `delete` requires `--yes` and preserves the existing soft-delete behavior.
- `reset` requires `--yes`, soft-deletes active capital entries, and keeps the
  portfolio.

Portfolio summary columns remain:

`Portfolio | Capital | Cash | Positions | Book Value | Realized PnL | Income | Return`

Internal database IDs are never displayed.

### Daily capital actions

```console
mpal deposit <amount> --portfolio <portfolio> [--date <date>] [--note <text>]
mpal deposit <amount> -p <portfolio> [--date <date>] [--note <text>]

mpal withdraw <amount> --portfolio <portfolio> [--date <date>] [--note <text>]
mpal withdraw <amount> -p <portfolio> [--date <date>] [--note <text>]
```

`--portfolio` / `-p` is required. There is no default portfolio.

- `deposit` records external money added to the portfolio. Storage continues
  to use the existing `inflow` entry type.
- `withdraw` records external money removed from the portfolio. Storage
  continues to use the existing `outflow` entry type.
- Withdrawal validation uses current active Cash, including active asset
  income, buy cash effects, sell proceeds, and soft-delete filtering.

### Capital

```console
mpal capital --portfolio <portfolio>
mpal capital -p <portfolio>

mpal capital log --portfolio <portfolio>
mpal capital log -p <portfolio>

mpal capital entry edit <entry-number> --portfolio <portfolio> [--amount <amount>] [--date <date>] [--note <text>]
mpal capital entry edit <entry-number> -p <portfolio> [--amount <amount>] [--date <date>] [--note <text>]

mpal capital entry delete <entry-number> --portfolio <portfolio>
mpal capital entry delete <entry-number> -p <portfolio>
```

`--portfolio` / `-p` is required. There is no default portfolio.

- `capital -p` shows capital-only current state for one active portfolio:
  deposits, withdrawals, and net capital. It should not duplicate full
  portfolio fields such as Positions or Book Value.
- `log` shows active capital entries.
- `entry edit` requires at least one of `--amount`, `--date`, or `--note`.
- `entry delete` soft-deletes one portfolio-local entry number.

Capital entry numbers are stable within one portfolio and are not internal row
IDs.

The previous `mpal capital show`, `mpal capital deposit`,
`mpal capital withdraw`, `mpal capital edit`, and `mpal capital delete`
command names are removed. `capital show`, `capital deposit`, and
`capital withdraw` were removed before public release because current capital
review is `capital -p` and daily capital actions are top-level `deposit` and
`withdraw` commands. No compatibility aliases are retained.

### Assets

```console
mpal asset add <symbol> [symbol...] --portfolio <portfolio>
mpal asset add <symbol> [symbol...] -p <portfolio>

mpal asset list

mpal asset list --portfolio <portfolio>
mpal asset list -p <portfolio>

mpal asset log <symbol> --portfolio <portfolio>
mpal asset log <symbol> -p <portfolio>

mpal asset delete <symbol> --portfolio <portfolio> --yes
mpal asset delete <symbol> -p <portfolio> --yes

mpal asset entry edit <symbol> <entry-number> --portfolio <portfolio> [--amount <amount>] [--price <price>] [--quantity <quantity>] [--fee <fee>] [--total <amount>] [--date <date>] [--note <text>]
mpal asset entry edit <symbol> <entry-number> -p <portfolio> [--amount <amount>] [--price <price>] [--quantity <quantity>] [--fee <fee>] [--total <amount>] [--date <date>] [--note <text>]

mpal asset entry delete <symbol> <entry-number> --portfolio <portfolio> --yes
mpal asset entry delete <symbol> <entry-number> -p <portfolio> --yes

mpal asset income <symbol> <amount> --portfolio <portfolio> [--date <date>] [--note <text>]
mpal asset income <symbol> <amount> -p <portfolio> [--date <date>] [--note <text>]

mpal asset buy <symbol> --portfolio <portfolio> --price <price> --quantity <quantity> [--fee <fee>] [--total <amount>] [--date <date>] [--note <text>]
mpal asset buy <symbol> -p <portfolio> --price <price> --quantity <quantity> [--fee <fee>] [--total <amount>] [--date <date>] [--note <text>]

mpal asset sell <symbol> --portfolio <portfolio> --price <price> --quantity <quantity> [--fee <fee>] [--total <amount>] [--date <date>] [--note <text>]
mpal asset sell <symbol> -p <portfolio> --price <price> --quantity <quantity> [--fee <fee>] [--total <amount>] [--date <date>] [--note <text>]
```

`--portfolio` / `-p` is required when an asset command targets one specific
portfolio. The global `mpal asset list` view omits `-p`. Symbols normalize to
uppercase through the shared symbol validator.

- `add` creates one or more symbols atomically.
- `list` without `-p` shows all active assets across all active portfolios,
  aggregated by asset within each portfolio.
- `list -p` shows all active assets in one portfolio. It uses the same columns
  as the global list and keeps the first column as `Asset/Portfolio` for
  consistent scanning.
- One-asset summary output is provided by
  `mpal summary -p <portfolio> -a <asset>`.
- `log` shows one asset's active transactions.
- `delete` requires `--yes` and soft-deletes the asset and its active
  transactions.
- `entry delete` requires `--yes`, soft-deletes one active transaction by
  asset-local entry number, replays the remaining active transactions in
  `entry_no` order, and updates derived transaction accounting fields
  atomically.
- `entry edit` updates one active transaction by asset-local entry number,
  keeps the transaction type unchanged, replays all active transactions in
  `entry_no` order, and updates derived transaction accounting fields
  atomically.
- `income` records generic manually entered asset income.
- `buy` records exact manual buy values.
- `sell` records exact manual sell values and uses the existing moving-average
  cost-basis relief.

The global and portfolio-scoped asset list columns are:

`Asset/Portfolio | Quantity | Cost Basis | Average Cost | Realized PnL | Income | Realized Return`

Combined labels display as `<SYMBOL> • <Portfolio>`, for example
`AAPL • Stocks` or `ETHA • Etfs`. The portfolio name capitalization in this
combined label is display-only; command syntax and lookup still use
`-p <portfolio>`. The same symbol in different portfolios remains separate
rows; assets are not combined globally across portfolios. Internal database
IDs are never displayed.

The one-asset `summary -p <portfolio> -a <asset>` output includes the current
fields from the existing single-asset state view:

`Quantity | Cost Basis | Average Cost | Realized PnL | Income | Realized Return`

Asset log columns remain:

`# | Date | Type | Price | Quantity | Fee | Total | Note`

The `#` value is a stable asset-local transaction number and is not an
internal database ID.

`mpal portfolio show`, `mpal asset show`, `mpal asset summary`,
`mpal asset edit`, and `mpal asset delete-entry` are removed. `portfolio show`
and `asset show` were removed before public release because `summary` now owns
all summary/reporting views. No compatibility aliases are retained.

### Asset transaction correction

The individual asset transaction correction commands are:

```console
mpal asset entry edit <symbol> <entry-number> --portfolio <portfolio> [options...]
mpal asset entry edit <symbol> <entry-number> -p <portfolio> [options...]

mpal asset entry delete <symbol> <entry-number> --portfolio <portfolio> --yes
mpal asset entry delete <symbol> <entry-number> -p <portfolio> --yes
```

`entry-number` is the asset-local number displayed by the asset log for the
same symbol and portfolio. Internal database IDs must not be accepted or
displayed.

`entry edit` behavior:

- `income` rows may edit amount, date, and note.
- `buy` rows may edit price, quantity, fee, total, date, and note.
- `sell` rows may edit price, quantity, fee, total, date, and note.
- Transaction type cannot be changed.
- At least one editable option is required.
- Existing money, price, quantity, and date validation applies.
- Future dates, invalid amounts, invalid totals, and recalculation failures are
  rejected.
- Buy and sell total validation keeps the current exact-total rules.

`entry delete` behavior:

- Requires an active portfolio, active asset, active transaction, and `--yes`.
- Soft-deletes only the transaction row.
- Does not delete the asset.
- Preserves database rows.
- Replays the remaining active asset ledger and rejects the deletion if the
  remaining ledger would be invalid.

Accounting replay for correction commands uses asset-local `entry_no` order.
The displayed asset log continues to sort by transaction date and then entry
number.

## Asset list output

`mpal asset list` is the global current-asset collection view. It does not
require `-p` and includes active assets only.

Rows are grouped at the asset-within-portfolio level. The same symbol in two
portfolios is shown as two rows, not one combined row.

Columns:

`Asset/Portfolio | Quantity | Cost Basis | Average Cost | Realized PnL | Income | Realized Return`

Example:

| Asset/Portfolio | Quantity | Cost Basis | Average Cost | Realized PnL | Income | Realized Return |
|---|---:|---:|---:|---:|---:|---:|
| AAPL • Stocks | 3 | 500.00 | 166.67 | +0.00 | 0.00 | +0.00% |

`mpal asset list -p <portfolio>` is the portfolio-scoped current-asset
collection view. It uses the same columns as the global list, including
`Asset/Portfolio`, so users can compare copied output from global and scoped
views without changing mental models. Combined labels display as
`<SYMBOL> • <Portfolio>`; the portfolio capitalization is display-only.

Formatting rules:

- Quantity uses the dynamic quantity display helper.
- `Average Cost` uses the dynamic price display helper.
- `Cost Basis`, `Realized PnL`, and `Income` use money display.
- `Realized PnL` and `Realized Return` use existing signed display.
- Positive PnL/return values use the profit style, negative values use the
  loss style, and income values use the income style.
- Tables use the existing rounded row-oriented table helper and centralized
  terminal theme, with subtle inset solid separators between data rows.
- Raw `Decimal` output and internal database IDs are never displayed.

## Shared input rules

- Money is parsed with the shared exact minor-unit parser.
- Price and quantity use exact decimal parsing and never Python `float`.
- Explicit dates use strict `YYYY-MM-DD`, cannot be in the future, and default
  to the current local date when omitted.
- Notes are optional text.
- Expected application errors are concise and do not print tracebacks.
- Failed atomic operations do not leave partial records.

User-facing numeric output uses explicit display helpers:

- Money fields use thousands separators and exactly two decimal places.
- Quantity fields use thousands separators and dynamic decimal precision
  without padded trailing zeros.
- Price fields and `Average Cost` use a price display scale inferred from the
  active asset's buy/sell prices, with at least two decimal places.
- Display rounding is presentation-only; internal accounting remains exact.

Terminal styling is presentation-only. Rich output uses centralized semantic
theme styles for headers, normal values, profit/loss, income/info, warnings,
errors, borders, and muted note text. Data tables use a shared rounded,
row-oriented layout with a header separator and without internal vertical
column dividers. Subtle solid data-row separators connect to the outer table
borders without adding internal column dividers. Row identity/key values in
first columns such as `#`, `Portfolio`, `Asset`, `Symbol`, and
`Asset/Portfolio` use a calm orange semantic style. These choices are
presentation-only.
Tables also use a centralized standard width policy so narrow current-state
tables and wider log/list tables share a consistent visual width where the
terminal allows it, while still responding to smaller terminal widths.

Trade totals retain the existing behavior:

- buy total: `price × quantity + fee`
- sell total: `price × quantity - fee`
- exactly representable calculated totals must match `--total` when supplied
- inexact minor-unit calculations require the exact broker/exchange `--total`
- no silent rounding is allowed

## Removed interface

The following commands and shapes must fail rather than delegate:

```text
mpal create
mpal reset
mpal delete
mpal inflow
mpal outflow
mpal log
mpal edit
mpal income
mpal buy
mpal sell
```

The previous combined portfolio/symbol positional argument is also removed
from legacy asset summary, log, delete, income, buy, and sell commands. Current
asset commands receive the symbol positionally and the portfolio through
`--portfolio` / `-p`.

The previous summary-style commands `mpal portfolio show <portfolio>` and
`mpal asset show <asset> -p <portfolio>` are removed before public release.
Use `mpal summary -p <portfolio>` and `mpal summary -p <portfolio> -a <asset>`
instead.

The previous nested capital forms `mpal capital show -p <portfolio>`,
`mpal capital deposit <amount> -p <portfolio>`, and
`mpal capital withdraw <amount> -p <portfolio>` are removed before public
release. Use `mpal capital -p <portfolio>`, `mpal deposit <amount> -p
<portfolio>`, and `mpal withdraw <amount> -p <portfolio>` instead.

No hidden alias plan exists for this cleanup.

## Help contract

- Root help lists only the seven root commands.
- Help examples use `mpal`.
- Help examples use `--portfolio` / `-p`.
- Help does not advertise removed commands or compatibility aliases.
- Portfolio-scoped command help shows both `--portfolio` and `-p`.
- Summary help documents global, portfolio, and portfolio-asset forms, and
  states that `--asset` requires `--portfolio`.
- Capital help documents the default `mpal capital -p <portfolio>` view, `log`,
  and `entry edit/delete`; it does not advertise removed nested daily actions.
