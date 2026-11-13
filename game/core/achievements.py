import arcade

from . import audio, textures
from .ui import Stage
from ..config import (
    ACHIEVEMENT_SOUND, ACHIEVEMENT_TOAST_TIME, ACHIEVEMENTS, HEIGHT, PLANK_PAD,
    TEXT_BRIGHT, TEXT_DIM, TEXT_HOVER, WIDTH,
)

BY_KEY = {entry[0]: entry for entry in ACHIEVEMENTS}


_unlocked = set()   # session only: every launch starts with none unlocked
_queue = []   # keys waiting for their popup


def unlocked(key):
    return key in _unlocked


def count(scene=None):
    keys = [entry[0] for entry in ACHIEVEMENTS if scene in (None, entry[1])]
    return sum(key in _unlocked for key in keys), len(keys)


def for_scene(scene):
    return [entry for entry in ACHIEVEMENTS if entry[1] == scene]


def unlock(key):
    if key not in BY_KEY or key in _unlocked:
        return False
    _unlocked.add(key)
    _queue.append(key)
    return True


TOAST_W = 400
TOAST_LEFT = (WIDTH - TOAST_W) / 2
TOAST_H = 78
TOAST_TOP = 18      # gap from the top of the canvas
SLIDE = 0.35        # seconds to slide in and out
ICON = 46


class Toast:
    def __init__(self, window):
        self.window = window
        self.key = None
        self.clock = 0.0
        self.size = None

    def layout(self):
        self.size = (self.window.width, self.window.height)
        self.stage = Stage(*self.size)
        stage = self.stage
        self.card = textures.hud_plate(
            stage.px(TOAST_W), stage.px(TOAST_H), stage.px(PLANK_PAD), True)
        self.icon = textures.icon("medal", stage.px(ICON))
        title = BY_KEY[self.key][2]
        self.kicker = stage.text(
            "ACHIEVEMENT UNLOCKED", 0, 0, TEXT_DIM, 11,
            anchor_y="center", bold=True)
        self.title = stage.text(title, 0, 0, TEXT_BRIGHT, 20,
                                anchor_y="center", bold=True)

    def update(self, delta_time):
        if self.key is None:
            if not _queue:
                return
            self.key = _queue.pop(0)
            self.clock = 0.0
            self.size = None
            audio.play(ACHIEVEMENT_SOUND)
        self.clock += delta_time
        if self.clock >= ACHIEVEMENT_TOAST_TIME:
            self.key = None

    def on_draw(self):
        if self.key is None:
            return
        if self.size != (self.window.width, self.window.height):
            self.layout()
        self.window.default_camera.use()
        t = min(self.clock, ACHIEVEMENT_TOAST_TIME - self.clock) / SLIDE
        t = max(0.0, min(1.0, t))
        ease = 1 - (1 - t) ** 3
        bottom = HEIGHT - TOAST_TOP - TOAST_H + (1 - ease) * (TOAST_H + TOAST_TOP + 20)
        left = TOAST_LEFT
        stage = self.stage
        arcade.draw_texture_rect(self.card, stage.rect(
            left - PLANK_PAD, bottom - PLANK_PAD,
            TOAST_W + 2 * PLANK_PAD, TOAST_H + 2 * PLANK_PAD))
        arcade.draw_texture_rect(
            self.icon,
            stage.rect(left + 22, bottom + (TOAST_H - ICON) / 2, ICON, ICON),
            color=arcade.types.Color(*TEXT_HOVER))
        for text, offset in ((self.kicker, 54), (self.title, 28)):
            text.x, text.y = stage.to_screen(left + 38 + ICON, bottom + offset)
            text.draw()


def attach(window):
    toast = Toast(window)
    window.push_handlers(on_draw=toast.on_draw, on_update=toast.update)
    window.achievement_toast = toast
