"""Playable characters."""

import arcade

from . import textures
from .config import (
    IDLE_PERIOD, JUMP_DURATION, JUMP_HEIGHT, SHADOW_ALPHA, SHADOW_ASPECT,
    SHADOW_COLOR, SHADOW_JUMP_SHRINK, SHADOW_RISE, SHADOW_WIDTH, TERRY_HEIGHT,
    WALK_FRAME_TIME, WALK_SPEED,
)


class Terry(arcade.Sprite):
    """Terry walks in eight directions and hops on demand."""

    def __init__(self, center_x, center_y):
        self.walk_frames, self.jump_frames, self.idle_frames = textures.terry_frames()
        first = self.idle_frames[0]
        super().__init__(
            first,
            scale=TERRY_HEIGHT / first.height,
            center_x=center_x,
            center_y=center_y,
        )
        self.ground_y = center_y
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

    def draw_shadow(self):
        """Draw the ground shadow; call this before the sprite itself.

        It follows `ground_y` rather than the drawn position, so it stays on
        the floor while Terry is in the air, fading and shrinking as he rises.
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

    def update_movement(self, delta_time, dx, dy, bounds):
        if dx or dy:
            length = (dx * dx + dy * dy) ** 0.5
            self.center_x += dx / length * WALK_SPEED * delta_time
            self.ground_y += dy / length * WALK_SPEED * delta_time

        left, right, bottom, top = bounds
        half_w = abs(self.width) / 2
        half_h = abs(self.height) / 2
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
