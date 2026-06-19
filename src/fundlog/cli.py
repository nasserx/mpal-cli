"""FundLog command-line interface."""

from typing import Annotated

import typer

from fundlog import __version__
from fundlog.config import APP_NAME
from fundlog.output.console import print_message

app = typer.Typer(
    name="fundlog",
    help="Manually track portfolio capital from the terminal.",
    no_args_is_help=True,
)

PLACEHOLDER_MESSAGE = "Not implemented yet."


def version_callback(value: bool) -> None:
    """Print the installed FundLog version and exit."""
    if value:
        typer.echo(f"{APP_NAME} {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show the FundLog version and exit.",
        ),
    ] = None,
) -> None:
    """FundLog manages manually recorded portfolio capital."""


def show_placeholder() -> None:
    """Report that a command has not been implemented."""
    print_message(PLACEHOLDER_MESSAGE)


@app.command("init")
def init_command() -> None:
    """Initialize FundLog's local data store."""
    show_placeholder()


@app.command()
def create(
    name: Annotated[str, typer.Argument(help="Name of the portfolio to create.")],
    initial: Annotated[
        str | None,
        typer.Option("--initial", help="Initial capital inflow amount."),
    ] = None,
) -> None:
    """Create a portfolio, optionally with initial capital."""
    show_placeholder()


@app.command()
def inflow(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    amount: Annotated[str, typer.Argument(help="Capital inflow amount.")],
    date: Annotated[
        str | None,
        typer.Option("--date", help="Entry date in YYYY-MM-DD format."),
    ] = None,
    note: Annotated[
        str | None,
        typer.Option("--note", help="Optional entry note."),
    ] = None,
) -> None:
    """Record capital entering a portfolio."""
    show_placeholder()


@app.command()
def outflow(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    amount: Annotated[str, typer.Argument(help="Capital outflow amount.")],
    date: Annotated[
        str | None,
        typer.Option("--date", help="Entry date in YYYY-MM-DD format."),
    ] = None,
    note: Annotated[
        str | None,
        typer.Option("--note", help="Optional entry note."),
    ] = None,
) -> None:
    """Record capital leaving a portfolio."""
    show_placeholder()


@app.command()
def summary(
    portfolio: Annotated[
        str | None,
        typer.Argument(help="Portfolio name."),
    ] = None,
    all_portfolios: Annotated[
        bool,
        typer.Option("--all", help="Show all portfolio summaries."),
    ] = False,
) -> None:
    """Show one portfolio summary or all portfolio summaries."""
    show_placeholder()


@app.command()
def log(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
) -> None:
    """Show the capital-entry log for a portfolio."""
    show_placeholder()


@app.command()
def edit(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    entry_id: Annotated[int, typer.Argument(help="Capital entry ID.")],
    amount: Annotated[
        str | None,
        typer.Option("--amount", help="Replacement entry amount."),
    ] = None,
    date: Annotated[
        str | None,
        typer.Option("--date", help="Replacement date in YYYY-MM-DD format."),
    ] = None,
    note: Annotated[
        str | None,
        typer.Option("--note", help="Replacement entry note."),
    ] = None,
) -> None:
    """Edit a portfolio capital entry."""
    show_placeholder()


@app.command()
def remove(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    entry_id: Annotated[int, typer.Argument(help="Capital entry ID.")],
) -> None:
    """Soft-remove a portfolio capital entry."""
    show_placeholder()


@app.command()
def reset(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Confirm the portfolio reset."),
    ] = False,
) -> None:
    """Reset portfolio entries while retaining the portfolio."""
    show_placeholder()
