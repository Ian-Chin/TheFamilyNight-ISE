import sys
from pathlib import Path

import arcade
import PIL.Image

WIDTH = 1280
HEIGHT = 720
TITLE = "UI test"

ASSETS = Path(__file__).parent / "assets"
BACKGROUND = (238, 240, 244)

PHASE_NAMES = ["Morning", "Afternoon", "Evening", "Night"]
BADGE_ROWS = [
    (71, 112, 838, 298),
    (71, 442, 838, 298),
    (71, 772, 838, 298),
    (71, 1099, 838, 298),
]

MARGIN = 24
BADGE_HEIGHT = 64
ICON_SIZE = 56
MAP_SIZE = 110


def load_badge_textures():
    """Slice Daycycle.png into one texture per phase."""
    sheet = PIL.Image.open(ASSETS / "Daycycle.png").convert("RGBA")
    textures = []
    for i, (x, y, w, h) in enumerate(BADGE_ROWS):
        crop = sheet.crop((x, y, x + w, y + h))
        textures.append(arcade.Texture(crop, hit_box_algorithm=None))
    return textures


class Button(arcade.Sprite):
    """A sprite that grows slightly when the mouse is over it."""

    def __init__(self, texture, target_height, center_x, center_y, name):
        scale = target_height / texture.height
        super().__init__(texture, scale=scale, center_x=center_x, center_y=center_y)
        self.name = name
        self.base_scale = scale
        self.hovered = False

    def set_texture_keep_size(self, texture, target_height):
        self.texture = texture
        self.base_scale = target_height / texture.height
        self.scale = self.base_scale * (1.06 if self.hovered else 1.0)

    def set_hovered(self, hovered):
        if hovered == self.hovered:
            return
        self.hovered = hovered
        self.scale = self.base_scale * (1.06 if hovered else 1.0)


class HUD(arcade.Window):
    def __init__(self):
        super().__init__(WIDTH, HEIGHT, TITLE)
        self.background_color = BACKGROUND

        self.badge_textures = load_badge_textures()
        self.phase = 0
        self.panel = None  # name of the open panel, or None

        badge_w = self.badge_textures[0].width * (BADGE_HEIGHT / self.badge_textures[0].height)
        top = HEIGHT - MARGIN - BADGE_HEIGHT / 2

        self.day_button = Button(
            self.badge_textures[0], BADGE_HEIGHT,
            MARGIN + badge_w / 2, top, "day",
        )
        self.settings_button = Button(
            arcade.load_texture(ASSETS / "settings.png"), ICON_SIZE,
            MARGIN + badge_w + 20 + ICON_SIZE / 2, top, "settings",
        )
        self.backpack_button = Button(
            arcade.load_texture(ASSETS / "Backpack.png"), ICON_SIZE + 10,
            WIDTH - MARGIN - (ICON_SIZE + 10) / 2, top, "backpack",
        )
        self.map_button = Button(
            arcade.load_texture(ASSETS / "Map.png"), MAP_SIZE,
            WIDTH - MARGIN - MAP_SIZE / 2, MARGIN + MAP_SIZE / 2, "map",
        )

        self.buttons = arcade.SpriteList()
        self.buttons.extend([
            self.day_button,
            self.settings_button,
            self.backpack_button,
            self.map_button,
        ])

    def on_draw(self):
        self.clear()
        self.buttons.draw()

        if self.panel:
            self.draw_panel(self.panel)

    def draw_panel(self, name):
        w, h = 320, 200
        left = (WIDTH - w) / 2
        bottom = (HEIGHT - h) / 2
        arcade.draw_lbwh_rectangle_filled(left, bottom, w, h, (54, 60, 70))
        arcade.draw_lbwh_rectangle_outline(left, bottom, w, h, (150, 158, 170), 2)
        arcade.draw_text(
            name.capitalize(), left + w / 2, bottom + h - 46,
            arcade.color.WHITE, 22, anchor_x="center",
        )
        arcade.draw_text(
            "Nothing here yet.", left + w / 2, bottom + h / 2 - 10,
            (190, 196, 206), 14, anchor_x="center",
        )
        arcade.draw_text(
            "Press Esc or click to close", left + w / 2, bottom + 20,
            (140, 148, 160), 11, anchor_x="center",
        )

    def on_mouse_motion(self, x, y, dx, dy):
        hits = arcade.get_sprites_at_point((x, y), self.buttons)
        for button in self.buttons:
            button.set_hovered(button in hits)

    def on_mouse_press(self, x, y, button, modifiers):
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        if self.panel:
            self.panel = None
            return
        hits = arcade.get_sprites_at_point((x, y), self.buttons)
        if not hits:
            return
        clicked = hits[-1]
        if clicked.name == "day":
            self.phase = (self.phase + 1) % len(PHASE_NAMES)
            self.day_button.set_texture_keep_size(
                self.badge_textures[self.phase], BADGE_HEIGHT
            )
        else:
            self.panel = clicked.name

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            if self.panel:
                self.panel = None
            else:
                arcade.close_window()


def main():
    window = HUD()
    if "--screenshot" in sys.argv:
        out = sys.argv[sys.argv.index("--screenshot") + 1]

        def shot(_delta):
            window.on_draw()
            arcade.get_image().save(out)
            arcade.close_window()

        arcade.schedule(shot, 0.4)
    arcade.run()


if __name__ == "__main__":
    main()
