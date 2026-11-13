from pathlib import Path
import arcade

from ...core import achievements, audio, textures
from ...core.backdrop import Backdrop
from ...config import HEIGHT, WIDTH
from ...core.dialogue import DialogBox
from ...core.options import SettingsPanel
from ...core.pause import PauseMenu
from ..menu.view import MenuView
from ...core.stage import StageView
from .common import DialogueController
from ..bumpy_bus.view import BumpyBusView


class MarketEndingView(StageView):
    """Ending cutscene view when Terry successfully defends his basket and escapes."""

    def __init__(self):
        super().__init__()
        self.backdrop = Backdrop("market-dash/Scene 2.4 - market interior.jpg")

        self.dialog = DialogBox()
        self.pause_menu = PauseMenu()
        self.settings_panel = SettingsPanel()
        self.widgets = [self.dialog, self.pause_menu, self.settings_panel]

        self.in_wave_dialogue = False
        self.dialogue_bg = None 

       
        end_scene = textures.background("market-dash/Scene 3 - returning home.jpg")

        self.dialogue_queue = [
            ("Terry", "Pant... pant... I actually made it through the checkout doors!", None),
            ("Terry", "Every single ingredient for tonight's dinner survived unscratched!", None),
            ("Terry", "The family is going to love this BBQ feast.", end_scene),
            ("Terry", "Let's hurry home before it gets dark!", end_scene),
        ]

        def end_advance():
            if self.dialog.typing:
                self.dialog.advance()
            else:
                self.advance_dialogue()

        def end_skip():
            self.dialog.close()
            self.finish_scene()

        self.dialog_ctrl = DialogueController(end_advance, end_skip)

        self.camera = arcade.camera.Camera2D(
            position=(WIDTH / 2, HEIGHT / 2),
            projection=arcade.LRBT(-WIDTH / 2, WIDTH / 2, -HEIGHT / 2, HEIGHT / 2),
            viewport=self.stage.viewport()
        )
        self.ui_camera = arcade.camera.Camera2D(
            position=(WIDTH / 2, HEIGHT / 2),
            projection=arcade.LRBT(-WIDTH / 2, WIDTH / 2, -HEIGHT / 2, HEIGHT / 2),
            viewport=self.stage.viewport()
        )
        self.relayout()

    def on_show_view(self):
        achievements.unlock("market_done")
        self.in_wave_dialogue = True
        if self.dialogue_queue:
            item = self.dialogue_queue.pop(0)
            speaker, text = item[0], item[1]
            self.dialogue_bg = item[2] if len(item) > 2 else None
            self.dialog.open(speaker, text)
            self.dialog_ctrl.record(speaker, text)

    def relayout(self):
        super().relayout()
        if hasattr(self, "camera"):
            self.camera.viewport = self.stage.viewport()
        if hasattr(self, "ui_camera"):
            self.ui_camera.viewport = self.stage.viewport()

    def advance_dialogue(self):
        if self.dialogue_queue:
            item = self.dialogue_queue.pop(0)
            speaker, text = item[0], item[1]
            self.dialogue_bg = item[2] if len(item) > 2 else None
            self.dialog.open(speaker, text)
            self.dialog_ctrl.record(speaker, text)
        else:
            self.dialog.close()
            self.dialogue_bg = None
            self.in_wave_dialogue = False
            self.finish_scene()

    def on_hide_view(self):
        self.backdrop.stop()

    def finish_scene(self):
        self.backdrop.stop()
        self.window.show_view(BumpyBusView())

    def on_update(self, delta_time):
        if self.pause_menu.visible or self.settings_panel.visible:
            return

        self.backdrop.update(delta_time)

        if self.in_wave_dialogue:
            if self.dialog.visible:
                self.dialog.update(delta_time)
            self.dialog_ctrl.update(
                delta_time,
                is_dialog_visible=self.dialog.visible,
                is_typing=self.dialog.typing
            )

    def on_draw(self):
        self.clear()

       
        self.camera.use()
        if self.in_wave_dialogue and self.dialogue_bg:
            arcade.draw_texture_rect(
                self.dialogue_bg,
                arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
            )
        elif self.backdrop:
            arcade.draw_texture_rect(
                self.backdrop.texture,
                arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
            )

       
        self.window.default_camera.use()
        if self.dialog.visible:
            self.dialog.draw()

       
        self.ui_camera.use()
        if self.in_wave_dialogue:
            self.dialog_ctrl.draw(show_controls=True)

       
        self.window.default_camera.use()
        if not self.settings_panel.visible:
            self.pause_menu.draw()
        self.settings_panel.draw()

    def on_key_press(self, key, modifiers):
        if self.settings_panel.visible:
            if self.settings_panel.on_key_press(key) == "close":
                self.settings_panel.close()
            return
        if self.pause_menu.visible:
            self.run_action(self.pause_menu.on_key_press(key))
            return
        if key == arcade.key.ESCAPE:
            if self.dialog_ctrl.history_panel.visible:
                self.dialog_ctrl.history_panel.toggle()
                return
            self.pause_menu.open()
            return

        if self.dialog_ctrl.history_panel.visible:
            if key in (arcade.key.ENTER, arcade.key.SPACE, arcade.key.NUM_ENTER):
                self.dialog_ctrl.history_panel.toggle()
            return

        if self.in_wave_dialogue and key in (arcade.key.ENTER, arcade.key.SPACE, arcade.key.NUM_ENTER):
            if self.dialog.typing:
                self.dialog.advance()
            else:
                self.advance_dialogue()

    def on_mouse_press(self, x, y, button, modifiers):
        canvas_x, canvas_y = self.canvas_point(x, y)

        if self.settings_panel.on_mouse_press(canvas_x, canvas_y, button):
            return
        if self.pause_menu.visible:
            self.run_action(self.pause_menu.on_mouse_press(canvas_x, canvas_y, button))
            return

       
        if self.dialog_ctrl.handle_mouse_press(canvas_x, canvas_y):
            return

        if self.in_wave_dialogue and button == arcade.MOUSE_BUTTON_LEFT:
            if self.dialog.typing:
                self.dialog.advance()
            else:
                self.advance_dialogue()

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.dialog_ctrl.history_panel.on_mouse_scroll(scroll_y)

                
    def run_action(self, action):
        if action == "resume":
            self.pause_menu.close()
        elif action == "settings":
            self.settings_panel.open()
        elif action == "menu":
            from ..menu.view import MenuView
            self.window.show_view(MenuView())
        elif action == "quit":
            self.window.close()