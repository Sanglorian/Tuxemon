# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import logging
from dataclasses import dataclass

from tuxemon.event.eventaction import EventAction, split_parameters
from tuxemon.session import Session


@dataclass
class SampleAction(EventAction):
    name = "sample"
    text: str
    avatar: str | None = None
    speaker: str | None = None

    def start(self, session: Session) -> None:
        pass


def test_all_positional():
    args, kwargs = split_parameters(SampleAction, ["hello", "bulbatux"])

    assert args == ["hello", "bulbatux"]
    assert kwargs == {}


def test_named_parameter():
    args, kwargs = split_parameters(
        SampleAction, ["hello", "speaker=npc_maple"]
    )

    assert args == ["hello"]
    assert kwargs == {"speaker": "npc_maple"}


def test_unknown_name_stays_positional(caplog):
    # another test may have raised the log level, so ask for the warning
    caplog.set_level(logging.WARNING, logger="tuxemon.event.eventaction")

    args, kwargs = split_parameters(SampleAction, ["hello", "volume=3"])

    assert args == ["hello", "volume=3"]
    assert kwargs == {}
    assert "not a parameter of action 'sample'" in caplog.text


def test_value_containing_an_equals_sign():
    args, kwargs = split_parameters(SampleAction, ["a=b=c"])

    assert args == ["a=b=c"]
    assert kwargs == {}


def test_value_of_a_named_parameter_may_contain_an_equals_sign():
    args, kwargs = split_parameters(SampleAction, ["hi", "speaker=a=b"])

    assert args == ["hi"]
    assert kwargs == {"speaker": "a=b"}


def test_non_string_parameters_are_untouched():
    args, kwargs = split_parameters(SampleAction, ["hello", 3, None])

    assert args == ["hello", 3, None]
    assert kwargs == {}


def test_private_fields_are_not_addressable():
    """The bookkeeping fields of EventAction are not script parameters."""
    args, kwargs = split_parameters(SampleAction, ["hello", "cancelled=true"])

    assert args == ["hello", "cancelled=true"]
    assert kwargs == {}
