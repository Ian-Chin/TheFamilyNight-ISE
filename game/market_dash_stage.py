import math
import arcade

from . import textures
from . import audio
from .config import HEIGHT, WIDTH
from .dialogue import DialogBox
from .options import SettingsPanel
from .pause import PauseMenu
from .views import MenuView, StageView
from .audio import Footsteps
from .sprites import Terry
from .market_dash_common import (
    MARKET_WALK_BOUNDS, MARKET_OBSTACLES,
    MARKET_STONE_AREAS, cover_rect
)


class MarketStageView(StageView):
    """Explorable market with 2 Red Exclamation zones and 1 Central Padlock defense zone."""

    def __init__(self, veg_done=False, meat_done=False):
        super().__init__()
        self.veg_done = veg_done
        self.meat_done = meat_done
        self.defend_unlocked = self.veg_done and self.meat_done

        self.near_veg = False
        self.near_meat = False
        self.near_defend = False

        self.held = set()
        self.time_elapsed = 0.0

        self.bg_texture = textures.background("market-dash/Scene 2.4 - market interior.jpg")

        # Defense pre-battle dialogue state
        self.stage_dialogue_queue = []
        self.stage_dialogue_callback = None

        def trigger_stage_dialogue(self, lines, on_finish):
            self.stage_dialogue_queue = list(lines)
            self.stage_dialogue_callback = on_finish
            self.advance_stage_dialogue()

        def advance_stage_dialogue(self):
            if self.stage_dialogue_queue:
                speaker, text = self.stage_dialogue_queue.pop(0)
                self.dialog.open(speaker, text)
            else:
                self.dialog.close()
                if self.stage_dialogue_callback:
                    cb = self.stage_dialogue_callback
                    self.stage_dialogue_callback = None
                    cb()

        # Spawn coordinates strictly outside all shelf collision blocks
        if self.defend_unlocked:
            spawn_x, spawn_y = 525, 175
        elif self.meat_done:
            spawn_x, spawn_y = 818, 175
        elif self.veg_done:
            spawn_x, spawn_y = 240, 260
        else:
            spawn_x, spawn_y = 495, 180

        self.terry = Terry(spawn_x, spawn_y, carrying=False)
        self.sprites = arcade.SpriteList()
        self.sprites.append(self.terry)
        self.sort_by_depth()

        # --- Interactive Indicators ---
        self.indicators = arcade.SpriteList()
        exclamation_tex = textures.ui_image("Exclamation Mark Symbol.png")
        lock_tex = textures.ui_image("Lock Symbol.png")

        # 1. Upper-Left Red Zone Marker (MEATS - Patio Walkway)
        self.meat_marker = arcade.Sprite(exclamation_tex, scale=0.20)
        self.meat_marker.center_x = 210
        self.meat_marker.base_y = 355
        self.meat_marker.center_y = self.meat_marker.base_y
        if not self.meat_done:
            self.indicators.append(self.meat_marker)

        # 2. Bottom-Right Red Zone Marker (VEGETABLES - Between Fruit Bins)
        self.veg_marker = arcade.Sprite(exclamation_tex, scale=0.20)
        self.veg_marker.center_x = 1050
        self.veg_marker.base_y = 75
        self.veg_marker.center_y = self.veg_marker.base_y
        if not self.veg_done:
            self.indicators.append(self.veg_marker)

        # 3. Center Green Zone Padlock (Middle of aisle)
        self.defend_lock = arcade.Sprite(lock_tex, scale=0.22)
        self.defend_lock.center_x = 630
        self.defend_lock.base_y = 75
        self.defend_lock.center_y = self.defend_lock.base_y
        self.indicators.append(self.defend_lock)

        # Padlock unlock timer (plays hop-unlock-fade if both are cleared)
        self.lock_anim_timer = 5.0 if self.defend_unlocked else 0.0

        self.footsteps = Footsteps(MARKET_STONE_AREAS)
        self.dialog = DialogBox()
        self.stage_dialogue_queue = []
        self.stage_dialogue_callback = None
        self.pause_menu = PauseMenu()
        self.settings_panel = SettingsPanel()
        self.widgets = [self.dialog, self.pause_menu, self.settings_panel]

        self.camera = arcade.camera.Camera2D(
            position=(WIDTH / 2, HEIGHT / 2),
            projection=arcade.LRBT(-WIDTH / 2, WIDTH / 2, -HEIGHT / 2, HEIGHT / 2),
            viewport=self.stage.viewport(),
        )
        self.relayout()

    def sort_by_depth(self):
        self.sprites.sort(key=lambda sprite: -sprite.ground_y)

    def relayout(self):
        super().relayout()
        if hasattr(self, "camera"):
            self.camera.viewport = self.stage.viewport()
        self.hint = self.stage.text(
            "WASD to move    Space to jump    Esc to pause",
            WIDTH / 2, 26, (238, 240, 246), 14,
            anchor_x="center", anchor_y="center",
        )

    def on_show_view(self):
        self.held.clear()
        self.relayout()

    def on_update(self, delta_time):
        if self.pause_menu.visible or self.settings_panel.visible:
            return

        delta_time = min(delta_time, 1 / 30)
        self.time_elapsed += delta_time

        if self.dialog.visible:
            self.dialog.update(delta_time)
            return

        # Player Movement
        dx = (arcade.key.D in self.held) - (arcade.key.A in self.held)
        dy = (arcade.key.W in self.held) - (arcade.key.S in self.held)
        self.terry.update_movement(
            delta_time, dx, dy, MARKET_WALK_BOUNDS, MARKET_OBSTACLES
        )
        self.footsteps.update(
            delta_time, bool(dx or dy) and not self.terry.jumping,
            self.terry.center_x, self.terry.ground_y
        )
        if dy:
            self.sort_by_depth()

        # Indicator Bobbing
        bob_offset = math.sin(self.time_elapsed * 4.0) * 6.0
        if not self.meat_done:
            self.meat_marker.center_y = self.meat_marker.base_y + bob_offset
        if not self.veg_done:
            self.veg_marker.center_y = self.veg_marker.base_y + bob_offset


        # Proximity Checks
        self.near_meat = (110 <= self.terry.center_x <= 310) and (230 <= self.terry.ground_y <= 480)
        self.near_veg = (1000 <= self.terry.center_x <= 1100) and (0 <= self.terry.ground_y <= 150)
        self.near_defend = (600 <= self.terry.center_x <= 660) and (0 <= self.terry.ground_y <= 150)

        # Context Prompts
        if self.near_meat:
            if not self.meat_done:
                self.hint.text = "Press Enter to gather prime meat!"
                self.meat_marker.alpha = 0
            else:
                self.hint.text = "Prime meat already secured!"
        elif self.near_veg:
            if not self.veg_done:
                self.hint.text = "Press Enter to gather fresh vegetables!"
                self.veg_marker.alpha = 0
            else:
                self.hint.text = "Vegetables already secured!"
        elif self.near_defend:
            if not self.defend_unlocked:
                self.hint.text = "Gather both meat and vegetables to unlock basket defense!"
            else:
                self.hint.text = "Press Enter to defend your basket and escape!"
        else:
            self.hint.text = "WASD to move    Space to jump    Esc to pause"
            if not self.meat_done:
                self.meat_marker.alpha = 255
            if not self.veg_done:
                self.veg_marker.alpha = 2555


    def on_draw(self):
        self.clear()

        # 1. World Layer in Camera Space
        self.camera.use()
        if self.bg_texture:
            arcade.draw_texture_rect(self.bg_texture, arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT))

        for character in self.sprites:
            character.draw_shadow()
        self.sprites.draw(pixelated=True)
        self.indicators.draw(pixelated=True)

        # 2. UI in Screen Space
        self.window.default_camera.use()
        self.hint.draw()

        if self.dialog.visible and getattr(self.dialog, "texture", None):
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
            self.held.clear()
            self.pause_menu.open()
            return
        # Advance stage dialog if active
        if self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.SPACE):
                if self.dialog.typing:
                    self.dialog.advance()
                else:
                    self.advance_stage_dialogue()
            return

        if key in (arcade.key.ENTER, arcade.key.NUM_ENTER):
            from .market_dash_catch import MarketCatchView

            # 1. Upper-Left: Meats
            if self.near_meat and not self.meat_done:
                self.held.clear()
                audio.play("ui_click")
                self.window.show_view(MarketCatchView(mode="meat", veg_done=self.veg_done, meat_done=self.meat_done))
                return

            # 2. Bottom-Right: Vegetables
            if self.near_veg and not self.veg_done:
                self.held.clear()
                audio.play("ui_click")
                self.window.show_view(MarketCatchView(mode="veg", veg_done=self.veg_done, meat_done=self.meat_done))
                return

            # 3. Center: Defense (Play pre-game warning dialogue before entering)
            if self.near_defend and self.defend_unlocked:
                self.held.clear()
                audio.play("ui_click")

                pre_defend_dialogue = [
                    ("Terry", "Wait... why is everyone suddenly staring at my basket?"),
                    ("Desperate Shopper", "Look! He's got the last prime steaks and fresh veggies! GET HIM!"),
                    ("Terry", "Oh no... they're swarming the exit!"),
                    ("Terry", "I'll have to use this frozen mackerel to defend myself and dash past them!"),
                ]

                def start_defend_game():
                    self.window.show_view(MarketCatchView(mode="defend", veg_done=self.veg_done, meat_done=self.meat_done))

                self.trigger_stage_dialogue(pre_defend_dialogue, start_defend_game)
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

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.settings_panel.on_mouse_drag(*self.canvas_point(x, y))

    def on_mouse_release(self, x, y, button, modifiers):
        self.settings_panel.on_mouse_release()

    def on_mouse_press(self, x, y, button, modifiers):
        canvas_x, canvas_y = self.canvas_point(x, y)
        if self.settings_panel.on_mouse_press(canvas_x, canvas_y, button):
            return
        if self.pause_menu.visible:
            self.run_action(self.pause_menu.on_mouse_press(canvas_x, canvas_y, button))
            return
        if self.dialog.visible:
            if self.dialog.typing:
                self.dialog.advance()
            else:
                self.advance_stage_dialogue()
            return

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

    def trigger_stage_dialogue(self, lines, on_finish):
        self.stage_dialogue_queue = list(lines)
        self.stage_dialogue_callback = on_finish
        self.advance_stage_dialogue()

    def advance_stage_dialogue(self):
        if self.stage_dialogue_queue:
            speaker, text = self.stage_dialogue_queue.pop(0)
            self.dialog.open(speaker, text)
        else:
            self.dialog.close()
            if self.stage_dialogue_callback:
                cb = self.stage_dialogue_callback
                self.stage_dialogue_callback = None
                cb()