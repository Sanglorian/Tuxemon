# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import partial
from typing import Optional, final

from tuxemon.event import get_npc
from tuxemon.event.eventaction import EventAction
from tuxemon.locale import T
from tuxemon.npc import NPC
from tuxemon.session import Session
from tuxemon.tools import open_choice_dialog
from tuxemon.ui.menu_options import ChoiceOption, MenuOptions

logger = logging.getLogger(__name__)


@final
@dataclass
class OpenShopAction(EventAction):
    """
    Open the shop menu for a NPC.

    Script usage:
        .. code-block::

            open_shop <npc_slug>[,menu]

    Script parameters:
        npc_slug: Either "player" or npc slug name (e.g. "npc_maple").
        menu: Either "buy", "sell" or "both". Default is "both".
    """

    name = "open_shop"
    npc_slug: str
    menu: Optional[str] = None

    def start(self, session: Session) -> None:
        menu = self.menu or "both"
        valid_menus = {"buy", "sell", "both"}

        if menu not in valid_menus:
            raise ValueError(
                f"Invalid menu value '{menu}'. Must be one of: {valid_menus}."
            )

        character = get_npc(session, self.npc_slug)
        if character is None:
            logger.error(f"{self.npc_slug} not found")
            return

        if character.economy is None:
            raise ValueError(
                f"'{character.slug}' has no assigned economy. Use the 'set_economy' EventAction first."
            )

        economy = character.economy

        def push_buy_menu(npc: NPC) -> None:
            session.client.push_state(
                "ShopBuyMenuState",
                buyer=session.player,
                seller=npc,
                economy=economy,
            )

        def push_sell_menu(npc: NPC) -> None:
            session.client.push_state(
                "ShopSellMenuState",
                buyer=npc,
                seller=session.player,
                economy=economy,
            )

        def buy_menu(npc: NPC) -> None:
            session.client.remove_state_by_name("ChoiceState")
            push_buy_menu(npc)

        def sell_menu(npc: NPC) -> None:
            session.client.remove_state_by_name("ChoiceState")
            push_sell_menu(npc)

        var_menu = MenuOptions(
            [
                ChoiceOption(
                    key="buy",
                    display_text=T.translate("buy"),
                    action=partial(buy_menu, character),
                ),
                ChoiceOption(
                    key="sell",
                    display_text=T.translate("sell"),
                    action=partial(sell_menu, character),
                ),
            ]
        )

        if menu == "both":
            open_choice_dialog(
                client=session.client, menu=var_menu, escape_key_exits=True
            )
        elif menu == "buy":
            push_buy_menu(character)
        elif menu == "sell":
            push_sell_menu(character)
