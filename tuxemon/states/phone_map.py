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
from tuxemon.platform.const import buttons
from tuxemon.platform.const.graphics import BG_PHONE_MAP
from tuxemon.platform.events import PlayerInput

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.entity.npc import NPC


logger = logging.getLogger(__name__)

# Nominal screen dimensions the pixel coordinates are authored against.
_NOMINAL_W = 256
_NOMINAL_H = 144

# The menu title bar shifts float widget y positions down; compensate here.
_TITLE_OFFSET_Y = 10

# Spatial navigation table: key -> direction -> destination key (None = no move)
_NAV: dict[str, dict[str, str | None]] = {
    "leather_town": {"down": "citypark",    "left": "routed",      "right": "route3",     "up": "route3"},
    "cotton_town":  {"down": "route1",      "left": "route1",      "right": "route2",     "up": "route2"},
    "paper_town":   {"down": "routec",      "left": "routec",      "right": "route1",     "up": "route1"},
    "candy_town":   {"down": "routec",      "left": "route6",      "right": "routec",     "up": "route6"},
    "timber_town":  {"down": "tunnel",      "left": "tunnel",      "right": "routee",     "up": "route5"},
    "flower_city":  {"down": "routed",      "left": "route5",      "right": "route4",     "up": "mansion"},
    "routec":       {"down": "dragonscave", "left": None,          "right": "paper_town", "up": "paper_town"},
    "route1":       {"down": "paper_town",  "left": "paper_town",  "right": "cotton_town","up": "cotton_town"},
    "dryadsgrove":  {"down": "cotton_town", "left": None,          "right": "cotton_town","up": "leather_town"},
    "route2":       {"down": "cotton_town", "left": "cotton_town", "right": "citypark",   "up": "citypark"},
    "citypark":     {"down": "route2",      "left": "leather_town","right": None,         "up": "leather_town"},
    "mansion":      {"down": "flower_city", "left": "flower_city", "right": "flower_city","up": None},
    "route3":       {"down": "leather_town","left": "route4",      "right": None,         "up": "route4"},
    "route4":       {"down": None,          "left": "flower_city", "right": "route3",     "up": "flower_city"},
    "route5":       {"down": "timber_town", "left": "timber_town", "right": "leather_town","up": "leather_town"},
    "tunnel":       {"down": "route6",      "left": "timber_town", "right": "route6",     "up": "timber_town"},
    "route6":       {"down": "candy_town",  "left": "tunnel",      "right": "candy_town", "up": "tunnel"},
    "routee":       {"down": "tunnel",      "left": "tunnel",      "right": None,         "up": "timber_town"},
    "dragonscave":  {"down": None,          "left": "routec",      "right": "routec",     "up": "routec"},
    "routed":       {"down": "leather_town","left": "flower_city", "right": "leather_town","up": "flower_city"},
}

# Core locations are always navigable; non-core require a tracker visit.
_CORE: frozenset[str] = frozenset({
    "leather_town", "cotton_town", "paper_town",
    "candy_town",   "timber_town", "flower_city",
    "route1", "route2", "route3", "route4", "route5", "route6",
    "tunnel", "citypark",
})

_DIR_BUTTON = {
    buttons.UP:    "up",
    buttons.DOWN:  "down",
    buttons.LEFT:  "left",
    buttons.RIGHT: "right",
}


@dataclass
class NuPhoneMapConfig:
    map_path: str
    map_data: list[tuple[int, int, str]]
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

            map_data = [(int(item[0]), int(item[1]), item[2]) for item in map_data]
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

    Coordinates in map_data are nominal pixel positions on a 256×144 grid.
    Pins for unvisited locations display as "???"; visited ones show their
    real name in the bottom-right corner when the cursor is on them.
    The player icon marks the player's current location.
    Directional navigation follows the spatial table in _NAV.

    If there are no trackers (locations), then it'll be not possible to consult
    the app. It'll appear a pop up with: "GPS tracker not updating."
    """

    name: ClassVar[str] = "NuPhoneMap"

    def _tx(self, nominal_x: int, menu_width: int) -> int:
        """Translate x: offset from widget's natural centre to nominal pixel."""
        return nominal_x * self.factor - menu_width // 2

    def _ty(self, nominal_y: int) -> int:
        """Translate y: nominal pixel scaled to actual resolution."""
        return (nominal_y - _TITLE_OFFSET_Y) * self.factor

    def add_menu_items(
        self,
        menu: Menu,
    ) -> None:
        new_image = self._create_image(data.map_path)
        new_image.scale(self.factor, self.factor)
        menu.add.image(image_path=new_image.copy())

        current_location = _location_for_slug(self.client.map_manager.map_slug)
        known = set(self.char.tracker.locations.keys())

        # widget id -> display name; key <-> widget (for navigation)
        self._pin_to_name: dict[int, str] = {}
        self._key_to_widget: dict[str, Any] = {}
        self._widget_id_to_key: dict[int, str] = {}
        self._selectable_keys: set[str] = set()

        for x, y, key in data.map_data:
            is_here = current_location == key
            is_selectable = key in _CORE or key in known
            display_name = T.translate(key) if key in known else "???"

            if is_here:
                player_icon = self._create_image("gfx/ui/menu/map_player.png")
                player_icon.scale(self.factor, self.factor)
                menu.add.image(player_icon.copy(), float=True).translate(
                    self._tx(x, menu._width),
                    self._ty(y),
                )

            # Invisible selectable widget at the pin position for cursor nav.
            # NoneSelection suppresses the default arrow; we draw our own
            # cursor in draw() at the exact pin coordinates.
            pin: Any = menu.add.label(
                title=" ",
                selectable=is_selectable,
                float=True,
                font_size=self.font_type.small,
            )
            pin.set_selection_effect(NoneSelection())
            pin.translate(
                self._tx(x, menu._width),
                self._ty(y),
            )
            self._pin_to_name[pin.get_id()] = display_name
            self._key_to_widget[key] = pin
            self._widget_id_to_key[pin.get_id()] = key
            if is_selectable:
                self._selectable_keys.add(key)

        # Name display at nominal (200, 119) — updated every frame in draw()
        self._name_label: Label = menu.add.label(
            title="",
            selectable=False,
            float=True,
            font_size=self.font_type.biggest,
        )
        self._name_label.translate(
            self._tx(200, menu._width),
            self._ty(119),
        )

        # Preload sniping cursor (drawn manually in draw() at exact pin pos)
        cursor_img = self._create_image("gfx/ui/icons/status/icon_sniping.png")
        cursor_img.scale(self.factor, self.factor)
        self._cursor_surface = cursor_img.get_surface()

        menu.set_title(title=T.translate("app_map")).center_content()

        # Place cursor on the player's current location if it's selectable,
        # otherwise fall back to the first selectable core pin.
        start = self._key_to_widget.get(current_location)
        if start is None or current_location not in self._selectable_keys:
            start = next(
                (self._key_to_widget[k] for k in self._selectable_keys
                 if k in self._key_to_widget),
                None,
            )
        if start is not None:
            start.select(update_menu=True)

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        if not event.pressed:
            return super().process_event(event)

        direction = _DIR_BUTTON.get(event.button)
        if direction is None:
            return super().process_event(event)

        selected = self.menu.get_selected_widget()
        if selected is None:
            return super().process_event(event)

        current_key = self._widget_id_to_key.get(selected.get_id())
        if current_key is None:
            return super().process_event(event)

        nav = _NAV.get(current_key, {})
        target_key = nav.get(direction)
        if target_key is None:
            return None  # consume event, no move

        if target_key not in self._selectable_keys:
            return None  # non-core unvisited — block movement

        target = self._key_to_widget.get(target_key)
        if target is not None:
            target.select(update_menu=True)
        return None  # consumed

    def draw(self, surface: Surface) -> None:
        selected = self.menu.get_selected_widget()
        if selected is not None:
            name = self._pin_to_name.get(selected.get_id(), "")
            self._name_label.set_title(name)
        else:
            self._name_label.set_title("")

        super().draw(surface)

        # Blit sniping icon centred on the selected pin
        if selected is not None and selected.get_id() in self._pin_to_name:
            rect = selected.get_rect()
            cw = self._cursor_surface.get_width()
            ch = self._cursor_surface.get_height()
            surface.blit(
                self._cursor_surface,
                (rect.centerx - cw // 2, rect.centery - ch // 2),
            )

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
