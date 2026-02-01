# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest

from tuxemon.money.controller import MoneyController
from tuxemon.money.manager import MoneyManager


@pytest.fixture
def npc():
    npc = MagicMock()
    npc.money_controller = MoneyController(npc)
    npc.money_controller.money_manager = MoneyManager()
    return npc


@pytest.fixture
def npc2():
    npc = MagicMock()
    npc.money_controller = MoneyController(npc)
    npc.money_controller.money_manager = MoneyManager()
    return npc


def test_transfer_money_success(npc, npc2):
    npc.money_controller.money_manager.add_money(100)
    npc.money_controller.transfer_money_to(50, npc2)
    assert npc.money_controller.money_manager.money == 50
    assert npc2.money_controller.money_manager.money == 50


def test_transfer_money_negative_amount(npc, npc2):
    with pytest.raises(ValueError):
        npc.money_controller.transfer_money_to(-10, npc2)


def test_transfer_money_zero_amount(npc, npc2):
    with pytest.raises(ValueError):
        npc.money_controller.transfer_money_to(0, npc2)


def test_transfer_money_insufficient_funds(npc, npc2):
    npc.money_controller.money_manager.add_money(20)

    with pytest.raises(ValueError):
        npc.money_controller.transfer_money_to(50, npc2)

    assert npc.money_controller.money_manager.money == 20
    assert npc2.money_controller.money_manager.money == 0


def test_transfer_bank_success(npc, npc2):
    npc.money_controller.money_manager.deposit_to_bank(100)
    npc.money_controller.transfer_bank_to(50, npc2)
    assert npc.money_controller.money_manager.bank_account == 50
    assert npc2.money_controller.money_manager.bank_account == 50


def test_transfer_bank_insufficient_funds(npc, npc2):
    npc.money_controller.money_manager.deposit_to_bank(20)

    with pytest.raises(ValueError):
        npc.money_controller.transfer_bank_to(50, npc2)

    assert npc.money_controller.money_manager.bank_account == 20
    assert npc2.money_controller.money_manager.bank_account == 0


def test_wallet_transfer_does_not_affect_bank(npc, npc2):
    npc.money_controller.money_manager.add_money(100)
    npc.money_controller.money_manager.deposit_to_bank(200)
    npc.money_controller.transfer_money_to(50, npc2)
    assert npc.money_controller.money_manager.money == 50
    assert npc.money_controller.money_manager.bank_account == 200


def test_bank_transfer_does_not_affect_wallet(npc, npc2):
    npc.money_controller.money_manager.add_money(100)
    npc.money_controller.money_manager.deposit_to_bank(200)
    npc.money_controller.transfer_bank_to(50, npc2)
    assert npc.money_controller.money_manager.money == 100
    assert npc.money_controller.money_manager.bank_account == 150
