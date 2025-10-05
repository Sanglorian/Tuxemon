# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import random
from functools import partial
from typing import ClassVar

from pygame_menu import locals
from pygame_menu.widgets.selection.highlight import HighlightSelection

from tuxemon import prepare
from tuxemon.combat.combat_context import (
    BattleMode,
    CombatContext,
    CombatType,
)
from tuxemon.constants.asset_loader import fetch_asset
from tuxemon.db import EnvironmentModel, db
from tuxemon.event import get_npc
from tuxemon.locale import T
from tuxemon.menu.menu import PygameMenuState
from tuxemon.player import Player
from tuxemon.session import local_session

DIFFICULTIES = ["beginner", "easy", "normal", "hard", "expert"]


class DifficultyBattleState(PygameMenuState):
    """
    A state that allows players to choose the difficulty level before entering the battle.
    """

    name: ClassVar[str] = "DifficultyBattleState"

    def __init__(self) -> None:
        width, height = prepare.SCREEN_SIZE
        super().__init__(height=height, width=width)

        self._build_menu()
        self.reset_theme()

    def _build_menu(self) -> None:
        """
        Constructs the difficulty selection menu with a title label and difficulty buttons.
        """
        title = T.translate("choose_difficulty")
        self.menu.add.label(
            title=title,
            font_size=self.font_type.big,
            align=locals.ALIGN_CENTER,
            underline=True,
        )

        for level in DIFFICULTIES:
            self.menu.add.button(
                title=T.translate(f"level_{level}"),
                action=partial(self.start_battle, level),
                button_id=f"diff_{level}",
                font_size=self.font_type.medium,
                selection_effect=HighlightSelection(),
                align=locals.ALIGN_CENTER,
            )

    def start_battle(self, difficulty: str) -> None:
        player = Player.create(local_session, slug=prepare.PLAYER_NPC)


        self.client.event_engine.execute_action(
            "create_npc", ["maple_girl", 0, 0], True
        )

        npc = get_npc(local_session, "maple_girl")
        if npc is None:
            return
        if difficulty == "beginner":
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(5, 10)]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(5, 10), npc.slug]
            )
        elif difficulty == "easy":
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(10, 15)]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(10, 15)]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(10, 15), npc.slug]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(10, 15), npc.slug]
            )
        elif difficulty == "normal":
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(15, 20)]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(15, 20)]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(15, 20)]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(15, 20), npc.slug]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(15, 20), npc.slug]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(15, 20), npc.slug]
            )
        elif difficulty == "hard":
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(20, 25)]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(20, 25)]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(20, 25)]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(20, 25)]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(20, 25), npc.slug]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(20, 25), npc.slug]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(20, 25), npc.slug]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(20, 25), npc.slug]
            )
        else:
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(25, 30)]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(25, 30)]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(25, 30)]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(25, 30)]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(25, 30)]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(25, 30), npc.slug]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(25, 30), npc.slug]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(25, 30), npc.slug]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(25, 30), npc.slug]
            )
            self.client.event_engine.execute_action(
                "random_monster", [random.randint(25, 30), npc.slug]
            )

        env = EnvironmentModel.lookup("grass", db)

        context = CombatContext(
            session=local_session,
            teams=[player, npc],
            combat_type=CombatType.TRAINER,
            graphics=env.battle_graphics,
            battle_mode=BattleMode.SINGLE,
        )
        self.client.push_state("CombatState", context=context)
        self.client.event_engine.execute_action(
            "play_music", [env.battle_music], True
        )
