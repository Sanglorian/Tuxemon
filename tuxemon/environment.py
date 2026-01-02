# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from tuxemon.database.runtime import db
from tuxemon.db import (
    BattleGraphicsModel,
    BattleHudModel,
    BattleMusicModel,
    EnvironmentModel,
)
from tuxemon.tools import scale

if TYPE_CHECKING:
    from pygame.rect import Rect

logger = logging.getLogger(__name__)


@dataclass
class PartyLayout:
    path: str
    init_pos: dict[str, int]
    target: dict[str, int]
    centerx: int
    offset: int

    @classmethod
    def create(
        cls, side: str, home: Rect, hud: BattleHudModel, hud_layer: int
    ) -> PartyLayout:
        center_off = scale(hud.tray_center_offset)
        spacing_off = scale(hud.icon_spacing_offset)

        if side == "opponent":
            return cls(
                path=hud.tray_opponent,
                init_pos={
                    "bottom": home.bottom,
                    "right": 0,
                    "layer": hud_layer,
                },
                target={"right": home.right},
                centerx=home.right - center_off,
                offset=spacing_off,
            )

        return cls(
            path=hud.tray_player,
            init_pos={
                "bottom": home.bottom,
                "left": home.right,
                "layer": hud_layer,
            },
            target={"left": home.left},
            centerx=home.left + center_off,
            offset=-spacing_off,
        )


@dataclass
class BattleLayout:
    back_island_pos: dict[str, int]
    front_island_pos: dict[str, int]
    offsets: dict[str, int]

    @classmethod
    def create(
        cls,
        graphics: BattleGraphicsModel,
        screen_rect: tuple[int, int],
        player_home: Rect,
        opp_home: Rect,
    ) -> BattleLayout:
        w, _ = screen_rect
        y_mod = scale(graphics.island_offset_y)

        return cls(
            back_island_pos={"bottom": opp_home.bottom + y_mod, "right": 0},
            front_island_pos={"bottom": player_home.bottom - y_mod, "left": w},
            offsets={
                "enemy_y": scale(graphics.enemy_base_offset),
                "monster_y": scale(graphics.monster_base_offset),
                "player_y": scale(graphics.player_base_offset),
            },
        )


class EnvironmentManager:
    """
    Central service for loading, unloading, and delegating access to
    environment-specific battle settings (graphics, music, etc.).
    Ensures safe access to the active environment context.
    """

    def __init__(self) -> None:
        self._active_handler: Optional[Environment] = None
        logger.debug("EnvironmentManager initialized.")

    def update(self, dt: float) -> None:
        if self._active_handler:
            self._active_handler.update(dt)

    def load_environment(self, slug: str) -> bool:
        """
        Loads a new environment by creating an EnvironmentData and Environment object.
        Returns True on success, False on failure.
        """
        self._active_handler = None
        try:
            env_data = EnvironmentData(slug)
            self._active_handler = Environment(env_data)
            logger.debug(f"Successfully loaded environment: {slug}")
            return True
        except Exception as e:
            logger.error(f"Failed to load environment '{slug}': {e}")
            return False

    def unload_environment(self) -> None:
        """Explicitly unloads the current environment, often called when changing maps."""
        self._active_handler = None
        logger.debug("Environment unloaded.")

    def get_active_environment(self) -> Optional[Environment]:
        """Returns the currently active Environment, or None if none is loaded."""
        return self._active_handler


class EnvironmentData:
    """
    Loads environment configuration from the database using a slug.
    Provides access to graphics and music models. Acts as the data
    layer for Environment.
    """

    def __init__(self, slug: str) -> None:
        """
        Loads the environment data model based on the provided slug.
        """
        self.slug = slug
        try:
            self.environment_model = EnvironmentModel.lookup(slug, db)
        except RuntimeError as e:
            # EntryNotFoundError is wrapped into a RuntimeError in EnvironmentModel.lookup
            logger.error(str(e))
            raise e

    def get_battle_graphics(self) -> BattleGraphicsModel:
        """Returns the loaded battle graphics model."""
        return self.environment_model.battle_graphics

    def get_battle_music(self) -> BattleMusicModel:
        """Returns the loaded battle music model."""
        return self.environment_model.battle_music


class Environment:
    """
    Runtime wrapper around EnvironmentData. Exposes high-level accessors
    for graphics, music, and combat menu state used during battles.
    """

    def __init__(self, environment_data: EnvironmentData) -> None:
        self.data = environment_data
        self.elapsed_time = 0.0
        self._party_layouts: dict[str, PartyLayout] = {}
        self._battle_layout: Optional[BattleLayout] = None
        logger.debug(f"Environment initialized for slug: {self.data.slug}")

    def update(self, dt: float) -> None:
        self.elapsed_time += dt

    def get_battle_graphics(self) -> BattleGraphicsModel:
        return self.data.get_battle_graphics()

    def get_battle_music(self) -> BattleMusicModel:
        return self.data.get_battle_music()

    def get_battle_assets(self) -> dict[str, str]:
        graphics = self.data.get_battle_graphics()
        return {
            "background": graphics.background,
            "island_back": graphics.island_back,
            "island_front": graphics.island_front,
        }

    def get_party_layout(
        self, side: str, home: Rect, hud_layer: int
    ) -> PartyLayout:
        if side not in self._party_layouts:
            hud = self.data.get_battle_graphics().hud
            self._party_layouts[side] = PartyLayout.create(
                side, home, hud, hud_layer
            )
        return self._party_layouts[side]

    def get_battle_layout(
        self, screen_rect: tuple[int, int], player_home: Rect, opp_home: Rect
    ) -> BattleLayout:
        if not self._battle_layout:
            graphics = self.data.get_battle_graphics()
            self._battle_layout = BattleLayout.create(
                graphics, screen_rect, player_home, opp_home
            )
        return self._battle_layout
