# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tuxemon.world.world_map_index import (
    NATIVE_TILE,
    WorldMapEntry,
    WorldMapIndex,
)

# ---------------------------------------------------------------------------
# helpers


def make_tmx(tmp_path: Path, name: str, width: int, height: int) -> Path:
    """Write a minimal .tmx file and return its path."""
    path = tmp_path / name
    path.write_text(
        f'<map width="{width}" height="{height}" tilewidth="16" tileheight="16"/>'
    )
    return path


def make_world_file(tmp_path: Path, entries: list[dict]) -> Path:
    path = tmp_path / "test.world"
    path.write_text(json.dumps({"maps": entries}))
    return path


# ---------------------------------------------------------------------------
# WorldMapEntry


def test_entry_pixel_dimensions():
    entry = WorldMapEntry("a.tmx", 0, 0, 10, 20)
    assert entry.pixel_width == 10 * NATIVE_TILE
    assert entry.pixel_height == 20 * NATIVE_TILE


# ---------------------------------------------------------------------------
# WorldMapIndex loading


def test_load_auto_size_from_tmx(tmp_path):
    make_tmx(tmp_path, "map_a.tmx", 40, 40)
    world = make_world_file(
        tmp_path,
        [{"fileName": "map_a.tmx", "x": 0, "y": 0, "width": 0, "height": 0}],
    )
    idx = WorldMapIndex(world, tmp_path)
    entry = idx.get_entry("map_a.tmx")
    assert entry is not None
    assert entry.tile_width == 40
    assert entry.tile_height == 40


def test_load_explicit_pixel_size(tmp_path):
    # width/height in world file are pixel dimensions
    world = make_world_file(
        tmp_path,
        [
            {
                "fileName": "b.tmx",
                "x": 100,
                "y": 200,
                "width": 224,
                "height": 144,
            }
        ],
    )
    idx = WorldMapIndex(world, tmp_path)
    entry = idx.get_entry("b.tmx")
    assert entry is not None
    assert entry.tile_width == 224 // NATIVE_TILE
    assert entry.tile_height == 144 // NATIVE_TILE


def test_world_coords_stored(tmp_path):
    make_tmx(tmp_path, "c.tmx", 20, 15)
    world = make_world_file(
        tmp_path,
        [{"fileName": "c.tmx", "x": 640, "y": 320, "width": 0, "height": 0}],
    )
    idx = WorldMapIndex(world, tmp_path)
    entry = idx.get_entry("c.tmx")
    assert entry is not None
    assert entry.world_x == 640
    assert entry.world_y == 320


def test_from_maps_dir_finds_world_file(tmp_path):
    make_tmx(tmp_path, "x.tmx", 10, 10)
    make_world_file(
        tmp_path,
        [{"fileName": "x.tmx", "x": 0, "y": 0, "width": 0, "height": 0}],
    )
    idx = WorldMapIndex.from_maps_dir(tmp_path)
    assert idx is not None
    assert idx.is_world_map("x.tmx")


def test_from_maps_dir_returns_none_when_no_world_file(tmp_path):
    assert WorldMapIndex.from_maps_dir(tmp_path) is None


# ---------------------------------------------------------------------------
# is_world_map


def test_is_world_map_returns_true_for_known_map(tmp_path):
    make_tmx(tmp_path, "known.tmx", 10, 10)
    world = make_world_file(
        tmp_path,
        [{"fileName": "known.tmx", "x": 0, "y": 0, "width": 0, "height": 0}],
    )
    idx = WorldMapIndex(world, tmp_path)
    assert idx.is_world_map("known.tmx")


def test_is_world_map_ignores_directory_prefix(tmp_path):
    make_tmx(tmp_path, "known.tmx", 10, 10)
    world = make_world_file(
        tmp_path,
        [{"fileName": "known.tmx", "x": 0, "y": 0, "width": 0, "height": 0}],
    )
    idx = WorldMapIndex(world, tmp_path)
    assert idx.is_world_map("/some/path/known.tmx")


def test_is_world_map_returns_false_for_unknown_map(tmp_path):
    world = make_world_file(tmp_path, [])
    idx = WorldMapIndex(world, tmp_path)
    assert not idx.is_world_map("unknown.tmx")


# ---------------------------------------------------------------------------
# get_entry


def test_get_entry_returns_none_for_missing(tmp_path):
    world = make_world_file(tmp_path, [])
    idx = WorldMapIndex(world, tmp_path)
    assert idx.get_entry("missing.tmx") is None


def test_get_entry_accepts_path_prefix(tmp_path):
    make_tmx(tmp_path, "m.tmx", 5, 5)
    world = make_world_file(
        tmp_path,
        [{"fileName": "m.tmx", "x": 0, "y": 0, "width": 0, "height": 0}],
    )
    idx = WorldMapIndex(world, tmp_path)
    assert idx.get_entry("mods/tuxemon/maps/m.tmx") is not None


# ---------------------------------------------------------------------------
# get_nearby_entries — adjacency


def _two_adjacent_maps(tmp_path: Path, gap: int = 0) -> WorldMapIndex:
    """Create an index with two 40×40 maps placed east-west with an optional gap."""
    make_tmx(tmp_path, "west.tmx", 40, 40)
    make_tmx(tmp_path, "east.tmx", 40, 40)
    west_w = 40 * NATIVE_TILE  # 640 px
    world = make_world_file(
        tmp_path,
        [
            {"fileName": "west.tmx", "x": 0, "y": 0, "width": 0, "height": 0},
            {
                "fileName": "east.tmx",
                "x": west_w + gap,
                "y": 0,
                "width": 0,
                "height": 0,
            },
        ],
    )
    return WorldMapIndex(world, tmp_path)


def test_adjacent_map_found_when_touching(tmp_path):
    idx = _two_adjacent_maps(tmp_path, gap=0)
    nearby = idx.get_nearby_entries("west.tmx", viewport_native_px=(320, 240))
    names = [e.filename for e in nearby]
    assert "east.tmx" in names


def test_current_map_excluded_from_nearby(tmp_path):
    idx = _two_adjacent_maps(tmp_path, gap=0)
    nearby = idx.get_nearby_entries("west.tmx", viewport_native_px=(320, 240))
    names = [e.filename for e in nearby]
    assert "west.tmx" not in names


def test_far_away_map_not_returned(tmp_path):
    make_tmx(tmp_path, "near.tmx", 40, 40)
    make_tmx(tmp_path, "far.tmx", 40, 40)
    near_w = 40 * NATIVE_TILE
    # Place "far" 3 viewports away so it shouldn't be included
    world = make_world_file(
        tmp_path,
        [
            {"fileName": "near.tmx", "x": 0, "y": 0, "width": 0, "height": 0},
            {
                "fileName": "far.tmx",
                "x": near_w * 10,
                "y": 0,
                "width": 0,
                "height": 0,
            },
        ],
    )
    idx = WorldMapIndex(world, tmp_path)
    nearby = idx.get_nearby_entries("near.tmx", viewport_native_px=(320, 240))
    assert not any(e.filename == "far.tmx" for e in nearby)


def test_returns_empty_for_unknown_current_map(tmp_path):
    world = make_world_file(tmp_path, [])
    idx = WorldMapIndex(world, tmp_path)
    assert idx.get_nearby_entries("nonexistent.tmx", (320, 240)) == []


def test_real_spyder_world_loads():
    """Smoke test: the actual spyder.world file loads without error."""
    world_file = Path("mods/tuxemon/maps/spyder.world")
    maps_dir = world_file.parent
    if not world_file.exists():
        pytest.skip("spyder.world not available")
    idx = WorldMapIndex(world_file, maps_dir)
    assert idx.is_world_map("spyder_flower_city.tmx")
    entry = idx.get_entry("spyder_flower_city.tmx")
    assert entry is not None
    assert entry.world_x == 640
    assert entry.world_y == 640
    assert entry.tile_width == 40
    assert entry.tile_height == 40


def test_real_spyder_adjacency():
    """Flower City and Route 4 are east-west neighbours in spyder.world."""
    world_file = Path("mods/tuxemon/maps/spyder.world")
    maps_dir = world_file.parent
    if not world_file.exists():
        pytest.skip("spyder.world not available")
    idx = WorldMapIndex(world_file, maps_dir)
    nearby = idx.get_nearby_entries("spyder_flower_city.tmx", (320, 240))
    names = [e.filename for e in nearby]
    assert "spyder_route4.tmx" in names
    assert "spyder_route5.tmx" in names
    assert "spyder_routea.tmx" in names


def test_touching_entries_include_edge_and_corner_neighbours(tmp_path):
    for name in ("mid.tmx", "east.tmx", "corner.tmx", "far.tmx"):
        make_tmx(tmp_path, name, 10, 10)
    size = 10 * NATIVE_TILE
    world = make_world_file(
        tmp_path,
        [
            {"fileName": "mid.tmx", "x": 0, "y": 0, "width": 0, "height": 0},
            {
                "fileName": "east.tmx",
                "x": size,
                "y": 0,
                "width": 0,
                "height": 0,
            },
            {
                "fileName": "corner.tmx",
                "x": size,
                "y": size,
                "width": 0,
                "height": 0,
            },
            # Two tiles away: nearby, but not touching.
            {
                "fileName": "far.tmx",
                "x": -size - 2 * NATIVE_TILE,
                "y": 0,
                "width": 0,
                "height": 0,
            },
        ],
    )
    idx = WorldMapIndex(world, tmp_path)
    names = {e.filename for e in idx.get_touching_entries("mid.tmx")}
    assert names == {"east.tmx", "corner.tmx"}


def test_touching_entries_unknown_map(tmp_path):
    make_tmx(tmp_path, "a.tmx", 10, 10)
    world = make_world_file(
        tmp_path,
        [{"fileName": "a.tmx", "x": 0, "y": 0, "width": 0, "height": 0}],
    )
    assert WorldMapIndex(world, tmp_path).get_touching_entries("x.tmx") == []


def _east_west(tmp_path: Path) -> WorldMapIndex:
    make_tmx(tmp_path, "west.tmx", 10, 10)
    make_tmx(tmp_path, "east.tmx", 10, 10)
    size = 10 * NATIVE_TILE
    world = make_world_file(
        tmp_path,
        [
            {"fileName": "west.tmx", "x": 0, "y": 0, "width": 0, "height": 0},
            {
                "fileName": "east.tmx",
                "x": size,
                "y": 0,
                "width": 0,
                "height": 0,
            },
        ],
    )
    return WorldMapIndex(world, tmp_path)


def test_seamless_link_for_walk_across_border(tmp_path):
    idx = _east_west(tmp_path)
    # Standing on west's last column, arriving on east's first column.
    assert idx.is_seamless_link("west.tmx", (9, 4), "east.tmx", (0, 4))


def test_no_seamless_link_when_destination_is_far_away(tmp_path):
    idx = _east_west(tmp_path)
    # A door or warp: same pair of maps, but nowhere near each other.
    assert not idx.is_seamless_link("west.tmx", (2, 2), "east.tmx", (7, 8))


def test_no_seamless_link_for_unknown_or_same_map(tmp_path):
    idx = _east_west(tmp_path)
    assert not idx.is_seamless_link("west.tmx", (9, 4), "cave.tmx", (0, 4))
    assert not idx.is_seamless_link("west.tmx", (1, 1), "west.tmx", (2, 1))
