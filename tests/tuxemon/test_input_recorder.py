# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import pygame

from tuxemon.platform.events import PlayerInput
from tuxemon.platform.input_manager import InputManager
from tuxemon.platform.input_recorder import InputRecorder


class DummyPlayer:
    def __init__(self):
        self.tile_pos = (5, 10)
        self.facing = "north"


class DummyClient:
    def __init__(self):
        self._map_name = "test_map"

    def get_map_name(self):
        return self._map_name


class DummySession:
    def __init__(self):
        self.player = DummyPlayer()
        self.client = DummyClient()


class TestInputRecorder(unittest.TestCase):
    def setUp(self):
        self.recorder = InputRecorder()
        self.session = DummySession()
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def make_event(self, button=1, value=1.0):
        return PlayerInput(button=button, value=value, timestamp=123.456)

    def test_start_and_stop_recording(self):
        self.recorder.start_recording(self.session)
        self.assertTrue(self.recorder._is_recording)
        e = self.make_event()
        self.recorder.record_event(e)
        events = self.recorder.stop_recording("test")
        self.assertFalse(self.recorder._is_recording)
        self.assertEqual(len(events), 1)
        self.assertIn("test", self.recorder.list_recordings())
        state = self.recorder.get_recording_state("test")
        self.assertEqual(state["map"], "test_map")

    def test_stop_recording_without_start(self):
        events = self.recorder.stop_recording("unused")
        self.assertEqual(events, [])

    def test_start_playback_and_next_event(self):
        e1 = self.make_event(button=1)
        e2 = self.make_event(button=2)
        self.recorder._recordings["play"] = [e1, e2]
        self.recorder.start_playback_named("play")
        self.assertTrue(self.recorder._is_playing_back)
        ev = self.recorder.next_playback_event()
        self.assertEqual(ev.button, 1)
        ev2 = self.recorder.next_playback_event()
        self.assertEqual(ev2.button, 2)
        ev3 = self.recorder.next_playback_event()
        self.assertIsNone(ev3)
        self.assertFalse(self.recorder._is_playing_back)

    def test_start_playback_while_recording(self):
        self.recorder.start_recording(self.session)
        self.recorder.start_playback([self.make_event()])
        self.assertFalse(self.recorder._is_playing_back)

    def test_save_and_load_file(self):
        self.recorder.start_recording(self.session)
        self.recorder.record_event(self.make_event())
        self.recorder.stop_recording("filetest")
        path = self.tmpdir / "recording.json"
        ok = self.recorder.save_to_file(path, "filetest")
        self.assertTrue(ok)
        self.assertTrue(path.exists())
        loaded = self.recorder.load_from_file(path, "loaded")
        self.assertEqual(len(loaded), 1)
        self.assertIn("loaded", self.recorder.list_recordings())
        state = self.recorder.get_recording_state("loaded")
        self.assertIn("map", state)

    def test_save_without_events(self):
        path = self.tmpdir / "empty.json"
        ok = self.recorder.save_to_file(path, "nonexistent")
        self.assertFalse(ok)
        self.assertFalse(path.exists())

    def test_load_nonexistent_file(self):
        path = self.tmpdir / "missing.json"
        result = self.recorder.load_from_file(path, "missing")
        self.assertIsNone(result)

    def test_multiple_recordings(self):
        self.recorder.start_recording(self.session)
        self.recorder.record_event(self.make_event(button=1))
        self.recorder.stop_recording("rec1")

        self.recorder.start_recording(self.session)
        self.recorder.record_event(self.make_event(button=2))
        self.recorder.stop_recording("rec2")

        self.assertIn("rec1", self.recorder.list_recordings())
        self.assertIn("rec2", self.recorder.list_recordings())
        self.assertNotEqual(
            self.recorder.get_recording("rec1")[0].button,
            self.recorder.get_recording("rec2")[0].button,
        )

    def test_record_event_clones(self):
        self.recorder.start_recording(self.session)
        e = self.make_event(button=99)
        self.recorder.record_event(e)
        e.button = 42
        events = self.recorder.stop_recording("clone_test")
        self.assertEqual(events[0].button, 99)

    def test_stop_playback_resets_state(self):
        e = self.make_event()
        self.recorder._recordings["play"] = [e]
        self.recorder.start_playback_named("play")
        self.recorder.stop_playback()
        self.assertFalse(self.recorder._is_playing_back)
        self.assertIsNone(self.recorder._current_playback_data)
        self.assertEqual(self.recorder._playback_index, 0)

    def test_save_load_round_trip(self):
        self.recorder.start_recording(self.session)
        e = self.make_event(button=7)
        self.recorder.record_event(e)
        self.recorder.stop_recording("roundtrip")
        path = self.tmpdir / "roundtrip.json"
        self.recorder.save_to_file(path, "roundtrip")
        loaded = self.recorder.load_from_file(path, "roundtrip_loaded")
        self.assertEqual(loaded[0].button, 7)
        state = self.recorder.get_recording_state("roundtrip_loaded")
        self.assertEqual(state["map"], "test_map")

    def test_empty_initial_state(self):
        self.recorder._initial_state = None
        self.recorder._recorded_events = [self.make_event()]
        path = self.tmpdir / "no_state.json"
        ok = self.recorder.save_to_file(path)
        self.assertTrue(ok)
        data = json.loads(path.read_text())
        self.assertEqual(data["initial_state"], {})


class DummyConfig:
    def __init__(self):
        self.controller = type(
            "C",
            (),
            {
                "type": None,
                "overlay": False,
                "hide_mouse": True,
                "show_input_visualizer": False,
                "combo_window_seconds": 5.0,
            },
        )()
        self.input = type("I", (), {"keyboard_button_map": {}})()


class DummyAFKManager:
    def reset(self):
        pass

    def update(self, dt):
        pass


class TestIntegrationRecorderManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.manager = InputManager(DummyConfig(), DummyAFKManager())
        self.recorder = self.manager.recorder

    def make_event(self, button=1):
        return PlayerInput(button=button, value=1.0, timestamp=0.0)

    def test_playback_events_flow_through_manager(self):
        e1 = self.make_event(button=10)
        e2 = self.make_event(button=20)
        self.recorder._recordings["demo"] = [e1, e2]
        self.recorder.start_playback_named("demo")

        events = list(self.manager.process_events())
        self.assertEqual(events[0].button, 10)
        events = list(self.manager.process_events())
        self.assertEqual(events[0].button, 20)
        events = list(self.manager.process_events())
        self.assertEqual(events, [])
        self.assertFalse(self.recorder._is_playing_back)
