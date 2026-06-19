"""FundLog command-line interface."""

from datetime import date as local_date
from typing import Annotated

import typer

from fundlog import __version__
from fundlog.amounts import parse_amount_minor
from fundlog.config import APP_NAME
from fundlog.errors import FundLogError, InvalidEntryDateError
from fundlog.output.console import (
    print_capital_entry_log,
    print_message,
    print_portfolio_summary,
)
from fundlog.storage import (
    create_portfolio,
    edit_capital_entry,
    get_capital_entry_log,
    get_portfolio_summary,
    initialize_database,
    record_inflow,
    record_outflow,
    remove_capital_entry,
)

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
    database_path = initialize_database()
    print_message(f"FundLog initialized at {database_path}")


@app.command()
def create(
    name: Annotated[str, typer.Argument(help="Name of the portfolio to create.")],
    initial: Annotated[
        str | None,
        typer.Option("--initial", help="Initial capital inflow amount."),
    ] = None,
) -> None:
    """Create a portfolio, optionally with initial capital."""
    if initial is not None:
        typer.echo("The --initial option is not implemented yet.", err=True)
        raise typer.Exit(code=1)

    try:
        create_portfolio(name)
    except FundLogError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    print_message(f"Portfolio '{name}' created.")


@app.command(context_settings={"ignore_unknown_options": True})
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
    try:
        amount_minor = parse_amount_minor(amount)
        entry_date = local_date.today() if date is None else _parse_entry_date(date)
        record_inflow(portfolio, amount_minor, entry_date, note)
    except FundLogError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    print_message(f"Inflow recorded for portfolio '{portfolio}'.")


def _parse_entry_date(value: str) -> local_date:
    """Parse an ISO entry date."""
    try:
        parsed_date = local_date.fromisoformat(value)
    except ValueError as error:
        raise InvalidEntryDateError(
            f"Invalid date: '{value}'. Use YYYY-MM-DD."
        ) from error
    if parsed_date.isoformat() != value:
        raise InvalidEntryDateError(f"Invalid date: '{value}'. Use YYYY-MM-DD.")
    return parsed_date


@app.command(context_settings={"ignore_unknown_options": True})
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
    try:
        amount_minor = parse_amount_minor(amount)
        entry_date = local_date.today() if date is None else _parse_entry_date(date)
        record_outflow(portfolio, amount_minor, entry_date, note)
    except FundLogError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    print_message(f"Outflow recorded for portfolio '{portfolio}'.")


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
    if all_portfolios:
        typer.echo("The --all option is not implemented yet.", err=True)
        raise typer.Exit(code=1)
    if portfolio is None:
        typer.echo("A portfolio name is required.", err=True)
        raise typer.Exit(code=1)

    try:
        portfolio_summary = get_portfolio_summary(portfolio)
    except FundLogError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    print_portfolio_summary(portfolio_summary)


@app.command()
def log(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
) -> None:
    """Show the capital-entry log for a portfolio."""
    try:
        entries = get_capital_entry_log(portfolio)
    except FundLogError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    if not entries:
        print_message(f"No active capital entries for portfolio '{portfolio}'.")
        return
    print_capital_entry_log(entries)


@app.command(context_settings={"ignore_unknown_options": True})
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
    if amount is None and date is None and note is None:
        typer.echo(
            "Provide at least one of --amount, --date, or --note.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        amount_minor = None if amount is None else parse_amount_minor(amount)
        entry_date = None if date is None else _parse_entry_date(date)
        edit_capital_entry(
            portfolio,
            entry_id,
            amount_minor=amount_minor,
            entry_date=entry_date,
            note=note,
        )
    except FundLogError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    print_message(f"Capital entry {entry_id} updated for portfolio '{portfolio}'.")


@app.command()
def remove(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    entry_id: Annotated[int, typer.Argument(help="Capital entry ID.")],
) -> None:
    """Soft-remove a portfolio capital entry."""
    try:
        remove_capital_entry(portfolio, entry_id)
    except FundLogError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    print_message(f"Capital entry {entry_id} removed from portfolio '{portfolio}'.")


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
