# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import pytest

from tuxemon.script.parser import (
    parse_action_string,
    parse_behav_string,
    parse_condition_string,
    split_escaped,
)


@pytest.mark.parametrize(
    "input_str, expected",
    [
        ("spam", ["spam"]),
        ("spam ", ["spam"]),
        (" spam", ["spam"]),
        (" spam ", ["spam"]),
        ("spam , eggs  ", ["spam", "eggs"]),
        ("spam , eggs,", ["spam", "eggs", ""]),
        ("spam , eggs  ,, ", ["spam", "eggs", "", ""]),
        ("", []),
        (",", ["", ""]),
        ("spam\\,eggs,ham", ["spam,eggs", "ham"]),
        ("spam\\,eggs\\,ham", ["spam,eggs,ham"]),
    ],
)
def test_split_escaped(input_str, expected):
    assert split_escaped(input_str) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("spam", ("spam", [])),
        ("spam eggs", ("spam", ["eggs"])),
        ("spam eggs,parrot", ("spam", ["eggs", "parrot"])),
        ("spam , ", ("spam", ["", ""])),
        ("spam eggs, ", ("spam", ["eggs", ""])),
        ("spam,eggs", ("spam,eggs", [])),
        ("   spam   ", ("", ["spam"])),
        ("spam ,,", ("spam", ["", "", ""])),
        ("spam ex parrot", ("spam", ["ex parrot"])),
        ("spam eggs,  ex parrot", ("spam", ["eggs", "ex parrot"])),
    ],
)
def test_parse_action_string(text, expected):
    assert parse_action_string(text) == expected


def test_no_type():
    with pytest.raises(ValueError):
        parse_condition_string("spam")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("spam eggs", ("spam", "eggs", [])),
        (" spam eggs ", ("", "spam", ["eggs"])),
        ("spam eggs, ", ("spam", "eggs,", [])),
        ("spam eggs, parrot", ("spam", "eggs,", ["parrot"])),
        (
            " spam eggs parrot, cheese, ",
            ("", "spam", ["eggs parrot", "cheese", ""]),
        ),
        (
            "spam eggs  ex parrot, cheese shop",
            ("spam", "eggs", ["ex parrot", "cheese shop"]),
        ),
    ],
)
def test_parse_condition_string(text, expected):
    assert parse_condition_string(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("walk", ("walk", [])),
        ("walk north", ("walk", ["north"])),
        ("move npc1, npc2", ("move", ["npc1", "npc2"])),
        ("  animate  idle  ", ("", ["animate  idle"])),
        ("trigger a\\,b,c", ("trigger", ["a,b", "c"])),
        ("trigger a\\,b\\,c", ("trigger", ["a,b,c"])),
    ],
)
def test_parse_behav_string(text, expected):
    assert parse_behav_string(text) == expected


def reconstruct_action(act_type: str, args: list[str]) -> str:
    if not args:
        return act_type
    escaped = [a.replace(",", r"\,") for a in args]
    return f"{act_type} " + ", ".join(escaped)


def reconstruct_condition(
    operator: str, cond_type: str, args: list[str]
) -> str:
    if not args:
        return f"{operator} {cond_type}"
    escaped = [a.replace(",", r"\,") for a in args]
    return f"{operator} {cond_type} " + ", ".join(escaped)


def reconstruct_behav(behav_type: str, args: list[str]) -> str:
    if not args:
        return behav_type
    escaped = [a.replace(",", r"\,") for a in args]
    return f"{behav_type} " + ", ".join(escaped)


@pytest.mark.parametrize(
    "text",
    [
        "walk",
        "walk north",
        "move npc1, npc2",
        "trigger a\\,b,c",
        "trigger a\\,b\\,c",
        "  animate idle  ",
    ],
)
def test_roundtrip_behav(text):
    behav_type, args = parse_behav_string(text)
    reconstructed = reconstruct_behav(behav_type, args)
    behav_type2, args2 = parse_behav_string(reconstructed)
    assert behav_type == behav_type2
    assert args == args2


@pytest.mark.parametrize(
    "text",
    [
        "spam",
        "spam eggs",
        "spam eggs,parrot",
        "spam eggs, ex parrot",
        "spam a\\,b,c",
        "spam a\\,b\\,c",
        "   spam   ",
    ],
)
def test_roundtrip_action(text):
    act_type, args = parse_action_string(text)
    reconstructed = reconstruct_action(act_type, args)
    act_type2, args2 = parse_action_string(reconstructed)
    assert act_type == act_type2
    assert args == args2


@pytest.mark.parametrize(
    "text",
    [
        "spam eggs",
        "spam eggs, parrot",
        "spam eggs  ex parrot, cheese shop",
        "spam eggs, a\\,b,c",
        "spam eggs, a\\,b\\,c",
        " spam eggs parrot, cheese, ",
    ],
)
def test_roundtrip_condition(text):
    operator, cond_type, args = parse_condition_string(text)
    reconstructed = reconstruct_condition(operator, cond_type, args)
    operator2, cond_type2, args2 = parse_condition_string(reconstructed)
    assert operator == operator2
    assert cond_type == cond_type2
    assert args == args2
