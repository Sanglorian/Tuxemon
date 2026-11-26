# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from collections.abc import Callable, Generator
from dataclasses import replace
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar

from pygame import SRCALPHA
from pygame.font import Font
from pygame.rect import Rect
from pygame.surface import Surface

from tuxemon.animation import ScheduleType
from tuxemon.constants.asset_loader import fetch_asset
from tuxemon.graphics import ColorLike, load_image, scale_surface
from tuxemon.locale.locale import T
from tuxemon.menu.interface import ExpBar, HpBar, MenuItem
from tuxemon.menu.menu import Menu
from tuxemon.monster.filter import MonsterFilter
from tuxemon.monster.monster import Monster
from tuxemon.monster.renderer import MonsterRenderer
from tuxemon.platform.const.graphics import (
    BG_MONSTERS,
    FONT_SIZE_ARBATA,
    FONT_SIZE_BIGGEST,
    GFX_HP_BAR,
    TRANSPARENT_COLOR,
)
from tuxemon.platform.const.sizes import PARTY_LIMIT
from tuxemon.scaling import DefaultScaling
from tuxemon.session import local_session
from tuxemon.sprite import Sprite
from tuxemon.tools import open_choice_dialog, open_dialog
from tuxemon.ui.graphic_box import GraphicBox
from tuxemon.ui.menu_options import (
    MenuOptions,
    create_choice_options,
    create_yes_no_options,
)
from tuxemon.ui.text import TextArea

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.config import LocaleConfig
    from tuxemon.entity.party import PartyHandler
    from tuxemon.item.item import Item
    from tuxemon.monster.monster import Monster
    from tuxemon.prepare import DisplayContext

LAYER_MONSTER_ICONS = 20
LAYER_STATUS_ICONS = 25
LAYER_PORTRAIT = 30

# A crate, shown in the box of a monster holding an item.
HELD_ITEM_MARKER = "gfx/ui/monster/held_item.png"

# Team menu layout, in nominal pixels on the 256 x 144 screen. Each party
# slot is an icon, a short gap and a box, drawn at nominal size and
# scaled up whole, so every scale is an exact multiple of the design.
SLOT_ICON_SIZE = 24
SLOT_GAP = 4
SLOT_BOX_SIZE = (86, 24)
SLOT_WIDTH = SLOT_ICON_SIZE + SLOT_GAP + SLOT_BOX_SIZE[0]
# (left, top, icon on the right) for each slot: the first monster on the
# left, the other five down the right, their icons alternating sides.
SLOT_LAYOUT = (
    (14, 7, False),
    (140, 7, False),
    (139, 34, True),
    (140, 61, False),
    (139, 88, True),
    (140, 115, False),
)
# Inside a box: name, "LEVEL n" (top of its glyphs) and the HP bar.
BOX_NAME_POS = (4, 0)
BOX_LEVEL_POS = (8, 15)
BOX_HP_RECT = (40, 13, 43, 8)
# Offset of the held-item crate's top right from the box's top right.
BOX_HELD_ITEM_POS = (-3, 0)
# The selected monster's front sprite, and its stats below it.
PORTRAIT_POS = (36, 39)
STATS_ROWS = (112, 119, 126)
# Left edge of the first column of stats.
STATS_LEFT = 24
# Gap from a column's longest label to its values, and from a column's
# widest possible value to the next column's labels.
STATS_LABEL_GAP = 4
STATS_COLUMN_GAP = 4
# Widest value each stat is laid out for, so columns don't move between
# monsters.
STATS_VALUE_TEMPLATE = "999"
# HP shows as current / maximum, or just the maximum when at full HP.
STATS_HP_SEPARATOR = "/"
# Light stripes in a filled box's background, counted up from the bottom
# row inside its border (1 = the bottom row).
BOX_STRIPE_ROWS_FROM_BOTTOM = (4, 2, 1)


class MonsterMenuState(Menu[Monster | None]):
    """
    A class to create monster menu objects.

    The monster menu allows you to view monsters in your party,
    teach them moves, and switch them both in and out of combat.
    """

    background_filename = BG_MONSTERS
    draw_borders = False

    name: ClassVar[str] = "MonsterMenuState"

    def __init__(
        self,
        client: BaseClient,
        monsters: list[Monster],
        monster_filter: MonsterFilter | None = None,
        *,
        on_selection: Callable[[MenuItem[Monster | None]], None] | None = None,
        is_valid_entry: Callable[[Monster | None], bool] | None = None,
        on_selection_change: Callable[[MonsterMenuState], None] | None = None,
        **kwargs: Any,
    ):
        super().__init__(client=client, **kwargs)
        self._external_on_selection = on_selection
        self._external_is_valid_entry = is_valid_entry
        self._external_on_selection_change = on_selection_change
        self.monster_filter = monster_filter or MonsterFilter()
        self.monsters = self.monster_filter.get_filtered_monsters(monsters)

        # make a text area to show messages
        rect = self.client.context.scaling.scale_tuple((20, 80, 80, 100))
        self.text_area = TextArea(
            font=self.font,
            font_color=self.font_color,
            rect=Rect(rect),
            scaling=self.client.context.scaling,
            font_shadow=(96, 96, 96),
        )
        self.sprites.add(self.text_area, layer=100)

        # Set up the border images used for the monster slots
        self.hp_bar = HpBar(self.client.context)
        self.exp_bar = ExpBar(self.client.context)
        self.slot_renderer = MonsterSlotRenderer(
            self.client.context, self.font_color, self.client.config.locale
        )

        self.monster_stats_display = MonsterStatsDisplay(self)
        self.monster_sprite_displays: list[MonsterSpriteDisplay] = []
        self.monster_portrait_display = MonsterPortraitDisplay(self)

        # The cursor sits left of each slot, 1 nominal px above centre.
        scale_int = self.client.context.scaling.scale_int
        arrow = self.cursor_controller.arrow
        arrow.y_offset = (
            scale_int(6)
            + arrow.rect.height // 2
            - scale_int(SLOT_BOX_SIZE[1]) // 2
        )

    def setup_resources(self) -> None:
        # Monster names are set in Arbata.
        self.font_filename = self.client.config.locale.arbata_font_file
        super().setup_resources()
        self.set_font(size=FONT_SIZE_ARBATA)

    def calc_menu_items_rect(self) -> Rect:
        # Slots are placed by SLOT_LAYOUT in screen coordinates.
        return Rect((0, 0), self.client.context.resolution)

    def slot_rect(self, index: int) -> Rect:
        """Where slot ``index`` (icon, gap and box) sits on screen."""
        scale_int = self.client.context.scaling.scale_int
        left, top, _ = SLOT_LAYOUT[index]
        return Rect(
            scale_int(left),
            scale_int(top),
            scale_int(SLOT_WIDTH),
            scale_int(SLOT_BOX_SIZE[1]),
        )

    def arrange_items(self) -> None:
        super().arrange_items()
        for index, item in enumerate(self.menu_items):
            item.rect.topleft = self.slot_rect(index).topleft

    def initialize_items(
        self,
    ) -> Generator[MenuItem[Monster | None], None, None]:
        # position the monster portrait
        try:
            monster = self.monsters[self.selected_index]
            self.monster_portrait_display.update(monster)
        except IndexError:
            self.monster_portrait_display.update(None)

        self.animations.empty()
        self.monster_portrait_display.animate_down()

        # make 6 slots
        for index in range(PARTY_LIMIT):
            rect = self.slot_rect(index)
            surface = Surface(rect.size, SRCALPHA)
            item = MenuItem(surface, None, None, None)
            yield item

        self.refresh_menu_items()

    def on_menu_selection(self, item: MenuItem[Monster | None]) -> None:
        if self._external_on_selection:
            return self._external_on_selection(item)
        return None

    def is_valid_entry(self, monster: Monster | None) -> bool:
        if self._external_is_valid_entry:
            return self._external_is_valid_entry(monster)
        return monster is not None

    def refresh_menu_items(self) -> None:
        """Used to render slots after their 'focus' flags change."""
        MonsterSpriteDisplay.cleanup(self.monster_sprite_displays)

        for index, item in enumerate(self.menu_items):
            self.assign_monster_to_item(index, item)

    def assign_monster_to_item(
        self, index: int, item: MenuItem[Monster | None]
    ) -> None:
        monster = self.monsters[index] if index < len(self.monsters) else None
        item.game_object = monster
        item.enabled = (monster is not None) and self.is_valid_entry(monster)
        item.image.fill(TRANSPARENT_COLOR)
        item.in_focus = (index == self.selected_index) and item.enabled
        icon_right = SLOT_LAYOUT[index][2]
        self.slot_renderer.render_slot(
            item.image, monster, item.in_focus, icon_right
        )

        if monster:
            scale_int = self.client.context.scaling.scale_int
            slot = self.slot_rect(index)
            icon_x = SLOT_WIDTH - SLOT_ICON_SIZE if icon_right else 0
            sprite_display = MonsterSpriteDisplay(self)
            sprite_display.update(
                monster, (slot.left + scale_int(icon_x), slot.top)
            )
            self.monster_sprite_displays.append(sprite_display)

    def on_menu_selection_change(self) -> None:
        if self._external_on_selection_change:
            self._external_on_selection_change(self)

        monster: Monster | None = None
        try:
            monster = self.monsters[self.selected_index]
            self.monster_portrait_display.update(monster)
        except IndexError:
            self.monster_portrait_display.update(None)

        self.monster_stats_display.update(monster)
        self.refresh_menu_items()

    def update(self, dt: float) -> None:
        super().update(dt)
        self.monster_portrait_display.apply_bob()

    def remove_monster_sprite_display(self, monster: Monster) -> None:
        for sprite_display in self.monster_sprite_displays:
            if sprite_display.monster == monster:
                if sprite_display.sprite:
                    self.sprites.remove(sprite_display.sprite)
                self.monster_sprite_displays.remove(sprite_display)
                break


class MonsterMenuHandler:
    """Handles interactions within the monster menu."""

    def __init__(self, client: BaseClient, party: PartyHandler) -> None:
        """Initialize with client and character."""
        self.name = "WorldMenuState"
        self.client = client
        self.party = party
        self.context: dict[str, Any] = {}

    def monster_menu_hook(self, monster_menu: MonsterMenuState) -> None:
        """Handles monster reordering."""
        monster = self.context.get("monster")
        if not monster:
            return

        monster_list = self.party.monsters
        original = monster_menu.get_selected_item()
        if original and original.game_object:
            original_monster = original.game_object
            index = monster_list.index(original_monster)
            monster_list[self.context["old_index"]] = original_monster
            monster_list[index] = self.context["monster"]
            self.context["old_index"] = index

    def select_monster(self, monster: Monster) -> None:
        """Selects a monster for movement."""
        self.context["monster"] = monster
        self.context["old_index"] = self.party.monsters.index(monster)
        self.client.remove_state_by_name("ChoiceState")

    def monster_stats(self, monster: Monster) -> None:
        """Displays monster statistics."""
        self.client.remove_state_by_name("ChoiceState")
        params = {
            "monster": monster,
            "source": self.name,
            "monsters": self.party.monsters,
        }
        self.client.push_state("MonsterInfoState", **params)

    def monster_techs(self, monster: Monster) -> None:
        """Displays monster techniques."""
        self.client.remove_state_by_name("ChoiceState")
        params = {
            "monster": monster,
            "source": self.name,
            "monsters": self.party.monsters,
        }
        self.client.push_state("MonsterMovesState", **params)

    def remove_item_direct(self, monster: Monster) -> None:
        item = monster.held_item
        if item:
            monster.unequip_item()
            self.party.owner.bag.add_item(item)

        self.client.remove_state_by_name("ChoiceState")
        self.monster_menu.refresh_menu_items()

    def open_item_picker(self, monster: Monster) -> None:
        from tuxemon.item.filter import ItemFilter
        from tuxemon.states.item_menu import ItemMenuState

        self.client.remove_state_by_name("ChoiceState")
        items_filtered = ItemFilter(self.party.owner.bag.items)
        items_filtered.add_filter(lambda item: item.behaviors.holdable)
        # the picker skips the validation the item menu does for a used item,
        # so an item this monster fails the conditions for is left out here
        items_filtered.add_filter(
            lambda item: item.validate_monster(local_session, monster)
        )

        self.client.push_state(
            ItemMenuState(
                self.client,
                character=self.party.owner,
                source=self.name,
                item_filter=items_filtered,
                on_selection=lambda menu_item: self._equip_from_picker(
                    monster, menu_item
                ),
            )
        )

    def _equip_from_picker(
        self, monster: Monster, menu_item: MenuItem[Item | None]
    ) -> None:
        item = menu_item.game_object
        if not item:
            return

        monster.equip_item(item)
        self.party.owner.bag.remove_item(item)
        self.client.remove_state_by_name("ItemMenuState")
        self.monster_menu.refresh_menu_items()

    def swap_items(self, mon_a: Monster, mon_b: Monster) -> None:
        """Swaps held items between two monsters."""
        mon_a.swap_items(mon_b)
        self.client.remove_state_by_name("ChoiceState")
        self.monster_menu.refresh_menu_items()

    def open_swap_picker(self, monster: Monster) -> None:
        """Opens a submenu to choose another monster to swap items with."""
        self.client.remove_state_by_name("ChoiceState")

        candidates = [
            m for m in self.party.monsters if m is not monster and m.held_item
        ]

        if not candidates:
            return

        actions = {
            m.name: partial(self.swap_items, monster, m) for m in candidates
        }
        menu = MenuOptions(create_choice_options(actions))
        open_choice_dialog(self.client, menu, escape_key_exits=True)

    def release_monster(self, monster: Monster) -> None:
        """Shows confirmation for releasing a monster."""
        self.client.remove_state_by_name("ChoiceState")
        params = {"name": monster.name.upper()}
        msg = T.format("release_confirmation", params)
        open_dialog(self.client, [msg], dialog_speed="max")

        options = create_yes_no_options(
            yes_action=partial(self.positive_answer, monster),
            no_action=self.negative_answer,
        )

        menu = MenuOptions(options)
        open_choice_dialog(self.client, menu, escape_key_exits=False)

    def positive_answer(self, monster: Monster) -> None:
        """Handles monster release."""
        success = self.party.release_monster(monster)
        if success:
            self.client.remove_state_by_name("ChoiceState")
            self.client.remove_state_by_name("DialogState")
            params = {"name": monster.name.upper()}
            msg = T.format("tuxemon_released", params)
            open_dialog(self.client, [msg], dialog_speed="max")
            self.monster_menu.remove_monster_sprite_display(monster)

            num_monsters = len(self.party.monsters)
            if self.monster_menu.selected_index >= num_monsters:
                self.monster_menu.change_selection(max(0, num_monsters - 1))

            self.monster_menu.refresh_menu_items()
            self.monster_menu.on_menu_selection_change()
        else:
            open_dialog(
                self.client, [T.translate("cant_release")], dialog_speed="max"
            )

    def negative_answer(self) -> None:
        """Handles rejection for releasing a monster."""
        self.client.remove_state_by_name("ChoiceState")
        self.client.remove_state_by_name("DialogState")

    def open_monster_submenu(self, monster_menu: MonsterMenuState) -> None:
        """Opens a submenu for the selected monster."""
        original = monster_menu.get_selected_item()
        if not (original and original.game_object):
            return

        mon = original.game_object

        actions: dict[str, Callable[..., None]] = {
            "info": partial(self.monster_stats, mon),
        }

        if mon.moves.moves:
            actions["tech"] = partial(self.monster_techs, mon)

        if mon.held_item:
            actions["unequip_item"] = partial(self.remove_item_direct, mon)

        holdable_items = [
            item
            for item in self.party.owner.bag.items
            if item.behaviors.holdable
        ]

        if holdable_items:
            actions["equip_item"] = partial(self.open_item_picker, mon)

        other_with_items = [
            m for m in self.party.monsters if m is not mon and m.held_item
        ]

        if other_with_items:
            actions["swap_item"] = partial(self.open_swap_picker, mon)

        if self.party.party_size > 1:
            actions.update(
                {
                    "move": partial(self.select_monster, mon),
                    "sort": lambda: self.open_sort_submenu(monster_menu),
                    "release": partial(self.release_monster, mon),
                }
            )

        options = create_choice_options(actions)
        menu = MenuOptions(options)
        open_choice_dialog(self.client, menu, escape_key_exits=True)

    def handle_selection(
        self,
        menu_item: MenuItem[Monster | None],
        monster_menu: MonsterMenuState,
    ) -> None:
        """Handles selection interaction for monsters."""
        if "monster" in self.context:
            del self.context["monster"]
        else:
            self.open_monster_submenu(monster_menu)

    def sort_monsters(
        self,
        monster_menu: MonsterMenuState,
        key: Callable[[Monster], Any],
        reverse: bool = False,
    ) -> None:
        """Sorts the monsters in the party by a given key."""
        self.party.monsters.sort(key=key, reverse=reverse)
        monster_menu.monsters = self.party.monsters
        monster_menu.refresh_menu_items()
        monster_menu.on_menu_selection_change()

    def open_monster_menu(self) -> None:
        """Pushes the monster menu state."""
        self.monster_menu = self.client.push_state(
            MonsterMenuState(
                self.client,
                self.party.monsters,
                on_selection=lambda item: self.handle_selection(
                    item, self.monster_menu
                ),
                on_selection_change=self.monster_menu_hook,
            )
        )

    def open_sort_submenu(self, monster_menu: MonsterMenuState) -> None:
        """Opens a submenu with sorting options."""
        actions: dict[str, Callable[..., None]] = {
            "level": lambda: self.sort_monsters(
                monster_menu, key=lambda m: m.level
            ),
            "hp": lambda: self.sort_monsters(
                monster_menu, key=lambda m: m.hp_ratio, reverse=True
            ),
            "name": lambda: self.sort_monsters(
                monster_menu, key=lambda m: m.name.lower()
            ),
            "id": lambda: self.sort_monsters(
                monster_menu, key=lambda m: m.txmn_id
            ),
        }
        options = create_choice_options(actions)
        menu = MenuOptions(options)
        open_choice_dialog(self.client, menu, escape_key_exits=True)


class MonsterStatsDisplay:
    """The selected monster's stats, in two columns of three, below it."""

    def __init__(self, menu_state: MonsterMenuState) -> None:
        self.menu_state = menu_state
        self.sprite = Sprite()
        self.sprite.image = Surface((1, 1), SRCALPHA)
        self.sprite.rect = Rect(0, 0, 1, 1)
        self.menu_state.sprites.add(self.sprite, layer=LAYER_MONSTER_ICONS)

    def update(self, monster: Monster | None) -> None:
        scale = self.menu_state.client.context.scaling.scale_int(1)
        width, height = self.menu_state.client.context.resolution
        nominal = Surface((width // scale, height // scale), SRCALPHA)
        if monster:
            font = self.menu_state.slot_renderer.minimal_font
            hp = str(monster.hp)
            if monster.current_hp != monster.hp:
                hp = f"{monster.current_hp}{STATS_HP_SEPARATOR}{hp}"
            hp_template = STATS_HP_SEPARATOR.join([STATS_VALUE_TEMPLATE] * 2)
            columns = (
                (
                    ("short_hp", hp),
                    ("melee", str(monster.melee)),
                    ("ranged", str(monster.ranged)),
                ),
                (
                    ("armour", str(monster.armour)),
                    ("dodge", str(monster.dodge)),
                    ("speed", str(monster.speed)),
                ),
            )
            templates = (hp_template, STATS_VALUE_TEMPLATE)
            label_x = STATS_LEFT
            for stats, template in zip(columns, templates):
                labels = [T.translate(key).upper() for key, _ in stats]
                value_x = (
                    label_x
                    + STATS_LABEL_GAP
                    + max(ink_width(font, label) for label in labels)
                )
                for row_top, label, (_, value) in zip(
                    STATS_ROWS, labels, stats
                ):
                    blit_ink(nominal, font, label, left=label_x, top=row_top)
                    blit_ink(nominal, font, value, left=value_x, top=row_top)
                label_x = value_x + ink_width(font, template)
                label_x += STATS_COLUMN_GAP
        self.sprite.image = scale_surface(nominal, scale)
        self.sprite.rect = self.sprite.image.get_rect()


class MonsterSpriteDisplay:
    """
    Manages the sprite used to visually represent a monster inside the party menu.

    Each instance tracks a single monster and its corresponding sprite. The class
    is responsible for creating the sprite, positioning it relative to the slot
    rectangle, updating it when the selected monster changes, and removing it
    cleanly from the menu state's sprite group when no longer needed.
    """

    def __init__(self, menu_state: MonsterMenuState) -> None:
        self.menu_state = menu_state
        self.scaling = self.menu_state.client.context.scaling
        self.resolution = self.menu_state.client.context.resolution
        self.sprite: Sprite | None = None
        self.status_icons: Sprite | None = None
        self.monster: Monster | None = None

    @staticmethod
    def cleanup(displays: list[MonsterSpriteDisplay]) -> None:
        for display in displays:
            display.remove_sprite()
        displays.clear()

    def update(
        self, monster: Monster | None, topleft: tuple[int, int]
    ) -> None:
        self.monster = monster

        if monster:
            if self.sprite:
                self.menu_state.sprites.remove(self.sprite)

            # The menu icon at its native 24 x 24 nominal size.
            renderer = MonsterRenderer(
                monster,
                scale=self.menu_state.client.context.scale,
                frame_duration=0.25,
            )
            self.sprite = renderer.get_sprite("menu")
            self.menu_state.sprites.add(self.sprite, layer=LAYER_MONSTER_ICONS)
            self.sprite.rect.topleft = topleft
            self._update_status_icons(monster, topleft)

        else:
            self.remove_sprite()

    def _update_status_icons(
        self, monster: Monster, topleft: tuple[int, int]
    ) -> None:
        """Show the monster's status icons (9 x 9) on the icon's bottom
        right corner, right to left."""
        if self.status_icons is not None:
            self.menu_state.sprites.remove(self.status_icons)
            self.status_icons = None
        icons = [
            load_image(status.icon)
            for status in monster.status.get_statuses()
            if status.icon
        ]
        if not icons:
            return
        width = sum(icon.get_width() for icon in icons) + len(icons) - 1
        height = max(icon.get_height() for icon in icons)
        nominal = Surface((width, height), SRCALPHA)
        x = width
        for icon in icons:
            x -= icon.get_width()
            nominal.blit(icon, (x, height - icon.get_height()))
            x -= 1
        marker = Sprite()
        marker.image = scale_surface(nominal, self.scaling.scale_int(1))
        marker.rect = marker.image.get_rect(
            bottomright=(
                topleft[0] + self.scaling.scale_int(SLOT_ICON_SIZE),
                topleft[1] + self.scaling.scale_int(SLOT_ICON_SIZE),
            )
        )
        self.menu_state.sprites.add(marker, layer=LAYER_STATUS_ICONS)
        self.status_icons = marker

    def remove_sprite(self) -> None:
        if self.sprite is not None:
            self.menu_state.sprites.remove(self.sprite)
            self.sprite = None
        if self.status_icons is not None:
            self.menu_state.sprites.remove(self.status_icons)
            self.status_icons = None
        self.monster = None


class MonsterPortraitDisplay:
    def __init__(self, menu_state: MonsterMenuState) -> None:
        self.menu_state = menu_state
        self.scaling = self.menu_state.client.context.scaling
        self.resolution = self.menu_state.client.context.resolution
        self.portrait = Sprite()
        self.portrait.rect = Rect(0, 0, 0, 0)
        self.menu_state.sprites.add(self.portrait, layer=LAYER_PORTRAIT)
        # The portrait bobs up and down. The animation eases a fractional
        # offset in nominal pixels; the portrait moves in whole ones.
        self.bob = PortraitBob()

    def update(self, monster: Monster | None) -> None:
        image = None
        if monster is not None:
            try:
                scale = self.menu_state.client.context.scale
                renderer = MonsterRenderer(monster, scale=scale)
                sprite = renderer.get_sprite("front")
                image = sprite.image
            except Exception:
                pass

        image = image or Surface((1, 1), SRCALPHA)

        self.portrait.image = image
        self.portrait.rect = image.get_rect(
            topleft=self.scaling.scale_tuple(PORTRAIT_POS)
        )

    def animate_down(self) -> None:
        ani = self.menu_state.animate(
            self.bob,
            y=-5,
            duration=1,
            transition="in_out_quad",
            relative=True,
        )
        ani.schedule(self.animate_up, ScheduleType.ON_FINISH)

    def animate_up(self) -> None:
        ani = self.menu_state.animate(
            self.bob,
            y=5,
            duration=1,
            transition="in_out_quad",
            relative=True,
        )
        ani.schedule(self.animate_down, ScheduleType.ON_FINISH)

    def apply_bob(self) -> None:
        """Move the portrait to its bob offset, in whole nominal pixels."""
        top = self.scaling.scale_int(PORTRAIT_POS[1] + round(self.bob.y))
        self.portrait.rect.top = top


class PortraitBob:
    """The portrait's bob offset, in (fractional) nominal pixels."""

    def __init__(self) -> None:
        self.y = 0.0


class MonsterSlotBorder:
    def __init__(self, root: str = "gfx/ui/monster/"):
        self.border_types = ["empty", "filled", "active"]
        self.borders: dict[str, GraphicBox] = {}
        # (fill, stripe) colours of each box's background, if it has one.
        self.backgrounds: dict[str, tuple[ColorLike, ColorLike] | None] = {}
        self.load_borders(root)

    def load_borders(self, root: str) -> None:
        for border_type in self.border_types:
            # Unscaled: slots are drawn at nominal size, then scaled up.
            filename = root + border_type + "_monster_slot_border.png"
            border = load_image(filename)

            # The background's top pixel is its fill colour and its bottom
            # pixel its stripe colour; see draw_background.
            filename = root + border_type + "_monster_slot_bg.png"
            background = load_image(filename)
            fill = background.get_at((0, 0))
            stripe = background.get_at((0, background.get_height() - 1))
            self.backgrounds[border_type] = (fill, stripe) if fill.a else None

            self.borders[border_type] = GraphicBox(Rect(0, 0, 3, 3), border)

    def _type(self, selected: bool, filled: bool) -> str:
        if selected:
            return "active"
        return "filled" if filled else "empty"

    def get_border(self, selected: bool, filled: bool) -> GraphicBox:
        return self.borders[self._type(selected, filled)]

    def draw_background(
        self, surface: Surface, inner: Rect, selected: bool, filled: bool
    ) -> None:
        """Fill a box's inside, with light stripes near its bottom."""
        colours = self.backgrounds[self._type(selected, filled)]
        if colours is None:
            return
        fill, stripe = colours
        surface.fill(fill, inner)
        for row in BOX_STRIPE_ROWS_FROM_BOTTOM:
            surface.fill(
                stripe, (inner.left, inner.bottom - row, inner.width, 1)
            )


def ink_width(font: Font, text: str) -> int:
    """Width of the glyphs (not the font's spacing) of ``text``."""
    return font.render(text, False, (0, 0, 0)).get_bounding_rect().width


def blit_ink(
    surface: Surface,
    font: Font,
    text: str,
    top: int,
    left: int | None = None,
    right: int | None = None,
) -> None:
    """Draw text so its glyphs (not the font's empty rows) start at ``top``,
    and start at ``left`` or end at ``right``."""
    image = font.render(text, False, (0, 0, 0))
    ink = image.get_bounding_rect()
    x = left - ink.left if left is not None else (right or 0) - ink.right
    surface.blit(image, (x, top - ink.top))


class MonsterSlotRenderer:
    """
    Draws a party slot's box.

    Everything is drawn at nominal size with the pixel fonts and unscaled
    assets, then scaled up whole, so it sits exactly on the pixel grid.
    """

    def __init__(
        self,
        context: DisplayContext,
        font_color: ColorLike,
        locale: LocaleConfig,
    ):
        self.context = context
        self.scaling = context.scaling
        self.font_color = font_color
        self.slot_border = MonsterSlotBorder()
        self.name_font = Font(
            fetch_asset("font", locale.arbata_font_file), FONT_SIZE_ARBATA
        )
        self.minimal_font = Font(
            fetch_asset("font", locale.minimal_font_file), FONT_SIZE_BIGGEST
        )
        # An HP bar drawn at nominal size, from the unscaled border image.
        self.hp_bar = HpBar(
            replace(context, scaling=DefaultScaling(1), scale=1)
        )
        self.hp_bar.border = GraphicBox(
            Rect(0, 0, 1, 1), load_image(GFX_HP_BAR)
        )

    def render_slot(
        self,
        surface: Surface,
        monster: Monster | None,
        in_focus: bool,
        icon_right: bool,
    ) -> None:
        nominal = Surface((SLOT_WIDTH, SLOT_BOX_SIZE[1]), SRCALPHA)
        box = Rect((0, 0), SLOT_BOX_SIZE)
        if not icon_right:
            box.left = SLOT_ICON_SIZE + SLOT_GAP

        filled = monster is not None
        border = self.slot_border.get_border(in_focus, filled)
        border.rect = box
        self.slot_border.draw_background(
            nominal, border.calc_inner_rect(box), in_focus, filled
        )
        border.draw(nominal, box)

        if monster:
            self._draw_box_contents(nominal, box, monster)

        surface.fill(TRANSPARENT_COLOR)
        surface.blit(scale_surface(nominal, self.scaling.scale_int(1)), (0, 0))

    def _draw_box_contents(
        self, surface: Surface, box: Rect, monster: Monster
    ) -> None:
        name = " ".join(filter(None, (monster.name, monster.gender_symbol)))
        surface.blit(
            self.name_font.render(name, False, self.font_color),
            box.move(BOX_NAME_POS).topleft,
        )

        blit_ink(
            surface,
            self.minimal_font,
            f"Lv {monster.level}",
            left=box.left + BOX_LEVEL_POS[0],
            top=box.top + BOX_LEVEL_POS[1],
        )

        self.hp_bar.value = monster.hp_ratio
        self.hp_bar.draw(surface, Rect(BOX_HP_RECT).move(box.topleft))

        # The held-item crate in the box's top right corner.
        if monster.held_item:
            crate = load_image(HELD_ITEM_MARKER)
            corner = box.move(BOX_HELD_ITEM_POS).topright
            surface.blit(crate, crate.get_rect(topright=corner))
