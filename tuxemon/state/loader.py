# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import inspect
import logging
import sys
from collections.abc import Generator
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

from tuxemon.constants.paths import get_active_mod_paths, mods_folder
from tuxemon.plugin import PluginManager
from tuxemon.state.state import State

if TYPE_CHECKING:
    from tuxemon.state.repository import StateRepository

logger = logging.getLogger(__name__)


class StateLoader:
    """
    Handles the discovery, loading, and initial registration of game state
    classes.
    """

    def __init__(self, base_package: str, lib_dir: Path) -> None:
        """
        Initializes the StateLoader.

        Parameters:
            base_package: The base package name (e.g., "my_game.states") to
                scan for states.
            lib_dir: The base directory where game libraries are located
                (e.g., paths.LIBDIR).
        """
        self.base_package = base_package
        self.lib_dir = lib_dir

    @staticmethod
    def _collect_states_from_module(
        import_name: str,
    ) -> Generator[type[State], None, None]:
        """
        Given a module, return all classes in it that are a game state.
        """
        if import_name not in sys.modules:
            try:
                import_module(import_name)
            except ImportError as e:
                logger.error(
                    f"Failed to import module {import_name} during state collection: {e}"
                )
                return

        classes = inspect.getmembers(sys.modules[import_name], inspect.isclass)

        for c in (i[1] for i in classes):
            if issubclass(c, object) and c.__name__ != "State":
                try:
                    from .state import State as RealState

                    if issubclass(c, RealState) and not inspect.isabstract(c):
                        yield c
                except ImportError:
                    logger.warning(
                        "Could not import base 'State' class for type checking during discovery."
                    )

    def collect_states_from_path(
        self,
        folder: Path,
    ) -> Generator[type[State], None, None]:
        """
        Load states from disk, but do not register them.

        Parameters:
            folder: Folder to load from.

        Yields:
            Each game state class.
        """
        try:
            import_name = f"{self.base_package}.{folder.name}"
            import_module(import_name)
            yield from self._collect_states_from_module(import_name)
        except Exception as e:
            template = (
                "{} failed to load or is not a valid game state package: {}"
            )
            logger.error(template.format(folder.name, e))
            raise

    def auto_state_discovery(self, repository: StateRepository) -> None:
        """
        Discover and register game states from the main states folder and mod states folders.
        Only loads top-level modules from the main states folder.
        """
        state_folder = self.lib_dir / Path(*self.base_package.split(".")[1:])
        logger.info(f"Initiating game state discovery from {state_folder}")

        plugin_folders = []

        # Include top-level .py files from main states folder
        if state_folder.is_dir():
            top_level_modules = [
                f.stem
                for f in state_folder.glob("*.py")
                if f.is_file() and f.stem != "State"
            ]
            plugin_folders.append(state_folder)
        else:
            logger.warning(
                f"State discovery path does not exist: {state_folder}"
            )

        # Include mod states folders
        mod_state_folders = [
            mod_path / "states"
            for mod_path in get_active_mod_paths()
            if (mod_path / "states").is_dir()
        ]
        plugin_folders.extend(mod_state_folders)

        pm = PluginManager.from_directory(
            plugin_folders=plugin_folders,
            root_path=mods_folder.parent,
            include=(
                top_level_modules
                if plugin_folders and plugin_folders[0] == state_folder
                else []
            ),
            exclude=["State"],
        )

        for plugin in pm.get_all_plugins(interface=State):
            state_cls = plugin.plugin_object
            try:
                if not inspect.isabstract(state_cls):
                    repository.add_state(state_cls)
                    state_name = getattr(state_cls, "name", state_cls.__name__)
                    logger.info(f"Registered state: {state_name}")
                else:
                    logger.debug(
                        f"Skipped abstract state: {state_cls.__name__}"
                    )
            except Exception:
                logger.error(
                    f"Error registering state '{state_cls.__name__}'",
                    exc_info=True,
                )
