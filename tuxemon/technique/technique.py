# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from tuxemon.core.asset import get_assets
from tuxemon.core.core_effect import TechEffectResult
from tuxemon.core.core_processor import ConditionProcessor, EffectProcessor
from tuxemon.database.runtime import db
from tuxemon.db import (
    MenuAction,
    Range,
    SoundProperties,
    StatModel,
    TechBehaviors,
    TechniqueModel,
    VisualProperties,
)
from tuxemon.element import ElementTypesHandler
from tuxemon.locale import T
from tuxemon.modifiers import ModifiersHandler
from tuxemon.monster_dir.stats import BasicStats
from tuxemon.surfanim import FlipAxes
from tuxemon.technique.cooldown import Cooldown
from tuxemon.technique.stats import (
    TechniqueBaseStats,
    TechniqueCurrentStats,
    TechniqueCustomBoosts,
)

if TYPE_CHECKING:
    from tuxemon.monster import Monster
    from tuxemon.plugin import PluginObject
    from tuxemon.session import Session

logger = logging.getLogger(__name__)

SIMPLE_PERSISTANCE_ATTRIBUTES = (
    "slug",
    "attempts",
    "successes",
    "failures",
)


class Technique:
    """
    Particular skill that tuxemon monsters can use in battle.
    """

    def __init__(self, save_data: Mapping[str, Any] | None = None) -> None:
        save_data = save_data or {}

        self.instance_id: UUID = uuid4()
        self.tech_id: int = 0

        # Technique Stats
        # Base: Immutable stats from DB (source of truth)
        self.base_stats: TechniqueBaseStats = TechniqueBaseStats()
        # Custom: Persistent boosts from save file (additive layer)
        self.custom_boosts: TechniqueCustomBoosts = TechniqueCustomBoosts()
        # Current: Dynamic stats used in battle (mutable)
        self.stats = self.compute_stats()

        self.cooldown = Cooldown()
        self.visuals = VisualProperties(
            animation=None, flip_axes=FlipAxes.NONE, loop=-1
        )
        self.hit: bool = False
        self.speed: int = 0
        self.range: Range = Range.melee
        self.sound = SoundProperties(sfx=None, volume=1.5)
        self.sort: str = ""
        self.slug: str = ""
        self.types: ElementTypesHandler = ElementTypesHandler()
        self.modifiers: ModifiersHandler = ModifiersHandler()
        self.behaviors: TechBehaviors
        self.use_success: str = ""
        self.use_failure: str = ""
        self.use_tech: str = ""
        self.confirm_text: str = ""
        self.cancel_text: str = ""
        self.menu_actions_data: Sequence[MenuAction] = []

        self.core_assets = get_assets()
        self.effects: Sequence[PluginObject] = []
        self.conditions: Sequence[PluginObject] = []
        self.stat_modifiers: dict[str, StatModel] = {}
        self.temporary_stat_boosts: BasicStats = BasicStats()

        # attempts: total times the technique was invoked
        # successes: number of successful uses
        # failures: number of failed uses
        self.attempts: int = 0
        self.successes: int = 0
        self.failures: int = 0
        self.set_state(save_data)

    @classmethod
    def create(
        cls, slug: str, save_data: Mapping[str, Any] | None = None
    ) -> Technique:
        method = cls(save_data)
        method.load(slug)
        return method

    @property
    def name(self) -> str:
        return T.translate(self.slug)

    @property
    def description(self) -> str:
        return T.translate(f"{self.slug}_description")

    @property
    def is_recharging(self) -> bool:
        """Returns whether the technique is currently recharging."""
        return self.cooldown.is_recharging

    @property
    def power(self) -> float:
        return self.stats.power

    @power.setter
    def power(self, value: float) -> None:
        self.stats.power = value

    @property
    def potency(self) -> float:
        return self.stats.potency

    @potency.setter
    def potency(self, value: float) -> None:
        self.stats.potency = value

    @property
    def accuracy(self) -> float:
        return self.stats.accuracy

    @accuracy.setter
    def accuracy(self, value: float) -> None:
        self.stats.accuracy = value

    @property
    def healing_power(self) -> float:
        return self.stats.healing_power

    @healing_power.setter
    def healing_power(self, value: float) -> None:
        self.stats.healing_power = value

    @property
    def default_stats(self) -> TechniqueCurrentStats:
        """
        Returns the baseline stats (base + custom boosts),
        without any temporary battle modifiers.
        """
        return self.compute_stats()

    def load(self, slug: str) -> None:
        """
        Loads and sets this technique's attributes from the technique
        database. The technique is looked up in the database by slug.

        Parameters:
            The slug of the technique to look up in the database.
        """
        results = TechniqueModel.lookup(slug, db)
        self.slug = results.slug  # a short English identifier

        self.sort = results.sort

        # technique use notifications (translated!)
        self.use_tech = T.maybe_translate(results.use_tech)
        self.use_success = T.maybe_translate(results.use_success)
        self.use_failure = T.maybe_translate(results.use_failure)
        self.confirm_text = T.translate(results.confirm_text)
        self.cancel_text = T.translate(results.cancel_text)

        # types
        self.types = ElementTypesHandler(results.types)

        self.base_stats = TechniqueBaseStats(
            accuracy=results.accuracy,
            potency=results.potency,
            power=results.power,
            healing_power=results.healing_power,
        )
        self.reset_current_stats()

        self.speed = results.speed.numeric_value
        self.behaviors = results.behaviors
        self.cooldown.duration = results.recharge
        self.cooldown.min_remaining = results.min_recharge
        self.cooldown.delay_turns = results.initial_delay
        self.cooldown.charge = results.starting_charge
        self.cooldown.multiplier = results.cooldown_multiplier
        self.range = results.range
        self.tech_id = results.tech_id
        self.menu_actions_data = results.menu_actions
        self.tags = results.tags
        self.stat_modifiers = results.stat_modifiers

        self.effect_defs = results.effects
        self.conditions = self.core_assets.parse_conditions(results.conditions)

        self.condition_handler = ConditionProcessor(self.conditions)
        self.target = results.target.model_dump()
        self.modifiers = ModifiersHandler(results.modifiers)

        self.visuals = results.visuals
        self.sound = results.sound

    def compute_stats(self) -> TechniqueCurrentStats:
        return TechniqueCurrentStats(
            power=self.base_stats.power + self.custom_boosts.power,
            potency=self.base_stats.potency + self.custom_boosts.potency,
            accuracy=self.base_stats.accuracy + self.custom_boosts.accuracy,
            healing_power=self.base_stats.healing_power
            + self.custom_boosts.healing_power,
        )

    def can_use(self, session: Session, target: Monster) -> bool:
        if self.is_recharging:
            return False
        return self.validate_monster(session, target)

    def validate_monster(self, session: Session, target: Monster) -> bool:
        """
        Check if the target meets all conditions that the technique has on its use.
        """
        return self.condition_handler.validate(session=session, target=target)

    def recharge(self, amount: int = 1) -> None:
        self.cooldown.tick(amount)

    def full_recharge(self) -> None:
        self.cooldown.reset()

    def use(
        self, session: Session, user: Monster, target: Monster
    ) -> TechEffectResult:
        """
        Applies the technique's effects using EffectProcessor and returns the results.
        """
        self.attempts += 1
        self.effects = self.core_assets.parse_effects(self.effect_defs)
        self.effect_handler = EffectProcessor(self.effects)
        result = self.effect_handler.process_tech(
            session=session,
            source=self,
            user=user,
            target=target,
        )
        self.cooldown.trigger()
        if session.client:
            session.client.active_effect_manager.add_technique(self)
        if result.success:
            self.successes += 1
        else:
            self.failures += 1
        return result

    def has_type(self, type_slug: str) -> bool:
        """
        Returns TRUE if there is the type among the types.
        """
        return self.types.has_type(type_slug)

    def reset_current_stats(self) -> None:
        """
        Reset current stats to Base + Custom Boosts.
        Called after battle or when technique is refreshed.
        """
        self.stats = self.compute_stats()

    def get_state(self) -> Mapping[str, Any]:
        """
        Prepares a dictionary of the technique to be saved to a file.
        """
        save_data = {
            attr: getattr(self, attr)
            for attr in SIMPLE_PERSISTANCE_ATTRIBUTES
            if getattr(self, attr)
        }

        save_data["instance_id"] = self.instance_id.hex

        boosts_data = self.custom_boosts.to_dict()
        if any(boosts_data.values()):
            save_data["custom_boosts"] = boosts_data

        return save_data

    def set_state(self, save_data: Mapping[str, Any]) -> None:
        """
        Loads information from saved data.
        """
        if not save_data:
            return

        self.load(save_data["slug"])

        if "custom_boosts" in save_data:
            self.custom_boosts = TechniqueCustomBoosts.from_dict(
                save_data["custom_boosts"]
            )
        self.reset_current_stats()

        for key, value in save_data.items():
            if key == "instance_id" and value:
                self.instance_id = UUID(value)
            elif key in SIMPLE_PERSISTANCE_ATTRIBUTES:
                setattr(self, key, value)


def decode_moves(
    json_data: Sequence[Mapping[str, Any]] | None,
) -> list[Technique]:
    return [Technique(save_data=tech) for tech in (json_data or [])]


def encode_moves(techs: Sequence[Technique]) -> Sequence[Mapping[str, Any]]:
    return [tech.get_state() for tech in techs]
