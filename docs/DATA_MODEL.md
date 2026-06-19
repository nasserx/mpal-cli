# FundLog Planned Data Model

This document describes the database conceptually. It does not prescribe a database engine, SQL schema, migration, or implementation type.

# v0.1 scope

The v0.1 database contains only these conceptual tables:

- `portfolios`
- `portfolio_entries`
- `audit_log`
- `schema_migrations`

## `portfolios`

**Purpose:** Store each user-managed portfolio.

**Important conceptual fields:** Stable ID, name, creation and update timestamps, and active/removal state.

**Relationships:** A portfolio owns zero or more portfolio entries. Audit records may reference it.

**Constraints:**

- `name` is required.
- Portfolio names are unique among active portfolios.
- Removing or resetting records must not create orphaned child records.

## `portfolio_entries`

**Purpose:** Store the operations from which portfolio balances are derived.

**Important conceptual fields:** Stable entry ID, portfolio ID, entry type, decimal-safe amount, effective date, optional note, creation and update timestamps, and soft-delete metadata.

**Relationships:** Every entry belongs to exactly one portfolio. Audit records may identify the entry and its changes.

**Constraints:**

- v0.1 entry types are only `inflow` and `outflow`.
- Amounts are positive and must support exact decimal-safe calculations.
- Entries support soft delete and are not physically removed by the `remove` or `reset` commands.
- Active entries determine current balances.
- Entry changes must preserve enough prior and new state for future audit history.
- Ledger validation must prevent insufficient-Cash outflows.

## `audit_log`

**Purpose:** Preserve an audit-ready history of state-changing actions.

**Important conceptual fields:** Stable audit ID, action, affected record kind and ID, portfolio ID when applicable, before and after state or equivalent change details, action timestamp, and contextual metadata.

**Relationships:** May reference portfolios and portfolio entries while remaining readable even if those records are inactive.

**Constraints:**

- Edits, removals, and resets must be representable.
- Audit records are append-oriented and must not be silently rewritten by ordinary commands.
- A reset must be traceable as one user action even when it affects multiple records.

## `schema_migrations`

**Purpose:** Track database schema evolution across FundLog versions.

**Important conceptual fields:** Migration identifier or version and application timestamp.

**Relationships:** Describes the state of the database schema rather than user portfolio data.

**Constraints:**

- Each migration is applied at most once.
- Applied migrations have a deterministic order.
- Unknown or unsupported schema versions must not be modified blindly.
- The migration mechanism must allow future schema evolution without discarding existing records.

## Relationship summary

```text
portfolios
  └── portfolio_entries

audit_log references affected records and actions
schema_migrations tracks database evolution
```
