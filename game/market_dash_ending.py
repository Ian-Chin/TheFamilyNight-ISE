from pathlib import Path
import arcade

from . import textures
from . import audio
from .config import HEIGHT, WIDTH
from .dialogue import DialogBox
from .options import SettingsPanel
from .pause import PauseMenu
from .views import MenuView, StageView
from .market_dash_common import DialogueController
from game.bumpy_bus import BumpyBusView


class MarketEndingView(StageView):
    """Ending cutscene view when Terry successfully defends his basket and escapes."""

    def __init__(self):
        super().__init__()
        self.bg_texture = textures.background("market-dash/Scene 2.4 - market interior.jpg")

        self.dialog = DialogBox()
        self.pause_menu = PauseMenu()
        self.settings_panel = SettingsPanel()
        self.widgets = [self.dialog, self.pause_menu, self.settings_panel]

        self.in_wave_dialogue = False
        self.dialogue_bg = None  # Holds the current scene cutscene image

        # Pass the background/cutscene texture as the 3rd tuple element
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
        self.relayout()

    def on_show_view(self):
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

    def finish_scene(self):
        self.window.show_view(BumpyBusView())

    def on_update(self, delta_time):
        if self.pause_menu.visible or self.settings_panel.visible:
            return

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

        # 1. Background image in camera space
        self.camera.use()
        if self.in_wave_dialogue and self.dialogue_bg:
            arcade.draw_texture_rect(
                self.dialogue_bg,
                arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
            )
        elif self.bg_texture:
            arcade.draw_texture_rect(
                self.bg_texture,
                arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
            )

        # 2. Dialogue Box (Screen Space)
        self.window.default_camera.use()
        if self.dialog.visible:
            self.dialog.draw()

        # # 3. Dialogue Controls (Auto, Skip, Log buttons)
        # self.camera.use()
        # if self.dialog.visible:
        #     self.dialog_ctrl.draw()

        # 3. Modals / Pause Menus
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
            self.pause_menu.open()
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

        if self.in_wave_dialogue and button == arcade.MOUSE_BUTTON_LEFT:
            if self.dialog.typing:
                self.dialog.advance()
            else:
                self.advance_dialogue()

                
    def run_action(self, action):
        if action == "resume":
            self.pause_menu.close()
        elif action == "settings":
            self.settings_panel.open()
        elif action == "menu":
            from .views import MenuView
            self.window.show_view(MenuView())
        elif action == "quit":
            self.window.close()