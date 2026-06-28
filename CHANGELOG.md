# Changelog

## 0.6.0

- Added `mpal portfolio allocation` to show active portfolio allocation by
  book value.
- Allocation uses `BOOK VALUE = TOTAL CASH + POSITIONS`; it is not based on
  capital, cash alone, market value, live prices, or unrealized PnL.
- Polished `mpal asset list` `Asset/Portfolio` labels so the asset symbol keeps
  the key style and the portfolio name uses a muted style.

## 0.5.2

- Renamed the project identity to `mpal` / `mpal-cli`.
- Cleaned up command consistency around portfolio, capital, and asset groups.
- Added asset current-state commands through `asset list` and `summary -p -a`.
- Added `capital -p` for capital-only current state.
- Expanded global `summary` with total cash, positions, book value, and
  optional `--explain` definitions.
- Added capital entry correction and deletion under `capital entry edit/delete`.
- Added asset entry correction and deletion under `asset entry edit/delete`.
- Added the asset transaction replay foundation.
- Corrected asset transaction edit/delete behavior through replay before commit.
- Added dynamic numeric display formatting.
- Polished terminal theme and table output.
- Added release-readiness metadata, documentation, and local validation scripts.
- Still intentionally excludes live prices, market value, and unrealized PnL.
