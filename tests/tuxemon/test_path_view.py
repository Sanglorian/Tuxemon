# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from tuxemon.entity.path import PathView


def test_empty_pathview():
    pv = PathView([])
    assert len(pv) == 0
    assert not pv
    assert pv.next() is None
    assert pv.consume() is None


def test_next_and_consume():
    pv = PathView([(1, 1), (2, 2)])
    assert pv.next() == (2, 2)
    assert pv.consume() == (2, 2)
    assert pv.next() == (1, 1)


def test_push():
    pv = PathView([])
    pv.push((3, 3))
    assert pv.next() == (3, 3)
    assert len(pv) == 1


def test_extend_reversed():
    pv = PathView([(0, 0)])
    pv.extend_reversed([(1, 1), (2, 2)])
    # reversed input → appended as 2,2 then 1,1
    assert list(pv) == [(0, 0), (2, 2), (1, 1)]
    assert pv.next() == (1, 1)


def test_iteration_and_len():
    pv = PathView([(1, 1), (2, 2)])
    assert list(pv) == [(1, 1), (2, 2)]
    assert len(pv) == 2


def test_repr():
    pv = PathView([(1, 1)])
    assert "PathView" in repr(pv)
