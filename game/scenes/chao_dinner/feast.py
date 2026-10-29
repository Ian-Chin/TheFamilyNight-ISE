"""The leftover feast: a monkeytype style typing game.

The family has gone and Terry is left with a table of food. The garden fills
the top of the screen, cropped to the table, with an on-screen keyboard on
the dark ground under it. Words run along a monospaced line in the middle:
typed letters light up, wrong ones go red, and a caret slides along under
the next letter, with the line after it waiting underneath.

Every word typed right is a bite. The table empties a course at a time as
the bites add up (the background crossfades through FEAST_STAGES), with
crumbs, a chomp and a line from Terry each time. The clock starts after a
count in; the round ends when it runs out or the table is clear, and the
results show the WPM, the accuracy, a WPM graph over the round and whether
the food got finished.
"""

import math
import random

import arcade
import PIL.Image
import PIL.ImageDraw
import pyglet

from ...core import audio, textures
from ...core.backdrop import Backdrop
from ...config import (
    AMBIENCE_NIGHT, FEAST_STAGES, GLASS_EDGE, GLASS_EDGE_HOVER, GLASS_FILL,
    GLASS_FILL_HOVER, GLASS_FILL_PANEL, HEIGHT, MENU_FONT, PLANK_PAD, QUEST_DONE, ROOT,
    TEXT_BRIGHT, TEXT_DIM, TEXT_HOVER, TEXT_SHADOW, WIDTH,
)
from .config import (
    FEAST_CARET, FEAST_COMBO_EVERY, FEAST_CORRECT, FEAST_COUNT_STEP, FEAST_CROP,
    FEAST_EXTRA, FEAST_FLOOR, FEAST_FONT, FEAST_GOAL_WORDS, FEAST_HURRY,
    FEAST_KEY_EDGE, FEAST_KEY_FACE, FEAST_KEY_GAP, FEAST_KEY_GLOW, FEAST_KEY_H,
    FEAST_KEY_HIT, FEAST_KEY_ROWS, FEAST_KEY_TOP, FEAST_KEY_W, FEAST_MAX_EXTRA,
    FEAST_OUT_TIME, FEAST_QUEUE, FEAST_SCENE_BOTTOM, FEAST_SLIDE, FEAST_SPACE_W,
    FEAST_STAGE_FADE, FEAST_STAGE_LINES, FEAST_TABLE_AREA, FEAST_TIME, FEAST_UNTYPED,
    FEAST_WORDS, FEAST_WORD_SIZE, FEAST_WORD_Y, FEAST_WRONG,
)
from ...core.options import SettingsPanel
from ...core.pause import PauseMenu
from ...core.ui import MenuButton
from ...core.stage import StageView

EMOTION_DIR = ROOT / "assets" / "emotions"
RESULT_W = 940
RESULT_H = 500
RESULT_LEFT = (WIDTH - RESULT_W) / 2
RESULT_BOTTOM = (HEIGHT - RESULT_H) / 2 - 6
GRAPH = (RESULT_LEFT + 430, RESULT_BOTTOM + 128, 470, 210)   # left, bottom, w, h
CRUMB_COLORS = (
    (214, 150, 74), (182, 104, 52), (236, 196, 120), (120, 168, 72),
    (220, 90, 60), (246, 222, 170),
)
BITE_WORDS = ("nom!", "yum!", "munch", "crunch!", "mmm", "chomp!", "gulp")


def ease_out(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def back_out(t):
    """Overshoots a little past 1 and settles, for things that pop in."""
    t = min(max(t, 0.0), 1.0)
    c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def with_alpha(color, alpha):
    return (*color[:3], max(0, min(255, round(alpha))))


def gradient_texture(color, name):
    """A tall strip of `color` going from solid at the bottom to clear on top."""
    image = PIL.Image.new("RGBA", (4, 256))
    pixels = image.load()
    for y in range(256):
        alpha = round(255 * (y / 255) ** 1.6)
        for x in range(4):
            pixels[x, y] = (*color, alpha)
    return arcade.Texture(image, hash=f"feast-gradient-{name}")


_flat_cache = {}


def flat_panel(width, height, pad, fill=GLASS_FILL, edge=GLASS_EDGE, edge_w=2):
    """A square-cornered glass panel, `width` x `height` pixels inside a
    clear margin of `pad`, laid out like the rounded planks it stands in for."""
    key = (width, height, pad, fill, edge, edge_w)
    if key not in _flat_cache:
        image = PIL.Image.new("RGBA", (width + 2 * pad, height + 2 * pad), (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(image)
        box = (pad, pad, pad + width - 1, pad + height - 1)
        draw.rectangle(box, fill=fill, outline=edge, width=edge_w)
        _flat_cache[key] = arcade.Texture(image, hash=f"feast-flat-{key}")
    return _flat_cache[key]


def flatten(widget, stage):
    """Swap a laid out widget's rounded art for square-cornered panels."""
    pad = stage.px(PLANK_PAD)
    if hasattr(widget, "plank"):
        size = (stage.px(widget.width), stage.px(widget.height), pad)
        widget.plank = flat_panel(*size)
        widget.plank_hovered = flat_panel(*size, fill=GLASS_FILL_HOVER, edge=GLASS_EDGE_HOVER)
    if hasattr(widget, "texture") and hasattr(widget, "height"):
        widget.texture = flat_panel(stage.px(widget.width), stage.px(widget.height), pad,
                                    fill=GLASS_FILL_PANEL)
    for button in getattr(widget, "buttons", ()):
        flatten(button, stage)


def emotion(name):
    """One of Terry's framed faces, trimmed to its frame."""
    image = PIL.Image.open(EMOTION_DIR / f"{name}.png").convert("RGBA")
    return arcade.Texture(image.crop(image.getbbox()), hash=f"feast-emotion-{name}")


class Particle(arcade.SpriteSolidColor):
    """A crumb or a spark. `px, py` are canvas units; the sprite itself is
    placed in window pixels each frame, so a whole burst draws in one go."""

    def __init__(self, x, y, vx, vy, life, size, color, spark=False):
        super().__init__(1, 1, color=arcade.types.Color(*color))
        self.px, self.py, self.vx, self.vy = x, y, vx, vy
        self.life, self.age = life, 0.0
        self.base_size, self.spark = size, spark


class Floater:
    """A word that pops up, drifts upward and fades away."""

    def __init__(self, labels, x, y, color, life=0.9, rise=46):
        """`labels` is the (shadow, text) pair to draw, shared with any other
        floater of the same word: each one is placed just before it draws."""
        self.x, self.y = x, y
        self.life, self.age, self.rise = life, 0.0, rise
        self.color = color
        self.shadow, self.text = labels

    def draw(self, stage):
        t = self.age / self.life
        alpha = 255 * (1 - max(0.0, (t - 0.55) / 0.45))
        y = self.y + self.rise * ease_out(t)
        for text, offset, color in ((self.shadow, 2, TEXT_SHADOW), (self.text, 0, self.color)):
            text.x, text.y = stage.to_screen(self.x + offset, y - offset)
            text.color = with_alpha(color, alpha)
            text.draw()


class TypingFeastView(StageView):
    """Intro, count in, the timed round, then the results."""

    def __init__(self):
        super().__init__()
        self.courses = [Backdrop(still) for still, _ in FEAST_STAGES]
        for course in self.courses:
            course.reserve()
        self.floor_fade = gradient_texture(FEAST_FLOOR, "floor")
        self.top_fade = gradient_texture((4, 6, 10), "top")
        self.faces = {
            "win": emotion("Terry_smile_excited"),
            "intro": emotion("Terry_excited"),
        }
        self.pause_menu = PauseMenu()
        self.settings_panel = SettingsPanel()
        button_y = RESULT_BOTTOM + 34
        # Continue carries the story on to the ending; Enter takes it too.
        self.result_buttons = [
            MenuButton("Continue", "continue", "award",
                       WIDTH / 2 - 405 - 18, button_y, 270, 56),
            MenuButton("Play again", "retry", "play",
                       WIDTH / 2 - 135, button_y, 270, 56),
            MenuButton("Main Menu", "menu", "book",
                       WIDTH / 2 + 135 + 18, button_y, 270, 56),
        ]
        self.widgets = [*self.result_buttons, self.pause_menu, self.settings_panel]
        self.clock = 0.0
        self.reset()
        self.relayout()

    # --- round state --------------------------------------------------------

    def reset(self):
        """A fresh round, waiting on the intro card."""
        self.mode = "intro"          # intro, count, play, ending, results
        self.mode_clock = 0.0
        self.time_left = FEAST_TIME
        self.elapsed = 0.0
        self.words = []
        self.typed = []
        self.index = 0
        self.more_words(120)
        self.correct_words = 0
        self.correct_keys = 0
        self.wrong_keys = 0
        self.typed_chars = 0
        self.streak = 0
        self.best_streak = 0
        self.history = []            # (second, wpm, raw, errors) per second
        self.second_chars = 0
        self.second_errors = 0
        self.next_second = 1
        self.course = 0
        self.old_course = None
        self.course_clock = FEAST_STAGE_FADE
        self.meter = 0.0             # the food meter's eased fill
        self.bump = 0.0
        self.shake = 0.0
        self.flash = 0.0
        self.hurry_second = None
        self.idle = 0.0              # seconds since the last key, for the caret
        self.slide = 0.0             # 1 just after a word, easing back to 0
        self.caret_x = None
        self.outgoing = None         # (texts, seconds since, colour) of the word just done
        self.key_glow = {}           # key -> (seconds left, color)
        self.crumbs = arcade.SpriteList()
        self.sparks = arcade.SpriteList()
        self.floaters = []
        self.banner = None           # (texts, seconds since shown)
        self.results = None
        self.dirty = True

    def more_words(self, count):
        """Top the word queue up, never the same word twice in a row."""
        for _ in range(count):
            word = random.choice(FEAST_WORDS)
            while self.words and word == self.words[-1]:
                word = random.choice(FEAST_WORDS)
            self.words.append(word)
            self.typed.append("")

    @property
    def progress(self):
        return min(1.0, self.correct_words / FEAST_GOAL_WORDS)

    @property
    def finished_food(self):
        return self.correct_words >= FEAST_GOAL_WORDS

    def correct_chars(self):
        """Letters of the words typed right, with the space after each."""
        total = sum(len(self.words[i]) + 1 for i in range(self.index)
                    if self.typed[i] == self.words[i])
        current = self.typed[self.index]
        if current and current == self.words[self.index]:
            total += len(current)
        return total

    def wpm(self):
        minutes = max(self.elapsed, 1.0) / 60
        return self.correct_chars() / 5 / minutes

    def raw(self):
        minutes = max(self.elapsed, 1.0) / 60
        return self.typed_chars / 5 / minutes

    def accuracy(self):
        total = self.correct_keys + self.wrong_keys
        return 100.0 if total == 0 else 100 * self.correct_keys / total

    def char_counts(self):
        """(correct, incorrect, extra, missed) letters over the words typed."""
        counts = [0, 0, 0, 0]
        last = self.index + (1 if self.typed[self.index] else 0)
        for i in range(last):
            word, typed = self.words[i], self.typed[i]
            for j, letter in enumerate(typed[:len(word)]):
                counts[0 if letter == word[j] else 1] += 1
            counts[2] += max(0, len(typed) - len(word))
            if i < self.index:
                counts[3] += max(0, len(word) - len(typed))
        return counts

    # --- layout -------------------------------------------------------------

    def relayout(self):
        super().relayout()
        stage = self.stage
        probe = arcade.Text("M" * 20, 0, 0, font_size=FEAST_WORD_SIZE * stage.scale,
                            font_name=FEAST_FONT, bold=True)
        self.advance = probe.content_width / 20 / stage.scale
        self.dirty = True
        self.labels = {}
        # Labels changed in place as the words go by, rather than rebuilt.
        self.run_pool = []
        self.queue_texts = [
            arcade.Text("", 0, 0, FEAST_UNTYPED, size * stage.scale, font_name=FEAST_FONT,
                        anchor_x="center", anchor_y="center")
            for _, size, _ in FEAST_QUEUE
        ]
        self.out_text = arcade.Text("", 0, 0, QUEST_DONE, FEAST_WORD_SIZE * 0.8 * stage.scale,
                                    font_name=FEAST_FONT, bold=True,
                                    anchor_x="center", anchor_y="center")
        self.warm_glyphs()
        for widget in self.widgets:
            flatten(widget, stage)
        self.build_keyboard()
        self.build_hud()
        if self.results is not None:
            self.build_results()

    def warm_glyphs(self):
        """Lay every letter out once at each size the round uses.

        A glyph is rasterised the first time it is shown at a given font and
        size, and doing that in the middle of the round stalls the frame the
        word is finished on. Doing it here moves the cost to the load.
        """
        letters = "abcdefghijklmnopqrstuvwxyz"
        scale = self.stage.scale
        sizes = [(FEAST_FONT, FEAST_WORD_SIZE, True), (FEAST_FONT, FEAST_WORD_SIZE * 0.8, True)]
        sizes += [(FEAST_FONT, size, False) for _, size, _ in FEAST_QUEUE]
        sizes += [(MENU_FONT, 18, True), (MENU_FONT, 34, True), (MENU_FONT, 13, True)]
        extra = "".join(BITE_WORDS) + "".join(FEAST_STAGE_LINES) + "0123456789!.,'%x "
        for font, size, bold in sizes:
            arcade.Text(letters + letters.upper() + extra, 0, 0, font_size=size * scale,
                        font_name=font, bold=bold)
        # The pop-up words and course lines, built now rather than on a bite.
        for key in (0, 1):
            for word in BITE_WORDS:
                self.label(word, 18, MENU_FONT, key=key, bold=True, anchor_x="center",
                           anchor_y="center")
            for line in FEAST_STAGE_LINES:
                self.label(line, 34, MENU_FONT, key=key, bold=True, anchor_x="center",
                           anchor_y="center")

    def label(self, content, size, font, key=0, **kwargs):
        """A Text for `content`, made once per layout and handed out again.

        Building an arcade.Text looks its font up through DirectWrite, about
        a millisecond each, so the words of the round reuse theirs instead.
        `key` tells apart copies that are drawn at the same time.
        """
        cache_key = (content, size, font, key, tuple(sorted(kwargs.items())))
        text = self.labels.get(cache_key)
        if text is None:
            text = arcade.Text(content, 0, 0, TEXT_BRIGHT, size * self.stage.scale,
                               font_name=font, **kwargs)
            self.labels[cache_key] = text
        return text

    def text(self, content, x, y, color, size, font=MENU_FONT, **kwargs):
        sx, sy = self.stage.to_screen(x, y)
        return arcade.Text(content, sx, sy, color, size * self.stage.scale,
                           font_name=font, **kwargs)

    def shadowed(self, content, x, y, color, size, drop=2, **kwargs):
        return [self.text(content, x + offset, y - offset, shade, size, **kwargs)
                for offset, shade in ((drop, TEXT_SHADOW), (0, color))]

    def build_keyboard(self):
        stage = self.stage
        self.keys = {}
        self.key_batch = pyglet.graphics.Batch()
        self.key_labels = {}
        row_w = len(FEAST_KEY_ROWS[0]) * (FEAST_KEY_W + FEAST_KEY_GAP) - FEAST_KEY_GAP
        first_left = (WIDTH - row_w) / 2
        stagger = (0, 0.32 * FEAST_KEY_W, 0.92 * FEAST_KEY_W)
        middle_y = FEAST_KEY_TOP - FEAST_KEY_H / 2
        for row, letters in enumerate(FEAST_KEY_ROWS):
            left = first_left + stagger[row]
            for letter in letters:
                self.keys[letter] = (left, middle_y - FEAST_KEY_H / 2, FEAST_KEY_W, FEAST_KEY_H)
                left += FEAST_KEY_W + FEAST_KEY_GAP
            middle_y -= FEAST_KEY_H + FEAST_KEY_GAP
        self.keys[" "] = ((WIDTH - FEAST_SPACE_W) / 2, middle_y - FEAST_KEY_H / 2,
                          FEAST_SPACE_W, FEAST_KEY_H)
        for key, (left, bottom, w, h) in self.keys.items():
            label = key.upper() if key != " " else "space"
            sx, sy = stage.to_screen(left + w / 2, bottom + h / 2)
            self.key_labels[key] = arcade.Text(
                label, sx, sy, TEXT_DIM, (12 if key != " " else 10) * stage.scale,
                font_name=MENU_FONT, bold=True, anchor_x="center",
                anchor_y="center", batch=self.key_batch,
            )
        # The resting keys never change, so they are baked into one shape list;
        # only the lit and hinted keys are drawn on top each frame.
        self.key_shapes = arcade.shape_list.ShapeElementList()
        edge = max(1, stage.scale)
        for key, (left, bottom, w, h) in self.keys.items():
            x, y = stage.to_screen(left + w / 2, bottom + h / 2)
            self.key_shapes.append(arcade.shape_list.create_rectangle_filled(
                x, y, w * stage.scale, h * stage.scale, FEAST_KEY_FACE))
            self.key_shapes.append(arcade.shape_list.create_rectangle_outline(
                x, y, w * stage.scale, h * stage.scale, FEAST_KEY_EDGE, edge))
        # The bumps on F and J, for fingers to find home.
        for key in "fj":
            left, bottom, w, h = self.keys[key]
            self.key_shapes.append(arcade.shape_list.create_line(
                *stage.to_screen(left + w / 2 - 5, bottom + 6),
                *stage.to_screen(left + w / 2 + 5, bottom + 6),
                (255, 255, 255, 90), max(1, 2 * stage.scale)))
        self.lit_keys = set()   # keys whose labels are not at rest

    def build_hud(self):
        stage = self.stage
        pad = stage.px(PLANK_PAD)
        self.small_plate = flat_panel(stage.px(170), stage.px(70), pad)
        self.small_plate_hot = flat_panel(stage.px(170), stage.px(70), pad,
                                          edge=with_alpha(FEAST_WRONG, 230))
        self.wide_plate = flat_panel(stage.px(200), stage.px(70), pad)
        self.meter_plate = flat_panel(stage.px(420), stage.px(70), pad)
        self.timer_text = self.shadowed("60", 110, HEIGHT - 48, TEXT_HOVER, 32,
                                        bold=True, anchor_x="center", anchor_y="center")
        self.timer_note = self.text("seconds", 110, HEIGHT - 76, TEXT_DIM, 11,
                                    anchor_x="center", anchor_y="center")
        self.wpm_text = self.shadowed("0", WIDTH - 135, HEIGHT - 48, TEXT_BRIGHT, 26,
                                      bold=True, anchor_x="center", anchor_y="center")
        self.wpm_note = self.text("wpm   ·   100% acc", WIDTH - 135, HEIGHT - 76,
                                  TEXT_DIM, 11, anchor_x="center", anchor_y="center")
        self.meter_label = self.text("LEFTOVERS EATEN", WIDTH / 2 - 190, HEIGHT - 42,
                                     TEXT_HOVER, 11, bold=True, anchor_y="center")
        self.meter_value = self.text("0%", WIDTH / 2 + 190, HEIGHT - 42, TEXT_BRIGHT,
                                     13, bold=True, anchor_x="right", anchor_y="center")
        self.streak_text = self.shadowed("", WIDTH / 2, FEAST_WORD_Y + 56, TEXT_HOVER, 13,
                                         drop=1.5, bold=True, anchor_x="center",
                                         anchor_y="center")
        self.hint_text = self.text(
            "Space to finish a word    Backspace to fix    Tab to restart    Esc to pause",
            WIDTH / 2, HEIGHT - 110, TEXT_DIM, 11,
            anchor_x="center", anchor_y="center")
        self.shown_hud = None
        self.intro_texts = [
            *self.shadowed("M I N I   G A M E", WIDTH / 2, HEIGHT / 2 + 128, TEXT_HOVER, 15,
                           bold=True, anchor_x="center", anchor_y="center"),
            *self.shadowed("Leftover Feast", WIDTH / 2, HEIGHT / 2 + 76, TEXT_BRIGHT, 54,
                           drop=3, bold=True, anchor_x="center", anchor_y="center"),
            *self.shadowed("Everyone's gone. The food isn't.", WIDTH / 2, HEIGHT / 2 + 26,
                           TEXT_DIM, 17, italic=True, anchor_x="center", anchor_y="center"),
            *self.shadowed("Type the words and press Space. Every word you get right is a bite.",
                           WIDTH / 2, HEIGHT / 2 - 26, TEXT_BRIGHT, 16,
                           anchor_x="center", anchor_y="center"),
            *self.shadowed(f"Eat {FEAST_GOAL_WORDS} bites in {int(FEAST_TIME)} seconds to clear the table.",
                           WIDTH / 2, HEIGHT / 2 - 54, TEXT_BRIGHT, 16,
                           anchor_x="center", anchor_y="center"),
        ]
        self.intro_press = self.shadowed("Press any key to start", WIDTH / 2, HEIGHT / 2 - 116,
                                         TEXT_HOVER, 19, bold=True,
                                         anchor_x="center", anchor_y="center")
        self.count_texts = {
            label: self.shadowed(label, WIDTH / 2, HEIGHT / 2 + 40, TEXT_BRIGHT if label != "EAT!" else TEXT_HOVER,
                                 120, drop=5, bold=True, anchor_x="center", anchor_y="center")
            for label in ("3", "2", "1", "EAT!")
        }
        if self.banner is not None:
            self.banner = (self.make_banner(self.banner[2], self.banner[3]), self.banner[1],
                           self.banner[2], self.banner[3])

    def make_banner(self, content, color):
        texts = [self.label(content, 34, MENU_FONT, key=k, bold=True, anchor_x="center",
                            anchor_y="center") for k in (0, 1)]
        texts[0].color, texts[1].color = TEXT_SHADOW, color
        for text, offset in zip(texts, (3, 0)):
            text.x = self.stage.to_screen(WIDTH / 2 + offset, 0)[0]
        return texts

    def show_banner(self, content, color=TEXT_HOVER):
        self.banner = (self.make_banner(content, color), 0.0, content, color)

    # --- the words -----------------------------------------------------------

    def word_runs(self):
        """The word being typed as runs of same-coloured letters:
        (first column, text, colour), and how many columns it takes."""
        word, typed = self.words[self.index], self.typed[self.index]
        runs, current = [], None
        width = max(len(word), len(typed))
        for j in range(width):
            if j < len(typed):
                if j < len(word):
                    letter = word[j]
                    color = FEAST_CORRECT if typed[j] == word[j] else FEAST_WRONG
                else:
                    letter, color = typed[j], FEAST_EXTRA
            else:
                letter, color = word[j], FEAST_UNTYPED
            if current is not None and current[2] == color:
                current[1] += letter
            else:
                current = [j, letter, color]
                runs.append(current)
        return runs, width

    def rebuild_words(self):
        """Lay out the word being typed and the stack waiting under it."""
        self.dirty = False
        runs, self.word_cols = self.word_runs()
        while len(self.run_pool) < len(runs):
            self.run_pool.append(arcade.Text(
                "", 0, 0, FEAST_UNTYPED, FEAST_WORD_SIZE * self.stage.scale,
                font_name=FEAST_FONT, bold=True, anchor_y="center"))
        self.word_texts = []
        for text, (column, content, color) in zip(self.run_pool, runs):
            if text.text != content:
                text.text = content
            self.word_texts.append((column, text, color))
        for k, text in enumerate(self.queue_texts):
            word = self.words[self.index + 1 + k]
            if text.text != word:
                text.text = word

    @staticmethod
    def queue_slot(place):
        """(y, size, opacity) at `place` in the stack: 0 is the middle, 1 the
        first waiting word, and so on; fractions are part way between."""
        slots = ((FEAST_WORD_Y, FEAST_WORD_SIZE, 255), *FEAST_QUEUE,
                 (FEAST_QUEUE[-1][0] - 30, FEAST_QUEUE[-1][1] - 3, 0))
        place = min(max(place, 0.0), len(slots) - 1.0)
        low = int(place)
        high = min(low + 1, len(slots) - 1)
        t = place - low
        return tuple(a + (b - a) * t for a, b in zip(slots[low], slots[high]))

    def send_off(self, word, right):
        """The word just finished floats up out of the middle and fades."""
        color = QUEST_DONE if right else FEAST_WRONG
        self.out_text.text = word
        self.outgoing = ([self.out_text], 0.0, color)

    # --- effects ------------------------------------------------------------

    def burst(self, x, y, count, spark=False, spread=1.0):
        for _ in range(count):
            angle = random.uniform(0.15 * math.pi, 0.85 * math.pi) if not spark \
                else random.uniform(0, 2 * math.pi)
            speed = random.uniform(120, 330) * spread
            color = random.choice(CRUMB_COLORS) if not spark else random.choice(
                ((255, 236, 160), (255, 214, 138), (255, 255, 255), (180, 240, 200)))
            (self.sparks if spark else self.crumbs).append(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                random.uniform(0.5, 1.0) if not spark else random.uniform(0.6, 1.2),
                random.uniform(3, 7) if not spark else random.uniform(2, 4),
                color, spark,
            ))

    def bite(self):
        """A word typed right: crumbs fly off somewhere on the table."""
        left, right, bottom, top = FEAST_TABLE_AREA
        x, y = random.uniform(left, right), random.uniform(bottom, top)
        self.burst(x, y, 14)
        self.bump = 1.0
        if random.random() < 0.55:
            word = random.choice(BITE_WORDS)
            labels = tuple(self.label(word, 18, MENU_FONT, bold=True, anchor_x="center",
                                      anchor_y="center", key=k) for k in (0, 1))
            self.floaters.append(Floater(labels, x, y + 20, TEXT_HOVER))

    def set_course(self, course):
        if course == self.course:
            return
        self.old_course, self.course = self.course, course
        self.course_clock = 0.0
        self.flash = 1.0
        audio.play("feast_chomp")
        audio.play("feast_stage")
        if 1 <= course <= len(FEAST_STAGE_LINES):
            self.show_banner(FEAST_STAGE_LINES[course - 1],
                             QUEST_DONE if course == len(FEAST_STAGES) - 1 else TEXT_HOVER)
        left, right, bottom, top = FEAST_TABLE_AREA
        for _ in range(4):
            self.burst(random.uniform(left, right), random.uniform(bottom, top), 12, spark=True)

    # --- input --------------------------------------------------------------

    def glow(self, key, color):
        if key in self.keys:
            self.key_glow[key] = (FEAST_KEY_GLOW, color)

    def type_letter(self, letter):
        word = self.words[self.index]
        typed = self.typed[self.index]
        if len(typed) >= len(word) + FEAST_MAX_EXTRA:
            return
        right = len(typed) < len(word) and word[len(typed)] == letter
        self.typed[self.index] = typed + letter
        self.typed_chars += 1
        self.second_chars += 1
        self.idle = 0.0
        self.dirty = True
        if right:
            self.correct_keys += 1
            self.glow(letter, FEAST_KEY_HIT)
            audio.play("feast_key", speed=random.uniform(0.92, 1.1))
        else:
            self.wrong_keys += 1
            self.second_errors += 1
            self.glow(letter, FEAST_WRONG)
            self.shake = 1.0
            audio.play("feast_error")

    def finish_word(self):
        word, typed = self.words[self.index], self.typed[self.index]
        if not typed:
            return
        self.typed_chars += 1
        self.second_chars += 1
        self.idle = 0.0
        self.glow(" ", FEAST_KEY_HIT)
        self.send_off(typed, typed == word)
        if typed == word:
            self.correct_keys += 1
            self.correct_words += 1
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
            audio.play("feast_word", speed=random.uniform(0.95, 1.12))
            self.bite()
            if self.streak % FEAST_COMBO_EVERY == 0:
                audio.play("feast_combo")
                self.show_banner(f"{self.streak} in a row!", (255, 236, 160))
                self.burst(WIDTH / 2, FEAST_WORD_Y, 26, spark=True)
            self.set_course(min(len(FEAST_STAGES) - 1,
                                int(self.progress * (len(FEAST_STAGES) - 1) + 1e-9)))
        else:
            self.wrong_keys += 1
            self.second_errors += 1
            self.streak = 0
            self.shake = 0.7
            audio.play("feast_error")
        self.index += 1
        if self.index + 60 > len(self.words):
            self.more_words(60)
        self.slide = 1.0
        self.caret_x = None
        self.dirty = True
        if self.finished_food:
            self.end_round()

    def backspace(self, whole_word):
        self.idle = 0.0
        if self.typed[self.index]:
            self.typed[self.index] = "" if whole_word else self.typed[self.index][:-1]
            self.dirty = True
            audio.play("feast_key", speed=0.8)
            return
        # A word sent off is gone, like a bite already eaten.

    def on_text(self, text):
        if self.pause_menu.visible or self.settings_panel.visible:
            return
        if self.mode == "intro":
            return
        if self.mode != "play":
            return
        for letter in text.lower():
            if letter == " ":
                self.finish_word()
            elif "a" <= letter <= "z":
                self.type_letter(letter)
            if self.mode != "play":
                return

    def on_key_press(self, key, modifiers):
        if self.settings_panel.visible:
            if self.settings_panel.on_key_press(key) == "close":
                self.settings_panel.close()
            return
        if self.pause_menu.visible:
            self.run_action(self.pause_menu.on_key_press(key))
            return
        if key == arcade.key.ESCAPE:
            self.pause_menu.open()
            return
        if key == arcade.key.TAB:
            self.restart()
            return
        if self.mode == "intro":
            self.start_count()
            return
        if self.mode == "results":
            if self.mode_clock > 1.0 and key in (arcade.key.ENTER, arcade.key.NUM_ENTER):
                self.run_action("continue")
            return
        if self.mode == "play" and key == arcade.key.BACKSPACE:
            self.backspace(bool(modifiers & (arcade.key.MOD_CTRL | arcade.key.MOD_ALT)))

    def on_mouse_motion(self, x, y, dx, dy):
        x, y = self.canvas_point(x, y)
        self.pause_menu.on_mouse_motion(x, y)
        if self.mode == "results" and not self.pause_menu.visible:
            for button in self.result_buttons:
                button.hovered = button.contains(x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        x, y = self.canvas_point(x, y)
        if self.settings_panel.on_mouse_press(x, y, button):
            return
        if self.pause_menu.visible:
            self.run_action(self.pause_menu.on_mouse_press(x, y, button))
            return
        if self.mode == "results" and button == arcade.MOUSE_BUTTON_LEFT:
            for item in self.result_buttons:
                if item.contains(x, y):
                    audio.play("ui_click")
                    self.run_action(item.action)
                    return

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.settings_panel.on_mouse_drag(*self.canvas_point(x, y))

    def on_mouse_release(self, x, y, button, modifiers):
        self.settings_panel.on_mouse_release()

    def run_action(self, action):
        if action is None:
            return
        if action == "resume":
            self.pause_menu.close()
        elif action == "settings":
            self.settings_panel.open()
        elif action == "retry":
            self.restart()
        elif action == "continue":
            from ..ending.view import EndingView
            self.window.show_view(EndingView())
        elif action == "menu":
            from ..menu.view import MenuView
            self.window.show_view(MenuView())
        elif action == "quit":
            self.window.close()

    # --- flow ---------------------------------------------------------------

    def restart(self):
        old = self.course
        self.reset()
        self.relayout()
        if old:
            # The full table comes back the same way it went.
            self.old_course, self.course_clock = old, 0.0
        self.start_count()

    def start_count(self):
        self.mode = "count"
        self.mode_clock = 0.0
        self.count_shown = -1
        audio.play("feast_whoosh")

    def start_play(self):
        self.mode = "play"
        self.mode_clock = 0.0
        self.idle = 0.0

    def end_round(self):
        self.mode = "ending"
        self.mode_clock = 0.0
        self.record_second(final=True)
        if self.finished_food:
            self.show_banner("Table cleared!", QUEST_DONE)
            self.flash = 1.0
            for _ in range(6):
                self.burst(random.uniform(200, 1080), random.uniform(340, 640), 16, spark=True)
        else:
            self.show_banner("Time's up!", TEXT_HOVER)
        audio.play("feast_whoosh")

    def show_results(self):
        self.mode = "results"
        self.mode_clock = 0.0
        counts = self.char_counts()
        self.results = {
            "wpm": self.wpm(),
            "raw": self.raw(),
            "acc": self.accuracy(),
            "counts": counts,
            "time": self.elapsed,
            "eaten": self.progress,
            "won": self.finished_food,
            "streak": self.best_streak,
            "words": self.correct_words,
        }
        self.stamped = False
        self.build_results()
        audio.play("feast_whoosh")

    def record_second(self, final=False):
        """Note this second's speed and errors for the results graph."""
        span = self.elapsed - (self.next_second - 1)
        if final and span < 0.25:
            return
        raw = self.second_chars / 5 / (max(span, 0.25) / 60)
        self.history.append((self.elapsed, self.wpm(), raw, self.second_errors))
        self.second_chars = 0
        self.second_errors = 0
        self.next_second += 1

    # --- results panel ------------------------------------------------------

    def build_results(self):
        r = self.results
        left, bottom = RESULT_LEFT, RESULT_BOTTOM
        top = bottom + RESULT_H
        stage = self.stage
        self.result_card = flat_panel(stage.px(RESULT_W), stage.px(RESULT_H), stage.px(PLANK_PAD),
                                      fill=GLASS_FILL_PANEL)
        # Just the numbers: the story carries on whatever the score.
        eaten = round(100 * r["eaten"])
        self.res_title = self.shadowed("Your Stats", left + 200, top - 52, TEXT_HOVER,
                                       32, drop=2.5, bold=True, anchor_y="center")
        self.res_note = self.text(f"Leftovers eaten: {eaten}%", left + 200, top - 88,
                                  TEXT_DIM, 14, anchor_y="center")
        self.res_face = self.faces["win"]
        col = left + 46
        self.res_labels = [
            self.text("wpm", col, top - 172, TEXT_DIM, 16, anchor_y="center"),
            self.text("acc", col + 190, top - 172, TEXT_DIM, 16, anchor_y="center"),
        ]
        self.res_wpm = self.text("0", col - 2, top - 218, TEXT_HOVER, 56, bold=True, anchor_y="center")
        self.res_acc = self.text("0%", col + 188, top - 218, TEXT_HOVER, 56, bold=True, anchor_y="center")
        correct, incorrect, extra, missed = r["counts"]
        rows = (
            ("raw", f"{round(r['raw'])}"),
            ("characters", f"{correct}/{incorrect}/{extra}/{missed}"),
            ("bites", f"{r['words']}/{FEAST_GOAL_WORDS}"),
            ("best streak", f"{r['streak']}"),
            ("time", f"{r['time']:.1f}s"),
        )
        self.res_rows = []
        y = top - 276
        for label, value in rows:
            self.res_rows.append(self.text(label, col, y, TEXT_DIM, 13, anchor_y="center"))
            self.res_rows.append(self.text(value, col + 150, y, TEXT_BRIGHT, 15, bold=True,
                                           anchor_y="center"))
            y -= 24
        gl, gb, gw, gh = GRAPH
        self.peak = max([10.0] + [max(w, raw) for _, w, raw, _ in self.history])
        self.peak = math.ceil(self.peak / 20) * 20
        self.graph_labels = [
            self.text(str(round(self.peak * k / 4)), gl - 8, gb + gh * k / 4, TEXT_DIM, 10,
                      anchor_x="right", anchor_y="center")
            for k in range(5)
        ]
        self.graph_labels.append(self.text("speed over the round", gl, gb + gh + 18,
                                           TEXT_DIM, 11, anchor_y="center"))
        legend_x = gl + gw
        self.graph_labels.append(self.text("wpm", legend_x - 120, gb + gh + 18, TEXT_HOVER, 11,
                                           bold=True, anchor_x="right", anchor_y="center"))
        self.graph_labels.append(self.text("raw", legend_x - 64, gb + gh + 18, TEXT_DIM, 11,
                                           bold=True, anchor_x="right", anchor_y="center"))
        self.graph_labels.append(self.text("errors", legend_x, gb + gh + 18, FEAST_WRONG, 11,
                                           bold=True, anchor_x="right", anchor_y="center"))
        span = max(1.0, r["time"])
        self.graph_labels.append(self.text("0s", gl, gb - 14, TEXT_DIM, 10,
                                           anchor_x="center", anchor_y="center"))
        self.graph_labels.append(self.text(f"{round(span)}s", gl + gw, gb - 14, TEXT_DIM, 10,
                                           anchor_x="center", anchor_y="center"))

    def draw_results(self):
        stage = self.stage
        r = self.results
        t = self.mode_clock
        rise = (1 - ease_out(t / 0.5)) * -40
        alpha = 255 * ease_out(t / 0.35)
        arcade.draw_rect_filled(arcade.LBWH(0, 0, stage.window_w, stage.window_h),
                                (0, 0, 0, round(150 * ease_out(t / 0.4))))
        left, bottom = RESULT_LEFT, RESULT_BOTTOM + rise
        arcade.draw_texture_rect(self.result_card, stage.rect(
            left - PLANK_PAD, bottom - PLANK_PAD, RESULT_W + 2 * PLANK_PAD,
            RESULT_H + 2 * PLANK_PAD), alpha=round(alpha))
        if t < 0.3:
            return
        top = bottom + RESULT_H
        face = self.res_face
        face_h = 112
        face_w = face_h * face.width / face.height
        wobble = math.sin(self.clock * 3) * 3
        arcade.draw_texture_rect(face, stage.rect(left + 34, top - 22 - face_h + wobble * 0.5,
                                                  face_w, face_h), pixelated=True,
                                 angle=wobble)
        for text in (*self.res_title, self.res_note, *self.res_labels, *self.res_rows):
            text.draw()
        count = ease_out((t - 0.35) / 1.1)
        self.res_wpm.text = str(round(r["wpm"] * count))
        self.res_acc.text = f"{round(r['acc'] * count)}%"
        self.res_wpm.draw()
        self.res_acc.draw()
        self.draw_graph(ease_out((t - 0.5) / 1.4))
        for button in self.result_buttons:
            button.draw()
        if t > 1.5 and not self.stamped:
            self.stamped = True
            audio.play("feast_win")

    def draw_graph(self, reveal):
        stage = self.stage
        gl, gb, gw, gh = GRAPH
        s = stage.scale
        for k in range(5):
            y = gb + gh * k / 4
            arcade.draw_line(*stage.to_screen(gl, y), *stage.to_screen(gl + gw, y),
                             (255, 255, 255, 26 if k else 70), max(1, s))
        for text in self.graph_labels:
            text.draw()
        if not self.history or reveal <= 0:
            return
        span = max(1.0, self.results["time"])
        shown = [h for h in self.history if h[0] <= span * reveal + 1e-6]
        if not shown:
            return

        def point(second, value):
            return stage.to_screen(gl + gw * min(second / span, 1.0),
                                   gb + gh * min(value / self.peak, 1.0))

        raw_points = [point(sec, raw) for sec, _, raw, _ in shown]
        wpm_points = [point(sec, wpm) for sec, wpm, _, _ in shown]
        if len(wpm_points) > 1:
            # Soft fill under the wpm line.
            for a, b in zip(wpm_points, wpm_points[1:]):
                base = stage.to_screen(0, gb)[1]
                arcade.draw_polygon_filled([a, b, (b[0], base), (a[0], base)],
                                           (255, 204, 110, 34))
            arcade.draw_line_strip(raw_points, (168, 175, 190, 150), 2 * s)
            arcade.draw_line_strip(wpm_points, FEAST_CARET, 3 * s)
        for x, y in wpm_points:
            arcade.draw_circle_filled(x, y, 3 * s, FEAST_CARET)
        for sec, _, _, errors in shown:
            if errors:
                x, y = point(sec, min(self.peak, errors * self.peak / 8))
                size = 4 * s
                arcade.draw_line(x - size, y - size, x + size, y + size, FEAST_WRONG, 2 * s)
                arcade.draw_line(x - size, y + size, x + size, y - size, FEAST_WRONG, 2 * s)

    # --- update -------------------------------------------------------------

    def on_show_view(self):
        audio.ambience(AMBIENCE_NIGHT).start()

    def on_hide_view(self):
        for course in self.courses:
            course.stop()
        audio.ambience(AMBIENCE_NIGHT).stop()

    def on_update(self, delta_time):
        audio.ambience(AMBIENCE_NIGHT).update(delta_time)
        self.courses[self.course].update(delta_time)
        fading = self.old_course is not None and self.course_clock < FEAST_STAGE_FADE
        for index, course in enumerate(self.courses):
            if index == self.course:
                continue
            if fading and index == self.old_course:
                course.update(delta_time)
            else:
                course.stop()
        if self.pause_menu.visible or self.settings_panel.visible:
            return
        delta_time = min(delta_time, 1 / 30)
        self.clock += delta_time
        self.mode_clock += delta_time
        self.course_clock += delta_time
        self.bump = max(0.0, self.bump - delta_time * 5)
        self.shake = max(0.0, self.shake - delta_time * 6)
        self.flash = max(0.0, self.flash - delta_time * 2.2)
        self.meter += (self.progress - self.meter) * min(1.0, delta_time * 7)
        self.slide = max(0.0, self.slide - delta_time / FEAST_SLIDE)
        if self.outgoing is not None:
            texts, age, color = self.outgoing
            age += delta_time
            self.outgoing = None if age > FEAST_OUT_TIME else (texts, age, color)
        self.idle += delta_time
        for key in list(self.key_glow):
            left, color = self.key_glow[key]
            left -= delta_time
            if left <= 0:
                del self.key_glow[key]
            else:
                self.key_glow[key] = (left, color)
        self.update_particles(delta_time)
        if self.banner is not None:
            texts, age, content, color = self.banner
            age += delta_time
            self.banner = None if age > 1.8 else (texts, age, content, color)

        if self.mode == "count":
            step = int(self.mode_clock / FEAST_COUNT_STEP)
            if step >= 3:
                # "EAT!" goes up as the clock starts; draw_count fades it out.
                audio.play("feast_go")
                self.start_play()
            elif step != self.count_shown:
                self.count_shown = step
                audio.play("feast_count")
        elif self.mode == "play":
            self.time_left -= delta_time
            self.elapsed += delta_time
            while self.elapsed >= self.next_second:
                self.record_second()
            seconds = math.ceil(self.time_left)
            if 0 < seconds <= FEAST_HURRY and seconds != self.hurry_second:
                self.hurry_second = seconds
                audio.play("feast_tick", speed=1.0 + (FEAST_HURRY - seconds) * 0.03)
            if self.time_left <= 0:
                self.time_left = 0
                self.end_round()
        elif self.mode == "ending" and self.mode_clock >= 1.6:
            self.show_results()

    def update_particles(self, delta_time):
        stage = self.stage
        for group in (self.crumbs, self.sparks):
            for p in list(group):
                p.age += delta_time
                if p.age >= p.life:
                    p.remove_from_sprite_lists()
                    continue
                p.px += p.vx * delta_time
                p.py += p.vy * delta_time
                fade = 1 - p.age / p.life
                if p.spark:
                    p.vx *= 1 - 2.5 * delta_time
                    p.vy = p.vy * (1 - 2.5 * delta_time) - 40 * delta_time
                    size = p.base_size * (0.6 + 0.6 * fade)
                    p.alpha = round(255 * fade)
                    p.angle = 45
                else:
                    p.vy -= 900 * delta_time
                    size = p.base_size
                    p.alpha = round(255 * min(1.0, fade * 2))
                    p.angle = p.age * 400
                p.position = stage.to_screen(p.px, p.py)
                p.width = p.height = max(1.0, size * stage.scale)
            while len(group) > 400:
                group[0].remove_from_sprite_lists()
        for floater in self.floaters:
            floater.age += delta_time
        self.floaters = [f for f in self.floaters if f.age < f.life]

    # --- drawing ------------------------------------------------------------

    def draw_course(self, backdrop, alpha):
        texture = backdrop.texture
        width = WIDTH * (1 + 0.012 * self.bump)
        height = texture.height * width / texture.width
        top = HEIGHT + FEAST_CROP * height * (1 + 0.012 * self.bump) - 6 * self.bump
        left = (WIDTH - width) / 2
        arcade.draw_texture_rect(texture, self.stage.rect(left, top - height, width, height),
                                 alpha=round(alpha))

    def on_draw(self):
        self.clear(color=FEAST_FLOOR)
        stage = self.stage
        fading = self.old_course is not None and self.course_clock < FEAST_STAGE_FADE
        if fading:
            self.draw_course(self.courses[self.old_course], 255)
            self.draw_course(self.courses[self.course],
                             255 * ease_out(self.course_clock / FEAST_STAGE_FADE))
        else:
            self.draw_course(self.courses[self.course], 255)

        # The garden sinks into the dark ground the keyboard sits on.
        arcade.draw_rect_filled(stage.rect(-WIDTH, -HEIGHT, 3 * WIDTH, HEIGHT + FEAST_SCENE_BOTTOM - 40),
                                FEAST_FLOOR)
        arcade.draw_texture_rect(self.floor_fade, stage.rect(
            0, FEAST_SCENE_BOTTOM - 40, WIDTH, 190))
        arcade.draw_texture_rect(self.top_fade, stage.rect(0, HEIGHT - 130, WIDTH, 130),
                                 angle=180, alpha=150)
        if self.flash > 0:
            arcade.draw_rect_filled(stage.rect(0, FEAST_SCENE_BOTTOM, WIDTH, HEIGHT - FEAST_SCENE_BOTTOM),
                                    (255, 246, 220, round(110 * self.flash)))

        self.draw_particles()
        for floater in self.floaters:
            floater.draw(stage)

        if self.mode in ("count", "play", "ending", "results"):
            self.draw_hud()
            self.draw_words()
        self.draw_keyboard()
        self.draw_banner()

        if self.mode == "intro":
            self.draw_intro()
        elif self.mode == "count":
            self.draw_count(self.mode_clock)
        elif self.mode == "play" and self.mode_clock < FEAST_COUNT_STEP:
            self.draw_count(3 * FEAST_COUNT_STEP + self.mode_clock)
        elif self.mode == "results":
            self.draw_results()
            # Sparks from the stamp land over the panel.
            self.draw_particles(sparks_only=True)

        if not self.settings_panel.visible:
            self.pause_menu.draw()
        self.settings_panel.draw()

    def draw_particles(self, sparks_only=False):
        if not sparks_only:
            self.crumbs.draw()
        self.sparks.draw()

    def draw_hud(self):
        stage = self.stage
        seconds = math.ceil(self.time_left)
        wpm = round(self.wpm()) if self.elapsed > 0.5 else 0
        acc = round(self.accuracy())
        eaten = round(100 * self.progress)
        shown = (seconds, wpm, acc, eaten, self.streak)
        if shown != self.shown_hud:
            self.shown_hud = shown
            for text in self.timer_text:
                text.text = str(seconds)
            for text in self.wpm_text:
                text.text = str(wpm)
            self.wpm_note.text = f"wpm   ·   {acc}% acc"
            self.meter_value.text = f"{eaten}%"
            for text in self.streak_text:
                text.text = f"streak  x{self.streak}" if self.streak >= 3 else ""
        hurry = self.mode == "play" and seconds <= FEAST_HURRY
        pulse = 1 + (0.08 * max(0.0, 1 - (math.ceil(self.time_left) - self.time_left) * 4)
                     if hurry else 0)
        plate = self.small_plate_hot if hurry else self.small_plate
        w, h = 170 * pulse, 70 * pulse
        arcade.draw_texture_rect(plate, stage.rect(110 - w / 2 - PLANK_PAD, HEIGHT - 57 - h / 2 - PLANK_PAD,
                                                   w + 2 * PLANK_PAD, h + 2 * PLANK_PAD))
        self.timer_text[1].color = FEAST_WRONG if hurry else TEXT_HOVER
        for text in (*self.timer_text, self.timer_note):
            text.draw()
        arcade.draw_texture_rect(self.wide_plate, stage.rect(WIDTH - 135 - 100 - PLANK_PAD,
                                                             HEIGHT - 92 - PLANK_PAD,
                                                             200 + 2 * PLANK_PAD, 70 + 2 * PLANK_PAD))
        for text in (*self.wpm_text, self.wpm_note):
            text.draw()

        # The food meter, with a notch where each course goes.
        arcade.draw_texture_rect(self.meter_plate, stage.rect(WIDTH / 2 - 210 - PLANK_PAD,
                                                              HEIGHT - 92 - PLANK_PAD,
                                                              420 + 2 * PLANK_PAD, 70 + 2 * PLANK_PAD))
        self.meter_label.draw()
        self.meter_value.draw()
        bar_l, bar_b, bar_w, bar_h = WIDTH / 2 - 190, HEIGHT - 76, 380, 14
        arcade.draw_rect_filled(stage.rect(bar_l, bar_b, bar_w, bar_h), (255, 255, 255, 30))
        fill = self.meter
        color = QUEST_DONE if self.progress >= 1 else FEAST_CARET
        if fill > 0.002:
            arcade.draw_rect_filled(stage.rect(bar_l, bar_b, bar_w * fill, bar_h), color)
            arcade.draw_rect_filled(stage.rect(bar_l, bar_b + bar_h * 0.55, bar_w * fill, bar_h * 0.45),
                                    (255, 255, 255, 50))
            glint = (self.clock * 0.6) % 1.0
            if glint < fill:
                arcade.draw_rect_filled(stage.rect(bar_l + bar_w * glint, bar_b, 6, bar_h),
                                        (255, 255, 255, 70))
        stages = len(FEAST_STAGES) - 1
        for k in range(1, stages):
            x = bar_l + bar_w * k / stages
            arcade.draw_line(*stage.to_screen(x, bar_b - 3), *stage.to_screen(x, bar_b + bar_h + 3),
                             (8, 10, 14, 200), max(1, 2 * stage.scale))

        if self.mode in ("play", "ending"):
            for text in self.streak_text:
                text.draw()
            self.hint_text.draw()

    def draw_words(self):
        if self.dirty:
            self.rebuild_words()
        stage = self.stage
        shake = math.sin(self.clock * 90) * 6 * self.shake
        slide = self.slide ** 2

        # A dark strip behind the word being typed keeps it clear of the food.
        arcade.draw_rect_filled(stage.rect(WIDTH / 2 - 330, FEAST_WORD_Y - 38, 660, 76),
                                (6, 8, 12, 185))
        for x in (WIDTH / 2 - 330, WIDTH / 2 + 330):
            arcade.draw_line(*stage.to_screen(x, FEAST_WORD_Y - 38),
                             *stage.to_screen(x, FEAST_WORD_Y + 38),
                             with_alpha(FEAST_CARET, 140), max(1, 2 * stage.scale))

        # The waiting stack, each word moving up a place as the last one goes.
        for k, text in enumerate(self.queue_texts):
            y, size, alpha = self.queue_slot(k + 1 + slide)
            text.x, text.y = stage.to_screen(WIDTH / 2, y)
            text.color = with_alpha(FEAST_UNTYPED, alpha)
            text.draw()

        # The word being typed, rising into the middle from the first slot.
        # Font sizes stay put: a new size means the glyphs being rasterised
        # all over again, which stalls the frame. Only the position slides.
        y, _, alpha = self.queue_slot(slide)
        size = FEAST_WORD_SIZE
        advance = self.advance
        left = WIDTH / 2 - self.word_cols * advance / 2 + shake
        for column, text, color in self.word_texts:
            text.x, text.y = stage.to_screen(left + column * advance, y)
            text.color = with_alpha(color, alpha)
            text.draw()

        if self.outgoing is not None:
            texts, age, color = self.outgoing
            t = age / FEAST_OUT_TIME
            for text in texts:
                text.x, text.y = stage.to_screen(WIDTH / 2, FEAST_WORD_Y + 70 * ease_out(t))
                text.color = with_alpha(color, 255 * (1 - t))
                text.draw()

        if self.mode not in ("play", "count"):
            return
        target = left + len(self.typed[self.index]) * advance
        if self.caret_x is None:
            self.caret_x = target
        self.caret_x += (target - self.caret_x) * 0.5
        blink = 1.0 if self.idle < 0.6 and self.mode == "play" else (
            0.5 + 0.5 * math.cos(self.clock * 2 * math.pi / 1.05))
        x, cy = stage.to_screen(self.caret_x - 1, y)
        arcade.draw_rect_filled(arcade.XYWH(x, cy, 3 * stage.scale, size * 1.2 * stage.scale),
                                with_alpha(FEAST_CARET, blink * alpha))

    def next_key(self):
        if self.mode != "play":
            return None
        word, typed = self.words[self.index], self.typed[self.index]
        if typed == word:
            return " "
        if len(typed) < len(word) and word[:len(typed)] == typed:
            return word[len(typed)]
        return None

    def draw_keyboard(self):
        stage = self.stage
        hint = self.next_key()
        self.key_shapes.draw()
        lit = set(self.key_glow)
        if hint is not None:
            lit.add(hint)
        for key in self.lit_keys - lit:
            left, bottom, w, h = self.keys[key]
            label = self.key_labels[key]
            label.y = stage.to_screen(0, bottom + h / 2)[1]
            label.color = TEXT_DIM
        self.lit_keys = lit
        for key in lit:
            left, bottom, w, h = self.keys[key]
            glow = self.key_glow.get(key)
            press = 0.0 if glow is None else glow[0] / FEAST_KEY_GLOW
            sink = 2 * press
            rect = stage.rect(left, bottom - sink, w, h)
            arcade.draw_rect_filled(rect, FEAST_KEY_FACE)
            if glow is not None:
                arcade.draw_rect_filled(rect, with_alpha(glow[1], 170 * press))
            arcade.draw_rect_outline(rect, TEXT_HOVER if key == hint else FEAST_KEY_EDGE,
                                     max(1, (2 if key == hint else 1) * stage.scale))
            label = self.key_labels[key]
            label.y = stage.to_screen(0, bottom + h / 2 - sink)[1]
            label.color = TEXT_BRIGHT if glow is not None else TEXT_HOVER
        self.key_batch.draw()

    def draw_banner(self):
        if self.banner is None:
            return
        texts, age = self.banner[0], self.banner[1]
        alpha = 255 * min(1.0, age / 0.12) * (1 - max(0.0, (age - 1.3) / 0.5))
        y = 560 + 18 * (1 - back_out(age / 0.35)) + 12 * max(0.0, age - 1.3)
        for text, offset in zip(texts, (3, 0)):
            text.y = self.stage.to_screen(0, y - offset)[1]
            text.color = with_alpha(text.color, alpha)
            text.draw()

    def draw_intro(self):
        stage = self.stage
        arcade.draw_rect_filled(arcade.LBWH(0, 0, stage.window_w, stage.window_h), (4, 6, 10, 175))
        band = textures.title_band(stage.px(WIDTH), stage.px(360))
        arcade.draw_texture_rect(band, stage.rect(0, HEIGHT / 2 - 160, WIDTH, 360), alpha=200)
        face = self.faces["intro"]
        size = 92
        bob = math.sin(self.clock * 2.6) * 4
        width = size * face.width / face.height
        arcade.draw_texture_rect(face, stage.rect(WIDTH / 2 - 330 - width / 2, HEIGHT / 2 + 30 + bob,
                                                  width, size), pixelated=True)
        for text in self.intro_texts:
            text.draw()
        blink = 0.55 + 0.45 * math.cos(self.clock * 4)
        for text in self.intro_press:
            text.color = with_alpha(text.color, 255 * blink)
            text.draw()

    def draw_count(self, clock):
        """The count in, `clock` seconds along; 3, 2, 1 and then "EAT!"."""
        step = min(3, int(clock / FEAST_COUNT_STEP))
        part = min(1.0, clock / FEAST_COUNT_STEP - step)
        label = ("3", "2", "1", "EAT!")[step]
        stage = self.stage
        arcade.draw_rect_filled(arcade.LBWH(0, 0, stage.window_w, stage.window_h),
                                (4, 6, 10, round(120 * (1 - (step == 3) * part))))
        alpha = 255 * min(1.0, part / 0.12) * (1 - max(0.0, (part - 0.7) / 0.3))
        for text, offset in zip(self.count_texts[label], (5, 0)):
            text.color = with_alpha(text.color, alpha)
            text.y = stage.to_screen(0, HEIGHT / 2 + 40 - offset + 30 * (1 - back_out(part / 0.3)))[1]
            text.draw()
        # A ring punches out from behind each number.
        x, y = stage.to_screen(WIDTH / 2, HEIGHT / 2 + 40)
        radius = (60 + 200 * ease_out(part)) * stage.scale
        arcade.draw_circle_outline(x, y, radius, with_alpha(FEAST_CARET, 180 * (1 - part)),
                                   4 * stage.scale)
