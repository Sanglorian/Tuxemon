# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest

from tuxemon.core.asset import init_assets
from tuxemon.database.runtime import db
from tuxemon.db import (
    EvolutionStage,
    LearningMethod,
    MonsterModel,
    TechniqueModel,
)
from tuxemon.event.eventaction import ActionManager
from tuxemon.event.eventbehavior import BehaviorManager
from tuxemon.event.eventengine import EventEngine
from tuxemon.event.running import ConditionEvaluator
from tuxemon.game_variables import GameVariablesManager
from tuxemon.npc import PartyHandler
from tuxemon.player import Player
from tuxemon.session import local_session


def mock_player(self):
    self.name = "Jeff"
    self._variables = GameVariablesManager()
    self.tuxepedia = MagicMock()
    self.party = PartyHandler(MagicMock, self)


@pytest.fixture(scope="module")
def base_models():
    init_assets()
    dragon_attr = MagicMock(
        armour=7, dodge=5, hp=6, melee=6, ranged=6, speed=6
    )
    blob_attr = MagicMock(armour=8, dodge=4, hp=8, melee=4, ranged=8, speed=4)

    models = {
        "monster": {
            "agnite": MonsterModel(
                slug="agnite",
                species="false_dragon",
                moveset=[
                    {
                        "level_learned": 1,
                        "technique": "ram",
                        "learning_method": LearningMethod.FALLBACK,
                    }
                ],
                evolutions=[],
                history=[],
                tags=[],
                terrains=["coastal", "desert", "mountains"],
                shape="dragon",
                stage="basic",
                types=["fire"],
                gender_weights={"male": 0.5, "female": 0.5},
                txmn_id=13,
                height=80,
                weight=24,
                catch_rate=100.0,
                sounds={},
                lower_catch_resistance=0.95,
                upper_catch_resistance=1.25,
            ),
            "nut": MonsterModel(
                slug="nut",
                species="hardware",
                moveset=[
                    {
                        "level_learned": 1,
                        "technique": "ram",
                        "learning_method": LearningMethod.FALLBACK,
                    }
                ],
                evolutions=[],
                history=[],
                tags=[],
                terrains=[],
                shape="blob",
                stage="basic",
                types=["metal"],
                gender_weights={"neuter": 1.0},
                txmn_id=4,
                height=45,
                weight=4,
                catch_rate=100.0,
                sounds={},
                lower_catch_resistance=0.95,
                upper_catch_resistance=1.25,
            ),
        },
        "shape": {
            "dragon": MagicMock(slug="dragon", attributes=dragon_attr),
            "blob": MagicMock(slug="blob", attributes=blob_attr),
        },
        "element": {
            "fire": MagicMock(
                slug="fire",
                icon="gfx/ui/icons/element/fire_type.png",
                types=[],
            ),
            "metal": MagicMock(
                slug="metal",
                icon="gfx/ui/icons/element/metal_type.png",
                types=[],
            ),
        },
        "status": {
            "faint": MagicMock(
                effects=[],
                modifiers=[],
                visuals={"animation": None, "flip_axes": "", "loop": False},
                icon="gfx/ui/icons/status/icon_faint.png",
                sound={"sfx": "sfx_faint", "volume": 1.5},
                slug="faint",
                range="special",
                sort="meta",
                cond_id=0,
            )
        },
        "technique": {
            "ram": TechniqueModel(
                tech_id=69,
                accuracy=0.85,
                visuals={"animation": None, "flip_axes": "", "loop": False},
                potency=0.0,
                power=1.5,
                range="melee",
                recharge=1,
                sound={"sfx": "sfx_blaster", "volume": 1.5},
                slug="ram",
                sort="damage",
                behaviors={},
                target={
                    "enemy_monster": False,
                    "enemy_team": False,
                    "enemy_trainer": False,
                    "own_monster": False,
                    "own_team": False,
                    "own_trainer": False,
                },
                types=[],
                use_tech="combat_used_x",
                tags=["animal"],
                category="simple",
                effects=[],
                modifiers=[],
            )
        },
    }

    return models


@pytest.fixture
def game_env(monkeypatch, base_models):
    """Creates a fresh game environment for each test."""
    monkeypatch.setattr(Player, "__init__", mock_player)
    local_session.set_client(MagicMock())

    action = ActionManager()
    evaluator = ConditionEvaluator(MagicMock(), MagicMock())
    behavior = BehaviorManager()
    engine = EventEngine(local_session, action, evaluator, behavior)
    local_session.client.event_engine = engine

    local_session.set_player(Player())
    player = local_session.player

    for key, value in base_models.items():
        db.database[key] = value

    return engine, player


def test_add_monster(game_env):
    engine, player = game_env
    engine.execute_action("add_monster", ["agnite", 5])
    assert len(player.monsters) == 1
    assert player.monsters[0].slug == "agnite"


def test_random_monster(game_env):
    engine, player = game_env
    engine.execute_action("random_monster", [5])
    assert len(player.monsters) == 1
    assert player.monsters[0].slug in {"nut", "agnite"}


def test_random_monster_experience(game_env):
    engine, player = game_env
    engine.execute_action("random_monster", [5, None, 69])
    assert player.monsters[0].experience_modifier == 69


def test_random_monster_money(game_env):
    engine, player = game_env
    engine.execute_action("random_monster", [5, None, None, 69])
    assert player.monsters[0].money_modifier == 69


def test_random_monster_shape(game_env):
    engine, player = game_env
    engine.execute_action("random_monster", [5, None, None, None, "blob"])
    assert player.monsters[0].slug == "nut"


def test_random_monster_evolution(game_env):
    engine, player = game_env
    engine.execute_action(
        "random_monster", [5, None, None, None, None, "basic"]
    )
    assert player.monsters[0].stage == EvolutionStage.basic


def test_give_experience_no_change(game_env):
    engine, player = game_env
    engine.execute_action("random_monster", [5])
    before = player.monsters[0].total_experience
    engine.execute_action("give_experience", [None, None])
    assert player.monsters[0].total_experience == before


def test_give_experience_negative(game_env):
    engine, player = game_env
    engine.execute_action("random_monster", [5])
    before = player.monsters[0].total_experience
    engine.execute_action("give_experience", [None, -50])
    assert player.monsters[0].total_experience == before


def test_give_experience_positive(game_env):
    engine, player = game_env
    engine.execute_action("random_monster", [5])
    before = player.monsters[0].total_experience
    engine.execute_action("give_experience", [None, 50])
    assert player.monsters[0].total_experience == before + 50


def test_give_experience_variable(game_env):
    engine, player = game_env
    engine.execute_action("random_monster", [5])
    engine.execute_action("set_variable", ["exp:50"])
    before = player.monsters[0].total_experience
    engine.execute_action("give_experience", [None, "exp"])
    assert player.monsters[0].total_experience == before + 50
