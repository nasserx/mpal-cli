"""Rich terminal output helpers."""

from decimal import Decimal, localcontext
from typing import TYPE_CHECKING

from rich._loop import loop_first_last, loop_last
from rich._pick import pick_bool
from rich.console import Console
from rich.segment import Segment
from rich.style import Style
from rich.table import Table
from rich.text import Span, Text

from mpal.amounts import format_money
from mpal.numbers import (
    format_price_display,
    format_quantity,
    infer_price_display_scale,
)
from mpal.output.formatting import (
    format_asset_portfolio_header,
    format_asset_portfolio_label,
    format_capital_entry_amount,
    format_capital_entry_type,
    format_income_money,
    format_profit_loss_money,
    format_profit_loss_percent,
    style_transaction_type,
)
from mpal.output.theme import (
    ERROR,
    INFO,
    MUTED,
    ROW_KEY,
    ROW_SEPARATOR,
    SUCCESS,
    TABLE_BORDER,
    TABLE_BOX,
    TABLE_CELL,
    TABLE_HEADER,
    WARNING,
)

if TYPE_CHECKING:
    from rich.console import ConsoleOptions, RenderResult
from mpal.storage.asset_logs import AssetTransaction
from mpal.storage.assets import Asset
from mpal.storage.logs import CapitalEntry, CapitalState
from mpal.storage.summaries import PortfolioSummary

STANDARD_TABLE_WIDTH = 110
ROW_KEY_COLUMN_HEADERS = frozenset(
    {"#", "Portfolio", "Asset", "Symbol", "Asset/Portfolio"}
)


def print_message(message: str) -> None:
    """Print a normal text message through Rich."""
    _print_styled_message(message, TABLE_CELL)


def print_success(message: str) -> None:
    """Print a successful operation message."""
    _print_styled_message(message, SUCCESS)


def print_error(message: str) -> None:
    """Print an expected user-facing error."""
    _print_styled_message(message, ERROR, stderr=True)


def print_info(message: str) -> None:
    """Print secondary informational output."""
    _print_styled_message(message, INFO)


def print_warning(message: str) -> None:
    """Print a warning or confirmation-related error."""
    _print_styled_message(message, WARNING, stderr=True)


def _print_styled_message(
    message: str,
    style: str,
    *,
    stderr: bool = False,
) -> None:
    """Print literal message text with one semantic style."""
    Console(stderr=stderr).print(Text(message, style=style))


def print_portfolio_summary(summary: PortfolioSummary) -> None:
    """Print one portfolio summary using the documented columns."""
    print_portfolio_summaries([summary])


def print_portfolio_summaries(summaries: list[PortfolioSummary]) -> None:
    """Print portfolio summaries using the documented columns."""
    table = _make_table()
    table.add_column("Portfolio")
    table.add_column("Capital", justify="right")
    table.add_column("Cash", justify="right")
    table.add_column("Positions", justify="right")
    table.add_column("Book Value", justify="right")
    table.add_column("Realized PnL", justify="right")
    table.add_column("Income", justify="right")
    table.add_column("Return", justify="right")
    for summary in summaries:
        table.add_row(
            summary.portfolio_name,
            format_money(summary.capital_minor),
            format_money(summary.cash_minor),
            format_money(summary.positions_minor),
            format_money(summary.book_value_minor),
            format_profit_loss_money(summary.realized_pnl_minor),
            format_income_money(summary.income_minor),
            format_profit_loss_percent(
                summary.realized_pnl_minor + summary.income_minor,
                summary.capital_minor,
            ),
        )
    _print_table(table)


def print_assets(assets: list[Asset]) -> None:
    """Print active asset current-state rows."""
    table = _make_table()
    table.add_column(format_asset_portfolio_header())
    table.add_column("Quantity", justify="right")
    table.add_column("Cost Basis", justify="right")
    table.add_column("Average Cost", justify="right")
    table.add_column("Realized PnL", justify="right")
    table.add_column("Income", justify="right")
    table.add_column("Realized Return", justify="right")
    for asset in assets:
        table.add_row(
            format_asset_portfolio_label(asset.symbol, asset.portfolio_name),
            format_quantity(asset.quantity),
            format_money(asset.cost_basis_minor),
            _format_average_cost(
                asset.cost_basis_minor,
                asset.quantity,
                asset.price_display_scale,
            ),
            format_profit_loss_money(asset.realized_pnl_minor),
            format_income_money(asset.income_minor),
            format_profit_loss_percent(
                asset.realized_pnl_minor + asset.income_minor,
                asset.total_buy_cost_minor,
            ),
        )
    _print_table(table)


def print_asset_summary(portfolio_name: str, asset: Asset) -> None:
    """Print one active asset's derived accounting summary."""
    table = _make_table()
    table.add_column("Quantity", justify="right")
    table.add_column("Cost Basis", justify="right")
    table.add_column("Average Cost", justify="right")
    table.add_column("Realized PnL", justify="right")
    table.add_column("Income", justify="right")
    table.add_column("Realized Return", justify="right")
    table.add_row(
        format_quantity(asset.quantity),
        format_money(asset.cost_basis_minor),
        _format_average_cost(
            asset.cost_basis_minor,
            asset.quantity,
            asset.price_display_scale,
        ),
        format_profit_loss_money(asset.realized_pnl_minor),
        format_income_money(asset.income_minor),
        format_profit_loss_percent(
            asset.realized_pnl_minor + asset.income_minor,
            asset.total_buy_cost_minor,
        ),
    )
    _print_table(table)


def print_asset_transaction_log(
    portfolio_name: str,
    symbol: str,
    transactions: list[AssetTransaction],
) -> None:
    """Print one asset's active transactions using the documented columns."""
    table = _make_table()
    table.add_column("#", justify="right")
    table.add_column("Date")
    table.add_column("Type")
    table.add_column("Price", justify="right")
    table.add_column("Quantity", justify="right")
    table.add_column("Fee", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Note")
    price_display_scale = infer_price_display_scale(
        [transaction.price_text for transaction in transactions]
    )
    for transaction in transactions:
        table.add_row(
            str(transaction.entry_no),
            transaction.transaction_date,
            style_transaction_type(transaction.transaction_type),
            (
                "--"
                if transaction.price_text is None
                else format_price_display(
                    transaction.price_text,
                    price_display_scale,
                )
            ),
            (
                "--"
                if transaction.quantity_text is None
                else format_quantity(transaction.quantity_text)
            ),
            (
                "--"
                if transaction.transaction_type == "income"
                else format_money(transaction.fee_minor)
            ),
            (
                format_income_money(transaction.total_minor)
                if transaction.transaction_type == "income"
                else format_money(transaction.total_minor)
            ),
            Text(transaction.note, style=MUTED) if transaction.note else "",
        )
    _print_table(table)


def _format_average_cost(
    cost_basis_minor: int,
    quantity: Decimal,
    price_display_scale: int,
) -> str:
    """Format derived unit book cost with deterministic price precision."""
    if quantity == 0:
        return "--"
    with localcontext() as context:
        context.prec = 80
        average_cost = Decimal(cost_basis_minor) / Decimal(100) / quantity
    return format_price_display(average_cost, price_display_scale)


def print_capital_entry_log(entries: list[CapitalEntry]) -> None:
    """Print active capital entries using the documented log columns."""
    table = _make_table()
    table.add_column("#", justify="right")
    table.add_column("Date")
    table.add_column("Type")
    table.add_column("Amount", justify="right")
    table.add_column("Note")
    for entry in entries:
        table.add_row(
            str(entry.entry_no),
            entry.entry_date,
            format_capital_entry_type(entry.entry_type),
            format_capital_entry_amount(entry.entry_type, entry.amount_minor),
            Text(entry.note, style=MUTED) if entry.note else "",
        )
    _print_table(table)


def print_capital_state(state: CapitalState) -> None:
    """Print capital-only current state for one portfolio."""
    table = _make_table()
    table.add_column("Portfolio")
    table.add_column("Deposits", justify="right")
    table.add_column("Withdrawals", justify="right")
    table.add_column("Net Capital", justify="right")
    table.add_row(
        state.portfolio_name,
        format_capital_entry_amount("inflow", state.deposits_minor),
        format_capital_entry_amount("outflow", state.withdrawals_minor),
        format_money(state.net_capital_minor),
    )
    _print_table(table)


def _make_table() -> Table:
    """Create mpal's shared row-oriented Rich table."""
    return MpalTable(
        box=TABLE_BOX,
        header_style=TABLE_HEADER,
        border_style=TABLE_BORDER,
        style=TABLE_CELL,
        row_separator_style=ROW_SEPARATOR,
        show_lines=False,
    )


def _print_table(table: Table) -> None:
    """Print a table with mpal's shared responsive width policy."""
    Console(width=_table_console_width()).print(table)


def _table_console_width() -> int:
    """Return the console width used for data table rendering."""
    console = Console()
    if not console.is_terminal:
        return STANDARD_TABLE_WIDTH
    return min(console.size.width, STANDARD_TABLE_WIDTH)


class MpalTable(Table):
    """Rich table with mpal's rounded, row-oriented separators."""

    def __init__(self, *args, row_separator_style: str, **kwargs) -> None:
        kwargs.setdefault("min_width", STANDARD_TABLE_WIDTH)
        super().__init__(*args, **kwargs)
        self.row_separator_style = row_separator_style

    def add_column(self, *args, **kwargs) -> None:
        """Add a column, styling identity-column body values as row keys."""
        header = args[0] if args else kwargs.get("header", "")
        if not self.columns and _is_row_key_header(header) and "style" not in kwargs:
            kwargs["style"] = ROW_KEY
        super().add_column(*args, **kwargs)

    def add_row(self, *renderables, style=None, end_section: bool = False) -> None:
        """Add a row, applying row-key styling to identity first-column cells."""
        if renderables and self.columns and _is_row_key_header(self.columns[0].header):
            renderables = (
                _style_row_key_renderable(renderables[0]),
                *renderables[1:],
            )
        super().add_row(*renderables, style=style, end_section=end_section)

    def _render(
        self,
        console: Console,
        options: "ConsoleOptions",
        widths: list[int],
    ) -> "RenderResult":
        table_style = console.get_style(self.style or "")

        border_style = table_style + console.get_style(self.border_style or "")
        row_separator_style = table_style + console.get_style(self.row_separator_style)
        _column_cells = (
            self._get_cells(console, column_index, column)
            for column_index, column in enumerate(self.columns)
        )

        row_cells = list(zip(*_column_cells))
        _box = (
            self.box.substitute(
                options,
                safe=pick_bool(self.safe_box, console.safe_box),
            )
            if self.box
            else None
        )
        _box = _box.get_plain_headed_box() if _box and not self.show_header else _box

        new_line = Segment.line()

        columns = self.columns
        show_header = self.show_header
        show_footer = self.show_footer
        show_edge = self.show_edge

        if _box:
            box_segments = [
                (
                    Segment(_box.head_left, border_style),
                    Segment(_box.head_right, border_style),
                    Segment(_box.head_vertical, border_style),
                ),
                (
                    Segment(_box.mid_left, border_style),
                    Segment(_box.mid_right, border_style),
                    Segment(_box.mid_vertical, border_style),
                ),
                (
                    Segment(_box.foot_left, border_style),
                    Segment(_box.foot_right, border_style),
                    Segment(_box.foot_vertical, border_style),
                ),
            ]
            if show_edge:
                yield Segment(_box.get_top(widths), border_style)
                yield new_line
        else:
            box_segments = []

        get_row_style = self.get_row_style
        get_style = console.get_style

        for index, (first, last, row_cell) in enumerate(loop_first_last(row_cells)):
            header_row = first and show_header
            footer_row = last and show_footer
            row = (
                self.rows[index - show_header]
                if (not header_row and not footer_row)
                else None
            )
            max_height = 1
            cells = []
            if header_row or footer_row:
                row_style = Style.null()
            else:
                row_style = get_style(
                    get_row_style(console, index - 1 if show_header else index)
                )
            for width, cell, column in zip(widths, row_cell, columns):
                render_options = options.update(
                    width=width,
                    justify=column.justify,
                    no_wrap=column.no_wrap,
                    overflow=column.overflow,
                    height=None,
                    highlight=column.highlight,
                )
                lines = console.render_lines(
                    cell.renderable,
                    render_options,
                    style=get_style(cell.style) + row_style,
                )
                max_height = max(max_height, len(lines))
                cells.append(lines)

            row_height = max(len(cell) for cell in cells)

            def align_cell(cell, vertical: str, width: int, style: Style):
                if header_row:
                    vertical = "bottom"
                elif footer_row:
                    vertical = "top"

                if vertical == "top":
                    return Segment.align_top(cell, width, row_height, style)
                if vertical == "middle":
                    return Segment.align_middle(cell, width, row_height, style)
                return Segment.align_bottom(cell, width, row_height, style)

            cells[:] = [
                Segment.set_shape(
                    align_cell(
                        cell,
                        _cell.vertical,
                        width,
                        get_style(_cell.style) + row_style,
                    ),
                    width,
                    max_height,
                )
                for width, _cell, cell, column in zip(widths, row_cell, cells, columns)
            ]

            if _box:
                if last and show_footer:
                    yield Segment(
                        _box.get_row(widths, "foot", edge=show_edge),
                        border_style,
                    )
                    yield new_line
                left, right, _divider = box_segments[0 if first else (2 if last else 1)]

                divider = (
                    _divider
                    if _divider.text.strip()
                    else Segment(
                        _divider.text,
                        row_style.background_style + _divider.style,
                    )
                )
                for line_no in range(max_height):
                    if show_edge:
                        yield left
                    for last_cell, rendered_cell in loop_last(cells):
                        yield from rendered_cell[line_no]
                        if not last_cell:
                            yield divider
                    if show_edge:
                        yield right
                    yield new_line
            else:
                for line_no in range(max_height):
                    for rendered_cell in cells:
                        yield from rendered_cell[line_no]
                    yield new_line

            if _box and first and show_header:
                yield Segment(
                    _box.get_row(widths, "head", edge=show_edge),
                    border_style,
                )
                yield new_line

            if self._should_render_row_separator(
                row=row,
                last=last,
                header_row=header_row,
                footer_row=footer_row,
                index=index,
                row_cells=row_cells,
            ):
                yield from self._render_row_separator(
                    widths,
                    border_style=border_style,
                    row_separator_style=row_separator_style,
                )
                yield new_line

        if _box and show_edge:
            yield Segment(_box.get_bottom(widths), border_style)
            yield new_line

    def _should_render_row_separator(
        self,
        *,
        row,
        last: bool,
        header_row: bool,
        footer_row: bool,
        index: int,
        row_cells: list[tuple],
    ) -> bool:
        if self.show_lines or self.leading or (row and row.end_section):
            return False
        if header_row or footer_row or last:
            return False
        if self.show_footer and index >= len(row_cells) - 2:
            return False
        return True

    def _render_row_separator(
        self,
        widths: list[int],
        *,
        border_style: Style,
        row_separator_style: Style,
    ) -> "RenderResult":
        inner_width = sum(widths) + max(0, len(widths) - 1)
        separator = "─" * inner_width

        if self.show_edge:
            yield Segment("├", border_style)
        yield Segment(separator, row_separator_style)
        if self.show_edge:
            yield Segment("┤", border_style)


def _is_row_key_header(header) -> bool:
    if isinstance(header, Text):
        header_text = header.plain
    else:
        header_text = str(header)
    return header_text in ROW_KEY_COLUMN_HEADERS


def _style_row_key_renderable(renderable):
    if isinstance(renderable, Text):
        text = renderable.copy()
        if not text.style or str(text.style) == TABLE_CELL:
            text.style = ROW_KEY
        text.spans = [
            (
                Span(span.start, span.end, ROW_KEY)
                if not span.style or str(span.style) == TABLE_CELL
                else span
            )
            for span in text.spans
        ]
        return text
    return Text(str(renderable), style=ROW_KEY)
