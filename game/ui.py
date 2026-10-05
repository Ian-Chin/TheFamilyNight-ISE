"""Menu widgets.

Positions are declared in canvas units (1280x720) and laid out into real
window pixels by a Stage. Textures and fonts are then built at that pixel
size, so nothing is drawn small and scaled up.
"""

import arcade

from . import audio, textures
from .config import (
    CREDIT_SIZE, HEIGHT, MENU_BUTTON_H, MENU_BUTTON_W, MENU_FONT, MENU_ICON,
    MENU_ICON_GAP, MENU_ICON_PAD, MENU_TEXT_SIZE, PLANK_PAD, SETTINGS_LABEL_SIZE,
    SETTINGS_CHOICE_H, SETTINGS_CHOICE_SIZE, SETTINGS_NOTE_SIZE,
    SETTINGS_VALUE_SIZE, SLIDER_FILL, SLIDER_FILL_DIM,
    SLIDER_KNOB, SLIDER_KNOB_COLOR, SLIDER_KNOB_EDGE, SLIDER_TRACK,
    SLIDER_TRACK_H, SLIDER_W, TEXT_BRIGHT, TEXT_DIM, TEXT_HOVER, TEXT_SHADOW,
    WIDTH,
)

HOVER_GROW = 5  # canvas units a widget grows by under the pointer


class Hoverable:
    """Shared hover state that ticks the pointer sound as it is entered.

    `hovered` is assigned wholesale by the views every time the mouse moves,
    so the sound hangs off the change rather than off the assignment.
    """

    _hovered = False

    @property
    def hovered(self):
        return self._hovered

    @hovered.setter
    def hovered(self, value):
        value = bool(value)
        if value and not self._hovered:
            audio.play("ui_hover")
        self._hovered = value

# The baked icons are white silhouettes, tinted at draw time.
ICON_TINT = arcade.types.Color(*TEXT_BRIGHT)
ICON_TINT_HOVER = arcade.types.Color(*TEXT_HOVER)


class Stage:
    """Maps the fixed canvas onto the window, keeping its aspect ratio."""

    def __init__(self, window_w, window_h):
        self.resize(window_w, window_h)

    def resize(self, window_w, window_h):
        self.window_w = window_w
        self.window_h = window_h
        self.scale = min(window_w / WIDTH, window_h / HEIGHT)
        self.width = WIDTH * self.scale
        self.height = HEIGHT * self.scale
        self.left = (window_w - self.width) / 2
        self.bottom = (window_h - self.height) / 2

    def to_screen(self, x, y):
        return self.left + x * self.scale, self.bottom + y * self.scale

    def to_canvas(self, x, y):
        return (x - self.left) / self.scale, (y - self.bottom) / self.scale

    def px(self, value):
        """Canvas units to whole device pixels, for texture sizes."""
        return max(1, round(value * self.scale))

    def rect(self, left, bottom, width, height):
        screen_left, screen_bottom = self.to_screen(left, bottom)
        return arcade.LBWH(
            screen_left, screen_bottom, width * self.scale, height * self.scale
        )

    def viewport(self):
        return arcade.LBWH(self.left, self.bottom, self.width, self.height)

    def text(self, content, x, y, color, size, **kwargs):
        screen_x, screen_y = self.to_screen(x, y)
        return arcade.Text(
            content, screen_x, screen_y, color, size * self.scale,
            font_name=MENU_FONT, **kwargs,
        )


class MenuButton(Hoverable):
    """A glass button with an icon on the left of its label."""

    def __init__(self, label, action, icon, left, bottom,
                 width=MENU_BUTTON_W, height=MENU_BUTTON_H):
        self.label = label
        self.action = action
        self.icon_name = icon
        self.left = left
        self.bottom = bottom
        self.width = width
        self.height = height
        self.right = left + width
        self.top = bottom + height
        self.hovered = False

    def contains(self, x, y):
        return self.left <= x <= self.right and self.bottom <= y <= self.top

    def layout(self, stage):
        self.stage = stage
        pad = stage.px(PLANK_PAD)
        width, height = stage.px(self.width), stage.px(self.height)
        self.plank = textures.plank(width, height, pad, False)
        self.plank_hovered = textures.plank(width, height, pad, True)
        self.icon = textures.icon(self.icon_name, stage.px(MENU_ICON))

        middle_y = self.bottom + self.height / 2
        self.icon_left = self.left + MENU_ICON_PAD
        self.icon_bottom = middle_y - MENU_ICON / 2
        text_x = self.left + MENU_ICON_PAD + MENU_ICON + MENU_ICON_GAP
        self.shadow_text = stage.text(
            self.label, text_x, middle_y - 2, TEXT_SHADOW, MENU_TEXT_SIZE,
            anchor_y="center", bold=True,
        )
        self.text = stage.text(
            self.label, text_x, middle_y, TEXT_BRIGHT, MENU_TEXT_SIZE,
            anchor_y="center", bold=True,
        )

    def draw(self):
        grow = HOVER_GROW if self.hovered else 0
        tint = ICON_TINT_HOVER if self.hovered else ICON_TINT
        arcade.draw_texture_rect(
            self.plank_hovered if self.hovered else self.plank,
            self.stage.rect(
                self.left - PLANK_PAD - grow,
                self.bottom - PLANK_PAD - grow / 2,
                self.width + 2 * PLANK_PAD + 2 * grow,
                self.height + 2 * PLANK_PAD + grow,
            ),
        )
        arcade.draw_texture_rect(
            self.icon,
            self.stage.rect(self.icon_left, self.icon_bottom, MENU_ICON, MENU_ICON),
            color=tint,
        )
        self.text.color = tint
        self.shadow_text.draw()
        self.text.draw()


class CreditsButton(Hoverable):
    """A round medallion button."""

    def __init__(self, icon, center_x, center_y):
        self.icon_name = icon
        self.center_x = center_x
        self.center_y = center_y
        self.radius = CREDIT_SIZE / 2
        self.hovered = False

    def contains(self, x, y):
        return (x - self.center_x) ** 2 + (y - self.center_y) ** 2 <= self.radius ** 2

    def layout(self, stage):
        self.stage = stage
        pad = stage.px(PLANK_PAD)
        diameter = stage.px(CREDIT_SIZE)
        self.disc = textures.disc(diameter, pad, False)
        self.disc_hovered = textures.disc(diameter, pad, True)
        self.icon_size = CREDIT_SIZE * 0.5
        self.icon = textures.icon(self.icon_name, stage.px(self.icon_size))

    def draw(self):
        grow = HOVER_GROW if self.hovered else 0
        size = CREDIT_SIZE + 2 * PLANK_PAD + 2 * grow
        arcade.draw_texture_rect(
            self.disc_hovered if self.hovered else self.disc,
            self.stage.rect(
                self.center_x - size / 2, self.center_y - size / 2, size, size,
            ),
        )
        icon_size = self.icon_size + grow
        arcade.draw_texture_rect(
            self.icon,
            self.stage.rect(
                self.center_x - icon_size / 2, self.center_y - icon_size / 2,
                icon_size, icon_size,
            ),
            color=ICON_TINT_HOVER if self.hovered else ICON_TINT,
        )


class Slider:
    """A labelled 0..1 bar, dragged with the mouse or nudged with the arrows.

    The value lives in the mixer, not in the slider: the widget reads it every
    frame, so a change made here is heard on the next sound played.
    """

    GRAB_PAD = 14   # canvas units either side of the track that still count

    def __init__(self, channel, label, note, left, middle_y, mixer):
        self.channel = channel
        self.label = label
        self.note = note
        self.left = left
        self.middle_y = middle_y
        self.mixer = mixer
        self.selected = False
        self.dragging = False

    @property
    def value(self):
        return self.mixer.get(self.channel)

    def contains(self, x, y):
        return (
            self.left - self.GRAB_PAD <= x <= self.left + SLIDER_W + self.GRAB_PAD
            and abs(y - self.middle_y) <= SLIDER_KNOB
        )

    def set_from_x(self, x):
        self.mixer.set(self.channel, (x - self.left) / SLIDER_W)

    def nudge(self, delta):
        self.mixer.nudge(self.channel, delta)

    def layout(self, stage):
        self.stage = stage
        self.label_text = stage.text(
            self.label, self.left - 30, self.middle_y + 11, TEXT_BRIGHT,
            SETTINGS_LABEL_SIZE, anchor_x="right", anchor_y="center", bold=True,
        )
        self.note_text = stage.text(
            self.note, self.left - 30, self.middle_y - 16, TEXT_DIM,
            SETTINGS_NOTE_SIZE, anchor_x="right", anchor_y="center",
        )
        self.value_text = stage.text(
            "", self.left + SLIDER_W + 26, self.middle_y, TEXT_BRIGHT,
            SETTINGS_VALUE_SIZE, anchor_y="center",
        )

    def draw(self):
        self.label_text.color = TEXT_HOVER if self.selected else TEXT_BRIGHT
        self.label_text.draw()
        self.note_text.draw()

        half = SLIDER_TRACK_H / 2
        arcade.draw_rect_filled(
            self.stage.rect(
                self.left, self.middle_y - half, SLIDER_W, SLIDER_TRACK_H,
            ),
            SLIDER_TRACK,
        )
        filled = SLIDER_W * self.value
        if filled > 0:
            arcade.draw_rect_filled(
                self.stage.rect(
                    self.left, self.middle_y - half, filled, SLIDER_TRACK_H,
                ),
                SLIDER_FILL if self.selected else SLIDER_FILL_DIM,
            )

        knob_x, knob_y = self.stage.to_screen(self.left + filled, self.middle_y)
        radius = self.stage.px(SLIDER_KNOB) / 2
        arcade.draw_circle_filled(knob_x, knob_y, radius, SLIDER_KNOB_COLOR)
        arcade.draw_circle_outline(
            knob_x, knob_y, radius, SLIDER_KNOB_EDGE, max(1, radius * 0.16),
        )

        self.value_text.text = f"{round(self.value * 100)}%"
        self.value_text.draw()


class Choice:
    """A labelled pick of one option out of a few, laid out like a Slider.

    Click a segment or step along with the arrows. The value lives in
    `setting` (anything with a `mode` and a `set(mode)`), read every frame.
    """

    def __init__(self, label, note, options, left, middle_y, setting):
        self.label = label
        self.note = note
        self.options = options   # (value, caption) pairs, left to right
        self.left = left
        self.middle_y = middle_y
        self.setting = setting
        self.selected = False
        self.dragging = False
        self.segment_w = SLIDER_W / len(options)

    @property
    def index(self):
        values = [value for value, _ in self.options]
        return values.index(self.setting.mode)

    def contains(self, x, y):
        return (
            self.left <= x <= self.left + SLIDER_W
            and abs(y - self.middle_y) <= SETTINGS_CHOICE_H / 2
        )

    def pick(self, index):
        index = min(len(self.options) - 1, max(0, index))
        self.setting.set(self.options[index][0])

    def set_from_x(self, x):
        self.pick(int((x - self.left) // self.segment_w))

    def nudge(self, delta):
        self.pick(self.index + (1 if delta > 0 else -1))

    def layout(self, stage):
        self.stage = stage
        self.label_text = stage.text(
            self.label, self.left - 30, self.middle_y + 11, TEXT_BRIGHT,
            SETTINGS_LABEL_SIZE, anchor_x="right", anchor_y="center", bold=True,
        )
        self.note_text = stage.text(
            self.note, self.left - 30, self.middle_y - 16, TEXT_DIM,
            SETTINGS_NOTE_SIZE, anchor_x="right", anchor_y="center",
        )
        self.option_texts = [
            stage.text(
                caption, self.left + (i + 0.5) * self.segment_w, self.middle_y,
                TEXT_DIM, SETTINGS_CHOICE_SIZE,
                anchor_x="center", anchor_y="center", bold=True,
            )
            for i, (_, caption) in enumerate(self.options)
        ]

    def draw(self):
        self.label_text.color = TEXT_HOVER if self.selected else TEXT_BRIGHT
        self.label_text.draw()
        self.note_text.draw()

        bottom = self.middle_y - SETTINGS_CHOICE_H / 2
        arcade.draw_rect_filled(
            self.stage.rect(self.left, bottom, SLIDER_W, SETTINGS_CHOICE_H),
            SLIDER_TRACK,
        )
        current = self.index
        for i, text in enumerate(self.option_texts):
            if i == current:
                arcade.draw_rect_filled(
                    self.stage.rect(
                        self.left + i * self.segment_w, bottom,
                        self.segment_w, SETTINGS_CHOICE_H,
                    ),
                    SLIDER_FILL if self.selected else SLIDER_FILL_DIM,
                )
                text.color = TEXT_SHADOW
            else:
                text.color = TEXT_DIM
            text.draw()


class Card:
    """A centred parchment popup with a title and a few rows of text.

    Rows are plain strings, drawn centred, or (left, right) pairs, drawn as
    two aligned columns.
    """

    TITLE_SIZE = 27
    ROW_SIZE = 19
    ROW_GAP = 40

    def __init__(self, width, height, title, rows):
        self.width = width
        self.height = height
        self.title = title
        self.rows = rows
        self.left = (WIDTH - width) / 2
        self.bottom = (HEIGHT - height) / 2

    def set_title(self, title):
        if title != self.title:
            self.title = title
            self.title_text.text = title

    def layout(self, stage):
        self.stage = stage
        self.texture = textures.card(
            stage.px(self.width), stage.px(self.height), stage.px(PLANK_PAD)
        )

        middle = self.left + self.width / 2
        self.title_text = stage.text(
            self.title, middle, self.bottom + self.height - 54, TEXT_HOVER,
            self.TITLE_SIZE, anchor_x="center", anchor_y="center", bold=True,
        )

        self.row_texts = []
        top_row = self.bottom + self.height - 112
        for index, row in enumerate(self.rows):
            y = top_row - index * self.ROW_GAP
            if isinstance(row, tuple):
                left_column, right_column = row
                self.row_texts.append(stage.text(
                    left_column, self.left + 64, y, TEXT_DIM, self.ROW_SIZE,
                    anchor_y="center",
                ))
                self.row_texts.append(stage.text(
                    right_column, self.left + 196, y, TEXT_BRIGHT, self.ROW_SIZE,
                    anchor_y="center",
                ))
            else:
                self.row_texts.append(stage.text(
                    row, middle, y, TEXT_BRIGHT, self.ROW_SIZE,
                    anchor_x="center", anchor_y="center",
                ))

        self.hint_text = stage.text(
            "Press Esc or click to close", middle, self.bottom + 28,
            TEXT_DIM, 13, anchor_x="center", anchor_y="center",
        )

    def draw(self):
        arcade.draw_texture_rect(self.texture, self.stage.rect(
            self.left - PLANK_PAD, self.bottom - PLANK_PAD,
            self.width + 2 * PLANK_PAD, self.height + 2 * PLANK_PAD,
        ))
        self.title_text.draw()
        for text in self.row_texts:
            text.draw()
        self.hint_text.draw()
