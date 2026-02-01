# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass

from tuxemon.db import SpatialCondition
from tuxemon.event.eventcondition import EventCondition
from tuxemon.session import Session
from tuxemon.tools import compare

logger = logging.getLogger(__name__)


@dataclass
class TimeIsCondition(EventCondition):
    """
    Evaluates a comparison against a real-time property provided by the
    session's TimeHandler. This allows scripts to react to the current
    hour, season, weekday, stage of day, and other time-based values.

    Script usage:
        .. code-block::

            is time_is <property>,<operation>,<value>

    Script parameters:
        property:
            The name of a time property to evaluate. Valid options include:
            "hour", "day_of_year", "year", "weekday", "leap_year",
            "daytime", "stage_of_day", and "season".

        operation:
            A comparison operator supported by the `compare` helper
            (e.g., "equals", "not_equals", "greater_than", "less_than").

        value:
            A literal value to compare against. Numeric values are compared
            numerically (e.g., hour > 17), while non-numeric values are
            compared as strings (e.g., season equals winter).

    Example:
        .. code-block::

            is time_is hour,greater_than,17
            is time_is season,equals,winter
            is time_is stage_of_day,equals,dusk
    """

    name = "time_is"

    def test(self, session: Session, condition: SpatialCondition) -> bool:
        snapshot = session.time.get_time_variables()

        property_name: str = condition.parameters[0]
        operation: str = condition.parameters[1]
        raw_value: str = condition.parameters[2]

        if not hasattr(snapshot, property_name):
            logger.error(f"Invalid time property '{property_name}'")
            return False

        value = getattr(snapshot, property_name)
        numeric_properties = {"hour", "day_of_year", "year"}

        # Numeric path
        if property_name in numeric_properties:
            try:
                v1 = float(value)
                v2 = float(raw_value)
            except ValueError:
                logger.error(f"Expected numeric value for '{property_name}'")
                return False
            return compare(operation, v1, v2)

        # String path (equals / not_equals only)
        if operation in ("equals", "=="):
            return str(value) == raw_value

        if operation in ("not_equals", "!="):
            return str(value) != raw_value

        logger.error(
            f"Operation '{operation}' not valid for non-numeric property '{property_name}'"
        )
        return False
