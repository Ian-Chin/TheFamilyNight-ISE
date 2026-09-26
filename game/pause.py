"""The in-game pause overlay.

A PauseMenu is owned by a view rather than being a view of its own, so the
scene underneath keeps drawing while the game is held. Any scene can reuse it:
lay it out with the other widgets, draw it last, and pass the mouse and key
events through. The handlers return an action string once a button is chosen.
"""

import arcade

from . import audio, textures
from .config import (
    HEIGHT, PAUSE_BUTTON_GAP, PAUSE_BUTTON_H, PAUSE_BUTTON_W, PAUSE_DIM,
    PAUSE_ITEMS, PAUSE_PANEL_PAD, PAUSE_PANEL_W, PAUSE_TITLE, PAUSE_TITLE_GAP,
    PAUSE_TITLE_SIZE, PLANK_PAD, TEXT_HOVER, WIDTH,
)
from .ui import MenuButton


class PauseMenu:
    """A dimmed screen with a parchment panel of buttons, centred on the canvas."""

    def __init__(self, items=PAUSE_ITEMS, title=PAUSE_TITLE):
        self.title = title
        self.visible = False

        stack_h = (
            len(items) * PAUSE_BUTTON_H + (len(items) - 1) * PAUSE_BUTTON_GAP
        )
        self.width = PAUSE_PANEL_W
        self.height = PAUSE_TITLE_GAP + PAUSE_PANEL_PAD + stack_h + PAUSE_PANEL_PAD
        self.left = (WIDTH - self.width) / 2
        self.bottom = (HEIGHT - self.height) / 2

        button_left = self.left + (self.width - PAUSE_BUTTON_W) / 2
        button_bottom = self.bottom + PAUSE_PANEL_PAD + stack_h - PAUSE_BUTTON_H
        self.buttons = []
        for label, action, icon in items:
            self.buttons.append(MenuButton(
                label, action, icon, button_left, button_bottom,
                PAUSE_BUTTON_W, PAUSE_BUTTON_H,
            ))
            button_bottom -= PAUSE_BUTTON_H + PAUSE_BUTTON_GAP

    def open(self):
        self.visible = True

    def close(self):
        self.visible = False
        for button in self.buttons:
            button.hovered = False

    def layout(self, stage):
        self.stage = stage
        self.texture = textures.card(
            stage.px(self.width), stage.px(self.height), stage.px(PLANK_PAD)
        )
        self.title_text = stage.text(
            self.title, self.left + self.width / 2,
            self.bottom + self.height - PAUSE_TITLE_GAP / 2, TEXT_HOVER,
            PAUSE_TITLE_SIZE, anchor_x="center", anchor_y="center", bold=True,
        )
        for button in self.buttons:
            button.layout(stage)

    def draw(self):
        if not self.visible:
            return
        arcade.draw_rect_filled(
            arcade.LBWH(0, 0, self.stage.window_w, self.stage.window_h), PAUSE_DIM,
        )
        arcade.draw_texture_rect(self.texture, self.stage.rect(
            self.left - PLANK_PAD, self.bottom - PLANK_PAD,
            self.width + 2 * PLANK_PAD, self.height + 2 * PLANK_PAD,
        ))
        self.title_text.draw()
        for button in self.buttons:
            button.draw()

    def on_mouse_motion(self, x, y):
        """`x, y` in canvas units."""
        if not self.visible:
            return
        for button in self.buttons:
            button.hovered = button.contains(x, y)

    def on_mouse_press(self, x, y, mouse_button):
        """Return the action of the button pressed, in canvas units, else None."""
        if not self.visible or mouse_button != arcade.MOUSE_BUTTON_LEFT:
            return None
        for button in self.buttons:
            if button.contains(x, y):
                audio.play("ui_click")
                return button.action
        return None

    def on_key_press(self, key):
        """Esc closes the menu; return "resume" so the caller unpauses."""
        if self.visible and key == arcade.key.ESCAPE:
            return "resume"
        return None
