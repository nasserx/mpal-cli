"""mpal command-line interface."""

from datetime import date as local_date
from typing import Annotated

import typer

from mpal import __version__
from mpal.amounts import parse_amount_minor
from mpal.assets import normalize_symbol
from mpal.config import APP_NAME
from mpal.dates import parse_transaction_date
from mpal.errors import MpalError
from mpal.numbers import parse_price, parse_quantity
from mpal.output.console import (
    print_asset_summary,
    print_asset_transaction_log,
    print_assets,
    print_capital_entry_log,
    print_capital_state,
    print_error,
    print_info,
    print_portfolio_summaries,
    print_portfolio_summary,
    print_success,
    print_warning,
)
from mpal.storage import (
    calculate_buy_total_minor,
    calculate_sell_total_minor,
    create_assets,
    create_portfolio,
    create_portfolio_with_initial,
    delete_asset,
    delete_asset_transaction_entry,
    delete_capital_entry,
    delete_portfolio,
    edit_asset_transaction_entry,
    edit_capital_entry,
    get_all_assets,
    get_all_portfolio_summaries,
    get_asset_summary,
    get_asset_transaction_log,
    get_assets,
    get_capital_entry_log,
    get_capital_state,
    get_portfolio_summary,
    initialize_database,
    record_buy,
    record_income,
    record_inflow,
    record_outflow,
    record_sell,
    reset_portfolio_entries,
)

PORTFOLIO_OPTION = typer.Option(
    "--portfolio",
    "-p",
    help="Portfolio name.",
)

HELP_EXAMPLES = r"""Examples:

  mpal init

  mpal portfolio create <portfolio> [--initial <amount>]

  mpal portfolio list

  mpal portfolio show <portfolio>

  mpal capital deposit <amount> -p <portfolio>

  mpal capital show -p <portfolio>

  mpal asset add <symbol> \[symbol...] -p <portfolio>

  mpal asset list

  mpal asset list -p <portfolio>

  mpal asset show <symbol> -p <portfolio>
"""

PORTFOLIO_HELP_EXAMPLES = """Examples:

  mpal portfolio create <portfolio> [--initial <amount>]

  mpal portfolio list

  mpal portfolio show <portfolio>

  mpal portfolio reset <portfolio> --yes

  mpal portfolio delete <portfolio> --yes
"""

CAPITAL_HELP_EXAMPLES = """Examples:

  mpal capital show -p <portfolio>

  mpal capital deposit <amount> -p <portfolio>

  mpal capital withdraw <amount> -p <portfolio>

  mpal capital log -p <portfolio>

  mpal capital entry edit <entry-number> -p <portfolio> --amount <amount>

  mpal capital entry delete <entry-number> -p <portfolio>
"""

CAPITAL_ENTRY_HELP_EXAMPLES = """Examples:

  mpal capital entry edit <entry-number> -p <portfolio> --amount <amount>

  mpal capital entry delete <entry-number> -p <portfolio>
"""

ASSET_HELP_EXAMPLES = r"""Examples:

  mpal asset add <symbol> \[symbol...] -p <portfolio>

  mpal asset list

  mpal asset list -p <portfolio>

  mpal asset show <symbol> -p <portfolio>

  mpal asset log <symbol> -p <portfolio>

  mpal asset income <symbol> <amount> -p <portfolio>

  mpal asset buy <symbol> -p <portfolio> --price <price> --quantity <quantity>

  mpal asset sell <symbol> -p <portfolio> --price <price> --quantity <quantity>

  mpal asset entry edit <symbol> <entry-number> -p <portfolio> [options...]

  mpal asset entry delete <symbol> <entry-number> -p <portfolio> --yes

  mpal asset delete <symbol> -p <portfolio> --yes
"""

ASSET_ENTRY_HELP_EXAMPLES = r"""Examples:

  mpal asset entry edit <symbol> <entry-number> -p <portfolio> [options...]

  mpal asset entry delete <symbol> <entry-number> -p <portfolio> --yes
"""

app = typer.Typer(
    name="mpal",
    help="Multi-Portfolio Asset Ledger for manual asset and capital tracking.",
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
capital_entry_app = typer.Typer(
    name="entry",
    help="Edit or delete historical capital entries.",
    epilog=CAPITAL_ENTRY_HELP_EXAMPLES,
    no_args_is_help=True,
)
asset_app = typer.Typer(
    name="asset",
    help="Manage symbols inside a portfolio.",
    epilog=ASSET_HELP_EXAMPLES,
    no_args_is_help=True,
)
asset_entry_app = typer.Typer(
    name="entry",
    help="Edit or delete historical asset transaction entries.",
    epilog=ASSET_ENTRY_HELP_EXAMPLES,
    no_args_is_help=True,
)
app.add_typer(portfolio_app)
app.add_typer(capital_app)
capital_app.add_typer(capital_entry_app)
app.add_typer(asset_app)
asset_app.add_typer(asset_entry_app)


def version_callback(value: bool) -> None:
    """Print the installed mpal version and exit."""
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
            help="Show the mpal version and exit.",
        ),
    ] = None,
) -> None:
    """Multi-Portfolio Asset Ledger for manual asset and capital tracking."""


@app.command("init")
def init_command() -> None:
    """Initialize mpal's local database."""
    try:
        database_path = initialize_database()
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"mpal initialized at {database_path}")


@portfolio_app.command("create")
def portfolio_create(
    portfolio: Annotated[str, typer.Argument(help="Name of the portfolio to create.")],
    initial: Annotated[
        str | None,
        typer.Option("--initial", help="Initial capital deposit amount."),
    ] = None,
) -> None:
    """Create a portfolio, optionally with initial capital."""
    try:
        if initial is None:
            create_portfolio(portfolio)
        else:
            amount_minor = parse_amount_minor(initial)
            create_portfolio_with_initial(
                portfolio,
                amount_minor,
                local_date.today(),
            )
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    if initial is None:
        print_success(f"Portfolio '{portfolio}' created.")
    else:
        print_success(f"Portfolio '{portfolio}' created with initial capital.")


@portfolio_app.command("list")
def portfolio_list() -> None:
    """Show financial summaries for all active portfolios."""
    try:
        summaries = get_all_portfolio_summaries()
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    if not summaries:
        print_info("No active portfolios.")
        return
    print_portfolio_summaries(summaries)


@portfolio_app.command("show")
def portfolio_show(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
) -> None:
    """Show one active portfolio's financial summary."""
    try:
        summary = get_portfolio_summary(portfolio)
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_portfolio_summary(summary)


@portfolio_app.command("delete")
def portfolio_delete(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Confirm the portfolio soft delete."),
    ] = False,
) -> None:
    """Soft-delete an entire portfolio and its active related data."""
    if not yes:
        print_warning("Delete requires the --yes confirmation flag.")
        raise typer.Exit(code=1)

    try:
        delete_portfolio(portfolio)
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Portfolio '{portfolio}' deleted.")


@portfolio_app.command("reset")
def portfolio_reset(
    portfolio: Annotated[str, typer.Argument(help="Portfolio name.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Confirm the portfolio reset."),
    ] = False,
) -> None:
    """Clear active capital entries while keeping the portfolio."""
    if not yes:
        print_warning("Reset requires the --yes confirmation flag.")
        raise typer.Exit(code=1)

    try:
        reset_portfolio_entries(portfolio)
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Portfolio '{portfolio}' reset.")


@capital_app.command("deposit", context_settings={"ignore_unknown_options": True})
def capital_deposit(
    amount: Annotated[str, typer.Argument(help="Capital deposit amount.")],
    portfolio: Annotated[str, PORTFOLIO_OPTION],
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
    """Record external money added to a portfolio."""
    try:
        amount_minor = parse_amount_minor(amount)
        entry_date = (
            local_date.today() if date is None else parse_transaction_date(date)
        )
        record_inflow(portfolio, amount_minor, entry_date, note)
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Deposit recorded for portfolio '{portfolio}'.")


@capital_app.command("withdraw", context_settings={"ignore_unknown_options": True})
def capital_withdraw(
    amount: Annotated[str, typer.Argument(help="Capital withdrawal amount.")],
    portfolio: Annotated[str, PORTFOLIO_OPTION],
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
    """Record external money withdrawn from a portfolio."""
    try:
        amount_minor = parse_amount_minor(amount)
        entry_date = (
            local_date.today() if date is None else parse_transaction_date(date)
        )
        record_outflow(portfolio, amount_minor, entry_date, note)
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Withdrawal recorded for portfolio '{portfolio}'.")


@capital_app.command("show")
def capital_show(
    portfolio: Annotated[str, PORTFOLIO_OPTION],
) -> None:
    """Show capital-only current state for a portfolio."""
    try:
        state = get_capital_state(portfolio)
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_capital_state(state)


@capital_app.command("log")
def capital_log(
    portfolio: Annotated[str, PORTFOLIO_OPTION],
) -> None:
    """Show active capital entries for a portfolio."""
    try:
        entries = get_capital_entry_log(portfolio)
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    if not entries:
        print_info(f"No active capital entries for portfolio '{portfolio}'.")
        return
    print_capital_entry_log(entries)


@capital_entry_app.command("edit")
def capital_entry_edit(
    entry_number: Annotated[
        int,
        typer.Argument(
            metavar="ENTRY_NUMBER",
            help="Entry number shown by the portfolio capital log.",
        ),
    ],
    portfolio: Annotated[str, PORTFOLIO_OPTION],
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
    """Edit a capital entry by its portfolio-local number."""
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
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Capital entry {entry_number} updated for portfolio '{portfolio}'.")


@capital_entry_app.command("delete")
def capital_entry_delete(
    entry_number: Annotated[
        int,
        typer.Argument(
            metavar="ENTRY_NUMBER",
            help="Entry number shown by the portfolio capital log.",
        ),
    ],
    portfolio: Annotated[str, PORTFOLIO_OPTION],
) -> None:
    """Soft-delete one capital entry by its portfolio-local number."""
    try:
        delete_capital_entry(portfolio, entry_number)
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Capital entry {entry_number} deleted from portfolio '{portfolio}'.")


@asset_app.command("add")
def asset_add(
    symbols: Annotated[
        list[str],
        typer.Argument(help="One or more asset symbols."),
    ],
    portfolio: Annotated[str, PORTFOLIO_OPTION],
) -> None:
    """Add one or more symbols to an existing portfolio."""
    try:
        normalized_symbols = create_assets(portfolio, symbols)
    except MpalError as error:
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


@asset_app.command("list")
def asset_list(
    portfolio: Annotated[str | None, PORTFOLIO_OPTION] = None,
) -> None:
    """Show active assets globally or in one portfolio."""
    if portfolio is None:
        try:
            assets = get_all_assets()
        except MpalError as error:
            print_error(str(error))
            raise typer.Exit(code=1) from error

        if not assets:
            print_info("No active assets.")
            return
        print_assets(assets)
        return

    try:
        assets = get_assets(portfolio)
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    if not assets:
        print_info(f"No active assets for portfolio '{portfolio}'.")
        return
    print_assets(assets)


@asset_app.command("show")
def asset_show(
    symbol: Annotated[str, typer.Argument(help="Asset symbol.")],
    portfolio: Annotated[str, PORTFOLIO_OPTION],
) -> None:
    """Show one active asset's current state."""
    try:
        normalized_symbol = normalize_symbol(symbol)
        summary = get_asset_summary(portfolio, normalized_symbol)
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_asset_summary(portfolio, summary)


@asset_app.command("log")
def asset_log(
    symbol: Annotated[str, typer.Argument(help="Asset symbol.")],
    portfolio: Annotated[str, PORTFOLIO_OPTION],
) -> None:
    """Show active transactions for an asset."""
    try:
        normalized_symbol = normalize_symbol(symbol)
        transactions = get_asset_transaction_log(portfolio, normalized_symbol)
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    if not transactions:
        print_info(
            f"No active transactions for asset '{normalized_symbol}' "
            f"in portfolio '{portfolio}'."
        )
        return
    print_asset_transaction_log(portfolio, normalized_symbol, transactions)


@asset_app.command("delete")
def asset_delete(
    symbol: Annotated[str, typer.Argument(help="Asset symbol.")],
    portfolio: Annotated[str, PORTFOLIO_OPTION],
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Confirm the asset soft delete."),
    ] = False,
) -> None:
    """Soft-delete an asset and its active transactions."""
    if not yes:
        print_warning("Asset delete requires the --yes confirmation flag.")
        raise typer.Exit(code=1)

    try:
        normalized_symbol = normalize_symbol(symbol)
        delete_asset(portfolio, normalized_symbol)
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(f"Asset '{normalized_symbol}' deleted from portfolio '{portfolio}'.")


@asset_entry_app.command("delete")
def asset_entry_delete(
    symbol: Annotated[str, typer.Argument(help="Asset symbol.")],
    entry_number: Annotated[
        int,
        typer.Argument(
            metavar="ENTRY_NUMBER",
            help="Transaction number shown by the asset log.",
        ),
    ],
    portfolio: Annotated[str, PORTFOLIO_OPTION],
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Confirm the asset transaction soft delete."),
    ] = False,
) -> None:
    """Soft-delete one asset transaction by its asset-local number."""
    if not yes:
        print_warning("Asset transaction delete requires the --yes confirmation flag.")
        raise typer.Exit(code=1)

    try:
        normalized_symbol = normalize_symbol(symbol)
        delete_asset_transaction_entry(portfolio, normalized_symbol, entry_number)
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(
        f"Asset transaction {entry_number} deleted for asset '{normalized_symbol}' "
        f"in portfolio '{portfolio}'."
    )


@asset_entry_app.command("edit")
def asset_entry_edit(
    symbol: Annotated[str, typer.Argument(help="Asset symbol.")],
    entry_number: Annotated[
        int,
        typer.Argument(
            metavar="ENTRY_NUMBER",
            help="Transaction number shown by the asset log.",
        ),
    ],
    portfolio: Annotated[str, PORTFOLIO_OPTION],
    amount: Annotated[
        str | None,
        typer.Option("--amount", help="Replacement income amount."),
    ] = None,
    price: Annotated[
        str | None,
        typer.Option("--price", help="Replacement trade unit price."),
    ] = None,
    quantity: Annotated[
        str | None,
        typer.Option("--quantity", help="Replacement trade quantity."),
    ] = None,
    fee: Annotated[
        str | None,
        typer.Option("--fee", help="Replacement trade fee."),
    ] = None,
    total: Annotated[
        str | None,
        typer.Option("--total", help="Replacement trade total."),
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
        typer.Option("--note", help="Replacement transaction note."),
    ] = None,
) -> None:
    """Edit one asset transaction by its asset-local number."""
    if all(
        value is None for value in (amount, price, quantity, fee, total, date, note)
    ):
        print_error(
            "Provide at least one of --amount, --price, --quantity, --fee, "
            "--total, --date, or --note."
        )
        raise typer.Exit(code=1)

    try:
        normalized_symbol = normalize_symbol(symbol)
        transaction_date = None if date is None else parse_transaction_date(date)
        edit_asset_transaction_entry(
            portfolio,
            normalized_symbol,
            entry_number,
            amount=amount,
            price=price,
            quantity=quantity,
            fee=fee,
            total=total,
            transaction_date=transaction_date,
            note=note,
        )
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(
        f"Asset transaction {entry_number} updated for asset '{normalized_symbol}' "
        f"in portfolio '{portfolio}'."
    )


@asset_app.command("income", context_settings={"ignore_unknown_options": True})
def asset_income(
    symbol: Annotated[str, typer.Argument(help="Asset symbol.")],
    amount: Annotated[str, typer.Argument(help="Asset income amount.")],
    portfolio: Annotated[str, PORTFOLIO_OPTION],
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
        normalized_symbol = normalize_symbol(symbol)
        amount_minor = parse_amount_minor(amount)
        transaction_date = (
            local_date.today() if date is None else parse_transaction_date(date)
        )
        record_income(
            portfolio,
            normalized_symbol,
            amount_minor,
            transaction_date,
            note,
        )
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(
        f"Income recorded for asset '{normalized_symbol}' in portfolio '{portfolio}'."
    )


@asset_app.command("buy")
def asset_buy(
    symbol: Annotated[str, typer.Argument(help="Asset symbol.")],
    portfolio: Annotated[str, PORTFOLIO_OPTION],
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
        normalized_symbol = normalize_symbol(symbol)
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
            normalized_symbol,
            parsed_price,
            parsed_quantity,
            fee_minor,
            total_minor,
            transaction_date,
            note,
        )
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(
        f"Buy recorded for asset '{normalized_symbol}' in portfolio '{portfolio}'."
    )


@asset_app.command("sell")
def asset_sell(
    symbol: Annotated[str, typer.Argument(help="Asset symbol.")],
    portfolio: Annotated[str, PORTFOLIO_OPTION],
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
        normalized_symbol = normalize_symbol(symbol)
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
            normalized_symbol,
            parsed_price,
            parsed_quantity,
            fee_minor,
            total_minor,
            transaction_date,
            note,
        )
    except MpalError as error:
        print_error(str(error))
        raise typer.Exit(code=1) from error

    print_success(
        f"Sell recorded for asset '{normalized_symbol}' in portfolio '{portfolio}'."
    )
