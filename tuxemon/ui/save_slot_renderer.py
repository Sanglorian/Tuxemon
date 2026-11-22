# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from base64 import b64decode
from typing import TYPE_CHECKING

from pygame import SRCALPHA
from pygame.image import frombuffer
from pygame.surface import Surface
from pygame.transform import smoothscale

from tuxemon.locale.locale import T
from tuxemon.platform.const.graphics import FONT_COLOR, WHITE_COLOR

if TYPE_CHECKING:
    from pygame.font import Font
    from pygame.rect import Rect

    from tuxemon.save_system.save_state import SaveData
    from tuxemon.scaling import ScalingStrategy


def render_thumbnail(save_data: SaveData, rect: Rect) -> Surface:
    """Return a scaled thumbnail or fallback placeholder."""
    if (
        save_data.screenshot
        and save_data.screenshot_width
        and save_data.screenshot_height
    ):
        raw = b64decode(save_data.screenshot)
        size = (save_data.screenshot_width, save_data.screenshot_height)
        img = frombuffer(raw, size, "RGB").convert()
        thumb_rect = img.get_rect().fit(rect)
        return smoothscale(img, thumb_rect.size)

    # fallback
    thumb_rect = rect.copy()
    thumb_rect.width //= 5
    img = Surface(thumb_rect.size)
    img.fill(WHITE_COLOR)
    return img


# Text positions inside a slot, in nominal pixels. The label is vertically
# centred in the 24 px slot; the player name and save time are two lines,
# 10 px apart, in a column to the right of the thumbnail.
LABEL_TOP = 5
DETAILS_LEFT = 102
DETAILS_LINE_HEIGHT = 10


def _blit_text(
    surface: Surface, text: str, font: Font, position: tuple[int, int]
) -> None:
    surface.blit(font.render(text, True, FONT_COLOR), position)


def render_empty_slot(
    rect: Rect, scaling: ScalingStrategy, font: Font, slot: int
) -> Surface:
    """Render the 'empty slot' UI block."""
    slot_image = Surface(rect.size, SRCALPHA)

    label = (
        T.translate("menu_no_autosave")
        if slot == 0
        else T.translate("empty_slot")
    )

    _blit_text(slot_image, label, font, (0, scaling.scale_int(LABEL_TOP)))
    return slot_image


def render_slot_text(
    slot_image: Surface,
    rect: Rect,
    slot_label: str,
    save_data: SaveData,
    scaling: ScalingStrategy,
    font: Font,
) -> None:
    """Draw slot number, player name, and time."""
    _blit_text(slot_image, slot_label, font, (0, scaling.scale_int(LABEL_TOP)))

    x = scaling.scale_int(DETAILS_LEFT)
    if save_data.npc_state and save_data.npc_state.player_name:
        _blit_text(slot_image, save_data.npc_state.player_name, font, (x, 0))

    if save_data.time:
        y = scaling.scale_int(DETAILS_LINE_HEIGHT)
        _blit_text(slot_image, save_data.time, font, (x, y))
