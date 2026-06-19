"""Rich terminal output helpers."""

from rich.console import Console


def print_message(message: str) -> None:
    """Print a plain message through Rich."""
    Console().print(message)
