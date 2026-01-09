# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import pytest

from tuxemon.db import (
    Behavior,
    BoundingBox,
    EventObject,
    Operator,
    ParameterizableRule,
    SpatialCondition,
)
from tuxemon.event.eventbehavior import (
    BehaviorManager,
    EventBehavior,
    expand_behavior_actions,
    expand_behavior_conditions,
)


@pytest.fixture
def dummy_event():
    return EventObject(
        id=123,
        name="test",
        box=BoundingBox(x=0, y=0, width=1, height=1),
        priority=0,
        timeout=None,
        delay=None,
        conds=[],
        acts=[],
        behavs=[],
    )


@pytest.fixture
def behavior_manager(monkeypatch):
    monkeypatch.setattr(
        "tuxemon.event.eventbehavior.load_plugins",
        lambda **kwargs: {},
    )
    return BehaviorManager(root_path=None)


class DummyBehavior(EventBehavior):
    name = "dummy"

    def expand(self, event, behavior):
        cond = SpatialCondition(
            type="dummy_cond",
            parameters=["x"],
            box=event.box,
            operator=Operator.IS,
            name="dummy_cond",
        )
        act = ParameterizableRule(
            type="dummy_act",
            parameters=["y"],
            name="dummy_act",
        )
        return [cond], [act]


def test_get_behavior_success(monkeypatch):
    monkeypatch.setattr(
        "tuxemon.event.eventbehavior.load_plugins",
        lambda **kwargs: {"dummy": DummyBehavior},
    )

    mgr = BehaviorManager(root_path=None)
    beh = mgr.get_behavior("dummy")

    assert isinstance(beh, DummyBehavior)


def test_get_behavior_missing(monkeypatch, caplog):
    monkeypatch.setattr(
        "tuxemon.event.eventbehavior.load_plugins",
        lambda **kwargs: {},
    )

    mgr = BehaviorManager(root_path=None)
    beh = mgr.get_behavior("unknown")

    assert beh is None
    assert "not implemented" in caplog.text.lower()


def test_get_behavior_instantiation_error(monkeypatch, caplog):

    class BadBehavior(EventBehavior):
        name = "bad"

        def __init__(self):
            raise RuntimeError("boom")

        def expand(self, event, behavior):
            return [], []

    monkeypatch.setattr(
        "tuxemon.event.eventbehavior.load_plugins",
        lambda **kwargs: {"bad": BadBehavior},
    )

    mgr = BehaviorManager(root_path=None)
    beh = mgr.get_behavior("bad")

    assert beh is None
    assert "error instantiating behavior" in caplog.text.lower()


def test_expand_behavior_conditions(monkeypatch, dummy_event):
    dummy_event.behavs = [Behavior(type="dummy", args=[], name="b1")]

    monkeypatch.setattr(
        "tuxemon.event.eventbehavior.load_plugins",
        lambda **kwargs: {"dummy": DummyBehavior},
    )

    mgr = BehaviorManager(root_path=None)
    conds = expand_behavior_conditions(dummy_event, mgr)

    assert len(conds) == 1
    assert isinstance(conds[0], SpatialCondition)
    assert conds[0].type == "dummy_cond"


def test_expand_behavior_actions(monkeypatch, dummy_event):
    dummy_event.behavs = [Behavior(type="dummy", args=[], name="b1")]

    monkeypatch.setattr(
        "tuxemon.event.eventbehavior.load_plugins",
        lambda **kwargs: {"dummy": DummyBehavior},
    )

    mgr = BehaviorManager(root_path=None)
    acts = expand_behavior_actions(dummy_event, mgr)

    assert len(acts) == 1
    assert isinstance(acts[0], ParameterizableRule)
    assert acts[0].type == "dummy_act"


def test_expand_behavior_skips_missing_plugin(monkeypatch, dummy_event):
    dummy_event.behavs = [Behavior(type="missing", args=[], name="b1")]

    monkeypatch.setattr(
        "tuxemon.event.eventbehavior.load_plugins",
        lambda **kwargs: {},
    )

    mgr = BehaviorManager(root_path=None)

    conds = expand_behavior_conditions(dummy_event, mgr)
    acts = expand_behavior_actions(dummy_event, mgr)

    assert conds == []
    assert acts == []


def test_expand_behavior_logs_error_on_plugin_failure(
    monkeypatch, dummy_event, caplog
):

    class ExplodingBehavior(EventBehavior):
        name = "explode"

        def expand(self, event, behavior):
            raise RuntimeError("boom")

    dummy_event.behavs = [Behavior(type="explode", args=[], name="b1")]

    monkeypatch.setattr(
        "tuxemon.event.eventbehavior.load_plugins",
        lambda **kwargs: {"explode": ExplodingBehavior},
    )

    mgr = BehaviorManager(root_path=None)

    conds = expand_behavior_conditions(dummy_event, mgr)
    acts = expand_behavior_actions(dummy_event, mgr)

    assert conds == []
    assert acts == []
    assert "error expanding behavior" in caplog.text.lower()
