# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import logging
import subprocess
import sys


def get_git_hash() -> str:
    """Gets the current Git hash."""
    if getattr(sys, "frozen", False):
        # Frozen builds have no git checkout, and spawning subprocesses
        # from a Win32GUI app with no console can raise OSError
        # (WinError 6, invalid std handles) that the clauses below
        # would not catch.
        return "N/A"
    try:
        githash = (
            subprocess.check_output(
                ["git", "describe", "--always"],
                stdin=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            .strip()
            .decode()
        )
        return f"Git Hash: {githash}"
    except (OSError, subprocess.CalledProcessError):
        logging.warning("Git hash not available.")
        return "N/A"
