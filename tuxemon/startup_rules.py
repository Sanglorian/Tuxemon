# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import importlib
import importlib.util
import sys
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from tuxemon.constants.paths import ROOT_DIR
from tuxemon.database.runtime import db

if TYPE_CHECKING:
    from tuxemon.client import LocalPygameClient
    from tuxemon.config import TuxemonConfig


class StartupRule(ABC):
    name: ClassVar[str]

    @abstractmethod
    def should_apply(self) -> bool: ...

    @abstractmethod
    def apply(self) -> None: ...


def _import_module(module_name: str) -> Any:
    """Import a module by dotted name, with file-based fallback for frozen builds."""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        # In a frozen build, modules under mods/ aren't on sys.path.
        # Compute the file path from ROOT_DIR and load directly.
        parts = module_name.split(".")
        candidate = ROOT_DIR.joinpath(*parts).with_suffix(".py")
        if candidate.exists():
            spec = importlib.util.spec_from_file_location(module_name, candidate)
            if spec is not None and spec.loader is not None:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                return module
        raise


def load_mod_startup_rules(
    client: LocalPygameClient,
    config: TuxemonConfig,
    load_slot: int | None = None,
) -> list[Any]:
    rules = []

    for mod_name in config.mods:
        meta = db.mod_metadata.get_mod_metadata(mod_name)
        rule_paths = meta.startup_rules

        for path in rule_paths:
            module_name, class_name = path.rsplit(".", 1)
            module = _import_module(module_name)
            cls = getattr(module, class_name)
            rule = cls(client=client, config=config, load_slot=load_slot)
            rules.append(rule)

    return rules
