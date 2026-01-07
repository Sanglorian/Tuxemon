# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from typing import Any

from pygame.sprite import Group

from tuxemon.animation import (
    Animation,
    ScheduledFunction,
    ScheduleType,
    Task,
)

logger = logging.getLogger(__name__)


class AnimationGroup:
    def __init__(self) -> None:
        self._group: Group[Task | Animation] = Group()

    def animate(self, *targets: Any, **kwargs: Any) -> Animation:
        ani = Animation(*targets, **kwargs)
        self._group.add(ani)
        return ani

    def task(
        self,
        func: ScheduledFunction,
        *,
        on_finish: ScheduledFunction | None = None,
        on_update: ScheduledFunction | None = None,
        interval: float = 0,
        times: int = 1,
        **kwargs: Any,
    ) -> Task:
        """
        Mirror the original State.task behavior:

        - require `func` to be callable
        - support on_finish / on_update
        - support additional callbacks via keyword names that match ScheduleType
        - validate schedule types and callables
        """
        if not callable(func):
            raise ValueError("Must provide a function to be called")

        task = Task(func, interval=interval, times=times)
        callbacks_to_schedule: dict[ScheduleType, ScheduledFunction] = {}

        if on_finish is not None:
            callbacks_to_schedule[ScheduleType.ON_FINISH] = on_finish
        if on_update is not None:
            callbacks_to_schedule[ScheduleType.ON_UPDATE] = on_update

        for key, value in kwargs.items():
            try:
                schedule_type = ScheduleType(key)
                if schedule_type in task._valid_schedules:
                    if callable(value):
                        callbacks_to_schedule[schedule_type] = value
                    else:
                        raise TypeError(
                            f"Callback for '{key}' must be callable."
                        )
                else:
                    raise ValueError
            except ValueError:
                raise ValueError(
                    f"Invalid callback trigger: '{key}'. "
                    f"Valid options: {[s.value for s in task._valid_schedules]}"
                )

        for when, callback in callbacks_to_schedule.items():
            task.schedule(callback, when)
            logger.debug(
                f"Scheduled callback for Task(id={id(task)}) at {when.value}."
            )

        self._group.add(task)
        return task

    def update(self, dt: float) -> None:
        self._group.update(dt)

    def clear(self) -> None:
        """
        Abort any abortable animations/tasks and clear the group.
        """
        for anim in list(self._group):
            if hasattr(anim, "abort"):
                anim.abort()
        self._group.empty()

    def remove_of(self, target: Any) -> None:
        """
        Remove animations whose targets reference `target`, mirroring original behavior.
        """
        animations = {ani for ani in self._group if isinstance(ani, Animation)}
        to_remove = [
            ani
            for ani in animations
            if any(td.target_ref() == target for td in ani.targets)
        ]

        if not to_remove:
            logger.debug(f"No animations found for target: {target}")
        else:
            logger.debug(
                f"Removing {len(to_remove)} animations for target={target}"
            )

        self._group.remove(*to_remove)
