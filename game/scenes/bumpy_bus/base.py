import arcade

from ...config import HEIGHT, WIDTH
from ...core import audio
from ...core.options import SettingsPanel
from ...core.pause import PauseMenu
from ...core.stage import StageView
from .config import LOSE_ITEMS


class BusView(StageView):
    def __init__(self, lose_title="Try Again", lose_message=""):
        super().__init__()
        self.held = set()
        self.keep_music = False
        self.music = audio.ambience("bus_music")
        self.pause_menu = PauseMenu()
        self.settings_panel = SettingsPanel()
        self.lose_card = PauseMenu(LOSE_ITEMS, lose_title, lose_message, width=460)
        self.widgets = [self.pause_menu, self.settings_panel, self.lose_card]
        self.camera = arcade.camera.Camera2D(
            position=(WIDTH / 2, HEIGHT / 2),
            projection=arcade.LRBT(-WIDTH / 2, WIDTH / 2, -HEIGHT / 2, HEIGHT / 2),
            viewport=self.stage.viewport(),
        )

    def relayout(self):
        super().relayout()
        self.camera.viewport = self.stage.viewport()

    @property
    def held_up(self):
        return (self.pause_menu.visible or self.settings_panel.visible
                or self.lose_card.visible)


    def go(self, view):
        self.keep_music = True
        self.held.clear()
        self.window.show_view(view)

    def retry(self):
        pass

    def on_show_view(self):
        self.music.start()

    def on_hide_view(self):
        if not self.keep_music:
            self.music.stop()


    def draw_menus(self):
        self.window.default_camera.use()
        self.lose_card.draw()
        if not self.settings_panel.visible:
            self.pause_menu.draw()
        self.settings_panel.draw()

    def draw_fade(self, alpha):
        if alpha > 0:
            arcade.draw_rect_filled(
                arcade.LBWH(0, 0, self.stage.window_w, self.stage.window_h),
                (0, 0, 0, round(min(255, alpha))),
            )


    def key_down(self, key):
        self.held.add(key)

    def click(self, x, y, button):
        pass

    def on_key_press(self, key, modifiers):
        if self.settings_panel.visible:
            if self.settings_panel.on_key_press(key) == "close":
                self.settings_panel.close()
            return
        if self.lose_card.visible:
            return
        if self.pause_menu.visible:
            self.run_action(self.pause_menu.on_key_press(key))
            return
        if key == arcade.key.ESCAPE:
            self.held.clear()
            audio.play("ui_click")
            self.pause_menu.open()
            return
        self.key_down(key)

    def on_key_release(self, key, modifiers):
        self.held.discard(key)

    def on_mouse_motion(self, x, y, dx, dy):
        canvas_x, canvas_y = self.canvas_point(x, y)
        self.pause_menu.on_mouse_motion(canvas_x, canvas_y)
        self.lose_card.on_mouse_motion(canvas_x, canvas_y)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.settings_panel.on_mouse_drag(*self.canvas_point(x, y))

    def on_mouse_release(self, x, y, button, modifiers):
        self.settings_panel.on_mouse_release()

    def on_mouse_press(self, x, y, button, modifiers):
        canvas_x, canvas_y = self.canvas_point(x, y)
        if self.settings_panel.on_mouse_press(canvas_x, canvas_y, button):
            return
        if self.lose_card.visible:
            self.run_action(self.lose_card.on_mouse_press(canvas_x, canvas_y, button))
        elif self.pause_menu.visible:
            self.run_action(self.pause_menu.on_mouse_press(canvas_x, canvas_y, button))
        else:
            self.click(canvas_x, canvas_y, button)

    def run_action(self, action):
        if action == "resume":
            self.pause_menu.close()
        elif action == "settings":
            self.settings_panel.open()
        elif action == "retry":
            self.retry()
        elif action == "menu":
            from ..menu.view import MenuView
            self.window.show_view(MenuView())
        elif action == "quit":
            self.window.close()
