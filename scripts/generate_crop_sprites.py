#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Generates placeholder sprite sheets for the farming layer.

These are stand-ins so the crop renderer can be seen working before real art
exists. Each sheet is a horizontal strip of 16-pixel-wide frames: one per
growth stage, youngest first, then the mature plant, then a withered frame.
Run from the repository root:

    python scripts/generate_crop_sprites.py
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

TILE = 16
OUT_DIR = Path("mods/tuxemon/sprites/crops")

SOIL_DRY = (122, 88, 62, 255)
SOIL_WET = (74, 52, 36, 255)
SOIL_EDGE = (54, 38, 26, 255)
WITHERED = (128, 116, 84, 255)
CLEAR = (0, 0, 0, 0)

# slug -> (growth stage count, frame height, leaf colour, fruit colour)
CROPS: dict[
    str, tuple[int, int, tuple[int, int, int], tuple[int, int, int]]
] = {
    "turnip": (4, 16, (86, 156, 74), (236, 236, 220)),
    "potato": (5, 16, (76, 132, 66), (198, 156, 96)),
    "tomato": (5, 24, (68, 140, 70), (206, 66, 52)),
    "corn": (5, 32, (96, 158, 68), (240, 206, 92)),
}


def new_sheet(frames: int, height: int) -> pygame.Surface:
    return pygame.Surface((TILE * frames, height), pygame.SRCALPHA)


def draw_soil(sheet: pygame.Surface, index: int, wet: bool) -> None:
    """A tilled tile: furrowed earth, darker when watered."""
    x = index * TILE
    body = SOIL_WET if wet else SOIL_DRY
    pygame.draw.rect(sheet, body, (x + 1, 1, TILE - 2, TILE - 2))
    pygame.draw.rect(sheet, SOIL_EDGE, (x + 1, 1, TILE - 2, TILE - 2), 1)
    for furrow_y in (5, 9, 13):
        pygame.draw.line(
            sheet, SOIL_EDGE, (x + 3, furrow_y), (x + TILE - 4, furrow_y)
        )


def draw_stage(
    sheet: pygame.Surface,
    index: int,
    height: int,
    progress: float,
    leaf: tuple[int, int, int],
    fruit: tuple[int, int, int],
) -> None:
    """
    A growing plant, anchored to the bottom of the frame so taller sheets rise
    out of the soil rather than floating above it.
    """
    x = index * TILE
    centre = x + TILE // 2
    plant_height = max(2, int((height - 3) * progress))
    base = height - 2

    pygame.draw.line(
        sheet, leaf, (centre, base), (centre, base - plant_height), 2
    )

    leaf_span = max(2, int(5 * progress))
    for offset in range(1, plant_height, 4):
        y = base - offset
        pygame.draw.line(sheet, leaf, (centre, y), (centre - leaf_span, y - 2))
        pygame.draw.line(sheet, leaf, (centre, y), (centre + leaf_span, y - 2))

    if progress >= 1.0:
        pygame.draw.circle(sheet, fruit, (centre, base - plant_height), 3)


def draw_withered(sheet: pygame.Surface, index: int, height: int) -> None:
    """A dead plant: a bare, drooping stalk."""
    x = index * TILE
    centre = x + TILE // 2
    base = height - 2
    pygame.draw.line(sheet, WITHERED, (centre, base), (centre, base - 5), 2)
    pygame.draw.line(
        sheet, WITHERED, (centre, base - 5), (centre + 3, base - 7), 2
    )
    pygame.draw.line(
        sheet, WITHERED, (centre, base - 3), (centre - 3, base - 5), 2
    )


def build_soil() -> None:
    sheet = new_sheet(2, TILE)
    draw_soil(sheet, 0, wet=False)
    draw_soil(sheet, 1, wet=True)
    pygame.image.save(sheet, str(OUT_DIR / "soil.png"))


def build_crop(
    slug: str,
    stages: int,
    height: int,
    leaf: tuple[int, int, int],
    fruit: tuple[int, int, int],
) -> None:
    sheet = new_sheet(stages + 1, height)
    for index in range(stages):
        progress = (index + 1) / stages
        draw_stage(sheet, index, height, progress, leaf, fruit)
    draw_withered(sheet, stages, height)
    pygame.image.save(sheet, str(OUT_DIR / f"{slug}.png"))


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    build_soil()
    for slug, (stages, height, leaf, fruit) in CROPS.items():
        build_crop(slug, stages, height, leaf, fruit)

    print(f"Wrote {len(CROPS) + 1} sheets to {OUT_DIR}")
    pygame.quit()


if __name__ == "__main__":
    main()
