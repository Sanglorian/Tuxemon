# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from typing import Protocol, TypeVar, overload

from tuxemon.prepare import DISPLAY_CONTEXT

TVarSequence = TypeVar("TVarSequence", bound=tuple[int, ...])


class ScalingStrategy(Protocol):
    """
    Strategy interface for scaling coordinate tuples.
    """

    def scale_tuple(self, coords: TVarSequence) -> TVarSequence: ...
    def scale_int(self, value: int) -> int: ...


class DefaultScaling:
    def scale_tuple(self, coords: TVarSequence) -> TVarSequence:
        return type(coords)(i * DISPLAY_CONTEXT.scale for i in coords)

    def scale_int(self, value: int) -> int:
        return value * DISPLAY_CONTEXT.scale


class ResolutionScaling:
    def __init__(
        self,
        base_resolution: tuple[int, int],
        current_resolution: tuple[int, int],
    ):
        self.base_w, self.base_h = base_resolution
        self.curr_w, self.curr_h = current_resolution

    def scale_int(self, value: int) -> int:
        # scale uniformly using width ratio
        return int(value * (self.curr_w / self.base_w))

    @overload
    def scale_tuple(self, coords: tuple[int, int]) -> tuple[int, int]: ...
    @overload
    def scale_tuple(
        self, coords: tuple[int, int, int, int]
    ) -> tuple[int, int, int, int]: ...

    def scale_tuple(
        self, coords: tuple[int, int] | tuple[int, int, int, int]
    ) -> tuple[int, int] | tuple[int, int, int, int]:
        sx = self.curr_w / self.base_w
        sy = self.curr_h / self.base_h

        if len(coords) == 2:
            w, h = coords
            return (int(w * sx), int(h * sy))

        if len(coords) == 4:
            x, y, w, h = coords
            return (int(x * sx), int(y * sy), int(w * sx), int(h * sy))

        raise ValueError("ResolutionScaling only supports 2- or 4-tuples")
