# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""Tests for the real-time planting system."""

from __future__ import annotations

import pytest

from tuxemon.farming.config import (
    FruitConfig,
    PlantingConfig,
    load_planting_config,
)
from tuxemon.farming.manager import FarmingManager
from tuxemon.farming.plot import (
    WET_DURATION,
    Plant,
    TilledTile,
    harvest_amount,
    merge_intervals,
    stage_index,
    wet_seconds,
    yield_value,
)

HOUR = 60 * 60.0
DAY = 24 * HOUR

# Three transitions, so four sprite stages, adding up to six minutes.
STAGES = [60.0, 120.0, 180.0]
GROW = sum(STAGES)

T0 = 1_700_000_000.0

CONFIG = PlantingConfig(
    fruits={
        "fire_berry": FruitConfig(
            slug="fire_berry",
            stage_seconds=list(STAGES),
            stages=["a.png", "b.png", "c.png", "d.png"],
        )
    }
)


class Clock:
    """A wall clock the tests can move."""

    def __init__(self, now: float = T0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def manager(clock: Clock) -> FarmingManager:
    return FarmingManager(clock=clock, config=CONFIG)


# -- stage selection ------------------------------------------------------


@pytest.mark.parametrize(
    ("elapsed", "expected"),
    [
        pytest.param(-5.0, 0, id="before-planting"),
        pytest.param(0.0, 0, id="just-planted"),
        pytest.param(59.9, 0, id="just-before-first-transition"),
        pytest.param(60.0, 1, id="on-first-transition"),
        pytest.param(179.9, 1, id="just-before-second-transition"),
        pytest.param(180.0, 2, id="on-second-transition"),
        pytest.param(359.9, 2, id="just-before-maturity"),
        pytest.param(360.0, 3, id="at-maturity"),
        pytest.param(100 * DAY, 3, id="long-after-maturity"),
    ],
)
def test_stage_index(elapsed: float, expected: int) -> None:
    assert stage_index(elapsed, STAGES) == expected


def test_stage_index_no_transitions() -> None:
    """A plant with no declared transitions is born in its only stage."""
    assert stage_index(0.0, []) == 0
    assert stage_index(1000.0, []) == 0


def test_plant_stage_uses_wall_clock() -> None:
    plant = Plant("fire_berry", T0, list(STAGES))
    assert plant.stage(T0) == 0
    assert plant.stage(T0 + 200) == 2
    assert plant.stage(T0 + GROW) == 3
    assert plant.stage_count == 4
    assert plant.matured_at == T0 + GROW
    assert not plant.is_mature(T0 + GROW - 0.1)
    assert plant.is_mature(T0 + GROW)


# -- the wet interval union ------------------------------------------------


@pytest.mark.parametrize(
    ("intervals", "expected"),
    [
        pytest.param([], [], id="empty"),
        pytest.param([(0.0, 5.0)], [(0.0, 5.0)], id="single"),
        pytest.param(
            [(5.0, 10.0), (0.0, 3.0)], [(0.0, 3.0), (5.0, 10.0)], id="sorted"
        ),
        pytest.param([(0.0, 5.0), (3.0, 8.0)], [(0.0, 8.0)], id="overlapping"),
        pytest.param([(0.0, 5.0), (5.0, 9.0)], [(0.0, 9.0)], id="touching"),
        pytest.param([(0.0, 9.0), (2.0, 4.0)], [(0.0, 9.0)], id="contained"),
        pytest.param([(4.0, 4.0)], [], id="zero-length-dropped"),
        pytest.param([(6.0, 2.0)], [], id="reversed-dropped"),
    ],
)
def test_merge_intervals(
    intervals: list[tuple[float, float]],
    expected: list[tuple[float, float]],
) -> None:
    assert merge_intervals(intervals) == expected


def test_wet_seconds_single_watering_inside_window() -> None:
    """A watering at planting time covers the whole six-minute growth."""
    assert wet_seconds([T0], T0, T0 + GROW) == GROW


def test_wet_seconds_watering_before_planting_still_counts() -> None:
    """Watering the soil an hour early still covers the growth window."""
    assert wet_seconds([T0 - HOUR], T0, T0 + GROW) == GROW


def test_wet_seconds_watering_long_before_planting_has_worn_off() -> None:
    assert wet_seconds([T0 - 2 * DAY], T0, T0 + GROW) == 0.0


def test_wet_seconds_overlapping_waterings_do_not_stack() -> None:
    """Two waterings an hour apart give 25 hours wet, not 48."""
    total = wet_seconds([T0, T0 + HOUR], T0, T0 + 3 * DAY)
    assert total == pytest.approx(DAY + HOUR)


def test_wet_seconds_separated_waterings_add_up() -> None:
    """Waterings that do not overlap contribute their full length each."""
    total = wet_seconds([T0, T0 + 3 * DAY], T0, T0 + 10 * DAY)
    assert total == pytest.approx(2 * DAY)


def test_wet_seconds_is_clipped_to_the_window() -> None:
    """Only the part of a wet period inside the window is counted."""
    assert wet_seconds([T0], T0 + 12 * HOUR, T0 + 36 * HOUR) == pytest.approx(
        12 * HOUR
    )


def test_wet_seconds_empty_window() -> None:
    assert wet_seconds([T0], T0, T0) == 0.0
    assert wet_seconds([T0], T0 + 10, T0) == 0.0


def test_watering_after_maturity_is_ignored() -> None:
    """The fraction freezes at maturity, so a late watering changes nothing."""
    plant = Plant("fire_berry", T0, list(STAGES))
    now = T0 + 7 * DAY
    dry = plant.watered_fraction([], now)
    late = plant.watered_fraction([T0 + GROW + HOUR], now)
    assert dry == 0.0
    assert late == 0.0


def test_fraction_is_measured_only_up_to_now_while_growing() -> None:
    """Halfway through growth, a watering can have covered at most half."""
    plant = Plant("fire_berry", T0, list(STAGES))
    fraction = plant.watered_fraction([T0], T0 + GROW / 2)
    assert fraction == pytest.approx(0.5)


def test_fraction_never_exceeds_one() -> None:
    plant = Plant("fire_berry", T0, list(STAGES))
    assert plant.watered_fraction([T0 - HOUR, T0], T0 + GROW) == 1.0


def test_fraction_of_an_instant_plant_is_zero() -> None:
    """A plant with no growth window cannot divide by it."""
    plant = Plant("fire_berry", T0, [])
    assert plant.watered_fraction([T0], T0) == 0.0


# -- fraction -> yield -> fruit -------------------------------------------


@pytest.mark.parametrize(
    ("fraction", "expected_yield", "expected_fruit"),
    [
        pytest.param(0.0, 1.00, 2, id="0-percent"),
        pytest.param(0.25, 1.25, 3, id="25-percent"),
        pytest.param(0.5, 1.50, 3, id="50-percent"),
        pytest.param(0.75, 1.75, 4, id="75-percent"),
        pytest.param(1.0, 2.00, 4, id="100-percent"),
    ],
)
def test_yield_table(
    fraction: float, expected_yield: float, expected_fruit: int
) -> None:
    assert yield_value(fraction) == pytest.approx(expected_yield)
    assert harvest_amount(fraction) == expected_fruit


@pytest.mark.parametrize(
    ("fraction", "expected"),
    [
        pytest.param(-1.0, 2, id="negative-clamped"),
        pytest.param(2.5, 4, id="above-one-clamped"),
    ],
)
def test_yield_is_clamped(fraction: float, expected: int) -> None:
    assert harvest_amount(fraction) == expected


def test_half_watered_does_not_round_up_to_four() -> None:
    """
    2 * 1.5 lands exactly on 3, and floating point must not push it to 4.

    A watering exactly halfway through growth covers half the window.
    """
    plant = Plant("fire_berry", T0, list(STAGES))
    tile = TilledTile(waterings=[T0 + GROW / 2], plant=plant)
    now = T0 + GROW
    assert tile.watered_fraction(now) == pytest.approx(0.5)
    assert tile.harvest_amount(now) == 3


# -- tile behaviour --------------------------------------------------------


def test_tile_wetness_expires_after_24_hours(clock: Clock) -> None:
    tile = TilledTile()
    tile.water(clock())
    assert tile.is_wet(clock())
    clock.advance(WET_DURATION - 1)
    assert tile.is_wet(clock())
    clock.advance(2)
    assert not tile.is_wet(clock())


def test_watering_again_restarts_the_24_hours(clock: Clock) -> None:
    tile = TilledTile()
    tile.water(clock())
    clock.advance(12 * HOUR)
    tile.water(clock())
    clock.advance(WET_DURATION - HOUR)
    assert tile.is_wet(clock()), "the second watering should still be running"


def test_waterings_are_kept_sorted() -> None:
    tile = TilledTile()
    tile.water(T0 + 100)
    tile.water(T0)
    assert tile.waterings == [T0, T0 + 100]


def test_pruning_keeps_only_waterings_that_still_matter() -> None:
    tile = TilledTile(waterings=[T0 - 2 * DAY, T0 - HOUR])
    tile.prune_waterings(T0)
    assert tile.waterings == [T0 - HOUR]


def test_pruning_leaves_a_planted_tile_alone() -> None:
    tile = TilledTile(
        waterings=[T0 - 2 * DAY], plant=Plant("fire_berry", T0, list(STAGES))
    )
    tile.prune_waterings(T0)
    assert tile.waterings == [T0 - 2 * DAY]


# -- manager ---------------------------------------------------------------


def test_till_marks_a_rectangle(manager: FarmingManager) -> None:
    assert manager.till("garden", 2, 3, 3, 2) == 6
    for x in (2, 3, 4):
        for y in (3, 4):
            assert manager.is_tilled("garden", (x, y))
    assert not manager.is_tilled("garden", (5, 3))
    assert not manager.is_tilled("garden", (2, 5))


def test_till_defaults_to_a_single_tile(manager: FarmingManager) -> None:
    assert manager.till("garden", 1, 1) == 1
    assert manager.is_tilled("garden", (1, 1))


def test_tilling_again_leaves_the_plant_alone(
    manager: FarmingManager,
) -> None:
    manager.till("garden", 0, 0)
    manager.plant("garden", (0, 0), "fire_berry")
    assert manager.till("garden", 0, 0, 2, 2) == 3
    tile = manager.get_tile("garden", (0, 0))
    assert tile is not None and tile.plant is not None


def test_plots_are_per_map(manager: FarmingManager) -> None:
    manager.till("garden", 0, 0)
    assert not manager.is_tilled("other_map", (0, 0))


def test_planting_requires_tilled_soil(manager: FarmingManager) -> None:
    assert manager.plant("garden", (0, 0), "fire_berry") is None


def test_planting_requires_a_plantable_item(manager: FarmingManager) -> None:
    manager.till("garden", 0, 0)
    assert manager.plant("garden", (0, 0), "potion") is None


def test_planting_fails_on_an_occupied_tile(manager: FarmingManager) -> None:
    manager.till("garden", 0, 0)
    assert manager.plant("garden", (0, 0), "fire_berry") is not None
    assert manager.plant("garden", (0, 0), "fire_berry") is None


def test_plant_copies_its_durations_from_config(
    manager: FarmingManager,
) -> None:
    """Retuning the config must not rewrite a plant already in the ground."""
    manager.till("garden", 0, 0)
    plant = manager.plant("garden", (0, 0), "fire_berry")
    assert plant is not None
    assert plant.stage_seconds == STAGES
    assert plant.stage_seconds is not CONFIG.fruits["fire_berry"].stage_seconds


def test_watering_an_empty_tilled_tile_counts_later(
    manager: FarmingManager, clock: Clock
) -> None:
    """A tile watered before planting is already wet when the seed goes in."""
    manager.till("garden", 0, 0)
    assert manager.water("garden", (0, 0))
    clock.advance(HOUR)
    manager.plant("garden", (0, 0), "fire_berry")
    clock.advance(GROW)
    tile = manager.get_tile("garden", (0, 0))
    assert tile is not None
    assert tile.watered_fraction(clock()) == pytest.approx(1.0)


def test_watering_untilled_ground_fails(manager: FarmingManager) -> None:
    assert not manager.water("garden", (0, 0))


def test_harvest_needs_a_mature_plant(
    manager: FarmingManager, clock: Clock
) -> None:
    manager.till("garden", 0, 0)
    manager.plant("garden", (0, 0), "fire_berry")
    assert not manager.can_harvest("garden", (0, 0))
    assert manager.harvest("garden", (0, 0)) is None

    clock.advance(GROW)
    assert manager.can_harvest("garden", (0, 0))
    assert manager.harvest("garden", (0, 0)) == ("fire_berry", 2)


def test_harvest_leaves_the_tile_tilled(
    manager: FarmingManager, clock: Clock
) -> None:
    manager.till("garden", 0, 0)
    manager.plant("garden", (0, 0), "fire_berry")
    clock.advance(GROW)
    manager.harvest("garden", (0, 0))

    assert manager.is_tilled("garden", (0, 0))
    tile = manager.get_tile("garden", (0, 0))
    assert tile is not None and tile.is_empty
    assert manager.plant("garden", (0, 0), "fire_berry") is not None


def test_harvest_of_a_fully_watered_plant(
    manager: FarmingManager, clock: Clock
) -> None:
    manager.till("garden", 0, 0)
    manager.plant("garden", (0, 0), "fire_berry")
    manager.water("garden", (0, 0))
    clock.advance(GROW)
    assert manager.harvest("garden", (0, 0)) == ("fire_berry", 4)


def test_harvest_on_an_empty_tile(manager: FarmingManager) -> None:
    manager.till("garden", 0, 0)
    assert manager.harvest("garden", (0, 0)) is None
    assert not manager.can_harvest("garden", (0, 0))


def test_untill_removes_the_tile(manager: FarmingManager) -> None:
    manager.till("garden", 0, 0)
    assert manager.untill("garden", 0, 0)
    assert not manager.untill("garden", 0, 0)
    assert not manager.is_tilled("garden", (0, 0))


# -- rendering -------------------------------------------------------------


def test_render_entries_show_soil_and_the_current_stage(
    manager: FarmingManager, clock: Clock
) -> None:
    manager.till("garden", 0, 0)
    manager.plant("garden", (0, 0), "fire_berry")

    entries = manager.render_entries("garden")
    assert entries == [
        (CONFIG.tilled_sprite, (0, 0), 1),
        ("a.png", (0, 0), 2),
    ]

    clock.advance(GROW)
    assert manager.render_entries("garden")[1][0] == "d.png"


def test_render_entries_show_wet_soil(
    manager: FarmingManager, clock: Clock
) -> None:
    manager.till("garden", 0, 0)
    manager.water("garden", (0, 0))
    assert manager.render_entries("garden")[0][0] == CONFIG.tilled_wet_sprite

    clock.advance(WET_DURATION + 1)
    assert manager.render_entries("garden")[0][0] == CONFIG.tilled_sprite


def test_render_entries_for_an_unknown_map(manager: FarmingManager) -> None:
    assert manager.render_entries("nowhere") == []


# -- persistence -----------------------------------------------------------


def test_state_round_trip(manager: FarmingManager, clock: Clock) -> None:
    manager.till("garden", 4, 5, 2, 1)
    manager.water("garden", (4, 5))
    clock.advance(30)
    manager.plant("garden", (4, 5), "fire_berry")
    planted_at = clock()

    state = manager.get_state()

    restored = FarmingManager(clock=clock, config=CONFIG)
    restored.set_state(state)

    assert restored.is_tilled("garden", (4, 5))
    assert restored.is_tilled("garden", (5, 5))
    tile = restored.get_tile("garden", (4, 5))
    assert tile is not None
    assert tile.plant is not None
    assert tile.plant.fruit == "fire_berry"
    assert tile.plant.planted_at == planted_at
    assert tile.plant.stage_seconds == STAGES
    assert tile.waterings == [planted_at - 30]


def test_state_is_json_encodable(manager: FarmingManager) -> None:
    """Tile keys must be strings, since saves go through JSON."""
    import json

    manager.till("garden", 4, 5)
    manager.water("garden", (4, 5))
    manager.plant("garden", (4, 5), "fire_berry")

    encoded = json.dumps(manager.get_state())
    restored = FarmingManager(clock=manager.clock, config=CONFIG)
    restored.set_state(json.loads(encoded))
    tile = restored.get_tile("garden", (4, 5))
    assert tile is not None and tile.plant is not None


def test_growth_continues_across_a_reload(
    manager: FarmingManager, clock: Clock
) -> None:
    """The game being shut is just time passing, as far as a plant knows."""
    manager.till("garden", 0, 0)
    manager.plant("garden", (0, 0), "fire_berry")
    manager.water("garden", (0, 0))
    state = manager.get_state()

    clock.advance(GROW)  # the player was away
    restored = FarmingManager(clock=clock, config=CONFIG)
    restored.set_state(state)

    assert restored.can_harvest("garden", (0, 0))
    assert restored.harvest("garden", (0, 0)) == ("fire_berry", 4)


def test_set_state_replaces_what_was_there(manager: FarmingManager) -> None:
    manager.till("garden", 0, 0)
    manager.set_state({})
    assert not manager.is_tilled("garden", (0, 0))


def test_set_state_of_none(manager: FarmingManager) -> None:
    manager.till("garden", 0, 0)
    manager.set_state(None)
    assert manager.plots == {}


def test_set_state_drops_unreadable_tiles(manager: FarmingManager) -> None:
    manager.set_state(
        {
            "garden": {
                "not-a-key": {"waterings": []},
                "1,2": {"waterings": [], "plant": {"fruit": "fire_berry"}},
                "3,4": {"waterings": [T0]},
            }
        }
    )
    assert sorted(manager.plots["garden"]) == [(3, 4)]


def test_empty_plots_are_not_saved(manager: FarmingManager) -> None:
    manager.till("garden", 0, 0)
    manager.untill("garden", 0, 0)
    assert manager.get_state() == {}


# -- config ----------------------------------------------------------------


def test_shipped_config_is_valid() -> None:
    """mods/planting.yaml must parse and validate as shipped."""
    from tuxemon.constants import paths
    from tuxemon.farming.config import CONFIG_FILENAME

    config = load_planting_config(paths.mods_folder / CONFIG_FILENAME)
    assert config.fruits, "no plantable items are declared"
    for fruit in config.fruits.values():
        assert len(fruit.stages) == len(fruit.stage_seconds) + 1


def test_config_inherits_defaults(tmp_path) -> None:
    path = tmp_path / "planting.yaml"
    path.write_text(
        "defaults:\n"
        "  stage_seconds: [1, 2]\n"
        "  stages: [a.png, b.png, c.png]\n"
        "fruits:\n"
        "  fire_berry: {}\n"
        "  water_berry:\n"
        "    stage_seconds: [9]\n"
        "    stages: [x.png, y.png]\n",
        encoding="utf-8",
    )
    config = load_planting_config(path)
    assert config.get("fire_berry").stage_seconds == [1.0, 2.0]
    assert config.get("water_berry").stages == ["x.png", "y.png"]
    assert config.is_plantable("fire_berry")
    assert not config.is_plantable("potion")


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        pytest.param(
            "  bad:\n    stage_seconds: []\n    stages: [a.png]\n",
            "stage_seconds",
            id="no-durations",
        ),
        pytest.param(
            "  bad:\n    stage_seconds: [1, 2]\n    stages: [a.png, b.png]\n",
            "one more sprite",
            id="sprite-count-mismatch",
        ),
        pytest.param(
            "  bad:\n    stage_seconds: [0]\n    stages: [a.png, b.png]\n",
            "non-positive",
            id="zero-duration",
        ),
    ],
)
def test_config_rejects_bad_entries(
    tmp_path, entry: str, message: str
) -> None:
    path = tmp_path / "planting.yaml"
    path.write_text(f"fruits:\n{entry}", encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_planting_config(path)


# -- the glue the player actually touches ----------------------------------
#
# The event action, the event condition and the two item effects all go
# through the same "tile in front of you" lookup, so they are exercised here
# against a stubbed session. The end-to-end run lives in
# scripts/farming_demo.py.


@pytest.fixture
def session(manager: FarmingManager):
    """A session stub with just enough client for the farming glue."""
    from unittest.mock import MagicMock

    from tuxemon.db import Direction

    player = MagicMock()
    player.tile_pos = (5, 10)
    player.facing = Direction.UP
    player.bag.find_item.return_value = None

    client = MagicMock()
    client.farming_manager = manager
    client.map_manager.map_slug = "garden"
    client.get_npc.side_effect = lambda slug: (
        player if slug == "player" else None
    )
    client.input_cache.was_button_pressed.return_value = True

    stub = MagicMock()
    stub.client = client
    stub.player = player
    return stub


FACED = (5, 9)


class StubItem:
    """The two fields the item effects read off an Item."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        self.name = slug


def test_faced_tile(session) -> None:
    from tuxemon.farming.targeting import faced_tile

    assert faced_tile(session) == ("garden", FACED)
    assert faced_tile(session, "npc_nobody") is None


def test_set_tilled_action(session, manager: FarmingManager) -> None:
    from tuxemon.event.actions.set_tilled import SetTilledAction

    SetTilledAction(x=2, y=3, width=2, height=2).start(session)
    assert sorted(manager.plots["garden"]) == [(2, 3), (2, 4), (3, 3), (3, 4)]


def test_set_tilled_action_rejects_an_empty_rectangle(session) -> None:
    from tuxemon.event.actions.set_tilled import SetTilledAction

    with pytest.raises(ValueError, match="positive size"):
        SetTilledAction(x=0, y=0, width=0, height=1).start(session)


def test_plant_effect(session, manager: FarmingManager, monkeypatch) -> None:
    from tuxemon.core.effects import plant as plant_module

    monkeypatch.setattr(plant_module, "open_dialog", lambda *a, **k: None)
    effect = plant_module.PlantEffect()
    item = StubItem("fire_berry")

    # untilled ground
    assert not effect.apply_item(session, item).success

    manager.till("garden", *FACED)
    assert effect.apply_item(session, item).success
    tile = manager.get_tile("garden", FACED)
    assert tile is not None and tile.plant is not None

    # a second planting into the same tile
    assert not effect.apply_item(session, item).success


def test_plant_effect_rejects_an_unplantable_item(
    session, manager: FarmingManager, monkeypatch
) -> None:
    from tuxemon.core.effects import plant as plant_module

    monkeypatch.setattr(plant_module, "open_dialog", lambda *a, **k: None)
    manager.till("garden", *FACED)
    result = plant_module.PlantEffect().apply_item(session, StubItem("potion"))
    assert not result.success
    tile = manager.get_tile("garden", FACED)
    assert tile is not None and tile.is_empty


def test_water_effect(
    session, manager: FarmingManager, clock: Clock, monkeypatch
) -> None:
    from tuxemon.core.effects import water_tile as water_module

    monkeypatch.setattr(water_module, "open_dialog", lambda *a, **k: None)
    effect = water_module.WaterTileEffect()
    item = StubItem("watering_can")

    assert not effect.apply_item(session, item).success

    manager.till("garden", *FACED)
    assert effect.apply_item(session, item).success
    tile = manager.get_tile("garden", FACED)
    assert tile is not None
    assert tile.waterings == [clock()]


def test_to_use_plant_condition(
    session, manager: FarmingManager, clock
) -> None:
    from tuxemon.event.conditions.to_use_plant import ToUsePlantCondition

    any_plant = ToUsePlantCondition("player")
    ripe_only = ToUsePlantCondition("player", "ripe")

    manager.till("garden", *FACED)
    assert not any_plant.test(session), "no plant yet"

    manager.plant("garden", FACED, "fire_berry")
    assert any_plant.test(session)
    assert not ripe_only.test(session), "not ripe yet"

    clock.advance(GROW)
    assert ripe_only.test(session)


def test_to_use_plant_needs_the_button(
    session, manager: FarmingManager
) -> None:
    from tuxemon.event.conditions.to_use_plant import ToUsePlantCondition

    manager.till("garden", *FACED)
    manager.plant("garden", FACED, "fire_berry")
    session.client.input_cache.was_button_pressed.return_value = False
    assert not ToUsePlantCondition("player").test(session)


def test_harvest_action(
    session, manager: FarmingManager, clock: Clock, monkeypatch
) -> None:
    from tuxemon.event.actions import harvest_plant as harvest_module

    monkeypatch.setattr(harvest_module, "open_dialog", lambda *a, **k: None)
    monkeypatch.setattr(
        harvest_module.Item, "create", staticmethod(lambda slug: slug)
    )
    action = harvest_module.HarvestPlantAction()

    manager.till("garden", *FACED)
    manager.plant("garden", FACED, "fire_berry")

    action.start(session)
    session.player.bag.add_item.assert_not_called()
    tile = manager.get_tile("garden", FACED)
    assert tile is not None and tile.plant is not None, "left alone unripe"

    clock.advance(GROW)
    action.start(session)
    session.player.bag.add_item.assert_called_once_with("fire_berry", 2)
    tile = manager.get_tile("garden", FACED)
    assert tile is not None and tile.is_empty


def test_harvest_action_tops_up_an_existing_stack(
    session, manager: FarmingManager, clock: Clock, monkeypatch
) -> None:
    from unittest.mock import MagicMock

    from tuxemon.event.actions import harvest_plant as harvest_module

    monkeypatch.setattr(harvest_module, "open_dialog", lambda *a, **k: None)
    existing = MagicMock()
    session.player.bag.find_item.return_value = existing

    manager.till("garden", *FACED)
    manager.plant("garden", FACED, "fire_berry")
    manager.water("garden", FACED)
    clock.advance(GROW)
    harvest_module.HarvestPlantAction().start(session)

    existing.increase_quantity.assert_called_once_with(4)
    session.player.bag.add_item.assert_not_called()
