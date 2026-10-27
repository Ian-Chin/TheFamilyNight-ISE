"""Playable characters and the family standing around the garden."""

import math
import random

import arcade

from . import textures
from .config import (
    CHAO_BITE_GAP, CHAO_BITE_LEAN, CHAO_BLINK_EVERY, CHAO_BLINK_TIME,
    CHAO_CHEW_BOB, CHAO_CHEW_SQUASH, CHAO_CHEW_TIME, CHAO_CHEWS,
    CHAO_FEET_DROP, CHAO_FEET_SHIFT, CHAO_FEET_SWING, CHAO_FEET_SWING_TIME,
    CHAO_GESTURE, CHAO_MORSEL, CHAO_PLATE_REACH, CHAO_REACH_TIME,
    CHAO_SEAT_LIFT, CHAO_SWAY_ANGLE, CHAO_SWAY_BOB, CHAO_SWAY_TIME,
    CHAO_TALK_BURST, CHAO_TALK_FLAP, FEET_HEIGHT, NPC_IDLE_FRAME, RIM_DARK, RIM_GLOW, FEET_WIDTH, IDLE_PERIOD, JUMP_DURATION, JUMP_HEIGHT,
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
    """A family member standing in the garden, breathing gently if their art
    has an idle sheet (see IDLE_SHEETS). The owning view calls `animate`."""

    def __init__(self, name, art_file, center_x, center_y, height, glow=True):
        self.idle_frames = textures.idle_frames(art_file, glow)
        texture = (self.idle_frames[0] if self.idle_frames
                   else textures.character(art_file, glow))
        super().__init__(texture, height, center_x, center_y)
        self.name = name
        # Everyone breathes on their own beat.
        self.idle_clock = random.uniform(0, NPC_IDLE_FRAME * 4)

    def animate(self, delta_time):
        if not self.idle_frames:
            return
        self.idle_clock += delta_time
        index = int(self.idle_clock / NPC_IDLE_FRAME) % len(self.idle_frames)
        self.texture = self.idle_frames[index]


def _ease(t):
    """Smooth 0 to 1 over t in 0..1, slow at both ends."""
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def _between(a, b, t):
    t = _ease(t)
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


class Diner:
    """Someone sat on a stool at the dinner table, built from their parts.

    The head rests over the stool and the shoes hang below it, toward the
    table. Everyone blinks now and then. Eaters reach the table-side hand out
    to the plate, bring a bite up to the mouth and chew it; the rest chat,
    mouth flapping in bursts and hands bobbing. `phase` offsets the cycles so
    the table does not move in step.
    """

    def __init__(self, art, x, y, height, eating, toward, phase=0.0):
        self.parts = parts = textures.diner_parts(art)
        self.scale = scale = height / parts.art_height
        self.stool = (x, y)
        self.eating = eating
        self.toward = toward   # +1 if the table is to the right, -1 if left
        self.visible = True    # off while they are away from the table
        self.clock = phase
        self.blink_every = CHAO_BLINK_EVERY + phase * 0.37

        face = parts.faces[(False, "drawn")]
        margin = RIM_DARK + RIM_GLOW
        head_h = face.height - 2 * margin
        # The middle of the whole figure, placed so the head sits on the stool.
        self.origin = (x, y + CHAO_SEAT_LIFT
                       - (parts.head_at[1] - head_h / 2) * scale)
        self.head_rest = self.at(parts.head_at)
        self.hands_rest = [self.at(spot) for spot in parts.hands_at]
        self.mouth = self.at(parts.mouth_at)
        half_head = (face.width - 2 * margin) * scale / 2
        self.plate = (self.head_rest[0] + toward * (half_head + CHAO_PLATE_REACH),
                      self.head_rest[1] - head_h * scale * 0.15)
        feet_middle = sum(spot[0] for spot in parts.feet_at) / 2
        self.feet_rest = [
            (x + toward * CHAO_FEET_SHIFT + (spot[0] - feet_middle) * scale,
             y - CHAO_FEET_DROP)
            for spot in parts.feet_at
        ]
        # The hand nearer the table is the one that eats.
        self.active = 1 if toward > 0 else 0

        def sprite(texture, size=None):
            sprite = arcade.Sprite(texture, scale=scale)
            if size:
                sprite.scale = size / texture.width
            return sprite

        self.feet = [sprite(foot) for foot in parts.feet]
        self.head = sprite(face)
        self.hands = [sprite(hand) for hand in parts.hands]
        self.morsel = sprite(textures.morsel_texture(), CHAO_MORSEL)
        self.sprites = arcade.SpriteList()
        for part in (*self.feet, self.head, *self.hands, self.morsel):
            self.sprites.append(part)
        self.update_seat(0.0)

    def at(self, spot):
        """A part's spot in art pixels, in canvas units."""
        return (self.origin[0] + spot[0] * self.scale,
                self.origin[1] + spot[1] * self.scale)

    @property
    def ground_y(self):
        """Depth for sorting, like a standing character's."""
        return self.stool[1]

    def draw(self):
        if self.visible:
            self.sprites.draw(pixelated=True)

    def update_seat(self, delta_time):
        self.clock += delta_time
        hands = list(self.hands_rest)
        mouth, bob, squash, lean, morsel = "drawn", 0.0, 0.0, 0.0, None
        if self.eating:
            mouth, bob, squash, lean, morsel = self.eat(hands)
        else:
            mouth, bob, lean = self.chat(hands)

        shut = (self.clock % self.blink_every) < CHAO_BLINK_TIME
        self.head.texture = self.parts.faces[(shut, mouth)]
        self.head.scale_x = self.scale
        self.head.scale_y = self.scale * (1 - squash)
        # Squashed from the top, so the head stays sat on the stool.
        self.head.center_x = self.head_rest[0]
        self.head.center_y = (self.head_rest[1] + bob
                              - squash * self.head.texture.height * self.scale / 2)
        # Arcade turns clockwise, so a positive angle tips the head right.
        self.head.angle = lean * self.toward

        for hand, (hx, hy) in zip(self.hands, hands):
            hand.position = (hx, hy)
        self.morsel.visible = morsel is not None
        if morsel:
            self.morsel.position = morsel

        swing = 2 * math.pi * self.clock / CHAO_FEET_SWING_TIME
        for index, (foot, (fx, fy)) in enumerate(zip(self.feet, self.feet_rest)):
            foot.position = (fx, fy + CHAO_FEET_SWING * math.sin(swing + index * math.pi))

    def eat(self, hands):
        """One bite: reach, lift, chew, rest. Moves the eating hand in place."""
        chewing = CHAO_CHEWS * CHAO_CHEW_TIME
        reach = CHAO_REACH_TIME
        t = self.clock % (2 * reach + chewing + CHAO_BITE_GAP)
        rest = self.hands_rest[self.active]
        mouth, bob, squash, morsel = "drawn", 0.0, 0.0, None
        if t < reach:
            hand = _between(rest, self.plate, t / reach)
        elif t < 2 * reach:
            hand = _between(self.plate, self.mouth, (t - reach) / reach)
            morsel = (hand[0], hand[1] + 4)
            if t > 2 * reach - 0.15:
                mouth = "open"   # opening up for the bite
        elif t < 2 * reach + chewing:
            chew_t = t - 2 * reach
            hand = _between(self.mouth, rest, chew_t / reach)
            mouth = "open" if (chew_t % CHAO_CHEW_TIME) < CHAO_CHEW_TIME / 2 else "chew"
            chew = math.sin(math.pi * (chew_t % CHAO_CHEW_TIME) / CHAO_CHEW_TIME)
            bob = chew * CHAO_CHEW_BOB
            squash = chew * CHAO_CHEW_SQUASH
        else:
            hand = rest
        hands[self.active] = hand
        bite = 2 * reach + chewing
        lean = CHAO_BITE_LEAN * math.sin(math.pi * t / bite) if t < bite else 0.0
        return mouth, bob, squash, lean, morsel

    def chat(self, hands):
        """Talking in bursts, hands bobbing along. Moves the hands in place."""
        wave = math.sin(2 * math.pi * self.clock / CHAO_SWAY_TIME)
        bob = (wave + 1) / 2 * CHAO_SWAY_BOB
        lean = wave * CHAO_SWAY_ANGLE
        mouth = "drawn"
        if (self.clock % (2 * CHAO_TALK_BURST)) < CHAO_TALK_BURST:
            if int(self.clock / CHAO_TALK_FLAP) % 2:
                mouth = "open"
            beat = 2 * math.pi * self.clock / (4 * CHAO_TALK_FLAP)
            for index, (hx, hy) in enumerate(hands):
                hands[index] = (hx, hy + CHAO_GESTURE * max(0.0, math.sin(beat + index * math.pi)))
        return mouth, bob, lean


class Terry(Character):
    """Terry walks in eight directions and hops on demand.

    With `carrying`, he holds the food tray from the prep table instead.
    With `glow` off, his art has the dark contour but no pale halo.
    """

    def __init__(self, center_x, center_y, carrying=False, glow=True):
        walk, jump, idle = textures.terry_frames(glow)
        height = TERRY_HEIGHT
        if carrying:
            # The tray rides above his head in some frames, so the carry art
            # is sized to match his body on the shortest walk frame, where
            # the tray is held low, not on the frame box.
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
