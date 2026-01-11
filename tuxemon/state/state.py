# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
import random
from abc import ABC
from collections.abc import Callable, Iterable
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar

from pygame.rect import Rect

from tuxemon.event import get_event_bus
from tuxemon.event.eventbus import Listener
from tuxemon.graphics import load_animated_sprite, load_sprite
from tuxemon.prepare import SCREEN_SIZE
from tuxemon.session import local_session
from tuxemon.sprite import Sprite, SpriteGroup
from tuxemon.state.animation_group import AnimationGroup

if TYPE_CHECKING:
    from pygame.sprite import Group
    from pygame.surface import Surface

    from tuxemon.animation import (
        Animation,
        ScheduledFunction,
        Task,
        TaskBase,
    )
    from tuxemon.platform.events import PlayerInput

logger = logging.getLogger(__name__)


class State(ABC):
    """This is a prototype class for States.

    All states should inherit from it. No direct instances of this
    class should be created. Update must be overloaded in the child class.

    Overview of Methods:
     * resume        - Called each time state is updated for first time
     * update        - Called each frame while state is active
     * process_event - Called when there is a new input event
     * pause         - Called when state is no longer active
     * shutdown      - Called before state is destroyed
    """

    name: ClassVar[str] = "State"
    rect = Rect((0, 0), SCREEN_SIZE)
    transparent = False  # ignore all background/borders
    force_draw = False  # draw even if completely under another state

    def __init__(self) -> None:
        """
        Constructor

        Attributes:
            force_draw: If True, state will never be skipped in drawing phase.
            rect: Area of the screen will be drawn on.

        Important!  The state must be ready to be drawn after this is called.
        """
        self.start_time = 0.0
        self.current_time = 0.0

        self.anim = AnimationGroup()

        # All sprites that draw on the screen
        self.sprites: SpriteGroup[Sprite] = SpriteGroup()

        self.client = local_session.client
        self.event_bus = get_event_bus()

        self._scheduled_task: Task | None = None

    def __init_subclass__(cls: type[State], **kwargs: Any) -> None:
        """Ensure subclasses define a class variable 'name'."""
        super().__init_subclass__(**kwargs)
        if "name" not in cls.__dict__:
            logger.error(f"Missing 'name' in subclass: {cls.__name__}")
            raise TypeError(
                f"{cls.__name__} must define a class variable 'name'"
            )

    @property
    def animations(self) -> Group[TaskBase]:
        return self.anim._group

    def load_sprite(self, filename: str, **kwargs: Any) -> Sprite:
        """Load a sprite and add it to this state."""
        layer = kwargs.pop("layer", 0)
        sprite = load_sprite(filename, **kwargs)
        self.sprites.add(sprite, layer=layer)
        return sprite

    def load_animated_sprite(
        self, filenames: Iterable[str], delay: float, **kwargs: Any
    ) -> Sprite:
        """Load an animated sprite and add it to this state."""
        layer = kwargs.pop("layer", 0)
        sprite = load_animated_sprite(filenames, delay, **kwargs)
        self.sprites.add(sprite, layer=layer)
        return sprite

    def animate(self, *targets: Any, **kwargs: Any) -> Animation:
        """
        Animate something in this state.

        Animations are processed even while state is inactive.

        Parameters:
            targets: Targets of the Animation.
            kwargs: Attributes and their final value.

        Returns:
            Resulting animation.
        """
        return self.anim.animate(*targets, **kwargs)

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
        return self.anim.task(
            func,
            on_finish=on_finish,
            on_update=on_update,
            interval=interval,
            times=times,
            **kwargs,
        )

    def chain_animations(
        self, *fns: Callable[[], Animation], start_delay: float = 0.0
    ) -> None:
        self.anim.chain_animations(*fns, start_delay=start_delay)

    def remove_animations_of(self, target: Any) -> None:
        """
        Given and object, remove any animations that it is used with.

        Parameters:
            target: Object whose animations should be removed.
        """
        self.anim.remove_of(target)

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        """
        Handles player input events.

        This function is only called when the
        player provides input such as pressing a key or clicking the mouse.

        Since this is part of a chain of event handlers, the return value
        from this method becomes input for the next one. Returning None
        signifies that this method has dealt with an event and wants it
        exclusively. Return the event and others can use it as well.

        You should return None if you have handled input here.

        Parameters:
            event: Player input event.

        Returns:
            ``None`` if the event should not be passed to the next
            handlers. Otherwise, return the input event.
        """
        return event

    def update(self, time_delta: float) -> None:
        """
        Time update function for state. Must be overloaded in children.

        Parameters:
            time_delta: Amount of time in fractional seconds since last update.
        """
        self.anim.update(time_delta)
        self.sprites.update(time_delta)

    def draw(self, surface: Surface) -> None:
        """
        Render the state to the surface passed. Must be overloaded in children.

        Do not change the state of any game entities. Every draw should be the
        same for a given game time. Any game changes should be done during
        update.

        Parameters:
            surface: Surface to be rendered onto.
        """

    def resume(self) -> None:
        """
        Called before update when state is newly in focus.

        This will be called:
        * before next update
        * after a pop operation which causes this state to be in focus

        After being called, state will begin to receive player input.
        Could be called several times over lifetime of state.

        Example uses: starting music, open menu, starting animations,
        timers, etc.
        """
        self.publish("state_resume")

    def pause(self) -> None:
        """
        Called when state is pushed back in the stack, allowed to pause.

        This will be called:
        * after update when state is pushed back
        * before being shutdown

        After being called, state will no longer receive player input.
        Could be called several times over lifetime of state.

        Example uses: stopping music, sounds, fading out, making state
        graphics dim, etc.
        """
        self.publish("state_pause")

    def shutdown(self) -> None:
        """
        Called when state is removed from stack and will be destroyed.

        This will be called:
        * after update when state is popped

        Make sure to release any references to objects that may cause
        cyclical dependencies.
        """
        self.publish("state_shutdown")

    def stop_scheduled_callbacks(self) -> None:
        """Stops any further scheduled callbacks by killing the task."""
        if self._scheduled_task:
            self._scheduled_task.abort()
            self._scheduled_task = None

    def schedule_callback(
        self,
        frequency: float,
        callback: Callable[[], None],
        min_frequency: float = 0.5,
        max_frequency: float = 5,
    ) -> None:
        """
        Schedules a callback function to execute at randomized intervals.

        This utility method sets up repeated execution of a given callback
        by scheduling it within a dynamic time frame.

        - Stops scheduling if the frequency is set to zero.
        - Ensures the execution interval falls within the defined limits
            (`min_frequency` to `max_frequency`).
        - Introduces randomization to prevent predictable timing patterns.
        - Executes the callback function immediately after scheduling.

        Parameters:
            frequency: The base frequency that determines execution intervals.
            callback: The function to be executed at each scheduled interval.
            min_frequency: The minimum allowed execution delay. Defaults to 0.5.
            max_frequency: The maximum allowed execution delay. Defaults to 5.
        """
        if frequency == 0.0:
            return
        _frequency = min(max_frequency, max(min_frequency, frequency))
        time = (min_frequency + min_frequency * random.random()) * _frequency
        self._scheduled_task = self.task(
            partial(self.schedule_callback, _frequency, callback),
            interval=time,
        )
        callback()

    def subscribe(
        self, event_name: str, callback: Callable[..., None], priority: int = 0
    ) -> None:
        self.event_bus.subscribe(event_name, callback, priority)

    def unsubscribe(
        self, event_name: str, callback: Callable[..., None]
    ) -> None:
        if self.event_bus.has_listeners_for_event(event_name):
            self.event_bus.unsubscribe(event_name, callback)

    def publish(self, event_name: str, *args: Any, **kwargs: Any) -> None:
        if self.event_bus.has_listeners_for_event(event_name):
            self.event_bus.publish(event_name, *args, **kwargs)

    def replace_events(self, event_name: str, events: list[Listener]) -> None:
        self.event_bus.clear_event(event_name)

        for listener in events:
            self.event_bus.subscribe(
                event_name,
                listener.callback,
                priority=listener.priority,
            )
