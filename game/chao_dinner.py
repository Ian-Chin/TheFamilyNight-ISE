"""The Chao family dinner scene.

Terry walks in down the garden path from above the canvas while the opening
black fades away, then settles by the dinner table.
"""

import arcade

from . import textures
from .config import (
    CHAO_DINNER_BG, CHAO_ENTRY_Y, CHAO_FADE_IN, CHAO_PATH_X, CHAO_STOP_Y,
    CHAO_WALK_BOUNDS, HEIGHT, WIDTH,
)
from .pause import PauseMenu
from .sprites import Terry
from .views import StageView

# --- HUD, parked ------------------------------------------------------------
# The day cycle badge, settings, backpack and map are built and working in
# game/hud.py, but kept out of the scene for now. To put them back, uncomment
# the four blocks marked "HUD:" below and these two imports.
# from .config import PANEL_H, PANEL_W
# from .hud import HUD
# from .ui import Card


def cover_rect(texture, rect):
    """Fill `rect` with `texture` without distorting it."""
    scale = max(rect.width / texture.width, rect.height / texture.height)
    return arcade.XYWH(
        rect.x, rect.y, texture.width * scale, texture.height * scale
    )


class ChaoDinnerView(StageView):
    """Scripted entrance: fade up from black as Terry walks down the path."""

    def __init__(self):
        super().__init__()
        self.background = textures.background(CHAO_DINNER_BG)

        self.terry = Terry(CHAO_PATH_X, CHAO_ENTRY_Y)
        self.sprites = arcade.SpriteList()
        self.sprites.append(self.terry)

        self.fade_clock = 0.0
        self.walking_in = True
        self.held = set()

        self.panel = None   # the label of the open HUD popup, or None
        self.pause_menu = PauseMenu()
        self.widgets = [self.pause_menu]
        # HUD: build it and lay it out with the other widgets.
        # self.hud = HUD()
        # self.placeholder = Card(PANEL_W, PANEL_H, "", ["Nothing here yet."])
        # self.widgets = [self.hud, self.placeholder, self.pause_menu]

        # The camera projects the fixed canvas into the letterboxed stage, so
        # Terry's coordinates stay in canvas units whatever the window size.
        self.camera = arcade.camera.Camera2D(
            position=(WIDTH / 2, HEIGHT / 2),
            projection=arcade.LRBT(-WIDTH / 2, WIDTH / 2, -HEIGHT / 2, HEIGHT / 2),
            viewport=self.stage.viewport(),
        )
        self.relayout()

    def relayout(self):
        super().relayout()
        self.camera.viewport = self.stage.viewport()
        self.hint = self.stage.text(
            "WASD to move    Space to jump    Esc to pause",
            WIDTH / 2, 26, (238, 240, 246), 14,
            anchor_x="center", anchor_y="center",
        )

    @property
    def fade_alpha(self):
        if self.fade_clock >= CHAO_FADE_IN:
            return 0
        return round(255 * (1 - self.fade_clock / CHAO_FADE_IN))

    def on_draw(self):
        self.clear()
        viewport = self.stage.viewport()
        arcade.draw_texture_rect(self.background, cover_rect(self.background, viewport))

        self.camera.use()
        self.terry.draw_shadow()
        self.sprites.draw(pixelated=True)
        self.window.default_camera.use()

        if not self.walking_in:
            self.hint.draw()
            # HUD: drawn once the scripted entrance is over, and under the fade
            # so the opening black covers it too.
            # self.hud.draw()
            # if self.panel:
            #     self.placeholder.set_title(self.panel)
            #     self.placeholder.draw()

        alpha = self.fade_alpha
        if alpha:
            arcade.draw_rect_filled(
                arcade.LBWH(0, 0, self.window.width, self.window.height),
                (0, 0, 0, alpha),
            )

        self.pause_menu.draw()

    def on_update(self, delta_time):
        if self.pause_menu.visible or self.panel:
            return

        # The first frame of a view carries the window's load time, which would
        # otherwise eat most of the opening fade in one step.
        delta_time = min(delta_time, 1 / 30)
        self.fade_clock += delta_time

        if self.walking_in:
            # Walk south along the path; the entry point sits above the canvas,
            # so the bounds are opened up to let Terry step in from off-screen.
            self.terry.update_movement(
                delta_time, 0, -1, (0, WIDTH, 0, CHAO_ENTRY_Y + self.terry.height),
            )
            if self.terry.ground_y <= CHAO_STOP_Y:
                self.terry.ground_y = CHAO_STOP_Y
                self.walking_in = False
            return

        dx = (arcade.key.D in self.held) - (arcade.key.A in self.held)
        dy = (arcade.key.W in self.held) - (arcade.key.S in self.held)
        self.terry.update_movement(delta_time, dx, dy, CHAO_WALK_BOUNDS)

    def on_key_press(self, key, modifiers):
        if self.pause_menu.visible:
            self.run_action(self.pause_menu.on_key_press(key))
            return

        if key == arcade.key.ESCAPE:
            self.held.clear()
            if self.panel:
                self.panel = None
            else:
                self.pause_menu.open()
            return

        if self.panel:
            return

        if self.walking_in:
            if key == arcade.key.SPACE:
                # Skip the entrance.
                self.fade_clock = CHAO_FADE_IN
                self.terry.ground_y = CHAO_STOP_Y
                self.walking_in = False
            return

        if key == arcade.key.SPACE:
            self.terry.start_jump()
            return
        self.held.add(key)

    def on_key_release(self, key, modifiers):
        self.held.discard(key)

    def on_mouse_motion(self, x, y, dx, dy):
        canvas_x, canvas_y = self.canvas_point(x, y)
        self.pause_menu.on_mouse_motion(canvas_x, canvas_y)
        # HUD: only light its buttons up when nothing is over the scene.
        # if self.pause_menu.visible or self.panel or self.walking_in:
        #     self.hud.clear_hover()
        # else:
        #     self.hud.on_mouse_motion(canvas_x, canvas_y)

    def on_mouse_press(self, x, y, button, modifiers):
        canvas_x, canvas_y = self.canvas_point(x, y)
        if self.pause_menu.visible:
            self.run_action(self.pause_menu.on_mouse_press(canvas_x, canvas_y, button))
            return
        if self.panel:
            # Any click dismisses an open popup.
            self.panel = None
            return
        if self.walking_in:
            return
        # HUD: a click on an icon opens its popup; the badge handles its own.
        # clicked = self.hud.on_mouse_press(canvas_x, canvas_y, button)
        # if clicked and clicked != "day":
        #     self.held.clear()
        #     self.panel = clicked.capitalize()

    def run_action(self, action):
        if action is None:
            return
        if action == "resume":
            self.pause_menu.close()
        elif action == "menu":
            from .views import MenuView

            self.window.show_view(MenuView())
        elif action == "quit":
            self.window.close()
