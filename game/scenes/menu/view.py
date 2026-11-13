import arcade

from ...core import audio, textures
from ...core.backdrop import Backdrop
from ...config import (
    CREDIT_SIZE, HEIGHT, MENU_BUTTON_H, MENU_BUTTON_W, PANEL_H, PANEL_W, WIDTH,
)
from .config import (
    CREDITS_H, CREDITS_NAMES, CREDITS_W, CREDIT_ICON, CREDIT_MARGIN, LOGO_TOP_MARGIN,
    LOGO_WIDTH, MENU_BUTTON_GAP, MENU_ITEMS, MENU_MUSIC, MENU_RIGHT, REVEAL_FLASH,
    REVEAL_TIME, REVEAL_ZOOM,
)
from ...core.options import SettingsPanel
from ...core.pause import PauseMenu
from ...core.settings import graphics
from ...core.sprites import Terry
from ...core.stage import StageView
from ...core.ui import Card, CreditsButton, MenuButton


def cover_rect(texture, window_w, window_h):
    scale = max(window_w / texture.width, window_h / texture.height)
    return arcade.XYWH(
        window_w / 2, window_h / 2, texture.width * scale, texture.height * scale
    )


class MenuView(StageView):
    def __init__(self, reveal=False):
        super().__init__()
        self.reveal = reveal
        self.reveal_clock = 0.0
        self.reveal_camera = arcade.camera.Camera2D() if reveal else None
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

    def prepare(self):
        atlas = self.window.ctx.default_atlas
        atlas.add(self.logo)
        self.backdrop.reserve()
        if graphics.animated and self.backdrop.video is not None:
            self.backdrop.start()

    def on_show_view(self):
        audio.ambience(MENU_MUSIC).start()

    def on_update(self, delta_time):
        self.backdrop.update(delta_time)
        audio.ambience(MENU_MUSIC).update(delta_time)
        if self.reveal:
            self.reveal_clock += min(delta_time, 1 / 30)
            if self.reveal_clock >= REVEAL_TIME:
                self.reveal = False

    def on_hide_view(self):
        self.backdrop.stop()

    def reveal_progress(self):
        return min(1.0, self.reveal_clock / REVEAL_TIME)

    def draw_flash(self):
        p = min(1.0, self.reveal_clock / REVEAL_FLASH)
        arcade.draw_rect_filled(
            arcade.LBWH(0, 0, self.stage.window_w, self.stage.window_h),
            (255, 255, 255, round(255 * (1 - p) ** 2)),
        )

    def on_draw(self):
        self.clear()
        if self.reveal:
            camera = self.reveal_camera
            camera.match_window()
            camera.zoom = 1 + (REVEAL_ZOOM - 1) * (1 - self.reveal_progress()) ** 3
            camera.use()
        background = self.backdrop.texture
        arcade.draw_texture_rect(
            background,
            cover_rect(background, self.stage.window_w, self.stage.window_h),
        )
        arcade.draw_texture_rect(self.logo, self.stage.rect(
            self.logo_left, self.logo_bottom, LOGO_WIDTH, self.logo_h,
        ))
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
        if self.reveal:
            self.window.default_camera.use()
            self.draw_flash()

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
            audio.ambience(MENU_MUSIC).stop()
            from ..market_dash import MarketDashView
            self.window.show_view(MarketDashView())
        elif item.action == "story":
            from .story import StoryView
            self.window.show_view(StoryView())
        elif item.action == "achievement":
            from .achievements import AchievementsView
            self.window.show_view(AchievementsView())
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
