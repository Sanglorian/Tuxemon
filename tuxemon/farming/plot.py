# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
The state and the arithmetic of a single tilled tile.

Everything here is pure: no pygame, no session, no client. A tile stores
absolute wall-clock timestamps and every derived value (growth stage, how long
the tile was wet, the yield) is recomputed from them on demand. That is what
makes growth survive the game being closed -- there is nothing to tick.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

#: How long one watering keeps a tile wet, in seconds (24 hours).
WET_DURATION: float = 24 * 60 * 60.0

#: Fruit handed over for a plant that spent none of its growing life watered.
BASE_YIELD: float = 1.0

#: Multiplier applied to the yield before rounding up into whole fruit.
HARVEST_MULTIPLIER: int = 2

# Ratios are floating point, so 50% watered can land on 1.4999999999999998 and
# ceil() would turn a clean 3 into a 4. Round the product back to this many
# decimal places before rounding up.
_HARVEST_PRECISION: int = 9


def merge_intervals(
    intervals: Sequence[tuple[float, float]],
) -> list[tuple[float, float]]:
    """
    Collapse overlapping or touching intervals into their union.

    Parameters:
        intervals: Half-open ``(start, end)`` pairs, in any order.

    Returns:
        Disjoint intervals sorted by start. Empty or reversed inputs are
        dropped.
    """
    ordered = sorted((start, end) for start, end in intervals if end > start)
    merged: list[tuple[float, float]] = []
    for start, end in ordered:
        if merged and start <= merged[-1][1]:
            last_start, last_end = merged[-1]
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def wet_seconds(
    waterings: Sequence[float],
    window_start: float,
    window_end: float,
    wet_duration: float = WET_DURATION,
) -> float:
    """
    Total time the tile was wet inside a window.

    Each watering at ``w`` makes the tile wet over ``[w, w + wet_duration)``.
    Watering again while already wet extends the wet period from the new
    timestamp rather than stacking, which falls out of taking the union.

    Parameters:
        waterings: Absolute timestamps of each watering, in any order.
        window_start: Start of the window to measure (inclusive).
        window_end: End of the window to measure (exclusive).
        wet_duration: How long one watering lasts.

    Returns:
        Seconds of overlap between the union of the wet periods and the window.
    """
    if window_end <= window_start:
        return 0.0

    total = 0.0
    for start, end in merge_intervals(
        [(w, w + wet_duration) for w in waterings]
    ):
        overlap = min(end, window_end) - max(start, window_start)
        if overlap > 0:
            total += overlap
    return total


def stage_index(elapsed: float, stage_seconds: Sequence[float]) -> int:
    """
    Which sprite stage a plant of this age is showing.

    ``stage_seconds`` holds one duration per stage *transition*, so a plant
    with three durations has four stages, and the last one is final.

    Parameters:
        elapsed: Age of the plant in seconds.
        stage_seconds: Duration of each transition, in order.

    Returns:
        Index into the stage list, clamped to ``[0, len(stage_seconds)]``.
    """
    if elapsed <= 0:
        return 0

    boundary = 0.0
    for index, duration in enumerate(stage_seconds):
        boundary += duration
        if elapsed < boundary:
            return index
    return len(stage_seconds)


def yield_value(fraction: float) -> float:
    """
    Yield for a plant that spent ``fraction`` of its growing life watered.

    Parameters:
        fraction: Watered share of the growth window, 0.0 to 1.0.

    Returns:
        A value from ``BASE_YIELD`` (never watered) to ``BASE_YIELD + 1``.
    """
    return BASE_YIELD + min(max(fraction, 0.0), 1.0)


def harvest_amount(fraction: float) -> int:
    """
    Whole fruit handed over for a plant watered ``fraction`` of its life.

    Parameters:
        fraction: Watered share of the growth window, 0.0 to 1.0.

    Returns:
        ``ceil(HARVEST_MULTIPLIER * yield_value(fraction))``.
    """
    product = HARVEST_MULTIPLIER * yield_value(fraction)
    return math.ceil(round(product, _HARVEST_PRECISION))


@dataclass
class Plant:
    """
    A fruit growing on a tilled tile.

    Attributes:
        fruit: Slug of the item that was planted, and of the item harvested.
        planted_at: Absolute wall-clock timestamp of planting.
        stage_seconds: Duration of each stage transition, copied from config
            at planting time so retuning the config cannot rewrite the past
            of a plant already in the ground.
    """

    fruit: str
    planted_at: float
    stage_seconds: list[float] = field(default_factory=list)

    @property
    def grow_seconds(self) -> float:
        """Total time from planting to maturity."""
        return float(sum(self.stage_seconds))

    @property
    def matured_at(self) -> float:
        """Absolute timestamp at which the plant reaches its final stage."""
        return self.planted_at + self.grow_seconds

    @property
    def stage_count(self) -> int:
        """Number of sprite stages, one more than the transition count."""
        return len(self.stage_seconds) + 1

    def age(self, now: float) -> float:
        """Seconds since the plant went into the ground."""
        return max(now - self.planted_at, 0.0)

    def stage(self, now: float) -> int:
        """Index of the sprite stage showing at ``now``."""
        return stage_index(self.age(now), self.stage_seconds)

    def is_mature(self, now: float) -> bool:
        """Whether the plant has reached its final stage and can be harvested."""
        return now >= self.matured_at

    def watered_fraction(
        self, waterings: Sequence[float], now: float
    ) -> float:
        """
        Share of the growth window the tile spent wet.

        Measured over ``[planted_at, matured_at]`` only, so a ripe plant left
        to sit dry loses nothing, and the window is truncated at ``now`` while
        the plant is still growing.

        Parameters:
            waterings: Watering timestamps recorded on the tile.
            now: Current wall-clock time.

        Returns:
            A value from 0.0 to 1.0. Zero if the plant matures instantly.
        """
        grow_seconds = self.grow_seconds
        if grow_seconds <= 0:
            return 0.0

        window_end = min(now, self.matured_at)
        wet = wet_seconds(waterings, self.planted_at, window_end)
        return min(wet / grow_seconds, 1.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fruit": self.fruit,
            "planted_at": self.planted_at,
            "stage_seconds": list(self.stage_seconds),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Plant:
        return cls(
            fruit=str(data["fruit"]),
            planted_at=float(data["planted_at"]),
            stage_seconds=[float(s) for s in data.get("stage_seconds", [])],
        )


@dataclass
class TilledTile:
    """
    A tile a map author (or the player) has turned into workable soil.

    Watering timestamps live here rather than on the :class:`Plant`, so
    watering a tilled tile before anything is planted still counts once
    something goes in.

    Attributes:
        waterings: Absolute timestamps of every watering, oldest first.
        plant: The plant currently growing here, if any.
    """

    waterings: list[float] = field(default_factory=list)
    plant: Plant | None = None

    @property
    def is_empty(self) -> bool:
        """Whether the tile is tilled but has nothing growing in it."""
        return self.plant is None

    def water(self, now: float) -> None:
        """Record a watering at ``now``."""
        self.waterings.append(now)
        self.waterings.sort()

    def is_wet(self, now: float) -> bool:
        """Whether a watering is still keeping this tile wet at ``now``."""
        return any(w <= now < w + WET_DURATION for w in self.waterings)

    def watered_fraction(self, now: float) -> float:
        """Share of the plant's growth window this tile spent wet."""
        if self.plant is None:
            return 0.0
        return self.plant.watered_fraction(self.waterings, now)

    def harvest_amount(self, now: float) -> int:
        """How much fruit this tile's plant would hand over right now."""
        if self.plant is None:
            return 0
        return harvest_amount(self.watered_fraction(now))

    def prune_waterings(self, now: float) -> None:
        """
        Drop watering timestamps that can no longer affect anything.

        Called after a harvest clears the tile: without a plant, only
        waterings still keeping the tile wet matter, and the rest would grow
        without bound in the save file.
        """
        if self.plant is not None:
            return
        self.waterings = [w for w in self.waterings if now < w + WET_DURATION]

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"waterings": list(self.waterings)}
        if self.plant is not None:
            data["plant"] = self.plant.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TilledTile:
        raw_plant = data.get("plant")
        return cls(
            waterings=sorted(float(w) for w in data.get("waterings", [])),
            plant=Plant.from_dict(raw_plant) if raw_plant else None,
        )
