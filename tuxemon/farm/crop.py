# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Final

from tuxemon.constants import paths
from tuxemon.database.yaml_utils import load_yaml

logger = logging.getLogger(__name__)

CROPS_FILENAME: Final[str] = "crops.yaml"


@dataclass(frozen=True)
class CropStage:
    """
    The visual state of a planted crop on a given day.

    ``index`` selects a frame from the crop's sprite sheet: frames run from
    the youngest seedling up to the mature plant, so a crop with three growth
    stages needs four frames. ``withered`` selects the optional final frame
    instead, when the sheet provides one.
    """

    index: int
    mature: bool
    withered: bool


@dataclass(frozen=True)
class CropModel:
    """A crop definition, loaded from ``mods/crops.yaml``."""

    slug: str
    seed_item: str
    produce_item: str
    sprite: str
    stage_days: tuple[int, ...]
    seasons: tuple[str, ...]
    water_tolerance: int = 2
    regrow_days: int | None = None
    harvest_yield: int = 1
    frame_width: int | None = None
    frame_height: int | None = None
    has_withered_frame: bool = True

    @property
    def days_to_mature(self) -> int:
        """Total watered days needed before the crop can be harvested."""
        return sum(self.stage_days)

    @property
    def growth_stage_count(self) -> int:
        """Number of sprite frames excluding any withered frame."""
        return len(self.stage_days) + 1

    def grows_in(self, season: str) -> bool:
        """Whether this crop can be planted in the given season."""
        return not self.seasons or season in self.seasons


def _parse_crop(slug: str, raw: dict[str, Any]) -> CropModel:
    stage_days = tuple(int(d) for d in raw["stage_days"])
    if not stage_days or any(d < 1 for d in stage_days):
        raise ValueError(
            f"Crop '{slug}' must define at least one stage of >= 1 day"
        )

    regrow = raw.get("regrow_days")
    return CropModel(
        slug=slug,
        seed_item=raw["seed_item"],
        produce_item=raw["produce_item"],
        sprite=raw["sprite"],
        stage_days=stage_days,
        seasons=tuple(raw.get("seasons", ())),
        water_tolerance=int(raw.get("water_tolerance", 2)),
        regrow_days=None if regrow is None else int(regrow),
        harvest_yield=int(raw.get("harvest_yield", 1)),
        frame_width=raw.get("frame_width"),
        frame_height=raw.get("frame_height"),
        has_withered_frame=bool(raw.get("has_withered_frame", True)),
    )


class CropLoader:
    """Caches the parsed contents of the crop config file."""

    _crops: dict[str, CropModel] = {}

    @classmethod
    def load(cls, filename: str = CROPS_FILENAME) -> dict[str, CropModel]:
        if not cls._crops:
            raw_data = load_yaml(paths.mods_folder / filename) or {}
            cls._crops = {
                slug: _parse_crop(slug, raw) for slug, raw in raw_data.items()
            }
            logger.debug(f"Loaded {len(cls._crops)} crop definitions")
        return cls._crops

    @classmethod
    def clear(cls) -> None:
        """Drops the cache. Used by tests and by mod reloading."""
        cls._crops = {}


def load_crops(filename: str = CROPS_FILENAME) -> dict[str, CropModel]:
    """Returns every known crop, keyed by slug."""
    return CropLoader.load(filename)


def lookup_crop(slug: str) -> CropModel | None:
    """Returns the crop definition for a slug, or ``None`` if unknown."""
    return load_crops().get(slug)


@dataclass
class PlantedCrop:
    """
    The mutable state of one crop growing on one tile.

    Growth is measured in *watered days*: a crop that goes unwatered does not
    advance, and withers once it has been dry for longer than the crop's
    ``water_tolerance``.
    """

    slug: str
    planted_day: int
    growth: int = 0
    dry_days: int = 0
    withered: bool = False
    harvests: int = 0
    _model: CropModel | None = field(
        default=None, repr=False, compare=False, kw_only=True
    )

    @property
    def model(self) -> CropModel | None:
        """The crop definition, resolved lazily and cached."""
        if self._model is None:
            self._model = lookup_crop(self.slug)
        return self._model

    def is_mature(self, model: CropModel) -> bool:
        """Whether the crop is ready to harvest."""
        return not self.withered and self.growth >= model.days_to_mature

    def get_stage(self, model: CropModel) -> CropStage:
        """Resolves the crop's current visual stage."""
        if self.withered:
            return CropStage(
                index=model.growth_stage_count, mature=False, withered=True
            )

        elapsed = 0
        for index, days in enumerate(model.stage_days):
            elapsed += days
            if self.growth < elapsed:
                return CropStage(index=index, mature=False, withered=False)

        return CropStage(
            index=len(model.stage_days), mature=True, withered=False
        )

    def advance_day(self, model: CropModel, watered: bool) -> None:
        """
        Applies one farm day to this crop.

        Parameters:
            model: The crop definition.
            watered: Whether the tile was watered during the day that just
                ended.
        """
        if self.withered:
            return

        if watered:
            self.growth += 1
            self.dry_days = 0
        else:
            self.dry_days += 1
            if self.dry_days > model.water_tolerance:
                self.withered = True
                logger.debug(f"Crop '{self.slug}' withered after drought")

    def harvest(self, model: CropModel) -> int:
        """
        Harvests the crop and returns the quantity produced.

        Returns 0 if the crop is not ready. Regrowing crops reset far enough
        to need ``regrow_days`` more watered days; others should be cleared
        from the tile by the caller once this returns.
        """
        if not self.is_mature(model):
            return 0

        self.harvests += 1
        if model.regrow_days is not None:
            self.growth = max(0, model.days_to_mature - model.regrow_days)
            self.dry_days = 0

        return model.harvest_yield

    def is_spent(self, model: CropModel) -> bool:
        """Whether the tile should be cleared: withered, or a one-off crop
        that has already been harvested."""
        return self.withered or (
            model.regrow_days is None and self.harvests > 0
        )

    def get_state(self) -> dict[str, Any]:
        """Prepares a dictionary of the crop to be saved."""
        return {
            "slug": self.slug,
            "planted_day": self.planted_day,
            "growth": self.growth,
            "dry_days": self.dry_days,
            "withered": self.withered,
            "harvests": self.harvests,
        }

    @classmethod
    def from_state(cls, save_data: dict[str, Any]) -> PlantedCrop:
        """Recreates a crop from saved data."""
        return cls(
            slug=str(save_data["slug"]),
            planted_day=int(save_data.get("planted_day", 1)),
            growth=int(save_data.get("growth", 0)),
            dry_days=int(save_data.get("dry_days", 0)),
            withered=bool(save_data.get("withered", False)),
            harvests=int(save_data.get("harvests", 0)),
        )
