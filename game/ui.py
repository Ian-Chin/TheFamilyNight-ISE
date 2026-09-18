"""Menu widgets.

Positions are declared in canvas units (1280x720) and laid out into real
window pixels by a Stage. Textures and fonts are then built at that pixel
size, so nothing is drawn small and scaled up.
"""

import arcade

from . import textures
from .config import (
    CARVED, CARVED_HOVER, CREDIT_SIZE, HEIGHT, INK, MENU_BUTTON_H, MENU_BUTTON_W,
    MENU_FONT, MENU_ICON, MENU_ICON_GAP, MENU_ICON_PAD, MENU_TEXT_SIZE,
    PLANK_EDGE, PLANK_PAD, WIDTH,
)

HOVER_GROW = 5  # canvas units a widget grows by under the pointer

# The baked icons are white silhouettes, tinted at draw time.
ICON_TINT = arcade.types.Color(*CARVED)
ICON_TINT_HOVER = arcade.types.Color(*CARVED_HOVER)


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


class MenuButton:
    """A wooden plank with an icon on the left of its label."""

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
            self.label, text_x, middle_y - 2, PLANK_EDGE[:3], MENU_TEXT_SIZE,
            anchor_y="center", bold=True,
        )
        self.text = stage.text(
            self.label, text_x, middle_y, CARVED, MENU_TEXT_SIZE,
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


class CreditsButton:
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
            self.title, middle, self.bottom + self.height - 54, PLANK_EDGE[:3],
            self.TITLE_SIZE, anchor_x="center", anchor_y="center", bold=True,
        )

        self.row_texts = []
        top_row = self.bottom + self.height - 112
        for index, row in enumerate(self.rows):
            y = top_row - index * self.ROW_GAP
            if isinstance(row, tuple):
                left_column, right_column = row
                self.row_texts.append(stage.text(
                    left_column, self.left + 64, y, (120, 96, 64), self.ROW_SIZE,
                    anchor_y="center",
                ))
                self.row_texts.append(stage.text(
                    right_column, self.left + 196, y, INK, self.ROW_SIZE,
                    anchor_y="center",
                ))
            else:
                self.row_texts.append(stage.text(
                    row, middle, y, INK, self.ROW_SIZE,
                    anchor_x="center", anchor_y="center",
                ))

        self.hint_text = stage.text(
            "Press Esc or click to close", middle, self.bottom + 28,
            (140, 120, 92), 13, anchor_x="center", anchor_y="center",
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
