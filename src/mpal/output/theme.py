"""Shared semantic styles for mpal terminal output."""

from rich.box import Box

HEADER = "#B39DDB"
SUCCESS = "#81C784"
ERROR = "#E57373"
WARNING = "#FFD54F"
INFO = "#64B5F6"
PROFIT = SUCCESS
LOSS = ERROR
INCOME = "#60A5FA"
ROW_KEY = "#EFAE83"
BORDER = "#4B5563"
MUTED = "#9CA3AF"
VALUE = "#D1D5DB"

TABLE_HEADER = HEADER
TABLE_BORDER = BORDER
TABLE_CELL = VALUE
ROW_SEPARATOR = f"dim {MUTED}"
RELATION_SEPARATOR = INFO
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
    "RELATION_SEPARATOR",
    "ROW_KEY",
    "ROW_SEPARATOR",
    "SUCCESS",
    "TABLE_BOX",
    "TABLE_BORDER",
    "TABLE_CELL",
    "TABLE_HEADER",
    "VALUE",
    "WARNING",
]
