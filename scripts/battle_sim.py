#!/usr/bin/env python3
"""
Headless AI-vs-AI battle simulator for Tuxemon.

Two modes:
  Gauntlet   — many random battles, aggregate win/technique stats.
  Tournament — single-elimination bracket; winners play winners until a
               champion emerges, then reports the podium with team rosters,
               top surviving monsters, and top techniques from winning sides.

Usage:
    python scripts/battle_sim.py -n 200 -s 3 -l 25
    python scripts/battle_sim.py --tournament 16 --team-size 3 --level 25
    python scripts/battle_sim.py --tournament 32 -s 4 -l 30 -v
"""
from __future__ import annotations

import argparse
import logging
import math
import random
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tuxemon.core.asset import init_assets
from tuxemon.prepare import core_init

core_init()
init_assets()

# Patch pre-existing game bug: noddingoff.py reads status.turn but the
# property is named nr_turn on the Status class.
from tuxemon.status.status import Status as _Status  # noqa: E402

if not hasattr(_Status, "turn"):
    _Status.turn = property(lambda self: self.lifecycle.turn)  # type: ignore[attr-defined]

from tuxemon.ai.manager import AIManager
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

MAX_TURNS = 150


# ── Stubs ──────────────────────────────────────────────────────────────────────

class _EffectManagerStub:
    def add_technique(self, tech: Any) -> None: pass
    def add_status(self, status: Any) -> None: pass


class _EventEngineStub:
    def execute_action(self, *a: Any, **kw: Any) -> None: pass


class _MapManagerStub:
    map_size = (0, 0)
    map_inside = False


class SimClient:
    def __init__(self, combat_session: CombatSession) -> None:
        self.event_bus = get_event_bus()
        self.combat_session = combat_session
        self.active_effect_manager = _EffectManagerStub()
        self.event_engine = _EventEngineStub()
        self.map_manager = _MapManagerStub()

    def push_state(self, *a: Any, **kw: Any) -> None: pass
    def remove_state_by_name(self, *a: Any, **kw: Any) -> None: pass


class _TimeStub:
    class _Vars:
        hour = 12
        stage_of_day = "day"
    def get_time_variables(self) -> "_TimeStub._Vars":
        return self._Vars()


class SimSession:
    def __init__(self, client: SimClient, player: "SimNPC") -> None:
        self.client = client
        self.player = player
        self.time = _TimeStub()


class _FakeBoxes:
    def attempt_add_monster(self, monster: Monster, policy: Any, kennel: Any) -> bool:
        return True
    def remove_from_box(self, *a: Any) -> None: pass


# ── SimNPC ─────────────────────────────────────────────────────────────────────

class SimNPC:
    _DEFAULT_SLUG = "sim_trainer"
    is_player: bool = False
    current_map: str | None = None

    class _TuxepediaStub:
        def register_seen(self, slug: str) -> None: pass

    class _BattleHandlerStub:
        def add_battle(self, *a: Any, **kw: Any) -> None: pass

    tuxepedia = _TuxepediaStub()
    battle_handler = _BattleHandlerStub()

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
        self.party = PartyHandler(monster_boxes=_FakeBoxes(), owner=self)
        for mon in monsters:
            self.party.add_monster(mon)

    @property
    def name(self) -> str:
        return self._name

    @property
    def monsters(self) -> list[Monster]:
        return self.party.monsters


# ── Routing policy bootstrap ───────────────────────────────────────────────────

def _ensure_routing_policy() -> None:
    if not RoutingPolicyRegistry._policies:
        RoutingPolicyRegistry._policies["default"] = {
            "force_to_box": False, "kennel_override": None,
            "locker_override": None, "max_party_size": 6,
            "allow_party_addition": True, "auto_release_if_box_full": False,
            "auto_discard_if_box_full": False, "overflow_kennel": None,
            "overflow_locker": None, "max_box_capacity": None,
            "nickname_rules": {}, "kennel_name_rules": {}, "locker_name_rules": {},
        }


# ── Action resolution ──────────────────────────────────────────────────────────

# Action log entries: (turn, user_slug, tech_slug, target_slug, success)
ActionEntry = tuple[int, str, str, str, bool]


def _resolve_action(
    action: Any,
    c_session: CombatSession,
    session: SimSession,
) -> ActionEntry | None:
    user, method, target = action.user, action.method, action.target

    if isinstance(method, Technique) and isinstance(user, Monster):
        result, _ = c_session.apply_technique(session, method, user, target)
        if result.should_tackle:
            c_session.enqueue_damage(user, target, result.damage)
        return (c_session.turn, user.slug, method.slug, target.slug, result.success)

    elif isinstance(method, Status):
        c_session.apply_status(session, method, target, EffectPhase.PERFORM_STATUS)

    elif isinstance(method, Item) and user is not None:
        c_session.apply_item(session, method, user, target)

    return None


def _drain_action_queue(
    c_session: CombatSession,
    session: SimSession,
    action_log: list[ActionEntry],
) -> None:
    while not c_session.action_queue.is_empty():
        action = c_session.action_queue.pop()
        entry = _resolve_action(action, c_session, session)
        if entry:
            action_log.append(entry)
        c_session.action_queue.sort()


def _remove_fainted(c_session: CombatSession, ai_manager: AIManager) -> None:
    for npc, monster_list in list(c_session.field_monsters.get_all_monsters().items()):
        for monster in list(monster_list):
            if monster.is_fainted:
                c_session.field_monsters.remove_monster(npc, monster)
                c_session.action_queue.remove_monster_actions(monster)
                c_session.damage_tracker.remove_monster(monster)
                ai_manager.remove_ai(monster)


# ── Phase handlers ─────────────────────────────────────────────────────────────

def _phase_housekeeping(c_session: CombatSession, session: SimSession) -> None:
    new_turn = c_session.next_turn()
    c_session.action_queue.set_current_turn(new_turn)
    # Pre-populate queue with actions scheduled for this turn (charge/lock moves).
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
        if monster.locked_turns_left > 0 or monster.is_charging:
            continue
        ai_manager.process_ai_turn(monster, char)


def _phase_post_action(
    c_session: CombatSession,
    session: SimSession,
    action_log: list[ActionEntry],
    ai_manager: AIManager,
) -> None:
    c_session.apply_statuses(session)
    _drain_action_queue(c_session, session, action_log)
    _remove_fainted(c_session, ai_manager)


# ── Battle result ──────────────────────────────────────────────────────────────

@dataclass
class BattleResult:
    winner: SimNPC | None          # None = draw or turn-limit
    loser: SimNPC | None
    turns: int
    action_log: list[ActionEntry]
    # Slugs of all monsters on the winning team (for win-rate tracking).
    winner_monster_slugs: list[str] = field(default_factory=list)
    # Subset of the above that were still alive at the end.
    winner_surviving_slugs: list[str] = field(default_factory=list)


# ── Core battle loop ───────────────────────────────────────────────────────────

def run_battle(
    npc_a: SimNPC,
    npc_b: SimNPC,
    is_double: bool = False,
    ai_factory: "Any | None" = None,
) -> BattleResult:
    """Run one AI-vs-AI battle. Both NPCs should have freshly spawned monsters."""
    event_bus = get_event_bus()
    c_session = CombatSession()
    client = SimClient(c_session)
    session = SimSession(client, npc_a)
    machine = CombatMachine(c_session)
    ai_manager = ai_factory(session) if ai_factory else AIManager(session)
    action_log: list[ActionEntry] = []

    c_session.set_combat_type(CombatType.TRAINER)
    c_session.set_battle_format(is_double)
    c_session.set_players([npc_a, npc_b])

    def on_monster_needed(player: SimNPC, ask: bool = False) -> None:
        while c_session.get_available_positions(player) > 0:
            bench = c_session.get_bench(player)
            if not bench:
                break
            replacement = ai_manager.choose_replacement_monster(player)
            if replacement is None:
                break
            c_session.add_monster_into_play(session, player, replacement)

    event_bus.subscribe("monster_needed", on_monster_needed)

    winner: SimNPC | None = None
    loser: SimNPC | None = None
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
                CombatPhase.HAS_WINNER, CombatPhase.DRAW_MATCH,
                CombatPhase.RAN_AWAY, CombatPhase.END_COMBAT,
            ):
                break

            if c_session.turn > MAX_TURNS:
                break

            next_phase = machine.determine_next_phase(phase)
            if next_phase is None and phase not in (CombatPhase.BEGIN, CombatPhase.READY):
                logger.warning("Machine stalled at %s  q=%d  a=%d",
                               phase, len(c_session.action_queue.queue),
                               len(c_session.active_monsters))
                break
            if next_phase == CombatPhase.END_COMBAT:
                break
            phase = next_phase

        remaining = c_session.remaining_players
        if len(remaining) == 1:
            winner = remaining[0]  # type: ignore[assignment]
            loser = (npc_b if winner is npc_a else npc_a)
        final_turn = c_session.turn

    finally:
        event_bus.unsubscribe("monster_needed", on_monster_needed)
        ai_manager.clear_ai()
        c_session.reset()

    # Collect monster stats from the winner's party (monsters still exist post-reset).
    winner_slugs: list[str] = []
    surviving_slugs: list[str] = []
    if winner is not None:
        for mon in winner.monsters:
            winner_slugs.append(mon.slug)
            if not mon.is_fainted:
                surviving_slugs.append(mon.slug)

    return BattleResult(
        winner=winner,
        loser=loser,
        turns=final_turn,
        action_log=action_log,
        winner_monster_slugs=winner_slugs,
        winner_surviving_slugs=surviving_slugs,
    )


# ── Team (persistent across tournament rounds) ─────────────────────────────────

@dataclass
class Team:
    name: str
    slugs: list[str]
    level: int
    wins: int = 0
    losses: int = 0
    designed: bool = False   # True for hand-crafted teams
    # Optional per-monster technique overrides: {slug: [tech1, tech2, tech3, tech4]}
    # When set, replaces the default level-up moveset with explicit techniques.
    tech_overrides: dict[str, list[str]] = field(default_factory=dict)

    def make_npc(self) -> SimNPC:
        monsters: list[Monster] = []
        for slug in self.slugs:
            try:
                mon = Monster.spawn_base(slug, self.level)
                if slug in self.tech_overrides:
                    mon.moves.moves.clear()
                    for tech_slug in self.tech_overrides[slug]:
                        tech = Technique.create(tech_slug)
                        mon.moves.learn(mon, tech, ignore_eligibility=True)
                monsters.append(mon)
            except Exception as exc:
                logger.debug("Skipping %s: %s", slug, exc)
        return SimNPC(self.name, monsters)

    def roster(self) -> str:
        return "  ".join(self.slugs)

    def label(self) -> str:
        return f"★ {self.name}" if self.designed else self.name


# ── Hand-crafted competitive teams ────────────────────────────────────────────
# Gen-1 teams (Alpha–Delta): designed from tournament win-rate / survival stats,
# using each monster's natural level-up moveset.
#
# Gen-2 teams (Epsilon–Theta): designed from tag analysis. Each monster is given
# an explicit 4-move set drawn from the highest-win-% techniques whose tags
# overlap with the monster's own tags.
#
# Dominant techniques by winner-share (doubles):
#   earthquake  (calamity, ground)  power 2.9 AoE
#   snowstorm   (calamity, weather) power 3.0 AoE + exhaust
#   tsunami     (water,    calamity) power 2.7 AoE
#   all_in      (leadership, fury)  power 3.0
#   frostbite   (ice, bite)         power 3.0
#   sudden_glow (healing, light)    healing sustain
#   fester      (toxic)             damage + toxic on both
#   flamethrower(flame, gadgets)    power 2.25 fire coverage
#   kraken      (pseudopod,summoner) power 2.5 water
#   mudslide    (ground)            power 2.25 earth

DESIGNED_TEAM_DEFS: list[tuple[str, list[str], dict[str, list[str]]]] = [
    # ── Gen-1 ──────────────────────────────────────────────────────────────────
    # cohldrabi (snowstorm+fester), vivitron (best survivor, battery_acid),
    # crankus (tsunami, proven champion), bishosand (proven survivor humanoid)
    ("Alpha", ["cohldrabi", "vivitron", "crankus", "bishosand"], {}),

    # thumpurn (earthquake, frequent podium), deviraptor (earthquake, dragon champ),
    # lightmare (sudden_glow), rabbitosaur (proven survivor 42/51)
    ("Beta", ["thumpurn", "deviraptor", "lightmare", "rabbitosaur"], {}),

    # crustagu (snowstorm+kraken+fester), delfeco (tsunami, past champion),
    # equill (earthquake), gectile (humanoid, Team 03 champ)
    ("Gamma", ["crustagu", "delfeco", "equill", "gectile"], {}),

    # brachifor (snowstorm+fester), dandicub (fester), krokivip (kraken), conifrost (snowstorm)
    ("Delta", ["brachifor", "dandicub", "krokivip", "conifrost"], {}),

    # ── Gen-2: tag-optimised movesets ──────────────────────────────────────────
    # Epsilon: asudopt (can learn ALL 13 dominant techs, 41 tags) anchors the team.
    # seraphice + lucifice are the two best secondary AoE users (6 techs each).
    # pyraminx brings water+ground AoE depth (tsunami/earthquake/kraken/mudslide).
    ("Epsilon", ["asudopt", "seraphice", "lucifice", "pyraminx"], {
        "asudopt":   ["earthquake", "snowstorm", "all_in",       "sudden_glow"],
        "seraphice": ["earthquake", "snowstorm", "tsunami",      "sudden_glow"],
        "lucifice":  ["earthquake", "snowstorm", "tsunami",      "flamethrower"],
        "pyraminx":  ["earthquake", "tsunami",   "kraken",       "mudslide"],
    }),

    # Zeta: calamity + poison coverage.
    # pythonova (calamity+toxic: AoE+fester), eruptibus (calamity+fire+bite: AoE+frostbite),
    # nimbulex (calamity+weather+water: AoE+sustain), bigfin (water+ground: AoE stack).
    ("Zeta", ["pythonova", "eruptibus", "nimbulex", "bigfin"], {
        "pythonova": ["earthquake", "snowstorm", "tsunami",      "fester"],
        "eruptibus": ["earthquake", "snowstorm", "frostbite",    "flamethrower"],
        "nimbulex":  ["earthquake", "snowstorm", "tsunami",      "sudden_glow"],
        "bigfin":    ["earthquake", "tsunami",   "kraken",       "mudslide"],
    }),

    # Eta: fire + earth coverage with sustain.
    # mingdyn (calamity+healing: AoE+heal), weedlantis (calamity+leadership: AoE+all_in),
    # volconey (calamity+ground: AoE+mudslide), rooksand (ground+water+fists: AoE+one_two).
    ("Eta", ["mingdyn", "weedlantis", "volconey", "rooksand"], {
        "mingdyn":   ["earthquake", "snowstorm", "sudden_glow",  "flamethrower"],
        "weedlantis":["earthquake", "snowstorm", "tsunami",      "all_in"],
        "volconey":  ["earthquake", "snowstorm", "tsunami",      "mudslide"],
        "rooksand":  ["earthquake", "tsunami",   "mudslide",     "one_two"],
    }),

    # Theta: bite/ice + status sustain depth.
    # leviadile (toxic+fury+ice+water: fester+frostbite+all_in),
    # angesnow (ice+healing+weather: snowstorm+frostbite+sudden_glow),
    # ampystoma (water+weather+light: AoE+sustain), krokivip (bite+water: frostbite+kraken).
    ("Theta", ["leviadile", "angesnow", "ampystoma", "krokivip"], {
        "leviadile": ["tsunami",    "fester",    "frostbite",    "all_in"],
        "angesnow":  ["snowstorm",  "frostbite", "sudden_glow",  "all_in"],
        "ampystoma": ["tsunami",    "snowstorm", "sudden_glow",  "water_blast"],
        "krokivip":  ["tsunami",    "frostbite", "all_in",       "water_blast"],
    }),

    # ── Gen-3: counter-teams designed to beat Theta ────────────────────────────
    # Converged type-coverage insight (iteration 3 analysis):
    #   laser_beam (lightning+metal):  2x vs ALL 4 Theta (lightning→water×3 + metal→cosmic)
    #   woodsmash  (heroic+wood):      2x vs ALL 4 Theta (heroic→frost×1 + wood→water/venom×3)
    #   earthquake (earth, AoE):       2x vs ampystoma; hits both active enemies simultaneously
    #   tsunami    (water, AoE):       extra AoE doubles pressure; hits both active enemies
    #
    # Recharge cycle (EQ=2, WS=2, LB=4, TS=3): never all four on cooldown simultaneously.
    # Monster selection: all chosen from the top unused pool by HP+attack composite score
    # (hp ≥ 455, combined attack ≥ 500) to match or exceed Theta's 1558 total HP.

    # Iota — lightning flagship. coproblight/rinocereed are top-score megafauna;
    # burrlock/glomon add bulk. All carry the full anti-Theta AoE+type core.
    ("Iota", ["coproblight", "burrlock", "rinocereed", "glomon"], {
        "coproblight": ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "burrlock":    ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "rinocereed":  ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "glomon":      ["earthquake", "woodsmash", "laser_beam", "tsunami"],
    }),

    # Kappa — shadowed pursuit. possessun/pharavion/helipi/bolt; all HP ≥ 455.
    # Standard core; tsunami provides second AoE since give_all proved weaker.
    ("Kappa", ["possessun", "pharavion", "helipi", "bolt"], {
        "possessun": ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "pharavion": ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "helipi":    ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "bolt":      ["earthquake", "woodsmash", "laser_beam", "tsunami"],
    }),

    # Lambda — forest-fire surge. uprout/nut/potturmeist (hp 456–482); uneye
    # brings the highest raw HP (494) to anchor the team's staying power.
    ("Lambda", ["uprout", "uneye", "nut", "potturmeist"], {
        "uprout":      ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "uneye":       ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "nut":         ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "potturmeist": ["earthquake", "woodsmash", "laser_beam", "tsunami"],
    }),

    # Mu — stone-wall brawlers. cairfrey/chromeye/parappi/stegofor all score ≥ 937.
    # Identical moveset — the competition here is pure HP/stat bulk vs Theta.
    ("Mu", ["cairfrey", "chromeye", "parappi", "stegofor"], {
        "cairfrey":  ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "chromeye":  ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "parappi":   ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "stegofor":  ["earthquake", "woodsmash", "laser_beam", "tsunami"],
    }),

    # Nu — elemental surge. neutrito/dracune/glombroc/sludgehog; all score ≥ 935.
    # sludgehog carries sudden_glow to test whether one healer in the lineup
    # trades better than a straight fourth AoE user.
    ("Nu", ["neutrito", "dracune", "glombroc", "sludgehog"], {
        "neutrito":  ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "dracune":   ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "glombroc":  ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "sludgehog": ["earthquake", "woodsmash", "laser_beam", "sudden_glow"],
    }),

    # Xi — toxic-lightning. pigabyte/gastronium/seirein/hampotamos; all hp ≥ 466.
    # hampotamos carries frostbite as a high-power finisher on frosty angesnow.
    ("Xi", ["pigabyte", "gastronium", "seirein", "hampotamos"], {
        "pigabyte":   ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "gastronium": ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "seirein":    ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "hampotamos": ["earthquake", "woodsmash", "laser_beam", "frostbite"],
    }),

    # Omicron — broad-front. stomic/jelillow/pawsand/potturney; scores 928–930.
    # dreamwalk (cosmic+shadow, 100% acc) on potturney for extra anti-Theta typing.
    ("Omicron", ["stomic", "jelillow", "pawsand", "potturney"], {
        "stomic":    ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "jelillow":  ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "pawsand":   ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "potturney": ["earthquake", "woodsmash", "laser_beam", "dreamwalk"],
    }),

    # Pi — precision elite. Best performers from iteration-3 rebuild; pearamanca
    # (hp 466) and devidra (hp 468) are top-tier. vivipere/angrito round out the
    # ranged-attack depth. All run the full AoE+type core.
    ("Pi", ["pearamanca", "angrito", "devidra", "vivipere"], {
        "pearamanca": ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "angrito":    ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "devidra":    ["earthquake", "woodsmash", "laser_beam", "tsunami"],
        "vivipere":   ["earthquake", "woodsmash", "laser_beam", "tsunami"],
    }),

    # ── Gen-4: counter-teams designed to beat Mu / Iota / Kappa ───────────────
    # Type-coverage analysis against the Gen-3 meta (Mu/Iota/Kappa monster types):
    #   Mu:    cairfrey(normal), chromeye(metal+cosmic), parappi(wood+sky), stegofor(wood)
    #   Iota:  coproblight(earth), burrlock(wood), rinocereed(wood), glomon(earth+water)
    #   Kappa: possessun(shadow), pharavion(water+heroic), helipi(wood+sky), bolt(metal)
    #
    # Attack-type 2x coverage scores vs those 12 monsters:
    #   sky    (ten_thousand_feathers): 8/12 — earth/heroic/wood defenders
    #   earth  (earthquake, AoE):       7/12 — fire/lightning/metal/wood defenders
    #   heroic (give_all):              2/12 — normal/shadow defenders (cairfrey, possessun)
    #   lightning+metal (laser_beam):   6/12 — metal/sky/water/earth/cosmic defenders
    # Combined: earthquake+ten_thousand_feathers+give_all covers ALL 12; laser_beam adds
    # 4x synergy on chromeye (metal+cosmic) and glomon (earth+water).
    #
    # Defensive typing: heroic-type monsters take NEUTRAL from all Gen-3 core moves
    # (earthquake/woodsmash/laser_beam/tsunami). Normal/shadow/venom types have only
    # ONE Gen-3 weakness (woodsmash via heroic→frost/normal/shadow).
    # Monster selection: high HP (≥ 400) + minimal Gen-3 weaknesses.

    # Rho — normal-bulk fortress. All four normal-type (1 Gen-3 weakness: woodsmash).
    # Highest total HP of any Gen-4 team at ~1871. legoplaste/zunna lead on stats.
    ("Rho", ["legoplaste", "zunna", "ruffalo", "caper"], {
        "legoplaste": ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "zunna":      ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "ruffalo":    ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "caper":      ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
    }),

    # Sigma — immune core. sampsack+enduros are pure heroic (0 Gen-3 weaknesses);
    # mystikapi (cosmic) and bumbulus (sky) each have only 1 weakness (laser_beam).
    # Lowest total HP but best defensive profile; tests whether 0-weakness typing
    # compensates for moderate bulk.
    ("Sigma", ["sampsack", "enduros", "mystikapi", "bumbulus"], {
        "sampsack":  ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "enduros":   ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "mystikapi": ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "bumbulus":  ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
    }),

    # Tau — shadow/venom wall. All four have exactly 1 Gen-3 weakness (woodsmash).
    # metoxic anchors with the highest HP in this team (hp ~483); ghosteeth/hoarseshoo
    # round out the shadow-type bulk.
    ("Tau", ["ghosteeth", "hoarseshoo", "hoarse", "metoxic"], {
        "ghosteeth":  ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "hoarseshoo": ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "hoarse":     ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "metoxic":    ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
    }),

    # Upsilon — cosmic fortress. happito/sadito/fuzzlet/fuzzina are metal+cosmic or
    # cosmic+normal (2 Gen-3 weaknesses each) but have HP ≥ 463, total ~1860.
    # Tests whether very high HP compensates for 2 weaknesses.
    ("Upsilon", ["happito", "sadito", "fuzzlet", "fuzzina"], {
        "happito": ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "sadito":  ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "fuzzlet": ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "fuzzina": ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
    }),

    # Phi — wood-wall brawlers. All wood-type (weak to earthquake+woodsmash),
    # but HP ≥ 457; total ~1853. Direct test: pure offensive coverage beats
    # typed weakness at high HP.
    ("Phi", ["baobaraffe", "cacaburr", "sprightly", "narcileaf"], {
        "baobaraffe": ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "cacaburr":   ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "sprightly":  ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "narcileaf":  ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
    }),

    # Chi — mixed-high-HP block. hoodoll(wood+venom), jeluna(water+cosmic),
    # sclairus(wood), gourda(wood); all HP ≥ 460; total ~1862.
    ("Chi", ["hoodoll", "jeluna", "sclairus", "gourda"], {
        "hoodoll": ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "jeluna":  ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "sclairus":["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "gourda":  ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
    }),

    # Psi — shadow/cosmic depth. bricgard(earth+heroic), lendos(shadow+cosmic),
    # boltnu(metal), cocrune(earth+shadow); each 2 weaknesses but HP ≥ 457; total ~1849.
    ("Psi", ["bricgard", "lendos", "boltnu", "cocrune"], {
        "bricgard": ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "lendos":   ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "boltnu":   ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "cocrune":  ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
    }),

    # Omega — mixed high-HP. slichen(wood), yiinaang(shadow+cosmic),
    # bedoo(water), pharfan(water); all HP ≥ 456; total ~1847.
    ("Omega", ["slichen", "yiinaang", "bedoo", "pharfan"], {
        "slichen":  ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "yiinaang": ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "bedoo":    ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
        "pharfan":  ["earthquake", "ten_thousand_feathers", "laser_beam", "give_all"],
    }),
]


def make_designed_teams(level: int) -> list[Team]:
    teams = []
    for entry in DESIGNED_TEAM_DEFS:
        name, slugs = entry[0], entry[1]
        overrides = entry[2] if len(entry) > 2 else {}
        teams.append(Team(name=name, slugs=slugs, level=level,
                          designed=True, tech_overrides=overrides))
    return teams


# ── Monster / technique stat accumulator ──────────────────────────────────────

@dataclass
class Stats:
    """Cross-battle tallies for monsters and techniques."""
    # How many match wins each monster species contributed to (on winning team)
    monster_wins: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    # How many times each species survived to end of a won battle
    monster_survivals: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    # How many times each species appeared on any team
    monster_appearances: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    # Technique uses by winning team in battles they won
    winning_tech_uses: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    # All technique uses
    total_tech_uses: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def record(self, result: BattleResult, npc_a: SimNPC, npc_b: SimNPC) -> None:
        for mon in npc_a.monsters:
            self.monster_appearances[mon.slug] += 1
        for mon in npc_b.monsters:
            self.monster_appearances[mon.slug] += 1

        for _t, user_slug, tech_slug, _tgt, _ok in result.action_log:
            self.total_tech_uses[tech_slug] += 1

        if result.winner is not None:
            winner_slug_set = set(result.winner_monster_slugs)
            for slug in result.winner_monster_slugs:
                self.monster_wins[slug] += 1
            for slug in result.winner_surviving_slugs:
                self.monster_survivals[slug] += 1
            for _t, user_slug, tech_slug, _tgt, _ok in result.action_log:
                if user_slug in winner_slug_set:
                    self.winning_tech_uses[tech_slug] += 1


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_monster_pool() -> list[str]:
    from tuxemon.database.runtime import db
    return list(db.database["monster"].keys())


def build_random_team(pool: list[str], team_size: int, level: int) -> list[Monster]:
    slugs = random.sample(pool, min(team_size, len(pool)))
    team: list[Monster] = []
    for slug in slugs:
        try:
            team.append(Monster.spawn_base(slug, level))
        except Exception as exc:
            logger.debug("Skipping %s: %s", slug, exc)
    return team


def _bar(n: int, total: int, width: int = 20) -> str:
    filled = round(n / total * width) if total else 0
    return "█" * filled + "░" * (width - filled)


# ── Gauntlet mode ──────────────────────────────────────────────────────────────

def simulate(num_battles: int, team_size: int, level: int, is_double: bool = False) -> None:
    _ensure_routing_policy()
    pool = get_monster_pool()
    fmt = "Double" if is_double else "Single"

    print(f"Gauntlet [{fmt}]: {num_battles} battles | team_size={team_size} | "
          f"level={level} | pool={len(pool)} species\n")

    wins_a = wins_b = draws = errors = 0
    total_turns = 0
    stats = Stats()

    for i in range(num_battles):
        team_a = build_random_team(pool, team_size, level)
        team_b = build_random_team(pool, team_size, level)
        if not team_a or not team_b:
            errors += 1
            continue

        npc_a = SimNPC("Alpha", team_a)
        npc_b = SimNPC("Beta", team_b)

        try:
            result = run_battle(npc_a, npc_b, is_double=is_double)
        except Exception:
            logger.exception("Battle %d crashed", i + 1)
            errors += 1
            continue

        total_turns += result.turns
        stats.record(result, npc_a, npc_b)

        if result.winner is npc_a:
            wins_a += 1
        elif result.winner is npc_b:
            wins_b += 1
        else:
            draws += 1

        if (i + 1) % max(1, num_battles // 10) == 0:
            print(f"  {i+1:>{len(str(num_battles))}}/{num_battles}  "
                  f"({(i+1)/num_battles*100:.0f}%)")

    completed = num_battles - errors
    print(f"\n{'─'*52}")
    print(f"Completed : {completed}/{num_battles}   Errors: {errors}")
    if not completed:
        return
    print(f"Alpha wins: {wins_a:>5}  ({wins_a/completed*100:5.1f}%)")
    print(f"Beta  wins: {wins_b:>5}  ({wins_b/completed*100:5.1f}%)")
    print(f"Draws     : {draws:>5}  ({draws/completed*100:5.1f}%)")
    print(f"Avg turns : {total_turns/completed:.1f}")

    _print_stats(stats, top_n=15)


# ── Tournament mode ─────────────────────────────────────────────────────────────

def _build_teams(
    num_teams: int, team_size: int, level: int, pool: list[str],
    reserved_slugs: set[str] | None = None,
    name_offset: int = 0,
) -> list[Team]:
    teams: list[Team] = []
    used_slugs: set[str] = set(reserved_slugs or [])
    while len(teams) < num_teams:
        available = [s for s in pool if s not in used_slugs]
        if len(available) < team_size:
            used_slugs = set(reserved_slugs or [])
            available = [s for s in pool if s not in used_slugs]
        sample = random.sample(available, team_size)
        used_slugs.update(sample)
        name = f"Team {len(teams) + 1 + name_offset:02d}"
        teams.append(Team(name=name, slugs=sample, level=level))
    return teams


def _run_bracket(
    teams: list[Team], is_double: bool, stats: Stats, verbose: bool = True
) -> tuple[Team, Team | None, Team | None]:
    """Run one single-elimination bracket. Returns (champion, runner_up, third).
    Resets wins/losses on each team before starting."""
    for t in teams:
        t.wins = 0
        t.losses = 0

    bracket = list(teams)
    random.shuffle(bracket)
    round_num = 0
    losers_r2: list[Team] = []
    final_loser: Team | None = None

    while len(bracket) > 1:
        round_num += 1
        if len(bracket) == 2:
            round_label = "Final"
        elif len(bracket) == 4:
            round_label = "Semi-finals"
            losers_r2 = []
        else:
            round_label = f"Round {round_num}"

        if verbose:
            print(f"── {round_label} {'─'*(44-len(round_label))}")

        next_bracket: list[Team] = []
        semi_losers: list[Team] = []

        for i in range(0, len(bracket), 2):
            team_a, team_b = bracket[i], bracket[i + 1]
            npc_a = team_a.make_npc()
            npc_b = team_b.make_npc()

            try:
                result = run_battle(npc_a, npc_b, is_double=is_double)
                stats.record(result, npc_a, npc_b)
            except Exception:
                logger.exception("Match %s vs %s crashed", team_a.name, team_b.name)
                result = BattleResult(winner=None, loser=None, turns=0, action_log=[])

            if result.winner is npc_a:
                winner_team, loser_team = team_a, team_b
            elif result.winner is npc_b:
                winner_team, loser_team = team_b, team_a
            else:
                hp_a = sum(m.current_hp for m in npc_a.monsters)
                hp_b = sum(m.current_hp for m in npc_b.monsters)
                winner_team, loser_team = (team_a, team_b) if hp_a >= hp_b else (team_b, team_a)

            winner_team.wins += 1
            loser_team.losses += 1
            next_bracket.append(winner_team)
            semi_losers.append(loser_team)

            if verbose:
                outcome = "draw→" if result.winner is None else "def "
                print(f"  {winner_team.name:<12} {outcome}  {loser_team.name:<12}"
                      f"  ({result.turns} turns)")

        if len(bracket) == 4:
            losers_r2 = semi_losers
        if len(bracket) == 2:
            final_loser = semi_losers[0] if semi_losers else None
        bracket = next_bracket
        if verbose:
            print()

    champion = bracket[0]
    runner_up = final_loser

    # 3rd place match
    third: Team | None = None
    if len(losers_r2) == 2:
        if verbose:
            print("── 3rd Place ────────────────────────────────────")
        team_c, team_d = losers_r2
        npc_c = team_c.make_npc()
        npc_d = team_d.make_npc()
        try:
            result3 = run_battle(npc_c, npc_d, is_double=is_double)
            stats.record(result3, npc_c, npc_d)
        except Exception:
            logger.exception("3rd-place match crashed")
            result3 = BattleResult(winner=None, loser=None, turns=0, action_log=[])

        if result3.winner is npc_c:
            third = team_c
        elif result3.winner is npc_d:
            third = team_d
        else:
            hp_c = sum(m.current_hp for m in npc_c.monsters)
            hp_d = sum(m.current_hp for m in npc_d.monsters)
            third = team_c if hp_c >= hp_d else team_d

        if verbose:
            outcome3 = "draw→" if result3.winner is None else "def "
            other = team_d if third is team_c else team_c
            print(f"  {third.name:<12} {outcome3}  {other.name:<12}"
                  f"  ({result3.turns} turns)\n")

    return champion, runner_up, third


def run_tournament(
    num_teams: int, team_size: int, level: int,
    is_double: bool = False, repeats: int = 1, seed: int | None = None,
    include_designed: bool = False,
) -> None:
    _ensure_routing_policy()
    pool = get_monster_pool()
    fmt = "Double" if is_double else "Single"

    bracket_size = 2 ** math.ceil(math.log2(max(num_teams, 2)))
    if bracket_size != num_teams:
        print(f"Rounding up to {bracket_size} teams (next power of 2).")
        num_teams = bracket_size

    designed_label = " +4 designed" if include_designed else ""
    print(f"Tournament [{fmt}]: {num_teams} teams | team_size={team_size} | "
          f"level={level} | repeats={repeats}{designed_label} | pool={len(pool)} species\n")

    # Seed only the team-building RNG so the same squads appear every repeat.
    if seed is not None:
        random.seed(seed)

    if include_designed:
        designed = make_designed_teams(level)
        reserved = {slug for t in designed for slug in t.slugs}
        random_slots = num_teams - len(designed)
        random_teams = _build_teams(random_slots, team_size, level, pool,
                                    reserved_slugs=reserved,
                                    name_offset=len(designed))
        teams = designed + random_teams
    else:
        teams = _build_teams(num_teams, team_size, level, pool)

    # From here on, battle RNG is free to vary across repeats.
    if seed is not None:
        random.seed(None)

    # Print team rosters once so we can refer to them by number later.
    if repeats > 1:
        print("── Teams ────────────────────────────────────────────")
        for t in teams:
            marker = "★ " if t.designed else "  "
            print(f" {marker}{t.name:<12}  {t.roster()}")
        print()

    stats = Stats()
    # championship_counts[team.name] = [1st_count, 2nd_count, 3rd_count]
    championship_counts: dict[str, list[int]] = {t.name: [0, 0, 0] for t in teams}
    verbose_bracket = repeats == 1

    for run_i in range(repeats):
        if repeats > 1:
            print(f"── Run {run_i + 1}/{repeats} {'─'*(40-len(str(run_i+1)+str(repeats)))}")
        champion, runner_up, third = _run_bracket(teams, is_double, stats, verbose=verbose_bracket)

        championship_counts[champion.name][0] += 1
        if runner_up:
            championship_counts[runner_up.name][1] += 1
        if third:
            championship_counts[third.name][2] += 1

        if repeats > 1:
            ru_str = f"  2nd {runner_up.name}" if runner_up else ""
            th_str = f"  3rd {third.name}" if third else ""
            print(f"  1st {champion.name}{ru_str}{th_str}")
            print(f"      {champion.roster()}\n")

    # ── Podium (single run) or leaderboard (multi-run) ────────────────────────
    if repeats == 1:
        champion, runner_up, third = (
            max(teams, key=lambda t: t.wins),
            None, None,
        )
        # Re-derive from championship_counts (already set above for run 1)
        champ_name = max(championship_counts, key=lambda n: championship_counts[n][0])
        champion = next(t for t in teams if t.name == champ_name)
        non_champ = [t for t in teams if t is not champion]
        non_champ.sort(key=lambda t: (-t.wins, t.losses))
        runner_up = non_champ[0] if non_champ else None

        print("── Podium ───────────────────────────────────────────")
        medals = ["1st", "2nd", "3rd"]
        podium = [t for t in [champion, runner_up, third] if t is not None]
        for medal, team in zip(medals, podium[:3]):
            print(f"  {medal}  {team.name}  ({team.wins}W-{team.losses}L)")
            print(f"       {team.roster()}")
        print()
    else:
        print("── Championship leaderboard ─────────────────────────")
        ranked = sorted(
            championship_counts.items(),
            key=lambda kv: (-kv[1][0], -kv[1][1], -kv[1][2]),
        )
        print(f"  {'Team':<14}  {'1st':>4}  {'2nd':>4}  {'3rd':>4}  Roster")
        for name, (g, s, b) in ranked:
            if g + s + b == 0:
                continue
            team = next(t for t in teams if t.name == name)
            marker = "★ " if team.designed else "  "
            print(f" {marker}{name:<12}  {g:>4}  {s:>4}  {b:>4}  {team.roster()}")
        print()

        # Designed vs random summary
        if include_designed:
            d_wins = sum(championship_counts[t.name][0] for t in teams if t.designed)
            r_wins = sum(championship_counts[t.name][0] for t in teams if not t.designed)
            d_teams = sum(1 for t in teams if t.designed)
            r_teams = sum(1 for t in teams if not t.designed)
            print(f"── Designed vs random (out of {repeats} runs) ─────────────")
            print(f"  Designed ({d_teams} teams): {d_wins} wins  "
                  f"({d_wins/repeats*100:.0f}% of tournaments)")
            print(f"  Random   ({r_teams} teams): {r_wins} wins  "
                  f"({r_wins/repeats*100:.0f}% of tournaments)")
            expected_pct = d_teams / len(teams) * 100
            print(f"  (Expected if equal: {expected_pct:.0f}% for designed)\n")

    _print_stats(stats, top_n=10)


# ── Duel mode: designed teams head-to-head vs a named opponent ────────────────

def run_duel(
    target_name: str, level: int, num_battles: int,
    team_size: int, is_double: bool = False,
) -> None:
    """Run each designed team against `target_name` for num_battles matches."""
    _ensure_routing_policy()
    designed = make_designed_teams(level)

    target = next((t for t in designed if t.name.lower() == target_name.lower()), None)
    if target is None:
        names = [t.name for t in designed]
        print(f"Unknown target '{target_name}'. Known teams: {', '.join(names)}")
        return

    challengers = [t for t in designed if t is not target]
    fmt = "Double" if is_double else "Single"
    print(f"Duel [{fmt}]: each designed team vs {target.name}  "
          f"({num_battles} battles each, level {level})\n")
    print(f"  {'Team':<14}  {'W':>4}  {'L':>4}  {'D':>4}  {'Win%':>6}")
    print(f"  {'─'*14}  {'─'*4}  {'─'*4}  {'─'*4}  {'─'*6}")

    for challenger in challengers:
        wins = losses = draws = 0
        for _ in range(num_battles):
            npc_c = challenger.make_npc()
            npc_t = target.make_npc()
            try:
                result = run_battle(npc_c, npc_t, is_double=is_double)
            except Exception:
                logger.exception("Duel %s vs %s crashed", challenger.name, target.name)
                continue
            if result.winner is npc_c:
                wins += 1
            elif result.winner is npc_t:
                losses += 1
            else:
                draws += 1
        total = wins + losses + draws
        pct = wins / total * 100 if total else 0
        marker = "★ " if challenger.designed else "  "
        print(f" {marker}{challenger.name:<12}  {wins:>4}  {losses:>4}  {draws:>4}  {pct:>5.1f}%")
    print()


# ── Learning AI: REINFORCE on move-scoring weights ────────────────────────────

# Lazy caches — populated on first access, reused for the rest of the session.
_learn_tech_cache: dict[str, "Technique | None"] = {}
_learn_mon_type_cache: dict[str, list] = {}


def _cached_technique(slug: str) -> "Technique | None":
    if slug not in _learn_tech_cache:
        try:
            _learn_tech_cache[slug] = Technique.create(slug)
        except Exception:
            _learn_tech_cache[slug] = None  # type: ignore[assignment]
    return _learn_tech_cache[slug]


def _cached_mon_types(slug: str) -> list:
    if slug not in _learn_mon_type_cache:
        try:
            mon = Monster.spawn_base(slug, 1)
            _learn_mon_type_cache[slug] = mon.types.current
        except Exception:
            _learn_mon_type_cache[slug] = []
    return _learn_mon_type_cache[slug]


def _action_features(tech_slug: str, target_slug: str) -> dict[str, float]:
    """Compute the 4-feature vector for a (technique, target) action."""
    from tuxemon.database.runtime import db
    from tuxemon.formula import simple_damage_multiplier
    from tuxemon.platform.const.sizes import POWER_RANGE

    tech = _cached_technique(tech_slug)
    if tech is None:
        return {"type_mult": 1.0, "power": 0.0, "accuracy": 0.0, "is_aoe": 0.0}

    target_types = _cached_mon_types(target_slug)
    type_mult = (
        simple_damage_multiplier(tech.types.current, target_types)
        if target_types else 1.0
    )
    tech_data = db.database["technique"].get(tech_slug)
    is_aoe = 1.0 if (tech_data and tech_data.target and tech_data.target.enemy_team) else 0.0

    return {
        "type_mult": type_mult,
        "power": (tech.power or 0.0) / POWER_RANGE[1],
        "accuracy": tech.accuracy or 0.0,
        "is_aoe": is_aoe,
    }


_FEAT_KEYS = ("type_mult", "power", "accuracy", "is_aoe")
_FEAT_ATTRS = {"type_mult": "w_type", "power": "w_power", "accuracy": "w_acc", "is_aoe": "w_aoe"}


@dataclass
class PolicyWeights:
    w_type: float = 1.0    # type-effectiveness multiplier weight
    w_power: float = 1.0   # normalised move power weight
    w_acc: float = 1.0     # accuracy weight
    w_aoe: float = 1.0     # AoE (enemy_team) bonus weight
    lr: float = 0.05

    def inject(self) -> None:
        """Write current weights into the AIConfigLoader cache under 'sim_trainer'."""
        from tuxemon.ai.ai import AIConfigLoader, SingleTechnique
        ai_techs = AIConfigLoader.get_ai_techniques("ai_techniques.yaml")
        ai_techs.techniques["sim_trainer"] = SingleTechnique(
            elemental_multiplier_weight=self.w_type,
            power_weight=self.w_power,
            accuracy_weight=self.w_acc,
        )

    def update(
        self,
        action_log: list[ActionEntry],
        policy_mon_slugs: set[str],
        outcome: float,
    ) -> None:
        """REINFORCE update on the policy's own actions (+1 win, -1 loss, 0 draw)."""
        if outcome == 0.0 or not policy_mon_slugs:
            return
        feats_used: list[dict[str, float]] = [
            _action_features(tech_slug, target_slug)
            for _t, user_slug, tech_slug, target_slug, _ok in action_log
            if user_slug in policy_mon_slugs
        ]
        if not feats_used:
            return
        n = len(feats_used)
        for fkey in _FEAT_KEYS:
            avg = sum(d[fkey] for d in feats_used) / n
            attr = _FEAT_ATTRS[fkey]
            setattr(self, attr, max(0.001, getattr(self, attr) + self.lr * outcome * avg))

    def label(self) -> str:
        return (f"type={self.w_type:.3f}  power={self.w_power:.3f}  "
                f"acc={self.w_acc:.3f}  aoe={self.w_aoe:.3f}")


@dataclass
class SwitchPolicy:
    """Learned weights for choosing which bench monster to send in on a faint."""
    w_type_adv: float = 1.0   # how super-effective our types are vs active enemies
    w_type_res: float = 1.0   # how resistant we are to active enemy types
    w_hp: float = 1.0         # HP fraction of the candidate monster
    lr: float = 0.05
    switch_log: list[dict[str, float]] = field(default_factory=list)

    def _features(self, mon: "Monster", opponents: list["Monster"]) -> dict[str, float]:
        from tuxemon.formula import simple_damage_multiplier
        if not opponents:
            return {"type_adv": 1.0, "type_res": 1.0, "hp": mon.hp_ratio}

        my_moves = mon.moves.get_moves()

        # type_adv: best technique-type matchup from our moveset vs each opponent's body type
        type_adv = sum(
            max(
                (simple_damage_multiplier(move.types.current, opp.types.current)
                 for move in my_moves),
                default=1.0,
            )
            for opp in opponents
        ) / len(opponents)

        # type_res: worst move-type matchup from each opponent's moveset hitting our body type
        # (inverse: higher = we resist more)
        type_res = sum(
            1.0 / max(
                0.01,
                max(
                    (simple_damage_multiplier(move.types.current, mon.types.current)
                     for move in opp.moves.get_moves()),
                    default=1.0,
                ),
            )
            for opp in opponents
        ) / len(opponents)

        return {"type_adv": type_adv, "type_res": type_res, "hp": mon.hp_ratio}

    def score(self, mon: "Monster", opponents: list["Monster"]) -> float:
        f = self._features(mon, opponents)
        return self.w_type_adv * f["type_adv"] + self.w_type_res * f["type_res"] + self.w_hp * f["hp"]

    def record(self, mon: "Monster", opponents: list["Monster"]) -> None:
        self.switch_log.append(self._features(mon, opponents))

    def update(self, outcome: float) -> None:
        if outcome == 0.0 or not self.switch_log:
            return
        n = len(self.switch_log)
        for key, attr in (("type_adv", "w_type_adv"), ("type_res", "w_type_res"), ("hp", "w_hp")):
            avg = sum(d[key] for d in self.switch_log) / n
            setattr(self, attr, max(0.001, getattr(self, attr) + self.lr * outcome * avg))

    def label(self) -> str:
        return f"adv={self.w_type_adv:.3f}  res={self.w_type_res:.3f}  hp={self.w_hp:.3f}"


class LearningAIManager(AIManager):
    """Drop-in replacement for AIManager that uses a SwitchPolicy for replacements."""

    def __init__(self, session: "Any", switch_policy: SwitchPolicy) -> None:
        super().__init__(session)
        self.switch_policy = switch_policy

    def choose_replacement_monster(self, character: SimNPC) -> "Monster | None":
        c_session = self.session.client.combat_session
        available = c_session.get_bench(character)
        if not available:
            return None

        opponents: list["Monster"] = (
            c_session.field_monsters.get_monsters(c_session.right_player)
            if character is c_session.left_player
            else c_session.field_monsters.get_monsters(c_session.left_player)
        )

        # Only apply the learned policy when there is a real choice to make
        if character.slug == "sim_trainer" and len(available) > 1:
            best = max(available, key=lambda m: self.switch_policy.score(m, opponents))
            self.switch_policy.record(best, opponents)
            return best

        return super().choose_replacement_monster(character)


def run_learn(
    n_battles: int, eval_every: int, eval_battles: int,
    team_size: int, level: int, is_double: bool = False,
    lr: float = 0.05,
) -> None:
    """
    Train move-selection and switch-selection policies simultaneously via REINFORCE.

    Side A (sim_trainer) uses both learned policies; Side B (rng_trainer) uses
    random move selection and picks the healthiest available bench monster.
    After each battle both weight vectors are nudged based on the outcome.
    """
    _ensure_routing_policy()
    pool = get_monster_pool()
    fmt = "Double" if is_double else "Single"

    print(f"Learn [{fmt}]: {n_battles} training battles | "
          f"eval every {eval_every} | team_size={team_size} | level={level} | lr={lr}")
    print("  Policy vs Random — REINFORCE on move weights (4) + switch weights (3)\n")
    print(f"  {'Battle':>8}  {'Win%':>6}  "
          f"{'── Move ──────────────────────────────':38}  "
          f"── Switch ───────────────────────────")
    print(f"  {'─'*8}  {'─'*6}  {'─'*38}  {'─'*38}")

    move_policy = PolicyWeights(lr=lr)
    switch_policy = SwitchPolicy(lr=lr)
    move_policy.inject()
    ai_factory = lambda s: LearningAIManager(s, switch_policy)

    eval_history: list[tuple[int, float]] = []

    for i in range(1, n_battles + 1):
        team_a = build_random_team(pool, team_size, level)
        team_b = build_random_team(pool, team_size, level)
        if not team_a or not team_b:
            continue

        npc_a = SimNPC("PolicySide", team_a, slug="sim_trainer")
        npc_b = SimNPC("RandomSide", team_b, slug="rng_trainer")
        policy_slugs = {m.slug for m in npc_a.monsters}
        switch_policy.switch_log.clear()

        try:
            result = run_battle(npc_a, npc_b, is_double=is_double, ai_factory=ai_factory)
        except Exception:
            continue

        outcome = +1.0 if result.winner is npc_a else (-1.0 if result.winner is npc_b else 0.0)
        move_policy.update(result.action_log, policy_slugs, outcome)
        switch_policy.update(outcome)
        move_policy.inject()

        if i % eval_every == 0:
            ew = et = 0
            for _ in range(eval_battles):
                ta = build_random_team(pool, team_size, level)
                tb = build_random_team(pool, team_size, level)
                if not ta or not tb:
                    continue
                na = SimNPC("EvalPolicy", ta, slug="sim_trainer")
                nb = SimNPC("EvalRandom", tb, slug="rng_trainer")
                sp_eval = SwitchPolicy(
                    w_type_adv=switch_policy.w_type_adv,
                    w_type_res=switch_policy.w_type_res,
                    w_hp=switch_policy.w_hp,
                )
                try:
                    r = run_battle(na, nb, is_double=is_double,
                                   ai_factory=lambda s, sp=sp_eval: LearningAIManager(s, sp))
                except Exception:
                    continue
                if r.winner is na:
                    ew += 1
                et += 1
            win_pct = ew / et * 100 if et else 0.0
            eval_history.append((i, win_pct))
            print(f"  {i:>8}  {win_pct:>5.1f}%  "
                  f"{move_policy.label():<38}  {switch_policy.label()}")

    # ── Final report ───────────────────────────────────────────────────────────
    print(f"\n── Final move weights ───────────────────────────────")
    move_ranked = sorted(
        [("type effectiveness", move_policy.w_type), ("move power", move_policy.w_power),
         ("accuracy", move_policy.w_acc), ("AoE bonus", move_policy.w_aoe)],
        key=lambda x: -x[1],
    )
    mmax = move_ranked[0][1] if move_ranked else 1.0
    for name, w in move_ranked:
        bar = _bar(int(w * 100), max(1, int(mmax * 100)))
        print(f"    {name:<22}  {bar}  {w:.3f}")

    print(f"\n── Final switch weights ─────────────────────────────")
    sw_ranked = sorted(
        [("type advantage",  switch_policy.w_type_adv),
         ("type resistance", switch_policy.w_type_res),
         ("HP fraction",     switch_policy.w_hp)],
        key=lambda x: -x[1],
    )
    smax = sw_ranked[0][1] if sw_ranked else 1.0
    for name, w in sw_ranked:
        bar = _bar(int(w * 100), max(1, int(smax * 100)))
        print(f"    {name:<22}  {bar}  {w:.3f}")

    if len(eval_history) > 1:
        print(f"\n── Win% vs random over training ─────────────────────")
        for battle_n, pct in eval_history:
            bar = _bar(int(pct), 100, width=30)
            print(f"    {battle_n:>6} battles  {bar}  {pct:.1f}%")
    print()


# ── Evolutionary / genetic team-building AI ──────────────────────────────────

def _load_tech_pool(min_power: float = 2.0, min_acc: float = 0.6) -> list[str]:
    """Return slugs of damage techniques that meet power/accuracy thresholds."""
    from tuxemon.database.runtime import db
    from tuxemon.db import TechSort
    result: list[str] = []
    for slug, data in db.database["technique"].items():
        if data.sort != TechSort.damage:
            continue
        if (data.power or 0.0) >= min_power and (data.accuracy or 0.0) >= min_acc:
            result.append(slug)
    return result


@dataclass
class EvoTeam:
    name: str
    slugs: list[str]
    tech_overrides: dict[str, list[str]]
    wins: int = 0
    losses: int = 0

    def win_rate(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total else 0.0

    def to_team(self, level: int) -> Team:
        return Team(
            name=self.name, slugs=list(self.slugs), level=level,
            designed=False,
            tech_overrides={k: list(v) for k, v in self.tech_overrides.items()},
        )

    def copy(self, new_name: str | None = None) -> "EvoTeam":
        return EvoTeam(
            name=new_name or self.name,
            slugs=list(self.slugs),
            tech_overrides={k: list(v) for k, v in self.tech_overrides.items()},
            wins=self.wins,
            losses=self.losses,
        )


def _evo_random_team(
    pool: list[str], tech_pool: list[str], team_size: int, name: str,
) -> EvoTeam:
    slugs = random.sample(pool, min(team_size, len(pool)))
    overrides: dict[str, list[str]] = {}
    if len(tech_pool) >= 4:
        for slug in slugs:
            overrides[slug] = random.sample(tech_pool, 4)
    return EvoTeam(name=name, slugs=slugs, tech_overrides=overrides)


def _evo_mutate(
    evo: EvoTeam, pool: list[str], tech_pool: list[str],
    mutation_rate: float = 0.25,
) -> EvoTeam:
    slugs = list(evo.slugs)
    overrides = {k: list(v) for k, v in evo.tech_overrides.items()}

    # Maybe swap a monster
    for i in range(len(slugs)):
        if random.random() < mutation_rate:
            available = [s for s in pool if s not in slugs]
            if available:
                old = slugs[i]
                slugs[i] = random.choice(available)
                overrides.pop(old, None)
                if len(tech_pool) >= 4:
                    overrides[slugs[i]] = random.sample(tech_pool, 4)

    # Maybe swap a move slot
    if len(tech_pool) >= 4:
        for slug in slugs:
            if slug in overrides:
                moves = overrides[slug]
                for j in range(len(moves)):
                    if random.random() < mutation_rate:
                        moves[j] = random.choice(tech_pool)

    return EvoTeam(name=evo.name, slugs=slugs, tech_overrides=overrides)


def _evo_crossover(a: EvoTeam, b: EvoTeam, name: str) -> EvoTeam:
    """Single-point crossover on roster; move-level crossover for shared slots."""
    n = len(a.slugs)
    point = random.randint(1, max(1, n - 1))
    new_slugs = a.slugs[:point] + b.slugs[point:]

    # Deduplicate while preserving order
    seen: set[str] = set()
    candidates = b.slugs + a.slugs  # prefer b's slugs for replacements
    for i, slug in enumerate(new_slugs):
        if slug in seen:
            replacement = next((s for s in candidates if s not in seen), slug)
            new_slugs[i] = replacement
        seen.add(new_slugs[i])

    # Build overrides with move-level crossover where both parents have the slug
    overrides: dict[str, list[str]] = {}
    for slug in new_slugs:
        moves_a = a.tech_overrides.get(slug)
        moves_b = b.tech_overrides.get(slug)
        if moves_a and moves_b:
            overrides[slug] = [
                random.choice([moves_a[i], moves_b[i]]) for i in range(len(moves_a))
            ]
        elif moves_a:
            overrides[slug] = list(moves_a)
        elif moves_b:
            overrides[slug] = list(moves_b)

    return EvoTeam(name=name, slugs=new_slugs, tech_overrides=overrides)


def run_evo(
    generations: int, population_size: int, battles_per_eval: int,
    team_size: int, level: int, is_double: bool = False,
) -> None:
    _ensure_routing_policy()
    pool = get_monster_pool()
    tech_pool = _load_tech_pool()
    fmt = "Double" if is_double else "Single"

    print(f"Evo [{fmt}]: {generations} gens | pop={population_size} | "
          f"eval={battles_per_eval} battles/team | team_size={team_size} | level={level}")
    print(f"  Monster pool: {len(pool)} species | Technique pool: {len(tech_pool)} moves\n")

    if len(tech_pool) < 4:
        print("Error: technique pool is too small; check min_power/min_acc thresholds.")
        return

    population: list[EvoTeam] = [
        _evo_random_team(pool, tech_pool, team_size, f"G0-{i+1:02d}")
        for i in range(population_size)
    ]

    elite_count = max(2, population_size // 4)
    best_ever: EvoTeam | None = None

    for gen in range(1, generations + 1):
        for evo in population:
            evo.wins = 0
            evo.losses = 0

        # Evaluate: each team plays battles_per_eval battles against random opponents
        others = {id(evo): [e for e in population if e is not evo] for evo in population}
        for evo in population:
            for _ in range(battles_per_eval):
                opp = random.choice(others[id(evo)])
                npc_a = evo.to_team(level).make_npc()
                npc_b = opp.to_team(level).make_npc()
                try:
                    result = run_battle(npc_a, npc_b, is_double=is_double)
                except Exception:
                    continue
                if result.winner is npc_a:
                    evo.wins += 1
                elif result.winner is npc_b:
                    evo.losses += 1

        population.sort(key=lambda e: -e.win_rate())
        best = population[0]
        avg_wr = sum(e.win_rate() for e in population) / len(population)

        if best_ever is None or best.win_rate() > best_ever.win_rate():
            best_ever = best.copy(best.name)

        roster_preview = " ".join(best.slugs[:3]) + ("…" if len(best.slugs) > 3 else "")
        print(f"Gen {gen:>3}/{generations}  best {best.win_rate()*100:5.1f}%  "
              f"avg {avg_wr*100:5.1f}%  [{best.name}]  {roster_preview}")

        # Carry elites into next generation; fill rest with crossover + mutation
        elites = [population[i].copy(f"G{gen}-E{i+1:02d}") for i in range(elite_count)]
        next_pop: list[EvoTeam] = list(elites)
        child_idx = 1
        while len(next_pop) < population_size:
            pa, pb = random.sample(elites, 2)
            child = _evo_crossover(pa, pb, f"G{gen}-C{child_idx:02d}")
            child = _evo_mutate(child, pool, tech_pool)
            next_pop.append(child)
            child_idx += 1
        population = next_pop

    # ── Champion report ────────────────────────────────────────────────────────
    champion = best_ever or population[0]
    print(f"\n── Champion ─────────────────────────────────────────")
    print(f"  {champion.name}  (win rate {champion.win_rate()*100:.1f}%)")
    print(f"  Monsters: {' '.join(champion.slugs)}")
    print("  Discovered moveset:")
    for slug in champion.slugs:
        moves = champion.tech_overrides.get(slug, ["(natural)"])
        print(f"    {slug:<30}  {', '.join(moves)}")

    # Benchmark champion vs all designed teams
    designed = make_designed_teams(level)
    print(f"\n── Champion vs designed teams ({battles_per_eval} battles each) ─")
    champ_team = champion.to_team(level)
    champ_team.name = "Champion"
    print(f"  {'Opponent':<14}  {'W':>4}  {'L':>4}  {'D':>4}  {'Win%':>6}")
    print(f"  {'─'*14}  {'─'*4}  {'─'*4}  {'─'*4}  {'─'*6}")
    for opp in designed:
        w = l = d = 0
        for _ in range(battles_per_eval):
            npc_c = champ_team.make_npc()
            npc_o = opp.make_npc()
            try:
                result = run_battle(npc_c, npc_o, is_double=is_double)
            except Exception:
                continue
            if result.winner is npc_c:
                w += 1
            elif result.winner is npc_o:
                l += 1
            else:
                d += 1
        total = w + l + d
        pct = w / total * 100 if total else 0
        print(f"  {opp.name:<14}  {w:>4}  {l:>4}  {d:>4}  {pct:>5.1f}%")
    print()


# ── Shared stats printer ───────────────────────────────────────────────────────

def _print_stats(stats: Stats, top_n: int = 15) -> None:
    # ── Top monsters by win rate ──────────────────────────────────────────────
    # Only show monsters with at least 3 appearances to filter noise.
    candidates = {
        slug: (stats.monster_wins[slug], stats.monster_appearances[slug])
        for slug in stats.monster_appearances
        if stats.monster_appearances[slug] >= 3
    }
    if candidates:
        by_winrate = sorted(
            candidates.items(),
            key=lambda kv: -(kv[1][0] / kv[1][1]),
        )[:top_n]
        total_battles = max(sum(stats.monster_appearances.values()) // 2, 1)
        print(f"── Top monsters (win rate, min 3 appearances) {'─'*8}")
        for slug, (wins, apps) in by_winrate:
            rate = wins / apps
            survived = stats.monster_survivals.get(slug, 0)
            print(f"  {slug:<30} {rate*100:5.1f}% wins  "
                  f"survived {survived}/{wins} won battles")
        print()

    # ── Top techniques used by winning teams ─────────────────────────────────
    if stats.winning_tech_uses:
        total_winning = sum(stats.winning_tech_uses.values())
        by_uses = sorted(stats.winning_tech_uses.items(), key=lambda kv: -kv[1])[:top_n]
        print(f"── Top techniques from winning teams {'─'*16}")
        for tech, count in by_uses:
            total = stats.total_tech_uses.get(tech, count)
            win_share = count / total if total else 0
            bar = _bar(count, by_uses[0][1])
            print(f"  {tech:<30} {bar}  {count:>5} uses  {win_share*100:.0f}% from winners")
        print()


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tuxemon headless AI-vs-AI battle simulator"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--tournament", type=int, metavar="TEAMS",
        help="Tournament: single-elimination with TEAMS entries (rounded to power of 2)",
    )
    mode.add_argument(
        "--duel", type=str, metavar="TEAM",
        help="Duel: run each designed team vs TEAM for -n battles each",
    )
    mode.add_argument(
        "--evo", type=int, metavar="GENS",
        help="Evo: run genetic algorithm for GENS generations to discover optimal teams",
    )
    mode.add_argument(
        "--learn", type=int, metavar="N",
        help="Learn: train a move-scoring policy via REINFORCE for N battles",
    )
    parser.add_argument(
        "-n", "--battles", type=int, default=20,
        metavar="N",
        help="Gauntlet battles or duel matches per challenger (default: 20)",
    )
    parser.add_argument(
        "--pop", type=int, default=20, metavar="N",
        help="Evo population size (default: 20)",
    )
    parser.add_argument(
        "--eval-battles", type=int, default=10, metavar="N",
        help="Evo/Learn battles per eval checkpoint (default: 10)",
    )
    parser.add_argument(
        "--eval-every", type=int, default=50, metavar="N",
        help="Learn: evaluate policy every N training battles (default: 50)",
    )
    parser.add_argument(
        "--lr", type=float, default=0.05, metavar="F",
        help="Learn: learning rate for REINFORCE weight updates (default: 0.05)",
    )
    parser.add_argument("-s", "--team-size", type=int, default=None,
                        help="Monsters per team (default: 3 singles, 4 doubles)")
    parser.add_argument("-l", "--level", type=int, default=25)
    parser.add_argument("-d", "--doubles", action="store_true",
                        help="Run as double battles (2 monsters active per side)")
    parser.add_argument("-r", "--repeat", type=int, default=1, metavar="N",
                        help="Re-run the same bracket N times (tournament only)")
    parser.add_argument("--seed", type=int, default=None,
                        help="RNG seed for reproducible team generation")
    parser.add_argument("--designed", action="store_true",
                        help="Inject 4 hand-crafted competitive teams into the bracket")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    # Default team size: 4 for doubles (2 active + 2 bench), 3 for singles.
    team_size = args.team_size if args.team_size is not None else (4 if args.doubles else 3)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.tournament:
        run_tournament(args.tournament, team_size, args.level,
                       is_double=args.doubles, repeats=args.repeat, seed=args.seed,
                       include_designed=args.designed)
    elif args.duel:
        run_duel(args.duel, args.level, args.battles, team_size,
                 is_double=args.doubles)
    elif args.evo:
        run_evo(args.evo, args.pop, args.eval_battles, team_size, args.level,
                is_double=args.doubles)
    elif args.learn:
        run_learn(args.learn, args.eval_every, args.eval_battles, team_size,
                  args.level, is_double=args.doubles, lr=args.lr)
    else:
        simulate(args.battles, team_size, args.level, is_double=args.doubles)


if __name__ == "__main__":
    main()
