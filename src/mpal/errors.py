"""mpal exception types."""


class MpalError(Exception):
    """Base exception for expected mpal errors."""


class DatabaseNotInitializedError(MpalError):
    """Raised when a command requires an initialized database."""


class StorageError(MpalError):
    """Raised when SQLite cannot complete a storage operation safely."""


class PortfolioAlreadyExistsError(MpalError):
    """Raised when an active portfolio name is already in use."""


class InvalidPortfolioNameError(MpalError):
    """Raised when a portfolio name is empty."""


class PortfolioNotFoundError(MpalError):
    """Raised when an active portfolio cannot be found."""


class InvalidSymbolError(MpalError):
    """Raised when an asset symbol is invalid."""


class AssetAlreadyExistsError(MpalError):
    """Raised when an active asset symbol already exists in a portfolio."""


class AssetNotFoundError(MpalError):
    """Raised when an active asset cannot be found in an active portfolio."""


class InvalidAmountError(MpalError):
    """Raised when a monetary amount is invalid."""


class InvalidQuantityError(MpalError):
    """Raised when an asset quantity is invalid."""


class InvalidPriceError(MpalError):
    """Raised when an asset unit price is invalid."""


class InvalidTradeTotalError(MpalError):
    """Raised when a trade cash total is inexact or inconsistent."""


class InsufficientAssetQuantityError(MpalError):
    """Raised when a sell exceeds an asset's active open quantity."""


class InvalidEntryDateError(MpalError):
    """Raised when a capital entry date is invalid."""


class InsufficientCashError(MpalError):
    """Raised when an outflow exceeds available portfolio cash."""


class CapitalEntryNotFoundError(MpalError):
    """Raised when a capital entry does not exist or is inactive."""


class InvalidLedgerEditError(MpalError):
    """Raised when an edit would make the active ledger invalid."""


class InvalidLedgerDeleteError(MpalError):
    """Raised when entry deletion would make the active ledger invalid."""
