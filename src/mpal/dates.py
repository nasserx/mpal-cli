"""Shared transaction-date parsing and validation."""

from datetime import date
from re import fullmatch

from mpal.errors import InvalidEntryDateError

INVALID_DATE_MESSAGE = "Date must be a valid ISO date in YYYY-MM-DD format."
FUTURE_DATE_MESSAGE = "Date cannot be in the future."


def parse_transaction_date(value: str, *, today: date | None = None) -> date:
    """Parse a strict ISO date and reject dates after the local current date."""
    if fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise InvalidEntryDateError(INVALID_DATE_MESSAGE)

    try:
        parsed_date = date.fromisoformat(value)
    except ValueError as error:
        raise InvalidEntryDateError(INVALID_DATE_MESSAGE) from error

    current_date = date.today() if today is None else today
    if parsed_date > current_date:
        raise InvalidEntryDateError(FUTURE_DATE_MESSAGE)

    return parsed_date
