# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""This module initializes the display, pygame, translations, and databases."""

from __future__ import annotations

import logging
import os

import pygame

from tuxemon.platform.const.sizes import NATIVE_RESOLUTION
from tuxemon.platform.const.sizes import TILE_SIZE as NATIVE_TILE_SIZE
from tuxemon.user_config import CONFIG

logger = logging.getLogger(__name__)

# Config-driven defaults
SCREEN_SIZE = CONFIG.resolution
TILE_SIZE = NATIVE_TILE_SIZE
SCALE = 1
DEV_TOOLS = CONFIG.dev_tools

Surface = pygame.Surface
Rect = pygame.Rect
SCREEN: Surface = Surface(CONFIG.resolution)
SCREEN_RECT: Rect = SCREEN.get_rect()


def pygame_init() -> None:
    """Initializes Pygame, display, translations, and databases."""
    core_init()
    from tuxemon import platform

    platform.init()

    global SCREEN, SCREEN_RECT, SCALE, TILE_SIZE

    import pygame as pg

    logger.debug("pygame init")
    pg.init()
    pg.display.set_caption(CONFIG.window_caption)

    if CONFIG.large_gui:
        SCALE = 2
    elif CONFIG.scaling:
        SCALE = int(SCREEN_SIZE[0] / NATIVE_RESOLUTION[0])

    TILE_SIZE = (NATIVE_TILE_SIZE[0] * SCALE, NATIVE_TILE_SIZE[1] * SCALE)

    from tuxemon.platform import is_android

    fullscreen = pg.FULLSCREEN if CONFIG.fullscreen else 0
    if is_android():
        fullscreen = pg.FULLSCREEN
    flags = pg.HWSURFACE | pg.DOUBLEBUF | fullscreen

    if CONFIG.vsync:
        pg.display.set_allow_screensaver()

    SCREEN = pg.display.set_mode(SCREEN_SIZE, flags, vsync=CONFIG.vsync)
    SCREEN_RECT = SCREEN.get_rect()

    pg.mouse.set_visible(not CONFIG.controller.hide_mouse)


def headless_init() -> None:
    """Initializes game components for a headless environment."""
    logger.debug("headless init")

    os.environ["SDL_VIDEODRIVER"] = "dummy"

    import pygame as pg

    pg.display.init()
    pg.font.init()

    global SCREEN, SCREEN_RECT

    SCREEN = pg.Surface(CONFIG.resolution)
    SCREEN_RECT = SCREEN.get_rect()

    core_init()


def core_init() -> None:
    from tuxemon.database.runtime import db
    from tuxemon.locale.locale import T

    T.initialize_translations(recompile=CONFIG.recompile_translations)
    db.load()
    logger.debug("Initializing core systems")
