# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tuxemon.map.manager import MapManager, MapType
from tuxemon.map.tuxemon import AbstractMap


@pytest.fixture
def map_manager():
    return MapManager()


@pytest.fixture
def mock_map():
    def _factory(map_type="town"):
        m = MagicMock(spec=AbstractMap)
        m.events = ["event1", "event2"]
        m.inits = ["init1", "init2"]
        m.maps = {"map1": "data1", "map2": "data2"}
        m.slug = "map_slug"
        m.name = "map_name"
        m.description = "map_description"
        m.inside = True
        m.is_inside = True
        m.size = (10, 20)
        m.map_type = map_type
        m.north_trans = "north"
        m.south_trans = "south"
        m.east_trans = "east"
        m.west_trans = "west"
        m.collision_lines_map = set()
        m.surface_map = {}
        m.collision_map = {}
        m.filename = "map_filename"
        return m

    return _factory


@pytest.mark.parametrize(
    "attr, expected",
    [
        ("events", []),
        ("inits", []),
        ("current_map", None),
        ("maps", {}),
        ("map_slug", ""),
        ("map_name", "Unknown Location"),
        ("map_desc", ""),
        ("map_inside", False),
        ("map_size", (0, 0)),
        ("map_type", MapType()),
        ("map_north", ""),
        ("map_south", ""),
        ("map_east", ""),
        ("map_west", ""),
    ],
)
def test_init(map_manager, attr, expected):
    assert getattr(map_manager, attr) == expected


def test_load_map(map_manager, mock_map):
    m = mock_map()
    map_manager.load_map(m)

    assert map_manager.current_map == m
    assert map_manager.events == m.events
    assert map_manager.inits == m.inits
    assert map_manager.maps == m.maps
    assert map_manager.map_slug == m.slug
    assert map_manager.map_name == m.name
    assert map_manager.map_desc == m.description
    assert map_manager.map_inside is True
    assert map_manager.map_size == m.size
    assert map_manager.map_type == MapType(name="town")
    assert map_manager.map_north == m.north_trans
    assert map_manager.map_south == m.south_trans
    assert map_manager.map_east == m.east_trans
    assert map_manager.map_west == m.west_trans
    assert map_manager.collision_lines_map == m.collision_lines_map
    assert map_manager.surface_map == m.surface_map
    assert map_manager.collision_map == m.collision_map


def test_load_map_with_invalid_map_type(map_manager, mock_map):
    m = mock_map(map_type="unknown_type")
    map_manager.load_map(m)
    assert map_manager.map_type.name == "notype"


def test_is_in_location_type(map_manager, mock_map):
    m = mock_map(map_type="town")
    map_manager.load_map(m)

    assert map_manager.is_in_location_type("town") is True
    assert map_manager.is_in_location_type("shop") is False


def test_get_map_filepath(map_manager, mock_map):
    assert map_manager.get_map_filepath() is None

    m = mock_map()
    map_manager.current_map = m
    assert map_manager.get_map_filepath() == m.filename


def test_get_map_name(map_manager, mock_map):
    assert map_manager.get_map_filepath() is None

    m = mock_map()
    map_manager.current_map = m

    assert map_manager.get_map_name() == Path(m.filename).name


def test_map_type_property_logs_warning_for_invalid_type(
    map_manager, mock_map, caplog
):
    m = mock_map(map_type="invalid")

    with caplog.at_level("WARNING", logger="tuxemon.map.manager"):
        map_manager.load_map(m)
        _ = map_manager.map_type

    assert any("Invalid map type" in msg for msg in caplog.messages)


@pytest.mark.parametrize(
    "slug, expected",
    [
        (None, "notype"),
        ("town", "town"),
        ("unknown", "notype"),
    ],
)
def test_map_type_slug_variants(map_manager, slug, expected):
    map_manager._map_type_slug = slug
    assert map_manager.map_type.name == expected


@pytest.mark.parametrize(
    "prop, expected",
    [
        ("collision_lines_map", set()),
        ("surface_map", {}),
        ("collision_map", {}),
        ("map_north", ""),
        ("map_south", ""),
        ("map_east", ""),
        ("map_west", ""),
    ],
)
def test_properties_without_map(map_manager, prop, expected):
    assert getattr(map_manager, prop) == expected
