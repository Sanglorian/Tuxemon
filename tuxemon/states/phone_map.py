# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

import pygame
from pygame.surface import Surface
from pygame_menu.locals import ALIGN_CENTER, POSITION_EAST
from pygame_menu.menu import Menu
from pygame_menu.widgets.selection.none import NoneSelection
from pygame_menu.widgets.widget.label import Label

from tuxemon.constants import paths
from tuxemon.database.yaml_utils import load_yaml
from tuxemon.locale.locale import T
from tuxemon.menu.menu import PygameMenuState
from tuxemon.platform.const.graphics import BG_PHONE_MAP
from tuxemon.tools import fix_measure

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.entity.npc import NPC


logger = logging.getLogger(__name__)


@dataclass
class NuPhoneMapConfig:
    map_path: str
    map_data: list[tuple[float, float, str]]
    map_groups: dict[str, list[str]] = field(default_factory=dict)


class Loader:
    _config_nuphone_map: NuPhoneMapConfig | None = None

    @classmethod
    def get_config_nuphone_map(cls, filename: str) -> NuPhoneMapConfig:
        yaml_path = paths.mods_folder / filename
        if not cls._config_nuphone_map:
            raw_data = load_yaml(yaml_path)
            if not isinstance(raw_data, dict):
                raise ValueError("Invalid YAML data")

            map_path = raw_data.get("map_path")
            map_data = raw_data.get("map_data")
            if not map_path or not map_data:
                raise ValueError("Missing required keys in YAML data")

            map_data = [(item[0], item[1], item[2]) for item in map_data]
            map_groups = raw_data.get("map_groups") or {}

            cls._config_nuphone_map = NuPhoneMapConfig(
                map_path=map_path,
                map_data=map_data,
                map_groups=map_groups,
            )
        return cls._config_nuphone_map


data = Loader.get_config_nuphone_map("nu_phone_map.yaml")

# Reverse lookup: map slug -> location key
_slug_to_location: dict[str, str] = {}
for _key, _slugs in data.map_groups.items():
    for _slug in _slugs:
        _slug_to_location[_slug] = _key


def _location_for_slug(slug: str) -> str:
    """Return the location key for a map slug, falling back to the slug itself."""
    return _slug_to_location.get(slug, slug)


class NuPhoneMap(PygameMenuState):
    """
    Shows a world map with a pin for every location in map_data.

    Pins for unvisited locations display as "???"; visited ones show their
    real name in the bottom-right corner when the cursor is on them.
    The player icon marks the player's current location.

    If there are no trackers (locations), then it'll be not possible to consult
    the app. It'll appear a pop up with: "GPS tracker not updating."
    """

    name: ClassVar[str] = "NuPhoneMap"

    def add_menu_items(
        self,
        menu: Menu,
    ) -> None:
        new_image = self._create_image(data.map_path)
        new_image.scale(self.factor, self.factor)
        menu.add.image(image_path=new_image.copy())

        current_location = _location_for_slug(self.client.map_manager.map_slug)
        known = set(self.char.tracker.locations.keys())

        # widget id -> display name (real name or "???")
        self._pin_to_name: dict[int, str] = {}

        for x, y, key in data.map_data:
            is_here = current_location == key
            display_name = T.translate(key) if key in known else "???"

            if is_here:
                player_icon = self._create_image("gfx/ui/menu/player.png")
                player_icon.scale(self.factor, self.factor)
                menu.add.image(player_icon.copy(), float=True).translate(
                    fix_measure(menu._width, x),
                    fix_measure(menu._height, y),
                )

            # Invisible selectable widget at the pin position for cursor nav.
            # NoneSelection suppresses the default arrow so we can draw our
            # own cursor indicator exactly at the pin coordinates in draw().
            pin: Any = menu.add.label(
                title=" ",
                selectable=True,
                float=True,
                font_size=self.font_type.small,
            )
            pin.set_selection_effect(NoneSelection())
            pin.translate(
                fix_measure(menu._width, x),
                fix_measure(menu._height, y),
            )
            self._pin_to_name[pin.get_id()] = display_name

        # Bottom-right name display — updated every frame in draw()
        self._name_label: Label = menu.add.label(
            title="",
            selectable=False,
            float=True,
            font_size=self.font_type.biggest,
        )
        self._name_label.translate(
            fix_measure(menu._width, 0.28),
            fix_measure(menu._height, 0.88),
        )

        menu.set_title(title=T.translate("app_map")).center_content()

    def draw(self, surface: Surface) -> None:
        selected = self.menu.get_selected_widget()
        if selected is not None:
            name = self._pin_to_name.get(selected.get_id(), "")
            self._name_label.set_title(name)
        else:
            self._name_label.set_title("")

        super().draw(surface)

        # Draw cursor dot on top of the menu at the exact pin position
        if selected is not None and selected.get_id() in self._pin_to_name:
            rect = selected.get_rect()
            pygame.draw.circle(surface, (255, 255, 255), rect.center, 3)

    def __init__(
        self, client: BaseClient, character: NPC, **kwargs: Any
    ) -> None:
        self.char = character
        width, height = client.context.resolution

        super().__init__(client=client, height=height, width=width, **kwargs)

        theme = self._setup_theme(BG_PHONE_MAP)
        theme.scrollarea_position = POSITION_EAST
        theme.widget_alignment = ALIGN_CENTER
        theme.title = True
        self._menu_config["theme"] = theme

        self.add_menu_items(self.menu)
        self.reset_theme()
