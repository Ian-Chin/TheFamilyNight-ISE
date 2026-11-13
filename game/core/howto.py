import arcade

from . import audio, textures
from ..config import (
    HEIGHT, PAUSE_DIM, PLANK_PAD, TEXT_BRIGHT, TEXT_DIM, TEXT_HOVER, TEXT_SHADOW, WIDTH,
)
from .ui import MenuButton

CARD_W = 940
CARD_H = 500
PREVIEW_W = 480
PREVIEW_H = 270
STEP_GAP = 68
BADGE_R = 15


class HowToPlay:
    def __init__(self, title, preview, steps):
        self.title = title
        self.preview_name = preview
        self.steps = steps
        self.stage = None
        self.visible = False
        self.width, self.height = CARD_W, CARD_H
        self.left = (WIDTH - CARD_W) / 2
        self.bottom = (HEIGHT - CARD_H) / 2
        self.preview_left = self.left + 34
        self.preview_bottom = self.bottom + 116
        self.steps_left = self.preview_left + PREVIEW_W + 40
        self.buttons = [MenuButton("Start", "start", "play",
                                   WIDTH / 2 - 135, self.bottom + 30, 270, 56)]

    def open(self):
        self.visible = True

    def close(self):
        self.visible = False
        for button in self.buttons:
            button.hovered = False

    def layout(self, stage):
        self.stage = stage
        self.texture = textures.card(stage.px(self.width), stage.px(self.height),
                                     stage.px(PLANK_PAD))
        self.preview = textures.ui_image(self.preview_name)
        top = self.bottom + self.height
        self.texts = [
            stage.text("HOW TO PLAY", self.left + 34, top - 36, TEXT_HOVER, 13,
                       bold=True, anchor_y="center"),
            stage.text(self.title, self.left + 34 + 2, top - 72 - 2, TEXT_SHADOW, 30,
                       bold=True, anchor_y="center"),
            stage.text(self.title, self.left + 34, top - 72, TEXT_BRIGHT, 30,
                       bold=True, anchor_y="center"),
            stage.text("Press Enter to start", WIDTH / 2 + 160, self.bottom + 58, TEXT_DIM,
                       12, anchor_y="center"),
        ]
        width = self.left + self.width - 34 - (self.steps_left + 2 * BADGE_R + 14)
        self.badges = []
        y = self.preview_bottom + PREVIEW_H - BADGE_R
        for number, step in enumerate(self.steps, 1):
            self.badges.append((self.steps_left + BADGE_R, y))
            self.texts.append(stage.text(str(number), self.steps_left + BADGE_R, y,
                                         (20, 22, 28), 13, bold=True,
                                         anchor_x="center", anchor_y="center"))
            self.texts.append(stage.text(step, self.steps_left + 2 * BADGE_R + 14, y + 11,
                                         TEXT_BRIGHT, 14, anchor_y="top",
                                         multiline=True, width=width * stage.scale))
            y -= STEP_GAP
        for button in self.buttons:
            button.layout(stage)

    def draw(self):
        if not self.visible:
            return
        stage = self.stage
        arcade.draw_rect_filled(arcade.LBWH(0, 0, stage.window_w, stage.window_h), PAUSE_DIM)
        arcade.draw_texture_rect(self.texture, stage.rect(
            self.left - PLANK_PAD, self.bottom - PLANK_PAD,
            self.width + 2 * PLANK_PAD, self.height + 2 * PLANK_PAD,
        ))
        frame = stage.rect(self.preview_left, self.preview_bottom, PREVIEW_W, PREVIEW_H)
        arcade.draw_texture_rect(self.preview, frame)
        arcade.draw_rect_outline(frame, TEXT_HOVER, max(1, 2 * stage.scale))
        for x, y in self.badges:
            arcade.draw_circle_filled(*stage.to_screen(x, y), BADGE_R * stage.scale, TEXT_HOVER)
        for text in self.texts:
            text.draw()
        for button in self.buttons:
            button.draw()

    def on_mouse_motion(self, x, y):
        if not self.visible:
            return
        for button in self.buttons:
            button.hovered = button.contains(x, y)

    def on_mouse_press(self, x, y, mouse_button):
        if not self.visible or mouse_button != arcade.MOUSE_BUTTON_LEFT:
            return None
        for button in self.buttons:
            if button.contains(x, y):
                audio.play("ui_click")
                return button.action
        return None
