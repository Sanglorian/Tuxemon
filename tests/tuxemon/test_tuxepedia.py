# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import Mock

from tuxemon.db import SeenStatus
from tuxemon.tuxepedia import (
    EVENT_MONSTER_ADDED,
    EVENT_MONSTER_REMOVED,
    EVENT_MONSTER_STATUS_UPDATED,
    EVENT_TUXEPEDIA_RESET,
    MonsterEntry,
    TuxepediaData,
    TuxepediaManager,
    TuxepediaReporter,
    decode_tuxepedia,
    encode_tuxepedia,
)


class MockEventBus:
    def __init__(self):
        self.publish = Mock()


class TestMonsterEntry(unittest.TestCase):

    def test_init(self):
        entry = MonsterEntry()
        self.assertEqual(entry.status, SeenStatus.seen)
        self.assertEqual(entry.appearance_count, 1)

    def test_update_status(self):
        entry = MonsterEntry()
        entry.update_status(SeenStatus.caught)
        self.assertEqual(entry.status, SeenStatus.caught)

    def test_cannot_set_caught_to_seen(self):
        entry = MonsterEntry(status=SeenStatus.caught)
        entry.update_status(SeenStatus.seen)
        self.assertEqual(entry.status, SeenStatus.caught)

    def test_reset_entry(self):
        entry = MonsterEntry(status=SeenStatus.caught, appearance_count=5)
        entry.reset_entry()
        self.assertEqual(entry.status, SeenStatus.seen)
        self.assertEqual(entry.appearance_count, 1)

    def test_get_state(self):
        entry = MonsterEntry(status=SeenStatus.caught, appearance_count=5)
        self.assertEqual(
            entry.get_state(),
            {
                "status": SeenStatus.caught,
                "appearance_count": 5,
                "caught_count": 0,
            },
        )


class TestTuxepediaData(unittest.TestCase):
    def setUp(self):
        initial_entries = {
            "rockitten": MonsterEntry(SeenStatus.seen, 2),
            "nut": MonsterEntry(SeenStatus.caught, 5),
            "flowey": MonsterEntry(SeenStatus.seen, 1),
        }
        self.data = TuxepediaData(initial_entries)

    def test_init(self):
        empty_data = TuxepediaData()
        self.assertEqual(empty_data.entries, {})

    def test_get_total_monsters(self):
        self.assertEqual(self.data.get_total_monsters(), 3)

    def test_get_seen_count(self):
        self.assertEqual(self.data.get_seen_count(), 2)

    def test_get_caught_count(self):
        self.assertEqual(self.data.get_caught_count(), 1)

    def test_get_appearance(self):
        self.assertEqual(self.data.get_appearance("nut"), 5)
        self.assertEqual(self.data.get_caught("nut"), 0)
        self.assertEqual(self.data.get_appearance("unknown"), 0)
        self.assertEqual(self.data.get_caught("unknown"), 0)

    def test_is_registered(self):
        self.assertTrue(self.data.is_registered("nut"))
        self.assertFalse(self.data.is_registered("squirtle"))

    def test_get_status(self):
        self.assertEqual(self.data.get_status("nut"), SeenStatus.caught)
        self.assertIsNone(self.data.get_status("unknown"))

    def test_delete_entry(self):
        self.data.delete_entry("nut")
        self.assertFalse(self.data.is_registered("nut"))
        with self.assertRaises(KeyError):
            self.data.delete_entry("unknown")


class TestTuxepediaManager(unittest.TestCase):
    def setUp(self):
        self.event_bus = MockEventBus()
        self.manager = TuxepediaManager(self.event_bus)

    def test_add_new_entry_seen(self):
        self.manager.add_entry("rockitten")

        self.assertIn("rockitten", self.manager.data.entries)
        self.assertEqual(
            self.manager.data.get_status("rockitten"), SeenStatus.seen
        )

        self.event_bus.publish.assert_called_with(
            EVENT_MONSTER_ADDED,
            monster_slug="rockitten",
            status=SeenStatus.seen,
            appearance_count=1,
            caught_count=0,
        )

    def test_update_existing_entry_to_caught(self):
        self.manager.add_entry("rockitten")
        self.manager.add_entry("rockitten", status=SeenStatus.caught)

        self.assertEqual(
            self.manager.data.get_status("rockitten"), SeenStatus.caught
        )
        self.assertEqual(self.manager.data.get_appearance("rockitten"), 2)
        self.assertEqual(self.manager.data.get_caught("rockitten"), 1)

        self.event_bus.publish.assert_called_with(
            EVENT_MONSTER_STATUS_UPDATED,
            monster_slug="rockitten",
            status=SeenStatus.caught,
            appearance_count=2,
            status_changed=True,
            caught_count=1,
        )

    def test_remove_entry(self):
        self.manager.add_entry("rockitten", status=SeenStatus.caught)
        self.manager.remove_entry("rockitten")

        self.assertNotIn("rockitten", self.manager.data.entries)

        self.event_bus.publish.assert_called_with(
            EVENT_MONSTER_REMOVED,
            monster_slug="rockitten",
            status=SeenStatus.caught,
            appearance_count=1,
            caught_count=0,
        )

        with self.assertRaises(ValueError):
            self.manager.remove_entry("nut")

    def test_reset_remove_seen_only(self):
        self.manager.add_entry("caught_mon", status=SeenStatus.caught)
        self.manager.add_entry("seen_mon_1")
        self.manager.add_entry("seen_mon_2")
        self.assertEqual(self.manager.data.get_total_monsters(), 3)

        self.manager.reset(remove_seen_only=True)

        self.assertEqual(self.manager.data.get_total_monsters(), 1)
        self.assertTrue(self.manager.data.is_registered("caught_mon"))
        self.assertFalse(self.manager.data.is_registered("seen_mon_1"))

        self.event_bus.publish.assert_called_with(
            EVENT_TUXEPEDIA_RESET,
            removed_count=2,
            remaining_count=1,
            remove_seen_only=True,
            removed_monsters=unittest.mock.ANY,
        )

    def test_reset_remove_all(self):
        self.manager.add_entry("caught_mon", status=SeenStatus.caught)
        self.manager.add_entry("seen_mon")
        self.manager.reset(remove_seen_only=False)

        self.assertEqual(self.manager.data.get_total_monsters(), 0)
        self.event_bus.publish.assert_called_with(
            EVENT_TUXEPEDIA_RESET,
            removed_count=2,
            remaining_count=0,
            remove_seen_only=False,
            removed_monsters=unittest.mock.ANY,
        )


class TestTuxepediaReporter(unittest.TestCase):
    def setUp(self):
        initial_entries = {
            "rockitten": MonsterEntry(SeenStatus.seen, 5),
            "nut": MonsterEntry(SeenStatus.caught, 10),
            "flowey": MonsterEntry(SeenStatus.seen, 2),
        }
        self.data = TuxepediaData(initial_entries)
        self.reporter = TuxepediaReporter(self.data)

    def test_get_most_frequent_monsters(self):
        top_two = self.reporter.get_most_frequent_monsters(2)
        self.assertEqual(top_two, [("nut", 10), ("rockitten", 5)])

    def test_get_monster_status_distribution(self):
        distribution = self.reporter.get_monster_status_distribution()
        self.assertEqual(distribution[SeenStatus.seen], 2)
        self.assertEqual(distribution[SeenStatus.caught], 1)

    def test_get_completeness_report(self):
        total_game = 10
        report = self.reporter.get_completeness_report(total_game)

        self.assertAlmostEqual(report["registered_percent"], 3 / 10)
        self.assertAlmostEqual(report["caught_percent"], 1 / 10)
        self.assertEqual(report["total_game"], 10)

    def test_get_unregistered_monsters(self):
        all_slugs = {"rockitten", "nut", "flowey", "ghost"}
        unregistered = self.reporter.get_unregistered_monsters(all_slugs)
        self.assertIn("ghost", unregistered)
        self.assertNotIn("nut", unregistered)

    def test_get_completeness_report_zero_total(self):
        report = self.reporter.get_completeness_report(0)
        self.assertEqual(report["total_game"], 0)
        self.assertEqual(report["registered_percent"], 0.0)
        self.assertEqual(report["caught_percent"], 0.0)


class TestSerialization(unittest.TestCase):
    def setUp(self):
        self.event_bus = MockEventBus()
        self.manager = TuxepediaManager(self.event_bus)
        self.manager.add_entry("rockitten")
        self.manager.add_entry("nut", status=SeenStatus.caught)
        self.manager.add_entry("nut", status=SeenStatus.caught)

    def test_encode_tuxepedia(self):
        json_data = encode_tuxepedia(self.manager)

        self.assertIn("rockitten", json_data)
        self.assertIn("nut", json_data)
        self.assertEqual(json_data["rockitten"]["status"], SeenStatus.seen)
        self.assertEqual(json_data["rockitten"]["appearance_count"], 1)
        self.assertEqual(json_data["nut"]["status"], SeenStatus.caught)
        self.assertEqual(json_data["nut"]["appearance_count"], 2)

    def test_decode_tuxepedia(self):
        json_data = {
            "rockitten": {"status": SeenStatus.seen, "appearance_count": 5},
            "nut": {"status": SeenStatus.caught, "appearance_count": 10},
        }

        new_manager = decode_tuxepedia(json_data, self.event_bus)

        self.assertTrue(new_manager.data.is_registered("nut"))
        self.assertEqual(new_manager.data.get_status("nut"), SeenStatus.caught)
        self.assertEqual(new_manager.data.get_appearance("nut"), 10)
        self.assertEqual(new_manager.data.get_caught("nut"), 0)

    def test_encode_decode_roundtrip(self):
        json_data = encode_tuxepedia(self.manager)
        new_manager = decode_tuxepedia(json_data, self.event_bus)

        for slug in self.manager.data.get_monsters():
            self.assertTrue(new_manager.data.is_registered(slug))
            self.assertEqual(
                self.manager.data.get_status(slug),
                new_manager.data.get_status(slug),
            )
            self.assertEqual(
                self.manager.data.get_appearance(slug),
                new_manager.data.get_appearance(slug),
            )
            self.assertEqual(
                self.manager.data.get_caught(slug),
                new_manager.data.get_caught(slug),
            )
