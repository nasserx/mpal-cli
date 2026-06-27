# Changelog

## 0.5.2

- Renamed the project identity to `mpal` / `mpal-cli`.
- Cleaned up command consistency around portfolio, capital, and asset groups.
- Added asset current-state commands through `asset list` and `summary -p -a`.
- Added `capital -p` for capital-only current state.
- Added capital entry correction and deletion under `capital entry edit/delete`.
- Added asset entry correction and deletion under `asset entry edit/delete`.
- Added the asset transaction replay foundation.
- Corrected asset transaction edit/delete behavior through replay before commit.
- Added dynamic numeric display formatting.
- Polished terminal theme and table output.
- Added release-readiness metadata, documentation, and local validation scripts.
- Still intentionally excludes live prices, market value, and unrealized PnL.
