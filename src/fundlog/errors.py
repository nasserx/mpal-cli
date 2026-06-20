"""FundLog exception types."""


class FundLogError(Exception):
    """Base exception for expected FundLog errors."""


class DatabaseNotInitializedError(FundLogError):
    """Raised when a command requires an initialized database."""


class StorageError(FundLogError):
    """Raised when SQLite cannot complete a storage operation safely."""


class PortfolioAlreadyExistsError(FundLogError):
    """Raised when an active portfolio name is already in use."""


class InvalidPortfolioNameError(FundLogError):
    """Raised when a portfolio name is empty."""


class PortfolioNotFoundError(FundLogError):
    """Raised when an active portfolio cannot be found."""


class InvalidSymbolError(FundLogError):
    """Raised when an asset symbol is invalid."""


class AssetAlreadyExistsError(FundLogError):
    """Raised when an active asset symbol already exists in a portfolio."""


class InvalidAssetReferenceError(FundLogError):
    """Raised when a portfolio/symbol asset reference is invalid."""


class AssetNotFoundError(FundLogError):
    """Raised when an active asset cannot be found in an active portfolio."""


class InvalidAmountError(FundLogError):
    """Raised when a monetary amount is invalid."""


class InvalidQuantityError(FundLogError):
    """Raised when an asset quantity is invalid."""


class InvalidPriceError(FundLogError):
    """Raised when an asset unit price is invalid."""


class InvalidTradeTotalError(FundLogError):
    """Raised when a trade cash total is inexact or inconsistent."""


class InvalidEntryDateError(FundLogError):
    """Raised when a capital entry date is invalid."""


class InsufficientCashError(FundLogError):
    """Raised when an outflow exceeds available portfolio cash."""


class CapitalEntryNotFoundError(FundLogError):
    """Raised when a capital entry does not exist or is inactive."""


class InvalidLedgerEditError(FundLogError):
    """Raised when an edit would make the active ledger invalid."""


class InvalidLedgerDeleteError(FundLogError):
    """Raised when entry deletion would make the active ledger invalid."""
