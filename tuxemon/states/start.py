# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""This module contains the Start state."""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar

from pygame.surface import Surface
from pygame_menu.locals import ALIGN_CENTER, POSITION_EAST
from pygame_menu.menu import Menu
from pygame_menu.themes import Theme

from tuxemon.database.runtime import db
from tuxemon.entity.npc import NPC
from tuxemon.launcher import GameLauncher
from tuxemon.locale.locale import T
from tuxemon.menu.menu import PygameMenuState
from tuxemon.menu.pixel_grid import (
    finish_pixel_menu,
    setup_pixel_theme,
    uses_arbata,
)
from tuxemon.platform.const.graphics import BG_START_SCREEN, BLACK_COLOR
from tuxemon.platform.const.sizes import PLAYER_NPC
from tuxemon.save_system.save import get_index_of_latest_save
from tuxemon.save_system.save_manager import SaveManager
from tuxemon.session import local_session
from tuxemon.state.state import State

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient

logger = logging.getLogger(__name__)


class BackgroundState(State):
    """
    Background state is used to prevent other states from
    being required to track dirty screen areas. For example,
    in the start state, there is a menu on a blank background,
    since menus do not clean up dirty areas, the blank,
    "Background state" will do that. The alternative is creating
    a system for states to clean up their dirty screen areas.

    Eventually the need for this will be phased out.
    """

    name: ClassVar[str] = "BackgroundState"

    def __init__(self, client: BaseClient, *args: Any, **kwargs: Any):
        super().__init__(client, *args, **kwargs)

    def draw(self, surface: Surface) -> None:
        surface.fill(BLACK_COLOR)


def setup_title_menu(state: PygameMenuState, theme: Theme) -> bool:
    """Set a title screen menu's theme up for Arbata, where the locale allows.

    Returns whether it did, i.e. whether the menu can be pixel perfect.
    """
    locale = state.client.config.locale
    if not uses_arbata(locale):
        return False
    scale = state.client.context.scaling.scale_int(1)
    setup_pixel_theme(theme, locale, state.font_type, scale)
    return True


def finish_title_menu(state: PygameMenuState, pixel_perfect: bool) -> None:
    """Give a title screen menu's entries their shadow and grid."""
    if pixel_perfect:
        scale = state.client.context.scaling.scale_int(1)
        finish_pixel_menu(state.menu, scale)


class StartState(PygameMenuState):
    """The state responsible for the start menu."""

    name: ClassVar[str] = "StartState"

    @property
    def _font_size(self) -> int:
        # Arbata has one (pixel) size, set by the theme.
        return (
            self.font_type.arbata if self.pixel_perfect else self.font_type.big
        )

    def add_menu_items(
        self,
        menu: Menu,
    ) -> None:
        # If there is a save, then move the cursor to "Load game" first
        index = get_index_of_latest_save()

        def new_game() -> None:
            launcher = GameLauncher(self.client)
            launcher.launch(
                session=local_session,
                meta=db.mod_metadata.get_mod_metadata(
                    self.client.config.mods[0]
                ),
                remove_states=["StartState"],
            )

        def change_state(
            state: State | str, **kwargs: Any
        ) -> Callable[[], None]:
            def _change() -> None:
                self.unsubscribe(
                    "afk.threshold_reached", self._on_afk_threshold
                )
                self.client.push_state(state, **kwargs)

            return _change

        def exit_game() -> None:
            self.client.quit()

        if index is not None:
            menu.add.button(
                title=T.translate("menu_load"),
                action=change_state("LoadMenuState"),
                font_size=self._font_size,
                button_id="menu_load",
            )

            if SaveManager.has_autosave():
                menu.add.button(
                    title=T.translate("menu_autosave"),
                    action=lambda: self.client.event_engine.execute_action(
                        "load_game",
                        [0, True],
                        True,
                    ),
                    font_size=self._font_size,
                    button_id="menu_autosave",
                )

        if len(self.client.config.mods) == 1:
            menu.add.button(
                title=T.translate("menu_new_game"),
                action=new_game,
                font_size=self._font_size,
                button_id="menu_new_game",
            )
        else:
            menu.add.button(
                title=T.translate("menu_new_game"),
                action=change_state(
                    "ModsChoice", mods=self.client.config.mods
                ),
                font_size=self._font_size,
                button_id="menu_mod_choice",
            )
        menu.add.button(
            title=T.translate("menu_battle"),
            action=change_state(
                "DifficultyPickState", on_pick=self.start_battle
            ),
            font_size=self._font_size,
            button_id="menu_battle",
        )
        menu.add.button(
            title=T.translate("menu_minigame"),
            action=change_state(
                "DifficultyPickState",
                on_pick=self.start_minigame,
                difficulties=["easy", "normal", "hard"],
            ),
            font_size=self._font_size,
            button_id="menu_minigame",
        )
        menu.add.button(
            title=T.translate("menu_options"),
            action=change_state("ControlState", main_menu=True),
            font_size=self._font_size,
            button_id="menu_options",
        )
        menu.add.button(
            title=T.translate("exit"),
            action=exit_game,
            font_size=self._font_size,
            button_id="exit",
        )

    def __init__(self, client: BaseClient, **kwargs: Any) -> None:
        width, height = client.context.resolution

        super().__init__(client=client, height=height, width=width, **kwargs)

        theme = self._setup_theme(BG_START_SCREEN)
        theme.scrollarea_position = POSITION_EAST
        theme.widget_alignment = ALIGN_CENTER
        self.pixel_perfect = setup_title_menu(self, theme)
        self._menu_config["theme"] = theme

        self.escape_key_exits = False
        self.client.afk_manager.add_threshold("IntroState", 15.0)
        self.event_bus.subscribe(
            "afk.threshold_reached", self._on_afk_threshold, priority=10
        )

        self.add_menu_items(self.menu)
        finish_title_menu(self, self.pixel_perfect)
        self.reset_theme()

    def _on_afk_threshold(self, level: str) -> None:
        if level == "IntroState":
            self.client.replace_state("IntroState")

    def shutdown(self) -> None:
        self.unsubscribe("afk.threshold_reached", self._on_afk_threshold)
        super().shutdown()

    def start_battle(self, difficulty: str) -> None:
        NPC.create_player(local_session, slug=PLAYER_NPC)
        self.client.push_state(
            "WorldState", session=local_session, map_name=None
        )
        self.client.event_engine.execute_action(
            "set_variable", [f"difficulty:{difficulty}"]
        )
        self.client.event_engine.execute_action("load_yaml", ["battle_menu"])

    def start_minigame(self, difficulty: str) -> None:
        self.client.push_state(
            "MinigameState",
            difficulty=difficulty,
            streak=0,
            score=0,
        )


class ModsChoice(PygameMenuState):
    """The state responsible for the mods menu."""

    name: ClassVar[str] = "ModsChoice"

    @property
    def _font_size(self) -> int:
        # Arbata has one (pixel) size, set by the theme.
        return (
            self.font_type.arbata if self.pixel_perfect else self.font_type.big
        )

    def add_menu_items(
        self,
        menu: Menu,
    ) -> None:

        def new_game(mod_name: str) -> None:
            launcher = GameLauncher(self.client)
            launcher.launch(
                session=local_session,
                meta=db.mod_metadata.get_mod_metadata(mod_name),
                remove_states=["StartState", "ModsChoice"],
            )

        for mod_name in self.mods:
            menu.add.button(
                title=T.translate(f"{mod_name}_campaign"),
                action=partial(new_game, mod_name),
                font_size=self._font_size,
                button_id=mod_name,
            )

    def __init__(
        self, client: BaseClient, mods: list[str], **kwargs: Any
    ) -> None:
        self.mods = mods
        width, height = client.context.resolution

        super().__init__(client=client, height=height, width=width, **kwargs)

        theme = self._setup_theme(BG_START_SCREEN)
        theme.scrollarea_position = POSITION_EAST
        theme.widget_alignment = ALIGN_CENTER
        self.pixel_perfect = setup_title_menu(self, theme)
        self._menu_config["theme"] = theme

        self.add_menu_items(self.menu)
        finish_title_menu(self, self.pixel_perfect)
        self.reset_theme()
