# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from datetime import datetime

import pytest

from tuxemon.time_handler import TimeHandler


@pytest.fixture
def time_handler():
    return TimeHandler(hemisphere="northern")


def test_get_current_time(time_handler):
    assert isinstance(time_handler.get_current_time(), datetime)


@pytest.mark.parametrize(
    "dt,expected",
    [
        (datetime(2022, 1, 1, 0, 0, 0), "false"),
        (datetime(2022, 1, 1, 6, 0, 0), "true"),
        (datetime(2022, 1, 1, 18, 0, 0), "false"),
        (datetime(2022, 1, 1, 12, 0, 0), "true"),
    ],
)
def test_day_night_cycle(time_handler, dt, expected):
    assert time_handler._get_day_night_cycle(dt) == expected


@pytest.mark.parametrize(
    "dt,expected",
    [
        (datetime(2022, 1, 1, 0, 0, 0), "night"),
        (datetime(2022, 1, 1, 4, 0, 0), "dawn"),
        (datetime(2022, 1, 1, 7, 0, 0), "dawn"),
        (datetime(2022, 1, 1, 10, 0, 0), "morning"),
        (datetime(2022, 1, 1, 14, 0, 0), "afternoon"),
        (datetime(2022, 1, 1, 17, 0, 0), "dusk"),
        (datetime(2022, 1, 1, 20, 0, 0), "night"),
    ],
)
def test_stage_of_day(time_handler, dt, expected):
    assert time_handler._get_stage_of_day(dt) == expected


@pytest.mark.parametrize(
    "dt,expected",
    [
        (datetime(2022, 1, 1), "winter"),
        (datetime(2022, 3, 20), "winter"),
        (datetime(2022, 6, 20), "spring"),
        (datetime(2022, 9, 20), "summer"),
        (datetime(2022, 12, 20), "autumn"),
    ],
)
def test_season_northern(time_handler, dt, expected):
    assert time_handler._get_season(dt) == expected


@pytest.mark.parametrize(
    "dt,expected",
    [
        (datetime(2022, 1, 1), "summer"),
        (datetime(2022, 3, 20), "summer"),
        (datetime(2022, 6, 20), "autumn"),
        (datetime(2022, 9, 20), "winter"),
        (datetime(2022, 12, 20), "spring"),
    ],
)
def test_season_southern(dt, expected):
    handler = TimeHandler(hemisphere="southern")
    assert handler._get_season(dt) == expected


@pytest.mark.parametrize(
    "year,expected",
    [
        (2020, True),
        (2019, False),
        (2024, True),
        (1900, False),
        (2000, True),
    ],
)
def test_is_leap_year(time_handler, year, expected):
    assert time_handler.is_leap_year(year) == expected


def test_get_time_variables(time_handler):
    time_handler.get_current_time = lambda: datetime(2022, 6, 20, 9, 30, 0)

    vars = time_handler.get_time_variables()

    assert vars.hour == 9
    assert vars.day_of_year == 171  # June 20, 2022
    assert vars.year == 2022
    assert vars.weekday == "monday"
    assert vars.leap_year == "false"
    assert vars.daytime == "true"
    assert vars.stage_of_day == "morning"
    assert vars.season == "spring"
