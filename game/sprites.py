"""Playable characters and the family standing around the garden."""

import arcade

from . import textures
from .config import (
    FEET_HEIGHT, FEET_WIDTH, IDLE_PERIOD, JUMP_DURATION, JUMP_HEIGHT,
    SHADOW_ALPHA, SHADOW_ASPECT, SHADOW_COLOR, SHADOW_JUMP_SHRINK, SHADOW_RISE,
    SHADOW_WIDTH, TERRY_HEIGHT, WALK_FRAME_TIME, WALK_SPEED,
)


class Character(arcade.Sprite):
    """A sprite that stands on the ground and casts a shadow there."""

    def __init__(self, texture, height, center_x, center_y):
        super().__init__(
            texture,
            scale=height / texture.height,
            center_x=center_x,
            center_y=center_y,
        )
        self.ground_y = center_y

    def draw_shadow(self):
        """Draw the ground shadow; call this before the sprite itself.

        It follows `ground_y` rather than the drawn position, so it stays on
        the floor while the character is in the air, fading and shrinking as
        they rise.
        """
        lift = max(0.0, self.center_y - self.ground_y) / JUMP_HEIGHT
        shrink = 1 - SHADOW_JUMP_SHRINK * min(lift, 1.0)
        width = abs(self.width) * SHADOW_WIDTH * shrink
        height = width * SHADOW_ASPECT
        feet_y = self.ground_y - abs(self.height) / 2
        arcade.draw_ellipse_filled(
            self.center_x, feet_y + SHADOW_RISE, width, height,
            (*SHADOW_COLOR, round(SHADOW_ALPHA * shrink)),
        )


class NPC(Character):
    """A family member standing still in the garden."""

    def __init__(self, name, art_file, center_x, center_y, height):
        super().__init__(
            textures.character(art_file), height, center_x, center_y
        )
        self.name = name


class Terry(Character):
    """Terry walks in eight directions and hops on demand."""

    def __init__(self, center_x, center_y):
        self.walk_frames, self.jump_frames, self.idle_frames = textures.terry_frames()
        super().__init__(
            self.idle_frames[0], TERRY_HEIGHT, center_x, center_y
        )
        self.frame_index = 0
        self.frame_timer = 0.0
        self.idle_index = 0
        self.idle_clock = 0.0
        self.jump_timer = None

    @property
    def jumping(self):
        return self.jump_timer is not None

    def start_jump(self):
        if not self.jumping:
            self.jump_timer = 0.0

    @property
    def feet_box(self):
        """(left, right, bottom, top) of the box Terry collides with.

        Only his feet are solid, so scenery drawn behind him may overlap the
        rest of the sprite without pushing him away.
        """
        half_w = abs(self.width) * FEET_WIDTH / 2
        bottom = self.ground_y - abs(self.height) / 2
        return (
            self.center_x - half_w, self.center_x + half_w,
            bottom, bottom + FEET_HEIGHT,
        )

    def block_x(self, obstacles, moved_right):
        """Undo a step into scenery along x by resting against its edge."""
        for left, right, bottom, top in obstacles:
            f_left, f_right, f_bottom, f_top = self.feet_box
            if f_right <= left or f_left >= right:
                continue
            if f_top <= bottom or f_bottom >= top:
                continue
            half_w = (f_right - f_left) / 2
            self.center_x = left - half_w if moved_right else right + half_w

    def block_y(self, obstacles, moved_up):
        """Undo a step into scenery along y by resting against its edge."""
        for left, right, bottom, top in obstacles:
            f_left, f_right, f_bottom, f_top = self.feet_box
            if f_right <= left or f_left >= right:
                continue
            if f_top <= bottom or f_bottom >= top:
                continue
            # `ground_y` sits above the feet box, so shift by the overlap.
            self.ground_y += (bottom - f_top) if moved_up else (top - f_bottom)

    def update_movement(self, delta_time, dx, dy, bounds, obstacles=()):
        left, right, bottom, top = bounds
        half_w = abs(self.width) / 2
        half_h = abs(self.height) / 2

        # One axis at a time, so a blocked direction still slides along the
        # other one instead of sticking to the corner of an obstacle.
        if dx or dy:
            length = (dx * dx + dy * dy) ** 0.5
            if dx:
                self.center_x += dx / length * WALK_SPEED * delta_time
                self.center_x = min(
                    max(self.center_x, left + half_w), right - half_w
                )
                self.block_x(obstacles, moved_right=dx > 0)
            if dy:
                self.ground_y += dy / length * WALK_SPEED * delta_time
                self.ground_y = min(
                    max(self.ground_y, bottom + half_h), top - half_h
                )
                self.block_y(obstacles, moved_up=dy > 0)

        self.center_x = min(max(self.center_x, left + half_w), right - half_w)
        self.ground_y = min(max(self.ground_y, bottom + half_h), top - half_h)

        if dx:
            # The art only draws a front-facing Terry, so mirror him to face
            # the direction of travel.
            self.scale_x = abs(self.scale_x) * (1 if dx > 0 else -1)

        self.animate(delta_time, moving=bool(dx or dy))

    def animate(self, delta_time, moving):
        if self.jumping:
            self.jump_timer += delta_time
            progress = self.jump_timer / JUMP_DURATION
            if progress >= 1.0:
                self.jump_timer = None
                self.center_y = self.ground_y
                self.frame_index = 0
                self.frame_timer = 0.0
                self.texture = self.idle_frames[self.idle_index]
                return
            index = min(int(progress * len(self.jump_frames)), len(self.jump_frames) - 1)
            self.texture = self.jump_frames[index]
            self.center_y = self.ground_y + JUMP_HEIGHT * (4 * progress * (1 - progress))
            return

        self.center_y = self.ground_y
        if not moving:
            self.frame_index = 0
            self.frame_timer = 0.0
            self.idle_clock = (self.idle_clock + delta_time) % IDLE_PERIOD
            phase = self.idle_clock / IDLE_PERIOD
            self.idle_index = int(phase * len(self.idle_frames)) % len(self.idle_frames)
            self.texture = self.idle_frames[self.idle_index]
            return

        self.idle_clock = 0.0
        self.frame_timer += delta_time
        while self.frame_timer >= WALK_FRAME_TIME:
            self.frame_timer -= WALK_FRAME_TIME
            self.frame_index = (self.frame_index + 1) % len(self.walk_frames)
        self.texture = self.walk_frames[self.frame_index]
