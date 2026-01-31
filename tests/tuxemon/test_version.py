# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import pytest

from tuxemon.version import (
    Version,
    VersionComparator,
    __version__,
    version_info,
)


def test_string_roundtrip():
    v = Version("1.2.3")
    assert str(v) == "1.2.3"


@pytest.mark.parametrize(
    "input_str",
    [
        "1.2.3",
        "1.2.3a1",
        "1.2.3b2",
        "1.2.3rc3",
        "1.2.3.post1",
        "1.2.3.dev4",
        "1!1.2.3",  # epoch
        "1.2.3+local",  # local version
    ],
)
def test_valid_pep440_versions(input_str):
    Version(input_str)  # should not raise


@pytest.mark.parametrize(
    "invalid",
    [
        "1.2.x",  # invalid character
        "1..3",  # empty segment
        "1.2.3-foo",  # invalid prerelease (SemVer style)
        "1.2.3+foo+bar",  # invalid local version (only one + allowed)
    ],
)
def test_invalid_pep440_versions(invalid):
    with pytest.raises(ValueError):
        Version(invalid)


def test_equality():
    assert Version("1.2.3") == Version("1.2.3")
    assert Version("1.2.3") != Version("1.2.4")


def test_comparison():
    assert Version("1.2.3") < Version("1.2.4")
    assert Version("1.2.3a1") < Version("1.2.3b1")
    assert Version("1.2.3b1") < Version("1.2.3rc1")
    assert Version("1.2.3rc1") < Version("1.2.3")
    assert Version("1.2.3") < Version("1.2.3.post1")
    assert Version("1.2.3.dev1") < Version("1.2.3")


@pytest.mark.parametrize(
    "v1,v2,expected",
    [
        (Version("1.2.3"), Version("1.2.3"), 0),
        (Version("1.2.4"), Version("1.2.3"), 1),
        (Version("1.2.3"), Version("1.2.4"), -1),
        (Version("2.0.0"), Version("1.9.9"), 1),
        (Version("1.0.0"), Version("2.0.0"), -1),
    ],
)
def test_version_comparator(v1, v2, expected):
    assert VersionComparator.compare(v1, v2) == expected


def test_dunder_version_is_string():
    assert isinstance(__version__, str)


def test_version_info_contains_dunder_version():
    assert __version__ in version_info()
