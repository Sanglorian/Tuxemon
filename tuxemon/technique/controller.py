# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Callable
from enum import Enum, auto
from functools import partial
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import TechEffectResult
from tuxemon.locale import T
from tuxemon.menu.interface import MenuItem
from tuxemon.session import Session
from tuxemon.states.monster_menu import MonsterMenuState
from tuxemon.technique.technique import Technique
from tuxemon.tools import open_dialog, show_result_as_dialog
from tuxemon.ui.menu_options import (
    ChoiceOption,
    MenuOptions,
    create_choice_options,
)

if TYPE_CHECKING:
    from tuxemon.monster import Monster
    from tuxemon.npc import NPC

logger = logging.getLogger(__name__)


class TechAction(Enum):
    USE = auto()
    CANCEL = auto()
    INSPECT = auto()


def noop_action() -> None:
    """A no-operation function for unhandled actions."""


class TechController:
    def __init__(
        self, session: Session, technique: Technique, character: NPC
    ) -> None:
        self.session = session
        self.technique = technique
        self.char = character

    def _show_tech_result(self, result: TechEffectResult) -> None:
        show_result_as_dialog(self.session, self.technique, result.success)

    def get_basic_action(self, key: str) -> Callable[[], None]:
        try:
            action_enum = TechAction[key.upper()]
        except KeyError:
            logger.warning(
                f"Unknown tech menu action key '{key}' for technique '{self.technique.slug}'"
            )
            return noop_action

        if action_enum == TechAction.USE:

            def action_use() -> None:
                self.session.client.remove_state_by_name("ChoiceState")
                monster_menu = MonsterMenuState(self.char.monsters)
                self.session.client.push_state(monster_menu)
                monster_menu.is_valid_entry = partial(self.technique.validate_monster, self.session)  # type: ignore[method-assign]
                monster_menu.on_menu_selection = self.get_monster_targeted_action(key)  # type: ignore[assignment]

            return action_use

        elif action_enum == TechAction.INSPECT:

            def action_inspect() -> None:
                self.session.client.remove_state_by_name("ChoiceState")
                open_dialog(
                    self.session.client,
                    [
                        f"Upon closer inspection, the {self.technique.name} is: {self.technique.description.lower()}"
                    ],
                )

            return action_inspect

        elif action_enum == TechAction.CANCEL:
            return lambda: self.session.client.remove_state_by_name(
                "ChoiceState"
            )

        return noop_action

    def get_monster_targeted_action(
        self, key: str
    ) -> Callable[[MenuItem[Monster]], None]:
        def action(menu_item: MenuItem[Monster]) -> None:
            monster = menu_item.game_object
            result = self.technique.use(self.session, monster, monster)
            self.session.client.remove_state_by_name("MonsterMenuState")
            self.session.client.remove_state_by_name("TechniqueMenuState")
            self.session.client.remove_state_by_name("WorldMenuState")
            self._show_tech_result(result)

        return action

    def _default_cancel_option(self) -> ChoiceOption:
        return ChoiceOption(
            key="cancel",
            display_text=T.translate("item_confirm_cancel").upper(),
            action=lambda: self.session.client.remove_state_by_name(
                "ChoiceState"
            ),
        )

    def get_confirm_menu_options(self) -> MenuOptions:
        actions: dict[str, Callable[..., None]] = {}

        if self.technique.menu_actions_data:
            for action_data in self.technique.menu_actions_data:
                key = action_data.get("key")
                if key:
                    actions[key] = self.get_basic_action(key)

            options = create_choice_options(actions)

            for opt, action_data in zip(
                options, self.technique.menu_actions_data
            ):
                if "display_text" in action_data:
                    opt.display_text = action_data["display_text"]
                elif not action_data.get("key"):
                    opt.display_text = "Unnamed Option"
        else:
            if self.technique.confirm_text:
                actions["use"] = self.get_basic_action("use")
            if self.technique.cancel_text:
                actions["cancel"] = self.get_basic_action("cancel")

            options = create_choice_options(actions)

            for opt in options:
                if opt.key == "use" and self.technique.confirm_text:
                    opt.display_text = self.technique.confirm_text.upper()
                elif opt.key == "cancel" and self.technique.cancel_text:
                    opt.display_text = self.technique.cancel_text.upper()

        if not any(
            opt.key.strip().lower() in ("cancel", "back", "close")
            for opt in options
        ):
            options.append(self._default_cancel_option())

        return MenuOptions(options)
