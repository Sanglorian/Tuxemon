# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""Helpers that keep pygame_menu menus on the nominal pixel grid.

The game is drawn at a whole-number multiple (the scale) of its native
256x144 resolution, so one nominal pixel is ``scale`` screen pixels square.
A menu is "pixel perfect" when everything in it - the frame, the text, its
shadow and the cursor - starts on a multiple of the scale. These helpers do
that for menus that use Arbata, a pixel font drawn at its own pixel size.
"""

from __future__ import annotations

import types
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any

from pygame.rect import Rect
from pygame.surface import Surface
from pygame_menu.locals import ORIENTATION_VERTICAL
from pygame_menu.utils import make_surface

from tuxemon.config import LOCALE_FONT_MAP
from tuxemon.menu.theme import TuxemonArrowSelection
from tuxemon.tools import transform_resource_filename

if TYPE_CHECKING:
    from pygame_menu.menu import Menu
    from pygame_menu.themes import Theme
    from pygame_menu.widgets.core.widget import Widget

    from tuxemon.config import LocaleConfig
    from tuxemon.menu.menu import FontSettings

# Colour of the pixel drop shadow (#d8d8d8).
PIXEL_SHADOW_COLOR = (216, 216, 216)

# Arbata capitals sit 6 nominal px into each entry (2 px padding plus 4 px
# above the capitals); lowering the 9 px cursor 5 px centres it on them.
ARBATA_CURSOR_OFFSET = 5

# Padding (top, right, bottom, left) for compact Arbata entries, in nominal
# px. Arbata has 4 px of line above its capitals and 3 below, and the pixel
# shadow takes the first of those; 1 px of padding on top and 2 below
# leaves 5 px of space above the capitals and 5 below the shadow.
ARBATA_COMPACT_PADDING = (1, 4, 2, 4)
ARBATA_COMPACT_CURSOR_OFFSET = 4

# Compact entries are 18 nominal px tall (1 + 14 px line + 1 px shadow + 2).
# This margin brings a list of them to one entry per 14 px line.
ARBATA_COMPACT_MARGIN = -4


def uses_arbata(locale: LocaleConfig) -> bool:
    """Whether menus in this locale can use Arbata.

    Locales with their own font (e.g. CJK, which Arbata lacks) keep it.
    """
    return locale.font_file == LOCALE_FONT_MAP["default"][0]


def arbata_font(locale: LocaleConfig) -> str:
    """Path to the Arbata font file."""
    return transform_resource_filename("font", locale.arbata_font_file)


def apply_arbata(
    theme: Theme,
    locale: LocaleConfig,
    font_type: FontSettings,
    scale: int,
    compact: bool = False,
) -> None:
    """Set a (private copy of a) theme up for pixel-perfect Arbata entries.

    The shared theme's shadow is offset a fixed 2 screen px, off the nominal
    grid at most scales, so it's turned off: use ``apply_pixel_shadow`` on
    the entries instead.

    ``compact`` entries have balanced padding, for lists one line apart
    (give each entry ``ARBATA_COMPACT_MARGIN`` as its bottom margin).
    """
    theme.widget_font = arbata_font(locale)
    theme.widget_font_size = font_type.arbata
    theme.widget_font_shadow = False
    cursor_offset = ARBATA_CURSOR_OFFSET
    if compact:
        top, right, bottom, left = ARBATA_COMPACT_PADDING
        theme.widget_padding = (
            top * scale,
            right * scale,
            bottom * scale,
            left * scale,
        )
        cursor_offset = ARBATA_COMPACT_CURSOR_OFFSET
    theme.widget_selection_effect = TuxemonArrowSelection(
        scale, y_offset_nominal=cursor_offset
    )


def pixel_shadow_renderer(scale: int) -> Callable[..., Any]:
    """A pygame_menu text renderer with a 3-layer, 1 nominal px drop shadow.

    The shadow is three copies of the text in the shadow colour: 1 nominal px
    down, 1 down and right, and 1 right, so it stays on the pixel grid and
    has no gaps along diagonal strokes.
    """
    offsets = ((0, scale), (scale, scale), (scale, 0))

    def render(widget: Any, string: str, color: Any) -> Any:
        text = widget._font_render_string(string, color)
        shadow = widget._font_render_string(string, PIXEL_SHADOW_COLOR)
        surface = make_surface(
            text.get_width() + scale, text.get_height() + scale, alpha=True
        )
        for offset in offsets:
            surface.blit(shadow, offset)
        surface.blit(text, (0, 0))
        return surface

    return render


def apply_pixel_shadow(widgets: Iterable[Widget], scale: int) -> None:
    """Draw these widgets' text with the pixel drop shadow."""
    render = pixel_shadow_renderer(scale)
    for widget in widgets:
        widget._render_string = types.MethodType(  # type: ignore[method-assign]
            render, widget
        )
        widget._force_render()


# Row of a compact Arbata entry, in nominal px from the top of its padding,
# that an underline 3 px below the capitals (clear of descenders) sits on.
ARBATA_COMPACT_UNDERLINE_ROW = 14


def add_pixel_underline(
    label: Widget,
    scale: int,
    row: int,
    color: Any = None,
    shadow: bool = True,
) -> None:
    """Underline a (rendered) label with a 1 nominal px line on the grid.

    pygame_menu's own underline is drawn with pygame.draw.line, which
    centres it on a y that is usually between nominal pixels and includes
    both end points, so it spills a screen pixel past the text. This draws
    a filled rect under the text instead (not under its pixel shadow, if
    it has one), at ``row`` nominal px from the top of the label's padding.
    """
    width, height = label.get_size()
    _top, pad_right, _bottom, pad_left = label.get_padding()
    text_width = width - pad_left - pad_right - (scale if shadow else 0)
    # Decorations are placed relative to the centre of the padded rect.
    label.get_decorator().add_rect(
        pad_left - width // 2,
        row * scale - height // 2,
        Rect(0, 0, text_width, scale),
        color if color is not None else label.get_font_color_status(),
        # Over shadowed text, so descenders' shadows don't break the line.
        prev=not shadow,
    )


def snap(value: int, scale: int) -> int:
    """The nearest multiple of ``scale`` to ``value``."""
    return (value + scale // 2) // scale * scale


def snap_up(value: int, step: int) -> int:
    """The smallest multiple of ``step`` that is at least ``value``."""
    return -(-value // step) * step


Margin = tuple[int, int, int, int]
NO_MARGIN: Margin = (0, 0, 0, 0)

# Space around a block of compact Arbata entries inside a popup's frame, in
# nominal px (left, top, right, bottom). The entries' padding already gives
# 5 px above and below; on the left, 5 px of space before the cursor
# matches the space after the text.
ARBATA_POPUP_MARGIN: Margin = (5, 0, 0, 0)


def _laid_out_widgets(menu: Menu) -> list[Widget]:
    """The widgets pygame_menu places itself (not floating, not framed)."""
    return [
        widget
        for widget in menu.get_widgets()
        if widget.is_visible()
        and not widget.is_floating()
        and widget.get_frame() is None
    ]


def _widget_block(widgets: list[Widget]) -> tuple[int, int, int, int]:
    """The box (left, top, right, bottom) the widgets and their cursor use."""
    left = top = 10**9
    right = bottom = -(10**9)
    for widget in widgets:
        # The rect with padding; get_position() is inside the padding.
        x, y, width, height = widget.get_rect()
        m_top, m_left, m_bottom, m_right = (0, 0, 0, 0)
        if widget.is_selectable:
            m_top, m_left, m_bottom, m_right = (
                int(m) for m in widget.get_selection_effect().get_margin()
            )
        left = min(left, x - m_left)
        top = min(top, y - m_top)
        right = max(right, x + width + m_right)
        bottom = max(bottom, y + height + m_bottom)
    return left, top, right, bottom


def grid_menu_size(
    menu: Menu, scale: int, margin: Margin = NO_MARGIN
) -> tuple[int, int]:
    """The size, in whole nominal px, that fits the entries plus a margin.

    ``margin`` is (left, top, right, bottom) in nominal px; see
    ``keep_on_grid``.
    """
    widgets = _laid_out_widgets(menu)
    if not widgets:
        width, height = menu.get_size(widget=True)
        return width, height
    menu.render()
    left, top, right, bottom = _widget_block(widgets)
    m_left, m_top, m_right, m_bottom = margin
    width = right - left + (m_left + m_right) * scale
    height = bottom - top + (m_top + m_bottom) * scale
    return snap_up(width, scale), snap_up(height, scale)


def _snap_layout(menu: Menu, scale: int, margin: Margin, center: bool) -> None:
    """Move the widgets pygame_menu has just laid out onto the grid."""
    widgets = _laid_out_widgets(menu)
    if not widgets:
        return
    if not center:
        for widget in widgets:
            widget._rect.x = snap(widget._rect.x, scale)
            widget._rect.y = snap(widget._rect.y, scale)
        return
    left, top, right, bottom = _widget_block(widgets)
    m_left, m_top, m_right, m_bottom = (m * scale for m in margin)
    avail_w = menu.get_width(inner=True) - m_left - m_right
    avail_h = menu.get_height(inner=True) - m_top - m_bottom
    dx = dy = 0
    if right - left <= avail_w:
        target = m_left + (avail_w - (right - left)) // 2
        dx = target // scale * scale - left
    if bottom - top <= avail_h:
        target = m_top + (avail_h - (bottom - top)) // 2
        dy = target // scale * scale - top
    for widget in widgets:
        rect = widget._rect
        rect.x = snap(rect.x + dx, scale)
        rect.y = snap(rect.y + dy, scale)


def keep_on_grid(
    menu: Menu,
    scale: int,
    margin: Margin = NO_MARGIN,
    center: bool = True,
) -> None:
    """Keep the menu's entries on the nominal pixel grid.

    pygame_menu centres widgets (and the block of widgets) in whole screen
    pixels, and starts each column 1 screen px down, so entries usually land
    between nominal pixels. After every layout pass (the menu lays itself
    out again whenever it's resized or an entry changes size), this centres
    the block of entries, with their cursor, in the menu, inside ``margin``
    (left, top, right, bottom, in nominal px) and rounding down to the grid;
    then each entry, keeping its own alignment, is rounded to the nearest
    grid position. If the entries don't fit (the menu scrolls), or for menus
    laid out by hand (``center=False``), each is only rounded to the grid.

    The menu itself must be on the grid, and a whole number of nominal px
    in size. Floating widgets and widgets in frames are placed by hand, and
    left alone.
    """
    if scale <= 1:
        return
    update_widget_position = menu._update_widget_position

    def update_and_snap() -> None:
        update_widget_position()
        _snap_layout(menu, scale, margin, center)

    menu._update_widget_position = update_and_snap  # type: ignore[method-assign]
    menu.render()


# The scrollbar's slider and arrows: the dark purple of the menu frame, so
# they stand out against the pale track.
PIXEL_SCROLLBAR_COLOR = (156, 142, 206)

# Scrollbar track width, in nominal px. Odd, so the arrows have a point.
PIXEL_SCROLLBAR_WIDTH = 5

# Arrows at the ends of the scrollbar track, one row per string, pointing
# up ("#" is filled). Each sits in a cell as tall as the track is wide,
# with a 1 px gap on either side; the slider moves between the cells.
PIXEL_SCROLLBAR_ARROW = ("..#..", ".###.", "#####")
_ARROW_CELL = PIXEL_SCROLLBAR_WIDTH


def setup_pixel_scrolling(theme: Theme, scale: int) -> None:
    """Give a theme a scrollbar in whole nominal px, with a dark slider."""
    theme.scrollbar_thick = PIXEL_SCROLLBAR_WIDTH * scale
    theme.scrollbar_slider_pad = scale
    theme.scrollbar_slider_color = PIXEL_SCROLLBAR_COLOR
    theme.scrollbar_slider_hover_color = PIXEL_SCROLLBAR_COLOR


def _draw_scroll_arrows(surface: Surface, scale: int) -> None:
    """Draw the up and down arrows at the ends of a vertical scrollbar."""
    height = surface.get_height()
    rows = len(PIXEL_SCROLLBAR_ARROW)
    # Centred in the cell: 1 px above and below a 3 px arrow.
    gap = (_ARROW_CELL - rows) // 2
    for i, row in enumerate(PIXEL_SCROLLBAR_ARROW):
        for x, pixel in enumerate(row):
            if pixel != "#":
                continue
            up = (gap + i) * scale
            down = height - (gap + i + 1) * scale
            for y in (up, down):
                surface.fill(
                    PIXEL_SCROLLBAR_COLOR, Rect(x * scale, y, scale, scale)
                )


def snap_scrolling(menu: Menu, scale: int) -> None:
    """Keep a scrolling menu on the nominal pixel grid as it scrolls.

    pygame_menu scrolls by whole screen pixels (converted to and from the
    scrollbar's slider position, which rounds), so the entries drift off
    the grid. This rounds the scroll offsets, and the slider, to the grid.
    It also gives the vertical scrollbar an arrow at each end, with the
    slider moving between them. Use with ``setup_pixel_scrolling`` on the
    menu's theme.
    """
    if scale <= 1:
        return
    area = menu.get_scrollarea()
    get_offsets = area.get_offsets

    def snapped_offsets() -> tuple[int, int]:
        x, y = get_offsets()
        return snap(x, scale), snap(y, scale)

    area.get_offsets = snapped_offsets  # type: ignore[method-assign]

    # pygame_menu makes new scrollbars whenever the menu is resized.
    create_rect = area.create_rect

    def create_rect_and_patch(width: int, height: int) -> None:
        create_rect(width, height)
        for scrollbar in area._scrollbars:
            _patch_scrollbar(scrollbar, scale)

    area.create_rect = create_rect_and_patch  # type: ignore[method-assign]
    for scrollbar in area._scrollbars:
        _patch_scrollbar(scrollbar, scale)


def _patch_scrollbar(scrollbar: Any, scale: int) -> None:
    """Snap a scrollbar's slider to the grid, and give it arrows."""
    vertical = scrollbar.get_orientation() == ORIENTATION_VERTICAL
    update_slider_rect = scrollbar._update_slider_rect
    render = scrollbar._render

    def snapped_slider_rect() -> None:
        update_slider_rect()
        x, y, width, height = scrollbar._slider_rect
        if vertical:
            # pygame_menu never resets the slider's x, and shrinks it by
            # the padding each time; put it back in the middle.
            x = scrollbar._slider_pad
            # Squeeze the slider's travel in between the arrow cells.
            length = scrollbar._page_ctrl_length
            cell = _ARROW_CELL * scale
            travel = max(1, length - 2 * cell)
            y = cell + y * travel // length
            height = height * travel // length
        scrollbar._slider_rect = Rect(
            snap(x, scale),
            snap(y, scale),
            max(scale, snap(width, scale)),
            max(scale, snap(height, scale)),
        )

    def render_with_arrows() -> bool | None:
        result = render()
        if scrollbar._surface is not None:
            _draw_scroll_arrows(scrollbar._surface, scale)
        return result

    scrollbar._update_slider_rect = snapped_slider_rect
    if vertical:
        scrollbar._render = render_with_arrows
    if scrollbar._slider_rect is not None:
        scrollbar._update_slider_rect()


def spread_on_pixel_grid(menu: Menu, menu_height: int, scale: int) -> None:
    """Spread the entries evenly down the menu, in whole nominal pixels.

    This does what vertical fills would, but fills split the spare space
    into fractions of a nominal pixel, which blurs the grid. Instead every
    entry gets the same whole-pixel pitch (the largest that fits) and the
    block is centred, also on the grid.
    """
    widgets = menu.get_widgets()
    if not widgets:
        return
    entry_height = widgets[0].get_height()
    available = menu_height // scale
    pitch = available // len(widgets)
    block = (len(widgets) - 1) * pitch * scale + entry_height
    top = (available - block // scale) // 2

    menu._auto_centering = False
    for widget in widgets:
        widget.set_margin(0, pitch * scale - entry_height)
        # pygame_menu starts each column 1 screen px down; take it back off.
        widget.translate(0, top * scale - 1)
    menu.render()


def setup_pixel_theme(
    theme: Theme, locale: LocaleConfig, font_type: FontSettings, scale: int
) -> None:
    """Set a (private copy of a) theme up for a pixel-perfect list menu.

    The entries are compact Arbata, one 14 nominal px line apart, and the
    scrollbar (if any) is a whole number of nominal px. Pair it with
    ``finish_pixel_menu`` once the entries are added.
    """
    apply_arbata(theme, locale, font_type, scale, compact=True)
    theme.widget_margin = (0, scale * ARBATA_COMPACT_MARGIN)
    setup_pixel_scrolling(theme, scale)


def finish_pixel_menu(
    menu: Menu, scale: int, margin: Margin = NO_MARGIN
) -> None:
    """Shadow a pixel-perfect menu's entries and keep them on the grid."""
    apply_pixel_shadow(menu.get_widgets(), scale)
    keep_on_grid(menu, scale, margin)
    snap_scrolling(menu, scale)
