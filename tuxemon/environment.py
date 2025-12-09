# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from typing import Optional

from tuxemon.db import (
    BattleGraphicsModel,
    BattleMusicModel,
    EnvironmentModel,
    db,
)

logger = logging.getLogger(__name__)


class EnvironmentManager:
    """
    Central service for loading, unloading, and delegating access to
    environment-specific battle settings (graphics, music, etc.).
    Ensures safe access to the active environment context.
    """

    def __init__(self) -> None:
        self._active_handler: Optional[Environment] = None
        logger.debug("EnvironmentManager initialized.")

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
        """
        Initializes the Environment with loaded data.
        """
        self.data = environment_data
        logger.debug(
            f"Environment initialized with data for slug: {self.data.slug}"
        )

    def get_battle_graphics(self) -> BattleGraphicsModel:
        """
        Returns the Pydantic model containing all graphics configuration
        for the current environment.
        """
        return self.data.get_battle_graphics()

    def get_battle_music(self) -> BattleMusicModel:
        """
        Returns the Pydantic model containing all music configuration
        for the current environment.
        """
        return self.data.get_battle_music()
