"""Tests for shared transaction-date validation."""

from datetime import date

import pytest

from fundlog.dates import parse_transaction_date
from fundlog.errors import InvalidEntryDateError


def test_parse_transaction_date_accepts_past_date() -> None:
    parsed = parse_transaction_date("2026-06-19", today=date(2026, 6, 20))

    assert parsed == date(2026, 6, 19)


def test_parse_transaction_date_accepts_today() -> None:
    parsed = parse_transaction_date("2026-06-20", today=date(2026, 6, 20))

    assert parsed == date(2026, 6, 20)


@pytest.mark.parametrize("value", ["19-06-2026", "20260619", "2026-02-30"])
def test_parse_transaction_date_rejects_invalid_iso_date(value: str) -> None:
    with pytest.raises(
        InvalidEntryDateError,
        match="Date must be a valid ISO date in YYYY-MM-DD format.",
    ):
        parse_transaction_date(value, today=date(2026, 6, 20))


def test_parse_transaction_date_rejects_future_date() -> None:
    with pytest.raises(
        InvalidEntryDateError,
        match="Date cannot be in the future.",
    ):
        parse_transaction_date("2026-06-21", today=date(2026, 6, 20))
