# FundLog v0.1 CLI Specification

## Command conventions

- A command names the main action: `create`, `inflow`, `edit`, and so on.
- Options use long names beginning with `--`.
- Short options such as `-x` may be introduced only when they provide clear value.
- Action-like pseudo-options such as `-inflow`, `-edit`, and `-remove` are not valid.
- Amounts are positive, decimal-safe numbers. Zero, negative, malformed, non-finite, or unsupported-precision amounts must be rejected.
- Explicit dates use ISO format `YYYY-MM-DD`. An omitted date uses the current local date.
- A failed command exits nonzero and must not leave partial changes.
- Portfolio uniqueness must be enforced consistently, including whatever case-normalization policy implementation adopts.

## `fundlog init`

**Purpose:** Initialize FundLog's local database.

**Arguments:** None.

**Options:** None in v0.1.

**Behavior:** Creates or prepares local storage and records the current schema version. Re-running against a valid initialized database is safe and does not erase data.

**Validation:** The storage location must be usable and the existing schema, if any, must be recognized.

**Errors:** Inaccessible storage, invalid database, unsupported schema version, or initialization failure.

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

**Validation:** Portfolio must exist and be active; amount and date must be valid.

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

**Validation:** Portfolio must exist and be active; amount and date must be valid; available Cash must be at least `AMOUNT`.

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

**Behavior:** Displays active inflow and outflow entries with at least entry ID, type, amount, date, and note. Ordering must be deterministic.

**Validation:** Portfolio must exist and be active.

**Errors:** FundLog is not initialized; unknown portfolio; database failure.

## `fundlog edit PORTFOLIO ENTRY_ID`

Examples:

```console
fundlog edit stocks 2 --amount 500
fundlog edit stocks 2 --date 2026-06-19
fundlog edit stocks 2 --note "corrected deposit"
```

**Purpose:** Correct an existing active capital entry within a portfolio.

**Arguments:**

- `PORTFOLIO`: Existing active portfolio.
- `ENTRY_ID`: Existing active entry belonging to that portfolio.

**Options:**

- `--amount AMOUNT`: Replacement positive amount.
- `--date DATE`: Replacement date in `YYYY-MM-DD`.
- `--note TEXT`: Replacement note.

**Behavior:** Updates only the supplied fields, preserves the entry ID and type, recalculates derived balances, and records enough audit information for future audit history.

**Validation:** At least one editable option is required. The entry must belong to `PORTFOLIO` and must not be removed. The resulting ledger must remain valid; in particular, editing must not produce insufficient Cash at any point under the ledger's deterministic ordering.

**Errors:** FundLog is not initialized; unknown portfolio or entry; entry belongs to another portfolio; removed entry; no edit option; invalid amount or date; edit would invalidate Cash; database failure.

## `fundlog remove PORTFOLIO ENTRY_ID`

Example:

```console
fundlog remove stocks 2
```

**Purpose:** Soft-delete a capital entry within a portfolio.

**Arguments:**

- `PORTFOLIO`: Existing active portfolio.
- `ENTRY_ID`: Existing active entry belonging to that portfolio.

**Options:** None in v0.1.

**Behavior:** Marks the entry removed without physically deleting it, recalculates derived balances, and retains audit-ready metadata.

**Validation:** The entry must belong to `PORTFOLIO` and be active. Removing it must leave a valid ledger with no insufficient-Cash state.

**Errors:** FundLog is not initialized; unknown portfolio or entry; entry belongs to another portfolio; entry already removed; removal would invalidate Cash; database failure.

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

**Behavior:** Atomically soft-deletes the portfolio and all its active capital entries. It preserves every database row and does not affect other portfolios. A deleted portfolio is excluded from summaries and cannot be used by portfolio commands. Because names are unique only among active portfolios, the name may be reused by a new portfolio.

**Validation:** Portfolio must exist and be active. `--yes` is mandatory.

**Errors:** FundLog is not initialized; missing `--yes`; unknown or inactive portfolio; database failure. Without `--yes`, no changes occur.
