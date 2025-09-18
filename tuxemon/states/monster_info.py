# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from collections.abc import Callable
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
from tuxemon.time_handler import today_ordinal
from tuxemon.tools import fix_measure

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
        fxw: Callable[[float], int] = lambda r: fix_measure(menu._width, r)
        fxh: Callable[[float], int] = lambda r: fix_measure(menu._height, r)
        menu._width = fxw(0.97)

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
        lab1.translate(fxw((34 / 256)), fxh((7.8 / 144)))
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
        lab2.translate(fxw((169.6 / 256)), fxh((10.8 / 144)))
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
        lab3.translate(fxw((82.4 / 256)), fxh((84.8 / 144)))

        lab3b: Any = menu.add.label(
            title=f"{y:,}",  # add commas for readability
            label_id="exp2",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab3b.translate(fxw((90 / 256)), fxh((94 / 144)))

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
            lab_gender.translate(fxw((7 / 256)), fxh((6 / 144)))

        # weight
        lab4: Any = menu.add.label(
            title=f"{mon_weight}{unit_weight}",
            label_id="weight",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab4.translate(fxw((121.6 / 256)), fxh((32.8 / 144)))
        # height
        lab5: Any = menu.add.label(
            title=f"{mon_height}{unit_height}",
            label_id="height",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab5.translate(fxw((82.4 / 256)), fxh((32.8 / 144)))

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
        lab8.translate(fxw((82.4 / 256)), fxh((55 / 144)))

        lab9: Any = menu.add.label(
            title=f"{cold}",
            label_id="taste-cold",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab9.translate(fxw((82.4 / 256)), fxh((63 / 144)))

        # capture
        reference = get_acquisition_reference(monster)
        lab10: Any = menu.add.label(
            title=reference,
            label_id="capture",
            font_size=self.font_type.big,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab10.translate(fxw((35 / 256)), fxh((117 / 144)))

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
            icon1_widget.translate(fxw(148.4 / 256), fxh(59 / 144))

        if len(types) >= 2:
            type2_icon = self._create_image(
                f"gfx/ui/icons/element/{types[1].slug}_type_watermark.png"
            )
            type2_icon.scale(prepare.SCALE, prepare.SCALE)
            icon2_widget = menu.add.image(image_path=type2_icon)
            icon2_widget.set_float(origin_position=True)
            # Position of type 2 (independent from type 1)
            icon2_widget.translate(fxw(131 / 256), fxh(43 / 144))

        # hp
        lab11: Any = menu.add.label(
            title=f"{monster.hp}",
            label_id="hp",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab11.translate(fxw((202 / 256)), fxh(32.8 / 144))
        # armour
        lab12: Any = menu.add.label(
            title=f"{monster.armour}",
            label_id="armour",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab12.translate(fxw((202 / 256)), fxh(45.8 / 144))
        # dodge
        lab13: Any = menu.add.label(
            title=f"{monster.dodge}",
            label_id="dodge",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab13.translate(fxw(202 / 256), fxh(58.8 / 144))
        # melee
        lab14: Any = menu.add.label(
            title=f"{monster.melee}",
            label_id="melee",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab14.translate(fxw(202 / 256), fxh(70.8 / 144))
        # ranged
        lab15: Any = menu.add.label(
            title=f"{monster.ranged}",
            label_id="ranged",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab15.translate(fxw(202 / 256), fxh(83.8 / 144))
        # speed
        lab16: Any = menu.add.label(
            title=f"{monster.speed}",
            label_id="speed",
            font_size=self.font_type.biggest,
            align=locals.ALIGN_LEFT,
            float=True,
            font_color=(0x5D, 0x41, 0x07),
        )
        lab16.translate(fxw(202 / 256), fxh(96.8 / 144))

        stat_positions = {
            "hp": (fxw((181.6 / 256)), fxh(34 / 144)),
            "armour": (fxw((181.6 / 256)), fxh(47 / 144)),
            "dodge": (fxw((181.6 / 256)), fxh(47 / 144)),
            "melee": (fxw(181.6 / 256), fxh(60 / 144)),
            "ranged": (fxw(181.6 / 256), fxh(85 / 144)),
            "speed": (fxw(181.6 / 256), fxh(98 / 144)),
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
            plus.translate(x + fxw(0.08), y)

        # Cold taste gives -10%
        cold_stat = get_stat_for_taste(monster.taste_cold)
        if cold_stat in stat_positions:
            x, y = stat_positions[cold_stat]
            minus = menu.add.image(image_path=minus_icon.copy())
            minus.set_float(origin_position=True)
            minus.translate(x + fxw(0.08), y)

        # bond icon
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

        bond_widget.translate(fxw(13.4 / 256), fxh(26 / 144))

        # image
        new_image = self._create_image(monster.sprite_handler.front_path)
        new_image.scale(prepare.SCALE, prepare.SCALE)
        image_widget = menu.add.image(image_path=new_image.copy())
        image_widget.set_float(origin_position=True)
        image_widget.translate(fxw((12.2 / 256)), fxh((25 / 144)))
        # tuxeball
        tuxeball = self._create_image(
            f"gfx/items/{monster.capture_device}.png"
        )
        tuxeball.scale(prepare.SCALE, prepare.SCALE)
        capture_device = menu.add.image(image_path=tuxeball)
        capture_device.set_float(origin_position=True)
        capture_device.translate(fxw((13.4 / 256)), fxh((108 / 144)))

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
