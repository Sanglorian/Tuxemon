# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

import pytest

from tuxemon.state.state import State


@pytest.fixture(autouse=True)
def mock_local_session_client(monkeypatch):
    mock_client = MagicMock()
    monkeypatch.setattr("tuxemon.session.local_session._client", mock_client)

    return mock_client


class DummyState(State):
    name = "Dummy"

    def draw(self, surface):
        pass


def test_state_initializes_correctly(monkeypatch):
    mock_event_bus = MagicMock()
    monkeypatch.setattr(
        "tuxemon.state.state.get_event_bus", lambda: mock_event_bus
    )
    s = DummyState()
    assert s.start_time == 0.0
    assert s.current_time == 0.0
    assert hasattr(s, "sprites")
    assert hasattr(s, "anim")
    assert s.event_bus is mock_event_bus
    assert s.client is not None


def test_load_sprite(monkeypatch):
    mock_sprite = MagicMock()
    mock_loader = MagicMock(return_value=mock_sprite)
    mock_group = MagicMock()
    monkeypatch.setattr("tuxemon.state.state.load_sprite", mock_loader)
    monkeypatch.setattr("tuxemon.state.state.SpriteGroup", lambda: mock_group)
    s = DummyState()
    result = s.load_sprite("hero.png", layer=3)
    assert result is mock_sprite
    mock_group.add.assert_called_once_with(mock_sprite, layer=3)


def test_load_animated_sprite(monkeypatch):
    mock_sprite = MagicMock()
    mock_loader = MagicMock(return_value=mock_sprite)
    mock_group = MagicMock()
    monkeypatch.setattr(
        "tuxemon.state.state.load_animated_sprite", mock_loader
    )
    monkeypatch.setattr("tuxemon.state.state.SpriteGroup", lambda: mock_group)
    s = DummyState()
    result = s.load_animated_sprite(["a.png", "b.png"], delay=0.1, layer=2)
    assert result is mock_sprite
    mock_group.add.assert_called_once_with(mock_sprite, layer=2)


def test_process_event_returns_event():
    s = DummyState()
    event = MagicMock()
    assert s.process_event(event) is event


def test_update_calls_animation_and_sprite_update(monkeypatch):
    s = DummyState()
    s.update_animations = MagicMock()
    s.sprites.update = MagicMock()
    s.update(0.16)
    s.update_animations.assert_called_once_with(0.16)
    s.sprites.update.assert_called_once_with(0.16)


def test_resume_publishes_event(monkeypatch):
    mock_bus = MagicMock()
    monkeypatch.setattr("tuxemon.state.state.get_event_bus", lambda: mock_bus)
    s = DummyState()
    s.resume()
    mock_bus.publish.assert_called_with("state_resume")


def test_pause_publishes_event(monkeypatch):
    mock_bus = MagicMock()
    monkeypatch.setattr("tuxemon.state.state.get_event_bus", lambda: mock_bus)
    s = DummyState()
    s.pause()
    mock_bus.publish.assert_called_with("state_pause")


def test_shutdown_publishes_event(monkeypatch):
    mock_bus = MagicMock()
    monkeypatch.setattr("tuxemon.state.state.get_event_bus", lambda: mock_bus)
    s = DummyState()
    s.shutdown()
    mock_bus.publish.assert_called_with("state_shutdown")


def test_schedule_callback(monkeypatch):
    s = DummyState()
    mock_task = MagicMock()
    s.task = MagicMock(return_value=mock_task)
    mock_callback = MagicMock()
    monkeypatch.setattr("random.random", lambda: 0.0)
    s.schedule_callback(1.0, mock_callback)
    mock_callback.assert_called_once()
    s.task.assert_called_once()
    assert s._scheduled_task is mock_task


def test_stop_scheduled_callbacks(monkeypatch):
    s = DummyState()
    mock_task = MagicMock()
    s._scheduled_task = mock_task
    s.stop_scheduled_callbacks()
    mock_task.abort.assert_called_once()
    assert s._scheduled_task is None


def test_subscribe(monkeypatch):
    mock_bus = MagicMock()
    monkeypatch.setattr("tuxemon.state.state.get_event_bus", lambda: mock_bus)
    s = DummyState()
    s.subscribe("event", lambda: None, priority=5)
    mock_bus.subscribe.assert_called_once()


def test_unsubscribe(monkeypatch):
    mock_bus = MagicMock()
    mock_bus.has_listeners_for_event.return_value = True
    monkeypatch.setattr("tuxemon.state.state.get_event_bus", lambda: mock_bus)
    s = DummyState()
    callback = lambda: None
    s.unsubscribe("event", callback)
    mock_bus.unsubscribe.assert_called_once()


def test_publish(monkeypatch):
    mock_bus = MagicMock()
    mock_bus.has_listeners_for_event.return_value = True
    monkeypatch.setattr("tuxemon.state.state.get_event_bus", lambda: mock_bus)
    s = DummyState()
    s.publish("event", 1, x=2)
    mock_bus.publish.assert_called_once_with("event", 1, x=2)


def test_replace_events(monkeypatch):
    mock_bus = MagicMock()
    monkeypatch.setattr("tuxemon.state.state.get_event_bus", lambda: mock_bus)
    listener = MagicMock()
    listener.callback = MagicMock()
    listener.priority = 3
    s = DummyState()
    s.replace_events("event", [listener])
    mock_bus.clear_event.assert_called_once_with("event")
    mock_bus.subscribe.assert_called_once_with(
        "event", listener.callback, priority=3
    )
