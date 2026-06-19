# FundLog v0.1 Financial Model

## Principles

FundLog derives every financial result from active recorded operations. v0.1 records only portfolio capital inflows and outflows. Financial amounts must use decimal-safe logic when implemented and must not use binary floating point.

## Summary table

The summary output has these columns:

| id | Portfolio | Capital | Cash | Invested | Value | PnL | Return |
|---:|---|---:|---:|---:|---:|---:|---:|

Their definitions are:

- **Capital** = total active inflows - total active outflows.
- **Cash** = available cash in the portfolio after active recorded operations.
- **Invested** = `0` in v0.1 because symbols and investment operations are not implemented yet.
- **Value** = Cash + Invested.
- **PnL** = `0` or N/A in v0.1 because investment operations are not implemented yet.
- **Return** = `0` or N/A in v0.1 because PnL is not available yet.

An implementation must choose one consistent v0.1 presentation for unavailable PnL and Return values. It must not imply market performance where none has been recorded.

## Entry rules

- An inflow increases Capital and Cash by the same amount.
- An outflow decreases Capital and Cash by the same amount.
- An outflow is rejected if Cash is insufficient.
- An outflow does not affect PnL.
- Entry removal is a soft delete.
- Portfolio reset soft-deletes portfolio entries.
- Reset requires the `--yes` confirmation option.
- Active entries alone contribute to current calculations.
- Edits, removals, and resets must retain enough information to support future auditing.
- Edits and removals must not leave a ledger state where an outflow exceeds available Cash under deterministic entry ordering.
- In v0.1, because only capital operations exist, Invested is `0` and Value normally equals Cash. If entries are removed or edited, all figures are recalculated from the remaining active records; no alternate Value is introduced.
- FundLog must not invent market value or any price-based valuation.

## Example scenarios

### Create a portfolio with an initial inflow

```console
fundlog create stocks --initial 5000
```

Result:

- Capital: `5000`
- Cash: `5000`
- Invested: `0`
- Value: `5000`
- PnL: `0` or N/A
- Return: `0` or N/A

### Add an inflow

Starting with Cash and Capital of `5000`:

```console
fundlog inflow stocks 1000
```

Result: Capital and Cash both become `6000`.

### Add an outflow with sufficient Cash

Starting with Cash and Capital of `6000`:

```console
fundlog outflow stocks 250
```

Result: Capital and Cash both become `5750`. PnL is unchanged.

### Attempt an outflow with insufficient Cash

Starting with Cash of `5750`:

```console
fundlog outflow stocks 6000
```

Result: the command fails, no entry is created, and all balances remain unchanged.

### Summary before trading features exist

For the preceding successful entries:

| id | Portfolio | Capital | Cash | Invested | Value | PnL | Return |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | stocks | 5750 | 5750 | 0 | 5750 | 0 or N/A | 0 or N/A |

The summary is ledger-derived. It contains no market price or manually entered portfolio value.
