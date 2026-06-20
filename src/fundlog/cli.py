"""FundLog command-line interface."""

from datetime import date as local_date
from typing import Annotated

import typer

from fundlog import __version__
from fundlog.amounts import parse_amount_minor
from fundlog.assets import parse_asset_reference
from fundlog.config import APP_NAME
from fundlog.dates import parse_transaction_date
from fundlog.errors import FundLogError
from fundlog.numbers import parse_price, parse_quantity
from fundlog.output.console import (
    print_asset_summary,
    print_asset_transaction_log,
    print_assets,
    print_capital_entry_log,
    print_error,
    print_info,
    print_portfolio_summaries,
    print_portfolio_summary,
    print_success,
    print_warning,
)
from fundlog.storage import (
    calculate_buy_total_minor,
    calculate_sell_total_minor,
    create_assets,
    create_portfolio,
    create_portfolio_with_initial,
    delete_asset,
    delete_capital_entry,
    delete_portfolio,
    edit_capital_entry,
    get_all_portfolio_summaries,
    get_asset_summary,
    get_asset_transaction_log,
    get_assets,
    get_capital_entry_log,
    get_portfolio_summary,
    initialize_database,
    record_buy,
    record_income,
    record_inflow,
    record_outflow,
    record_sell,
    reset_portfolio_entries,
)

ASSET_ADD_SHAPE = r"fundlog asset add <portfolio> <symbol> \[symbol...]"
ASSET_BUY_SHAPE = (
    "fundlog asset buy <portfolio>/<symbol> --price <price> "
    "--quantity <quantity> "
    "[--fee <fee>] [--total <amount>] [--date <date>] [--note <text>]"
)
ASSET_SELL_SHAPE = (
    "fundlog asset sell <portfolio>/<symbol> --price <price> "
    "--quantity <quantity> "
    "[--fee <fee>] [--total <amount>] [--date <date>] [--note <text>]"
)

HELP_EXAMPLES = "Examples:\n\n  " + "\n\n  ".join(
    (
        "fundlog init",
        "fundlog portfolio create <portfolio> [--initial <amount>]",
        "fundlog portfolio summary <portfolio>",
        "fundlog portfolio summary --all",
        ("fundlog capital inflow <portfolio> <amount> [--date <date>] [--note <text>]"),
        (
            "fundlog capital outflow <portfolio> <amount> "
            "[--date <date>] [--note <text>]"
        ),
        "fundlog capital log <portfolio>",
        "fundlog capital edit <portfolio> <entry-number>",
        "fundlog capital delete <portfolio> <entry-number>",
        ASSET_ADD_SHAPE,
        "fundlog asset summary <portfolio>",
        "fundlog asset log <portfolio>/<symbol>",
        "fundlog asset summary <portfolio>/<symbol>",
        "fundlog asset delete <portfolio>/<symbol> --yes",
        (
            "fundlog asset income <portfolio>/<symbol> <amount> "
            "[--date <date>] [--note <text>]"
        ),
        ASSET_BUY_SHAPE,
        ASSET_SELL_SHAPE,
    )
)

PORTFOLIO_HELP_EXAMPLES = "Examples:\n\n  " + "\n\n  ".join(
    (
        "fundlog portfolio create <portfolio> [--initial <amount>]",
        "fundlog portfolio summary <portfolio>",
        "fundlog portfolio summary --all",
        "fundlog portfolio reset <portfolio> --yes",
        "fundlog portfolio delete <portfolio> --yes",
    )
)

PORTFOLIO_SUMMARY_HELP_EXAMPLES = """Examples:

  fundlog portfolio summary <portfolio>

  fundlog portfolio summary --all
"""

CAPITAL_HELP_EXAMPLES = "Examples:\n\n  " + "\n\n  ".join(
    (
        ("fundlog capital inflow <portfolio> <amount> [--date <date>] [--note <text>]"),
        (
            "fundlog capital outflow <portfolio> <amount> "
            "[--date <date>] [--note <text>]"
        ),
        "fundlog capital log <portfolio>",
        "fundlog capital edit <portfolio> <entry-number>",
        "fundlog capital delete <portfolio> <entry-number>",
    )
)

ASSET_HELP_EXAMPLES = "Examples:\n\n  " + "\n\n  ".join(
    (
        ASSET_ADD_SHAPE,
        "fundlog asset summary <portfolio>",
        "fundlog asset summary <portfolio>/<symbol>",
        "fundlog asset log <portfolio>/<symbol>",
        "fundlog asset delete <portfolio>/<symbol> --yes",
        (
            "fundlog asset income <portfolio>/<symbol> <amount> "
            "[--date <date>] [--note <text>]"
        ),
        ASSET_BUY_SHAPE,
        ASSET_SELL_SHAPE,
    )
)

INCOME_HELP_EXAMPLES = """Examples:

  fundlog asset income <portfolio>/<symbol> <amount>

  fundlog asset income <portfolio>/<symbol> <amount> --date <date> --note <text>
"""

BUY_HELP_EXAMPLES = f"Example:\n\n  {ASSET_BUY_SHAPE}"

SELL_HELP_EXAMPLES = f"Example:\n\n  {ASSET_SELL_SHAPE}"

app = typer.Typer(
    name="fundlog",
    help="Manually track portfolio capital from the terminal.",
    epilog=HELP_EXAMPLES,
    no_args_is_help=True,
)
portfolio_app = typer.Typer(
    name="portfolio",
    help="Manage portfolio lifecycle and summaries.",
    epilog=PORTFOLIO_HELP_EXAMPLES,
    no_args_is_help=True,
)
capital_app = typer.Typer(
    name="capital",
    help="Manage external portfolio capital entries.",
    epilog=CAPITAL_HELP_EXAMPLES,
    no_args_is_help=True,
)
asset_app = typer.Typer(
    name="asset",
    help="Manage symbols inside a portfolio.",
    epilog=ASSET_HELP_EXAMPLES,
    no_args_is_help=True,
)
app.add_typer(portfolio_app)
app.add_typer(capital_app)
app.add_typer(asset_app)


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


@asset_app.command("add")
def asset_add(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    symbols: Annotated[
        list[str],
        typer.Argument(help="One or more asset symbols."),
    ],
) -> None:
    """Add one or more symbols to an existing portfolio."""
    try:
        normalized_symbols = create_assets(portfolio, symbols)
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    if len(normalized_symbols) == 1:
        print_success(
            f"Asset '{normalized_symbols[0]}' added to portfolio '{portfolio}'."
        )
        return
    print_success(
        f"{len(normalized_symbols)} assets added to portfolio '{portfolio}': "
        f"{', '.join(normalized_symbols)}."
    )


@asset_app.command("list", hidden=True)
def asset_list(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
) -> None:
    """Compatibility alias for portfolio-wide asset summary."""
    _print_portfolio_asset_summary(portfolio)


def _print_portfolio_asset_summary(portfolio: str) -> None:
    """Print every active asset summary for one active portfolio."""
    try:
        assets = get_assets(portfolio)
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    if not assets:
        print_info(f"No active assets for portfolio '{portfolio}'.")
        return
    print_assets(assets)


@asset_app.command("delete")
def asset_delete(
    reference: Annotated[
        str,
        typer.Argument(help="Asset reference in <portfolio>/<symbol> form."),
    ],
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Confirm the asset soft delete."),
    ] = False,
) -> None:
    """Soft-delete an asset from a portfolio."""
    if not yes:
        print_warning("Asset delete requires the --yes confirmation flag.")
        raise typer.Exit(code=1)

    try:
        portfolio, symbol = parse_asset_reference(reference)
        delete_asset(portfolio, symbol)
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Asset '{symbol}' deleted from portfolio '{portfolio}'.")


@asset_app.command("summary")
def asset_summary(
    target: Annotated[
        str,
        typer.Argument(
            help="Portfolio name or asset reference in <portfolio>/<symbol> form."
        ),
    ],
) -> None:
    """Show all asset summaries in a portfolio or one asset summary."""
    if "/" not in target:
        _print_portfolio_asset_summary(target)
        return

    try:
        portfolio, symbol = parse_asset_reference(target)
        summary = get_asset_summary(portfolio, symbol)
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_asset_summary(portfolio, summary)


@asset_app.command("log")
def asset_log(
    reference: Annotated[
        str,
        typer.Argument(help="Asset reference in <portfolio>/<symbol> form."),
    ],
) -> None:
    """Show active transactions for an asset."""
    try:
        portfolio, symbol = parse_asset_reference(reference)
        transactions = get_asset_transaction_log(portfolio, symbol)
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    if not transactions:
        print_info(f"No active transactions for asset '{symbol}/{portfolio}'.")
        return
    print_asset_transaction_log(portfolio, symbol, transactions)


@app.command(
    hidden=True,
    context_settings={"ignore_unknown_options": True},
    epilog=INCOME_HELP_EXAMPLES,
)
@asset_app.command(
    "income",
    context_settings={"ignore_unknown_options": True},
    epilog=INCOME_HELP_EXAMPLES,
)
def income(
    reference: Annotated[
        str,
        typer.Argument(help="Asset reference in <portfolio>/<symbol> form."),
    ],
    amount: Annotated[str, typer.Argument(help="Asset income amount.")],
    date: Annotated[
        str | None,
        typer.Option(
            "--date",
            help=(
                "Transaction date in YYYY-MM-DD; defaults to today "
                "and cannot be future."
            ),
        ),
    ] = None,
    note: Annotated[
        str | None,
        typer.Option("--note", help="Optional income note."),
    ] = None,
) -> None:
    """Record manual income for an existing asset."""
    try:
        portfolio, symbol = parse_asset_reference(reference)
        amount_minor = parse_amount_minor(amount)
        transaction_date = (
            local_date.today() if date is None else parse_transaction_date(date)
        )
        record_income(
            portfolio,
            symbol,
            amount_minor,
            transaction_date,
            note,
        )
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Income recorded for asset '{symbol}/{portfolio}'.")


@app.command(
    hidden=True,
    context_settings={"ignore_unknown_options": True},
    epilog=BUY_HELP_EXAMPLES,
)
@asset_app.command(
    "buy",
    context_settings={"ignore_unknown_options": True},
    epilog=BUY_HELP_EXAMPLES,
)
def buy(
    reference: Annotated[
        str,
        typer.Argument(help="Asset reference in <portfolio>/<symbol> form."),
    ],
    price: Annotated[str, typer.Option("--price", help="Exact unit price.")],
    quantity: Annotated[
        str,
        typer.Option("--quantity", help="Exact quantity to buy."),
    ],
    fee: Annotated[
        str | None,
        typer.Option("--fee", help="Trade fee; defaults to 0.00."),
    ] = None,
    total: Annotated[
        str | None,
        typer.Option("--total", help="Exact buy cash outflow including fees."),
    ] = None,
    date: Annotated[
        str | None,
        typer.Option(
            "--date",
            help=(
                "Transaction date in YYYY-MM-DD; defaults to today "
                "and cannot be future."
            ),
        ),
    ] = None,
    note: Annotated[
        str | None,
        typer.Option("--note", help="Optional buy note."),
    ] = None,
) -> None:
    """Record a manual buy for an existing asset."""
    try:
        portfolio, symbol = parse_asset_reference(reference)
        parsed_price = parse_price(price)
        parsed_quantity = parse_quantity(quantity)
        fee_minor = 0 if fee is None else parse_amount_minor(fee, allow_zero=True)
        provided_total_minor = None if total is None else parse_amount_minor(total)
        total_minor = calculate_buy_total_minor(
            parsed_price,
            parsed_quantity,
            fee_minor,
            provided_total_minor,
        )
        transaction_date = (
            local_date.today() if date is None else parse_transaction_date(date)
        )
        record_buy(
            portfolio,
            symbol,
            parsed_price,
            parsed_quantity,
            fee_minor,
            total_minor,
            transaction_date,
            note,
        )
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Buy recorded for asset '{symbol}/{portfolio}'.")


@app.command(
    hidden=True,
    context_settings={"ignore_unknown_options": True},
    epilog=SELL_HELP_EXAMPLES,
)
@asset_app.command(
    "sell",
    context_settings={"ignore_unknown_options": True},
    epilog=SELL_HELP_EXAMPLES,
)
def sell(
    reference: Annotated[
        str,
        typer.Argument(help="Asset reference in <portfolio>/<symbol> form."),
    ],
    price: Annotated[str, typer.Option("--price", help="Exact unit price.")],
    quantity: Annotated[
        str,
        typer.Option("--quantity", help="Exact quantity to sell."),
    ],
    fee: Annotated[
        str | None,
        typer.Option("--fee", help="Trade fee; defaults to 0.00."),
    ] = None,
    total: Annotated[
        str | None,
        typer.Option("--total", help="Exact net sell proceeds after fees."),
    ] = None,
    date: Annotated[
        str | None,
        typer.Option(
            "--date",
            help=(
                "Transaction date in YYYY-MM-DD; defaults to today "
                "and cannot be future."
            ),
        ),
    ] = None,
    note: Annotated[
        str | None,
        typer.Option("--note", help="Optional sell note."),
    ] = None,
) -> None:
    """Record a manual sell for an existing asset."""
    try:
        portfolio, symbol = parse_asset_reference(reference)
        parsed_price = parse_price(price)
        parsed_quantity = parse_quantity(quantity)
        fee_minor = 0 if fee is None else parse_amount_minor(fee, allow_zero=True)
        provided_total_minor = None if total is None else parse_amount_minor(total)
        total_minor = calculate_sell_total_minor(
            parsed_price,
            parsed_quantity,
            fee_minor,
            provided_total_minor,
        )
        transaction_date = (
            local_date.today() if date is None else parse_transaction_date(date)
        )
        record_sell(
            portfolio,
            symbol,
            parsed_price,
            parsed_quantity,
            fee_minor,
            total_minor,
            transaction_date,
            note,
        )
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Sell recorded for asset '{symbol}/{portfolio}'.")


@app.command(hidden=True)
@portfolio_app.command("create")
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


@app.command(hidden=True, context_settings={"ignore_unknown_options": True})
@capital_app.command("inflow", context_settings={"ignore_unknown_options": True})
def inflow(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    amount: Annotated[str, typer.Argument(help="Capital inflow amount.")],
    date: Annotated[
        str | None,
        typer.Option(
            "--date",
            help="Entry date in YYYY-MM-DD; defaults to today and cannot be future.",
        ),
    ] = None,
    note: Annotated[
        str | None,
        typer.Option("--note", help="Optional entry note."),
    ] = None,
) -> None:
    """Record money added to a portfolio."""
    try:
        amount_minor = parse_amount_minor(amount)
        entry_date = (
            local_date.today() if date is None else parse_transaction_date(date)
        )
        record_inflow(portfolio, amount_minor, entry_date, note)
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Inflow recorded for portfolio '{portfolio}'.")


@app.command(hidden=True, context_settings={"ignore_unknown_options": True})
@capital_app.command("outflow", context_settings={"ignore_unknown_options": True})
def outflow(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    amount: Annotated[str, typer.Argument(help="Capital outflow amount.")],
    date: Annotated[
        str | None,
        typer.Option(
            "--date",
            help="Entry date in YYYY-MM-DD; defaults to today and cannot be future.",
        ),
    ] = None,
    note: Annotated[
        str | None,
        typer.Option("--note", help="Optional entry note."),
    ] = None,
) -> None:
    """Record money withdrawn from a portfolio."""
    try:
        amount_minor = parse_amount_minor(amount)
        entry_date = (
            local_date.today() if date is None else parse_transaction_date(date)
        )
        record_outflow(portfolio, amount_minor, entry_date, note)
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Outflow recorded for portfolio '{portfolio}'.")


@app.command(hidden=True)
@portfolio_app.command(
    "summary",
    epilog=PORTFOLIO_SUMMARY_HELP_EXAMPLES,
)
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


@app.command(hidden=True)
@capital_app.command("log")
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


@app.command(hidden=True, context_settings={"ignore_unknown_options": True})
@capital_app.command("edit", context_settings={"ignore_unknown_options": True})
def edit(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    entry_number: Annotated[
        int,
        typer.Argument(
            metavar="ENTRY_NUMBER",
            help="Entry number shown by the portfolio capital log.",
        ),
    ],
    amount: Annotated[
        str | None,
        typer.Option("--amount", help="Replacement entry amount."),
    ] = None,
    date: Annotated[
        str | None,
        typer.Option(
            "--date",
            help="Replacement date in YYYY-MM-DD; cannot be future.",
        ),
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
        entry_date = None if date is None else parse_transaction_date(date)
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


@app.command(hidden=True)
@portfolio_app.command("reset")
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


@portfolio_app.command("delete")
def portfolio_delete(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            help="Soft-delete the entire portfolio and its entries.",
        ),
    ] = False,
) -> None:
    """Soft-delete an entire portfolio and its entries."""
    _delete_portfolio_command(portfolio, yes)


@capital_app.command("delete")
def capital_delete(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    entry_number: Annotated[
        int,
        typer.Argument(
            metavar="ENTRY_NUMBER",
            help="Entry number shown by the portfolio capital log.",
        ),
    ],
) -> None:
    """Soft-delete one capital entry by its portfolio-local number."""
    _delete_capital_entry_command(portfolio, entry_number)


@app.command(hidden=True)
def delete(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    entry_number: Annotated[
        int | None,
        typer.Argument(
            metavar="ENTRY_NUMBER",
            help="Entry number shown by the portfolio capital log.",
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
        _delete_capital_entry_command(portfolio, entry_number)
        return

    _delete_portfolio_command(portfolio, yes)


def _delete_capital_entry_command(portfolio: str, entry_number: int) -> None:
    """Run capital-entry deletion for grouped and compatibility commands."""
    try:
        delete_capital_entry(portfolio, entry_number)
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Capital entry {entry_number} deleted from portfolio '{portfolio}'.")


def _delete_portfolio_command(portfolio: str, yes: bool) -> None:
    """Run portfolio deletion for grouped and compatibility commands."""
    if not yes:
        print_warning("Delete requires the --yes confirmation flag.")
        raise typer.Exit(code=1)

    try:
        delete_portfolio(portfolio)
    except FundLogError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Portfolio '{portfolio}' deleted.")
