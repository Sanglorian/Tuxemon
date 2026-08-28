# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml
from pygame.rect import Rect
from pygame.surface import Surface

from tuxemon.core.effects.farm_harvest import FarmHarvestEffect
from tuxemon.core.effects.farm_plant import FarmPlantEffect
from tuxemon.core.effects.farm_till import FarmTillEffect
from tuxemon.core.effects.farm_water import FarmWaterEffect
from tuxemon.db import Direction
from tuxemon.event.actions.farm_sleep import FarmSleepAction
from tuxemon.farm.calendar import DEFAULT_SEASON_LENGTH, FarmCalendar
from tuxemon.farm.crop import CropModel, PlantedCrop, load_crops
from tuxemon.farm.grid import FarmGrid, FarmTile
from tuxemon.farm.manager import FarmManager
from tuxemon.farm.renderer import (
    CROP_LAYER_OFFSET,
    SOIL_DRY,
    SOIL_LAYER_OFFSET,
    SOIL_WET,
    CropLayer,
    CropSpriteCache,
)
from tuxemon.farm.targeting import is_tillable, resolve_target

MAP = "farm_test"


def make_model(**overrides: object) -> CropModel:
    """A three-stage crop that matures after four watered days."""
    defaults: dict[str, object] = {
        "slug": "testnip",
        "seed_item": "testnip_seed",
        "produce_item": "testnip",
        "sprite": "sprites/crops/testnip.png",
        "stage_days": (1, 1, 2),
        "seasons": ("spring",),
        "water_tolerance": 2,
        "harvest_yield": 1,
    }
    defaults.update(overrides)
    return CropModel(**defaults)  # type: ignore[arg-type]


def plant(model: CropModel, **overrides: object) -> PlantedCrop:
    """A crop already bound to its model, so no config file is consulted."""
    crop = PlantedCrop(slug=model.slug, planted_day=1, _model=model)
    for key, value in overrides.items():
        setattr(crop, key, value)
    return crop


# ---------------------------------------------------------------------------
# FarmCalendar
# ---------------------------------------------------------------------------


def test_calendar_starts_on_the_first_day_of_spring():
    calendar = FarmCalendar()
    assert calendar.day == 1
    assert calendar.day_of_season == 1
    assert calendar.season == "spring"
    assert calendar.year == 1


def test_calendar_rolls_into_the_next_season():
    calendar = FarmCalendar(season_length=4)
    calendar.advance_day(4)
    assert calendar.day == 5
    assert calendar.season == "summer"
    assert calendar.day_of_season == 1


def test_calendar_rolls_into_the_next_year():
    calendar = FarmCalendar(season_length=2)
    calendar.advance_day(8)
    assert calendar.season == "spring"
    assert calendar.year == 2


def test_calendar_rejects_non_advancing_days():
    calendar = FarmCalendar()
    with pytest.raises(ValueError):
        calendar.advance_day(0)
    with pytest.raises(ValueError):
        calendar.advance_day(-3)


def test_calendar_rejects_an_empty_season():
    with pytest.raises(ValueError):
        FarmCalendar(season_length=0)


def test_calendar_survives_a_save_round_trip():
    calendar = FarmCalendar(season_length=5)
    calendar.advance_day(12)

    restored = FarmCalendar()
    restored.set_state(calendar.get_state())

    assert restored.day == calendar.day
    assert restored.season_length == 5
    assert restored.season == calendar.season


def test_calendar_repairs_a_corrupt_season_length():
    calendar = FarmCalendar()
    calendar.set_state({"day": 3, "season_length": 0})
    assert calendar.season_length == DEFAULT_SEASON_LENGTH
    assert calendar.day == 3


def test_calendar_does_not_read_the_real_clock():
    """
    The farm day must move only when the game says so. If this ever starts
    tracking the system date, sleeping stops being what advances a day.
    """
    calendar = FarmCalendar()
    before = calendar.day
    assert calendar.day == before
    assert calendar.days_since(before) == 0


# ---------------------------------------------------------------------------
# Crop growth
# ---------------------------------------------------------------------------


def test_crop_grows_only_on_watered_days():
    model = make_model()
    crop = plant(model)

    crop.advance_day(model, watered=True)
    crop.advance_day(model, watered=False)
    crop.advance_day(model, watered=True)

    assert crop.growth == 2
    assert not crop.withered


def test_crop_matures_after_enough_watered_days():
    model = make_model()
    crop = plant(model)

    for _ in range(model.days_to_mature):
        crop.advance_day(model, watered=True)

    assert crop.is_mature(model)
    assert crop.get_stage(model).mature


def test_crop_withers_past_its_water_tolerance():
    model = make_model(water_tolerance=2)
    crop = plant(model)

    crop.advance_day(model, watered=False)
    crop.advance_day(model, watered=False)
    assert not crop.withered

    crop.advance_day(model, watered=False)
    assert crop.withered
    assert crop.get_stage(model).withered


def test_watering_resets_the_drought_counter():
    model = make_model(water_tolerance=2)
    crop = plant(model)

    crop.advance_day(model, watered=False)
    crop.advance_day(model, watered=False)
    crop.advance_day(model, watered=True)
    crop.advance_day(model, watered=False)
    crop.advance_day(model, watered=False)

    assert not crop.withered


def test_withered_crop_stops_growing():
    model = make_model()
    crop = plant(model, withered=True, growth=1)

    crop.advance_day(model, watered=True)

    assert crop.growth == 1


def test_stage_advances_through_every_frame():
    model = make_model(stage_days=(1, 1, 2))
    crop = plant(model)

    seen = [crop.get_stage(model).index]
    for _ in range(model.days_to_mature):
        crop.advance_day(model, watered=True)
        seen.append(crop.get_stage(model).index)

    assert seen == [0, 1, 2, 2, 3]
    assert max(seen) == model.growth_stage_count - 1


def test_harvest_returns_nothing_before_maturity():
    model = make_model()
    crop = plant(model)
    assert crop.harvest(model) == 0


def test_harvest_yields_produce_and_spends_a_one_off_crop():
    model = make_model(harvest_yield=3)
    crop = plant(model, growth=model.days_to_mature)

    assert crop.harvest(model) == 3
    assert crop.is_spent(model)


def test_regrowing_crop_stays_and_needs_regrow_days_again():
    model = make_model(regrow_days=2)
    crop = plant(model, growth=model.days_to_mature)

    assert crop.harvest(model) == 1
    assert not crop.is_spent(model)
    assert not crop.is_mature(model)

    crop.advance_day(model, watered=True)
    assert not crop.is_mature(model)
    crop.advance_day(model, watered=True)
    assert crop.is_mature(model)


def test_regrow_days_longer_than_maturity_does_not_go_negative():
    model = make_model(regrow_days=99)
    crop = plant(model, growth=model.days_to_mature)

    crop.harvest(model)

    assert crop.growth == 0


def test_crop_survives_a_save_round_trip():
    model = make_model()
    crop = plant(model, growth=2, dry_days=1, harvests=1)

    restored = PlantedCrop.from_state(crop.get_state())

    assert restored.slug == crop.slug
    assert restored.growth == 2
    assert restored.dry_days == 1
    assert restored.harvests == 1


def test_seasons_gate_planting():
    model = make_model(seasons=("summer",))
    assert model.grows_in("summer")
    assert not model.grows_in("winter")


def test_a_crop_with_no_seasons_grows_year_round():
    model = make_model(seasons=())
    assert model.grows_in("winter")


# ---------------------------------------------------------------------------
# FarmGrid
# ---------------------------------------------------------------------------


def test_untouched_tiles_are_not_remembered():
    grid = FarmGrid()
    assert grid.get_tile(MAP, (1, 1)) is None
    assert grid.tile_count() == 0


def test_tilling_remembers_the_tile():
    grid = FarmGrid()
    assert grid.till(MAP, (2, 3))

    tile = grid.get_tile(MAP, (2, 3))
    assert tile is not None
    assert tile.tilled


def test_tilling_twice_fails():
    grid = FarmGrid()
    grid.till(MAP, (2, 3))
    assert not grid.till(MAP, (2, 3))


def test_watering_requires_tilled_soil():
    grid = FarmGrid()
    assert not grid.water(MAP, (0, 0))

    grid.till(MAP, (0, 0))
    assert grid.water(MAP, (0, 0))
    assert not grid.water(MAP, (0, 0))


def test_planting_requires_tilled_soil():
    grid = FarmGrid()
    assert not grid.plant(MAP, (1, 1), "turnip", day=1)

    grid.till(MAP, (1, 1))
    assert grid.plant(MAP, (1, 1), "turnip", day=1)


def test_planting_an_unknown_crop_fails():
    grid = FarmGrid()
    grid.till(MAP, (1, 1))
    assert not grid.plant(MAP, (1, 1), "not_a_crop", day=1)


def test_planting_on_an_occupied_tile_fails():
    grid = FarmGrid()
    grid.till(MAP, (1, 1))
    grid.plant(MAP, (1, 1), "turnip", day=1)
    assert not grid.plant(MAP, (1, 1), "potato", day=1)


def test_advance_day_grows_watered_crops_and_dries_the_soil():
    grid = FarmGrid()
    grid.till(MAP, (1, 1))
    grid.plant(MAP, (1, 1), "turnip", day=1)
    grid.water(MAP, (1, 1))

    grid.advance_day()

    tile = grid.get_tile(MAP, (1, 1))
    assert tile is not None and tile.crop is not None
    assert tile.crop.growth == 1
    assert not tile.watered


def test_advance_day_grows_crops_on_every_map():
    grid = FarmGrid()
    for map_slug in ("farm_a", "farm_b"):
        grid.till(map_slug, (0, 0))
        grid.plant(map_slug, (0, 0), "turnip", day=1)
        grid.water(map_slug, (0, 0))

    grid.advance_day()

    for map_slug in ("farm_a", "farm_b"):
        tile = grid.get_tile(map_slug, (0, 0))
        assert tile is not None and tile.crop is not None
        assert tile.crop.growth == 1


def test_harvesting_a_mature_crop_clears_the_tile_but_keeps_the_soil():
    grid = FarmGrid()
    grid.till(MAP, (1, 1))
    grid.plant(MAP, (1, 1), "turnip", day=1)

    turnip = load_crops()["turnip"]
    for _ in range(turnip.days_to_mature):
        grid.water(MAP, (1, 1))
        grid.advance_day()

    assert grid.harvest(MAP, (1, 1)) == (turnip.produce_item, 1)

    tile = grid.get_tile(MAP, (1, 1))
    assert tile is not None
    assert tile.crop is None
    assert tile.tilled


def test_harvesting_an_immature_crop_returns_nothing():
    grid = FarmGrid()
    grid.till(MAP, (1, 1))
    grid.plant(MAP, (1, 1), "turnip", day=1)
    assert grid.harvest(MAP, (1, 1)) is None


def test_clearing_forgets_the_tile():
    grid = FarmGrid()
    grid.till(MAP, (1, 1))
    assert grid.clear(MAP, (1, 1))
    assert grid.get_tile(MAP, (1, 1)) is None
    assert grid.map_slugs() == []


def test_advance_day_prunes_tiles_with_nothing_left_to_remember():
    grid = FarmGrid()
    grid._maps[MAP] = {(4, 4): FarmTile(tilled=False, watered=False)}

    grid.advance_day()

    assert grid.tile_count() == 0


def test_grid_survives_a_save_round_trip():
    grid = FarmGrid()
    grid.till(MAP, (2, 3))
    grid.plant(MAP, (2, 3), "turnip", day=1)
    grid.water(MAP, (2, 3))
    grid.till("other_map", (9, 9))

    restored = FarmGrid()
    restored.set_state(grid.get_state())

    tile = restored.get_tile(MAP, (2, 3))
    assert tile is not None
    assert tile.tilled and tile.watered
    assert tile.crop is not None and tile.crop.slug == "turnip"
    assert restored.get_tile("other_map", (9, 9)) is not None


def test_grid_discards_tiles_with_unreadable_coordinates():
    restored = FarmGrid()
    restored.set_state({MAP: {"nonsense": {"tilled": True}}})
    assert restored.tile_count() == 0


# ---------------------------------------------------------------------------
# FarmManager
# ---------------------------------------------------------------------------


def test_manager_refuses_a_crop_that_is_out_of_season():
    manager = FarmManager()
    manager.till(MAP, (1, 1))

    # tomato is summer-only, and a new farm starts in spring
    assert manager.calendar.season == "spring"
    assert not manager.plant(MAP, (1, 1), "tomato")
    assert manager.plant(MAP, (1, 1), "turnip")


def test_manager_advance_day_moves_the_calendar_and_the_crops():
    manager = FarmManager()
    manager.till(MAP, (1, 1))
    manager.plant(MAP, (1, 1), "turnip")
    manager.water(MAP, (1, 1))

    assert manager.advance_day() == 2

    tile = manager.get_tile(MAP, (1, 1))
    assert tile is not None and tile.crop is not None
    assert tile.crop.growth == 1


def test_manager_advances_several_days_at_once():
    manager = FarmManager()
    manager.till(MAP, (1, 1))
    manager.plant(MAP, (1, 1), "turnip")
    manager.water(MAP, (1, 1))

    manager.advance_day(3)

    assert manager.calendar.day == 4
    tile = manager.get_tile(MAP, (1, 1))
    assert tile is not None and tile.crop is not None
    # only the first day was watered, so the crop grew once then dried out
    assert tile.crop.growth == 1


def test_manager_survives_a_save_round_trip():
    manager = FarmManager()
    manager.till(MAP, (5, 5))
    manager.plant(MAP, (5, 5), "turnip")
    manager.advance_day(2)

    restored = FarmManager()
    restored.set_state(manager.get_state())

    assert restored.calendar.day == manager.calendar.day
    assert restored.get_tile(MAP, (5, 5)) is not None


def test_manager_tolerates_an_absent_farm_in_an_older_save():
    manager = FarmManager()
    manager.set_state({})
    assert manager.calendar.day == 1
    assert manager.grid.tile_count() == 0


# ---------------------------------------------------------------------------
# Crop config
# ---------------------------------------------------------------------------


def test_shipped_crops_have_sprite_sheets_with_enough_frames():
    """
    Every crop needs one frame per growth stage plus the mature plant, and a
    withered frame when it claims one. A short sheet means a crop that draws
    the wrong thing on its last day.
    """
    from tuxemon.graphics import load_image

    for slug, model in load_crops().items():
        sheet = load_image(model.sprite)
        frame_width = model.frame_width or 16
        expected = model.growth_stage_count + (
            1 if model.has_withered_frame else 0
        )
        actual = sheet.get_width() // frame_width

        assert actual == expected, (
            f"{slug}: sheet has {actual} frames, expected {expected}"
        )
        assert sheet.get_height() == (model.frame_height or 16)


# ---------------------------------------------------------------------------
# CropLayer
# ---------------------------------------------------------------------------


@dataclass
class FakeRenderer:
    offset: tuple[int, int] = (0, 0)

    def get_center_offset(self) -> tuple[int, int]:
        return self.offset


@dataclass
class FakeMap:
    sprite_layer: int = 2
    renderer: FakeRenderer = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.renderer is None:
            self.renderer = FakeRenderer()


@dataclass
class FakeMapManager:
    map_slug: str = MAP


@dataclass
class FakeContext:
    tile_size: tuple[int, int] = (16, 16)
    scale: int = 1
    rect: Rect = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.rect is None:
            self.rect = Rect(0, 0, 320, 240)


def make_layer(
    manager: FarmManager,
    crop_frames: int = 5,
    crop_height: int = 16,
    context: FakeContext | None = None,
) -> CropLayer:
    """A layer with frames injected, so no art needs to be on disk."""
    sprites = CropSpriteCache()
    sprites.set_frames("soil", [Surface((16, 16)), Surface((16, 16))])
    sprites.set_frames(
        "testnip", [Surface((16, crop_height)) for _ in range(crop_frames)]
    )
    return CropLayer(
        manager,
        FakeMapManager(),  # type: ignore[arg-type]
        context or FakeContext(),  # type: ignore[arg-type]
        sprites,
    )


def test_layer_draws_nothing_on_an_untouched_map():
    layer = make_layer(FarmManager())
    assert layer.get_rendered_tiles(FakeMap()) == []  # type: ignore[arg-type]


def test_layer_draws_soil_for_a_tilled_tile():
    manager = FarmManager()
    manager.till(MAP, (1, 1))

    rendered = layer_tiles(make_layer(manager))

    assert len(rendered) == 1
    _, _, layer_index = rendered[0]
    assert layer_index == 2 - SOIL_LAYER_OFFSET


def test_layer_draws_soil_and_crop_below_the_character_layer():
    manager = FarmManager()
    manager.till(MAP, (1, 1))
    tile = manager.get_tile(MAP, (1, 1))
    assert tile is not None
    tile.crop = plant(make_model())

    rendered = layer_tiles(make_layer(manager))

    layers = [layer_index for _, _, layer_index in rendered]
    assert layers == [2 - SOIL_LAYER_OFFSET, 2 - CROP_LAYER_OFFSET]
    assert all(index < 2 for index in layers)


def test_layer_picks_the_wet_soil_frame_once_watered():
    manager = FarmManager()
    manager.till(MAP, (1, 1))
    layer = make_layer(manager)
    dry_frame = layer.sprites.get_soil_frames(1)[SOIL_DRY]
    wet_frame = layer.sprites.get_soil_frames(1)[SOIL_WET]

    assert layer_tiles(layer)[0][0] is dry_frame

    manager.water(MAP, (1, 1))
    assert layer_tiles(layer)[0][0] is wet_frame


def test_layer_picks_the_frame_matching_the_growth_stage():
    manager = FarmManager()
    manager.till(MAP, (1, 1))
    tile = manager.get_tile(MAP, (1, 1))
    assert tile is not None

    model = make_model()
    crop = plant(model)
    tile.crop = crop
    layer = make_layer(manager)
    frames = layer.sprites.get_crop_frames(model, 1)

    for expected in (0, 1, 2, 2, 3):
        assert layer_tiles(layer)[1][0] is frames[expected]
        crop.advance_day(model, watered=True)


def test_layer_picks_the_withered_frame():
    manager = FarmManager()
    manager.till(MAP, (1, 1))
    tile = manager.get_tile(MAP, (1, 1))
    assert tile is not None

    model = make_model()
    tile.crop = plant(model, withered=True)
    layer = make_layer(manager)

    frames = layer.sprites.get_crop_frames(model, 1)
    assert layer_tiles(layer)[1][0] is frames[-1]


def test_layer_clamps_when_the_sheet_is_missing_frames():
    manager = FarmManager()
    manager.till(MAP, (1, 1))
    tile = manager.get_tile(MAP, (1, 1))
    assert tile is not None

    model = make_model()
    tile.crop = plant(model, withered=True)
    layer = make_layer(manager, crop_frames=2)

    rendered = layer_tiles(layer)
    frames = layer.sprites.get_crop_frames(model, 1)
    assert rendered[1][0] is frames[-1]


def test_layer_bottom_anchors_a_tall_crop_over_its_tile():
    manager = FarmManager()
    manager.till(MAP, (2, 3))
    tile = manager.get_tile(MAP, (2, 3))
    assert tile is not None
    tile.crop = plant(make_model())

    rendered = layer_tiles(make_layer(manager, crop_height=32))
    soil_rect = rendered[0][1]
    crop_rect = rendered[1][1]

    # tile (2, 3) at 16px tiles with no camera offset
    assert soil_rect.topleft == (32, 48)
    # the tall crop shares the tile's bottom edge and centre line
    assert crop_rect.bottom == soil_rect.bottom
    assert crop_rect.centerx == soil_rect.centerx
    assert crop_rect.top == soil_rect.bottom - 32


def test_layer_skips_offscreen_tiles():
    manager = FarmManager()
    manager.till(MAP, (500, 500))

    assert layer_tiles(make_layer(manager)) == []


def test_layer_honours_the_camera_offset():
    manager = FarmManager()
    manager.till(MAP, (1, 1))
    layer = make_layer(manager)

    shifted = FakeMap(renderer=FakeRenderer(offset=(10, 20)))
    rect = layer.get_rendered_tiles(shifted)[0][1]  # type: ignore[arg-type]

    assert rect.topleft == (16 + 10, 16 + 20)


def test_layer_draws_nothing_before_the_map_renderer_is_ready():
    """
    Tile positions are resolved against the map renderer's centre offset,
    which is asserted on. A caller outside MapRenderer.draw must get an empty
    list rather than an AssertionError.
    """
    manager = FarmManager()
    manager.till(MAP, (1, 1))
    layer = make_layer(manager)

    unready = FakeMap(renderer=None)  # type: ignore[arg-type]
    unready.renderer = None  # type: ignore[assignment]

    assert layer.get_rendered_tiles(unready) == []  # type: ignore[arg-type]


def test_layer_draws_nothing_without_a_loaded_map():
    layer = make_layer(FarmManager())
    layer.map_manager = FakeMapManager(map_slug="")  # type: ignore[assignment]
    assert layer.get_rendered_tiles(FakeMap()) == []  # type: ignore[arg-type]


def test_layer_survives_art_that_failed_to_load():
    manager = FarmManager()
    manager.till(MAP, (1, 1))
    layer = make_layer(manager)
    layer.sprites.set_frames("soil", [])

    assert layer_tiles(layer) == []


def layer_tiles(layer: CropLayer) -> list[tuple[Surface, Rect, int]]:
    """Renders the fake map and returns the surfaces produced."""
    return layer.get_rendered_tiles(FakeMap())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tool targeting and the tillable-ground rule
# ---------------------------------------------------------------------------


@dataclass
class FakeGameVariables:
    values: dict = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.values is None:
            self.values = {}

    def set(self, key, value) -> None:
        self.values[key] = value

    def get(self, key, default=None):
        return self.values.get(key, default)


@dataclass
class FakeBag:
    removed: list = None  # type: ignore[assignment]
    added: list = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.removed = []
        self.added = []

    def remove_item(self, item, quantity: int = 1) -> bool:
        self.removed.append((item, quantity))
        return True

    def add_item(self, item, quantity: int = 1) -> bool:
        self.added.append((item, quantity))
        return True


class FakePlayer:
    def __init__(self, tile_pos=(3, 3), facing=Direction.UP) -> None:
        self.tile_pos = tile_pos
        self.facing = facing
        self.game_variables = FakeGameVariables()
        self.bag = FakeBag()


class FakeCollisionManager:
    def __init__(self, occupied=()) -> None:
        self.occupied = set(occupied)

    def is_tile_occupied(self, coords) -> bool:
        return coords in self.occupied


class FakeFarmMapManager:
    def __init__(self, blocked=(), size=(20, 20)) -> None:
        self.map_slug = MAP
        self.collision_map = {pos: None for pos in blocked}
        self.map_size = size


class FakeClient:
    def __init__(self, farm, player, blocked=(), occupied=()) -> None:
        self.farm_manager = farm
        self._player = player
        self.map_manager = FakeFarmMapManager(blocked)
        self.collision_manager = FakeCollisionManager(occupied)

    def get_npc(self, slug):
        return self._player if slug == "player" else None


class FakeFarmSession:
    def __init__(
        self, farm=None, blocked=(), occupied=(), facing=Direction.UP
    ):
        self.player = FakePlayer(facing=facing)
        self.farm = farm if farm is not None else FarmManager()
        self.client = FakeClient(self.farm, self.player, blocked, occupied)


def test_resolve_target_returns_the_tile_in_front():
    session = FakeFarmSession(facing=Direction.UP)
    target = resolve_target(session, "player")  # type: ignore[arg-type]
    assert target is not None
    assert target.map_slug == MAP
    assert target.pos == (3, 2)


def test_resolve_target_gives_up_on_an_unknown_character():
    session = FakeFarmSession()
    assert resolve_target(session, "npc_nobody") is None  # type: ignore[arg-type]


def test_open_ground_is_tillable():
    session = FakeFarmSession()
    assert is_tillable(session, (3, 2))  # type: ignore[arg-type]


def test_a_wall_is_not_tillable():
    session = FakeFarmSession(blocked=[(3, 2)])
    assert not is_tillable(session, (3, 2))  # type: ignore[arg-type]


def test_a_tile_someone_is_standing_on_is_not_tillable():
    session = FakeFarmSession(occupied=[(3, 2)])
    assert not is_tillable(session, (3, 2))  # type: ignore[arg-type]


def test_ground_off_the_edge_of_the_map_is_not_tillable():
    session = FakeFarmSession()
    assert not is_tillable(session, (-1, 4))  # type: ignore[arg-type]
    assert not is_tillable(session, (99, 4))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tool item effects
# ---------------------------------------------------------------------------


@dataclass
class FakeItem:
    name: str = "Hoe"
    slug: str = "hoe"


def test_hoe_effect_tills_the_facing_tile():
    session = FakeFarmSession()
    result = FarmTillEffect().apply_item(session, FakeItem())  # type: ignore[arg-type]

    assert result.success
    assert session.farm.get_tile(MAP, (3, 2)) is not None


def test_hoe_effect_refuses_a_wall():
    session = FakeFarmSession(blocked=[(3, 2)])
    result = FarmTillEffect().apply_item(session, FakeItem())  # type: ignore[arg-type]

    assert not result.success
    assert session.farm.get_tile(MAP, (3, 2)) is None


def test_watering_can_effect_needs_tilled_soil():
    session = FakeFarmSession()
    assert not FarmWaterEffect().apply_item(session, FakeItem()).success  # type: ignore[arg-type]

    session.farm.till(MAP, (3, 2))
    assert FarmWaterEffect().apply_item(session, FakeItem()).success  # type: ignore[arg-type]


def test_seed_effect_plants_and_spends_one_seed():
    session = FakeFarmSession()
    session.farm.till(MAP, (3, 2))
    item = FakeItem(name="Turnip Seeds", slug="turnip_seed")

    result = FarmPlantEffect("turnip").apply_item(session, item)  # type: ignore[arg-type]

    assert result.success
    assert session.farm.get_tile(MAP, (3, 2)).crop.slug == "turnip"
    assert session.player.bag.removed == [(item, 1)]


def test_seed_effect_keeps_the_seed_when_planting_fails():
    """
    The item pipeline consumes a failed item by default. Seeds opt out of that
    and spend themselves on success, so a mistimed swing costs nothing.
    """
    session = FakeFarmSession()
    item = FakeItem(name="Turnip Seeds", slug="turnip_seed")

    result = FarmPlantEffect("turnip").apply_item(session, item)  # type: ignore[arg-type]

    assert not result.success
    assert session.player.bag.removed == []


def test_seed_effect_refuses_a_crop_out_of_season():
    session = FakeFarmSession()
    session.farm.till(MAP, (3, 2))
    item = FakeItem(name="Tomato Seeds", slug="tomato_seed")

    # tomato is summer-only and a new farm starts in spring
    result = FarmPlantEffect("tomato").apply_item(session, item)  # type: ignore[arg-type]

    assert not result.success
    assert session.player.bag.removed == []


def test_sickle_effect_returns_nothing_from_bare_ground():
    session = FakeFarmSession()
    assert not FarmHarvestEffect().apply_item(session, FakeItem()).success  # type: ignore[arg-type]


def test_sickle_effect_banks_the_produce(monkeypatch):
    session = FakeFarmSession()
    session.farm.till(MAP, (3, 2))
    session.farm.plant(MAP, (3, 2), "turnip")
    crop = session.farm.get_tile(MAP, (3, 2)).crop
    crop.growth = crop.model.days_to_mature

    monkeypatch.setattr(
        "tuxemon.core.effects.farm_harvest.Item.create", lambda slug: slug
    )
    result = FarmHarvestEffect().apply_item(session, FakeItem())  # type: ignore[arg-type]

    assert result.success
    assert session.player.bag.added == [("turnip", 1)]
    assert session.player.game_variables.get("farm_harvest_item") == "turnip"


# ---------------------------------------------------------------------------
# Farm items and crop config agree with each other
# ---------------------------------------------------------------------------


FARM_ITEMS = [
    "hoe",
    "watering_can",
    "sickle",
    "turnip_seed",
    "potato_seed",
    "tomato_seed",
    "corn_seed",
    "turnip",
    "potato",
    "tomato",
    "corn",
]


def load_item_yaml(slug: str) -> dict:
    path = Path("mods/tuxemon/db/item") / f"{slug}.yaml"
    assert path.is_file(), f"missing item definition: {path}"
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_every_farm_item_has_its_icon():
    for slug in FARM_ITEMS:
        data = load_item_yaml(slug)
        sprite = Path("mods/tuxemon") / data["sprite"]
        assert sprite.is_file(), f"{slug}: missing sprite {sprite}"


def test_every_crop_names_items_that_exist():
    """
    A typo between crops.yaml and the item database would only show up as a
    seed that plants nothing, or a harvest that banks a broken item.
    """
    for slug, model in load_crops().items():
        seed = load_item_yaml(model.seed_item)
        assert seed["slug"] == model.seed_item

        effect = seed["effects"][0]
        assert effect["type"] == "farm_plant"
        assert effect["parameters"] == [slug], (
            f"{model.seed_item} plants {effect['parameters']}, not {slug}"
        )

        produce = load_item_yaml(model.produce_item)
        assert produce["slug"] == model.produce_item


def test_seed_bags_are_not_consumed_by_the_item_pipeline():
    """
    Seeds spend themselves inside the effect. If they were also marked
    consumable, a failed planting would still cost a seed.
    """
    for slug, model in load_crops().items():
        seed = load_item_yaml(model.seed_item)
        assert seed["behaviors"]["consumable"] is False, model.seed_item


def test_tools_are_reusable_and_usable_in_the_world():
    for slug in ("hoe", "watering_can", "sickle"):
        data = load_item_yaml(slug)
        assert data["behaviors"]["consumable"] is False, slug
        assert data["behaviors"]["requires_monster_menu"] is False, slug
        assert data["usable_in"] == ["WorldState"], slug


# ---------------------------------------------------------------------------
# Sleeping
# ---------------------------------------------------------------------------


class FakeSleepClient(FakeClient):
    """A client with no world state, so the sleep action skips the fade."""

    active_state_names: list[str] = []


def test_sleeping_outside_the_world_still_passes_the_night():
    """
    The bed fades the screen while the day turns. With no world to fade the
    action must still end the day rather than hang waiting for a transition.
    """
    session = FakeFarmSession()
    session.client = FakeSleepClient(session.farm, session.player)
    session.farm.till(MAP, (1, 1))
    session.farm.plant(MAP, (1, 1), "turnip")
    session.farm.water(MAP, (1, 1))

    action = FarmSleepAction()
    action.days = 1
    action.trans_time = None
    action.rgb = None
    action.start(session)  # type: ignore[arg-type]

    assert session.farm.calendar.day == 2
    tile = session.farm.get_tile(MAP, (1, 1))
    assert tile is not None and tile.crop is not None
    assert tile.crop.growth == 1
    assert not tile.watered


def test_sleeping_records_the_new_date_for_map_scripts():
    session = FakeFarmSession()
    session.client = FakeSleepClient(session.farm, session.player)

    action = FarmSleepAction()
    action.days = 3
    action.trans_time = None
    action.rgb = None
    action.start(session)  # type: ignore[arg-type]

    variables = session.player.game_variables
    assert variables.get("farm_day") == "4"
    assert variables.get("farm_day_of_season") == "4"
    assert variables.get("farm_season") == "spring"
    assert variables.get("farm_year") == "1"


def test_sleeping_for_no_days_is_refused():
    session = FakeFarmSession()
    session.client = FakeSleepClient(session.farm, session.player)

    action = FarmSleepAction()
    action.days = 0
    action.trans_time = None
    action.rgb = None
    action.start(session)  # type: ignore[arg-type]

    assert session.farm.calendar.day == 1


# ---------------------------------------------------------------------------
# The farm shop economy
# ---------------------------------------------------------------------------

FARM_ECONOMY = "paper_scoop_farm"
STARTING_MONEY = 500  # mods/tuxemon/mod.yaml starting_money


def load_farm_economy() -> dict:
    path = Path("mods/tuxemon/db/economy") / f"{FARM_ECONOMY}.yaml"
    with path.open(encoding="utf-8") as handle:
        entries = yaml.safe_load(handle)
    economy = next(e for e in entries if e["slug"] == FARM_ECONOMY)
    return {item["slug"]: item for item in economy["items"]}


def test_the_farm_shop_stocks_every_crop_and_tool():
    stock = load_farm_economy()

    for slug in ("hoe", "watering_can", "sickle"):
        assert slug in stock, f"the farm shop does not sell a {slug}"

    for slug, model in load_crops().items():
        assert model.seed_item in stock, f"no seed for {slug} on sale"
        assert model.produce_item in stock, (
            f"{slug} produce has no price, so it cannot be sold"
        )


def test_a_first_toolkit_and_some_seed_fit_the_starting_purse():
    """
    Farming has to be reachable on day one. If the tools cost more than the
    player starts with, the whole loop is gated behind battling for money.
    """
    stock = load_farm_economy()
    toolkit = sum(
        stock[slug]["price"] for slug in ("hoe", "watering_can", "sickle")
    )
    cheapest_seed = min(
        stock[model.seed_item]["price"] for model in load_crops().values()
    )

    assert toolkit + cheapest_seed <= STARTING_MONEY, (
        f"toolkit {toolkit} plus seed {cheapest_seed} exceeds {STARTING_MONEY}"
    )


def test_every_crop_is_worth_growing():
    """
    The shop pays `cost` for produce and charges `price` for seed.

    A one-off crop has to clear its seed in a single harvest. A regrowing
    crop is allowed to cost more than one picking returns — that is the
    trade its higher seed price buys — but it must break even well inside a
    season, or planting one is a trap rather than a commitment.
    """
    stock = load_farm_economy()
    season_length = DEFAULT_SEASON_LENGTH

    for slug, model in load_crops().items():
        seed_price = stock[model.seed_item]["price"]
        per_harvest = stock[model.produce_item]["cost"] * model.harvest_yield

        if model.regrow_days is None:
            assert per_harvest > seed_price, (
                f"{slug}: seed costs {seed_price}, "
                f"its one harvest returns {per_harvest}"
            )
            continue

        harvests_needed = (
            -(-seed_price // per_harvest) + 1
        )  # clear it, not tie
        day = model.days_to_mature + model.regrow_days * (harvests_needed - 1)
        assert day <= season_length, (
            f"{slug}: needs {harvests_needed} harvests to profit, "
            f"reached on day {day} of a {season_length}-day season"
        )


def test_a_regrowing_crop_beats_a_staple_over_a_full_season():
    """
    The premium seeds should reward holding a plot for the season. If they
    did not, there would be no reason to ever plant anything but turnips.
    """
    stock = load_farm_economy()
    season_length = DEFAULT_SEASON_LENGTH

    def season_profit(model) -> float:
        seed = stock[model.seed_item]["price"]
        per_harvest = stock[model.produce_item]["cost"] * model.harvest_yield

        if model.regrow_days is None:
            cycles = season_length // model.days_to_mature
            return cycles * (per_harvest - seed)

        harvests = 1 + max(
            0,
            (season_length - model.days_to_mature) // model.regrow_days,
        )
        return harvests * per_harvest - seed

    crops = load_crops()
    staple = season_profit(crops["turnip"])
    for slug, model in crops.items():
        if model.regrow_days is not None:
            assert season_profit(model) > staple, (
                f"{slug} returns {season_profit(model)} over a season, "
                f"less than turnips at {staple}"
            )


def test_produce_is_worth_something_at_any_shop():
    """
    Shops that do not list an item fall back to its intrinsic cost. Produce
    with no cost would be worth nothing outside the farm counter.
    """
    for model in load_crops().values():
        produce = load_item_yaml(model.produce_item)
        assert produce.get("cost", 0) > 0, model.produce_item


def test_the_farm_counter_pays_better_than_the_fallback():
    """
    Selling where you bought the seed should be the better deal.
    """
    stock = load_farm_economy()
    resale_multiplier = 0.5  # the general Scoops all use this

    for model in load_crops().values():
        here = stock[model.produce_item]["cost"]
        elsewhere = (
            load_item_yaml(model.produce_item)["cost"] * resale_multiplier
        )
        assert here > elsewhere, model.produce_item


def test_the_shop_and_its_seller_are_named():
    """
    The shop title and the NPC both read from the locale file. A missing
    entry shows the raw slug to the player.
    """
    po = Path("mods/tuxemon/l18n/en_US/LC_MESSAGES/base.po").read_text(
        encoding="utf-8"
    )
    for msgid in (
        FARM_ECONOMY,
        "spyder_papermart_orla",
        "spyder_paper_scoop_farm_welcome",
    ):
        assert f'msgid "{msgid}"' in po, f"no translation for {msgid}"


def test_the_seed_seller_is_wired_into_the_paper_town_scoop():
    path = Path("mods/tuxemon/maps/spyder_paper_scoop.yaml")
    with path.open(encoding="utf-8") as handle:
        events = yaml.safe_load(handle)["events"]

    create = events["Create Seed Seller"]
    assert (
        f"set_economy spyder_papermart_orla,{FARM_ECONOMY}"
        in create["actions"]
    )
    # she must not appear during the opening cutscene
    assert "is variable_set intro_scoop:done" in create["conditions"]

    talk = events["Talk Orla"]
    assert "talk spyder_papermart_orla" in talk["behav"]
    assert "open_shop spyder_papermart_orla,both_item" in talk["actions"]
