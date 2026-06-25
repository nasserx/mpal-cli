# mpal Data Model

This document describes the implemented SQLite model and planned future audit
infrastructure.

Portfolio and asset summaries are derived from manual records rather than
stored balances. The schema does not store market value, live prices, derived
positions, or derived returns. Implemented manual asset transactions provide
the inputs for Cost Basis, Realized PnL, Income, and Return without introducing
market APIs.

The asset design is specified in `docs/ASSETS_SPEC.md`. The `assets` and
`asset_transactions` tables are implemented. Asset income, buy, and sell
commands create asset transactions. Their active effects contribute to asset
summaries and portfolio summaries. Monetary fields use integer minor units.
User-entered quantity and price fields use normalized decimal text, never
SQLite floating point or Python `float`.

## Implemented scope

The implemented database contains:

- `portfolios`
- `capital_entries`
- `assets`
- `asset_transactions`

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
- New portfolio names continue to reject `/` under the existing validation
  contract. The CLI no longer combines portfolio and symbol into one argument.
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
- Ledger validation must prevent insufficient-Cash withdrawals.

## `assets`

**Purpose:** Store normalized symbols owned by portfolios.

**Important fields:** Internal stable ID, portfolio ID, normalized symbol,
creation and update timestamps, and soft-delete state.

**Relationships:** Every asset belongs to exactly one portfolio.

**Constraints:**

- Symbols are stored uppercase.
- One active asset per normalized symbol may exist within a portfolio.
- The same symbol may exist in different portfolios.
- Active-only uniqueness allows a symbol to be reused after a previous asset row
  is soft-deleted.
- `asset delete` atomically soft-deletes the asset and its active transaction
  rows without removing them.
- Active asset queries exclude soft-deleted rows.
- Internal asset IDs are not exposed by the CLI.
- Portfolio-wide asset summaries are ordered by symbol.
- The table contains no quantity, price, fee, trade, income, market-value, or
  unrealized-PnL fields.

## Future `audit_log`

**Purpose:** Preserve an audit-ready history of state-changing actions.

**Important conceptual fields:** Stable audit ID, action, affected record kind and ID, portfolio ID when applicable, before and after state or equivalent change details, action timestamp, and contextual metadata.

**Relationships:** May reference portfolios and portfolio entries while remaining readable even if those records are inactive.

**Constraints:**

- Edits, entry deletions, resets, and portfolio deletions must be representable.
- Audit records are append-oriented and must not be silently rewritten by ordinary commands.
- A reset must be traceable as one user action even when it affects multiple records.

## `asset_transactions`

**Purpose:** Store manual asset transactions and support the asset log and
derived accounting.

**Important fields:** Internal stable ID, asset ID, asset-local entry number,
transaction type, effective date, nullable exact price and quantity text, fee
and total money, signed cash and position effects, realized PnL, income, note,
timestamps, and soft-delete state.

**Relationships:** Every transaction belongs to exactly one asset.

**Constraints:**

- Allowed transaction types are `buy`, `sell`, and `income`.
- Entry numbers start at 1 independently for each asset row.
- `(asset_id, entry_no)` is fully unique, so numbers are not reused after soft
  deletion.
- Price and quantity are nullable for income rows and use exact decimal text
  when present.
- Fee, Total, cash effect, position effect, realized PnL, and income are integer
  minor units.
- Cash, position, and realized-PnL effects may be signed.
- Fee and income fields are nonnegative.
- Rows support soft delete and active log queries exclude deleted rows.
- Asset logs order rows by transaction date and then entry number.
- Internal IDs are not exposed by the CLI.
- The table contains no market value or unrealized PnL.
- Individual transaction correction preserves row identity and asset-local
  entry numbers. `asset edit` updates one active row in place. `asset
  delete-entry` soft-deletes one active row only. Both commands recalculate
  affected active transaction accounting fields. Neither command hard-deletes
  rows or exposes internal IDs.
- Correction replay uses active transactions in asset-local `entry_no` order.
  Display order may remain transaction date then entry number.

The asset income command inserts `income` rows with null price and quantity,
zero fee, positive total/cash/income fields, and zero
position/realized-PnL fields. Asset buy inserts normalized price and quantity,
a nonnegative fee, positive total and position effect, negative cash effect,
and zero realized-PnL and income fields. Asset sell inserts normalized price
and quantity, a nonnegative fee, positive net total and cash effect, negative
relieved-cost position effect, calculated Realized PnL, and zero income.
Portfolio summaries read all active transaction effects.

For edits, `transaction_type` is immutable. Income rows keep null price and
quantity, zero fee, zero position effect, and zero realized-PnL. Buy and sell
rows keep exact normalized price and quantity text, exact integer minor unit
fee and total fields, and recalculated cash, position, and realized-PnL effects
according to the replay rules in `docs/FINANCIAL_MODEL.md`.

## Future `schema_migrations`

**Purpose:** Track database schema evolution across mpal versions.

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
  ├── capital_entries
  └── assets
       └── asset_transactions

future audit_log records affected records and actions
future schema_migrations tracks database evolution
```
