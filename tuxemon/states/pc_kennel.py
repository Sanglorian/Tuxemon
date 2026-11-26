# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import replace
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

from pygame import SRCALPHA
from pygame.font import Font
from pygame.rect import Rect
from pygame.surface import Surface
from pygame_menu.menu import Menu

from tuxemon.constants.asset_loader import fetch_asset
from tuxemon.graphics import load_image, scale_surface
from tuxemon.locale.locale import T
from tuxemon.menu.interface import HpBar, MenuItem
from tuxemon.menu.menu import PygameMenuState
from tuxemon.menu.transitions import SlideRight
from tuxemon.monster.renderer import MonsterRenderer
from tuxemon.platform.const import buttons, intentions
from tuxemon.platform.const.graphics import (
    BG_PC_KENNEL,
    FONT_SIZE_ARBATA,
    FONT_SIZE_BIGGEST,
    GFX_HP_BAR,
)
from tuxemon.platform.const.sizes import MAX_KENNEL, PARTY_LIMIT
from tuxemon.scaling import DefaultScaling
from tuxemon.state.state import State
from tuxemon.states.monster_menu import MonsterMenuState
from tuxemon.tools import open_choice_dialog, open_dialog
from tuxemon.ui.graphic_box import GraphicBox
from tuxemon.ui.menu_options import (
    MenuOptions,
    create_choice_options,
    create_yes_no_options,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.entity.npc import NPC
    from tuxemon.monster.monster import Monster
    from tuxemon.platform.events import PlayerInput


MenuGameObj = Callable[[], object]


MAX_BOX = MAX_KENNEL

# Monster Take layout, in nominal pixels on the 256 x 144 screen: a grid of
# menu icons on the left, the selected monster's details on the right.
KENNEL_GRID_COLUMNS = 6
KENNEL_ICON_SIZE = 24
KENNEL_GRID_RECT = (4, 6, 168, 132)
# First icon's offset inside the grid frame, and the distance between icons.
KENNEL_GRID_OFFSET = (6, 6)
KENNEL_GRID_PITCH = (26, 24)
KENNEL_PANEL_RECT = (176, 6, 76, 132)
KENNEL_PANEL_PADDING = 7
KENNEL_HP_BAR_HEIGHT = 8
# Height of Minimal3x5's glyphs.
KENNEL_MINIMAL_HEIGHT = 5
KENNEL_TEXT_COLOR = (0, 0, 0)
# The kennel's count shows as monsters / capacity.
KENNEL_COUNT_SEPARATOR = "/"
# Arbata's capitals start 4 px into its line box.
ARBATA_CAP_TOP = 4
GFX_KENNEL_SELECTION_BORDER = "gfx/ui/monster/active_monster_slot_border.png"
GFX_KENNEL_SELECTION_BG = "gfx/ui/monster/active_monster_slot_bg.png"
# Holding a direction repeats it after a delay, in seconds.
KENNEL_REPEAT_DELAY = 0.5
KENNEL_REPEAT_INTERVAL = 0.08


class MonsterActionHandler:
    def __init__(
        self,
        client: BaseClient,
        char: NPC,
        box_name: str,
        source_state: str,
    ) -> None:
        self.client = client
        self.char = char
        self.box_name = box_name
        self.source_state = source_state
        self.monster_boxes = char.monster_boxes

    def pick(self, monster: Monster) -> None:
        self._clear_states("ChoiceState", "MonsterTakeState")
        self.char.party.transfer_monster_to_party(monster)
        open_dialog(
            self.client,
            [T.format("menu_storage_take_monster", {"name": monster.name})],
            dialog_speed="max",
        )

    def move(self, monster: Monster, box_ids: list[str]) -> None:
        if len(box_ids) == 1:
            self.move_monster(monster, box_ids[0], box_ids)
        else:
            actions = {
                box: partial(self.move_monster, monster, box, box_ids)
                for box in box_ids
            }
            options = create_choice_options(actions)
            open_choice_dialog(
                self.client,
                menu=MenuOptions(options),
                escape_key_exits=True,
            )

    def release(self, monster: Monster) -> None:
        options = create_yes_no_options(
            yes_action=partial(self.output, monster),
            no_action=partial(self.output, None),
        )

        open_choice_dialog(
            self.client,
            menu=MenuOptions(options),
            escape_key_exits=True,
        )

    def move_monster(
        self, monster: Monster, box: str, box_ids: list[str]
    ) -> None:
        self._clear_states("ChoiceState")
        if len(box_ids) >= 2:
            self._clear_states("MonsterTakeState")
        self.monster_boxes.move_monster(self.box_name, box, monster)

    def output(self, monster: Monster | None) -> None:
        self._clear_states("ChoiceState", "MonsterTakeState")
        if monster is not None:
            self.monster_boxes.remove_from_box(
                "monster", self.box_name, monster
            )
            open_dialog(
                self.client,
                [T.format("tuxemon_released", {"name": monster.name})],
                dialog_speed="max",
            )

    def info(self, mon: Monster) -> None:
        self._clear_states("ChoiceState")
        self.client.state_manager.push_state(
            "MonsterInfoState",
            **{
                "monster": mon,
                "source": self.source_state,
                "monsters": self.monster_boxes.get_monsters(self.box_name),
            },
        )

    def tech(self, mon: Monster) -> None:
        self._clear_states("ChoiceState")
        self.client.state_manager.push_state(
            "MonsterMovesState",
            **{
                "monster": mon,
                "source": self.source_state,
                "monsters": self.monster_boxes.get_monsters(self.box_name),
            },
        )

    def description_dialog(self, mon: Monster) -> None:
        actions = {
            "info": partial(self.info, mon),
            "tech": partial(self.tech, mon),
        }

        options = create_choice_options(actions)

        open_choice_dialog(
            self.client,
            menu=MenuOptions(options),
            escape_key_exits=True,
        )

    def swap(self, box_monster: Monster, party_monster: Monster) -> None:
        self._clear_states("ChoiceState", "MonsterTakeState")

        swapped_out = self.monster_boxes.swap_with_external_monster_by_iid(
            box_monster.instance_id, party_monster
        )

        if self.char.party.replace_monster(party_monster, swapped_out):
            logger.info(
                f"{party_monster.name} swapped with {swapped_out.name}"
            )
        else:
            logger.warning(f"Failed to swap {swapped_out.name}")

        open_dialog(
            self.client,
            [
                T.format(
                    "menu_storage_swap_monster",
                    {
                        "from": party_monster.name,
                        "to": box_monster.name,
                    },
                )
            ],
            dialog_speed="max",
        )

    def _clear_states(self, *state_names: str) -> None:
        for name in state_names:
            self.client.state_manager.remove_state_by_name(name)


class MonsterTakeState(State):
    """Menu for the Monster Take state.

    Shows all tuxemon currently in a storage kennel as a grid of icons, with
    the selected one's details alongside. Selecting one opens its options
    (take it into the party, move it, release it, or see its info and
    techniques).

    Everything is drawn at nominal size with the pixel fonts and unscaled
    assets, then scaled up whole, so it sits exactly on the pixel grid.
    """

    name: ClassVar[str] = "MonsterTakeState"

    def __init__(
        self,
        client: BaseClient,
        box_name: str,
        character: NPC,
        swap_target: Monster | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(client, **kwargs)
        self.box_name = box_name
        self.char = character
        self.monster_boxes = self.char.monster_boxes
        self.swap_target = swap_target
        self.handler = MonsterActionHandler(
            self.client, self.char, self.box_name, self.name
        )
        self.selected_index = 0
        self._repeat_last = 0.0

        context = self.client.context
        locale = self.client.config.locale
        self.name_font = Font(
            fetch_asset("font", locale.arbata_font_file), FONT_SIZE_ARBATA
        )
        self.minimal_font = Font(
            fetch_asset("font", locale.minimal_font_file), FONT_SIZE_BIGGEST
        )
        self.background = load_image(BG_PC_KENNEL)
        border = load_image(self.client.config.menu_border)
        self.frame = GraphicBox(Rect(0, 0, 1, 1), border)
        self.frame_fill = border.get_at(
            (border.get_width() // 2, border.get_height() // 2)
        )
        selection = load_image(GFX_KENNEL_SELECTION_BORDER)
        self.selection = GraphicBox(Rect(0, 0, 1, 1), selection)
        self.selection_fill = load_image(GFX_KENNEL_SELECTION_BG).get_at(
            (0, 0)
        )
        # An HP bar drawn at nominal size, from the unscaled border image.
        self.hp_bar = HpBar(
            replace(context, scaling=DefaultScaling(1), scale=1)
        )
        self.hp_bar.border = GraphicBox(
            Rect(0, 0, 1, 1), load_image(GFX_HP_BAR)
        )
        self.select_sound = self.client.sound_manager.load_sound(
            self.client.config.menu_sound
        )

        self.box: list[Monster] = []
        self.icons: dict[Monster, Surface] = {}
        self.fronts: dict[Monster, Surface] = {}
        self.image = Surface((1, 1), SRCALPHA)
        self.refresh()

    def refresh(self) -> None:
        """Re-read the kennel (monsters may have left it) and redraw."""
        self.box = sorted(
            self.monster_boxes.get_monsters(self.box_name),
            key=lambda x: x.slug,
        )
        for monster in self.box:
            if monster not in self.icons:
                renderer = MonsterRenderer(monster, scale=1)
                self.icons[monster] = renderer.get_sprite("menu").image
                self.fronts[monster] = renderer.get_sprite("front").image
        last = max(0, len(self.box) - 1)
        self.selected_index = min(self.selected_index, last)
        self.redraw()

    def resume(self) -> None:
        super().resume()
        self.refresh()

    def update(self, dt: float) -> None:
        super().update(dt)
        if not self.box:
            self.client.state_manager.pop_state(self)

    def draw(self, surface: Surface) -> None:
        surface.blit(self.image, (0, 0))

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        if event.button in (buttons.B, buttons.BACK, intentions.MENU_CANCEL):
            if event.pressed:
                self.client.state_manager.pop_state(self)
            return None

        if event.button in (buttons.A, intentions.SELECT):
            if event.pressed and self.box:
                self.select_sound.play()
                monster = self.box[self.selected_index]
                self.kennel_options(monster.instance_id.hex, self.handler)
            return None

        moves = {
            buttons.LEFT: -1,
            buttons.RIGHT: 1,
            buttons.UP: -KENNEL_GRID_COLUMNS,
            buttons.DOWN: KENNEL_GRID_COLUMNS,
        }
        if event.button in moves:
            if event.pressed or self._repeat_due(event):
                self.move_selection(moves[event.button])
            return None

        return event

    def _repeat_due(self, event: PlayerInput) -> bool:
        """Whether a held direction should move again."""
        if not event.is_held(KENNEL_REPEAT_DELAY):
            return False
        if self.current_time - self._repeat_last < KENNEL_REPEAT_INTERVAL:
            return False
        self._repeat_last = self.current_time
        return True

    def move_selection(self, step: int) -> None:
        index = self.selected_index + step
        if not self.box or index < 0:
            return
        if index >= len(self.box):
            # Moving down onto a short last row lands on its last monster.
            if step != KENNEL_GRID_COLUMNS:
                return
            index = len(self.box) - 1
            if index // KENNEL_GRID_COLUMNS == (
                self.selected_index // KENNEL_GRID_COLUMNS
            ):
                return
        self.selected_index = index
        self.redraw()

    def redraw(self) -> None:
        nominal = self.background.copy()
        self._draw_grid(nominal)
        self._draw_details(nominal)
        self.image = scale_surface(nominal, self.scale_int(1))

    def _draw_frame(self, surface: Surface, rect: Rect) -> None:
        surface.fill(self.frame_fill, rect.inflate(-2, -2))
        self.frame.draw(surface, rect)

    def _draw_grid(self, surface: Surface) -> None:
        grid = Rect(KENNEL_GRID_RECT)
        self._draw_frame(surface, grid)
        left, top = grid.move(KENNEL_GRID_OFFSET).topleft
        pitch_x, pitch_y = KENNEL_GRID_PITCH
        for index, monster in enumerate(self.box):
            row, column = divmod(index, KENNEL_GRID_COLUMNS)
            cell = Rect(
                left + column * pitch_x,
                top + row * pitch_y,
                KENNEL_ICON_SIZE,
                KENNEL_ICON_SIZE,
            )
            if index == self.selected_index:
                highlight = Rect(
                    cell.left - 1, cell.top, pitch_x, KENNEL_ICON_SIZE
                )
                surface.fill(self.selection_fill, highlight.inflate(-2, -2))
                self.selection.draw(surface, highlight)
            surface.blit(self.icons[monster], cell)

    def _draw_details(self, surface: Surface) -> None:
        panel = Rect(KENNEL_PANEL_RECT)
        self._draw_frame(surface, panel)
        left = panel.left + KENNEL_PANEL_PADDING
        right = panel.right - KENNEL_PANEL_PADDING

        title = T.translate(self.box_name).upper()
        self._blit_arbata(surface, title, left, panel.top + 8)
        count = f"{len(self.box)}{KENNEL_COUNT_SEPARATOR}{MAX_BOX}"
        blit_ink(
            surface, self.minimal_font, count, right=right, top=panel.top + 20
        )

        if not self.box:
            return
        monster = self.box[self.selected_index]
        front = self.fronts[monster]
        surface.blit(
            front, front.get_rect(midtop=(panel.centerx, panel.top + 30))
        )
        self._blit_arbata(surface, monster.name, left, panel.top + 97)
        level_top = panel.top + 110
        blit_ink(
            surface,
            self.minimal_font,
            f"Lv {monster.level}",
            left=left,
            top=level_top,
        )
        # The gender symbol goes at the end of the level line: the longest
        # names fill the panel's width on their own.
        if monster.gender_symbol:
            symbol = self.name_font.render(
                monster.gender_symbol, False, KENNEL_TEXT_COLOR
            )
            ink = symbol.get_bounding_rect()
            middle = level_top + KENNEL_MINIMAL_HEIGHT // 2
            surface.blit(symbol, (right - ink.right, middle - ink.centery))
        self.hp_bar.value = monster.hp_ratio
        self.hp_bar.draw(
            surface,
            Rect(left, panel.top + 117, right - left, KENNEL_HP_BAR_HEIGHT),
        )

    def _blit_arbata(
        self, surface: Surface, text: str, left: int, cap_top: int
    ) -> None:
        """Draw Arbata text with its capitals' top at ``cap_top``."""
        image = self.name_font.render(text, False, KENNEL_TEXT_COLOR)
        ink_left = image.get_bounding_rect().left
        surface.blit(image, (left - ink_left, cap_top - ARBATA_CAP_TOP))

    def kennel_options(
        self, instance_id: str, handler: MonsterActionHandler
    ) -> None:
        iid = UUID(instance_id)
        mon = self.monster_boxes.get_monsters_by_iid(iid)
        if mon is None:
            logger.error(f"Monster {iid} not found")
            return

        box_ids = [
            key
            for key in self.monster_boxes.monster_boxes
            if not self.monster_boxes.is_box_hidden(key, "monster")
        ]
        kennels = [
            key
            for key in box_ids
            if key != self.box_name
            and self.monster_boxes.get_box_size(key, "monster") < MAX_KENNEL
        ]

        swap_target = self.swap_target
        if swap_target:
            actions = {"swap": lambda: handler.swap(mon, swap_target)}
        else:
            actions = {}
            if len(self.char.monsters) < PARTY_LIMIT:
                actions["pick"] = lambda: handler.pick(mon)
            if kennels:
                actions["move"] = lambda: handler.move(mon, kennels)
            actions["release"] = lambda: handler.release(mon)
        actions["info"] = lambda: handler.info(mon)
        actions["tech"] = lambda: handler.tech(mon)

        filtered_actions = {
            action: func
            for action, func in actions.items()
            if not (action == "move" and len(box_ids) < 2)
        }

        options = create_choice_options(filtered_actions)
        open_choice_dialog(
            self.client,
            menu=MenuOptions(options),
            escape_key_exits=True,
        )


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
    image = font.render(text, False, KENNEL_TEXT_COLOR)
    ink = image.get_bounding_rect()
    x = left - ink.left if left is not None else (right or 0) - ink.right
    surface.blit(image, (x, top - ink.top))


class MonsterBoxState(PygameMenuState):
    """Menu to choose a tuxemon box."""

    name: ClassVar[str] = "MonsterBoxState"

    def __init__(
        self, client: BaseClient, character: NPC, **kwargs: Any
    ) -> None:
        width, height = client.context.resolution

        super().__init__(
            client=client, height=height, transition=SlideRight(), **kwargs
        )

        self.char = character

        menu_items_map = self.get_menu_items_map()
        self.add_menu_items(self.menu, menu_items_map)

    def add_menu_items(
        self,
        menu: Menu,
        items: Sequence[tuple[str, MenuGameObj]],
    ) -> None:
        menu.add.vertical_fill()
        for key, callback in items:
            player = self.char
            num_mons = player.monster_boxes.get_box_size(key, "monster")
            label = T.format(
                f"{T.translate(key).upper()}: {num_mons}/{MAX_BOX}"
            )
            menu.add.button(label, callback)
            menu.add.vertical_fill()

        width, height = self.client.context.resolution
        widgets_size = menu.get_size(widget=True)
        b_width, b_height = menu.get_scrollarea().get_border_size()
        menu.resize(
            widgets_size[0],
            height - 2 * b_height,
            position=(width + b_width, b_height, False),
        )

    def get_menu_items_map(self) -> Sequence[tuple[str, MenuGameObj]]:
        """
        Return a list of menu options and callbacks, to be overridden by
        class descendants.
        """
        return []

    def change_state(self, state: str, **kwargs: Any) -> partial[State]:
        return partial(
            self.client.state_manager.replace_state, state, **kwargs
        )


class MonsterStorageState(MonsterBoxState):
    """Menu to choose a box, which you can then take a tuxemon from."""

    name: ClassVar[str] = "MonsterStorageState"

    def __init__(self, client: BaseClient, *args: Any, **kwargs: Any):
        super().__init__(client, *args, **kwargs)

    def get_menu_items_map(self) -> Sequence[tuple[str, MenuGameObj]]:
        menu_items_map = []
        monster_boxes = self.char.monster_boxes
        for box_name, monsters in monster_boxes.monster_boxes.items():
            if not monster_boxes.is_box_hidden(box_name, "monster"):
                if not monsters:
                    menu_callback = partial(
                        open_dialog,
                        self.client,
                        [T.translate("menu_storage_empty_kennel")],
                    )
                else:
                    menu_callback = self.change_state(
                        "MonsterTakeState",
                        box_name=box_name,
                        character=self.char,
                    )
                menu_items_map.append((box_name, menu_callback))
        return menu_items_map


class MonsterDropOffState(MonsterBoxState):
    """Menu to choose a box, which you can then drop off a tuxemon into."""

    name: ClassVar[str] = "MonsterDropOffState"

    def __init__(self, client: BaseClient, *args: Any, **kwargs: Any):
        super().__init__(client, *args, **kwargs)

    def get_menu_items_map(self) -> Sequence[tuple[str, MenuGameObj]]:
        menu_items_map = []
        monster_boxes = self.char.monster_boxes
        for box_name, monsters in monster_boxes.monster_boxes.items():
            if not monster_boxes.is_box_hidden(box_name, "monster"):
                if len(monsters) < MAX_BOX:
                    menu_callback = self.change_state(
                        "MonsterDropOff",
                        box_name=box_name,
                        character=self.char,
                    )
                else:
                    menu_callback = partial(
                        open_dialog,
                        self.client,
                        [T.translate("menu_storage_full_kennel")],
                    )
                menu_items_map.append((box_name, menu_callback))
        return menu_items_map


class MonsterDropOff(MonsterMenuState):
    """Shows all Tuxemon in player's party, puts it into box if selected."""

    name: ClassVar[str] = "MonsterDropOff"

    def __init__(
        self,
        client: BaseClient,
        box_name: str,
        character: NPC,
        on_selection: Callable[[Monster], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(client=client, monsters=character.monsters, **kwargs)

        self.box_name = box_name
        self.char = character
        self.on_selection = on_selection

    def is_valid_entry(self, monster: Monster | None) -> bool:
        alive_monsters = [
            mon for mon in self.char.monsters if not mon.is_fainted
        ]
        if monster is not None:
            return len(alive_monsters) != 1 or monster not in alive_monsters
        return True

    def on_menu_selection(
        self,
        menu_item: MenuItem[Monster | None],
    ) -> None:
        monster = menu_item.game_object
        assert monster

        if monster.plague.is_infected():
            open_dialog(
                self.client,
                [T.translate("menu_storage_infected_monster")],
                dialog_speed="max",
            )
            return

        if self.on_selection:
            self.on_selection(monster)
            self.client.state_manager.pop_state(self)
        else:
            self.char.party.transfer_monster_to_box(monster, self.box_name)
            self.client.state_manager.pop_state(self)
