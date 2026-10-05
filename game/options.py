"""The settings screen: audio levels and the graphics mode.

Like PauseMenu, a SettingsPanel is owned by a view rather than being one: lay
it out with the other widgets, draw it over whatever is behind, and pass the
mouse and key events through in canvas units. `on_key_press` returns "close"
once the player is done with it.
"""

import arcade

from . import audio, textures
from .config import (
    GRAPHICS_CHOICES, HEIGHT, PAUSE_DIM, PLANK_PAD, SETTINGS_HINT_SIZE, SETTINGS_PANEL_PAD,
    SETTINGS_PANEL_W, SETTINGS_ROW_GAP, SETTINGS_ROWS, SETTINGS_STEP,
    SETTINGS_TITLE, SETTINGS_TITLE_GAP, SLIDER_W, TEXT_DIM, TEXT_HOVER, WIDTH,
)
from .settings import graphics, mixer
from .ui import Choice, Slider

TITLE_SIZE = 32


class SettingsPanel:
    """Volume sliders over a graphics mode switch, centred on the canvas."""

    def __init__(self):
        self.visible = False
        self.selected = 0

        rows = len(SETTINGS_ROWS) + 1
        self.width = SETTINGS_PANEL_W
        self.height = (
            SETTINGS_TITLE_GAP + SETTINGS_PANEL_PAD
            + rows * SETTINGS_ROW_GAP + SETTINGS_PANEL_PAD
        )
        self.left = (WIDTH - self.width) / 2
        self.bottom = (HEIGHT - self.height) / 2

        # Sliders sit on the right of the panel, labels in the space left of
        # them, so the rows line up down a single edge.
        slider_left = self.left + self.width - SETTINGS_PANEL_PAD - SLIDER_W - 72
        middle_y = (
            self.bottom + self.height - SETTINGS_TITLE_GAP
            - SETTINGS_PANEL_PAD - SETTINGS_ROW_GAP / 2
        )
        self.sliders = []
        for channel, label, note in SETTINGS_ROWS:
            self.sliders.append(
                Slider(channel, label, note, slider_left, middle_y, mixer)
            )
            middle_y -= SETTINGS_ROW_GAP
        # The switch shares the sliders' events, so it rides in the same list.
        self.sliders.append(Choice(
            "Graphics", "animated or still backgrounds", GRAPHICS_CHOICES,
            slider_left, middle_y, graphics,
        ))
        self.apply_selection()

    def open(self):
        self.visible = True
        self.selected = 0
        self.apply_selection()

    def close(self):
        self.visible = False
        for slider in self.sliders:
            slider.dragging = False

    def apply_selection(self):
        for index, slider in enumerate(self.sliders):
            slider.selected = index == self.selected

    def layout(self, stage):
        self.stage = stage
        self.texture = textures.card(
            stage.px(self.width), stage.px(self.height), stage.px(PLANK_PAD)
        )
        middle = self.left + self.width / 2
        self.title_text = stage.text(
            SETTINGS_TITLE, middle,
            self.bottom + self.height - SETTINGS_TITLE_GAP / 2, TEXT_HOVER,
            TITLE_SIZE, anchor_x="center", anchor_y="center", bold=True,
        )
        self.hint_text = stage.text(
            "Drag a bar, or use the arrow keys    Esc to go back",
            middle, self.bottom + 34, TEXT_DIM, SETTINGS_HINT_SIZE,
            anchor_x="center", anchor_y="center",
        )
        for slider in self.sliders:
            slider.layout(stage)

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
        for slider in self.sliders:
            slider.draw()
        self.hint_text.draw()

    def on_key_press(self, key):
        """Return "close" when the player is finished, else None."""
        if not self.visible:
            return None
        if key == arcade.key.ESCAPE:
            return "close"
        if key in (arcade.key.DOWN, arcade.key.S):
            self.selected = (self.selected + 1) % len(self.sliders)
            self.apply_selection()
        elif key in (arcade.key.UP, arcade.key.W):
            self.selected = (self.selected - 1) % len(self.sliders)
            self.apply_selection()
        elif key in (arcade.key.LEFT, arcade.key.A):
            self.sliders[self.selected].nudge(-SETTINGS_STEP)
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self.sliders[self.selected].nudge(SETTINGS_STEP)
        return None

    def on_mouse_press(self, x, y, mouse_button):
        """`x, y` in canvas units. Returns True when the click was ours."""
        if not self.visible or mouse_button != arcade.MOUSE_BUTTON_LEFT:
            return False
        for index, slider in enumerate(self.sliders):
            if slider.contains(x, y):
                audio.play("ui_click")
                self.selected = index
                self.apply_selection()
                slider.dragging = True
                slider.set_from_x(x)
                return True
        # Clicks anywhere else are swallowed, so the scene behind the panel
        # does not also act on them.
        return True

    def on_mouse_drag(self, x, y):
        if not self.visible:
            return
        for slider in self.sliders:
            if slider.dragging:
                slider.set_from_x(x)

    def on_mouse_release(self):
        for slider in self.sliders:
            slider.dragging = False
