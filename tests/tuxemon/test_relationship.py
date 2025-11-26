# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from typing import Any, Mapping

from tuxemon.event.eventbus import EventBus
from tuxemon.relationship import (
    Connection,
    RelationshipConstants,
    Relationships,
    RelationshipStatus,
    decode_relationships,
    encode_relationships,
)


class TestConnection(unittest.TestCase):
    def test_connection_initialization(self):
        connection = Connection(
            relationship_type="friend",
            strength=75,
            steps=100,
            decay_rate=0.02,
            decay_threshold=1000,
        )
        self.assertEqual(connection.relationship_type, "friend")
        self.assertEqual(connection.strength, 75)
        self.assertEqual(connection.steps, 100)
        self.assertEqual(connection.decay_rate, 0.02)
        self.assertEqual(connection.decay_threshold, 1000)

    def test_update_steps(self):
        connection = Connection(relationship_type="friend")
        connection.update_steps(current_steps=200)
        self.assertEqual(connection.steps, 200)

    def test_apply_decay_no_decay(self):
        connection = Connection(
            relationship_type="friend",
            strength=75,
            steps=100,
            decay_threshold=500,
        )
        connection.apply_decay(current_steps=400)
        self.assertEqual(connection.strength, 75)

    def test_apply_decay_minimum_strength(self):
        connection = Connection(
            relationship_type="friend",
            strength=5,
            steps=0,
            decay_rate=0.5,
            decay_threshold=100,
        )
        connection.apply_decay(current_steps=200)
        self.assertEqual(connection.strength, 4)

    def test_apply_decay_maximum_strength(self):
        connection = Connection(
            relationship_type="friend",
            strength=95,
            steps=0,
            decay_rate=0.5,
            decay_threshold=100,
        )
        connection.apply_decay(current_steps=200)
        self.assertEqual(connection.strength, 94)

    def test_get_state(self):
        connection = Connection(
            relationship_type="friend",
            strength=75,
            steps=100,
            decay_rate=0.02,
            decay_threshold=1000,
        )
        state = connection.get_state()
        self.assertEqual(
            state,
            {
                "relationship_type": "friend",
                "strength": 75,
                "steps": 100,
                "decay_rate": 0.02,
                "decay_threshold": 1000,
            },
        )

    def test_apply_decay_with_profile_mod(self):
        connection = Connection(
            "friend", strength=50, steps=0, decay_rate=1.0, decay_threshold=100
        )
        connection.get_profile_value = lambda key: (
            2.0 if key == "decay_rate_mod" else 1.0
        )
        connection.apply_decay(current_steps=200)
        self.assertEqual(connection.strength, 46)

    def test_get_status(self):
        connection = Connection("friend", strength=90)
        status = connection.get_status()
        self.assertEqual(status, RelationshipStatus.BEST_FRIEND)


class TestRelationships(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.relationships = Relationships(self.event_bus)
        self.connection = Connection("friend", 75, 100, 0.02, 1000)

    def test_add_connection(self):
        self.relationships.add_connection("npc1", self.connection)
        connection = self.relationships.get_connection("npc1")
        self.assertIsNotNone(connection)
        self.assertEqual(connection.relationship_type, "friend")

    def test_remove_connection(self):
        self.relationships.add_connection("npc1", self.connection)
        self.relationships.remove_connection("npc1")
        connection = self.relationships.get_connection("npc1")
        self.assertIsNone(connection)

    def test_update_connection_strength(self):
        self.relationships.add_connection("npc1", self.connection)
        self.relationships.update_connection_strength("npc1", 90)
        connection = self.relationships.get_connection("npc1")
        self.assertEqual(connection.strength, 90)

    def test_get_connection(self):
        self.relationships.add_connection("npc1", self.connection)
        connection = self.relationships.get_connection("npc1")
        self.assertIsNotNone(connection)
        self.assertEqual(connection.relationship_type, "friend")

    def test_get_all_connections(self):
        self.relationships.add_connection("npc1", self.connection)
        connection = Connection("enemy", 25, 50, 0.01, 500)
        self.relationships.add_connection("npc2", connection)
        connections = self.relationships.get_all_connections()
        self.assertEqual(len(connections), 2)
        self.assertIn("npc1", connections)
        self.assertIn("npc2", connections)

    def test_update_connection_decay_rate(self):
        self.relationships.add_connection("npc1", self.connection)
        self.relationships.update_connection_decay_rate("npc1", 0.05)
        connection = self.relationships.get_connection("npc1")
        self.assertEqual(connection.decay_rate, 0.05)

    def test_update_connection_decay_threshold(self):
        self.relationships.add_connection("npc1", self.connection)
        self.relationships.update_connection_decay_threshold("npc1", 1500)
        connection = self.relationships.get_connection("npc1")
        self.assertEqual(connection.decay_threshold, 1500)

    def test_update_connection_strength_clamps(self):
        self.relationships.add_connection("npc1", self.connection)
        self.relationships.update_connection_strength("npc1", 999)
        self.assertEqual(
            self.relationships.get_connection("npc1").strength,
            RelationshipConstants.STRENGTH[1],
        )
        self.relationships.update_connection_strength("npc1", -50)
        self.assertEqual(
            self.relationships.get_connection("npc1").strength,
            RelationshipConstants.STRENGTH[0],
        )

    def test_modify_connection_strength_with_profile_mod(self):
        connection = Connection("friend", 50, 0, 0.01, 100)
        self.relationships.add_connection("npc1", connection)
        connection = self.relationships.get_connection("npc1")
        connection.get_profile_value = lambda key: (
            2.0 if key == "strength_increase_mod" else 1.0
        )
        self.relationships.modify_connection_strength("npc1", 10)
        self.assertEqual(connection.strength, 70)

    def test_modify_connection_strength_with_profile_mod(self):
        connection = Connection("friend", 50, 0, 0.01, 100)
        self.relationships.add_connection("npc1", connection)
        connection = self.relationships.get_connection("npc1")
        connection.get_profile_value = lambda key: (
            2.0 if key == "strength_decrease_mod" else 1.0
        )
        self.relationships.modify_connection_strength("npc1", -10)
        self.assertEqual(connection.strength, 30)


class TestEncodingDecoding(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.relationships = Relationships(self.event_bus)
        self.connection = Connection("friend", 75, 100, 0.02, 1000)

    def test_encode_relationships(self):
        self.relationships.add_connection("npc1", self.connection)
        encoded_data = encode_relationships(self.relationships)
        self.assertIsInstance(encoded_data, dict)
        self.assertIn("npc1", encoded_data)
        self.assertEqual(encoded_data["npc1"]["relationship_type"], "friend")

    def test_decode_relationships(self):
        json_data = {
            "npc1": {
                "relationship_type": "friend",
                "strength": 75,
                "steps": 100,
                "decay_rate": 0.02,
                "decay_threshold": 1000,
            }
        }
        relationships = decode_relationships(json_data, self.event_bus)
        connection = relationships.get_connection("npc1")
        self.assertIsNotNone(connection)
        self.assertEqual(connection.relationship_type, "friend")

    def test_decode_empty_relationships(self):
        json_data: Mapping[str, Any] = {}
        relationships = decode_relationships(json_data, self.event_bus)
        self.assertIsInstance(relationships, Relationships)
        self.assertEqual(len(relationships.get_all_connections()), 0)

    def test_encode_decode_roundtrip(self):
        self.relationships.add_connection("npc1", self.connection)
        encoded = encode_relationships(self.relationships)
        decoded = decode_relationships(encoded, self.event_bus)
        conn = decoded.get_connection("npc1")
        self.assertEqual(conn.relationship_type, "friend")
        self.assertEqual(conn.strength, 75)
        self.assertEqual(conn.steps, 100)


class TestRelationshipEventBus(unittest.TestCase):
    def setUp(self):
        self.eventbus = EventBus()
        connection = Connection("friend", 50, 0, 0.01, 100)
        self.relationships = Relationships(event_bus=self.eventbus)
        self.relationships.add_connection(slug="npc1", connection=connection)

    def test_strength_update_via_eventbus(self):
        self.eventbus.publish(
            "relationship_modified",
            npc_slug="npc1",
            attribute="strength",
            value=80,
        )
        conn = self.relationships.get_connection("npc1")
        self.assertEqual(conn.strength, 80)

    def test_decay_rate_update_via_eventbus(self):
        self.eventbus.publish(
            "relationship_modified",
            npc_slug="npc1",
            attribute="decay_rate",
            value=0.05,
        )
        conn = self.relationships.get_connection("npc1")
        self.assertEqual(conn.decay_rate, 0.05)

    def test_decay_threshold_update_via_eventbus(self):
        self.eventbus.publish(
            "relationship_modified",
            npc_slug="npc1",
            attribute="decay_threshold",
            value=200,
        )
        conn = self.relationships.get_connection("npc1")
        self.assertEqual(conn.decay_threshold, 200)

    def test_invalid_attribute_via_eventbus(self):
        self.eventbus.publish(
            "relationship_modified",
            npc_slug="npc1",
            attribute="unknown_attr",
            value=123,
        )
        conn = self.relationships.get_connection("npc1")
        self.assertEqual(conn.strength, 50)
