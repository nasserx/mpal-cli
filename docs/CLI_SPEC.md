# Multi-Portfolio Asset Ledger CLI Specification

## Command identity

The official executable name is `mpal`. Documentation, help, tests, and
examples must use `mpal`; shell shortcuts are not part of the interface.

mpal is local-first and fully manual. Commands do not fetch prices, call
market APIs, calculate market value, or calculate unrealized PnL.

## Root hierarchy

`mpal --help` exposes only:

- `init`
- `portfolio`
- `capital`
- `asset`

This is a breaking CLI redesign. Earlier root commands are removed, hidden
aliases are removed, and no compatibility aliases are retained.

## Command vocabulary

The command hierarchy standardizes command names around the shape of the data
being shown or modified:

- `list` shows a collection of current things.
- `show` shows the current state/details of one thing.
- `log` shows historical entries or transactions.
- `entry edit` and `entry delete` edit or delete one historical log entry.
- `delete` deletes a whole entity.

`summary` may remain in output titles such as `Portfolio Summary` or `Asset
Summary`, but it is not a command name.

This is a breaking local CLI cleanup. Old command names are removed rather
than retained as compatibility aliases.

## Official commands

### Initialization

```console
mpal init
```

Creates or upgrades the local SQLite database using the existing idempotent
schema checks.

### Portfolio

```console
mpal portfolio create <portfolio> [--initial <amount>]
mpal portfolio list
mpal portfolio show <portfolio>
mpal portfolio delete <portfolio> --yes
mpal portfolio reset <portfolio> --yes
```

- `create` creates an active portfolio. `--initial` atomically creates its
  first capital deposit using the current local date.
- `list` shows every active portfolio using the standard portfolio financial
  summary columns.
- `show` shows one active portfolio using the same summary columns.
- `delete` requires `--yes` and preserves the existing soft-delete behavior.
- `reset` requires `--yes`, soft-deletes active capital entries, and keeps the
  portfolio.

Portfolio summary columns remain:

`Portfolio | Capital | Cash | Positions | Book Value | Realized PnL | Income | Return`

Internal database IDs are never displayed.

### Capital

```console
mpal capital show --portfolio <portfolio>
mpal capital show -p <portfolio>

mpal capital deposit <amount> --portfolio <portfolio> [--date <date>] [--note <text>]
mpal capital deposit <amount> -p <portfolio> [--date <date>] [--note <text>]

mpal capital withdraw <amount> --portfolio <portfolio> [--date <date>] [--note <text>]
mpal capital withdraw <amount> -p <portfolio> [--date <date>] [--note <text>]

mpal capital log --portfolio <portfolio>
mpal capital log -p <portfolio>

mpal capital entry edit <entry-number> --portfolio <portfolio> [--amount <amount>] [--date <date>] [--note <text>]
mpal capital entry edit <entry-number> -p <portfolio> [--amount <amount>] [--date <date>] [--note <text>]

mpal capital entry delete <entry-number> --portfolio <portfolio>
mpal capital entry delete <entry-number> -p <portfolio>
```

`--portfolio` / `-p` is required. There is no default portfolio.

- `show` shows capital-only current state for one active portfolio: deposits,
  withdrawals, and net capital. It should not duplicate full portfolio fields
  such as Positions or Book Value.
- `deposit` records external money added to the portfolio. Storage continues
  to use the existing `inflow` entry type.
- `withdraw` records external money removed from the portfolio. Storage
  continues to use the existing `outflow` entry type.
- Withdrawal validation uses current active Cash, including active asset
  income, buy cash effects, sell proceeds, and soft-delete filtering.
- `log` shows active capital entries.
- `entry edit` requires at least one of `--amount`, `--date`, or `--note`.
- `entry delete` soft-deletes one portfolio-local entry number.

Capital entry numbers are stable within one portfolio and are not internal row
IDs.

The previous `mpal capital edit` and `mpal capital delete` command names are
removed. No compatibility aliases are retained.

### Assets

```console
mpal asset add <symbol> [symbol...] --portfolio <portfolio>
mpal asset add <symbol> [symbol...] -p <portfolio>

mpal asset list

mpal asset list --portfolio <portfolio>
mpal asset list -p <portfolio>

mpal asset show <symbol> --portfolio <portfolio>
mpal asset show <symbol> -p <portfolio>

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
  as the global list and keeps the first column as `A/P` for
  consistent scanning.
- `show <symbol> -p` shows the current state/details for one active asset.
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

`A/P | Quantity | Cost Basis | Average Cost | Realized PnL | Income | Realized Return`

`A/P` means `Asset/Portfolio`. Values use `<SYMBOL>/<portfolio>`, for example
`AAPL/stocks` or `ETHA/etfs`. The same symbol in different portfolios remains
separate rows; assets are not combined globally across portfolios. Internal
database IDs are never displayed.

The one-asset `show` output includes the current fields from the existing
single-asset state view:

`Quantity | Cost Basis | Average Cost | Realized PnL | Income | Realized Return`

Asset log columns remain:

`# | Date | Type | Price | Quantity | Fee | Total | Note`

The `#` value is a stable asset-local transaction number and is not an
internal database ID.

`mpal asset summary`, `mpal asset edit`, and `mpal asset delete-entry` are
removed. No compatibility aliases are retained.

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

`A/P | Quantity | Cost Basis | Average Cost | Realized PnL | Income | Realized Return`

Example:

| A/P | Quantity | Cost Basis | Average Cost | Realized PnL | Income | Realized Return |
|---|---:|---:|---:|---:|---:|---:|
| AAPL/stocks | 3 | 500.00 | 166.67 | +0.00 | 0.00 | +0.00% |

`mpal asset list -p <portfolio>` is the portfolio-scoped current-asset
collection view. It uses the same columns as the global list, including
`A/P`, so users can compare copied output from global and scoped views without
changing mental models. `A/P` means `Asset/Portfolio`.

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
column dividers. Subtle solid data-row separators are presentation-only.

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
mpal summary
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
from legacy asset summary, log, delete, income, buy, and sell commands. Current asset
commands receive the symbol positionally and the portfolio through
`--portfolio` / `-p`.

No hidden alias plan exists for this cleanup.

## Help contract

- Root help lists only the four root commands.
- Help examples use `mpal`.
- Help examples use `--portfolio` / `-p`.
- Help does not advertise removed commands or compatibility aliases.
- Portfolio-scoped command help shows both `--portfolio` and `-p`.
