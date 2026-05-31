#!/usr/bin/env python3
"""
Headless AI-vs-AI battle simulator for Tuxemon.

Runs many battles with randomly assembled teams and reports aggregate stats
useful for playtesting rule changes (damage formula, technique balance, etc.).

Usage:
    python scripts/battle_sim.py -n 50 -s 3 -l 25
    python scripts/battle_sim.py --battles 200 --team-size 4 --level 30 -v
"""
from __future__ import annotations

import argparse
import logging
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Add project root so this can be run from any directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Initialize DB + translations before importing anything that uses them.
from tuxemon.core.asset import init_assets
from tuxemon.prepare import core_init

core_init()
init_assets()

# ── Patch pre-existing game bug: noddingoff.py accesses status.turn but the ──
# ── property is actually named nr_turn on the Status class.                  ──
from tuxemon.status.status import Status as _Status  # noqa: E402

if not hasattr(_Status, "turn"):
    _Status.turn = property(lambda self: self.lifecycle.turn)  # type: ignore[attr-defined]

from tuxemon.ai.manager import AIManager
from tuxemon.boxes import MonsterBoxes
from tuxemon.combat.combat_context import CombatType
from tuxemon.combat.machine import CombatMachine, CombatPhase
from tuxemon.combat.session import CombatSession
from tuxemon.db import EffectPhase, NpcCombatModel
from tuxemon.entity.party import PartyHandler
from tuxemon.entity.routing import RoutingPolicyRegistry
from tuxemon.event import get_event_bus
from tuxemon.item.item import Item
from tuxemon.monster.monster import Monster
from tuxemon.status.status import Status
from tuxemon.technique.technique import Technique

logger = logging.getLogger(__name__)

# ── Safety limit ───────────────────────────────────────────────────────────────
MAX_TURNS = 150


# ── Minimal stubs ──────────────────────────────────────────────────────────────

class _EffectManagerStub:
    def add_technique(self, tech: Any) -> None:
        pass

    def add_status(self, status: Any) -> None:
        pass


class _EventEngineStub:
    def execute_action(self, *args: Any, **kwargs: Any) -> None:
        pass


class _MapManagerStub:
    map_size = (0, 0)
    map_inside = False


class SimClient:
    """Provides the attributes that combat effects access via session.client."""

    def __init__(self, combat_session: CombatSession) -> None:
        self.event_bus = get_event_bus()
        self.combat_session = combat_session
        self.active_effect_manager = _EffectManagerStub()
        self.event_engine = _EventEngineStub()
        self.map_manager = _MapManagerStub()

    def push_state(self, *args: Any, **kwargs: Any) -> None:
        pass

    def remove_state_by_name(self, *args: Any, **kwargs: Any) -> None:
        pass


class _TimeStub:
    class _Vars:
        hour = 12
        stage_of_day = "day"

    def get_time_variables(self) -> "_TimeStub._Vars":
        return self._Vars()


class SimSession:
    """Minimal session wrapper used throughout the combat system."""

    def __init__(self, client: SimClient, player: "SimNPC") -> None:
        self.client = client
        # session.player is accessed by some item/trap effects; safe to be one trainer.
        self.player = player
        self.time = _TimeStub()


# ── Fake boxes ─────────────────────────────────────────────────────────────────

class _FakeBoxes:
    """Overflow box that silently accepts excess monsters."""

    def attempt_add_monster(
        self, monster: Monster, policy: Any, kennel: Any
    ) -> bool:
        return True

    def remove_from_box(self, *args: Any) -> None:
        pass


# ── SimNPC ─────────────────────────────────────────────────────────────────────

class SimNPC:
    """
    Lightweight NPC substitute for the battle simulator.

    Provides all attributes that CombatSession, AIManager, and combat effects
    access on an NPC, without requiring the full game session stack.
    """

    # Default slug used when the AI trainer config doesn't have a special entry.
    # Falls through to `default_decision`, which is fine.
    _DEFAULT_SLUG = "sim_trainer"

    is_player: bool = False

    def __init__(
        self,
        name: str,
        monsters: list[Monster],
        switch_logic: str | None = "healthiest",
        slug: str | None = None,
    ) -> None:
        self._name = name
        self.slug = slug or self._DEFAULT_SLUG
        self.items: list[Item] = []
        self.combat = NpcCombatModel(switch_logic=switch_logic)
        self._tuxepedia: dict[str, bool] = {}

        boxes: Any = _FakeBoxes()
        self.party = PartyHandler(
            monster_boxes=boxes,
            owner=self,
        )
        for mon in monsters:
            self.party.add_monster(mon)

    @property
    def name(self) -> str:
        return self._name

    @property
    def monsters(self) -> list[Monster]:
        return self.party.monsters

    # ── stubs for attributes touched during battle tracking ──────────────────

    class _TuxepediaStub:
        def register_seen(self, slug: str) -> None:
            pass

    class _BattleHandlerStub:
        def add_battle(self, *args: Any, **kwargs: Any) -> None:
            pass

    tuxepedia = _TuxepediaStub()
    battle_handler = _BattleHandlerStub()

    # current_map is read by track_battles(); None is acceptable.
    current_map: str | None = None


# ── Routing policy bootstrap ───────────────────────────────────────────────────

def _ensure_routing_policy() -> None:
    """Register a bare-minimum 'default' routing policy if not yet loaded."""
    if not RoutingPolicyRegistry._policies:
        RoutingPolicyRegistry._policies["default"] = {
            "force_to_box": False,
            "kennel_override": None,
            "locker_override": None,
            "max_party_size": 6,
            "allow_party_addition": True,
            "auto_release_if_box_full": False,
            "auto_discard_if_box_full": False,
            "overflow_kennel": None,
            "overflow_locker": None,
            "max_box_capacity": None,
            "nickname_rules": {},
            "kennel_name_rules": {},
            "locker_name_rules": {},
        }


# ── Action resolution ──────────────────────────────────────────────────────────

def _resolve_action(
    action: Any,
    c_session: CombatSession,
    session: SimSession,
) -> tuple[str, str, str, bool] | None:
    """
    Apply one action popped from the queue.
    Returns (user_name, method_slug, target_name, success) or None for statuses.
    """
    user = action.user
    method = action.method
    target = action.target

    if isinstance(method, Technique) and isinstance(user, Monster):
        result, _ = c_session.apply_technique(session, method, user, target)
        if result.should_tackle:
            c_session.enqueue_damage(user, target, result.damage)
        return (user.name, method.slug, target.name, result.success)

    elif isinstance(method, Status):
        c_session.apply_status(session, method, target, EffectPhase.PERFORM_STATUS)
        return None

    elif isinstance(method, Item) and user is not None:
        c_session.apply_item(session, method, user, target)
        return None

    return None


def _drain_action_queue(
    c_session: CombatSession,
    session: SimSession,
    action_log: list,
) -> None:
    """Pop and resolve every action currently in the queue."""
    while not c_session.action_queue.is_empty():
        action = c_session.action_queue.pop()
        entry = _resolve_action(action, c_session, session)
        if entry:
            action_log.append((c_session.turn,) + entry)
        c_session.action_queue.sort()


def _remove_fainted(
    c_session: CombatSession,
    ai_manager: AIManager,
) -> None:
    """Pull fainted monsters off the field and clean up associated state."""
    for npc, monster_list in list(
        c_session.field_monsters.get_all_monsters().items()
    ):
        for monster in list(monster_list):
            if monster.is_fainted:
                c_session.field_monsters.remove_monster(npc, monster)
                c_session.action_queue.remove_monster_actions(monster)
                c_session.damage_tracker.remove_monster(monster)
                ai_manager.remove_ai(monster)


# ── Phase handlers ─────────────────────────────────────────────────────────────

def _phase_housekeeping(
    c_session: CombatSession,
    session: SimSession,
) -> None:
    new_turn = c_session.next_turn()
    c_session.action_queue.set_current_turn(new_turn)
    # Pre-populate the queue with actions that were scheduled for this turn
    # (e.g. second turn of a charge/lock move).  Without this the machine
    # would stall in DECISION waiting for the locked monster's action.
    if c_session.action_queue.pending:
        c_session.action_queue.autoclean_pending()
        c_session.action_queue.from_pending_to_action(new_turn)
    c_session.fill_battlefield_positions(ask=new_turn > 1)
    c_session.track_enemy_monsters(session)


def _phase_decision(
    c_session: CombatSession,
    session: SimSession,
    ai_manager: AIManager,
) -> None:
    c_session.check_decisions(session)
    c_session.initialize_hit_chances()
    for monster in list(c_session.active_monsters):
        char = c_session.field_monsters.get_npc_for_monster(monster)
        monster.moves.recharge_moves()
        # Locked / charging monsters already have their action pre-queued
        # from the previous turn's schedule_action_in_turns call.
        if monster.locked_turns_left > 0 or monster.is_charging:
            continue
        ai_manager.process_ai_turn(monster, char)


def _phase_post_action(
    c_session: CombatSession,
    session: SimSession,
    action_log: list,
    ai_manager: AIManager,
) -> None:
    # Status ticks for this turn.
    c_session.apply_statuses(session)
    _drain_action_queue(c_session, session, action_log)
    _remove_fainted(c_session, ai_manager)


# ── Battle runner ──────────────────────────────────────────────────────────────

class BattleResult:
    def __init__(
        self,
        winner: SimNPC | None,
        turns: int,
        action_log: list,
    ) -> None:
        self.winner = winner  # None = draw / turn-limit
        self.turns = turns
        self.action_log = action_log  # list[(turn, user, tech, target, success)]


def run_battle(npc_a: SimNPC, npc_b: SimNPC) -> BattleResult:
    """Run one complete AI-vs-AI battle, capturing the winner before state is reset."""
    event_bus = get_event_bus()
    c_session = CombatSession()
    client = SimClient(c_session)
    session = SimSession(client, npc_a)
    machine = CombatMachine(c_session)
    ai_manager = AIManager(session)
    action_log: list = []

    c_session.set_combat_type(CombatType.TRAINER)
    c_session.set_battle_format(False)
    c_session.set_players([npc_a, npc_b])

    def on_monster_needed(player: SimNPC, ask: bool = False) -> None:
        bench = c_session.get_bench(player)
        if bench:
            replacement = ai_manager.choose_replacement_monster(player)
            if replacement:
                c_session.add_monster_into_play(session, player, replacement)

    event_bus.subscribe("monster_needed", on_monster_needed)

    winner: SimNPC | None = None
    final_turn = 0

    try:
        phase: CombatPhase | None = CombatPhase.READY

        while phase is not None:
            if phase == CombatPhase.HOUSEKEEPING:
                _phase_housekeeping(c_session, session)

            elif phase == CombatPhase.DECISION:
                _phase_decision(c_session, session, ai_manager)

            elif phase == CombatPhase.PRE_ACTION:
                c_session.action_queue.sort()

            elif phase == CombatPhase.ACTION:
                _drain_action_queue(c_session, session, action_log)
                _remove_fainted(c_session, ai_manager)

            elif phase == CombatPhase.POST_ACTION:
                _phase_post_action(c_session, session, action_log, ai_manager)

            elif phase in (
                CombatPhase.HAS_WINNER,
                CombatPhase.DRAW_MATCH,
                CombatPhase.RAN_AWAY,
                CombatPhase.END_COMBAT,
            ):
                break

            if c_session.turn > MAX_TURNS:
                logger.debug("Turn limit — draw.")
                break

            next_phase = machine.determine_next_phase(phase)

            if next_phase is None and phase not in (
                CombatPhase.BEGIN,
                CombatPhase.READY,
            ):
                logger.warning(
                    "Machine stalled at %s  queue=%d  active=%d",
                    phase,
                    len(c_session.action_queue.queue),
                    len(c_session.active_monsters),
                )
                break

            if next_phase == CombatPhase.END_COMBAT:
                break

            phase = next_phase

        # Determine winner before reset clears player list.
        remaining = c_session.remaining_players
        if len(remaining) == 1:
            winner = remaining[0]  # type: ignore[assignment]
        final_turn = c_session.turn

    finally:
        event_bus.unsubscribe("monster_needed", on_monster_needed)
        ai_manager.clear_ai()
        c_session.reset()

    return BattleResult(winner=winner, turns=final_turn, action_log=action_log)


# ── Team / monster helpers ─────────────────────────────────────────────────────

def get_monster_pool() -> list[str]:
    from tuxemon.database.runtime import db

    return list(db.database["monster"].keys())


def build_random_team(
    pool: list[str],
    team_size: int,
    level: int,
) -> list[Monster]:
    slugs = random.sample(pool, min(team_size, len(pool)))
    team: list[Monster] = []
    for slug in slugs:
        try:
            team.append(Monster.spawn_base(slug, level))
        except Exception as exc:
            logger.debug("Skipping %s: %s", slug, exc)
    return team


# ── Simulation loop ────────────────────────────────────────────────────────────

def simulate(num_battles: int, team_size: int, level: int) -> None:
    _ensure_routing_policy()

    pool = get_monster_pool()
    if len(pool) < team_size:
        print(
            f"Monster pool has only {len(pool)} species "
            f"but team-size is {team_size}. Aborting."
        )
        return

    print(
        f"Running {num_battles} battles | "
        f"team_size={team_size} | level={level} | "
        f"pool={len(pool)} species"
    )
    print()

    wins_a = wins_b = draws = errors = 0
    total_turns = 0
    tech_usage: dict[str, int] = defaultdict(int)

    for i in range(num_battles):
        team_a = build_random_team(pool, team_size, level)
        team_b = build_random_team(pool, team_size, level)

        if not team_a or not team_b:
            errors += 1
            continue

        npc_a = SimNPC("Alpha", team_a)
        npc_b = SimNPC("Beta", team_b)

        try:
            result = run_battle(npc_a, npc_b)
        except Exception:
            logger.exception("Battle %d crashed", i + 1)
            errors += 1
            continue

        total_turns += result.turns

        if result.winner is npc_a:
            wins_a += 1
        elif result.winner is npc_b:
            wins_b += 1
        else:
            draws += 1

        for _turn, _user, tech, _target, _ok in result.action_log:
            tech_usage[tech] += 1

        if (i + 1) % max(1, num_battles // 10) == 0:
            pct = (i + 1) / num_battles * 100
            print(f"  {i + 1:>{len(str(num_battles))}}/{num_battles}  ({pct:.0f}%)")

    completed = num_battles - errors
    print()
    print("─" * 52)
    print(f"Completed : {completed}/{num_battles}   Errors: {errors}")
    if not completed:
        return
    print(
        f"Alpha wins: {wins_a:>5}  ({wins_a / completed * 100:5.1f}%)"
        "  ← randomly-seeded, so ~50% expected"
    )
    print(f"Beta  wins: {wins_b:>5}  ({wins_b / completed * 100:5.1f}%)")
    print(f"Draws     : {draws:>5}  ({draws / completed * 100:5.1f}%)")
    print(f"Avg turns : {total_turns / completed:.1f}")
    print()

    if tech_usage:
        print("Top 15 most-used techniques:")
        for tech, count in sorted(
            tech_usage.items(), key=lambda x: -x[1]
        )[:15]:
            print(f"  {tech:<35} {count:>6}")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tuxemon headless AI-vs-AI battle simulator"
    )
    parser.add_argument(
        "-n", "--battles", type=int, default=20,
        help="Number of battles to simulate (default: 20)",
    )
    parser.add_argument(
        "-s", "--team-size", type=int, default=3,
        help="Monsters per team (default: 3)",
    )
    parser.add_argument(
        "-l", "--level", type=int, default=25,
        help="Level for all monsters (default: 25)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Show DEBUG-level logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    simulate(args.battles, args.team_size, args.level)


if __name__ == "__main__":
    main()
