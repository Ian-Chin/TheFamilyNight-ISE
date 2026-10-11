from pathlib import Path
import arcade

from . import audio
from .config import HEIGHT, WIDTH
from .dialogue import DialogBox
from .options import SettingsPanel
from .pause import PauseMenu
from .views import MenuView, StageView
from .market_dash_common import BG_DIR, cover_rect


# ============================================================================
# PART 4: Transition to Bumpy Bus Scene
# ============================================================================
class MarketEndingView(StageView):
    """Part 4: Walking back home with ingredients, then transitioning directly to Bumpy Bus."""

    def __init__(self):
        super().__init__()
        self.dialog = DialogBox()
        self.pause_menu = PauseMenu()
        self.settings_panel = SettingsPanel()
        self.widgets = [self.dialog, self.pause_menu, self.settings_panel]

        walk_home_img = BG_DIR / "Scene 3 - returning home.jpg"

        self.ending_slides = [
            ("Terry", "Phew... that was an absolute war zone, but I made it out alive!", walk_home_img),
            ("Terry", "Prime meat, fresh produce, and even this frozen mackerel??? Forget about it..", walk_home_img),
            ("Terry", "The BBQ is officially saved.", walk_home_img),
            ("Terry", "It's 4:30 PM. I need to catch the bus now before Dave and the relatives arrive!", walk_home_img),
        ]
        self.current_slide = 0
        self.bg_texture = None

        self.relayout()

    def on_show_view(self):
        audio.play("dialog_open")
        self.trigger_slide(0)

    def trigger_slide(self, index):
        if index >= len(self.ending_slides):
            self.dialog.close()
            # Seamless transition to Scene 2 (Bumpy Bus)
            from game.bumpy_bus import BumpyBusView
            self.window.show_view(BumpyBusView())
            return

        self.current_slide = index
        speaker, text, img_target = self.ending_slides[index]

        if img_target and Path(img_target).exists():
            self.bg_texture = arcade.load_texture(str(img_target))

        self.dialog.open(speaker, text)

    def advance_slide(self):
        if self.dialog.typing:
            self.dialog.advance()
        else:
            self.trigger_slide(self.current_slide + 1)

    def on_update(self, delta_time):
        if self.pause_menu.visible or self.settings_panel.visible:
            return

        if self.dialog.visible:
            self.dialog.update(delta_time)

    def on_draw(self):
        self.clear()

        if self.bg_texture:
            arcade.draw_texture_rect(
                self.bg_texture,
                cover_rect(self.bg_texture, self.stage.viewport())
            )
        else:
            arcade.draw_rect_filled(
                arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT),
                (24, 28, 36)
            )

        if self.dialog.visible:
            self.dialog.draw()

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

        if key in (arcade.key.ENTER, arcade.key.SPACE, arcade.key.NUM_ENTER):
            self.advance_slide()

    def on_mouse_press(self, x, y, button, modifiers):
        canvas_x, canvas_y = self.canvas_point(x, y)
        if self.settings_panel.on_mouse_press(canvas_x, canvas_y, button):
            return
        if self.pause_menu.visible:
            self.run_action(self.pause_menu.on_mouse_press(canvas_x, canvas_y, button))
            return

        if button == arcade.MOUSE_BUTTON_LEFT:
            self.advance_slide()

    def on_mouse_motion(self, x, y, dx, dy):
        self.pause_menu.on_mouse_motion(*self.canvas_point(x, y))

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.settings_panel.on_mouse_drag(*self.canvas_point(x, y))

    def on_mouse_release(self, x, y, button, modifiers):
        self.settings_panel.on_mouse_release()

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