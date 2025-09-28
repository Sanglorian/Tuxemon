# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import yaml

from tuxemon.constants.paths import mods_folder
from tuxemon.prepare import KENNEL

logger = logging.getLogger(__name__)


class RoutingPolicyRegistry:
    _policies: dict[str, dict[str, Any]] = {}

    @classmethod
    def load_from_file(cls, path: str) -> None:
        yaml_path = mods_folder / path
        with yaml_path.open() as f:
            raw = yaml.safe_load(f)
        cls._policies = raw

    @classmethod
    def get(cls, name: str) -> RoutingPolicy:
        if name not in cls._policies:
            raise KeyError(f"Routing policy '{name}' not found.")
        return RoutingPolicy(name)

    @classmethod
    def get_raw(cls, name: str) -> dict[str, Any]:
        return cls._policies[name]

    @classmethod
    def all(cls) -> dict[str, dict[str, Any]]:
        return cls._policies.copy()


class RoutingPolicy:
    """
    Controls routing behavior for monster addition.
    Loaded by name from RoutingPolicyRegistry.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._data = RoutingPolicyRegistry.get_raw(name)

    @property
    def force_to_box(self) -> bool:
        return bool(self._data.get("force_to_box", False))

    @property
    def kennel_override(self) -> str | None:
        return self._data.get("kennel_override")

    def should_force_to_box(self) -> bool:
        return self.force_to_box

    def get_kennel(self) -> str:
        return self.kennel_override or KENNEL

    def to_dict(self) -> Mapping[str, Any]:
        return {"routing_policy": self.name}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RoutingPolicy:
        name = data.get("routing_policy")
        if name is None:
            raise ValueError("Missing 'routing_policy' in saved data.")

        if name not in RoutingPolicyRegistry.all():
            raise ValueError(f"Routing policy '{name}' not found in registry.")

        return cls(name=name)
