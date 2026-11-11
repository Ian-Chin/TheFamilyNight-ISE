"""Round 2 of the bus scene: the highway home, seen from behind the bus.

The road runs away to a horizon and everything on it is a flat pixel sprite
sized by how far off it is. traffic.py decides what is on the road and what
hits what; this file only draws it, plays the sounds and runs the screens
around the game, with the same widgets the other scenes use.

The ground is not a picture. It is a stack of flat strips, one per ROW_H of
canvas, each as wide as the road is at that distance. The strips never move:
only their colours swap as the road slides under them, which is what makes
the stripes run toward the camera.
"""

import functools
import math
import random

import arcade

from ...config import (
    HEIGHT, PLANK_PAD, TEXT_BRIGHT, TEXT_DIM, TEXT_HOVER, TEXT_SHADOW, WIDTH,
)
from ...core import achievements, audio, textures
from ...core.widgets import TitleCard
from . import highway_art
from .config import (
    BACKDROP_SCALE, BACKDROP_SINK, BAND, BUS_WIDTH, BUS_Z, CAR_PAINTS, DASH_ON,
    DASH_PERIOD, DASH_W, FAR_Z, GRASS, HAZE, HIGHWAY_DURATION, HIGHWAY_FADE,
    HIGHWAY_HINT, HIGHWAY_HINT_TIME, HIGHWAY_KICKER,
    HIGHWAY_LOSE_MESSAGE, HIGHWAY_LOSE_TITLE, HIGHWAY_MIN_LIVES, HIGHWAY_TAGLINE,
    HIGHWAY_TITLE, HORIZON, KPH_PER_UNIT, LANE_PAINT, NEAR_MISSES_FOR_ACHIEVEMENT,
    PROP_GAP, PROP_X, PROPS, ROAD_HALF, ROW_H, RUMBLE, RUMBLE_BAND, RUMBLE_W,
    TARMAC, TRUCK_PAINTS, VAN_PAINTS, VIEW_DEPTH,
)
from .base import BusView
from .hud import bread_textures
from .traffic import Traffic

FADE_IN_Z = 3.0      # road units over which far things fade up out of the haze
POPUP_LIFE = 0.9

# HUD boxes as (left, bottom, width, height), in canvas units.
LIVES_PLATE = (24, HEIGHT - 84, 250, 62)
TRIP_PLATE = (WIDTH / 2 - 215, HEIGHT - 68, 430, 46)
STATS_PLATE = (WIDTH - 24 - 250, HEIGHT - 84, 250, 62)
TRIP_BAR = (TRIP_PLATE[0] + 110, TRIP_PLATE[1] + 17, 222, 12)
BAR_TRACK = (255, 255, 255, 46)
BAR_FILL = (226, 186, 112)


def _texture(image):
    return arcade.Texture(image, hit_box_algorithm=arcade.hitbox.algo_bounding_box)


@functools.lru_cache(maxsize=1)
def highway_textures():
    """Every picture the round uses, painted once per run."""
    art = {
        "bus": _texture(highway_art.bus_rear()),
        "backdrop": _texture(highway_art.backdrop(width=WIDTH // BACKDROP_SCALE + 8)),
        "tree": _texture(highway_art.tree()),
        "bush": _texture(highway_art.bush()),
        "sign": _texture(highway_art.sign()),
        ("lamp", -1): _texture(highway_art.lamp(1)),    # on the left, arm over the road
        ("lamp", 1): _texture(highway_art.lamp(-1)),
        "bread": bread_textures(),
    }
    painters = (
        ("car", highway_art.car_rear, CAR_PAINTS),
        ("van", highway_art.van_rear, VAN_PAINTS),
        ("truck", highway_art.truck_rear, TRUCK_PAINTS),
    )
    for kind, painter, paints in painters:
        for index, paint in enumerate(paints):
            art[(kind, index)] = _texture(painter(paint))
    return art


def depth_scale(z):
    return VIEW_DEPTH / (VIEW_DEPTH + z)


def project(x, z):
    """A point on the road as (canvas x, canvas y, scale)."""
    scale = depth_scale(z)
    return WIDTH / 2 + x * ROAD_HALF * scale, HORIZON * (1 - scale), scale


def hazed(color, haze):
    return tuple(round(c + (h - c) * haze) for c, h in zip(color, HAZE))


class Ground:
    """The road and its verges, as colour strips from the bottom to the horizon."""

    def __init__(self):
        self.sprites = arcade.SpriteList()
        self.rows = []
        for index in range(HORIZON // ROW_H):
            y = index * ROW_H + ROW_H / 2
            scale = (HORIZON - y) / HORIZON
            half = ROAD_HALF * scale
            rumble_w = max(2, RUMBLE_W * scale)
            dash_w = max(2, DASH_W * scale)
            # Far strips wash out toward the sky, which also hides the
            # shimmer of stripes too thin to draw.
            haze = (1 - min(1.0, scale * 4)) * 0.6
            self.rows.append({
                "z": VIEW_DEPTH * (1 - scale) / scale,
                "grass": self.strip(WIDTH + 40, WIDTH / 2, y),
                "road": self.strip(2 * half, WIDTH / 2, y),
                "rumble": [self.strip(rumble_w, WIDTH / 2 + side * (half + rumble_w / 2), y)
                           for side in (-1, 1)],
                "dash": [self.strip(dash_w, WIDTH / 2 + side * half / 3, y)
                         for side in (-1, 1)],
                "grass_colors": [hazed(color, haze) for color in GRASS],
                "road_colors": [hazed(color, haze) for color in TARMAC],
                "rumble_colors": [hazed(color, haze) for color in RUMBLE],
                "paint": hazed(LANE_PAINT, haze),
                "state": None,
            })
        self.update(0.0)

    def strip(self, width, x, y):
        sprite = arcade.SpriteSolidColor(max(1, round(width)), ROW_H, center_x=x, center_y=y)
        self.sprites.append(sprite)
        return sprite

    def update(self, distance):
        """Recolour whichever strips the road has slid a band along under."""
        for row in self.rows:
            if row["z"] > FAR_Z * 1.4:
                state = (0, 0, False)     # too far to tell the bands apart
            else:
                along = row["z"] + distance
                state = (int(along / BAND) & 1, int(along / RUMBLE_BAND) & 1,
                         along % DASH_PERIOD < DASH_ON)
            if state == row["state"]:
                continue
            row["state"] = state
            band, rumble, dash = state
            row["grass"].color = row["grass_colors"][band]
            row["road"].color = row["road_colors"][band]
            for sprite in row["rumble"]:
                sprite.color = row["rumble_colors"][rumble]
            for sprite in row["dash"]:
                sprite.color = row["paint"] if dash else row["road_colors"][band]


class Actor(arcade.Sprite):
    """Anything standing on the road, sized by how far away it is."""

    def __init__(self, texture, road_width):
        super().__init__(texture)
        self.road_width = road_width
        self.depth = 0.0

    def place(self, x, z, lift=0.0):
        """Stand on road point (x, z)."""
        self.depth = z
        screen_x, ground_y, scale = project(x, z)
        self.scale = self.road_width * ROAD_HALF * scale / self.texture.width
        self.center_x = screen_x
        self.center_y = ground_y + self.height / 2 + lift

    def fade_in(self, share=1.0):
        """Come up out of the haze over the last FADE_IN_Z before FAR_Z."""
        near = max(0.0, min(1.0, (FAR_Z - self.depth) / FADE_IN_Z))
        self.alpha = round(255 * near * share)


class BusHighwayView(BusView):
    """Round 2: steer the bus through the traffic and reach the BBQ."""

    def __init__(self, lives=3, food=100, damaged=()):
        super().__init__(HIGHWAY_LOSE_TITLE, HIGHWAY_LOSE_MESSAGE)
        # Whatever round 1 left: bread to lose here, and the shopping to deliver.
        self.start_lives = max(HIGHWAY_MIN_LIVES, lives)
        self.lives = self.start_lives
        self.food = food
        self.damaged = tuple(damaged)

        self.art = highway_textures()
        self.traffic = Traffic()
        self.ground = Ground()

        self.backdrop = arcade.SpriteList()
        sky = arcade.Sprite(self.art["backdrop"], scale=BACKDROP_SCALE)
        sky.center_x = WIDTH / 2
        sky.center_y = HORIZON - BACKDROP_SINK + sky.height / 2
        self.backdrop.append(sky)

        # Bus, traffic and scenery share one list, drawn far to near.
        self.actors = arcade.SpriteList()
        self.bus = Actor(self.art["bus"], BUS_WIDTH)
        self.actors.append(self.bus)
        self.cars = {}             # Vehicle -> its Actor
        self.props = []            # Actors with a road `x`
        self.prop_count = 0
        self.next_prop = PROP_GAP
        z = FAR_Z
        while z > 1.0:
            self.add_prop(z)
            z -= PROP_GAP

        self.clock = 0.0
        self.fade_clock = 0.0
        self.leaving = None        # seconds into the fade out, once the road is clear
        self.destination = None
        self.flash = 0.0
        self.popups = []           # [arcade.Text, age, canvas x, canvas y]
        self.engine_player = None

        self.title_card = TitleCard(HIGHWAY_KICKER, HIGHWAY_TITLE, HIGHWAY_TAGLINE)
        self.widgets.append(self.title_card)
        self.place_actors()
        self.relayout()

    # --- Layout -------------------------------------------------------------

    def relayout(self):
        super().relayout()
        stage = self.stage
        pad = stage.px(PLANK_PAD)
        self.plates = [
            (box, textures.hud_plate(stage.px(box[2]), stage.px(box[3]), pad, False))
            for box in (LIVES_PLATE, TRIP_PLATE, STATS_PLATE)
        ]
        middle = dict(anchor_y="center")
        left, bottom, width, height = TRIP_PLATE
        self.trip_label = stage.text(
            "ROUND 2", left + 18, bottom + height / 2, TEXT_HOVER, 13,
            bold=True, **middle,
        )
        self.trip_text = stage.text(
            "", left + width - 18, bottom + height / 2, TEXT_BRIGHT, 14,
            anchor_x="right", bold=True, **middle,
        )
        left, bottom, width, height = STATS_PLATE
        self.stat_labels = [
            stage.text(label, x, bottom + height - 18, TEXT_DIM, 11,
                       anchor_x="center", bold=True, **middle)
            for label, x in (("OVERTAKES", left + width * 0.28), ("KM/H", left + width * 0.74))
        ]
        self.overtake_text, self.speed_text = [
            stage.text("0", x, bottom + 22, TEXT_BRIGHT, 22,
                       anchor_x="center", bold=True, **middle)
            for x in (left + width * 0.28, left + width * 0.74)
        ]
        self.hint_shadow, self.hint = [
            stage.text(HIGHWAY_HINT, WIDTH / 2 + offset, 30 - offset, color, 16,
                       anchor_x="center", bold=True, **middle)
            for offset, color in ((1.5, TEXT_SHADOW), (0, TEXT_BRIGHT))
        ]

    # --- Scenery ------------------------------------------------------------

    def add_prop(self, z):
        kind, width = PROPS[self.prop_count % len(PROPS)]
        side = -1 if self.prop_count % 2 else 1
        self.prop_count += 1
        texture = self.art[(kind, side)] if kind == "lamp" else self.art[kind]
        prop = Actor(texture, width)
        # Lamps stand at the kerb; everything else is scattered over the verge.
        prop.x = side * (1.2 if kind == "lamp" else random.uniform(*PROP_X))
        prop.depth = z
        self.props.append(prop)
        self.actors.append(prop)

    def update_props(self, travelled):
        self.next_prop -= travelled
        while self.next_prop <= 0:
            self.add_prop(FAR_Z)
            self.next_prop += PROP_GAP
        for prop in self.props:
            prop.depth -= travelled
        for prop in [p for p in self.props if p.depth < -0.3]:
            self.props.remove(prop)
            prop.remove_from_sprite_lists()

    def place_actors(self):
        """Put every sprite where the road says it is, far ones drawn first."""
        traffic = self.traffic
        for prop in self.props:
            prop.place(prop.x, prop.depth)
            prop.fade_in()

        for vehicle in traffic.vehicles:
            if vehicle not in self.cars:
                sprite = Actor(self.art[(vehicle.kind, vehicle.paint)], vehicle.width)
                self.cars[vehicle] = sprite
                self.actors.append(sprite)
            sprite = self.cars[vehicle]
            sprite.place(vehicle.x, vehicle.z)
            sprite.angle = vehicle.spin
            sprite.fade_in(vehicle.fade)
        for vehicle in [v for v in self.cars if v not in traffic.vehicles]:
            self.cars.pop(vehicle).remove_from_sprite_lists()

        # The bus leans into a turn and shudders a little on its springs.
        self.bus.place(traffic.x, BUS_Z, lift=math.sin(self.clock * 34) * 1.2)
        self.bus.angle = traffic.vx * 2.4
        blinking = traffic.grace > 0 and int(traffic.grace * 11) % 2 == 0
        self.bus.alpha = 110 if blinking else 255
        self.actors.sort(key=lambda sprite: -sprite.depth)

    def add_popup(self, words, color):
        x, y, _ = project(self.traffic.x, BUS_Z)
        text = arcade.Text(
            words, x, y, color, 30, anchor_x="center", bold=True,
            font_name="Kenney Pixel Square",
        )
        self.popups.append([text, 0.0, x, y + self.bus.height + 10])

    # --- Sound --------------------------------------------------------------

    def on_hide_view(self):
        super().on_hide_view()
        self.stop_engine()

    def start_engine(self):
        if self.engine_player is None:
            self.engine_player = audio.play("bus_engine", loop=True)

    def stop_engine(self):
        audio.stop(self.engine_player)
        self.engine_player = None

    # --- Frame --------------------------------------------------------------

    def on_update(self, delta_time):
        self.music.update(delta_time)
        if self.held_up:
            self.stop_engine()
            return
        # A long first frame would otherwise jump the bus down the road.
        delta_time = min(delta_time, 0.05)
        self.clock += delta_time
        self.fade_clock += delta_time
        self.flash = max(0.0, self.flash - delta_time * 3)
        self.title_card.update(delta_time)
        self.start_engine()

        traffic = self.traffic
        steer = (
            any(key in self.held for key in (arcade.key.D, arcade.key.RIGHT))
            - any(key in self.held for key in (arcade.key.A, arcade.key.LEFT))
        )
        before = traffic.distance
        if self.leaving is not None:
            self.leaving += delta_time
            traffic.update(delta_time, steer, traffic=False)
            if self.leaving >= HIGHWAY_FADE:
                self.arrive()
                return
        elif not self.title_card.finished:
            # The card is still up: free to try the steering, no traffic yet.
            traffic.update(delta_time, steer, traffic=False)
            traffic.clock = 0.0
        else:
            self.react(traffic.update(delta_time, steer))

        self.update_props(traffic.distance - before)
        self.ground.update(traffic.distance)
        self.place_actors()
        for popup in self.popups:
            popup[1] += delta_time
        self.popups = [popup for popup in self.popups if popup[1] < POPUP_LIFE]
        self.camera.position = (
            WIDTH / 2 + math.sin(self.clock * 71) * 7 * traffic.shake,
            HEIGHT / 2 + math.cos(self.clock * 83) * 5 * traffic.shake,
        )

    def react(self, events):
        """Sounds, bread and achievements for what the traffic just did."""
        traffic = self.traffic
        for event in events:
            if event == "crash":
                self.lives -= 1
                self.flash = 1.0
                audio.play("bus_crash")
                audio.play("hp_reduced")
                self.add_popup("CRASH!", (255, 110, 96))
            elif event == "near":
                audio.play("bus_swish")
                self.add_popup("CLOSE!", (255, 232, 150))
        if traffic.near_misses >= NEAR_MISSES_FOR_ACHIEVEMENT:
            achievements.unlock("egg_bus_close")
        if self.lives <= 0:
            self.held.clear()
            audio.play("game_failed")
            self.lose_card.open()
        elif traffic.done:
            self.finish()

    def finish(self):
        """The road is clear: sound the horn and fade out toward the garden."""
        from ..bbq.hub import BbqView
        if self.traffic.crashes == 0:
            achievements.unlock("bus_dodger")
        achievements.unlock("bus_arrive")
        audio.play("bus_horn")
        self.traffic.safe = True
        self.leaving = 0.0
        # Built now, so its load time hides inside the fade.
        self.destination = BbqView()

    def arrive(self):
        self.window.bus_delivery = {
            "remaining_food": self.food,
            "damaged_ingredients": list(self.damaged),
            "life": self.lives,
        }
        self.window.show_view(self.destination)

    # --- Drawing ------------------------------------------------------------

    @property
    def fade_alpha(self):
        """Black over the scene: up out of it at the start, back into it at the end."""
        alpha = 1 - self.fade_clock / HIGHWAY_FADE
        if self.leaving is not None:
            alpha = self.leaving / HIGHWAY_FADE
        return round(255 * max(0.0, min(1.0, alpha)))

    def on_draw(self):
        self.clear()
        self.camera.use()
        self.backdrop.draw(pixelated=True)
        self.ground.sprites.draw(pixelated=True)
        self.actors.draw(pixelated=True)
        for text, age, x, y in self.popups:
            text.x, text.y = x, y + age * 60
            text.color = (*text.color[:3], round(255 * (1 - (age / POPUP_LIFE) ** 2)))
            text.draw()
        if self.flash > 0:
            arcade.draw_rect_filled(
                arcade.LBWH(-20, -20, WIDTH + 40, HEIGHT + 40),
                (255, 80, 60, round(90 * self.flash)),
            )

        self.window.default_camera.use()
        self.draw_hud()
        self.title_card.draw()
        if self.fade_alpha:
            arcade.draw_rect_filled(
                arcade.LBWH(0, 0, self.stage.window_w, self.stage.window_h),
                (0, 0, 0, self.fade_alpha),
            )
        self.draw_menus()

    def draw_hud(self):
        stage = self.stage
        traffic = self.traffic
        for (left, bottom, width, height), plate in self.plates:
            arcade.draw_texture_rect(plate, stage.rect(
                left - PLANK_PAD, bottom - PLANK_PAD,
                width + 2 * PLANK_PAD, height + 2 * PLANK_PAD,
            ))

        # Bread, the same health bar as inside the bus.
        bread = self.art["bread"][max(0, self.lives)]
        left, bottom, width, height = LIVES_PLATE
        bread_w = width - 28
        bread_h = bread_w * bread.height / bread.width
        arcade.draw_texture_rect(bread, stage.rect(
            left + 14, bottom + (height - bread_h) / 2, bread_w, bread_h,
        ), pixelated=True)

        # How much of the road home is behind the bus.
        share = min(1.0, traffic.clock / HIGHWAY_DURATION)
        left, bottom, width, height = TRIP_BAR
        arcade.draw_rect_filled(stage.rect(left, bottom, width, height), BAR_TRACK)
        if share > 0:
            arcade.draw_rect_filled(stage.rect(left, bottom, width * share, height), BAR_FILL)
        self.set_text(self.trip_text, "Home!" if share >= 1 else f"{round(share * 100)}%")
        self.set_text(self.overtake_text, str(traffic.overtakes))
        self.set_text(self.speed_text, str(round(traffic.speed * KPH_PER_UNIT)))
        for text in (self.trip_label, self.trip_text, *self.stat_labels,
                     self.overtake_text, self.speed_text):
            text.draw()

        if self.clock < HIGHWAY_HINT_TIME and self.title_card.finished:
            self.hint_shadow.draw()
            self.hint.draw()

    @staticmethod
    def set_text(text, words):
        # Laying text out again costs more than this comparison.
        if text.text != words:
            text.text = words

    # --- Input --------------------------------------------------------------

    def key_down(self, key):
        if key == arcade.key.SPACE and not self.title_card.finished:
            self.title_card.skip()
            return
        super().key_down(key)

    def retry(self):
        self.go(BusHighwayView(self.start_lives, self.food, self.damaged))
