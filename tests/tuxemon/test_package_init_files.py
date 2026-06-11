# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Guard against missing __init__.py files in the tuxemon package.

Plain Python and the Android APK tolerate directories without
__init__.py (PEP 420 namespace packages), but the cx_Freeze Windows
build does not: modules in such directories are silently unimportable
at runtime. This has caused real bugs that only appeared in the
frozen exe — event behaviors not loading (events firing without their
guard conditions) and technique effects not loading (every technique
"missing"). This test makes the failure visible in CI instead of in
the shipped installer.
"""

import unittest
from pathlib import Path

TUXEMON_ROOT = Path(__file__).resolve().parent.parent.parent / "tuxemon"


class TestPackageInitFiles(unittest.TestCase):
    def test_every_module_dir_has_init(self) -> None:
        missing = []
        for path in sorted(TUXEMON_ROOT.rglob("*.py")):
            directory = path.parent
            # Walk up to the package root so intermediate dirs are
            # checked too (a missing parent breaks all children).
            while directory != TUXEMON_ROOT.parent:
                if not (directory / "__init__.py").exists():
                    missing.append(directory)
                directory = directory.parent
        missing = sorted(set(missing))
        self.assertEqual(
            missing,
            [],
            "Directories with Python modules but no __init__.py "
            "(these break the cx_Freeze Windows build): "
            + ", ".join(str(d.relative_to(TUXEMON_ROOT.parent)) for d in missing),
        )


if __name__ == "__main__":
    unittest.main()
