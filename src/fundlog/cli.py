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
    print_portfolio_summaries,
    print_portfolio_summary,
)
from fundlog.storage import (
    create_portfolio,
    create_portfolio_with_initial,
    delete_capital_entry,
    delete_portfolio,
    edit_capital_entry,
    get_all_portfolio_summaries,
    get_capital_entry_log,
    get_portfolio_summary,
    initialize_database,
    record_inflow,
    record_outflow,
    reset_portfolio_entries,
)

app = typer.Typer(
    name="fundlog",
    help="Manually track portfolio capital from the terminal.",
    no_args_is_help=True,
)


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


@app.command("init")
def init_command() -> None:
    """Initialize FundLog's local data store."""
    try:
        database_path = initialize_database()
    except FundLogError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

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
    try:
        if initial is None:
            create_portfolio(name)
        else:
            amount_minor = parse_amount_minor(initial)
            create_portfolio_with_initial(
                name,
                amount_minor,
                local_date.today(),
            )
    except FundLogError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    if initial is None:
        print_message(f"Portfolio '{name}' created.")
    else:
        print_message(f"Portfolio '{name}' created with initial capital.")


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
    if all_portfolios and portfolio is not None:
        typer.echo(
            "A portfolio name cannot be combined with --all.",
            err=True,
        )
        raise typer.Exit(code=1)
    if all_portfolios:
        try:
            portfolio_summaries = get_all_portfolio_summaries()
        except FundLogError as error:
            typer.echo(str(error), err=True)
            raise typer.Exit(code=1) from error

        if not portfolio_summaries:
            print_message("No active portfolios.")
            return
        print_portfolio_summaries(portfolio_summaries)
        return
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
    entry_no: Annotated[
        int,
        typer.Argument(
            metavar="ENTRY_NUMBER",
            help="Portfolio-local capital entry number.",
        ),
    ],
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
            entry_no,
            amount_minor=amount_minor,
            entry_date=entry_date,
            note=note,
        )
    except FundLogError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    print_message(f"Capital entry {entry_no} updated for portfolio '{portfolio}'.")


@app.command()
def reset(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Confirm the portfolio reset."),
    ] = False,
) -> None:
    """Reset portfolio entries while retaining the portfolio."""
    if not yes:
        typer.echo("Reset requires the --yes confirmation flag.", err=True)
        raise typer.Exit(code=1)

    try:
        reset_portfolio_entries(portfolio)
    except FundLogError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    print_message(f"Portfolio '{portfolio}' reset.")


@app.command()
def delete(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    entry_no: Annotated[
        int | None,
        typer.Argument(
            metavar="ENTRY_NUMBER",
            help="Portfolio-local entry number to delete.",
        ),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Confirm the portfolio deletion."),
    ] = False,
) -> None:
    """Soft-delete one entry or an entire portfolio."""
    if entry_no is not None:
        if yes:
            typer.echo(
                "Do not combine an entry number with --yes.",
                err=True,
            )
            raise typer.Exit(code=1)
        try:
            delete_capital_entry(portfolio, entry_no)
        except FundLogError as error:
            typer.echo(str(error), err=True)
            raise typer.Exit(code=1) from error

        print_message(f"Capital entry {entry_no} deleted from portfolio '{portfolio}'.")
        return

    if not yes:
        typer.echo("Delete requires the --yes confirmation flag.", err=True)
        raise typer.Exit(code=1)

    try:
        delete_portfolio(portfolio)
    except FundLogError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    print_message(f"Portfolio '{portfolio}' deleted.")
