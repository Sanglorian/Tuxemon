# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pygame.rect import Rect

from tuxemon.database.runtime import db
from tuxemon.db import GenderType, MonsterModel
from tuxemon.event.actions.add_monster import AddMonsterAction
from tuxemon.locale.locale import T
from tuxemon.monster.monster import Monster
from tuxemon.monster.stats import IndividualValues
from tuxemon.platform.const.sizes import PLAYER_NAME_LIMIT
from tuxemon.states.combat_state import CombatState
from tuxemon.taste import Taste
from tuxemon.tools import show_nickname_prompt

MONSTER_SLUG = "rockitten"


class FakeState:
    """Records the name and keyword arguments of a pushed state."""

    def __init__(self, name: str, **kwargs: Any) -> None:
        self.name = name
        self.kwargs = kwargs


class FakeClient:
    """Minimal stand-in for the state stack driven by the nickname prompt."""

    def __init__(self) -> None:
        self.states: list[FakeState] = []
        self.npcs: dict[str, Any] = {}
        self.context = SimpleNamespace(rect=Rect(0, 0, 256, 144))

    def push_state(self, name: str, **kwargs: Any) -> FakeState:
        state = FakeState(name, **kwargs)
        self.states.append(state)
        return state

    def remove_state_by_name(self, name: str) -> None:
        self.states = [state for state in self.states if state.name != name]

    def get_npc(self, slug: str) -> Any:
        return self.npcs.get(slug)

    @property
    def active_state_names(self) -> list[str]:
        return [state.name for state in self.states]

    def find_state(self, name: str) -> FakeState | None:
        for state in self.states:
            if state.name == name:
                return state
        return None


class Counter:
    """Counts how many times it was called as an ``on_done`` callback."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1


def make_monster(slug: str = MONSTER_SLUG) -> Monster:
    """Builds a bare monster exposing the real ``name`` property."""
    monster = Monster.__new__(Monster)
    monster.slug = slug
    monster.instance_id = uuid4()
    monster._custom_name = None
    return monster


def get_choices(client: FakeClient) -> dict[str, Any]:
    """Maps the keys of the pushed choice dialog to their actions."""
    choice = client.find_state("ChoiceState")
    assert choice is not None
    return {
        option.key: option.action
        for option in choice.kwargs["menu"].get_menu()
    }


@pytest.fixture
def client() -> FakeClient:
    return FakeClient()


@pytest.fixture
def monster() -> Monster:
    return make_monster()


def test_prompt_asks_about_the_species(client, monster):
    monster.name = "Rocky"
    show_nickname_prompt(client, monster)

    dialog = client.find_state("DialogState")
    assert dialog is not None
    # the question is about the species, not the (already set) custom name
    assert dialog.kwargs["text"] == [
        T.format("give_nickname", {"name": T.translate(MONSTER_SLUG)})
    ]


def test_prompt_offers_no_before_yes(client, monster):
    show_nickname_prompt(client, monster)

    choice = client.find_state("ChoiceState")
    assert choice is not None
    assert choice.kwargs["escape_key_exits"] is False
    assert [option.key for option in choice.kwargs["menu"].get_menu()] == [
        "no",
        "yes",
    ]


def test_yes_opens_the_keyboard(client, monster):
    show_nickname_prompt(client, monster)
    get_choices(client)["yes"]()

    # the dialogs are torn down before the keyboard is shown
    assert client.active_state_names == ["InputMenu"]

    keyboard = client.find_state("InputMenu")
    assert keyboard is not None
    assert keyboard.kwargs["prompt"] == T.translate("input_monster_name")
    assert keyboard.kwargs["initial"] == ""
    assert keyboard.kwargs["char_limit"] == PLAYER_NAME_LIMIT
    assert keyboard.kwargs["escape_key_exits"] is False


def test_yes_sets_the_name(client, monster):
    done = Counter()
    show_nickname_prompt(client, monster, on_done=done)
    get_choices(client)["yes"]()

    keyboard = client.find_state("InputMenu")
    assert keyboard is not None
    keyboard.kwargs["callback"]("Rocky")

    assert monster.name == "Rocky"
    assert monster.name != T.translate(MONSTER_SLUG)
    assert done.calls == 1


def test_no_keeps_the_species_name(client, monster):
    done = Counter()
    show_nickname_prompt(client, monster, on_done=done)
    get_choices(client)["no"]()

    assert monster.name == T.translate(MONSTER_SLUG)
    assert monster._custom_name is None
    assert client.active_state_names == []
    assert done.calls == 1


def test_empty_input_keeps_the_species_name(client, monster):
    done = Counter()
    show_nickname_prompt(client, monster, on_done=done)
    get_choices(client)["yes"]()

    keyboard = client.find_state("InputMenu")
    assert keyboard is not None
    keyboard.kwargs["callback"]("")

    assert monster.name == T.translate(MONSTER_SLUG)
    assert monster._custom_name is None
    assert done.calls == 1


def test_on_done_fires_only_once(client, monster):
    done = Counter()
    show_nickname_prompt(client, monster, on_done=done)
    get_choices(client)["yes"]()

    keyboard = client.find_state("InputMenu")
    assert keyboard is not None
    keyboard.kwargs["callback"]("Rocky")
    keyboard.kwargs["callback"]("Pebbles")

    assert done.calls == 1


def test_prompt_without_callback_does_not_raise(client, monster):
    show_nickname_prompt(client, monster)
    get_choices(client)["no"]()

    assert client.active_state_names == []


@pytest.fixture
def trainer() -> Any:
    npc = MagicMock()
    npc.monsters = []
    return npc


@pytest.fixture
def session(client, trainer, monkeypatch) -> Any:
    monkeypatch.setitem(db.database, "monster", {MONSTER_SLUG: MagicMock()})
    client.npcs = {"player": trainer, "maple": trainer}

    session = MagicMock()
    session.client = client
    return session


def run_action(action: AddMonsterAction, session: Any) -> None:
    action.start(session)
    action.update(session, 0.0)


def test_add_monster_prompts_the_player(session, client, monster):
    action = AddMonsterAction(monster_slug=MONSTER_SLUG, monster_level=5)

    with patch.object(Monster, "spawn_base", return_value=monster):
        run_action(action, session)

    assert client.find_state("ChoiceState") is not None
    assert not action.done

    get_choices(client)["no"]()
    action.update(session, 0.0)
    assert action.done


def test_add_monster_for_npc_never_prompts(session, client, monster):
    action = AddMonsterAction(
        monster_slug=MONSTER_SLUG, monster_level=5, npc_slug="maple"
    )

    with patch.object(Monster, "spawn_base", return_value=monster):
        run_action(action, session)

    assert client.active_state_names == []
    assert action.done


def make_combat_state(captured: Monster | None, is_new: bool) -> Any:
    """A stub carrying only what the end-of-combat capture flow touches."""
    combat = MagicMock()
    combat._captured_mon = captured
    combat._captured_mon_is_new = is_new
    combat.name = "CombatState"
    return combat


def test_capture_prompts_before_leaving_combat(monster):
    combat = make_combat_state(monster, is_new=False)

    with patch(
        "tuxemon.states.combat_state.show_nickname_prompt"
    ) as fake_prompt:
        CombatState.end_combat(combat)

    # the prompt only goes up once the combat stack has been unwound
    combat.clear_combat_states.assert_called_once()
    fake_prompt.assert_called_once()
    args, kwargs = fake_prompt.call_args
    assert args[1] is monster
    assert kwargs["on_done"] == combat._after_capture

    # nothing else happens until the player answers
    combat._after_capture.assert_not_called()


def test_no_capture_skips_the_prompt(monster):
    combat = make_combat_state(None, is_new=False)

    with patch(
        "tuxemon.states.combat_state.show_nickname_prompt"
    ) as fake_prompt:
        CombatState.end_combat(combat)

    fake_prompt.assert_not_called()
    combat._after_capture.assert_called_once()


def test_new_species_still_shows_the_tuxepedia_entry(monster):
    combat = make_combat_state(monster, is_new=True)

    with patch("tuxemon.states.combat_state.MonsterModel") as model:
        CombatState._after_capture(combat)

    combat.client.remove_state_by_name.assert_called_once_with("CombatState")
    combat.client.push_state.assert_called_once_with(
        "JournalInfoState",
        character=combat.session.player,
        monster=model.lookup.return_value,
        source="CombatState",
        reveal=True,
    )


def test_known_species_leaves_combat(monster):
    combat = make_combat_state(monster, is_new=False)

    CombatState._after_capture(combat)

    combat.client.push_state.assert_called_once_with(
        "FadeOutTransition", caller=combat
    )


class FakeMonsterModel:
    """Just enough of a monster model to build a monster without assets."""

    species = "testspecies"
    stage = None
    tags: list[Any] = []
    terrains: list[Any] = []
    max_moves = 4
    txmn_id = 0
    catch_rate = 100
    upper_catch_resistance = 1.0
    lower_catch_resistance = 1.0
    gender_weights = {GenderType.NEUTER: 1.0}
    types: list[Any] = []
    shape = None
    randomly = False
    evolutions: list[Any] = []
    history: list[Any] = []
    moveset: list[Any] = []
    flairs: list[Any] = []
    sprites = None
    sounds = None
    height = 1.0
    weight = 1.0


@pytest.fixture
def saveable_monster(monkeypatch) -> Monster:
    """A monster complete enough to be serialized and read back."""
    monkeypatch.setattr(Taste, "_tastes", {})
    original_init = Monster.__init__

    def fake_init(self, slug=MONSTER_SLUG, db_data=None, instance_id=None):
        original_init(self, slug, db_data or FakeMonsterModel(), instance_id)

    monkeypatch.setattr(Monster, "__init__", fake_init)
    monkeypatch.setattr(Monster, "_init_assets", lambda self, db_data: None)
    monkeypatch.setattr(
        MonsterModel,
        "lookup",
        staticmethod(lambda slug, db: FakeMonsterModel()),
    )

    monster = Monster()
    monster.individual_values = IndividualValues()
    monster.flair_slugs = set()
    monster.flairs = {}
    return monster


def test_species_name_is_not_saved(saveable_monster):
    save_data = saveable_monster.get_state()

    # the species name follows the locale, so it must not reach the save file
    assert "name" not in save_data


def test_nickname_survives_a_save_round_trip(saveable_monster):
    saveable_monster.name = "Rocky"
    save_data = saveable_monster.get_state()

    assert save_data["name"] == "Rocky"
    assert Monster.from_save(save_data).name == "Rocky"


def test_saved_species_name_is_not_read_back_as_a_nickname(saveable_monster):
    # older saves stored the translated species name for every monster
    save_data = dict(saveable_monster.get_state())
    save_data["name"] = T.translate(MONSTER_SLUG)

    restored = Monster.from_save(save_data)
    assert restored._custom_name is None
    assert restored.name == T.translate(MONSTER_SLUG)
