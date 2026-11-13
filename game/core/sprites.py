import random

import arcade

from . import textures
from ..config import (
    CHAO_EAT_FRAME_TIMES, CHAO_HEAD_RISE, CHAO_SHEET_RES, CHAO_TALK_FRAME_TIMES,
    FEET_HEIGHT, FEET_WIDTH, IDLE_PERIOD, JUMP_DURATION, JUMP_HEIGHT, NPC_IDLE_FRAME,
    SHADOW_ALPHA, SHADOW_ASPECT, SHADOW_COLOR, SHADOW_JUMP_SHRINK, SHADOW_RISE,
    SHADOW_WIDTH, TERRY_HEIGHT, WALK_FRAME_TIME, WALK_SPEED,
)


class Character(arcade.Sprite):
    def __init__(self, texture, height, center_x, center_y):
        super().__init__(
            texture,
            scale=height / texture.height,
            center_x=center_x,
            center_y=center_y,
        )
        self.ground_y = center_y

    def draw_shadow(self):
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
    def __init__(self, name, art_file, center_x, center_y, height, glow=True):
        self.idle_frames = textures.idle_frames(art_file, glow)
        texture = (self.idle_frames[0] if self.idle_frames
                   else textures.character(art_file, glow))
        super().__init__(texture, height, center_x, center_y)
        self.name = name
        self.idle_clock = random.uniform(0, NPC_IDLE_FRAME * 4)

    def animate(self, delta_time):
        if not self.idle_frames:
            return
        self.idle_clock += delta_time
        index = int(self.idle_clock / NPC_IDLE_FRAME) % len(self.idle_frames)
        self.texture = self.idle_frames[index]


class Diner:
    def __init__(self, name, x, y, height, eating, phase=0.0):
        kind = "eat" if eating else "talk"
        self.frames = textures.diner_frames(name, kind)
        self.frame_times = CHAO_EAT_FRAME_TIMES if eating else CHAO_TALK_FRAME_TIMES
        self.stool = (x, y)
        self.head_rest = (x, y + height * CHAO_HEAD_RISE)
        self.visible = True    # off while they are away from the table
        self.clock = phase

        self.sprite = arcade.Sprite(self.frames[0], scale=1 / CHAO_SHEET_RES,
                                    center_x=x, center_y=y)
        self.sprites = arcade.SpriteList()
        self.sprites.append(self.sprite)
        self.update_seat(0.0)

    @property
    def ground_y(self):
        return self.stool[1]

    def draw(self):
        if self.visible:
            self.sprites.draw(pixelated=True)

    def update_seat(self, delta_time):
        self.clock += delta_time
        t = self.clock % sum(self.frame_times)
        for index, time in enumerate(self.frame_times):
            if t < time:
                break
            t -= time
        self.sprite.texture = self.frames[index]


class Terry(Character):
    def __init__(self, center_x, center_y, carrying=False, glow=True):
        walk, jump, idle = textures.terry_frames(glow)
        height = TERRY_HEIGHT
        if carrying:
            body = TERRY_HEIGHT * textures.body_share(walk[0])
            walk, jump, idle = textures.terry_carry_frames()
            height = body / min(map(textures.body_share, walk))
        self.walk_frames, self.jump_frames, self.idle_frames = walk, jump, idle
        super().__init__(self.idle_frames[0], height, center_x, center_y)
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
        half_w = abs(self.width) * FEET_WIDTH / 2
        bottom = self.ground_y - abs(self.height) / 2
        return (
            self.center_x - half_w, self.center_x + half_w,
            bottom, bottom + FEET_HEIGHT,
        )

    def block_x(self, obstacles, moved_right):
        for left, right, bottom, top in obstacles:
            f_left, f_right, f_bottom, f_top = self.feet_box
            if f_right <= left or f_left >= right:
                continue
            if f_top <= bottom or f_bottom >= top:
                continue
            half_w = (f_right - f_left) / 2
            self.center_x = left - half_w if moved_right else right + half_w

    def block_y(self, obstacles, moved_up):
        for left, right, bottom, top in obstacles:
            f_left, f_right, f_bottom, f_top = self.feet_box
            if f_right <= left or f_left >= right:
                continue
            if f_top <= bottom or f_bottom >= top:
                continue
            self.ground_y += (bottom - f_top) if moved_up else (top - f_bottom)

    def update_movement(self, delta_time, dx, dy, bounds, obstacles=()):
        left, right, bottom, top = bounds
        half_w = abs(self.width) / 2
        half_h = abs(self.height) / 2

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
