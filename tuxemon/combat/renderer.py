# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from abc import ABC
from functools import partial
from typing import TYPE_CHECKING, ClassVar

from pygame.rect import Rect
from pygame.surface import Surface
from pygame.transform import flip as pg_flip

from tuxemon import graphics
from tuxemon.animation import Animation, ScheduleType
from tuxemon.combat.utils import build_hud_text
from tuxemon.event import get_event_bus
from tuxemon.formula import config_combat
from tuxemon.platform.const.sizes import PARTY_LIMIT
from tuxemon.prepare import SCALE, SCREEN, SCREEN_RECT
from tuxemon.sprite import CaptureDeviceSprite, HordeSprite, Sprite
from tuxemon.tools import scale
from tuxemon.ui.combat_bars import CombatBars
from tuxemon.ui.combat_hud import CombatLayoutManager
from tuxemon.ui.combat_layout import (
    LayoutManager,
    layout_groups,
    prepare_layout,
    scaled_layouts,
)
from tuxemon.ui.combat_monsters import MonsterSpriteMap
from tuxemon.ui.combat_status import StatusIconManager
from tuxemon.ui.combat_text_display import CombatTextDisplay
from tuxemon.ui.combat_zone import CombatZone
from tuxemon.ui.graphic_box import GraphicBox
from tuxemon.ui.text import TextArea
from tuxemon.ui.text_alignment import HorizontalAlignment

if TYPE_CHECKING:
    from tuxemon.combat.session import CombatSession
    from tuxemon.core.core_effect import ItemEffectResult
    from tuxemon.environment import Environment
    from tuxemon.item.item import Item
    from tuxemon.monster import Monster
    from tuxemon.npc import NPC
    from tuxemon.session import Session
    from tuxemon.states.combat_state import CombatState

logger = logging.getLogger(__name__)

HUD_LAYER = 100


def toggle_visible(sprite: Sprite) -> None:
    sprite.toggle_visible()


class CombatAnimations(ABC):
    """
    Collection of combat animations.

    Mixin-ish thing until things are sorted out.
    Mostly just a collections of methods to animate the sprites

    These methods should not, without [many] exception[s], manipulate
    game/combat state.  These should just move sprites around
    the screen, with the occasional creation/removal of sprites....
    but never game objects.
    """

    name: ClassVar[str] = "CombatAnimations"

    def __init__(
        self,
        session: Session,
        state: CombatState,
        combat_session: CombatSession,
        teams: list[NPC],
    ) -> None:
        self.session = session
        self.state = state
        self.combat_session = combat_session
        self.event_bus = get_event_bus()
        self.sprite_map = MonsterSpriteMap()
        self.capdevs: list[CaptureDeviceSprite] = []
        self.horde_sprite: HordeSprite | None = None
        self.bars = CombatBars()
        layout_manager = LayoutManager(scaled_layouts, layout_groups)
        _layout = prepare_layout(teams, layout_manager)
        self.hud_manager = CombatLayoutManager(_layout)
        self.status_icons = StatusIconManager(state, _layout, self.hud_manager)
        self.combat_zone = CombatZone(SCREEN_RECT)
        self.text_display = CombatTextDisplay(
            get_rect_func=self.hud_manager.get_rect,
            shadow_text_func=self.state.shadow_text,
        )
        self.background_sprite: Sprite | None = None
        self.monsters_just_leveled_up: dict[str, bool] = {}

    def refresh_ui(self, env: Environment) -> None:
        """Call this whenever HP or EXP changes."""
        current_graphics = env.get_battle_graphics()
        self.bars.draw_bars(self.hud_manager.hud_map, current_graphics)

    def show_combat_dialog(self) -> None:
        """Create and show the area where battle messages are displayed."""
        # make the border and area at the bottom of the screen for messages
        rect_screen = SCREEN_RECT.copy()
        rect = Rect(0, 0, rect_screen.w, rect_screen.h // 4)
        rect.bottomright = rect_screen.w, rect_screen.h
        border = graphics.load_and_scale(self.state.borders_filename)
        self.dialog_box = GraphicBox(border, None, self.state.background_color)
        self.dialog_box.rect = rect
        self.state.sprites.add(self.dialog_box, layer=HUD_LAYER)

        # make a text area to show messages
        self.text_area = TextArea(self.state.font, self.state.font_color)
        self.text_area.rect = self.dialog_box.calc_inner_rect(
            self.dialog_box.rect,
        )
        self.state.sprites.add(self.text_area, layer=HUD_LAYER)

    def transition_none_normal(self, env: Environment) -> None:
        """From newly opened to normal."""
        self.animate_parties_in(env)

        for player, layout in self.hud_manager.layout.items():
            self.animate_party_hud_in(env, player, layout["party"][0])

        for player in self.combat_session.players[
            : 2 if self.combat_session.is_trainer_battle else 1
        ]:
            self.state.task(
                partial(self.animate_trainer_leave, player), interval=3
            )

    def blink(self, sprite: Sprite) -> None:
        self.state.task(
            partial(toggle_visible, sprite), interval=0.20, times=8
        )

    def animate_trainer_leave(self, trainer: NPC | Monster) -> None:
        """Animate the trainer leaving the screen."""
        sprite = self.sprite_map.get_sprite(trainer)
        if sprite is None:
            raise KeyError(f"Sprite not found for entity: {trainer.name}")

        x_offset = self.combat_zone.get_horizontal_offset(
            sprite.rect, scale(-150)
        )
        self.state.animate(
            sprite.rect, x=x_offset, relative=True, duration=0.8
        )

    def animate_monster_release(
        self,
        npc: NPC,
        monster: Monster,
        sprite: Sprite,
    ) -> None:
        """
        Animates the release of a monster from a capture device.

        This function coordinates the animation of the capture device falling, the
        monster sprite moving into position, and the capture device opening animation.
        It also plays the combat call sound.
        """
        session = self.combat_session
        self.hud_manager.assign(
            session.count_players, npc, monster, session.is_double
        )
        feet = self.hud_manager.get_feet_position(npc, monster)

        # Load and scale capture device sprite
        capdev = self.state.load_sprite(
            f"gfx/items/{monster.capture_device}.png"
        )
        graphics.scale_sprite(capdev, 0.4)
        capdev.rect.center = (feet[0], feet[1] - scale(60))

        # Animate capture device falling
        fall_time = 0.7
        animate_fall = partial(
            self.state.animate,
            duration=fall_time,
            transition="out_quad",
        )
        animate_fall(capdev.rect, bottom=feet[1], transition="in_back")
        animate_fall(capdev, rotation=720, initial=0)

        # Animate capture device fading away
        delay = fall_time + 0.6
        fade_duration = 0.9
        h = capdev.rect.height
        animate_fade = partial(
            self.state.animate, duration=fade_duration, delay=delay
        )
        animate_fade(capdev, width=1, height=h * 1.5)
        animate_fade(capdev.rect, y=-scale(14), relative=True)

        # Convert capture device sprite for easy fading
        def convert_sprite() -> None:
            capdev.image = graphics.convert_alpha_to_colorkey(capdev.image)
            self.state.animate(
                capdev.image,
                set_alpha=0,
                initial=255,
                duration=fade_duration,
            )

        self.state.task(convert_sprite, interval=delay)
        self.state.task(
            capdev.kill, interval=fall_time + delay + fade_duration
        )

        # Load monster sprite and set final position
        monster_sprite = monster.get_sprite(
            "back" if npc == session.left_player else "front"
        )
        monster_sprite.rect.midbottom = feet
        self.state.sprites.add(monster_sprite)
        self.sprite_map.add_sprite(monster, monster_sprite)

        # Position monster sprite off screen and animate it to final spot
        monster_sprite.rect.top = SCREEN.get_height()
        self.state.animate(
            monster_sprite.rect,
            bottom=feet[1],
            transition="out_quad",
            duration=0.9,
            delay=fall_time + 0.5,
        )

        # Play capture device opening animation
        assert sprite.animation
        sprite.rect.midbottom = feet
        self.state.task(sprite.animation.play, interval=1.3)
        self.state.task(partial(self.state.sprites.add, sprite), interval=1.3)

        # Load and play combat call sound
        self.play_sound_effect(
            monster.combat_call.sfx, monster.combat_call.volume
        )

    def animate_sprite_tackle(self, attacker: Sprite) -> None:
        duration = 0.3
        original_x = attacker.rect.x
        _, horizontal = self.combat_zone.get_zone(attacker.rect)

        delta = (
            scale(14) if horizontal is HorizontalAlignment.LEFT else -scale(14)
        )

        self.state.animate(
            attacker.rect,
            x=original_x + delta,
            duration=duration,
            transition="out_circ",
            yoyo=True,
            yoyo_loops=1,
        )

    def animate_monster_faint(self, monster: Monster) -> None:
        """Animate a monster fainting and remove it."""

        def kill_monster() -> None:
            """Remove the monster's sprite and HUD elements."""
            self.sprite_map.remove_sprite(monster)
            self.status_icons.remove_monster_icons(monster)
            self.hud_manager.delete_hud(monster)

        self.animate_monster_leave(monster)
        self.state.task(kill_monster, interval=2)

        for (
            monsters
        ) in self.combat_session.field_monsters.get_all_monsters().values():
            if monster in monsters:
                monsters.remove(monster)

        self.animate_update_horde_hud()
        # Update the party HUD to reflect the fainted tuxemon
        self.animate_update_party_hud()

    def animate_sprite_take_damage(self, sprite: Sprite) -> None:
        original_x, original_y = sprite.rect.topleft
        animate = partial(
            self.state.animate,
            sprite.rect,
            duration=1,
            transition="in_out_elastic",
        )
        ani = animate(x=original_x, initial=original_x + scale(400))
        # just want the end of the animation, not the entire thing
        ani._elapsed = 0.735
        ani = animate(y=original_y, initial=original_y - scale(400))
        # just want the end of the animation, not the entire thing
        ani._elapsed = 0.735

    def animate_hp(self, env: Environment, monster: Monster) -> None:
        hp_bar = self.bars.get_hp_bar(monster)

        ani = Animation(
            hp_bar,
            value=monster.hp_ratio,
            duration=0.7,
            transition="out_quint",
        )

        ani.schedule(partial(self.refresh_ui, env), ScheduleType.ON_UPDATE)
        ani.schedule(partial(self.refresh_ui, env), ScheduleType.ON_FINISH)
        self.state.animations.add(ani)

    def animate_exp(self, env: Environment, monster: Monster) -> None:
        exp_bar = self.bars.get_exp_bar(monster)
        value_for_new_level = monster.experience_progress_percent

        def register(ani: Animation) -> Animation:
            ani.schedule(partial(self.refresh_ui, env), ScheduleType.ON_UPDATE)
            self.state.animations.add(ani)
            return ani

        if self.monsters_just_leveled_up.get(monster.slug, False):

            def fill_to_max() -> Animation:
                ani = register(
                    self.state.animate(
                        exp_bar, value=1.0, duration=0.3, transition="linear"
                    )
                )
                ani.schedule(
                    partial(self.refresh_ui, env), ScheduleType.ON_FINISH
                )
                return ani

            def animate_new_level_progress() -> Animation:
                exp_bar.value = 0.0
                ani = register(
                    self.state.animate(
                        exp_bar,
                        value=value_for_new_level,
                        duration=0.7,
                        transition="linear",
                        delay=0.5,
                    )
                )
                ani.schedule(
                    partial(self.refresh_ui, env), ScheduleType.ON_FINISH
                )
                return ani

            self.state.chain_animations(
                fill_to_max, animate_new_level_progress
            )
            self.monsters_just_leveled_up[monster.slug] = False
        else:
            ani = register(
                self.state.animate(
                    exp_bar,
                    value=value_for_new_level,
                    duration=0.7,
                    transition="out_quint",
                )
            )
            ani.schedule(partial(self.refresh_ui, env), ScheduleType.ON_FINISH)

    def animate_monster_leave(self, monster: Monster) -> None:
        sprite = self.sprite_map.get_sprite(monster)
        if sprite is None:
            raise KeyError(f"Sprite not found for entity: {monster.name}")

        x_offset = self.combat_zone.get_horizontal_offset(
            sprite.rect, scale(-150)
        )

        cry = (
            monster.combat_call
            if monster.current_hp > 0
            else monster.faint_call
        )

        self.play_sound_effect(cry.sfx, cry.volume)
        self.state.animate(sprite.rect, x=x_offset, relative=True, duration=2)
        self.status_icons.animate_icons(monster, self.state.animate)

    def _update_hud_details(
        self, env: Environment, monster: Monster, hud: Sprite, is_player: bool
    ) -> None:
        """
        Gathers data and delegates drawing of text labels to CombatTextDisplay.
        """
        owner = monster.get_owner()
        trainer_battle = self.combat_session.is_trainer_battle

        symbol = False
        if not is_player:
            left_player = self.combat_session.left_player
            if left_player.tuxepedia.is_caught(monster.slug):
                symbol = True

        label_data = build_hud_text(
            env.get_battle_graphics().menu,
            monster,
            is_player,
            trainer_battle,
            symbol,
        )

        self.text_display.draw_text(
            hud=hud,
            owner=owner,
            label_data=label_data,
        )

    def check_hud(self, monster: Monster, filename: str) -> Sprite:
        """
        Checks whether exists or not a hud, it returns a sprite.
        To avoid building over an existing one.

        Parameters:
            monster: Monster who needs to update the hud.
            filename: Filename of the hud.
        """
        sprite = self.hud_manager.get_hud(monster)
        if sprite is None:
            sprite = self.state.load_sprite(filename, layer=HUD_LAYER)

        return sprite

    def build_hud(
        self,
        env: Environment,
        monster: Monster,
        hud_position: str,
        animate: bool = True,
    ) -> None:
        """
        Builds the HUD for a monster, focusing on creation and animation.
        """
        owner = monster.get_owner()
        hud_rect = self.hud_manager.get_rect(owner, hud_position)

        _, h_align = self.combat_zone.get_zone(hud_rect)
        is_player = h_align is HorizontalAlignment.RIGHT

        hud_graphics = (
            env.get_battle_graphics().hud.hud_player
            if is_player
            else env.get_battle_graphics().hud.hud_opponent
        )

        hud = self.check_hud(monster, hud_graphics)
        hud.base_image = hud.image.copy()
        hud.player = is_player
        self.hud_manager.assign_hud(monster, hud)

        self._update_hud_details(env, monster, hud, is_player)

        if is_player:
            hud.rect.bottomleft = hud_rect.right, hud_rect.bottom
        else:
            hud.rect.bottomright = 0, hud_rect.bottom

        if animate:
            target_pos = (
                {"left": hud_rect.left}
                if is_player
                else {"right": hud_rect.right}
            )
            animate_func = partial(self.state.animate, duration=2.0, delay=1.3)
            animate_func(hud.rect, **target_pos)

            self.animate_hp(env, monster)
            if hud.player:
                self.animate_exp(env, monster)
        else:
            if is_player:
                hud.rect.left = hud_rect.left
            else:
                hud.rect.right = hud_rect.right

    def _load_sprite(
        self, sprite_type: str, position: dict[str, int]
    ) -> Sprite:
        return self.state.load_sprite(sprite_type, **position)

    def animate_party_hud_left(
        self, env: Environment, home: Rect
    ) -> tuple[Sprite | None, int, int]:
        if not (
            self.combat_session.is_trainer_battle
            and not self.combat_session.is_double
        ):
            return None, home.right - scale(13), scale(8)

        hud_data = env.data.get_battle_graphics().hud
        party_layout = env.get_party_layout("opponent", home, HUD_LAYER)

        tray = self._load_sprite(party_layout.path, party_layout.init_pos)
        self.state.animate(
            tray.rect,
            duration=hud_data.animation_duration,
            delay=hud_data.animation_delay,
            **party_layout.target,
        )

        return tray, party_layout.centerx, party_layout.offset

    def animate_party_hud_right(
        self, env: Environment, home: Rect
    ) -> tuple[Sprite, int, int]:
        hud_data = env.data.get_battle_graphics().hud
        party_layout = env.get_party_layout("player", home, HUD_LAYER)

        tray = self._load_sprite(party_layout.path, party_layout.init_pos)
        self.state.animate(
            tray.rect,
            duration=hud_data.animation_duration,
            delay=hud_data.animation_delay,
            **party_layout.target,
        )

        return tray, party_layout.centerx, party_layout.offset

    def animate_party_hud_in(
        self, env: Environment, player: NPC, home: Rect
    ) -> None:
        """
        Animates the party HUD (the arrow thing with balls).

        Parameters:
            player: The player whose HUD is being animated.
            home: Location and size of the HUD.
        """
        _, h_align = self.combat_zone.get_zone(home)

        is_opponent_horde = (
            player is self.combat_session.right_player
            and self.combat_session.is_horde_battle
        )

        if is_opponent_horde:
            tray, _, _ = self.animate_party_hud_left(env, home)

            self.horde_sprite = HordeSprite(
                opponent_party=player.party,
                tray_rect=home,
                shadow_text_func=self.state.shadow_text,
                scale_func=scale,
            )
            self.state.sprites.add(self.horde_sprite, layer=HUD_LAYER)

            animate_func = partial(self.state.animate, duration=2.0, delay=1.5)
            self.horde_sprite.animate_in(animate_func)
            return

        if h_align is HorizontalAlignment.LEFT:
            tray, centerx, offset = self.animate_party_hud_left(env, home)
        else:
            tray, centerx, offset = self.animate_party_hud_right(env, home)

        if tray is None or any(t.wild for t in player.monsters):
            return

        monster_count = player.party.party_size
        positions = (
            [monster_count - i - 1 for i in range(PARTY_LIMIT)]
            if h_align is HorizontalAlignment.LEFT
            else list(range(PARTY_LIMIT))
        )

        scaled_top = scale(1)

        for index, pos in enumerate(positions):
            monster = player.monsters[index] if index < monster_count else None
            centerx_pos = centerx - (pos if monster else index) * offset

            sprite = self._load_sprite(
                env.get_battle_graphics().icons.icon_empty,
                {
                    "top": tray.rect.top + scaled_top,
                    "centerx": centerx_pos,
                    "layer": HUD_LAYER,
                },
            )

            capdev = CaptureDeviceSprite(
                sprite=sprite,
                tray=tray,
                monster=monster,
                icon=env.get_battle_graphics().icons,
            )
            self.capdevs.append(capdev)
            animate = partial(
                self.state.animate, duration=1.5, delay=2.2 + index * 0.2
            )
            capdev.animate_capture(animate)

    def animate_update_party_hud(self) -> None:
        """
        Update the balls in the party HUD to reflect fainted Tuxemon.

        Note:
            Party HUD is the arrow thing with balls.  Yes, that one.
        """
        for dev in self.capdevs:
            prev = dev.state
            if prev != dev.update_state():
                animate = partial(self.state.animate, duration=0.1, delay=0.1)
                dev.animate_capture(animate)

    def animate_update_horde_hud(self) -> None:
        """
        Update the horde HUD to reflect the horde.
        """
        if self.combat_session.is_horde_battle and self.horde_sprite:
            if self.horde_sprite.update_count_display():
                animate_func = partial(
                    self.state.animate, duration=2.0, delay=1.5
                )
                self.horde_sprite.animate_in(animate_func)
            if self.horde_sprite.is_defeated():
                self.state.task(self.horde_sprite.kill, interval=2)
                self.horde_sprite = None

    def update_background(self, bg_path: str) -> None:
        # Clear old
        if hasattr(self, "background_sprite") and self.background_sprite:
            if self.background_sprite in self.state.sprites:
                self.state.sprites.remove(self.background_sprite)
            self.background_sprite = None

        # Load and scale to SCALE only (no stretching to full screen)
        surf = graphics.load_and_scale(bg_path, SCALE)

        # Create a full-screen surface (black by default)
        full_height = SCREEN_RECT.height
        full_width = SCREEN_RECT.width
        full_surf = Surface((full_width, full_height))
        full_surf.fill((0, 0, 0))  # fill rest with black

        # Blit background onto the top of the full surface
        full_surf.blit(surf, (0, 0))

        # Extend last row of background downward to fill gap
        last_row = surf.subsurface(
            Rect(0, surf.get_height() - 1, surf.get_width(), 1)
        )
        for y in range(surf.get_height(), full_height):
            full_surf.blit(last_row, (0, y))

        # Wrap in sprite
        spr = Sprite()
        spr.image = full_surf
        spr.rect = full_surf.get_rect()
        spr.rect.topleft = (0, 0)

        self.state.sprites.add(spr, layer=0)
        self.background_sprite = spr

    def animate_parties_in(self, env: Environment) -> None:
        """Animate the parties entering the battle scene."""
        session = self.combat_session
        assets = env.get_battle_assets()
        self.update_background(assets["background"])

        # Get player and opponent
        player, opponent = session.players
        opp_mon = opponent.monsters[0]
        self.hud_manager.assign(
            session.count_players, opponent, opp_mon, session.is_double
        )
        player_home = self.hud_manager.get_rect(player, "home")
        opp_home = self.hud_manager.get_rect(opponent, "home")

        battle_layout = env.get_battle_layout(
            SCREEN_RECT.size, player_home, opp_home
        )
        back_island = self.state.load_sprite(
            assets["island_back"], **battle_layout.back_island_pos
        )
        front_island = self.state.load_sprite(
            assets["island_front"], **battle_layout.front_island_pos
        )

        # Load and animate opponent
        if session.is_trainer_battle:
            sprite_name = opponent.template.combat_front
            enemy = self.state.load_sprite(
                f"gfx/sprites/player/{sprite_name}.png",
                bottom=back_island.rect.bottom
                - battle_layout.offsets["enemy_y"],
                centerx=back_island.rect.centerx,
            )
            self.sprite_map.add_sprite(opponent, enemy)
        else:
            enemy = opp_mon.get_sprite("front")
            enemy.rect.bottom = (
                back_island.rect.bottom - battle_layout.offsets["monster_y"]
            )
            enemy.rect.centerx = back_island.rect.centerx
            self.sprite_map.add_sprite(opp_mon, enemy)
            session.field_monsters.add_monster(opponent, opp_mon)
            self.update_hud(env, opponent, True, True)

        self.state.sprites.add(enemy)

        # Load and animate player
        player_back = self.state.load_sprite(
            f"gfx/sprites/player/{player.template.combat_front}.png",
            bottom=front_island.rect.centery
            + battle_layout.offsets["player_y"],
            centerx=front_island.rect.centerx,
        )

        self.sprite_map.add_sprite(player, player_back)
        self.flip_sprites(enemy, player_back)
        self.animate_sprites(
            env, enemy, back_island, front_island, player_back
        )

        if not session.is_trainer_battle:
            sound = session.right_player.monsters[0].combat_call
            self.play_sound_effect(sound.sfx, sound.volume)

        self.state.dialog.alert(session.get_start_message(), self.text_area)

    def flip_sprites(self, enemy: Sprite, player_back: Sprite) -> None:
        """Flip the sprites horizontally."""

        def flip() -> None:
            enemy.image = pg_flip(enemy.image, True, False)
            player_back.image = pg_flip(player_back.image, True, False)

        flip()
        self.state.task(flip, interval=1.5)

    def animate_sprites(
        self,
        env: Environment,
        enemy: Sprite,
        back_island: Sprite,
        front_island: Sprite,
        player_back: Sprite,
    ) -> None:
        """Animate the sprites."""
        session = self.combat_session
        graphics = env.get_battle_graphics()

        y_mod = scale(graphics.entry_jump_distance)
        duration = graphics.entry_duration

        animate = partial(
            self.state.animate, transition="out_quad", duration=duration
        )

        # Opponent side
        pos_opp = self.hud_manager.get_rect(session.right_player, "home")
        animate(enemy.rect, back_island.rect, centerx=pos_opp.centerx)
        animate(
            enemy.rect,
            back_island.rect,
            y=-y_mod,
            transition="out_back",
            relative=True,
        )

        # Player side
        pos_pla = self.hud_manager.get_rect(session.left_player, "home")
        animate(player_back.rect, front_island.rect, centerx=pos_pla.centerx)
        animate(
            player_back.rect,
            front_island.rect,
            y=y_mod,
            transition="out_back",
            relative=True,
        )

    def play_sound_effect(
        self, sound: str | None, value: float | None = None
    ) -> None:
        """Play the sound effect."""
        if sound is None:
            return
        volume = value or self.state.client.config.sound_volume
        self.state.client.sound_manager.play_sound(sound, volume)

    def animate_throwing(
        self,
        monster: Monster,
        item: Item,
    ) -> Sprite:
        """
        Animation for throwing the item.

        Parameters:
            monster: The monster being targeted.
            item: The item thrown at the monster.

        Returns:
            The animated item sprite.
        """
        monster_sprite = self.sprite_map.get_sprite(monster)
        if monster_sprite is None:
            raise KeyError(f"Sprite not found for entity: {monster.name}")
        sprite = self.state.load_sprite(item.sprite)
        animate = partial(
            self.state.animate, sprite.rect, transition="in_quad", duration=1.0
        )
        graphics.scale_sprite(sprite, 0.4)
        sprite.rect.center = scale(0), scale(0)
        animate(x=monster_sprite.rect.centerx)
        animate(y=monster_sprite.rect.centery)
        return sprite

    def animate_capture_monster(
        self,
        result: ItemEffectResult,
        monster: Monster,
        item: Item,
        sprite: Sprite,
        texts: tuple[str, str, str],
    ) -> None:
        """
        Animation for capturing monsters.

        Parameters:
            result: Result of the capture plugin.
            monster: The monster being captured.
            item: The capture device used to capture the monster.
            sprite: The sprite to animate.
            messages: Success header, success and failture text.
        """
        num_shakes = result.num_shakes
        is_captured = result.success
        success_header, success_body, failure_text = texts
        monster_sprite = self.sprite_map.get_sprite(monster)
        if monster_sprite is None:
            raise KeyError(f"Sprite not found for entity: {monster.name}")

        capdev = self.animate_throwing(monster, item)
        hit_time = 1.0
        self.state.task(
            partial(toggle_visible, monster_sprite), interval=hit_time
        )

        if sprite.animation:
            self.state.task(sprite.animation.play, interval=hit_time)
            self.state.task(
                partial(self.state.sprites.add, sprite), interval=hit_time
            )

        sprite.rect.midbottom = monster_sprite.rect.midbottom

        def shake_up() -> Animation:
            return self.state.animate(
                capdev.rect,
                y=scale(3),
                relative=True,
                duration=0.1,
                transition="in_quad",
            )

        def shake_down() -> Animation:
            return self.state.animate(
                capdev.rect,
                y=-scale(6),
                relative=True,
                duration=0.2,
                transition="in_quad",
            )

        def shake_up2() -> Animation:
            return self.state.animate(
                capdev.rect,
                y=scale(3),
                relative=True,
                duration=0.1,
                transition="in_quad",
            )

        for i in range(num_shakes):
            start = 1.8 + i * 1.0
            self.state.chain_animations(
                shake_up, shake_down, shake_up2, start_delay=start
            )

        breakout_time = 1.8 + num_shakes * 1.0

        # SUCCESS CASE
        if is_captured:

            def kill_monster() -> None:
                self.sprite_map.remove_sprite(monster)
                self.hud_manager.delete_hud(monster)

            self.state.task(kill_monster, interval=2 + num_shakes)

            full_msg = f"{success_header}\n{success_body}"

            msg_delay = num_shakes / 2
            dialog_delay = (
                num_shakes
                + msg_delay
                + len(full_msg) * config_combat.letter_time
            )

            def show_success() -> None:
                self.state.dialog.alert(full_msg, self.text_area)

            self.state.task(show_success, interval=dialog_delay)

            self.state.task(
                partial(self.event_bus.publish, "clean_combat"),
                interval=dialog_delay + 4,
            )

        # FAILURE CASE
        else:

            def show_monster() -> None:
                toggle_visible(monster_sprite)
                self.play_sound_effect(
                    monster.combat_call.sfx, monster.combat_call.volume
                )

            def capture_capsule() -> None:
                if sprite.animation:
                    sprite.animation.play()
                capdev.kill()

            def blink_monster() -> None:
                self.blink(sprite)

            def show_failure() -> None:
                self.state.dialog.alert(failure_text, self.text_area)

            self.state.task(show_monster, interval=breakout_time)
            self.state.task(capture_capsule, interval=breakout_time)
            self.state.task(blink_monster, interval=breakout_time + 0.5)

            failure_delay = (
                breakout_time + len(failure_text) * config_combat.letter_time
            )
            self.state.task(show_failure, interval=failure_delay)

            full_msg = failure_text

        callback_delay = (
            breakout_time + len(full_msg) * config_combat.letter_time + 1.0
        )

        self.state.task(
            lambda: self.event_bus.publish(
                "capture_finished", monster=monster, is_captured=is_captured
            ),
            interval=callback_delay,
        )

    def update_hud(
        self, env: Environment, character: NPC, animate: bool, delete: bool
    ) -> None:
        """
        Updates the Heads-Up Display (HUD) for monsters belonging to the given character.

        Parameters:
            character: The character whose monsters' HUDs should be refreshed.
            animate: Whether to animate HUD transitions.
            delete: Whether to delete existing HUDs before updating.
        """
        monsters = self.combat_session.field_monsters.get_monsters(character)
        if not monsters:
            return

        # Cleanup old HUDs if requested
        if delete:
            for monster in monsters:
                self.hud_manager.delete_hud(monster)

        # Assign and Build HUDs
        # If there is only 1 monster, we use the ID "hud".
        # If there are multiple, we use "hud0", "hud1", etc.
        is_multi = len(monsters) > 1

        for i, monster in enumerate(monsters):
            hud_id = f"hud{i}" if is_multi else "hud"
            self.build_hud(env, monster, hud_id, animate)
