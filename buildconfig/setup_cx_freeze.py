#!/usr/bin/python
"""
Build the Windows binary package using cx_Freeze (Python 3.10+).

Do NOT run from a virtual environment.
"""

import logging
import os
import sys
from pathlib import Path

from cx_Freeze import Executable, setup

from tuxemon.database.yaml_utils import load_yaml

# Ensure tuxemon package is discoverable when run from buildconfig/
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

logger = logging.getLogger(__name__)

# Prevent SDL from opening a window during build
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "disk"


def load_config(config_file: str = "build_config.yaml"):
    config_path = BASE_DIR / config_file
    try:
        return load_yaml(config_path)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    config = load_config()

    build_exe_options = {
        "packages": config["packages"],
        "excludes": config["excludes"],
        "includes": config["includes"],
        "include_files": config["include_files"],
    }

    setup(
        name=config["name"],
        version=config["version"],
        description=config["description"],
        options={"build_exe": build_exe_options},
        executables=[
            Executable(
                config["executable"],  # run_tuxemon.py
                base=config["base"],
                icon=config["icon"],
                # No target_name → cx_Freeze outputs run_tuxemon.exe
            )
        ],
    )

    # Stamp the commit into the build so a running exe can report exactly
    # which code it was built from (read by run_tuxemon.py at startup).
    sha = os.environ.get("GITHUB_SHA", "unknown")
    for build_dir in Path("build").glob("exe.*"):
        info = build_dir / "build_info.txt"
        info.write_text(
            f"{config['name']} {config['version']} commit {sha}\n",
            encoding="utf-8",
        )
        print(f"Wrote {info}")

    # Dynamically imported plugins are invisible to cx_Freeze's static
    # analysis; if one is missing from the output the exe still builds
    # but breaks at runtime (e.g. events firing without conditions,
    # techniques always missing). Fail the build instead.
    critical_modules = [
        "tuxemon/event/behaviors/talk",
        "tuxemon/event/behaviors/door",
        "tuxemon/event/conditions/button_pressed",
        "tuxemon/event/actions/teleport",
        "tuxemon/core/effects/damage",
        "tuxemon/core/conditions",
    ]
    for build_dir in Path("build").glob("exe.*"):
        lib_dir = build_dir / "lib"
        missing = [
            mod
            for mod in critical_modules
            if not list(lib_dir.glob(f"{mod}*"))
        ]
        if missing:
            sys.exit(
                f"Frozen build at {build_dir} is missing critical "
                f"plugin modules: {missing}. Check for directories "
                "without __init__.py (cx_Freeze skips them)."
            )
        print(f"Verified critical plugin modules present in {build_dir}")

    logger.info("Build completed successfully.")
