#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Play the whole planting loop end to end, headless, with time faked forward.

Growth is real-world time, so waiting out a six-minute crop by hand is no way
to check anything. This drives the loop the way a player does -- the map event
lays the plot out, the Fruit is used from the bag menu, the watering can is
used from the bag menu, INTERACT harvests -- while a fake clock jumps hours at
a time. The save is written to disk and read back in the middle, so the
persistence claim is checked too.

Run from the repository root::

    python scripts/farming_demo.py

Exits non-zero if any step misbehaves.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Headless: a dummy video driver still gives a real display surface, which
# pygame needs before it will convert any of the game's images.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

HOUR = 60 * 60.0

MAP_NAME = "spyder_timber_walledgarden1.tmx"
PLOT_ORIGIN = (5, 9)
FRUIT = "fire_berry"
CAN = "watering_can"
PARTY_MONSTER = "rockitten"


class FakeClock:
    """A wall clock the demo can push forward."""

    def __init__(self, start: float = 1_700_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def fail(message: str) -> None:
    print(f"  FAIL: {message}")
    raise SystemExit(1)


def check(condition: bool, message: str) -> None:
    if not condition:
        fail(message)
    print(f"  ok: {message}")


def build_client(save_dir: Path) -> tuple[Any, Any]:
    """Bring up a real client, world and player on the garden map."""
    from tuxemon.constants import paths

    # Write saves into the throwaway directory, never over the player's own.
    save_dir.mkdir(parents=True, exist_ok=True)
    paths.USER_GAME_SAVE_DIR = save_dir

    from tuxemon.prepare import pygame_init

    context = pygame_init()

    from tuxemon.client import LocalPygameClient
    from tuxemon.config import TuxemonConfig
    from tuxemon.constants.asset_loader import fetch_asset
    from tuxemon.entity.npc import NPC
    from tuxemon.session import local_session

    client = LocalPygameClient.create(TuxemonConfig(), context)
    local_session.set_client(client)
    NPC.create_player(local_session, slug="npc_red")
    client.push_state(
        "WorldState",
        session=local_session,
        map_name=fetch_asset("maps", MAP_NAME),
    )
    return client, local_session


def place_player(session: Any, position: tuple[int, int], facing: str) -> None:
    """Stand the player on a tile, looking a given way."""
    from tuxemon.db import Direction
    from tuxemon.math import Vector2

    player = session.player
    player.body.position = Vector2(*position)
    player.set_facing(Direction(facing))


def use_item_from_bag(client: Any, session: Any, slug: str) -> None:
    """
    Use an item the way a player does: open the bag, pick the item, confirm.

    This deliberately goes through ItemMenuState and the confirm dialog rather
    than calling Item.use directly, so that a menu that refuses a
    world-targeted item shows up here as a failure.
    """
    from tuxemon.menu.interface import MenuItem
    from tuxemon.states.item_menu import ItemMenuState

    item = session.player.bag.find_item(slug)
    if item is None:
        fail(f"'{slug}' is not in the bag")

    menu_state = ItemMenuState(
        client, character=session.player, source="WorldMenuState"
    )
    client.push_state(menu_state)
    menu_state.on_menu_selection(MenuItem(None, None, None, item))

    if "ChoiceState" not in client.active_state_names:
        client.remove_state_by_name("ItemMenuState")
        fail(f"the bag refused to offer '{slug}' for use")

    choice = client.get_state_by_name("ChoiceState")
    use_option = next(
        (option for option in choice.menu.get_widgets() if option.get_title()),
        None,
    )
    if use_option is None:
        fail(f"no confirm option offered for '{slug}'")
    use_option.apply()

    for name in ("DialogState", "ChoiceState", "ItemMenuState"):
        client.remove_state_by_name(name)


def press_interact(client: Any) -> None:
    """Fire an INTERACT press and let the event engine act on it."""
    from tuxemon.platform.const import intentions
    from tuxemon.platform.events import PlayerInput

    client.input_cache.clear_frame_state()
    client.event_bus.publish(
        "PLAYER_INPUT", PlayerInput(intentions.INTERACT, 1, 1)
    )
    client.event_engine.check_conditions()
    client.event_engine.update_running_events(0.0)
    client.remove_state_by_name("DialogState")


def bag_count(session: Any, slug: str) -> int:
    item = session.player.bag.find_item(slug)
    return item.quantity if item else 0


def run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        save_dir = Path(tmp)
        client, session = build_client(save_dir)

        clock = FakeClock()
        farming = client.farming_manager
        farming.clock = clock

        # The bag menu asks whether an item is usable on any party monster
        # before it will offer it, so the demo needs a party. Rockitten is
        # earth type, which keeps the berry's combat-side "not already this
        # element" condition happy.
        client.event_engine.execute_action("add_monster", [PARTY_MONSTER, 5])

        print("\n1. The map's own events lay out the plot")
        map_slug = client.map_manager.map_slug
        check(
            not farming.is_tilled(map_slug, PLOT_ORIGIN),
            "nothing is tilled before the map's init events run",
        )
        # The plot and the tools both come from the init events in
        # maps/spyder_timber_walledgarden1.yaml, not from this script.
        client.event_engine.update(0.0)
        client.remove_state_by_name("DialogState")
        check(
            bag_count(session, CAN) == 1 and bag_count(session, FRUIT) == 3,
            "the map handed over a watering can and three berries",
        )
        check(
            farming.is_tilled(map_slug, PLOT_ORIGIN),
            f"{PLOT_ORIGIN} on '{map_slug}' is tilled by the map event",
        )
        check(
            farming.is_tilled(
                map_slug, (PLOT_ORIGIN[0] + 3, PLOT_ORIGIN[1] + 1)
            ),
            "and so is the far corner of the 4x2 plot",
        )
        check(
            not farming.is_tilled(map_slug, (0, 0)),
            "untouched ground is not tilled",
        )

        print("\n2. Planting a Fruit from the bag")
        place_player(session, (PLOT_ORIGIN[0], PLOT_ORIGIN[1] + 1), "up")
        before = bag_count(session, FRUIT)
        use_item_from_bag(client, session, FRUIT)
        tile = farming.get_tile(map_slug, PLOT_ORIGIN)
        check(
            tile is not None and tile.plant is not None,
            "a plant is now growing on the faced tile",
        )
        check(
            bag_count(session, FRUIT) == before - 1,
            f"one {FRUIT} was consumed ({before} -> {before - 1})",
        )
        check(tile.plant.stage(clock()) == 0, "it shows the first stage")

        print("\n3. Planting into an occupied tile fails")
        before = bag_count(session, FRUIT)
        use_item_from_bag(client, session, FRUIT)
        check(
            bag_count(session, FRUIT) == before,
            "no fruit was consumed on the occupied tile",
        )

        print("\n4. Planting on bare ground fails")
        place_player(session, (1, 10), "left")
        before = bag_count(session, FRUIT)
        use_item_from_bag(client, session, FRUIT)
        check(
            bag_count(session, FRUIT) == before,
            "no fruit was consumed on untilled ground",
        )

        print("\n5. The watering can")
        place_player(session, (1, 10), "left")
        use_item_from_bag(client, session, CAN)
        check(
            not farming.get_tile(map_slug, (0, 10)),
            "watering untilled ground changed nothing",
        )

        place_player(session, (PLOT_ORIGIN[0], PLOT_ORIGIN[1] + 1), "up")
        use_item_from_bag(client, session, CAN)
        check(
            len(tile.waterings) == 1, "the watering was recorded on the tile"
        )
        check(tile.is_wet(clock()), "the tile is wet")
        check(
            bag_count(session, CAN) == 1,
            "the watering can was not consumed",
        )

        print("\n6. Saving and reloading keeps the plot")
        session.save_state(index=1, slot=1)
        planted_at = tile.plant.planted_at
        waterings = list(tile.waterings)

        from tuxemon.save_system.save_manager import SaveManager

        farming.set_state({})
        check(not farming.plots, "the in-memory plot was cleared")
        reloaded = SaveManager.load(1)
        if reloaded is None:
            fail("the save could not be read back")
        session.world.set_state(session, reloaded.world_state)
        tile = farming.get_tile(map_slug, PLOT_ORIGIN)
        check(
            tile is not None and tile.plant is not None,
            "the plant came back from disk",
        )
        check(
            tile.plant.planted_at == planted_at,
            "with its planted-at time intact",
        )
        check(tile.waterings == waterings, "and its watering history intact")

        print("\n7. Growing on the wall clock")
        stages = []
        for offset in (0, 61, 181, 361):
            stages.append(tile.plant.stage(planted_at + offset))
        check(
            stages == [0, 1, 2, 3],
            f"the stage advances with elapsed time: {stages}",
        )
        check(
            not tile.plant.is_mature(planted_at + 359),
            "it is not ripe a couple of seconds early",
        )

        print("\n8. Drying out after 24 hours")
        clock.advance(23 * HOUR)
        check(tile.is_wet(clock()), "still wet after 23 hours")
        clock.advance(2 * HOUR)
        check(not tile.is_wet(clock()), "dry after 25 hours")

        print("\n9. Harvesting with INTERACT")
        check(tile.plant.is_mature(clock()), "the plant is fully grown")
        fraction = tile.watered_fraction(clock())
        expected = tile.harvest_amount(clock())
        print(
            f"     watered for {fraction:.0%} of its growth "
            f"-> yield {1 + fraction:.2f} -> {expected} fruit"
        )
        check(
            abs(fraction - 1.0) < 1e-9,
            "one watering covered the whole six-minute growth window",
        )

        place_player(session, (PLOT_ORIGIN[0], PLOT_ORIGIN[1] + 1), "up")
        before = bag_count(session, FRUIT)
        press_interact(client)
        check(
            bag_count(session, FRUIT) == before + expected,
            f"the map event handed over {expected} {FRUIT}",
        )
        tile = farming.get_tile(map_slug, PLOT_ORIGIN)
        check(tile is not None and tile.is_empty, "the tile is empty again")
        check(
            farming.is_tilled(map_slug, PLOT_ORIGIN),
            "and still tilled, ready to replant",
        )

        print("\n10. A plant that is never watered still grows")
        place_player(session, (PLOT_ORIGIN[0], PLOT_ORIGIN[1] + 1), "up")
        use_item_from_bag(client, session, FRUIT)
        tile = farming.get_tile(map_slug, PLOT_ORIGIN)
        tile.waterings.clear()
        clock.advance(HOUR)
        check(tile.plant.is_mature(clock()), "it matured unwatered")
        check(
            tile.harvest_amount(clock()) == 2,
            "and yields the minimum 2 fruit",
        )
        before = bag_count(session, FRUIT)
        press_interact(client)
        check(
            bag_count(session, FRUIT) == before + 2,
            "which is what the player receives",
        )

        print("\n11. An unripe plant is left alone")
        place_player(session, (PLOT_ORIGIN[0], PLOT_ORIGIN[1] + 1), "up")
        use_item_from_bag(client, session, FRUIT)
        before = bag_count(session, FRUIT)
        press_interact(client)
        check(
            bag_count(session, FRUIT) == before,
            "nothing was harvested from the seedling",
        )
        tile = farming.get_tile(map_slug, PLOT_ORIGIN)
        check(
            tile is not None and tile.plant is not None,
            "and it is still in the ground",
        )

    print("\nAll steps passed.")


if __name__ == "__main__":
    run()
