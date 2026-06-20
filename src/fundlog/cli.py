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
    print_error,
    print_info,
    print_portfolio_summaries,
    print_portfolio_summary,
    print_success,
    print_warning,
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

HELP_EXAMPLES = """Examples:

  fundlog init

  fundlog create stocks --initial 5000

  fundlog inflow stocks 1000

  fundlog outflow stocks 250

  fundlog summary stocks

  fundlog summary --all

  fundlog log stocks

  fundlog edit stocks 1 --amount 500

  fundlog delete stocks 1

  fundlog delete stocks --yes
"""

app = typer.Typer(
    name="fundlog",
    help="Manually track portfolio capital from the terminal.",
    epilog=HELP_EXAMPLES,
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
    """Initialize FundLog's local database."""
    try:
        database_path = initialize_database()
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"FundLog initialized at {database_path}")


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
        print_error(str(error))
        raise typer.Exit(code=1) from error

    if initial is None:
        print_success(f"Portfolio '{name}' created.")
    else:
        print_success(f"Portfolio '{name}' created with initial capital.")


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
    """Record money added to a portfolio."""
    try:
        amount_minor = parse_amount_minor(amount)
        entry_date = local_date.today() if date is None else _parse_entry_date(date)
        record_inflow(portfolio, amount_minor, entry_date, note)
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Inflow recorded for portfolio '{portfolio}'.")


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
    """Record money withdrawn from a portfolio."""
    try:
        amount_minor = parse_amount_minor(amount)
        entry_date = local_date.today() if date is None else _parse_entry_date(date)
        record_outflow(portfolio, amount_minor, entry_date, note)
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Outflow recorded for portfolio '{portfolio}'.")


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
        print_error("A portfolio name cannot be combined with --all.")
        raise typer.Exit(code=1)
    if all_portfolios:
        try:
            portfolio_summaries = get_all_portfolio_summaries()
        except FundLogError as error:
            print_error(str(error))
            raise typer.Exit(code=1) from error

        if not portfolio_summaries:
            print_info("No active portfolios.")
            return
        print_portfolio_summaries(portfolio_summaries)
        return
    if portfolio is None:
        print_error("A portfolio name is required.")
        raise typer.Exit(code=1)

    try:
        portfolio_summary = get_portfolio_summary(portfolio)
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_portfolio_summary(portfolio_summary)


@app.command()
def log(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
) -> None:
    """Show capital entries for a portfolio."""
    try:
        entries = get_capital_entry_log(portfolio)
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    if not entries:
        print_info(f"No active capital entries for portfolio '{portfolio}'.")
        return
    print_capital_entry_log(entries)


@app.command(context_settings={"ignore_unknown_options": True})
def edit(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    entry_number: Annotated[
        int,
        typer.Argument(
            metavar="ENTRY_NUMBER",
            help="Entry number shown by 'fundlog log <portfolio>'.",
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
    """Edit a capital entry by its number in the portfolio log."""
    if amount is None and date is None and note is None:
        print_error("Provide at least one of --amount, --date, or --note.")
        raise typer.Exit(code=1)

    try:
        amount_minor = None if amount is None else parse_amount_minor(amount)
        entry_date = None if date is None else _parse_entry_date(date)
        edit_capital_entry(
            portfolio,
            entry_number,
            amount_minor=amount_minor,
            entry_date=entry_date,
            note=note,
        )
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Capital entry {entry_number} updated for portfolio '{portfolio}'.")


@app.command()
def reset(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Confirm the portfolio reset."),
    ] = False,
) -> None:
    """Clear all entries from a portfolio while keeping the portfolio."""
    if not yes:
        print_warning("Reset requires the --yes confirmation flag.")
        raise typer.Exit(code=1)

    try:
        reset_portfolio_entries(portfolio)
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Portfolio '{portfolio}' reset.")


@app.command()
def delete(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    entry_number: Annotated[
        int | None,
        typer.Argument(
            metavar="ENTRY_NUMBER",
            help="Entry number shown by 'fundlog log <portfolio>'.",
        ),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            help="Soft-delete the entire portfolio and its entries.",
        ),
    ] = False,
) -> None:
    """Delete an entry, or delete a portfolio with --yes."""
    if entry_number is not None:
        if yes:
            print_warning("Do not combine an entry number with --yes.")
            raise typer.Exit(code=1)
        try:
            delete_capital_entry(portfolio, entry_number)
        except FundLogError as error:
            print_error(str(error))
            raise typer.Exit(code=1) from error

        print_success(
            f"Capital entry {entry_number} deleted from portfolio '{portfolio}'."
        )
        return

    if not yes:
        print_warning("Delete requires the --yes confirmation flag.")
        raise typer.Exit(code=1)

    try:
        delete_portfolio(portfolio)
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Portfolio '{portfolio}' deleted.")
