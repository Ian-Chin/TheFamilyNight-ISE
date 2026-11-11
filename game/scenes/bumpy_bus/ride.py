"""Round 1: inside the bus, keeping your balance while it brakes and bumps.

balance.py decides how Terry leans and when the driver does something
dangerous. This view draws the cabin and the balance bar, runs the alerts that
threaten the shopping, and hands over to round 2 when the ride is done.
"""

import math
import random

import arcade

from ...config import (
    HEIGHT, KEYCAP_TEXT, PLANK_PAD, TEXT_BRIGHT, TEXT_DIM, TEXT_HOVER, TEXT_SHADOW, WIDTH,
)
from ...core import achievements, audio, textures
from .balance import DANGER, RECOVER_TIME, RIDE_DURATION, BusBalance
from .base import BusView
from .cabin import Cabin
from .config import (
    BAR_AMBER, BAR_BOTTOM, BAR_CENTER, BAR_FIGURE_H, BAR_GREEN, BAR_H, BAR_REACH, BAR_RED,
    BRAKES_FOR_ACHIEVEMENT, CABIN_BOTTOM, CABIN_SIZE, EVENT_KEYS, EVENT_NAMES, EVENT_PRESSES,
    EVENT_SCENES, EVENT_TIME, FIRST_EVENT_DELAY, FOOD_LOSS, LEAVE_FADE, NO_EVENTS_LAST,
    REACTION_CUES, REACTION_EVENT_DELAY, RIDE_HINT, RIDE_HINT_TIME, RIDE_KICKER,
    RIDE_LOSE_MESSAGE, RIDE_LOSE_TITLE, RIDE_TAGLINE, RIDE_TITLE, SOLVED_EVENT_DELAY,
)
from .hud import BusHud
from ...core.widgets import TitleCard

INGREDIENT_NAMES = ("eggs", "meat", "cabbage", "eggplant")
KEYS = [getattr(arcade.key, letter) for letter in EVENT_KEYS]
BAR_PLATE = (BAR_CENTER - 264, BAR_BOTTOM - 8, 528, 32)
LEFT_PLATE = (150, BAR_BOTTOM - 8, 214, 32)
RIGHT_PLATE = (916, BAR_BOTTOM - 8, 214, 32)
ALERT_BOX = (WIDTH / 2 - 250, 420, 500, 100)
KEY_W, KEY_H = 64, 48
RED = (255, 113, 113)
WHITE = (241, 246, 238)


class BusRideView(BusView):
    def __init__(self, cabin=None):
        super().__init__(RIDE_LOSE_TITLE, RIDE_LOSE_MESSAGE)
        self.cabin = cabin or Cabin()
        self.rng = random.Random()
        self.balance = BusBalance(self.rng)

        face = textures.terry_frames(glow=False)[2][0]
        self.figure = arcade.Sprite(face, scale=BAR_FIGURE_H / face.height)
        self.figures = arcade.SpriteList()
        self.figures.append(self.figure)

        self.title_card = TitleCard(RIDE_KICKER, RIDE_TITLE, RIDE_TAGLINE)
        self.hud = BusHud("ROUND 1", alerts=True)
        self.widgets += [self.title_card, self.hud]

        self.mode = "title"
        self.anim = 0.0                # drives the idle cabin and the flashing
        self.elapsed = 0.0             # seconds of the ride itself
        self.leave_time = 0.0
        self.lives = 3
        self.food = 100
        self.damaged = set()
        self.event = None              # index of the alert showing, if any
        self.previous_event = None
        self.event_key = None
        self.event_left = 0.0
        self.presses = 0
        self.next_event = self.rng.uniform(*FIRST_EVENT_DELAY)
        self.reaction = None           # scene playing after a missed alert
        self.reaction_time = 0.0
        self.cues_played = set()
        self.relayout()

    def relayout(self):
        super().relayout()
        stage = self.stage
        pad = stage.px(PLANK_PAD)
        self.plates = {
            box: textures.hud_plate(stage.px(box[2]), stage.px(box[3]), pad, False)
            for box in (BAR_PLATE, LEFT_PLATE, RIGHT_PLATE, ALERT_BOX)
        }
        self.keycap = textures.keycap(stage.px(KEY_W), stage.px(KEY_H), stage.px(2))
        middle = dict(anchor_y="center", bold=True)
        center = dict(anchor_x="center", anchor_y="center", bold=True)
        y = BAR_BOTTOM + BAR_H / 2
        self.left_text = stage.text("A  Lean", LEFT_PLATE[0] + LEFT_PLATE[2] / 2, y, WHITE, 15, **center)
        self.right_text = stage.text("Lean  D", RIGHT_PLATE[0] + RIGHT_PLATE[2] / 2, y, WHITE, 15, **center)
        self.ouch_text = stage.text("OUCH!", 0, 0, RED, 30, **center)
        self.hint_shadow, self.hint = [
            stage.text(RIDE_HINT, WIDTH / 2 + offset, 598 - offset, color, 16, **center)
            for offset, color in ((1.5, TEXT_SHADOW), (0, TEXT_BRIGHT))
        ]
        left, bottom = ALERT_BOX[0], ALERT_BOX[1]
        text_x = left + 112
        self.alert_kicker = stage.text("ALERT", text_x, bottom + 80, TEXT_HOVER, 12, **middle)
        self.alert_name = stage.text("", text_x, bottom + 55, TEXT_BRIGHT, 22, **middle)
        self.alert_detail = stage.text("", text_x, bottom + 30, TEXT_DIM, 15, **middle)
        self.alert_key = stage.text(
            "", left + 26 + KEY_W / 2, bottom + (ALERT_BOX[3] - KEY_H) / 2 + KEY_H / 2 + 2,
            KEYCAP_TEXT, 26, **center,
        )

    # --- Frame --------------------------------------------------------------

    def retry(self):
        self.go(BusRideView(self.cabin))

    def on_update(self, delta_time):
        self.music.update(delta_time)
        if self.held_up:
            return
        delta_time = min(delta_time, 0.05)
        self.anim += delta_time
        if self.mode == "title":
            self.title_card.update(delta_time)
            if self.title_card.finished:
                self.mode = "ride"
                self.anim = 0.0
        elif self.mode == "ride":
            self.update_ride(delta_time)
        elif self.mode == "leaving":
            self.leave_time += delta_time
            if self.leave_time >= LEAVE_FADE:
                from .highway import BusHighwayView
                damaged = [INGREDIENT_NAMES[i] for i in sorted(self.damaged)]
                self.go(BusHighwayView(self.lives, self.food, damaged))
        self.hud.lives = self.lives
        self.hud.damaged = self.damaged
        self.hud.alert = self.event
        self.hud.share = self.elapsed / RIDE_DURATION
        self.hud.note = f"{round(min(1.0, self.hud.share) * 100)}%"

    def update_ride(self, delta_time):
        self.elapsed += delta_time
        lean = (any(k in self.held for k in (arcade.key.D, arcade.key.RIGHT))
                - any(k in self.held for k in (arcade.key.A, arcade.key.LEFT)))
        for name in self.balance.update(delta_time, lean):
            if name == "warn":
                audio.play("bus_jump", gain=0.8)
            elif name == "brake":
                audio.play("bus_swish", gain=1.6)
            elif name == "surge":
                audio.play("bus_engine", gain=1.5)
            elif name == "bump":
                audio.play("bus_land", gain=1.5)
            elif name == "stumble":
                self.lives = max(0, self.lives - 1)
                audio.play("bus_cane_hit", gain=0.8)
                audio.play("hp_reduced")
        if self.balance.brakes_held >= BRAKES_FOR_ACHIEVEMENT:
            achievements.unlock("bus_brakes")
        if self.lives == 0:
            self.fail()
            return

        if self.reaction:
            self.reaction_time += delta_time
            duration = self.cabin.duration(self.reaction)
            for index, (share, sound, *gain) in enumerate(REACTION_CUES[self.reaction]):
                if index not in self.cues_played and self.reaction_time >= share * duration:
                    self.cues_played.add(index)
                    audio.play(sound, gain=gain[0] if gain else 1.0)
            if self.reaction_time >= duration:
                self.cabin.release(self.reaction)
                self.reaction = None
                self.next_event = self.elapsed + self.rng.uniform(*REACTION_EVENT_DELAY)
        if (self.event is None and self.reaction is None and self.elapsed >= self.next_event
                and self.elapsed < RIDE_DURATION - NO_EVENTS_LAST):
            self.start_event()
        if self.event is not None:
            self.event_left -= delta_time
            if self.event_left <= 0:
                self.spoil()
                if self.food == 0:
                    self.fail()
                    return
        if self.elapsed >= RIDE_DURATION:
            if self.balance.stumbles == 0:
                achievements.unlock("bus_surfer")
            if self.food == 100:
                achievements.unlock("bus_guard")
            self.leave()

    def start_event(self):
        choices = [i for i in range(len(EVENT_SCENES)) if i != self.previous_event]
        self.event = self.previous_event = self.rng.choice(choices)
        self.event_key = self.rng.choice([k for k in KEYS if k != self.event_key])
        self.event_left = EVENT_TIME
        self.presses = 0
        # Read its sheet now, while the countdown runs.
        self.cabin.prepare(EVENT_SCENES[self.event])
        audio.play("bus_warning")

    def spoil(self):
        """The alert ran out: play the scene, and one ingredient is ruined."""
        self.reaction = EVENT_SCENES[self.event]
        self.reaction_time = 0.0
        self.cues_played = set()
        self.damaged.add(self.rng.randrange(len(INGREDIENT_NAMES)))
        self.food = max(0, self.food - FOOD_LOSS)
        self.event = None
        audio.play("hp_reduced")

    def leave(self):
        audio.play("bus_horn")
        self.mode = "leaving"
        self.leave_time = 0.0
        self.event = None
        self.reaction = None

    def fail(self):
        self.held.clear()
        self.event = None
        self.reaction = None
        self.mode = "failed"
        audio.play("game_failed")
        self.lose_card.open()

    # --- Drawing ------------------------------------------------------------

    @staticmethod
    def say(text, words, color=None):
        # Laying text out again costs more than this comparison.
        if text.text != words:
            text.text = words
        if color is not None and tuple(text.color[:3]) != color:
            text.color = color

    def draw_cabin(self):
        if self.reaction:
            texture = self.cabin.at(self.reaction, self.reaction_time)
        else:
            texture = self.cabin.at("idle", self.anim)
        dx, dy = self.balance.shake() if self.mode == "ride" else (0, 0)
        arcade.draw_texture_rect(
            texture, arcade.LBWH(dx, CABIN_BOTTOM - dy, *CABIN_SIZE), pixelated=True,
        )

    def plate(self, box):
        left, bottom, width, height = box
        arcade.draw_texture_rect(self.plates[box], arcade.LBWH(
            left - PLANK_PAD, bottom - PLANK_PAD, width + 2 * PLANK_PAD, height + 2 * PLANK_PAD,
        ))

    def draw_bar(self):
        """The bar along the bottom: Terry slides and tips as the bus throws him."""
        b = self.balance
        flash = math.sin(self.anim * 18) > 0
        if b.danger and flash:
            arcade.draw_rect_filled(
                arcade.LBWH(BAR_CENTER - 272, BAR_BOTTOM - 14, 544, 44), (255, 113, 113, 200),
            )
        for box in (BAR_PLATE, LEFT_PLATE, RIGHT_PLATE):
            self.plate(box)
        left = BAR_CENTER - BAR_REACH - 12
        arcade.draw_rect_filled(arcade.LBWH(left, BAR_BOTTOM, 2 * BAR_REACH + 24, BAR_H), BAR_RED)
        arcade.draw_rect_filled(arcade.LBWH(
            BAR_CENTER - BAR_REACH * DANGER, BAR_BOTTOM, 2 * BAR_REACH * DANGER, BAR_H), BAR_AMBER)
        arcade.draw_rect_filled(arcade.LBWH(
            BAR_CENTER - BAR_REACH * 0.42, BAR_BOTTOM, 2 * BAR_REACH * 0.42, BAR_H), BAR_GREEN)
        arcade.draw_rect_filled(arcade.LBWH(BAR_CENTER - 2, BAR_BOTTOM - 2, 4, BAR_H + 4), WHITE)

        # Chevrons racing the way everyone is about to be thrown.
        cue = b.cue
        if cue and b.jolt != "bump":
            thrown = cue[1]
            for index in range(3):
                x = BAR_CENTER + thrown * (64 + index * 46 + (self.anim * 170) % 46)
                arcade.draw_polygon_filled(
                    [(x, 76), (x + thrown * 14, 68), (x, 60)], RED if b.active else BAR_AMBER,
                )

        if b.recover > 0:
            lean, tilt = b.fell_toward * 0.93, b.fell_toward * 80
            alpha = 255 if int(b.recover * 10) % 2 else 110
        else:
            lean, tilt, alpha = b.lean, b.lean * 34, 255
        x, feet = BAR_CENTER + lean * BAR_REACH, BAR_BOTTOM + BAR_H + 2
        arcade.draw_ellipse_filled(x, feet, 48, 12, (8, 12, 20, 130))
        angle = math.radians(tilt)
        self.figure.angle = tilt
        self.figure.alpha = alpha
        self.figure.center_x = x + math.sin(angle) * BAR_FIGURE_H / 2
        self.figure.center_y = feet + math.cos(angle) * BAR_FIGURE_H / 2
        self.figures.draw(pixelated=True)

        since_fall = RECOVER_TIME - b.recover
        if b.recover > 0 and since_fall < 0.25:
            arcade.draw_rect_filled(
                arcade.LBWH(0, 0, WIDTH, HEIGHT), (255, 70, 70, round(110 * (1 - since_fall / 0.25))),
            )

    def draw_bar_text(self):
        b, stage = self.balance, self.stage
        flash = math.sin(self.anim * 18) > 0
        left, right, left_color, right_color = "A  Lean", "Lean  D", WHITE, WHITE
        cue = b.cue
        if cue:
            text, thrown = cue
            alarm = RED if flash else WHITE
            if b.jolt == "bump":
                left, right, left_color, right_color = "Bumpy", "Road!", alarm, alarm
            elif thrown < 0:
                left, right, left_color = text, "Hold D!", alarm
            else:
                left, right, right_color = "Hold A!", text, alarm
        self.say(self.left_text, left, left_color)
        self.say(self.right_text, right, right_color)
        self.left_text.draw()
        self.right_text.draw()
        if b.recover > 0:
            self.ouch_text.x, self.ouch_text.y = stage.to_screen(
                BAR_CENTER + b.fell_toward * (BAR_REACH - 120), 112,
            )
            self.ouch_text.draw()

    def draw_alert(self):
        stage = self.stage
        left, bottom, width, height = ALERT_BOX
        arcade.draw_texture_rect(self.plates[ALERT_BOX], stage.rect(
            left - PLANK_PAD, bottom - PLANK_PAD, width + 2 * PLANK_PAD, height + 2 * PLANK_PAD,
        ))
        key_left, key_bottom = left + 26, bottom + (height - KEY_H) / 2
        arcade.draw_texture_rect(self.keycap, stage.rect(
            key_left - 2, key_bottom - 2, KEY_W + 4, KEY_H + 4,
        ))
        letter = chr(self.event_key).upper()
        self.say(self.alert_key, letter)
        self.say(self.alert_name, EVENT_NAMES[self.event])
        self.say(self.alert_detail,
                 f"Tap {letter}   {self.presses} / {EVENT_PRESSES[self.event]}")
        arcade.draw_rect_filled(
            stage.rect(left + 112, bottom + 10, 362, 5), (255, 255, 255, 46),
        )
        arcade.draw_rect_filled(stage.rect(
            left + 112, bottom + 10, 362 * max(0.0, self.event_left / EVENT_TIME), 5,
        ), BAR_RED if self.event_left < 2.5 else BAR_AMBER)
        for text in (self.alert_kicker, self.alert_name, self.alert_detail, self.alert_key):
            text.draw()

    def on_draw(self):
        self.clear()
        self.camera.use()
        self.draw_cabin()
        if self.mode in ("ride", "leaving"):
            self.draw_bar()

        self.window.default_camera.use()
        self.hud.draw()
        if self.mode in ("ride", "leaving"):
            self.draw_bar_text()
        if self.mode == "ride":
            if self.event is not None:
                self.draw_alert()
            elif self.anim < RIDE_HINT_TIME:
                self.hint_shadow.draw()
                self.hint.draw()
        self.title_card.draw()
        if self.mode == "leaving":
            self.draw_fade(255 * self.leave_time / LEAVE_FADE)
        self.draw_menus()

    # --- Input --------------------------------------------------------------

    def key_down(self, key):
        if self.mode == "title":
            if key == arcade.key.SPACE:
                self.title_card.skip()
            return
        if self.mode == "ride" and self.event is not None and key == self.event_key:
            self.presses += 1
            if self.presses >= EVENT_PRESSES[self.event]:
                audio.play("bus_protect")
                self.event = None
                self.next_event = self.elapsed + self.rng.uniform(*SOLVED_EVENT_DELAY)
            return
        super().key_down(key)
