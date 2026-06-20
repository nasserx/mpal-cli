# FundLog Data Model

This document describes the implemented v0.1 SQLite model and planned future
audit infrastructure.

Portfolio summaries are derived from manual records rather than stored balances. The v0.1 schema does not store market value, live prices, positions, realized PnL, income, or return. Future manual trading records may provide inputs for those calculations without introducing market APIs.

## v0.1 scope

The implemented v0.1 database contains:

- `portfolios`
- `capital_entries`

`audit_log` and `schema_migrations` remain future design concepts; they are not
implemented v0.1 tables. Current migrations are small, idempotent schema checks
applied during initialization and normal database access.

## `portfolios`

**Purpose:** Store each user-managed portfolio.

**Important conceptual fields:** Internal stable ID, name, creation and update timestamps, and soft-delete state.

**Relationships:** A portfolio owns zero or more portfolio entries. Audit records may reference it.

**Constraints:**

- `name` is required.
- Portfolio names are unique among active portfolios.
- Portfolios support soft delete and are not physically removed by `delete`.
- Deleting a portfolio also soft-deletes its active capital entries atomically.
- A deleted portfolio name may be reused because uniqueness applies only to active portfolios.
- Deleting entries or resetting a portfolio must not create orphaned child records.

## `capital_entries`

**Purpose:** Store the operations from which portfolio balances are derived.

**Important conceptual fields:** Internal stable ID, portfolio ID, portfolio-local entry number, entry type, decimal-safe amount, effective date, optional note, creation and update timestamps, and soft-delete metadata.

**Relationships:** Every entry belongs to exactly one portfolio. Audit records may identify the entry and its changes.

**Constraints:**

- v0.1 entry types are only `inflow` and `outflow`.
- Entry numbers start at 1 independently for each portfolio row.
- Entry numbers are unique within a portfolio and are not reused after soft delete or reset.
- Internal database IDs are never exposed as user-facing entry numbers.
- Initialization idempotently adds and backfills missing entry numbers for older databases, ordered by internal ID within each portfolio.
- Amounts are positive and must support exact decimal-safe calculations.
- Entries support soft delete and are not physically removed by entry `delete`, `reset`, or portfolio `delete`.
- Active entries determine current balances.
- Entry rows and timestamps are retained for future audit tooling.
- Ledger validation must prevent insufficient-Cash outflows.

## Future `audit_log`

**Purpose:** Preserve an audit-ready history of state-changing actions.

**Important conceptual fields:** Stable audit ID, action, affected record kind and ID, portfolio ID when applicable, before and after state or equivalent change details, action timestamp, and contextual metadata.

**Relationships:** May reference portfolios and portfolio entries while remaining readable even if those records are inactive.

**Constraints:**

- Edits, entry deletions, resets, and portfolio deletions must be representable.
- Audit records are append-oriented and must not be silently rewritten by ordinary commands.
- A reset must be traceable as one user action even when it affects multiple records.

## Future `schema_migrations`

**Purpose:** Track database schema evolution across FundLog versions.

**Important conceptual fields:** Migration identifier or version and application timestamp.

**Relationships:** Describes the state of the database schema rather than user portfolio data.

**Constraints:**

- Each tracked migration is applied at most once.
- Applied migrations have a deterministic order.
- Unknown or unsupported schema versions must not be modified blindly.
- The migration mechanism must allow future schema evolution without discarding existing records.

## Relationship summary

```text
portfolios
  └── capital_entries

future audit_log records affected records and actions
future schema_migrations tracks database evolution
```
