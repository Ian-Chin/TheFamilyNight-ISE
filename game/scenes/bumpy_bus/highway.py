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
    HEIGHT, KEYCAP_TEXT, PLANK_PAD, TEXT_BRIGHT, TEXT_DIM, TEXT_HOVER, TEXT_SHADOW, WIDTH,
)
from ...core import achievements, audio, textures
from ...core.dialogue import DialogBox
from ...core.widgets import Portraits, TitleCard
from . import highway_art
from .config import (
    ARRIVAL_LINES, ARRIVAL_LINES_SPOILED, ARRIVE_PAUSE, ARRIVE_WALK, BACKDROP_SCALE,
    BACKDROP_SINK, BAND, BUS_ART_SHARE, BUS_SPEED, BUS_WIDTH, BUS_Z, CAR_PAINTS, DASH_ON,
    DASH_PERIOD, DASH_W, FAR_Z, GRASS, HAZE, HIGHWAY_DURATION, HIGHWAY_FADE, HIGHWAY_HINT,
    HIGHWAY_HINT_TIME, HIGHWAY_KICKER, HIGHWAY_LOSE_MESSAGE, HIGHWAY_LOSE_TITLE,
    HIGHWAY_MIN_LIVES, HIGHWAY_TAGLINE, HIGHWAY_TITLE, HORIZON, HOUSE_STOP_Z, HOUSE_WIDTH,
    HOUSE_X, KPH_PER_UNIT, LANE_PAINT, LANE_X, NEAR_MISSES_FOR_ACHIEVEMENT, PARK_X, PROP_GAP,
    PROP_X, PROPS, ROAD_HALF, ROW_H, RUMBLE, RUMBLE_BAND, RUMBLE_W, SHOUT_COOLDOWN,
    SHOUT_SHOW, SHOUTS_FOR_ACHIEVEMENT, TARMAC, TERRY_PATH, TERRY_ROAD_W, TRUCK_PAINTS,
    VAN_PAINTS, VIEW_DEPTH,
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
SHOUT_PLATE = (WIDTH - 24 - 250, HEIGHT - 140, 250, 44)
KEY_W, KEY_H = 40, 28
SMOKE = (234, 234, 238, 150)
DUST = (206, 190, 150, 190)
SPARKS = ((255, 226, 120, 255), (255, 160, 70, 255), (255, 255, 255, 255))
BAR_TRACK = (255, 255, 255, 46)
BAR_FILL = (226, 186, 112)


def _texture(image):
    return arcade.Texture(image, hit_box_algorithm=arcade.hitbox.algo_bounding_box)


@functools.lru_cache(maxsize=1)
def highway_textures():
    """Every picture the round uses, painted once per run."""
    art = {
        "bus": _texture(highway_art.bus_rear()),
        "bus_shout": _texture(highway_art.bus_rear(driver=True)),
        "bus_brake": _texture(highway_art.bus_rear(braking=True)),
        "house": _texture(highway_art.house()),
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


class Pool:
    """Flat colour rectangles drawn in one batch, handed out afresh each frame.

    The effects (smoke, sparks, tyre marks) are all little squares, like the
    dust in the walking scenes; pooling them keeps a burst of fifty to one
    draw call.
    """

    def __init__(self, size):
        self.sprites = arcade.SpriteList()
        for _ in range(size):
            self.sprites.append(arcade.SpriteSolidColor(8, 8, color=(255, 255, 255, 0)))
        self.used = self.shown = 0

    def begin(self):
        self.used = 0

    def rect(self, x, y, width, height, color, angle=0.0):
        if self.used == len(self.sprites):
            return
        sprite = self.sprites[self.used]
        self.used += 1
        sprite.center_x, sprite.center_y = x, y
        sprite.width, sprite.height = max(1, width), max(1, height)
        sprite.angle = angle
        sprite.color = color

    def end(self):
        for index in range(self.used, self.shown):
            self.sprites[index].color = (0, 0, 0, 0)
        self.shown = self.used


class BusHighwayView(BusView):
    """Round 2: steer the bus through the traffic, then pull in at home."""

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
        self.bus = Actor(self.art["bus"], BUS_WIDTH * BUS_ART_SHARE)
        self.actors.append(self.bus)
        self.cars = {}             # Vehicle -> its Actor
        self.props = []            # Actors with a road `x`
        self.prop_count = 0
        self.next_prop = PROP_GAP
        z = FAR_Z
        while z > 1.0:
            self.add_prop(z)
            z -= PROP_GAP

        # Effects: marks lie on the road under everything, bits fly over it.
        self.road_fx = Pool(48)
        self.air_fx = Pool(160)
        self.marks = []            # tyre marks, as [road x, z]
        self.waves = []            # the shout racing up the lane, as [road x, z, age]
        self.bits = []             # smoke and sparks, in canvas units
        self.smoke_clock = 0.0

        # "drive", then home: "pulling_in", "parked", "walking", "talking".
        self.phase = "drive"
        self.clock = 0.0
        self.fade_clock = 0.0
        self.leaving = None        # seconds into the fade out, at the very end
        self.destination = None
        self.flash = 0.0
        self.shout_show = 0.0      # seconds the driver stays out of the window
        self.popups = []           # [arcade.Text, age, canvas x, canvas y]
        self.engine_player = None
        self.typing_player = None
        self.house = None
        self.walker = None         # Terry, once he is off the bus
        self.park_time = self.walk_time = self.step_clock = 0.0
        self.line = 0

        self.walk_frames, _, self.idle_frames = textures.terry_frames()
        self.terry_faces = textures.terry_faces()
        self.default_face = textures.terry_frames(glow=False)[2][0]
        self.portraits = Portraits(self.default_face)
        self.dialog = DialogBox()
        self.title_card = TitleCard(HIGHWAY_KICKER, HIGHWAY_TITLE, HIGHWAY_TAGLINE)
        self.widgets += [self.title_card, self.dialog, self.portraits]
        self.place_actors()
        self.relayout()

    # --- Layout -------------------------------------------------------------

    def relayout(self):
        super().relayout()
        stage = self.stage
        pad = stage.px(PLANK_PAD)
        self.plates = {
            box: textures.hud_plate(stage.px(box[2]), stage.px(box[3]), pad, False)
            for box in (LIVES_PLATE, TRIP_PLATE, STATS_PLATE, SHOUT_PLATE)
        }
        self.keycap = textures.keycap(stage.px(KEY_W), stage.px(KEY_H), stage.px(2))
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
        left, bottom, width, height = SHOUT_PLATE
        self.shout_key = stage.text(
            "Q", left + 14 + KEY_W / 2, bottom + height / 2 + 2, KEYCAP_TEXT, 15,
            anchor_x="center", bold=True, **middle,
        )
        self.shout_label = stage.text(
            "Shout", left + 66, bottom + height / 2, TEXT_BRIGHT, 15, bold=True, **middle,
        )
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
        if self.phase == "drive":
            # Nothing new is planted once home is coming up.
            self.next_prop -= travelled
            while self.next_prop <= 0:
                self.add_prop(FAR_Z)
                self.next_prop += PROP_GAP
        for prop in self.props:
            prop.depth -= travelled
        for prop in [p for p in self.props if p.depth < -0.3]:
            self.props.remove(prop)
            prop.remove_from_sprite_lists()
        if self.house is not None:
            self.house.depth = max(HOUSE_STOP_Z, self.house.depth - travelled)

    def place_actors(self):
        """Put every sprite where the road says it is, far ones drawn first."""
        traffic = self.traffic
        for prop in self.props:
            prop.place(prop.x, prop.depth)
            prop.fade_in()
        if self.house is not None:
            self.house.place(self.house.x, self.house.depth)
            self.house.fade_in()

        for vehicle in traffic.vehicles:
            if vehicle not in self.cars:
                sprite = Actor(self.art[(vehicle.kind, vehicle.paint)], vehicle.width)
                self.cars[vehicle] = sprite
                self.actors.append(sprite)
            sprite = self.cars[vehicle]
            sprite.place(vehicle.x, vehicle.z,
                         lift=vehicle.lift * ROAD_HALF * depth_scale(vehicle.z))
            if vehicle.hit:
                sprite.angle = vehicle.spin
            else:
                # Swerving for the verge after a shout, it leans into the turn.
                sprite.angle = max(-1.0, min(1.0, (vehicle.target_x - vehicle.x) * 4)) * 7
            sprite.fade_in(vehicle.fade)
        for vehicle in [v for v in self.cars if v not in traffic.vehicles]:
            sprite = self.cars.pop(vehicle)
            if vehicle.hit:
                self.twinkle(sprite.center_x, sprite.center_y)
            sprite.remove_from_sprite_lists()

        # The bus leans into a turn and shudders on its springs while it moves.
        moving = traffic.speed > 0.5
        self.bus.place(traffic.x, BUS_Z, lift=math.sin(self.clock * 34) * 1.2 if moving else 0)
        self.bus.angle = traffic.vx * 2.4
        blinking = traffic.grace > 0 and int(traffic.grace * 11) % 2 == 0
        self.bus.alpha = 110 if blinking else 255
        if self.shout_show > 0:
            look = "bus_shout"
        elif self.phase != "drive" or traffic.slowed > 0:
            look = "bus_brake"
        else:
            look = "bus"
        if self.bus.texture is not self.art[look]:
            self.bus.texture = self.art[look]
        self.actors.sort(key=lambda sprite: -sprite.depth)

    def add_popup(self, words, color):
        x, y, _ = project(self.traffic.x, BUS_Z)
        text = arcade.Text(
            words, x, y, color, 30, anchor_x="center", bold=True,
            font_name="Kenney Pixel Square",
        )
        self.popups.append([text, 0.0, x, y + self.bus.height + 10])

    # --- Effects ------------------------------------------------------------

    def bit(self, x, y, vx, vy, size, color, life, grow=0.0, gravity=0.0):
        """One square of smoke, dust or spark, in canvas units."""
        self.bits.append({
            "x": x, "y": y, "vx": vx, "vy": vy, "size": size, "grow": grow,
            "gravity": gravity, "color": color, "life": life, "age": 0.0,
        })

    def burst(self, x, y, count, speed):
        """Sparks thrown out of a crash."""
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            pace = speed * random.uniform(0.4, 1.0)
            self.bit(x, y, math.cos(angle) * pace, math.sin(angle) * pace + 120,
                     random.uniform(6, 12), random.choice(SPARKS), 0.6, gravity=700)

    def twinkle(self, x, y):
        """All that is left of a car knocked over the horizon."""
        for dx, dy in ((0, 0), (-9, 0), (9, 0), (0, -9), (0, 9), (-18, 0), (18, 0), (0, 18), (0, -18)):
            self.bit(x + dx, y + dy, 0, 0, 7 if (dx or dy) else 11, (255, 250, 214, 255), 0.4)

    def wheels(self):
        """Canvas points under the bus's two rear wheels, and their scale."""
        return [project(self.traffic.x + side * 0.17, BUS_Z) for side in (-1, 1)]

    def update_effects(self, delta_time, travelled):
        traffic = self.traffic
        # Tyres: steering hard smokes them and lays rubber on the road.
        skidding = abs(traffic.vx) > 0.9 and traffic.speed > 2
        self.smoke_clock -= delta_time
        if skidding:
            for side in (-1, 1):
                self.marks.append([traffic.x + side * 0.17, BUS_Z])
            if self.smoke_clock <= 0:
                self.smoke_clock = 0.03
                away = -1 if traffic.vx > 0 else 1
                for x, y, scale in self.wheels():
                    self.bit(x + random.uniform(-6, 6), y + 6,
                             away * random.uniform(30, 110), -random.uniform(120, 240),
                             random.uniform(10, 16), SMOKE, 0.45, grow=60)
        for mark in self.marks:
            mark[1] -= travelled
        self.marks = [mark for mark in self.marks if mark[1] > -0.45][-40:]
        for wave in self.waves:
            wave[1] += 17 * delta_time
            wave[2] += delta_time
        self.waves = [wave for wave in self.waves if wave[2] < 0.5]

        for vehicle, sprite in self.cars.items():
            if vehicle.hit:
                # The whoosh: a white streak left hanging behind the flying car.
                size = max(4, sprite.width * 0.22)
                self.bit(sprite.center_x, sprite.center_y, 0, 0, size, (255, 255, 255, 190), 0.28)
            elif vehicle.pulled and abs(vehicle.x) > 1.05 and vehicle.fade >= 1 and random.random() < 0.5:
                # Bumping along the verge kicks up dust.
                x, y, scale = project(vehicle.x, vehicle.z)
                self.bit(x + random.uniform(-20, 20) * scale, y + 4, random.uniform(-30, 30),
                         random.uniform(20, 70), max(3, 16 * scale), DUST, 0.5, grow=20)

        for bit in self.bits:
            bit["age"] += delta_time
            bit["x"] += bit["vx"] * delta_time
            bit["y"] += bit["vy"] * delta_time
            bit["vy"] -= bit["gravity"] * delta_time
        self.bits = [bit for bit in self.bits if bit["age"] < bit["life"]]

    def draw_effects(self):
        self.road_fx.begin()
        for x, z in self.marks:
            near, far = project(x, z), project(x, z + 0.2)
            self.road_fx.rect(near[0], (near[1] + far[1]) / 2, max(2, 0.04 * ROAD_HALF * near[2]),
                              max(2, far[1] - near[1]), (22, 24, 32, 170))
        for x, z, age in self.waves:
            sx, sy, scale = project(x, z)
            self.road_fx.rect(sx, sy, 0.5 * ROAD_HALF * scale, max(2, 14 * scale),
                              (255, 226, 120, round(230 * (1 - age / 0.5))))
        self.road_fx.end()

        self.air_fx.begin()
        for bit in self.bits:
            share = bit["age"] / bit["life"]
            size = bit["size"] + bit["grow"] * bit["age"]
            r, g, b, a = bit["color"]
            self.air_fx.rect(round(bit["x"]), round(bit["y"]), size, size,
                             (r, g, b, round(a * (1 - share))))
        self.air_fx.end()

    # --- Sound --------------------------------------------------------------

    def on_hide_view(self):
        super().on_hide_view()
        self.stop_engine()
        self.stop_typing()

    def start_engine(self):
        if self.engine_player is None:
            self.engine_player = audio.play("bus_engine", loop=True)

    def stop_engine(self):
        audio.stop(self.engine_player)
        self.engine_player = None

    def stop_typing(self):
        audio.stop(self.typing_player)
        self.typing_player = None

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
        self.shout_show = max(0.0, self.shout_show - delta_time)
        self.title_card.update(delta_time)

        traffic = self.traffic
        before = traffic.distance
        if self.phase == "drive":
            self.start_engine()
            steer = (
                any(key in self.held for key in (arcade.key.D, arcade.key.RIGHT))
                - any(key in self.held for key in (arcade.key.A, arcade.key.LEFT))
            )
            if not self.title_card.finished:
                # The card is still up: free to try the steering, no traffic yet.
                traffic.update(delta_time, steer, traffic=False)
                traffic.clock = 0.0
            else:
                self.react(traffic.update(delta_time, steer))
        else:
            self.come_home(delta_time)
            if self.leaving is not None:
                self.leaving += delta_time
                if self.leaving >= HIGHWAY_FADE:
                    self.arrive()
                    return

        travelled = traffic.distance - before
        self.update_props(travelled)
        self.ground.update(traffic.distance)
        self.place_actors()
        self.update_effects(delta_time, travelled)
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
                audio.play("bus_swish", gain=1.6)
                audio.play("hp_reduced")
                self.add_popup("CRASH!", (255, 110, 96))
                for vehicle in traffic.vehicles:
                    if vehicle.hit and vehicle.air == 0.0:
                        x, y, scale = project(vehicle.x, vehicle.z)
                        self.burst(x, y + 40 * scale, 20, 420)
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

    def shout(self):
        """Q: the driver leans out and yells the lane ahead clear."""
        moved = self.traffic.shout()
        if moved is None:
            return
        self.shout_show = SHOUT_SHOW
        audio.play("bus_horn")
        self.add_popup("MOVE IT!" if moved else "HEY!", (255, 232, 150))
        lane_x = LANE_X[self.traffic.bus_lane()]
        self.waves += [[lane_x, BUS_Z + 0.5 + index * 0.7, 0.0] for index in range(3)]
        if self.traffic.shooed >= SHOUTS_FOR_ACHIEVEMENT:
            achievements.unlock("egg_bus_shout")

    # --- Home ---------------------------------------------------------------

    def finish(self):
        """The traffic is behind: home comes up on the left and the bus pulls in."""
        if self.traffic.crashes == 0:
            achievements.unlock("bus_dodger")
        audio.play("bus_horn")
        self.held.clear()
        self.traffic.safe = True
        self.phase = "pulling_in"
        self.house = Actor(self.art["house"], HOUSE_WIDTH)
        self.house.x = HOUSE_X
        self.house.depth = FAR_Z
        self.actors.append(self.house)
        # Scenery this far off on the left would end up standing in the yard.
        for prop in [p for p in self.props if p.x < 0 and p.depth > FAR_Z - HOUSE_STOP_Z - 0.2]:
            self.props.remove(prop)
            prop.remove_from_sprite_lists()

    def come_home(self, delta_time):
        """Everything after the traffic: brake, park, and Terry walks in."""
        traffic = self.traffic
        if self.phase == "pulling_in":
            self.start_engine()
            left = self.house.depth - HOUSE_STOP_Z
            # Ease off as the house gets close, and stop level with it.
            speed = min(BUS_SPEED[1], 0.6 + left * 1.6) if left > 0.02 else 0.0
            traffic.coast(delta_time, speed, PARK_X)
            if speed == 0.0:
                self.park()
            return
        traffic.coast(delta_time, 0.0, PARK_X)
        if self.phase == "parked":
            self.park_time += delta_time
            if self.park_time >= ARRIVE_PAUSE:
                self.phase = "walking"
                self.walker = Actor(self.walk_frames[0], TERRY_ROAD_W)
                self.actors.append(self.walker)
                audio.play("bus_land")
        if self.phase == "walking":
            self.walk_time += delta_time
            self.step_clock -= delta_time
            if self.step_clock <= 0:
                self.step_clock = 0.32
                audio.play("step_stone")
            frame = int(self.walk_time / 0.11) % len(self.walk_frames)
            self.put_walker(min(1.0, self.walk_time / ARRIVE_WALK), self.walk_frames[frame])
            if self.walk_time >= ARRIVE_WALK:
                self.start_talking()
        elif self.phase == "talking":
            self.dialog.update(delta_time)
            if not self.dialog.typing:
                self.stop_typing()

    def park(self):
        """Stopped at the kerb: the brakes sigh and the dust settles."""
        from ..bbq.hub import BbqView
        self.phase = "parked"
        self.park_time = 0.0
        self.stop_engine()
        audio.play("bus_swish", gain=1.4)
        for x, y, scale in self.wheels():
            for _ in range(8):
                self.bit(x + random.uniform(-20, 20), y + 4, random.uniform(-90, 90),
                         random.uniform(10, 80), random.uniform(8, 14), DUST, 0.7, grow=30)
        # Built now, while nothing is moving, so its load time does not show.
        if self.destination is None:
            self.destination = BbqView()

    def put_walker(self, share, texture):
        """Terry `share` of the way from the kerb to the garden gate."""
        (x0, z0), (x1, z1) = TERRY_PATH
        if self.walker.texture is not texture:
            self.walker.texture = texture
        self.walker.place(x0 + (x1 - x0) * share, z0 + (z1 - z0) * share)
        # He is heading left, and the art faces right.
        self.walker.scale_x = -abs(self.walker.scale_x)

    def start_talking(self):
        self.phase = "talking"
        self.put_walker(1.0, self.idle_frames[0])
        self.lines = ARRIVAL_LINES_SPOILED if self.damaged else ARRIVAL_LINES
        self.line = 0
        self.say()

    def say(self):
        words, face = self.lines[self.line]
        names = list(self.damaged)
        spoiled = " and ".join([", ".join(names[:-1]), names[-1]] if len(names) > 1 else names)
        self.portraits.terry = self.terry_faces.get(face, self.default_face)
        audio.play("dialog_open")
        self.dialog.open("Terry", words.format(spoiled=spoiled))
        self.typing_player = audio.play("dialog_type", loop=True)

    def advance(self):
        self.stop_typing()
        if not self.dialog.advance():
            return
        self.line += 1
        if self.line < len(self.lines):
            self.say()
        else:
            achievements.unlock("bus_arrive")
            self.leaving = 0.0

    def skip_home(self):
        """Enter or Space before Terry speaks: jump to him at the gate."""
        self.traffic.vehicles.clear()
        self.traffic.x, self.traffic.vx = PARK_X, 0.0
        self.house.depth = HOUSE_STOP_Z
        if self.phase == "pulling_in":
            self.traffic.coast(0.0, 0.0, PARK_X)
            self.park()
        if self.walker is None:
            self.walker = Actor(self.walk_frames[0], TERRY_ROAD_W)
            self.actors.append(self.walker)
        self.start_talking()

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
        self.draw_effects()
        self.road_fx.sprites.draw(pixelated=True)
        self.actors.draw(pixelated=True)
        self.air_fx.sprites.draw(pixelated=True)
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
        if self.dialog.visible:
            self.portraits.draw(partner=None, speaking="left")
            self.dialog.draw()
        self.draw_fade(self.fade_alpha)
        self.draw_menus()

    def plate(self, box):
        left, bottom, width, height = box
        arcade.draw_texture_rect(self.plates[box], self.stage.rect(
            left - PLANK_PAD, bottom - PLANK_PAD,
            width + 2 * PLANK_PAD, height + 2 * PLANK_PAD,
        ))

    def draw_hud(self):
        stage = self.stage
        traffic = self.traffic
        for box in (LIVES_PLATE, TRIP_PLATE, STATS_PLATE):
            self.plate(box)

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

        if self.phase != "drive" or not self.title_card.finished:
            return
        # Q, and how long until the driver has his breath back.
        self.plate(SHOUT_PLATE)
        left, bottom, width, height = SHOUT_PLATE
        ready = traffic.shout_wait <= 0
        arcade.draw_texture_rect(self.keycap, stage.rect(
            left + 12, bottom + (height - KEY_H) / 2 - 2, KEY_W + 4, KEY_H + 4,
        ))
        self.set_text(self.shout_label, "Shout!" if ready else "Shout")
        self.shout_label.color = TEXT_HOVER if ready else TEXT_DIM
        bar = (left + 138, bottom + height / 2 - 5, 98, 10)
        arcade.draw_rect_filled(stage.rect(*bar), BAR_TRACK)
        filled = 1 - traffic.shout_wait / SHOUT_COOLDOWN
        arcade.draw_rect_filled(stage.rect(bar[0], bar[1], bar[2] * filled, bar[3]), BAR_FILL)
        self.shout_key.draw()
        self.shout_label.draw()
        if self.clock < HIGHWAY_HINT_TIME:
            self.hint_shadow.draw()
            self.hint.draw()

    @staticmethod
    def set_text(text, words):
        # Laying text out again costs more than this comparison.
        if text.text != words:
            text.text = words

    # --- Input --------------------------------------------------------------

    def click(self, x, y, button):
        if (self.phase == "talking" and self.leaving is None
                and button == arcade.MOUSE_BUTTON_LEFT):
            self.advance()

    def key_down(self, key):
        go_on =key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.RETURN, arcade.key.SPACE)
        if self.phase == "drive":
            if not self.title_card.finished:
                if key == arcade.key.SPACE:
                    self.title_card.skip()
                    return
            elif key == arcade.key.Q:
                self.shout()
                return
            super().key_down(key)
        elif go_on and self.leaving is None:
            if self.phase == "talking":
                self.advance()
            else:
                self.skip_home()

    def retry(self):
        self.go(BusHighwayView(self.start_lives, self.food, self.damaged))
