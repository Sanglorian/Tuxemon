# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Which items can be planted, and how long each one takes to grow.

Backed by ``mods/planting.yaml``; see that file for the format. An item is
plantable if, and only if, it has an entry there *and* carries the ``plant``
effect, so no existing item category has to be repurposed.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tuxemon.constants import paths
from tuxemon.database.yaml_utils import load_yaml

logger = logging.getLogger(__name__)

CONFIG_FILENAME = "planting.yaml"

#: Sprite shown on a tilled tile with nothing growing in it.
DEFAULT_TILLED_SPRITE = "gfx/farming/tilled.png"

#: Sprite shown on a tilled tile that is currently wet.
DEFAULT_TILLED_WET_SPRITE = "gfx/farming/tilled_wet.png"


@dataclass
class FruitConfig:
    """
    Growth settings for one plantable item.

    Attributes:
        slug: Slug of the item, which is also the slug harvested back.
        stage_seconds: Duration of each stage transition, in seconds. One
            fewer entry than there are sprites.
        stages: Sprite paths, one per stage, in growth order.
    """

    slug: str
    stage_seconds: list[float] = field(default_factory=list)
    stages: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if not self.stage_seconds:
            raise ValueError(f"'{self.slug}' declares no stage_seconds.")
        if any(duration <= 0 for duration in self.stage_seconds):
            raise ValueError(
                f"'{self.slug}' has a non-positive stage duration."
            )
        if len(self.stages) != len(self.stage_seconds) + 1:
            raise ValueError(
                f"'{self.slug}' needs exactly one more sprite than it has "
                f"stage durations: got {len(self.stages)} sprites for "
                f"{len(self.stage_seconds)} durations."
            )


@dataclass
class PlantingConfig:
    """Everything ``mods/planting.yaml`` declares."""

    fruits: dict[str, FruitConfig] = field(default_factory=dict)
    tilled_sprite: str = DEFAULT_TILLED_SPRITE
    tilled_wet_sprite: str = DEFAULT_TILLED_WET_SPRITE

    def is_plantable(self, slug: str) -> bool:
        return slug in self.fruits

    def get(self, slug: str) -> FruitConfig | None:
        return self.fruits.get(slug)


def _build(raw: Mapping[str, Any]) -> PlantingConfig:
    defaults = raw.get("defaults") or {}
    default_seconds = [float(s) for s in defaults.get("stage_seconds", [])]
    default_stages = [str(s) for s in defaults.get("stages", [])]

    fruits: dict[str, FruitConfig] = {}
    for slug, entry in (raw.get("fruits") or {}).items():
        entry = entry or {}
        fruit = FruitConfig(
            slug=str(slug),
            stage_seconds=[
                float(s) for s in entry.get("stage_seconds", default_seconds)
            ],
            stages=[str(s) for s in entry.get("stages", default_stages)],
        )
        fruit.validate()
        fruits[fruit.slug] = fruit

    return PlantingConfig(
        fruits=fruits,
        tilled_sprite=str(raw.get("tilled_sprite", DEFAULT_TILLED_SPRITE)),
        tilled_wet_sprite=str(
            raw.get("tilled_wet_sprite", DEFAULT_TILLED_WET_SPRITE)
        ),
    )


_cache: PlantingConfig | None = None


def load_planting_config(path: Path) -> PlantingConfig:
    """Read and validate a planting config from an explicit path."""
    return _build(load_yaml(path) or {})


def get_planting_config(reload: bool = False) -> PlantingConfig:
    """
    The planting config, loaded once and cached.

    Parameters:
        reload: Re-read the file instead of using the cached copy.

    Returns:
        The parsed config, or an empty one if the file is missing or invalid,
        in which case nothing is plantable but the game still runs.
    """
    global _cache
    if _cache is None or reload:
        try:
            _cache = load_planting_config(paths.mods_folder / CONFIG_FILENAME)
        except Exception as e:
            logger.error(f"Could not load {CONFIG_FILENAME}: {e}")
            _cache = PlantingConfig()
    return _cache
