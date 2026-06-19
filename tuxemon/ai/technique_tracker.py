# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.formula import simple_damage_multiplier
from tuxemon.platform.const.sizes import POWER_RANGE
from tuxemon.technique.technique import Technique

if TYPE_CHECKING:
    from tuxemon.ai.ai import SingleTechnique
    from tuxemon.monster.monster import Monster
    from tuxemon.session import Session

logger = logging.getLogger(__name__)


@dataclass
class TechniqueScoreResult:
    total: float
    breakdown: dict[str, float]


class TechniqueTracker:
    def __init__(self, session: Session, moves: list[Technique]):
        self.session = session
        self.moves = moves

    def get_valid_moves(
        self, opponents: list[Monster]
    ) -> list[tuple[Technique, Monster]]:
        """Returns valid techniques and their corresponding opponents."""
        return [
            (mov, opponent)
            for mov in self.moves
            for opponent in opponents
            if mov.can_use(self.session, opponent)
        ]

    def evaluate_technique(
        self,
        user: Monster,
        technique: Technique,
        opponent: Monster,
        config: SingleTechnique,
    ) -> float:
        """
        Evaluate the effectiveness of a technique against a specific opponent.
        """
        result = technique_score(user, technique, opponent, config)
        logger.debug(
            f"Technique evaluation for {technique.slug} vs {opponent.slug}: {result.breakdown}"
        )
        logger.debug(f"Final technique score: {result.total}")
        return result.total


def technique_score(
    user: Monster,
    technique: Technique,
    opponent: Monster,
    config: SingleTechnique,
) -> TechniqueScoreResult:
    """Calculate technique score with breakdown."""

    breakdown: dict[str, float] = {}

    # Raw type-effectiveness multiplier — reused by both effectiveness and ko scoring.
    raw_effectiveness = simple_damage_multiplier(
        technique.types.current, opponent.types.current
    )

    # Elemental effectiveness
    effectiveness_score = 0.0
    if config.elemental_multiplier_weight:
        effectiveness_score = raw_effectiveness * config.elemental_multiplier_weight
    elemental_health = config.elemental_health_threshold
    elemental_scaling = config.elemental_health_scaling
    if elemental_health and elemental_scaling:
        if opponent.current_hp > opponent.hp * elemental_health:
            effectiveness_score *= elemental_scaling
    breakdown["effectiveness"] = effectiveness_score

    # Range bonus (flat bonus by technique range category)
    # Note: technique.range.value gives the clean string ("melee", "touch", etc.)
    type_bonus = getattr(config, f"{technique.range.value}_bonus", None) or 0.0
    breakdown["type_bonus"] = type_bonus

    # Power
    power_score = 0.0
    if config.power_weight:
        normalized_power = technique.power / POWER_RANGE[1]
        power_score = normalized_power * config.power_weight
    breakdown["power"] = power_score

    # Accuracy
    accuracy_score = 0.0
    if config.accuracy_weight:
        accuracy_score = technique.accuracy * config.accuracy_weight
    breakdown["accuracy"] = accuracy_score

    # Healing
    healing_score = 0.0
    health_priority = config.health_priority_threshold
    healing_penalty = config.healing_penalty_threshold
    is_healing_move = technique.healing_power > 0.0 or technique.power == 0.0

    if health_priority and is_healing_move:
        if user.hp_ratio < health_priority and config.healing_weight:
            healing_score = technique.healing_power * config.healing_weight
    if healing_penalty and is_healing_move:
        if user.hp_ratio > healing_penalty and config.healing_penalty_weight:
            healing_score = (
                -technique.healing_power * config.healing_penalty_weight
            )
    breakdown["healing"] = healing_score

    # Speed: two additive terms, both derived from normalised technique speed
    # (extremely_slow=-1, normal=0, extremely_fast=+1).
    #   speed_weight       — baseline preference (negative = prefer slow/powerful moves)
    #   speed_urgency_weight — extra weight scaled by (1 − user HP ratio): zero at
    #                          full HP, grows linearly as HP falls.  Positive means
    #                          "prefer fast moves more urgently when near death."
    # Both weights can be trained via REINFORCE and are independently signed.
    normalized_speed = technique.speed / 3.0
    speed_score = 0.0
    if config.speed_weight:
        speed_score += normalized_speed * config.speed_weight
    if config.speed_urgency_weight:
        speed_score += normalized_speed * (1.0 - user.hp_ratio) * config.speed_urgency_weight
    breakdown["speed"] = speed_score

    # Potency weighted by target HP: a pure DoT (e.g. poison/burn) ticks more times
    # before the target dies, so it yields more total damage on a 100%-HP target than
    # a 10%-HP one. This is a throughput approximation only — it deliberately ignores
    # two tactical cases where a low-HP target is the *better* condition target:
    #   - healing denial (festering blocks healing): most valuable against a low-HP
    #     enemy trying to recover, ~worthless against a full-HP one — the opposite of
    #     the weighting below.
    #   - finishing DoTs: poison/burn on an ~8%-HP target can secure the KO without
    #     spending another attack, which the raw tick count undervalues.
    potency_score = 0.0
    if config.potency_weight:
        potency_score = (technique.potency or 0.0) * opponent.hp_ratio * config.potency_weight
    breakdown["potency"] = potency_score

    # Stat matchup: reward moves whose range type uses the user's stronger attack stat
    # and exploits the opponent's weaker defensive stat.
    #
    # Range-to-stat mapping (from range_map.yaml):
    #   melee  → user melee  vs target armour
    #   touch  → user melee  vs target dodge
    #   reach  → user ranged vs target armour
    #   ranged → user ranged vs target dodge
    #
    # user_align:   +1 when the move uses the user's dominant attack stat, -1 when it
    #               uses the weaker one.
    # target_weak:  +1 when the move hits the opponent's lower defensive stat, -1 when
    #               it runs into the higher one.
    # Combined score ranges [-2, +2]; multiply by stat_matchup_weight.
    stat_matchup_score = 0.0
    if config.stat_matchup_weight:
        cs_user = user.get_combat_stats()
        cs_opp = opponent.get_combat_stats()
        u_mel = float(cs_user.melee)
        u_rng = float(cs_user.ranged)
        t_arm = float(cs_opp.armour)
        t_dod = float(cs_opp.dodge)
        u_sum = u_mel + u_rng or 1.0
        t_sum = t_arm + t_dod or 1.0
        r = technique.range.value
        if r in ("melee", "touch"):
            user_align = (u_mel - u_rng) / u_sum
        elif r in ("ranged", "reach"):
            user_align = (u_rng - u_mel) / u_sum
        else:
            user_align = 0.0
        if r in ("melee", "reach"):
            target_weak = (t_dod - t_arm) / t_sum   # positive when armour < dodge
        elif r in ("ranged", "touch"):
            target_weak = (t_arm - t_dod) / t_sum   # positive when dodge < armour
        else:
            target_weak = 0.0
        stat_matchup_score = (user_align + target_weak) * config.stat_matchup_weight
    breakdown["stat_matchup"] = stat_matchup_score

    # Status application: flat bonus for moves that apply a condition via "give" effect.
    # Works alongside potency_weight (which scales DoT output by target HP); this weight
    # rewards the *act* of inflicting any status, useful for control-oriented AI.
    status_score = 0.0
    if config.status_weight:
        has_give = any(e.type == "give" for e in technique.effect_defs)
        if has_give:
            status_score = config.status_weight
    breakdown["status"] = status_score

    # Recharge penalty: discourages high-cooldown moves.
    # cooldown.duration is the number of turns the technique is locked out after use.
    # Use a negative weight to penalise multi-turn moves; zero or positive to ignore.
    recharge_score = 0.0
    if config.recharge_weight:
        recharge_score = technique.cooldown.duration * config.recharge_weight
    breakdown["recharge"] = recharge_score

    # KO potential: bonus proportional to how close this technique can bring a KO.
    # Estimated as (normalised_power × type_effectiveness) / opponent_hp_ratio,
    # clamped to [0, 1].  Peaks when a strong, effective move threatens a weakened foe.
    ko_score = 0.0
    if config.ko_weight:
        normalized_power = technique.power / POWER_RANGE[1]
        ko_ratio = normalized_power * raw_effectiveness / max(opponent.hp_ratio, 0.01)
        ko_score = min(1.0, ko_ratio) * config.ko_weight
    breakdown["ko"] = ko_score

    # Doubles spread bonus: flat bonus for moves that can target the whole enemy team.
    # Set spread_weight positive to prefer spread moves; leave null in singles configs.
    spread_score = 0.0
    if config.spread_weight:
        if technique.target.get("enemy_team", False):
            spread_score = config.spread_weight
    breakdown["spread"] = spread_score

    # Target focus: scales with opponent HP ratio for target-selection in doubles.
    # Negative weight → prefer weakened targets (KO focus).
    # Positive weight  → prefer healthier targets (soften multiple opponents).
    target_focus_score = 0.0
    if config.target_focus_weight:
        target_focus_score = opponent.hp_ratio * config.target_focus_weight
    breakdown["target_focus"] = target_focus_score

    total_score = sum(breakdown.values())

    logger.debug(
        f"Technique score breakdown for {technique.slug}: {breakdown}"
    )
    logger.debug(f"Final technique score: {total_score}")
    return TechniqueScoreResult(total=total_score, breakdown=breakdown)
