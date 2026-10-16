"""Overlays for the Chao dinner: title card, prompt, quests and portraits.

Each one follows the widget pattern used across the game: `layout(stage)`
builds textures and text at the window's real pixel size, `draw()` puts them
on screen. Positions are canvas units throughout.
"""

import math

import arcade

from . import textures
from .config import (
    CHAO_KEYCAP_H, CHAO_KEYCAP_W, CHAO_KICKER_SIZE, CHAO_PROMPT_BOB,
    CHAO_PROMPT_GAP, CHAO_PROMPT_H, CHAO_PROMPT_KEY, CHAO_PROMPT_KEY_SIZE,
    CHAO_PROMPT_LABEL, CHAO_PROMPT_PAD, CHAO_PROMPT_POINTER, CHAO_PROMPT_SIZE,
    CHAO_QUEST_HEADER, CHAO_QUEST_HEADER_SIZE, CHAO_QUEST_NOTE_SIZE,
    CHAO_QUEST_MARKER, CHAO_QUEST_RIGHT, CHAO_QUEST_ROW_GAP,
    CHAO_QUEST_TITLE_SIZE, CHAO_QUEST_TOP, CHAO_QUESTS, CHAO_TAGLINE_SIZE,
    CHAO_TITLE, CHAO_TITLE_BAND_H, CHAO_TITLE_DELAY, CHAO_TITLE_FADE,
    CHAO_TITLE_HOLD, CHAO_TITLE_KICKER, CHAO_TITLE_RISE, CHAO_TITLE_RULE,
    CHAO_TITLE_SIZE, CHAO_TITLE_TAGLINE, CHAO_TITLE_Y, GLASS_EDGE_HOVER,
    DIALOG_BOTTOM, DIALOG_H, KEYCAP_TEXT, KIDS_HINT, KIDS_HUD_H,
    KIDS_HUD_NOTE_SIZE, KIDS_HUD_TOP, KIDS_HUD_W, KIDS_TIMER_SIZE, PLANK_PAD, PORTRAIT_DIM, PORTRAIT_H,
    PORTRAIT_INSET, PORTRAIT_SINK, PORTRAIT_SPEAKING_GROW, QUEST_DONE,
    TEXT_BRIGHT, TEXT_DIM, TEXT_HOVER, TEXT_SHADOW, WIDTH,
)


def with_alpha(color, alpha):
    return (*color[:3], round(alpha))


def place(stage, text, x, y):
    """Move an arcade.Text to canvas point (x, y)."""
    text.x, text.y = stage.to_screen(x, y)


class TitleCard:
    """The scene title, drifting up out of a blur while Terry walks in."""

    def __init__(self, kicker=None, title=None, tagline=None):
        self.clock = 0.0
        self.stage = None
        # Default to Chao dinner constants if no custom strings are provided
        self.kicker_text = kicker if kicker is not None else CHAO_TITLE_KICKER
        self.title_text = title if title is not None else CHAO_TITLE
        self.tagline_text = tagline if tagline is not None else CHAO_TITLE_TAGLINE

    @property
    def length(self):
        return CHAO_TITLE_DELAY + 2 * CHAO_TITLE_FADE + CHAO_TITLE_HOLD

    @property
    def finished(self):
        return self.clock >= self.length

    def skip(self):
        self.clock = self.length

    def update(self, delta_time):
        self.clock += delta_time

    @property
    def share(self):
        """0 to 1: how far up the card is, including the blur behind it."""
        clock = self.clock - CHAO_TITLE_DELAY
        if clock <= 0 or self.finished:
            return 0.0
        if clock < CHAO_TITLE_FADE:
            return self.ease(clock / CHAO_TITLE_FADE)
        if clock < CHAO_TITLE_FADE + CHAO_TITLE_HOLD:
            return 1.0
        left = 2 * CHAO_TITLE_FADE + CHAO_TITLE_HOLD - clock
        return self.ease(left / CHAO_TITLE_FADE)

    @staticmethod
    def ease(t):
        t = max(0.0, min(1.0, t))
        return t * t * (3 - 2 * t)

    @property
    def rise(self):
        """Canvas units the words sit above their resting line."""
        clock = self.clock - CHAO_TITLE_DELAY
        if clock < CHAO_TITLE_FADE + CHAO_TITLE_HOLD:
            # Fading in: start low and drift up into place.
            return -(1 - self.share) * CHAO_TITLE_RISE
        # Fading out: carry on upwards and away.
        return (1 - self.share) * CHAO_TITLE_RISE

    def layout(self, stage):
        self.stage = stage
        self.band = textures.title_band(
            stage.px(WIDTH), stage.px(CHAO_TITLE_BAND_H)
        )
        center = dict(anchor_x="center", anchor_y="center")

        # Use the stored text strings rather than the hardcoded constants
        self.kicker = stage.text(
            self.kicker_text, 0, 0, TEXT_HOVER, CHAO_KICKER_SIZE,
            bold=True, **center,
        )
        self.title_shadow = stage.text(
            self.title_text, 0, 0, TEXT_SHADOW, CHAO_TITLE_SIZE, bold=True, **center,
        )
        self.title = stage.text(
            self.title_text, 0, 0, TEXT_BRIGHT, CHAO_TITLE_SIZE, bold=True, **center,
        )
        self.tagline = stage.text(
            self.tagline_text, 0, 0, TEXT_DIM, CHAO_TAGLINE_SIZE,
            italic=True, **center,
        )
        self.kicker_half = self.kicker.content_width / stage.scale / 2

    def draw(self):
        share = self.share
        if share <= 0:
            return
        stage = self.stage
        alpha = 255 * share
        arcade.draw_texture_rect(
            self.band,
            stage.rect(0, CHAO_TITLE_Y - CHAO_TITLE_BAND_H / 2,
                       WIDTH, CHAO_TITLE_BAND_H),
            alpha=round(alpha),
        )

        mid_x, y = WIDTH / 2, CHAO_TITLE_Y + self.rise
        kicker_y = y + 62
        place(stage, self.kicker, mid_x, kicker_y)
        place(stage, self.title_shadow, mid_x + 3, y - 4)
        place(stage, self.title, mid_x, y)
        place(stage, self.tagline, mid_x, y - 58)

        # Hairlines either side of the kicker, each ending in a small diamond.
        rule = with_alpha(TEXT_HOVER, alpha * 0.8)
        gap = self.kicker_half + 22
        for side in (-1, 1):
            inner = mid_x + side * gap
            outer = mid_x + side * (gap + CHAO_TITLE_RULE)
            arcade.draw_line(
                *stage.to_screen(inner, kicker_y), *stage.to_screen(outer, kicker_y),
                rule, max(1, stage.scale * 1.5),
            )
            self.diamond(inner, kicker_y, 4, rule)

        self.kicker.color = with_alpha(TEXT_HOVER, alpha)
        self.title_shadow.color = with_alpha(TEXT_SHADOW, alpha * 0.7)
        self.title.color = with_alpha(TEXT_BRIGHT, alpha)
        self.tagline.color = with_alpha(TEXT_DIM, alpha)
        for text in (self.kicker, self.title_shadow, self.title, self.tagline):
            text.draw()

    def diamond(self, x, y, size, color):
        stage = self.stage
        arcade.draw_polygon_filled([
            stage.to_screen(x, y + size), stage.to_screen(x + size, y),
            stage.to_screen(x, y - size), stage.to_screen(x - size, y),
        ], color)


class InteractPrompt:
    """A floating "Interact [Enter]" tag with a pointer down at its target."""

    def __init__(self, label=CHAO_PROMPT_LABEL):
        self.label_text = label
        self.stage = None
        self.clock = 0.0

    def update(self, delta_time):
        self.clock += delta_time

    def layout(self, stage):
        self.stage = stage
        center_y = dict(anchor_y="center")
        self.label_shadow = stage.text(
            self.label_text, 0, 0, TEXT_SHADOW, CHAO_PROMPT_SIZE,
            bold=True, **center_y,
        )
        self.label = stage.text(
            self.label_text, 0, 0, TEXT_BRIGHT, CHAO_PROMPT_SIZE,
            bold=True, **center_y,
        )
        self.key = stage.text(
            CHAO_PROMPT_KEY, 0, 0, KEYCAP_TEXT, CHAO_PROMPT_KEY_SIZE,
            bold=True, anchor_x="center", anchor_y="center",
        )
        self.label_w = self.label.content_width / stage.scale
        self.width = (
            CHAO_PROMPT_PAD + self.label_w + CHAO_PROMPT_PAD
            + CHAO_KEYCAP_W + CHAO_PROMPT_PAD * 0.7
        )
        pad = stage.px(PLANK_PAD)
        self.plank = textures.plank(
            stage.px(self.width), stage.px(CHAO_PROMPT_H), pad, True,
        )
        self.keycap = textures.keycap(
            stage.px(CHAO_KEYCAP_W), stage.px(CHAO_KEYCAP_H), stage.px(2),
        )

    def box(self, tip_x, tip_y):
        """(left, bottom, width, height) of the plank for a pointer at tip."""
        bob = math.sin(self.clock * 4) * CHAO_PROMPT_BOB
        bottom = tip_y + CHAO_PROMPT_GAP + CHAO_PROMPT_POINTER + bob
        return tip_x - self.width / 2, bottom, self.width, CHAO_PROMPT_H

    def contains(self, tip_x, tip_y, x, y):
        left, bottom, width, height = self.box(tip_x, tip_y)
        return left <= x <= left + width and bottom <= y <= bottom + height

    def draw(self, tip_x, tip_y):
        stage = self.stage
        left, bottom, width, height = self.box(tip_x, tip_y)
        arcade.draw_texture_rect(self.plank, stage.rect(
            left - PLANK_PAD, bottom - PLANK_PAD,
            width + 2 * PLANK_PAD, height + 2 * PLANK_PAD,
        ))
        # The pointer hangs off the bottom edge, in the plank's hover gold.
        tip = bottom - CHAO_PROMPT_POINTER
        arcade.draw_polygon_filled([
            stage.to_screen(tip_x - CHAO_PROMPT_POINTER, bottom - 1),
            stage.to_screen(tip_x + CHAO_PROMPT_POINTER, bottom - 1),
            stage.to_screen(tip_x, tip),
        ], GLASS_EDGE_HOVER)

        middle_y = bottom + height / 2
        text_x = left + CHAO_PROMPT_PAD
        place(stage, self.label_shadow, text_x, middle_y - 2)
        place(stage, self.label, text_x, middle_y)
        self.label_shadow.draw()
        self.label.draw()

        key_x = text_x + self.label_w + CHAO_PROMPT_PAD
        arcade.draw_texture_rect(self.keycap, stage.rect(
            key_x - 2, middle_y - CHAO_KEYCAP_H / 2 - 2,
            CHAO_KEYCAP_W + 4, CHAO_KEYCAP_H + 4,
        ))
        # The key face sits above its lip, so its label does too.
        place(stage, self.key, key_x + CHAO_KEYCAP_W / 2, middle_y + 2)
        self.key.draw()


class QuestPanel:
    """The quest list in the top right: bare, right-aligned text on the scene.

    There is no panel behind it, so every line carries a drop shadow to stay
    legible over the garden.
    """

    SHADOW = (0, 0, 0, 210)

    def __init__(self, quests=None):
        self.stage = None
        # Use custom quests if provided; otherwise fallback to CHAO_QUESTS for teammate compatibility
        self.quest_defs = quests if quests is not None else CHAO_QUESTS
        self.done = {key: False for key, *_ in self.quest_defs}
        self.progress = {}   # key -> text shown after the note, like "1/4"

    def complete(self, key):
        self.done[key] = True
        self.refresh()

    def set_progress(self, key, text):
        self.progress[key] = text
        self.refresh()

    def shadowed(self, content, y, color, size, bold=False, italic=False):
        """A right-aligned line and its shadow, as [shadow, text]."""
        right = CHAO_QUEST_RIGHT - 3 * CHAO_QUEST_MARKER
        return [
            self.stage.text(
                content, right + offset, y - offset, shade, size,
                anchor_x="right", anchor_y="center", bold=bold, italic=italic,
            )
            for offset, shade in ((1.5, self.SHADOW), (0, color))
        ]

    def layout(self, stage):
        self.stage = stage
        top = CHAO_QUEST_TOP
        self.header = [
            stage.text(
                CHAO_QUEST_HEADER, CHAO_QUEST_RIGHT + offset, top - offset,
                shade, CHAO_QUEST_HEADER_SIZE, anchor_x="right",
                anchor_y="center", bold=True,
            )
            for offset, shade in ((1.5, self.SHADOW), (0, TEXT_HOVER))
        ]
        self.rule_y = top - 12
        self.rows = []
        row_top = top - 30
        for key, title, note, optional in self.quest_defs:
            self.rows.append({
                "key": key,
                "marker": (CHAO_QUEST_RIGHT - CHAO_QUEST_MARKER, row_top),
                "title": self.shadowed(
                    title, row_top, TEXT_BRIGHT, CHAO_QUEST_TITLE_SIZE, bold=True,
                ),
                "note": self.shadowed(
                    note, row_top - 18, TEXT_DIM, CHAO_QUEST_NOTE_SIZE,
                    italic=optional,
                ),
                "base_note": ("Optional: " if optional else "") + note,
            })
            row_top -= CHAO_QUEST_ROW_GAP
        self.refresh()

    def refresh(self):
        if self.stage is None:
            return
        for row in self.rows:
            key = row["key"]
            done = self.done[key]
            progress = self.progress.get(key)
            note = row["base_note"] + (f"  ({progress})" if progress else "")
            for text in row["note"]:
                text.text = "Done" if done else note
            row["note"][1].color = QUEST_DONE if done else TEXT_DIM
            row["title"][1].color = TEXT_DIM if done else TEXT_BRIGHT

    def draw(self):
        stage = self.stage
        for text in self.header:
            text.draw()
        rule_left = CHAO_QUEST_RIGHT - 70
        for offset, color in ((1.5, self.SHADOW), (0, with_alpha(TEXT_HOVER, 150))):
            arcade.draw_line(
                *stage.to_screen(rule_left + offset, self.rule_y - offset),
                *stage.to_screen(CHAO_QUEST_RIGHT + offset, self.rule_y - offset),
                color, max(1, stage.scale),
            )
        s = stage.scale
        for row in self.rows:
            x, y = stage.to_screen(*row["marker"])
            radius = CHAO_QUEST_MARKER * s
            arcade.draw_circle_filled(x + 1.5 * s, y - 1.5 * s, radius + s, self.SHADOW)
            if self.done[row["key"]]:
                arcade.draw_circle_filled(x, y, radius + 0.5 * s, QUEST_DONE)
                arcade.draw_line_strip(
                    [(x - 2.6 * s, y), (x - 0.6 * s, y - 2 * s), (x + 2.8 * s, y + 2.2 * s)],
                    TEXT_SHADOW, 1.6 * s,
                )
            else:
                arcade.draw_circle_outline(x, y, radius, TEXT_HOVER, 1.6 * s)
            for text in (*row["title"], *row["note"]):
                text.draw()


class Portraits:
    """Terry standing on the left of the dialogue box, his partner on the right.

    Whoever is speaking is drawn full colour and a touch larger; the other
    is dimmed. Draw this before the dialogue box, which covers their feet.
    """

    def __init__(self, terry):
        self.terry = terry
        self.stage = None

    def layout(self, stage):
        self.stage = stage

    def draw(self, partner, speaking):
        """`partner` is a texture or None; `speaking` is "left" or "right"."""
        bottom = DIALOG_BOTTOM + DIALOG_H - PORTRAIT_SINK
        sides = [("left", self.terry)]
        if partner is not None:
            sides.append(("right", partner))
        for side, texture in sides:
            talking = side == speaking
            height = PORTRAIT_H * (PORTRAIT_SPEAKING_GROW if talking else 1)
            width = height * texture.width / texture.height
            if side == "left":
                left = PORTRAIT_INSET
            else:
                left = WIDTH - PORTRAIT_INSET - width
            arcade.draw_texture_rect(
                texture, self.stage.rect(left, bottom, width, height),
                color=arcade.color.WHITE if talking else arcade.types.Color(*PORTRAIT_DIM),
                pixelated=True,
            )

class KidsHud:
    """The mini game's clock and seat count, on a plank at the top middle,
    with the how-to line along the bottom of the screen."""

    def __init__(self):
        self.stage = None
        self.shown = None   # (seconds, seated, total) last written to the text

    def layout(self, stage):
        self.stage = stage
        self.shown = None
        pad = stage.px(PLANK_PAD)
        self.plank = textures.plank(
            stage.px(KIDS_HUD_W), stage.px(KIDS_HUD_H), pad, False,
        )
        self.plank_hurry = textures.plank(
            stage.px(KIDS_HUD_W), stage.px(KIDS_HUD_H), pad, True,
        )
        middle = WIDTH / 2
        center = dict(anchor_x="center", anchor_y="center")
        top = KIDS_HUD_TOP
        self.timer = [
            stage.text("", middle + offset, top - 28 - offset, shade,
                       KIDS_TIMER_SIZE, bold=True, **center)
            for offset, shade in ((2, TEXT_SHADOW), (0, TEXT_BRIGHT))
        ]
        self.note = stage.text("", middle, top - 58, TEXT_DIM,
                               KIDS_HUD_NOTE_SIZE, **center)
        self.hint = [
            stage.text(KIDS_HINT, middle + offset, 26 - offset, shade, 14,
                       bold=True, **center)
            for offset, shade in ((1.5, TEXT_SHADOW), (0, TEXT_HOVER))
        ]

    def draw(self, time_left, seated, total):
        stage = self.stage
        seconds = math.ceil(time_left)
        if self.shown != (seconds, seated, total):
            self.shown = (seconds, seated, total)
            clock = f"{seconds // 60}:{seconds % 60:02d}"
            for text in self.timer:
                text.text = clock
            self.note.text = f"Kids in their seats: {seated}/{total}"
        hurry = seconds <= 10
        arcade.draw_texture_rect(
            self.plank_hurry if hurry else self.plank,
            stage.rect(WIDTH / 2 - KIDS_HUD_W / 2 - PLANK_PAD,
                       KIDS_HUD_TOP - KIDS_HUD_H - PLANK_PAD,
                       KIDS_HUD_W + 2 * PLANK_PAD, KIDS_HUD_H + 2 * PLANK_PAD),
        )
        self.timer[1].color = TEXT_HOVER if hurry else TEXT_BRIGHT
        for text in (*self.timer, self.note, *self.hint):
            text.draw()
