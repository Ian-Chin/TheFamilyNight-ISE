"""Screens: the title menu and the playable field."""

import arcade

from . import audio, textures
from .backdrop import Backdrop
from .config import (
    CREDIT_ICON, CREDIT_MARGIN, CREDIT_SIZE, CREDITS_H, CREDITS_NAMES, CREDITS_W,
    HEIGHT, LOGO_TOP_MARGIN, LOGO_WIDTH, MENU_BUTTON_GAP, MENU_BUTTON_H,
    MENU_BUTTON_W, MENU_ITEMS, MENU_RIGHT, PANEL_H, PANEL_W, WIDTH,
)
from .options import SettingsPanel
from .pause import PauseMenu
from .sprites import Terry
from .ui import Card, CreditsButton, MenuButton, Stage


def cover_rect(texture, window_w, window_h):
    """Fill the window with `texture` without distorting it."""
    scale = max(window_w / texture.width, window_h / texture.height)
    return arcade.XYWH(
        window_w / 2, window_h / 2, texture.width * scale, texture.height * scale
    )


class StageView(arcade.View):
    """A view laid out on the fixed canvas and rebuilt when the window changes."""

    def __init__(self):
        super().__init__()
        self.stage = Stage(self.window.width, self.window.height)
        self.widgets = []

    def relayout(self):
        for widget in self.widgets:
            widget.layout(self.stage)

    def on_resize(self, width, height):
        super().on_resize(width, height)
        self.stage.resize(width, height)
        self.relayout()

    def canvas_point(self, x, y):
        return self.stage.to_canvas(x, y)


class MenuView(StageView):
    def __init__(self):
        super().__init__()
        self.backdrop = Backdrop("menu-bg.jpg")
        self.logo = textures.ui_image("logo.png")

        self.logo_h = LOGO_WIDTH * self.logo.height / self.logo.width
        self.logo_left = MENU_RIGHT - LOGO_WIDTH
        self.logo_bottom = HEIGHT - LOGO_TOP_MARGIN - self.logo_h

        self.buttons = []
        left = MENU_RIGHT - MENU_BUTTON_W
        bottom = self.logo_bottom - 24 - MENU_BUTTON_H
        for label, action, icon in MENU_ITEMS:
            self.buttons.append(MenuButton(label, action, icon, left, bottom))
            bottom -= MENU_BUTTON_H + MENU_BUTTON_GAP

        self.credits_button = CreditsButton(
            CREDIT_ICON,
            CREDIT_MARGIN + CREDIT_SIZE / 2,
            CREDIT_MARGIN + CREDIT_SIZE / 2,
        )
        self.placeholder = Card(PANEL_W, PANEL_H, "", ["Nothing here yet."])
        self.credits_card = Card(
            CREDITS_W, CREDITS_H, "Credits", list(CREDITS_NAMES)
        )
        self.settings_panel = SettingsPanel()

        self.widgets = [
            *self.buttons, self.credits_button, self.placeholder,
            self.credits_card, self.settings_panel,
        ]
        self.relayout()
        self.panel = None

    def on_update(self, delta_time):
        self.backdrop.update(delta_time)

    def on_hide_view(self):
        self.backdrop.stop()

    def on_draw(self):
        self.clear()
        background = self.backdrop.texture
        arcade.draw_texture_rect(
            background,
            cover_rect(background, self.stage.window_w, self.stage.window_h),
        )
        arcade.draw_texture_rect(self.logo, self.stage.rect(
            self.logo_left, self.logo_bottom, LOGO_WIDTH, self.logo_h,
        ))
        # The settings panel is see-through enough that the button stack
        # reads straight through it, so the menu steps out of the way.
        if not self.settings_panel.visible:
            for button in self.buttons:
                button.draw()
            self.credits_button.draw()
        if self.panel == "Credits":
            self.credits_card.draw()
        elif self.panel:
            self.placeholder.set_title(self.panel)
            self.placeholder.draw()
        self.settings_panel.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        x, y = self.canvas_point(x, y)
        if self.settings_panel.visible:
            for button in self.buttons:
                button.hovered = False
            self.credits_button.hovered = False
            return
        for button in self.buttons:
            button.hovered = button.contains(x, y)
        self.credits_button.hovered = self.credits_button.contains(x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        canvas_x, canvas_y = self.canvas_point(x, y)
        if self.settings_panel.on_mouse_press(canvas_x, canvas_y, button):
            return
        if self.panel:
            self.panel = None
            return
        if self.credits_button.contains(canvas_x, canvas_y):
            audio.play("ui_click")
            self.panel = "Credits"
            return
        for item in self.buttons:
            if item.contains(canvas_x, canvas_y):
                audio.play("ui_click")
                self.activate(item)
                return

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.settings_panel.on_mouse_drag(*self.canvas_point(x, y))

    def on_mouse_release(self, x, y, button, modifiers):
        self.settings_panel.on_mouse_release()

    def activate(self, item):
        if item.action == "play":
            # Start BBQ Scene (CK)
            from .bbq_scene import BbqView
            
            self.window.show_view(BbqView())

            # Imported here: the scene module imports StageView from this one. (Ian)
            # from .chao_dinner import ChaoDinnerView

            # self.window.show_view(ChaoDinnerView())
        elif item.action == "settings":
            self.settings_panel.open()
        elif item.action == "quit":
            self.window.close()
        else:
            self.panel = item.label

    def on_key_press(self, key, modifiers):
        if self.settings_panel.visible:
            if self.settings_panel.on_key_press(key) == "close":
                self.settings_panel.close()
            return
        if key == arcade.key.ESCAPE:
            if self.panel:
                self.panel = None
            else:
                self.window.close()


class GameView(StageView):
    """An empty white field Terry can walk around."""

    def __init__(self):
        super().__init__()
        self.background_color = arcade.color.WHITE
        self.terry = Terry(WIDTH / 2, HEIGHT / 2)
        self.sprites = arcade.SpriteList()
        self.sprites.append(self.terry)
        self.held = set()
        self.pause_menu = PauseMenu()
        self.widgets = [self.pause_menu]
        self.widgets = [self.pause_menu]

        # A Camera2D projection is measured from its position, so the camera
        # sits at the middle of the canvas and projects half of it each way.
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
            WIDTH / 2, 26, (170, 176, 188), 14, anchor_x="center", anchor_y="center",
        )

    def on_draw(self):
        self.clear()
        self.camera.use()
        self.sprites.draw()
        self.window.default_camera.use()
        self.hint.draw()
        self.pause_menu.draw()

    def on_update(self, delta_time):
        if self.pause_menu.visible:
            return
        dx = (arcade.key.D in self.held) - (arcade.key.A in self.held)
        dy = (arcade.key.W in self.held) - (arcade.key.S in self.held)
        self.terry.update_movement(delta_time, dx, dy, (0, WIDTH, 0, HEIGHT))

    def on_key_press(self, key, modifiers):
        if self.pause_menu.visible:
            self.run_action(self.pause_menu.on_key_press(key))
            return
        if key == arcade.key.ESCAPE:
            self.held.clear()
            self.pause_menu.open()
            return
        if key == arcade.key.SPACE:
            self.terry.start_jump()
            return
        self.held.add(key)

    def on_key_release(self, key, modifiers):
        self.held.discard(key)

    def on_mouse_motion(self, x, y, dx, dy):
        self.pause_menu.on_mouse_motion(*self.canvas_point(x, y))

    def on_mouse_press(self, x, y, button, modifiers):
        canvas_x, canvas_y = self.canvas_point(x, y)
        self.run_action(self.pause_menu.on_mouse_press(canvas_x, canvas_y, button))

    def run_action(self, action):
        if action is None:
            return
        if action == "resume":
            self.pause_menu.close()
        elif action == "menu":
            self.window.show_view(MenuView())
        elif action == "quit":
            self.window.close()
