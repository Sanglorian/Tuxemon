#!/usr/bin/env python3
"""
Cheat script: add every monster in the database to monster storage boxes.

Usage:
    python scripts/cheat_all_monsters.py --slot SLOT [--level LEVEL]

Run from the Tuxemon root directory. The game must NOT be running.
"""

import argparse
import sys
from pathlib import Path

# Ensure tuxemon package is importable from repo root.
sys.path.insert(0, str(Path(__file__).parent.parent))

from tuxemon.constants import paths
from tuxemon.database import db as _db_module
from tuxemon.monster.monster import Monster
from tuxemon.save_system import save as save_module
from tuxemon.save_system.save import get_save_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Add all monsters to a save file.")
    parser.add_argument("--slot", type=int, required=True, help="Save slot number")
    parser.add_argument("--level", type=int, default=5, help="Monster level (default: 5)")
    args = parser.parse_args()

    save_path = get_save_path(args.slot)
    if not save_path.exists():
        print(f"Save file not found: {save_path}")
        print("Start a new game, save once, then re-run this script.")
        sys.exit(1)

    save_data = save_module.load(save_path)
    if save_data is None:
        print("Failed to load save data.")
        sys.exit(1)

    # Collect every monster slug from the database.
    monster_slugs = sorted(_db_module.database["monster"].keys())
    print(f"Found {len(monster_slugs)} monsters in the database.")

    npc = save_data.npc_state
    if npc is None:
        print("Save file has no player state (npc_state is None).")
        sys.exit(1)

    # Get existing party slugs so we can skip duplicates already in storage.
    existing = {m["slug"] for m in npc.monsters}
    for box_monsters in npc.monster_boxes.values():
        for m in box_monsters:
            existing.add(m["slug"])

    # Spawn and pack into boxes of 30.
    BOX_SIZE = 30
    new_monsters: list[dict] = []
    skipped = 0
    for slug in monster_slugs:
        if slug in existing:
            skipped += 1
            continue
        try:
            m = Monster.spawn_base(slug, args.level)
            new_monsters.append(dict(m.get_state()))
        except Exception as e:
            print(f"  Warning: could not spawn {slug!r}: {e}")

    if not new_monsters:
        print("All monsters are already in the save. Nothing to do.")
        sys.exit(0)

    print(f"Adding {len(new_monsters)} monsters ({skipped} already present).")

    # Find the highest existing cheat-box index so we don't overwrite real boxes.
    existing_box_keys = set(npc.monster_boxes.keys())
    cheat_box_idx = 1
    while f"cheat_box_{cheat_box_idx}" in existing_box_keys:
        cheat_box_idx += 1

    # Build updated monster_boxes dict.
    boxes_dict = dict(npc.monster_boxes)
    chunk_start = 0
    while chunk_start < len(new_monsters):
        chunk = new_monsters[chunk_start : chunk_start + BOX_SIZE]
        box_key = f"cheat_box_{cheat_box_idx}"
        boxes_dict[box_key] = chunk
        print(f"  Created box {box_key!r} with {len(chunk)} monsters.")
        cheat_box_idx += 1
        chunk_start += BOX_SIZE

    # Pydantic models are immutable by default; rebuild with updated fields.
    updated_npc = npc.model_copy(update={"monster_boxes": boxes_dict})
    final_save = save_data.model_copy(update={"npc_state": updated_npc})

    save_module.save(final_save, save_path)
    print(f"Done! Save written to {save_path}")


if __name__ == "__main__":
    main()