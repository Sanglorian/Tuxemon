# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from typing import Any, ClassVar, Optional

import pygame_menu
from pygame_menu import locals

from tuxemon import formula, prepare
from tuxemon.db import MonsterModel, db
from tuxemon.locale import T
from tuxemon.menu.menu import PygameMenuState
from tuxemon.monster import Monster
from tuxemon.platform.const import buttons
from tuxemon.platform.events import PlayerInput
from tuxemon.session import local_session
from tuxemon.time_handler import today_ordinal
from tuxemon.tools import transform_resource_filename

lookup_cache: dict[str, MonsterModel] = {}


import json

with open("mods/tuxemon/db/taste/taste.json", "r") as f:
    taste_map = json.load(f)


def _lookup_monsters() -> None:
    monsters = list(db.database["monster"])
    for mon in monsters:
        results = MonsterModel.lookup(mon, db)
        if results.txmn_id > 0:
            lookup_cache[mon] = results


class MonsterInfoState(PygameMenuState):
    """
    Shows details of the single monster with the journal
    background graphic.
    """

    name: ClassVar[str] = "MonsterInfoState"

    def add_menu_items(
        self,
        menu: pygame_menu.Menu,
        monster: Monster,
    ) -> None:
        window_width = menu._width
        window_height = menu._height
        scale = max(int(prepare.SCALE), 1)
        scaled_width = scale * prepare.NATIVE_RESOLUTION[0]
        scaled_height = scale * prepare.NATIVE_RESOLUTION[1]
        letter_x = max((window_width - scaled_width) // 2, 0)
        letter_y = max((window_height - scaled_height) // 2, 0)

        padding = getattr(menu._theme, "widget_padding", 0)
        pad_top = pad_left = 0
        if isinstance(padding, (int, float)):
            pad_top = pad_left = int(padding)
        elif isinstance(padding, (list, tuple)):
            if len(padding) == 2:
                pad_top = int(padding[0])
                pad_left = int(padding[1])
            elif len(padding) == 4:
                pad_top = int(padding[0])
                pad_left = int(padding[3])

        origin_x = letter_x - pad_left
        origin_y = letter_y - pad_top

        background = self._create_image(prepare.INDIV_INFO)
        background.scale(scale, scale)
        background_widget = menu.add.image(image_path=background)
        background_widget.set_float(origin_position=True)
        background_widget.translate(origin_x, origin_y)

        def scene_x(native_px: float) -> int:
            return origin_x + int(round(native_px * scale))

        def scene_y(native_py: float) -> int:
            return origin_y + int(round(native_py * scale))

        def scale_px(native_px: float) -> int:
            return int(round(native_px * scale))

        # types
        types = " ".join(
            map(lambda s: T.translate(s.slug), monster.types.current)
        )
        # weight and height
        models = list(lookup_cache.values())
        results = next(
            (model for model in models if model.slug == monster.slug), None
        )
        if results is None:
            return
        diff_weight = formula.diff_percentage(monster.weight, results.weight)
        diff_height = formula.diff_percentage(monster.height, results.height)
        unit = self.client.config.unit_measure
        if unit == "metric":
            mon_weight = round(monster.weight)
            mon_height = round(monster.height)
            unit_weight = prepare.U_KG
            unit_height = prepare.U_CM
        else:
            mon_weight = formula.convert_lbs(monster.weight)
            mon_height = formula.convert_ft(monster.height)
            unit_weight = prepare.U_LB
            unit_height = prepare.U_FT
        # name
        menu._auto_centering = False
        lab1: Any = menu.add.label(
            title=f"{monster.name.upper()}",
            label_id="name",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab1.translate(scene_x(34), scene_y(8))
        # level + exp
        exp = monster.total_experience
        lab2: Any = menu.add.label(
            title=f"Lv. {monster.level}",
            label_id="level",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab2.translate(scene_x(169.6), scene_y(10.8))
        # XP progress to next level
        exp_current_level = monster.experience_required(
            0
        )  # total EXP at current level
        exp_next_level = monster.experience_required(
            1
        )  # total EXP needed at next level

        # how much XP earned since last level-up
        x = monster.total_experience - exp_current_level
        # how much XP is needed in total to level up
        y = exp_next_level - exp_current_level

        lab3: Any = menu.add.label(
            title=f"{x:,}/",  # add commas for readability
            label_id="exp",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab3.translate(scene_x(82.4), scene_y(84.8))

        lab3b: Any = menu.add.label(
            title=f"{y:,}",  # add commas for readability
            label_id="exp2",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab3b.translate(scene_x(90), scene_y(94))

        # gender
        gender_symbol = ""
        if monster.gender == "male":
            gender_symbol = "\u2642"  # ♂
        elif monster.gender == "female":
            gender_symbol = "\u2640"  # ♀

        if gender_symbol:
            lab_gender: Any = menu.add.label(
                title=gender_symbol,
                label_id="gender",
                font_size=self.font_type.biggest,
                align=locals.ALIGN_LEFT,
                font_color=(0x5D, 0x41, 0x07),
                float=True,
            )
            lab_gender.translate(scene_x(7), scene_y(6))

        # weight
        lab4: Any = menu.add.label(
            title=f"{mon_weight}{unit_weight}",
            label_id="weight",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab4.translate(scene_x(121.6), scene_y(32.8))
        # height
        lab5: Any = menu.add.label(
            title=f"{mon_height}{unit_height}",
            label_id="height",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab5.translate(scene_x(82.4), scene_y(32.8))

        # taste
        tastes = T.translate("tastes")
        cold = T.translate(f"taste_{monster.taste_cold.lower()}")
        warm = T.translate(f"taste_{monster.taste_warm.lower()}")
        lab8: Any = menu.add.label(
            title=f"{warm}",
            label_id="taste-warm",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab8.translate(scene_x(82.4), scene_y(55))

        lab9: Any = menu.add.label(
            title=f"{cold}",
            label_id="taste-cold",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab9.translate(scene_x(82.4), scene_y(63))

        # capture
        reference = get_acquisition_reference(monster)
        lab10: Any = menu.add.label(
            title=reference,
            label_id="capture",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_name=transform_resource_filename("font", "Pizel.ttf"),
            font_color=(0x5D, 0x41, 0x07),
        )
        lab10.translate(scene_x(35), scene_y(117))

        # type icons (first and second type separately)
        types = monster.types.current

        if len(types) >= 1:
            type1_icon = self._create_image(
                f"gfx/ui/icons/element/{types[0].slug}_type_watermark.png"
            )
            type1_icon.scale(prepare.SCALE, prepare.SCALE)
            icon1_widget = menu.add.image(image_path=type1_icon)
            icon1_widget.set_float(origin_position=True)
            # Position of type 1 (set wherever you want)
            icon1_widget.translate(scene_x(148.4), scene_y(59))

        if len(types) >= 2:
            type2_icon = self._create_image(
                f"gfx/ui/icons/element/{types[1].slug}_type_watermark.png"
            )
            type2_icon.scale(prepare.SCALE, prepare.SCALE)
            icon2_widget = menu.add.image(image_path=type2_icon)
            icon2_widget.set_float(origin_position=True)
            # Position of type 2 (independent from type 1)
            icon2_widget.translate(scene_x(131), scene_y(43))

        # hp
        lab11: Any = menu.add.label(
            title=f"{monster.hp}",
            label_id="hp",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab11.translate(scene_x(202), scene_y(32.8))
        # armour
        lab12: Any = menu.add.label(
            title=f"{monster.armour}",
            label_id="armour",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab12.translate(scene_x(202), scene_y(45.8))
        # dodge
        lab13: Any = menu.add.label(
            title=f"{monster.dodge}",
            label_id="dodge",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab13.translate(scene_x(202), scene_y(58.8))
        # melee
        lab14: Any = menu.add.label(
            title=f"{monster.melee}",
            label_id="melee",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab14.translate(scene_x(202), scene_y(70.8))
        # ranged
        lab15: Any = menu.add.label(
            title=f"{monster.ranged}",
            label_id="ranged",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab15.translate(scene_x(202), scene_y(83.8))
        # speed
        lab16: Any = menu.add.label(
            title=f"{monster.speed}",
            label_id="speed",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab16.translate(scene_x(202), scene_y(96.8))

        stat_positions = {
            "hp": (scene_x(181.6), scene_y(34)),
            "armour": (scene_x(181.6), scene_y(47)),
            "dodge": (scene_x(181.6), scene_y(47)),
            "melee": (scene_x(181.6), scene_y(60)),
            "ranged": (scene_x(181.6), scene_y(85)),
            "speed": (scene_x(181.6), scene_y(98)),
        }

        plus_icon = self._create_image("gfx/ui/icons/plusminus/plus.png")
        minus_icon = self._create_image("gfx/ui/icons/plusminus/minus.png")
        plus_icon.scale(prepare.SCALE, prepare.SCALE)
        minus_icon.scale(prepare.SCALE, prepare.SCALE)

        # Helper: find which stat a taste affects
        def get_stat_for_taste(slug: str) -> str | None:
            for entry in taste_map:
                if entry["slug"] == slug.lower():
                    return entry["modifiers"][0]["values"][0]
            return None

        # Warm taste gives +10%
        warm_stat = get_stat_for_taste(monster.taste_warm)
        if warm_stat in stat_positions:
            x, y = stat_positions[warm_stat]
            plus = menu.add.image(image_path=plus_icon.copy())
            plus.set_float(origin_position=True)
            plus.translate(x + scale_px(20), y)

        # Cold taste gives -10%
        cold_stat = get_stat_for_taste(monster.taste_cold)
        if cold_stat in stat_positions:
            x, y = stat_positions[cold_stat]
            minus = menu.add.image(image_path=minus_icon.copy())
            minus.set_float(origin_position=True)
            minus.translate(x + scale_px(20), y)

        # bond icon
        try:
            player = local_session.player
        except ValueError:
            player = None

        if player is not None and player.items.find_item("friendship_scroll"):
            bond_value = monster.bond

            if bond_value <= 20:
                bond_file = "gfx/ui/icons/bond/bond1.png"
            elif bond_value <= 50:
                bond_file = "gfx/ui/icons/bond/bond2.png"
            elif bond_value <= 75:
                bond_file = "gfx/ui/icons/bond/bond3.png"
            else:
                bond_file = "gfx/ui/icons/bond/bond4.png"

            bond_icon = self._create_image(bond_file)
            bond_icon.scale(prepare.SCALE, prepare.SCALE)
            bond_widget = menu.add.image(image_path=bond_icon)
            bond_widget.set_float(origin_position=True)

            bond_widget.translate(scene_x(13.4), scene_y(26))

        # image
        new_image = self._create_image(monster.sprite_handler.front_path)
        new_image.scale(prepare.SCALE, prepare.SCALE)
        image_widget = menu.add.image(image_path=new_image.copy())
        image_widget.set_float(origin_position=True)
        image_widget.translate(scene_x(12.2), scene_y(25))
        # tuxeball
        tuxeball = self._create_image(
            f"gfx/items/{monster.capture_device}.png"
        )
        tuxeball.scale(prepare.SCALE, prepare.SCALE)
        capture_device = menu.add.image(image_path=tuxeball)
        capture_device.set_float(origin_position=True)
        capture_device.translate(scene_x(13.4), scene_y(108))

    def __init__(self, **kwargs: Any) -> None:
        if not lookup_cache:
            _lookup_monsters()
        monster: Optional[Monster] = None
        source = ""
        for element in kwargs.values():
            monster = element["monster"]
            source = element["source"]
        if monster is None:
            raise ValueError("No monster")
        width, height = prepare.SCREEN_SIZE

        theme = self._setup_theme(prepare.INDIV_INFO)
        theme.background_color = prepare.BACKGROUND_COLOR
        theme.scrollarea_position = locals.POSITION_EAST
        theme.widget_alignment = locals.ALIGN_CENTER
        theme.widget_font_shadow = False

        super().__init__(height=height, width=width)
        self._source = source
        self._monster = monster
        self.add_menu_items(self.menu, monster)
        self.reset_theme()

    def process_event(self, event: PlayerInput) -> Optional[PlayerInput]:
        param: dict[str, Any] = {"source": self._source}
        client = self.client

        if self._source in [
            "WorldMenuState",
            "MonsterMenuState",
            "MonsterTakeState",
        ]:
            monsters = _get_monsters(self._monster, self._source)
            slot = monsters.index(self._monster)

            if event.button == buttons.RIGHT and event.pressed:
                slot = (slot + 1) % len(monsters)
                param["monster"] = monsters[slot]
                client.replace_state("MonsterInfoState", kwargs=param)
            elif event.button == buttons.LEFT and event.pressed:
                slot = (slot - 1) % len(monsters)
                param["monster"] = monsters[slot]
                client.replace_state("MonsterInfoState", kwargs=param)

        if (
            event.button in (buttons.BACK, buttons.B, buttons.A)
            and event.pressed
        ):
            client.remove_state_by_name("MonsterInfoState")

        return None


def get_acquisition_reference(monster: Monster) -> str:
    acq_type = monster.acquisition
    doc = today_ordinal() - monster.capture
    time_key = "today" if doc < 1 else "days_ago"
    msgid = f"tuxepedia_acquisition_{acq_type.value}_{time_key}"
    return T.translate(msgid) if doc < 1 else T.format(msgid, {"doc": doc})


def _get_monsters(monster: Monster, source: str) -> list[Monster]:
    owner = monster.get_owner()
    if source == "MonsterTakeState":
        box = owner.monster_boxes.get_box_name(monster.instance_id)
        if box is None:
            raise ValueError("Box doesn't exist")
        return owner.monster_boxes.get_monsters(box)
    else:
        return owner.monsters
