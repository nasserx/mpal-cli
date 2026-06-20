# FundLog v0.1 CLI Specification

## Command conventions

- A command names the main action: `create`, `inflow`, `edit`, and so on.
- Options use long names beginning with `--`.
- Short options such as `-x` may be introduced only when they provide clear value.
- Internal database IDs are not part of the CLI contract.
- Capital entry numbers are stable and local to one portfolio.
- Amounts are positive, decimal-safe numbers. Zero, negative, malformed, non-finite, or unsupported-precision amounts must be rejected.
- Explicit dates use ISO format `YYYY-MM-DD` and cannot be in the future. An omitted date uses the current local date.
- A failed command exits nonzero and must not leave partial changes.
- Portfolio uniqueness must be enforced consistently, including whatever case-normalization policy implementation adopts.

## `fundlog init`

**Purpose:** Initialize FundLog's local database.

**Arguments:** None.

**Options:** None in v0.1.

**Behavior:** Creates or prepares local storage and applies known idempotent schema migrations. Re-running against a valid initialized database is safe and does not erase data.

**Validation:** The storage location must be usable and the existing schema, if any, must be recognized.

**Errors:** Inaccessible storage, invalid database, incompatible existing schema, or initialization failure.

## `fundlog create NAME`

Examples:

```console
fundlog create stocks
fundlog create stocks --initial 5000
```

**Purpose:** Create a portfolio, optionally with initial capital.

**Arguments:**

- `NAME`: Required portfolio name.

**Options:**

- `--initial AMOUNT`: Positive amount recorded as the portfolio's initial inflow.

**Behavior:** Without options, creates an empty portfolio. `--initial` creates the portfolio and an inflow entry using the current local date. The operation is atomic.

**Validation:** `NAME` must be nonempty and unique among active portfolios. `--initial` must be a valid positive amount.

**Errors:** FundLog is not initialized; portfolio already exists; invalid initial amount; database failure.

## `fundlog inflow PORTFOLIO AMOUNT`

Examples:

```console
fundlog inflow stocks 1000
fundlog inflow stocks 1000 --date 2026-06-19 --note "initial deposit"
```

**Purpose:** Record capital entering a portfolio.

**Arguments:**

- `PORTFOLIO`: Existing active portfolio.
- `AMOUNT`: Positive inflow amount.

**Options:**

- `--date DATE`: Entry date in `YYYY-MM-DD`.
- `--note TEXT`: Optional note.

**Behavior:** Creates an inflow entry and increases Capital and Cash by `AMOUNT`.

**Validation:** Portfolio must exist and be active; amount and date must be valid. An explicit date cannot be later than the current local date.

**Errors:** FundLog is not initialized; unknown portfolio; invalid amount or date; database failure.

## `fundlog outflow PORTFOLIO AMOUNT`

Examples:

```console
fundlog outflow stocks 250
fundlog outflow stocks 250 --date 2026-06-19 --note "withdrawal"
```

**Purpose:** Record capital leaving a portfolio.

**Arguments:**

- `PORTFOLIO`: Existing active portfolio.
- `AMOUNT`: Positive outflow amount.

**Options:**

- `--date DATE`: Entry date in `YYYY-MM-DD`.
- `--note TEXT`: Optional note.

**Behavior:** Creates an outflow entry and decreases Capital and Cash by `AMOUNT`.

**Validation:** Portfolio must exist and be active; amount and date must be valid; an explicit date cannot be later than the current local date; available Cash must be at least `AMOUNT`.

**Errors:** FundLog is not initialized; unknown portfolio; invalid amount or date; insufficient Cash; database failure.

## `fundlog summary PORTFOLIO`

Example:

```console
fundlog summary stocks
```

**Purpose:** Show the derived summary for one portfolio.

**Arguments:**

- `PORTFOLIO`: Existing active portfolio.

**Options:** None in v0.1.

**Behavior:** Displays one row with `Portfolio`, `Capital`, `Cash`, `Positions`, `Book Value`, `Realized PnL`, `Income`, and `Return`, derived from active recorded entries. The internal portfolio ID is not displayed. Book Value is based only on manual records and is not market value.

**Validation:** Portfolio must exist and be active. `PORTFOLIO` and `--all` are mutually exclusive forms.

**Errors:** FundLog is not initialized; unknown portfolio; database failure.

## `fundlog summary --all`

Example:

```console
fundlog summary --all
```

**Purpose:** Show derived summaries for all active portfolios.

**Arguments:** None.

**Options:**

- `--all`: Select all active portfolios.

**Behavior:** Displays one summary row per active portfolio. An empty result is valid when no portfolios exist.

**Validation:** `--all` cannot be combined with a portfolio argument.

**Errors:** FundLog is not initialized; conflicting arguments; database failure.

## `fundlog log PORTFOLIO`

Example:

```console
fundlog log stocks
```

**Purpose:** Show the capital entries recorded for one portfolio.

**Arguments:**

- `PORTFOLIO`: Existing active portfolio.

**Options:** None in v0.1.

**Behavior:** Displays active inflow and outflow entries with the portfolio-local entry number (`#`), type, amount, date, and note. Internal database IDs are not displayed. Ordering is deterministic by date and then entry number.

**Validation:** Portfolio must exist and be active.

**Errors:** FundLog is not initialized; unknown portfolio; database failure.

## `fundlog edit PORTFOLIO ENTRY_NUMBER`

Examples:

```console
fundlog edit stocks 2 --amount 500
fundlog edit stocks 2 --date 2026-06-19
fundlog edit stocks 2 --note "corrected deposit"
```

**Purpose:** Correct an existing active capital entry within a portfolio.

**Arguments:**

- `PORTFOLIO`: Existing active portfolio.
- `ENTRY_NUMBER`: Existing active portfolio-local entry number.

**Options:**

- `--amount AMOUNT`: Replacement positive amount.
- `--date DATE`: Replacement date in `YYYY-MM-DD`.
- `--note TEXT`: Replacement note.

**Behavior:** Updates only the supplied fields, preserves the portfolio-local entry number and type, recalculates derived balances, and updates the row timestamp. Full before-and-after audit history is future work.

**Validation:** At least one editable option is required. The entry number must exist and be active within `PORTFOLIO`. An entry number from another portfolio is not found. A replacement date cannot be later than the current local date. The resulting active-entry Cash balance must not be negative.

**Errors:** FundLog is not initialized; unknown portfolio; unknown or inactive entry number; no edit option; invalid amount or date; edit would invalidate Cash; database failure.

## `fundlog reset PORTFOLIO --yes`

Examples:

```console
fundlog reset stocks --yes
```

**Purpose:** Clear a portfolio's recorded operations while retaining the portfolio.

**Arguments:**

- `PORTFOLIO`: Existing active portfolio.

**Options:**

- `--yes`: Required confirmation.

**Behavior:** Soft-deletes all active portfolio entries while keeping the portfolio active. The action retains audit-ready metadata.

**Validation:** Portfolio must exist and be active. `--yes` is mandatory.

**Errors:** FundLog is not initialized; missing `--yes`; unknown portfolio; database failure. Without `--yes`, no changes occur.

## `fundlog delete PORTFOLIO ENTRY_NUMBER`

Example:

```console
fundlog delete stocks 2
```

**Purpose:** Soft-delete one active capital entry.

**Arguments:**

- `PORTFOLIO`: Existing active portfolio.
- `ENTRY_NUMBER`: Existing active portfolio-local entry number.

**Options:** None.

**Behavior:** Soft-deletes the selected entry without physically deleting its row. The entry number is never reused.

**Validation:** The entry number must exist and be active within `PORTFOLIO`. Deletion must leave a valid nonnegative Cash balance.

**Errors:** FundLog is not initialized; unknown portfolio; unknown or inactive entry number; deletion would invalidate Cash; database failure.

## `fundlog delete PORTFOLIO --yes`

Example:

```console
fundlog delete stocks --yes
```

**Purpose:** Archive a portfolio from normal user views.

**Arguments:**

- `PORTFOLIO`: Existing active portfolio.

**Options:**

- `--yes`: Required confirmation.

**Behavior:** Atomically soft-deletes the portfolio and all its active capital entries. It preserves every database row and does not affect other portfolios. A deleted portfolio is excluded from summaries and cannot be used by portfolio commands. Because names are unique only among active portfolios, the name may be reused by a new portfolio row, whose entry numbering starts again at 1.

**Validation:** Portfolio must exist and be active. `--yes` is mandatory.

**Errors:** FundLog is not initialized; missing `--yes`; unknown or inactive portfolio; database failure. Without `--yes`, no changes occur.

## `fundlog asset add PORTFOLIO SYMBOL [SYMBOL ...]`

Examples:

```console
fundlog asset add stocks AAPL
fundlog asset add stocks AAPL AMZN MSFT
```

**Purpose:** Add one or more manually tracked symbols to an existing portfolio.

**Arguments:**

- `PORTFOLIO`: Existing active portfolio.
- `SYMBOL`: One or more symbols.

**Options:** None in the asset foundation.

**Behavior:** Normalizes symbols to uppercase and atomically creates active
portfolio-owned assets. A multi-symbol command creates every supplied asset or
none. It does not create trades or change portfolio summary values.

**Validation:** The portfolio must exist and be active. Each normalized symbol
must be 1–32 characters, start with a letter or number, and contain only
letters, numbers, `.`, `-`, or `_`. Symbols are case-insensitive. Duplicate
symbols in one command and symbols already active in the portfolio are rejected.

**Errors:** FundLog is not initialized; unknown portfolio; invalid symbol;
duplicate symbol; active asset already exists; database failure.

## `fundlog asset list PORTFOLIO`

Example:

```console
fundlog asset list stocks
```

**Purpose:** List active assets in one portfolio.

**Arguments:**

- `PORTFOLIO`: Existing active portfolio.

**Options:** None in the asset foundation.

**Behavior:** Displays active assets ordered by uppercase symbol using
`Symbol`, `Quantity`, `Cost Basis`, `Realized PnL`, `Income`, and
`Realized Return`. Quantity, Cost Basis, and Realized PnL remain zero until
buy/sell accounting exists. Income displays the sum of active income
transactions. Realized Return remains `0.00%` while Total Buy Cost is zero.
Internal database IDs are not displayed. An existing portfolio with no assets
prints a deterministic empty-list message.

**Validation:** The portfolio must exist and be active.

**Errors:** FundLog is not initialized; unknown portfolio; database failure.

## `fundlog asset delete PORTFOLIO/SYMBOL --yes`

Example:

```console
fundlog asset delete stocks/AAPL --yes
```

**Purpose:** Soft-delete one active asset from an active portfolio.

**Arguments:**

- `PORTFOLIO/SYMBOL`: Asset reference containing exactly one `/`.

**Options:**

- `--yes`: Required confirmation.

**Behavior:** Normalizes the symbol to uppercase, sets the active asset row's
soft-delete timestamp, and preserves the database row. The deleted asset no
longer appears in `asset list`. The active-only uniqueness rule allows the same
symbol to be added again later. No asset transaction behavior exists in this
phase.

**Validation:** The reference must contain exactly one `/` with a nonempty
portfolio and symbol. The portfolio and asset must both be active. The symbol
uses the normal symbol validation rules. `--yes` is mandatory.

**Errors:** FundLog is not initialized; missing `--yes`; invalid asset
reference; unknown or inactive portfolio; unknown or inactive asset; database
failure. Without `--yes`, no changes occur.

## `fundlog asset log PORTFOLIO/SYMBOL`

Example:

```console
fundlog asset log stocks/AAPL
```

**Purpose:** Show active transactions stored for one active asset.

**Arguments:**

- `PORTFOLIO/SYMBOL`: Asset reference containing exactly one `/`.

**Options:** None in the read-only log foundation.

**Behavior:** Displays the uppercase-symbol title `SYMBOL/portfolio` and the
columns `#`, `Date`, `Type`, `Price`, `Quantity`, `Fee`, `Total`, and `Note`.
Rows are ordered by transaction date and then asset-local entry number. Price
and quantity use their separate precision-aware formatters; Fee and Total use
money formatting. Internal database IDs are not displayed. An asset with no
active transactions prints a deterministic empty-state message.

Income transactions appear in this log. Assets without income or future trade
records show the empty state.

**Validation:** The reference must contain exactly one `/` with a nonempty
portfolio and symbol. The portfolio and asset must both be active. The symbol
uses the normal symbol validation rules.

**Errors:** FundLog is not initialized; invalid asset reference; unknown or
inactive portfolio; unknown or inactive asset; database failure.

## `fundlog income PORTFOLIO/SYMBOL AMOUNT`

Examples:

```console
fundlog income stocks/AAPL 32
fundlog income stocks/AAPL 32 --date 2026-06-20 --note "Dividend"
```

**Purpose:** Record manual income or a distribution for an existing active
asset.

**Arguments:**

- `PORTFOLIO/SYMBOL`: Asset reference containing exactly one `/`.
- `AMOUNT`: Positive money amount.

**Options:**

- `--date DATE`: Transaction date in `YYYY-MM-DD`; defaults to the current local
  date and cannot be in the future.
- `--note TEXT`: Optional note.

**Behavior:** Creates an asset-local `income` transaction with no price,
quantity, or fee. Total, positive cash effect, and income equal `AMOUNT`.
Position effect and realized PnL are zero. The transaction appears in
`asset log`, contributes to the asset list Income column, and increases the
portfolio Cash, Book Value, Income, and realized Return. It does not change
Capital, Positions, Cost Basis, or Realized PnL.

**Validation:** The reference, active portfolio, active asset, amount, and date
must be valid. The amount uses the shared money parser and must be greater than
zero. Explicit dates use the shared date helper.

**Errors:** FundLog is not initialized; invalid asset reference; unknown or
inactive portfolio; unknown or inactive asset; invalid amount or date; database
failure.

## `fundlog buy PORTFOLIO/SYMBOL --price PRICE --quantity QUANTITY`

Examples:

```console
fundlog buy stocks/AAPL --price 234.43 --quantity 3
fundlog buy stocks/AAPL --price 234.43 --quantity 3 --fee 2.30
fundlog buy stocks/AAPL --price 0.000533 --quantity 0.0538 --total 0.01
```

**Purpose:** Record a manual buy for an existing active asset.

**Arguments:**

- `PORTFOLIO/SYMBOL`: Asset reference containing exactly one `/`.

**Required options:**

- `--price PRICE`: Positive exact unit price.
- `--quantity QUANTITY`: Positive exact quantity.

**Optional options:**

- `--fee FEE`: Nonnegative money fee; defaults to `0.00`.
- `--total AMOUNT`: Exact total cash outflow including fees.
- `--date DATE`: Transaction date in `YYYY-MM-DD`; defaults to the current local
  date and cannot be in the future.
- `--note TEXT`: Optional note.

**Behavior:** Records normalized price and quantity text. The buy total is
`price × quantity + fee`; Cash decreases and Positions/Cost Basis increase by
that total. Realized PnL and Income do not change.

Without `--total`, the calculated amount must be exactly representable in
integer minor units. Otherwise the command fails and requests an exact broker
or exchange total. With `--total`, that amount controls the cash and position
effects. If the calculated amount is exactly representable, it must equal the
provided total.

**Validation:** The database, reference, portfolio, asset, price, quantity, fee,
total, and date must be valid. No failed command creates a partial transaction.

**Errors:** FundLog is not initialized; invalid reference; unknown or inactive
portfolio or asset; invalid price, quantity, fee, total, or date; inexact
calculated total without `--total`; exact calculated/provided total mismatch;
database failure.
