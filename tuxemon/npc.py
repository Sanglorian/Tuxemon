# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING
from uuid import UUID

from tuxemon.boxes import ItemBoxes, MonsterBoxes
from tuxemon.database.runtime import db
from tuxemon.db import DialogueProfile, NpcModel
from tuxemon.entity import Entity
from tuxemon.entity_dir.bag import BagHandler
from tuxemon.entity_dir.battle import BattlesHandler
from tuxemon.entity_dir.party import PartyHandler
from tuxemon.entity_dir.path import PathController
from tuxemon.entity_dir.routing import RoutingPolicy
from tuxemon.entity_dir.steps import StepManager
from tuxemon.game_variables import GameVariablesManager, PlayerVariablesManager
from tuxemon.locale import T
from tuxemon.map.map_view import SpriteController
from tuxemon.mission.controller import MissionController
from tuxemon.mission.manager import MissionManager
from tuxemon.money.controller import MoneyController
from tuxemon.monster import Monster
from tuxemon.monster_dir.evolution_registry import EvolutionRegistry
from tuxemon.platform.const.sizes import PLAYER_NPC
from tuxemon.relationship import (
    Relationships,
    decode_relationships,
    encode_relationships,
)
from tuxemon.save_state import NPCState
from tuxemon.step_tracker import StepTrackerManager, decode_steps, encode_steps
from tuxemon.teleporter import TeleportFaint
from tuxemon.tracker import TrackingData, decode_tracking, encode_tracking
from tuxemon.tuxepedia import (
    TuxepediaManager,
    decode_tuxepedia,
    encode_tuxepedia,
)
from tuxemon.ui.cipher_processor import decode_cipher, encode_cipher

if TYPE_CHECKING:
    from tuxemon.db import BattleMusicModel
    from tuxemon.economy.applier import ShopInventory
    from tuxemon.economy.economy import Economy
    from tuxemon.item.item import Item
    from tuxemon.session import Session


logger = logging.getLogger(__name__)


class NPC(Entity):
    """
    Class for humanoid type game objects, NPC, Players, etc.

    Currently, all movement is handled by a queue called "path".  This queue
    provides robust movement in a tile based environment.  It supports
    arbitrary length paths for directly setting a series of movements.

    Pathfinding is accomplished by setting the path directly.

    To move one tile, simply set a path of one item.
    """

    def __init__(
        self,
        npc_slug: str,
        npc_data: NpcModel,
        session: Session,
        instance_id: UUID | None = None,
    ) -> None:
        super().__init__(
            slug=npc_slug, session=session, instance_id=instance_id
        )

        self.template = npc_data.template
        self.combat = npc_data.combat
        self.persistence = npc_data.persistence
        self.audio = npc_data.audio

        self._custom_name: str | None = None
        # general
        self.gender: str | None = None
        self.behavior: str | None = "wander"  # not used for now
        self._variables = GameVariablesManager()
        self.battle_handler = BattlesHandler()
        # Tracks Tuxepedia (monster seen or caught)
        self.tuxepedia = TuxepediaManager(session.client.event_bus)
        self.relationships = Relationships(session.client.event_bus)
        self.money_controller = MoneyController(self)
        # list of ways player can interact with the Npc
        self.interactions: Sequence[str] = []
        self.mission_controller = MissionController(self, MissionManager())
        self.economy: Economy | None = None
        self.shop_inventory: ShopInventory | None = None
        self.teleport_faint = TeleportFaint()
        self.tracker = TrackingData()
        self.step_tracker = StepTrackerManager()
        self.step_manager = StepManager(session, self.step_tracker)
        self.unlocked_letters: set[str] = set()
        # Variables for long-term item and monster storage
        # Keeping these separate so other code can safely
        # assume that all values are lists
        self.monster_boxes = MonsterBoxes()
        self.party = PartyHandler(monster_boxes=self.monster_boxes, owner=self)
        self.item_boxes = ItemBoxes()
        self.bag = BagHandler(item_boxes=self.item_boxes, owner=self)
        self.evolution_registry = EvolutionRegistry()
        self.steps: float = 0.0
        self.dialogue: DialogueProfile | None = None
        self.sprite_controller = SpriteController(self)

        # PathController manages all path/pathfinding state & logic.
        self.path_controller = PathController(
            self,
            self.client.pathfinder,
            self.client.map_manager,
            self.client.npc_manager,
        )
        self.final_move_dest: tuple[int, int] = (0, 0)

    @classmethod
    def create(cls, session: Session, npc_slug: str) -> NPC:
        npc_data = NpcModel.lookup(npc_slug, db)
        return cls(npc_slug, npc_data, session)

    @classmethod
    def from_save(cls, session: Session, save_data: NPCState) -> NPC:
        slug = save_data.player_slug or PLAYER_NPC
        npc_data = NpcModel.lookup(slug, db)
        npc = cls(slug, npc_data, session)
        npc.set_state(session, save_data)
        return npc

    @property
    def name(self) -> str:
        return self._custom_name or T.translate(self.slug)

    @name.setter
    def name(self, value: str) -> None:
        self._custom_name = value

    @property
    def gender_translated(self) -> str:
        if self.gender is None:
            return ""
        return T.translate(f"gender_{self.gender}")

    @property
    def game_variables(self) -> PlayerVariablesManager:
        return self._variables.player

    @property
    def monsters(self) -> list[Monster]:
        """Returns the list of monsters in the party."""
        return self.party.monsters

    @property
    def items(self) -> list[Item]:
        """Returns the list of items in the bag."""
        return self.bag.items

    @property
    def path(self) -> list[tuple[int, int]]:
        """Returns the current movement path assigned to the NPC."""
        return self.path_controller.path

    @property
    def move_destination(self) -> tuple[int, int] | None:
        """Returns the NPC's current movement destination tile, if any."""
        return self.path_controller.move_destination

    def get_state(self, session: Session) -> NPCState:
        """
        Prepares a dictionary of the npc to be saved to a file.

        Parameters:
            session: Game session.

        Returns:
            Dictionary containing all the information about the npc.
        """
        base = super().get_state(session)

        monster_boxes_state = self.monster_boxes.get_state()
        item_boxes_state = self.item_boxes.get_state()

        base.gender = self.gender
        base.current_map = self.current_map
        base.facing = self.facing.value
        base.game_variables = self._variables.get_player_state()
        base.battles = self.battle_handler.encode_battle()
        base.tuxepedia = encode_tuxepedia(self.tuxepedia)
        base.relationships = encode_relationships(self.relationships)
        base.money = self.money_controller.save()
        base.items = self.bag.encode_items()
        base.template = self.template.model_dump()
        base.missions = self.mission_controller.encode_missions()
        base.monsters = self.party.encode_party()
        base.player_slug = self.slug
        base.player_name = self.name
        base.player_steps = self.steps
        base.monster_boxes = monster_boxes_state["monster_boxes"]
        base.monster_box_metadata = monster_boxes_state["monster_box_metadata"]
        base.item_boxes = item_boxes_state["item_boxes"]
        base.item_box_metadata = item_boxes_state["item_box_metadata"]
        base.teleport_faint = self.teleport_faint.to_dict()
        base.tracker = encode_tracking(self.tracker)
        base.step_tracker = encode_steps(self.step_tracker)
        base.unlocked_letters = encode_cipher(self.unlocked_letters)
        base.evolution_registry = self.evolution_registry.encode_registry()
        base.routing_policy = self.party.routing_policy.to_dict()

        return base

    def set_state(self, session: Session, save_data: NPCState) -> None:
        """
        Recreates npc from saved data.

        Parameters:
            session: Game session.
            save_data: Data used to recreate the NPC.
        """
        super().set_state(session, save_data)

        self.gender = save_data.gender
        self._variables.set_player_state(save_data.game_variables)
        self.tuxepedia = decode_tuxepedia(
            save_data.tuxepedia, session.client.event_bus
        )
        self.relationships = decode_relationships(
            save_data.relationships, session.client.event_bus
        )
        self.battle_handler.decode_battle(save_data)
        self.bag.decode_items(save_data)
        self.party.decode_party(save_data)
        self.mission_controller.decode_missions(save_data.missions)
        self.name = save_data.player_name or "Player"
        self.steps = save_data.player_steps or 0.0
        self.money_controller.load(save_data)
        self.unlocked_letters = decode_cipher(save_data)
        self.evolution_registry.decode_registry(save_data.evolution_registry)
        self.monster_boxes.load(self, save_data)
        self.item_boxes.load(save_data)

        self.teleport_faint = TeleportFaint.from_dict(save_data)

        self.tracker = decode_tracking(save_data.tracker)
        self.step_tracker = decode_steps(save_data.step_tracker)
        self.party.routing_policy_name = RoutingPolicy.from_dict(save_data)

        if save_data.template:
            self.template.slug = save_data.template.get("slug", "")
            self.template.sprite_name = save_data.template.get(
                "sprite_name", ""
            )
            self.template.combat_front = save_data.template.get(
                "combat_front", ""
            )
            self.sprite_controller.update_template(self.template)

    def get_active_battle_music(
        self, default_music: BattleMusicModel
    ) -> BattleMusicModel:
        if self.audio and self.audio.battle_music:
            return self.audio.battle_music
        return default_music

    def pathfind(self, destination: tuple[int, int]) -> None:
        self.path_controller.start_path(destination)

    def set_path_and_start(self, path: list[tuple[int, int]]) -> None:
        self.path_controller.set_path_and_start(path)

    def cancel_path(self) -> None:
        self.path_controller.cancel_path()

    def cancel_movement(self) -> None:
        self.path_controller.cancel_movement()

    def abort_movement(self, preserve_position: bool = False) -> None:
        self.path_controller.abort_movement(preserve_position)

    def update(self, time_delta: float) -> None:
        """
        Handles NPC movement updates, including animations, physics, and
        navigation.

        This method updates:
        - Physics calculations for movement.
        - Animation state of the NPC.
        - Movement logic, including path progression and direct movement
            requests.

        Parameters:
            time_delta: The time elapsed since the last update
            (from clock.tick()/1000.0).
        """
        # Update sprite animations based on movement state.
        self.sprite_controller.update(time_delta)
        self.update_physics(time_delta)
        self.path_controller.update(time_delta)
