# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Platform-specific implementations and configurations.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional, Protocol

__all__ = (
    "init",
    "mixer",
    "get_user_storage_dir",
    "get_system_storage_dirs",
    "is_android",
)

logger = logging.getLogger(__name__)


class MusicProtocol(Protocol):
    def load(self, filename: str) -> None: ...
    def play(
        self, loops: int = 0, start: float = 0.0, fade_ms: int = 0
    ) -> None: ...
    def stop(self) -> None: ...
    def pause(self) -> None: ...
    def unpause(self) -> None: ...
    def fadeout(self, time: int) -> None: ...
    def set_volume(self, volume: float) -> None: ...
    def get_volume(self) -> float: ...
    def get_busy(self) -> bool: ...


class MixerProtocol(Protocol):
    def pre_init(
        self,
        *,
        frequency: int,
        size: int,
        channels: int,
        buffer: int,
    ) -> None: ...

    music: MusicProtocol


class DummyMusic(MusicProtocol):
    def load(self, filename: str) -> None:
        pass

    def play(
        self, loops: int = 0, start: float = 0.0, fade_ms: int = 0
    ) -> None:
        pass

    def stop(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def unpause(self) -> None:
        pass

    def fadeout(self, time: int) -> None:
        pass

    def set_volume(self, volume: float) -> None:
        pass

    def get_volume(self) -> float:
        return 0.0

    def get_busy(self) -> bool:
        return False


class DummyMixer(MixerProtocol):
    def pre_init(self, *args: Any, **kwargs: Any) -> None:
        pass

    music: MusicProtocol = DummyMusic()


class AndroidContextProtocol(Protocol):
    def getExternalFilesDir(self, arg: Optional[str]) -> Any: ...


class AndroidModuleProtocol(Protocol):
    context: AndroidContextProtocol


_pygame_mixer_in_use: bool = False
android_module: Optional[AndroidModuleProtocol] = None
mixer: MixerProtocol = DummyMixer()


def is_android() -> bool:
    """Checks if the platform is Android."""
    return android_module is not None


def _init_mixer() -> None:
    """
    Determines and initializes the appropriate sound mixer (Android or Pygame).
    Sets the global 'mixer' and '_pygame_mixer_in_use' variables.
    """
    global android_module, mixer, _pygame_mixer_in_use

    try:
        import android
        import android.mixer as android_mixer

        mixer = android_mixer
        android_module = android
    except ImportError:
        pass
    else:
        logger.info("Using Android mixer")
        _pygame_mixer_in_use = False
        return

    try:
        import pygame.mixer as pygame_mixer

        mixer = pygame_mixer  # replaces DummyMixer
        _pygame_mixer_in_use = True
    except ImportError:
        logger.error("Neither Android nor Pygame mixer found")
    else:
        logger.info("Using Pygame mixer")


def _pre_init_sound() -> None:
    """
    Initializes the sound system settings for low latency.
    Requires _init_mixer() to have been called first.
    """
    if _pygame_mixer_in_use and mixer is not None:
        logger.debug("pre-init pygame mixer")
        try:
            # Use mixer.pre_init() to set low-latency settings
            mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
        except Exception as e:
            logger.error(f"Failed to initialize Pygame mixer: {e}")


def init() -> None:
    """
    Initializes platform-specific sub-systems.
    This includes selecting the sound mixer and calling pre_init() for low latency.
    This function should be called before pygame.init().
    """
    _init_mixer()
    _pre_init_sound()


def get_user_storage_dir() -> Path:
    """
    Legacy wrapper: returns the user storage directory.
    """
    return UserStorage(android_module).user_dir()


def get_system_storage_dirs() -> Sequence[Path]:
    """
    Legacy wrapper: returns system storage directories.
    """
    return SystemStorage(android_module).system_dirs()


class SystemStorage:
    """
    Cross-platform abstraction for system storage directories.
    Provides immutable storage paths for built-in mods/resources.
    """

    def __init__(self, android_module: Optional[Any] = None) -> None:
        self.android_module = android_module

    def system_dirs(self) -> Sequence[Path]:
        """
        Return system storage directories depending on platform.
        """
        paths: list[Path] = []

        if self.android_module is None:
            # Linux / Unix-like defaults
            paths.extend(
                [
                    Path("/usr/share/tuxemon/"),
                    Path("/usr/local/share/tuxemon/"),
                ]
            )

            # Respect XDG_DATA_DIRS
            try:
                xdg_data_dirs = os.environ.get("XDG_DATA_DIRS", "")
                if xdg_data_dirs:
                    for data_dir in xdg_data_dirs.split(":"):
                        path = Path(data_dir) / "tuxemon"
                        if path.is_dir():
                            paths.append(path)
                        else:
                            logger.debug(
                                f"Checked non-existent XDG data directory: {path}"
                            )
            except Exception as e:
                logger.error(f"Error handling XDG_DATA_DIRS: {e}")

        else:
            # Android-specific immutable storage
            try:
                # APK assets (read-only)
                # NOTE: getAssets() is not a real filesystem path.
                asset_dir = Path(self.android_module.context.getAssets())
                paths.append(asset_dir)

                # OBB expansion files
                obb_dir = Path(
                    self.android_module.context.getObbDir().getPath()
                )
                if obb_dir.is_dir():
                    paths.append(obb_dir)

            except Exception as e:
                logger.error(f"Error handling Android system storage: {e}")

        return paths

    def list_mods(self) -> list[str]:
        """
        Return a list of available mods/resources from system storage.
        """
        mods: list[str] = []
        for directory in self.system_dirs():
            if directory.is_dir():
                for item in directory.iterdir():
                    if item.is_dir():
                        mods.append(item.name)
        return mods


class UserStorage:
    """
    Cross-platform abstraction for user storage directories.
    Provides mutable storage paths for saves, configs, cache, downloaded mods.
    """

    def __init__(self, android_module: Optional[Any] = None) -> None:
        self.android_module = android_module

    def user_dir(self) -> Path:
        """
        Return the user storage directory depending on platform.
        """
        if self.android_module is None:
            return Path.home() / ".tuxemon"

        try:
            return Path(
                self.android_module.context.getExternalFilesDir(None).getPath()
            )
        except Exception as e:
            logger.error(f"Error handling Android user storage: {e}")
            return Path.home() / ".tuxemon"

    def ensure_dirs(self) -> None:
        """
        Ensure that required user subdirectories exist.
        """
        base = self.user_dir()
        for sub in ["saves", "config", "mods", "cache"]:
            path = base / sub
            path.mkdir(parents=True, exist_ok=True)
