"""FundLog exception types."""


class FundLogError(Exception):
    """Base exception for expected FundLog errors."""


class DatabaseNotInitializedError(FundLogError):
    """Raised when a command requires an initialized database."""


class PortfolioAlreadyExistsError(FundLogError):
    """Raised when an active portfolio name is already in use."""


class InvalidPortfolioNameError(FundLogError):
    """Raised when a portfolio name is empty."""
