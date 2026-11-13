import arcade

from ...core import textures
from ...config import HEIGHT, WIDTH
from .config import (
    HUD_BACKPACK_H, HUD_BADGE_H, HUD_GAP, HUD_HOVER_GROW, HUD_MAP_H, HUD_MARGIN,
    HUD_PLATE_INSET, HUD_PLATE_PAD, HUD_SETTINGS_H, PHASE_NAMES,
)


class HudButton:
    def __init__(self, name, texture, height, plate=True):
        self.name = name
        self.height = height
        self.plate = plate
        self.set_texture(texture)
        self.center_x = 0.0
        self.center_y = 0.0
        self.hovered = False

    def set_texture(self, texture):
        self.texture = texture
        self.width = texture.width * self.height / texture.height

    def place(self, center_x, center_y):
        self.center_x = center_x
        self.center_y = center_y

    @property
    def plate_size(self):
        inset = 2 * HUD_PLATE_INSET if self.plate else 0
        return self.width + inset, self.height + inset

    def contains(self, x, y):
        plate_w, plate_h = self.plate_size
        return (
            abs(x - self.center_x) <= plate_w / 2
            and abs(y - self.center_y) <= plate_h / 2
        )

    def layout(self, stage):
        if not self.plate:
            return
        plate_w, plate_h = self.plate_size
        size = (stage.px(plate_w), stage.px(plate_h), stage.px(HUD_PLATE_PAD))
        self.plate_art = textures.hud_plate(*size, False)
        self.plate_art_hovered = textures.hud_plate(*size, True)

    def draw(self, stage):
        grow = HUD_HOVER_GROW if self.hovered else 1.0
        if self.plate:
            plate_w, plate_h = self.plate_size
            width = plate_w * grow + 2 * HUD_PLATE_PAD
            height = plate_h * grow + 2 * HUD_PLATE_PAD
            arcade.draw_texture_rect(
                self.plate_art_hovered if self.hovered else self.plate_art,
                stage.rect(
                    self.center_x - width / 2, self.center_y - height / 2,
                    width, height,
                ),
            )
        width, height = self.width * grow, self.height * grow
        arcade.draw_texture_rect(self.texture, stage.rect(
            self.center_x - width / 2, self.center_y - height / 2, width, height,
        ))


class HUD:
    def __init__(self):
        self.badges = textures.day_badges()
        self.phase = 0

        self.day = HudButton("day", self.badges[0], HUD_BADGE_H, plate=False)
        self.settings = HudButton(
            "settings", textures.ui_image("settings.png"), HUD_SETTINGS_H
        )
        self.backpack = HudButton(
            "backpack", textures.ui_image("Backpack.png"), HUD_BACKPACK_H
        )
        self.map = HudButton("map", textures.ui_image("Map.png"), HUD_MAP_H)

        top = HEIGHT - HUD_MARGIN - HUD_BADGE_H / 2
        self.day.place(HUD_MARGIN + self.day.width / 2, top)
        self.settings.place(
            self.day.center_x + self.day.width / 2 + HUD_GAP
            + self.settings.plate_size[0] / 2,
            top,
        )
        self.backpack.place(
            WIDTH - HUD_MARGIN - self.backpack.plate_size[0] / 2,
            HEIGHT - HUD_MARGIN - self.backpack.plate_size[1] / 2,
        )
        self.map.place(
            WIDTH - HUD_MARGIN - self.map.plate_size[0] / 2,
            HUD_MARGIN + self.map.plate_size[1] / 2,
        )

        self.buttons = [self.day, self.settings, self.backpack, self.map]

    @property
    def phase_name(self):
        return PHASE_NAMES[self.phase]

    def clear_hover(self):
        for button in self.buttons:
            button.hovered = False

    def layout(self, stage):
        self.stage = stage
        for button in self.buttons:
            button.layout(stage)

    def draw(self):
        for button in self.buttons:
            button.draw(self.stage)

    def on_mouse_motion(self, x, y):
        for button in self.buttons:
            button.hovered = button.contains(x, y)

    def on_mouse_press(self, x, y, mouse_button):
        if mouse_button != arcade.MOUSE_BUTTON_LEFT:
            return None
        for button in self.buttons:
            if button.contains(x, y):
                if button is self.day:
                    self.advance_phase()
                return button.name
        return None

    def advance_phase(self):
        self.phase = (self.phase + 1) % len(self.badges)
        self.day.set_texture(self.badges[self.phase])
