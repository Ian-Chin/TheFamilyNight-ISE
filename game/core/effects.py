"""Small particle effects drawn in canvas units, under the sprites.

WalkDust kicks up little square puffs from behind a walker's feet: soft dust
on grass, and a few hopping grey chips on stone. Squares rather than circles,
so the bits sit with the pixel art around them.
"""

import random

import arcade

from ..config import (
    DUST_GRASS_COLOR, DUST_GRAVITY, DUST_INTERVAL, DUST_LIFE, DUST_STONE_CHIP,
    DUST_STONE_COLOR,
)


class WalkDust:
    def __init__(self, stone_areas=()):
        self.stone_areas = stone_areas
        self.particles = []
        self.clock = 0.0

    def on_stone(self, x, y):
        return any(
            left <= x <= right and bottom <= y <= top
            for left, right, bottom, top in self.stone_areas
        )

    def update(self, delta_time, moving, x, feet_y, dx, dy):
        """Age the bits, and kick up new ones while `moving`.

        (dx, dy) is the walking direction; bits land behind it.
        """
        for bit in self.particles:
            bit["age"] += delta_time
            bit["x"] += bit["vx"] * delta_time
            bit["y"] += bit["vy"] * delta_time
            if bit["chip"]:
                bit["vy"] -= DUST_GRAVITY * delta_time
                # Chips bounce off the ground once and settle.
                if bit["y"] < bit["floor"]:
                    bit["y"] = bit["floor"]
                    bit["vy"] = abs(bit["vy"]) * 0.3
                    bit["vx"] *= 0.5
        self.particles = [b for b in self.particles if b["age"] < b["life"]]

        if not moving:
            self.clock = 0.0
            return
        self.clock -= delta_time
        if self.clock > 0:
            return
        self.clock = DUST_INTERVAL
        self.kick(x, feet_y, dx, dy)

    def kick(self, x, feet_y, dx, dy):
        stone = self.on_stone(x, feet_y)
        color = DUST_STONE_COLOR if stone else DUST_GRASS_COLOR
        back_x, back_y = -dx, -dy
        for _ in range(3):
            self.particles.append({
                "x": x + back_x * 10 + random.uniform(-10, 10),
                "y": feet_y + back_y * 4 + random.uniform(0, 5),
                "vx": back_x * random.uniform(12, 30) + random.uniform(-10, 10),
                "vy": random.uniform(10, 24),
                "age": 0.0, "life": DUST_LIFE * random.uniform(0.8, 1.2),
                "size": random.uniform(6, 10), "grow": random.uniform(8, 14),
                "color": color, "chip": False, "floor": 0,
            })
        if stone:
            for _ in range(random.randint(1, 2)):
                self.particles.append({
                    "x": x + random.uniform(-8, 8),
                    "y": feet_y + 2,
                    "vx": back_x * random.uniform(30, 60) + random.uniform(-30, 30),
                    "vy": random.uniform(70, 120),
                    "age": 0.0, "life": DUST_LIFE * 0.9,
                    "size": random.uniform(3, 4.5), "grow": 0,
                    "color": DUST_STONE_CHIP, "chip": True,
                    "floor": feet_y - random.uniform(0, 6),
                })

    def draw(self):
        for bit in self.particles:
            share = bit["age"] / bit["life"]
            size = bit["size"] + bit["grow"] * share
            r, g, b, a = bit["color"]
            arcade.draw_rect_filled(
                arcade.XYWH(round(bit["x"]), round(bit["y"]), size, size),
                (r, g, b, round(a * (1 - share))),
            )
