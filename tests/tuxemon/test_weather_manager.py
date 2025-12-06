# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2025 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock, patch

from tuxemon.db import Temperature, Wind
from tuxemon.world.weather import (
    WeatherTransitionRecord,
    WeatherTransitionRule,
    WeatherTransitionRulesModel,
    WorldWeatherManager,
)


class TestWorldWeatherManager(unittest.TestCase):
    def setUp(self):
        patcher = patch("tuxemon.world.weather.Weather")
        self.addCleanup(patcher.stop)
        self.mock_weather_class = patcher.start()

        def dummy_weather(slug):
            obj = MagicMock()
            obj.slug = slug
            obj.current_temperature = Temperature("mild")
            obj.current_wind = Wind("calm")
            return obj

        self.mock_weather_class.side_effect = dummy_weather

        rule = WeatherTransitionRule(next_slug="rainy", trigger_chance=1.0)
        self.rules_model = WeatherTransitionRulesModel(
            transitions={"sunny": [rule]}
        )

    def test_initial_weather(self):
        mgr = WorldWeatherManager(
            initial_slug="sunny", rules_model=self.rules_model
        )
        self.assertEqual(mgr.current_slug, "sunny")
        self.assertEqual(mgr.elapsed_time, 0.0)

    def test_force_transition_records_elapsed(self):
        mgr = WorldWeatherManager(
            initial_slug="sunny", rules_model=self.rules_model
        )
        mgr._elapsed_duration_seconds = 5.0
        mgr.force_transition("rainy")
        history = mgr.get_transition_history()
        self.assertEqual(len(history), 1)
        rec = history[0]
        self.assertEqual(rec.from_slug, "sunny")
        self.assertEqual(rec.to_slug, "rainy")
        self.assertEqual(rec.sim_time, 5.0)

    def test_advance_turn_triggers_transition(self):
        mgr = WorldWeatherManager(
            initial_slug="sunny", rules_model=self.rules_model, seed=42
        )
        mgr._elapsed_duration_seconds = 3.0
        mgr.advance_turn()
        history = mgr.get_transition_history()
        self.assertEqual(len(history), 1)
        rec = history[0]
        self.assertEqual(rec.from_slug, "sunny")
        self.assertEqual(rec.to_slug, "rainy")
        self.assertEqual(rec.sim_time, 3.0)

    def test_no_transition_when_chance_zero(self):
        zero_rule = WeatherTransitionRule(
            next_slug="rainy", trigger_chance=0.0
        )
        rules_model = WeatherTransitionRulesModel(
            transitions={"sunny": [zero_rule]}
        )
        mgr = WorldWeatherManager(
            initial_slug="sunny", rules_model=rules_model, seed=42
        )
        mgr._elapsed_duration_seconds = 5.0
        mgr.advance_turn()
        self.assertEqual(len(mgr.get_transition_history()), 0)

    def test_validator_cumulative_chance_exceeds_one(self):
        bad_rules = [
            WeatherTransitionRule(next_slug="rainy", trigger_chance=0.6),
            WeatherTransitionRule(next_slug="stormy", trigger_chance=0.6),
        ]
        with self.assertRaises(ValueError):
            WeatherTransitionRulesModel(transitions={"sunny": bad_rules})

    def test_validator_invalid_duration_bounds(self):
        bad_rule = WeatherTransitionRule(
            next_slug="rainy",
            trigger_chance=1.0,
            min_duration_seconds=10,
            max_duration_seconds=5,
        )
        with self.assertRaises(ValueError):
            WeatherTransitionRulesModel(transitions={"sunny": [bad_rule]})

    def test_temperature_requirement_blocks_transition(self):
        rule = WeatherTransitionRule(
            next_slug="rainy",
            trigger_chance=1.0,
            required_temperature=Temperature("hot"),
        )
        rules_model = WeatherTransitionRulesModel(
            transitions={"sunny": [rule]}
        )
        mgr = WorldWeatherManager(
            initial_slug="sunny", rules_model=rules_model
        )
        mgr._elapsed_duration_seconds = 5.0
        mgr.advance_turn()
        self.assertEqual(len(mgr.get_transition_history()), 0)

    def test_wind_requirement_blocks_transition(self):
        rule = WeatherTransitionRule(
            next_slug="rainy",
            trigger_chance=1.0,
            required_wind=Wind("stormy"),
        )
        rules_model = WeatherTransitionRulesModel(
            transitions={"sunny": [rule]}
        )
        mgr = WorldWeatherManager(
            initial_slug="sunny", rules_model=rules_model
        )
        mgr._elapsed_duration_seconds = 5.0
        mgr.advance_turn()
        self.assertEqual(len(mgr.get_transition_history()), 0)

    def test_multiple_transitions_accumulate_history(self):
        mgr = WorldWeatherManager(
            initial_slug="sunny", rules_model=self.rules_model, seed=42
        )
        mgr._elapsed_duration_seconds = 2.0
        mgr.advance_turn()
        mgr._elapsed_duration_seconds = 4.0
        mgr.force_transition("rainy")
        history = mgr.get_transition_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].from_slug, "sunny")
        self.assertEqual(history[1].from_slug, "rainy")

    def test_deterministic_transitions_with_seed(self):
        rule = WeatherTransitionRule(next_slug="rainy", trigger_chance=1.0)
        rules_model = WeatherTransitionRulesModel(
            transitions={"sunny": [rule]}
        )

        mgr1 = WorldWeatherManager(
            initial_slug="sunny", rules_model=rules_model, seed=123
        )
        mgr2 = WorldWeatherManager(
            initial_slug="sunny", rules_model=rules_model, seed=123
        )

        mgr1._elapsed_duration_seconds = 2.0
        mgr1.advance_turn()
        mgr2._elapsed_duration_seconds = 2.0
        mgr2.advance_turn()

        h1 = mgr1.get_transition_history()
        h2 = mgr2.get_transition_history()
        self.assertEqual(
            [(r.from_slug, r.to_slug, r.sim_time) for r in h1],
            [(r.from_slug, r.to_slug, r.sim_time) for r in h2],
        )

    def test_performance_many_updates(self):
        rules_model = WeatherTransitionRulesModel(
            transitions={
                "sunny": [
                    WeatherTransitionRule(
                        next_slug="rainy", trigger_chance=1.0
                    )
                ],
                "rainy": [
                    WeatherTransitionRule(
                        next_slug="sunny", trigger_chance=1.0
                    )
                ],
            }
        )
        mgr = WorldWeatherManager(
            initial_slug="sunny", rules_model=rules_model, seed=42
        )

        for i in range(1000):
            mgr._elapsed_duration_seconds = i + 1
            mgr.advance_turn()

        history = mgr.get_transition_history()
        self.assertEqual(len(history), 1000)
        for rec in history:
            self.assertIsNotNone(rec.from_slug)
            self.assertIsNotNone(rec.to_slug)

    def test_weighted_randomness_with_multiple_rules(self):
        rules = [
            WeatherTransitionRule(next_slug="rainy", trigger_chance=0.7),
            WeatherTransitionRule(next_slug="stormy", trigger_chance=0.3),
        ]
        rules_model = WeatherTransitionRulesModel(transitions={"sunny": rules})

        mgr = WorldWeatherManager(
            initial_slug="sunny", rules_model=rules_model, seed=99
        )

        outcomes = []
        for i in range(100):
            mgr._elapsed_duration_seconds = i + 1
            mgr.advance_turn()
            if mgr.current_slug != "sunny":
                outcomes.append(mgr.current_slug)
                mgr.set_weather("sunny")

        rainy_count = outcomes.count("rainy")
        stormy_count = outcomes.count("stormy")

        self.assertGreater(rainy_count, 0)
        self.assertGreater(stormy_count, 0)

        self.assertGreater(rainy_count, stormy_count)

    def test_history_integrity_sequence(self):
        rules_model = WeatherTransitionRulesModel(
            transitions={
                "sunny": [
                    WeatherTransitionRule(
                        next_slug="rainy", trigger_chance=1.0
                    )
                ],
                "rainy": [
                    WeatherTransitionRule(
                        next_slug="sunny", trigger_chance=1.0
                    )
                ],
            }
        )
        mgr = WorldWeatherManager(
            initial_slug="sunny", rules_model=rules_model, seed=42
        )

        for i in range(20):
            mgr._elapsed_duration_seconds = i + 1
            mgr.advance_turn()

        history = mgr.get_transition_history()
        self.assertGreater(len(history), 0)

        for i in range(1, len(history)):
            prev = history[i - 1]
            curr = history[i]
            self.assertEqual(
                prev.to_slug,
                curr.from_slug,
                f"History integrity broken at index {i}: {prev.to_slug} != {curr.from_slug}",
            )

    def test_alternating_pattern_in_history(self):
        rules_model = WeatherTransitionRulesModel(
            transitions={
                "sunny": [
                    WeatherTransitionRule(
                        next_slug="rainy", trigger_chance=1.0
                    )
                ],
                "rainy": [
                    WeatherTransitionRule(
                        next_slug="sunny", trigger_chance=1.0
                    )
                ],
            }
        )
        mgr = WorldWeatherManager(
            initial_slug="sunny", rules_model=rules_model, seed=42
        )

        for i in range(10):
            mgr._elapsed_duration_seconds = i + 1
            mgr.advance_turn()

        history = mgr.get_transition_history()
        self.assertGreater(len(history), 0)

        expected_sequence = []
        current = "sunny"
        for i in range(len(history)):
            next_slug = "rainy" if current == "sunny" else "sunny"
            expected_sequence.append((current, next_slug))
            current = next_slug

        actual_sequence = [(rec.from_slug, rec.to_slug) for rec in history]
        self.assertEqual(actual_sequence, expected_sequence)

    def test_serialization_of_transition_record(self):
        rec = WeatherTransitionRecord(
            from_slug="sunny", to_slug="rainy", sim_time=5.0
        )
        as_dict = rec.__dict__
        self.assertIn("from_slug", as_dict)
        self.assertIn("to_slug", as_dict)
        self.assertIn("sim_time", as_dict)
        self.assertIn("real_time", as_dict)

    def test_no_rules_means_weather_stuck(self):
        rules_model = WeatherTransitionRulesModel(transitions={})
        mgr = WorldWeatherManager(
            initial_slug="sunny", rules_model=rules_model
        )
        mgr._elapsed_duration_seconds = 5.0
        mgr.advance_turn()
        self.assertEqual(len(mgr.get_transition_history()), 0)
        self.assertEqual(mgr.current_slug, "sunny")

    def test_last_transition_property_updates(self):
        mgr = WorldWeatherManager(
            initial_slug="sunny", rules_model=self.rules_model
        )
        mgr._elapsed_duration_seconds = 3.0
        mgr.advance_turn()
        self.assertIsNotNone(mgr.last_transition)
        self.assertEqual(mgr.last_transition.next_slug, "rainy")

    def test_real_time_field_is_populated(self):
        mgr = WorldWeatherManager(
            initial_slug="sunny", rules_model=self.rules_model
        )
        mgr._elapsed_duration_seconds = 2.0
        mgr.advance_turn()
        history = mgr.get_transition_history()
        self.assertGreater(len(history), 0)
        rec = history[0]
        self.assertIsInstance(rec.real_time, float)
        self.assertGreater(rec.real_time, 0.0)
