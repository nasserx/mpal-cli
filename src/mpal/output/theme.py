"""Shared semantic styles for mpal terminal output."""

from rich.box import Box

HEADER = "#C77DFF"
SUCCESS = "#4ADE80"
ERROR = "#F87171"
WARNING = "#FACC15"
INFO = "#60A5FA"
PROFIT = SUCCESS
LOSS = ERROR
INCOME = "#60A5FA"
BORDER = "#4B5563"
MUTED = "#9CA3AF"
VALUE = "#D1D5DB"

TABLE_HEADER = HEADER
TABLE_BORDER = BORDER
TABLE_CELL = VALUE
TABLE_BOX = Box(
    """\
╭──╮
│  │
├──┤
│  │
├──┤
├──┤
│  │
╰──╯
"""
)

__all__ = [
    "BORDER",
    "ERROR",
    "HEADER",
    "INFO",
    "INCOME",
    "LOSS",
    "MUTED",
    "PROFIT",
    "SUCCESS",
    "TABLE_BOX",
    "TABLE_BORDER",
    "TABLE_CELL",
    "TABLE_HEADER",
    "VALUE",
    "WARNING",
]
