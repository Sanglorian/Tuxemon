# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Any
from uuid import UUID

from tuxemon.network.networking import CharData, update_client
from tuxemon.npc import NPC

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.monster import Monster
    from tuxemon.network.manager import NetworkManager
    from tuxemon.save_state import NPCState
    from tuxemon.session import Session

logger = logging.getLogger(__name__)


class NPCRepository:
    """
    Internal helper for storing and querying NPCs.
    Not exposed publicly; NPCManager keeps public dicts for compatibility.
    """

    def __init__(self) -> None:
        self._data: dict[str, NPC] = {}

    def add(self, npc: NPC) -> None:
        self._data[npc.slug] = npc

    def remove(self, slug: str, *, cleanup: bool = True) -> None:
        npc = self._data.pop(slug, None)
        if npc and cleanup:
            npc.remove_collision()

    def get(self, slug: str) -> NPC | None:
        return self._data.get(slug)

    def find_by_iid(self, iid: UUID) -> NPC | None:
        return next(
            (npc for npc in self._data.values() if npc.instance_id == iid),
            None,
        )

    def find_by_pos(self, pos: tuple[int, int]) -> NPC | None:
        return next(
            (npc for npc in self._data.values() if npc.tile_pos == pos), None
        )

    def values(self) -> Iterable[NPC]:
        return self._data.values()

    def items(self) -> Iterable[tuple[str, NPC]]:
        return self._data.items()

    def keep_persistent(self) -> None:
        kept: dict[str, NPC] = {}
        for slug, npc in self._data.items():
            if npc.persistence:
                kept[slug] = npc
            else:
                npc.remove_collision()
        self._data = kept

    def export_public(self) -> dict[str, NPC]:
        """
        Return a shallow copy for public exposure.
        """
        return dict(self._data)


class NPCManager:
    def __init__(self) -> None:
        # Internal repositories
        self._on_map = NPCRepository()
        self._off_map = NPCRepository()

        # Public backward-compatible dicts
        self.npcs: dict[str, NPC] = {}
        self.npcs_off_map: dict[str, NPC] = {}

    def _sync_public_dicts(self) -> None:
        self.npcs = self._on_map.export_public()
        self.npcs_off_map = self._off_map.export_public()

    def npc_exists(self, slug: str) -> bool:
        return slug in self.npcs

    def add_npc(self, npc: NPC) -> None:
        self._on_map.add(npc)
        self._off_map.remove(npc.slug, cleanup=False)
        self._sync_public_dicts()

    def add_npc_off_map(self, npc: NPC) -> None:
        self._off_map.add(npc)
        self._on_map.remove(npc.slug, cleanup=False)
        self._sync_public_dicts()

    def remove_npc(self, slug: str) -> None:
        self._on_map.remove(slug)
        self._sync_public_dicts()

    def remove_npc_off_map(self, slug: str) -> None:
        self._off_map.remove(slug)
        self._sync_public_dicts()

    def get_npc(self, slug: str) -> NPC | None:
        return self._on_map.get(slug)

    def get_npc_off_map(self, slug: str) -> NPC | None:
        return self._off_map.get(slug)

    def get_npc_off_map_by_iid(self, iid: UUID) -> NPC | None:
        return self._off_map.find_by_iid(iid)

    def get_entity_pos(self, pos: tuple[int, int]) -> NPC | None:
        return self._on_map.find_by_pos(pos)

    def _update_entities(
        self,
        entities: Iterable[NPC],
        time_delta: float,
        client: BaseClient,
    ) -> None:
        for entity in entities:
            entity.update(time_delta)

            if not entity.update_location:
                continue

            char_dict = CharData(
                tile_pos=entity.final_move_dest,
                name=entity.name,
                facing=entity.facing,
                monsters=[],
                inventory=[],
            )
            update_client(entity, char_dict, client)
            entity.update_location = False

    def update_npcs(self, dt: float, client: BaseClient) -> None:
        self._update_entities(self._on_map.values(), dt, client)

    def update_npcs_off_map(self, dt: float, client: BaseClient) -> None:
        self._update_entities(self._off_map.values(), dt, client)

    def clear_npcs(self) -> None:
        self._on_map.keep_persistent()
        self._off_map.keep_persistent()
        self._sync_public_dicts()

    def get_all_entities(self) -> Sequence[NPC]:
        return list(self._on_map.values())

    def get_all_monsters(self) -> list[Monster]:
        return [
            monster
            for npc in self._on_map.values()
            for monster in npc.monsters
        ]

    def get_monster_by_iid(self, iid: UUID) -> Monster | None:
        return next(
            (
                monster
                for npc in self._on_map.values()
                for monster in npc.monsters
                if monster.instance_id == iid
            ),
            None,
        )

    def add_clients_to_map(
        self,
        registry: dict[str, Any],
        current_map: str,
    ) -> None:
        self.clear_npcs()

        for client in registry.values():
            if "sprite" not in client:
                continue

            sprite = client["sprite"]
            client_map = client.get("map_name")

            if client_map == current_map:
                self._on_map.add(sprite)
                self._off_map.remove(sprite.slug, cleanup=False)
            else:
                self._off_map.add(sprite)
                self._on_map.remove(sprite.slug, cleanup=False)

        self._sync_public_dicts()

    def get_all_slugs(self) -> list[str]:
        return list(self._on_map._data.keys()) + list(
            self._off_map._data.keys()
        )

    def handle_player_teleport(
        self,
        client: BaseClient,
        char: NPC,
        network: NetworkManager,
    ) -> None:
        client.event_data["transition"] = False

        if network.is_connected():
            assert network.client is not None
            current_map = client.get_map_name()
            self.add_clients_to_map(network.client.registry, current_map)
            network.client.update_player(char.facing.value)

        self.update_npcs(0.0, client)
        self.update_npcs_off_map(0.0, client)

    def get_persistent_npc_states(self, session: Session) -> list[NPCState]:
        states = []
        player_slug = session.player.slug

        for npc in (*self._on_map.values(), *self._off_map.values()):
            if npc.persistence and npc.slug != player_slug:
                if npc.session:
                    states.append(npc.get_state(npc.session))
                else:
                    logger.warning(
                        f"Cannot save persistent NPC {npc.slug}: missing session",
                    )

        return states

    def load_persistent_npc_states(
        self,
        session: Session,
        npc_states: list[NPCState],
    ) -> None:
        if not npc_states:
            return

        current_map = session.client.get_map_name()

        for state in npc_states:
            if not state.player_slug:
                continue

            npc = NPC(npc_slug=state.player_slug, session=session)
            npc.set_state(session, state)

            if state.current_map == current_map:
                self._on_map.add(npc)
                self._off_map.remove(npc.slug, cleanup=False)
            else:
                self._off_map.add(npc)
                self._on_map.remove(npc.slug, cleanup=False)

        self._sync_public_dicts()
