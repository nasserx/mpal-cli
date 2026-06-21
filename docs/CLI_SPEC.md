# FundLog CLI Specification

## Command identity

The official executable name is `fundlog`. Documentation, help, tests, and
examples must use `fundlog`; shell shortcuts are not part of the interface.

FundLog is local-first and fully manual. Commands do not fetch prices, call
market APIs, calculate market value, or calculate unrealized PnL.

## Root hierarchy

`fundlog --help` exposes only:

- `init`
- `portfolio`
- `capital`
- `asset`

This is a breaking CLI redesign. Earlier root commands are removed, hidden
aliases are removed, and no compatibility aliases are retained.

## Official commands

### Initialization

```console
fundlog init
```

Creates or upgrades the local SQLite database using the existing idempotent
schema checks.

### Portfolio

```console
fundlog portfolio create <portfolio> [--initial <amount>]
fundlog portfolio list
fundlog portfolio show <portfolio>
fundlog portfolio delete <portfolio> --yes
fundlog portfolio reset <portfolio> --yes
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
fundlog capital deposit <amount> --portfolio <portfolio> [--date <date>] [--note <text>]
fundlog capital deposit <amount> -p <portfolio> [--date <date>] [--note <text>]

fundlog capital withdraw <amount> --portfolio <portfolio> [--date <date>] [--note <text>]
fundlog capital withdraw <amount> -p <portfolio> [--date <date>] [--note <text>]

fundlog capital log --portfolio <portfolio>
fundlog capital log -p <portfolio>

fundlog capital edit <entry-number> --portfolio <portfolio> [--amount <amount>] [--date <date>] [--note <text>]
fundlog capital edit <entry-number> -p <portfolio> [--amount <amount>] [--date <date>] [--note <text>]

fundlog capital delete <entry-number> --portfolio <portfolio>
fundlog capital delete <entry-number> -p <portfolio>
```

`--portfolio` / `-p` is required. There is no default portfolio.

- `deposit` records external money added to the portfolio. Storage continues
  to use the existing `inflow` entry type.
- `withdraw` records external money removed from the portfolio. Storage
  continues to use the existing `outflow` entry type.
- Withdrawal validation uses current active Cash, including active asset
  income, buy cash effects, sell proceeds, and soft-delete filtering.
- `log` shows active capital entries.
- `edit` requires at least one of `--amount`, `--date`, or `--note`.
- `delete` soft-deletes one portfolio-local entry number.

Capital entry numbers are stable within one portfolio and are not internal row
IDs.

### Assets

```console
fundlog asset add <symbol> [symbol...] --portfolio <portfolio>
fundlog asset add <symbol> [symbol...] -p <portfolio>

fundlog asset summary --portfolio <portfolio>
fundlog asset summary -p <portfolio>

fundlog asset summary <symbol> --portfolio <portfolio>
fundlog asset summary <symbol> -p <portfolio>

fundlog asset log <symbol> --portfolio <portfolio>
fundlog asset log <symbol> -p <portfolio>

fundlog asset delete <symbol> --portfolio <portfolio> --yes
fundlog asset delete <symbol> -p <portfolio> --yes

fundlog asset income <symbol> <amount> --portfolio <portfolio> [--date <date>] [--note <text>]
fundlog asset income <symbol> <amount> -p <portfolio> [--date <date>] [--note <text>]

fundlog asset buy <symbol> --portfolio <portfolio> --price <price> --quantity <quantity> [--fee <fee>] [--total <amount>] [--date <date>] [--note <text>]
fundlog asset buy <symbol> -p <portfolio> --price <price> --quantity <quantity> [--fee <fee>] [--total <amount>] [--date <date>] [--note <text>]

fundlog asset sell <symbol> --portfolio <portfolio> --price <price> --quantity <quantity> [--fee <fee>] [--total <amount>] [--date <date>] [--note <text>]
fundlog asset sell <symbol> -p <portfolio> --price <price> --quantity <quantity> [--fee <fee>] [--total <amount>] [--date <date>] [--note <text>]
```

`--portfolio` / `-p` is required for every asset command. Symbols normalize to
uppercase through the shared symbol validator.

- `add` creates one or more symbols atomically.
- `summary -p` shows all active asset summaries in symbol order.
- `summary <symbol> -p` shows one active asset summary.
- `log` shows one asset's active transactions.
- `delete` requires `--yes` and soft-deletes the asset and its active
  transactions.
- `income` records generic manually entered asset income.
- `buy` records exact manual buy values.
- `sell` records exact manual sell values and uses the existing moving-average
  cost-basis relief.

Asset summary columns remain:

`Asset | Quantity | Cost Basis | Average Cost | Realized PnL | Income | Realized Return`

The one-asset summary omits the `Asset` column because the symbol is selected
by the command.

Asset log columns remain:

`# | Date | Type | Price | Quantity | Fee | Total | Note`

## Shared input rules

- Money is parsed with the shared exact minor-unit parser.
- Price and quantity use exact decimal parsing and never Python `float`.
- Explicit dates use strict `YYYY-MM-DD`, cannot be in the future, and default
  to the current local date when omitted.
- Notes are optional text.
- Expected application errors are concise and do not print tracebacks.
- Failed atomic operations do not leave partial records.

Trade totals retain the existing behavior:

- buy total: `price × quantity + fee`
- sell total: `price × quantity - fee`
- exactly representable calculated totals must match `--total` when supplied
- inexact minor-unit calculations require the exact broker/exchange `--total`
- no silent rounding is allowed

## Removed interface

The following commands and shapes must fail rather than delegate:

```text
fundlog create
fundlog summary
fundlog reset
fundlog delete
fundlog inflow
fundlog outflow
fundlog log
fundlog edit
fundlog income
fundlog buy
fundlog sell
fundlog asset list
```

The previous combined portfolio/symbol positional argument is also removed
from asset summary, log, delete, income, buy, and sell commands. Current asset
commands receive the symbol positionally and the portfolio through
`--portfolio` / `-p`.

No hidden alias plan exists in this branch.

## Help contract

- Root help lists only the four root commands.
- Help examples use `fundlog`.
- Help examples use `--portfolio` / `-p`.
- Help does not advertise removed commands or compatibility aliases.
- Portfolio-scoped command help shows both `--portfolio` and `-p`.
