"""FundLog exception types."""


class FundLogError(Exception):
    """Base exception for expected FundLog errors."""


class DatabaseNotInitializedError(FundLogError):
    """Raised when a command requires an initialized database."""


class PortfolioAlreadyExistsError(FundLogError):
    """Raised when an active portfolio name is already in use."""


class InvalidPortfolioNameError(FundLogError):
    """Raised when a portfolio name is empty."""


class PortfolioNotFoundError(FundLogError):
    """Raised when an active portfolio cannot be found."""


class InvalidAmountError(FundLogError):
    """Raised when a monetary amount is invalid."""


class InvalidEntryDateError(FundLogError):
    """Raised when a capital entry date is invalid."""


class InsufficientCashError(FundLogError):
    """Raised when an outflow exceeds available portfolio cash."""
