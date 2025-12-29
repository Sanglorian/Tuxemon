# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""This module initializes the display, pygame, translations, and databases."""
from __future__ import annotations

import logging
import re

import pygame as pg

from tuxemon.platform.const.sizes import NATIVE_RESOLUTION
from tuxemon.platform.const.sizes import TILE_SIZE as NATIVE_TILE_SIZE
from tuxemon.user_config import CONFIG

logger = logging.getLogger(__name__)

# Config-driven defaults
SCREEN_SIZE = CONFIG.resolution
TILE_SIZE = NATIVE_TILE_SIZE
SCALE = 1
DEV_TOOLS = CONFIG.dev_tools

SCREEN: pg.surface.Surface = pg.Surface(CONFIG.resolution)  # dummy surface
SCREEN_RECT: pg.rect.Rect = pg.Rect(0, 0, *CONFIG.resolution)  # dummy rect
JOYSTICKS: list[pg.joystick.JoystickType] = []


def _compile_joystick_blacklist() -> list[re.Pattern[str]]:
    """Compiles a list of regex patterns for blacklisting joysticks."""
    logger.debug("Compiling joystick blacklist patterns.")
    return [
        re.compile(r"Microsoft.*Transceiver.*"),
        re.compile(r".*Synaptics.*", re.I),
        re.compile(r"Wacom*.", re.I),
    ]


joystick_blacklist = _compile_joystick_blacklist()


def pygame_init() -> None:
    """Initializes Pygame, display, translations, and databases."""
    from tuxemon import platform

    platform.init()

    global JOYSTICKS, SCREEN, SCREEN_RECT, SCALE, TILE_SIZE

    import pygame as pg

    from tuxemon.locale import T

    T.initialize_translations(recompile=CONFIG.recompile_translations)
    from tuxemon.database.runtime import db

    db.load()

    logger.debug("pygame init")
    pg.init()
    pg.display.set_caption(CONFIG.window_caption)

    # Calculate scale and adjusted TILE_SIZE
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

    # Joystick setup
    JOYSTICKS = []
    for i in range(pg.joystick.get_count()):
        try:
            joystick = pg.joystick.Joystick(i)
            name = joystick.get_name()
            print(f'Found joystick: "{name}"')
            if any(pattern.match(name) for pattern in joystick_blacklist):
                print(f'Ignoring joystick: "{name}"')
            else:
                print(f'Configuring joystick: "{name}"')
                JOYSTICKS.append(joystick)
        except Exception as e:
            logger.warning(f"Failed to initialize joystick {i}: {e}")
