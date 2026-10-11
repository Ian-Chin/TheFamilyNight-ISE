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
    """Explorable market scene with free WASD movement, obstacles, and unlockable minigame trigger."""

    def __init__(self, unlocked=False):
        super().__init__()
        self.game_unlocked = unlocked
        self.near_circle = False
        self.held = set()
        self.fade_clock = 0.0
        self.walking_in = False   # Set False so WASD works immediately
        self.time_elapsed = 0.0

        # Background image
        self.bg_texture = textures.background("market-dash/Scene 2.4 - market interior.jpg")

        # If already unlocked (retry state), spawn Terry closer to the stall patio
        spawn_x = 240 if self.game_unlocked else 495
        spawn_y = 300 if self.game_unlocked else 180
        self.terry = Terry(spawn_x, spawn_y, carrying=False)
        self.sprites = arcade.SpriteList()
        self.sprites.append(self.terry)
        self.sort_by_depth()

        # Lock indicator on the green checkered tiles in the patio
        self.indicators = arcade.SpriteList()
        self.lock_sprite = None

        if not self.game_unlocked:
            try:
                lock_tex = textures.ui_image("Lock Symbol.png")
            except Exception:
                lock_tex = textures.ui_image("Lock_Symbol.png")

            self.lock_sprite = arcade.Sprite(lock_tex, scale=0.22)
            self.lock_sprite.center_x = 185
            self.lock_sprite.base_y = 405
            self.lock_sprite.center_y = self.lock_sprite.base_y
            self.indicators.append(self.lock_sprite)

        # --- REQUIRED WIDGETS (Do not omit these lines) ---
        self.footsteps = Footsteps(MARKET_STONE_AREAS)
        self.dialog = DialogBox()
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

    def on_draw(self):
        self.clear()
        viewport = self.stage.viewport()

        if self.bg_texture:
            arcade.draw_texture_rect(
                self.bg_texture,
                cover_rect(self.bg_texture, viewport)
            )
        else:
            arcade.draw_rect_filled(
                arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT),
                (40, 44, 52)
            )

        # Sprites & Lock in Camera Space
        self.camera.use()
        for character in self.sprites:
            character.draw_shadow()
        self.sprites.draw(pixelated=True)
        self.indicators.draw(pixelated=True)

        # UI & HUD
        self.window.default_camera.use()
        self.hint.draw()

        if self.dialog.visible:
            self.dialog.draw()

        if not self.settings_panel.visible:
            self.pause_menu.draw()
        self.settings_panel.draw()

    def on_update(self, delta_time):
        if self.pause_menu.visible or self.settings_panel.visible:
            return

        delta_time = min(delta_time, 1 / 30)

        if self.dialog.visible:
            self.dialog.update(delta_time)
            return

        # Player free movement
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

        # Handle padlock bobbing & unlocking animation only if still locked
        if not self.game_unlocked and self.lock_sprite:
            self.time_elapsed += delta_time
            if not hasattr(self, "lock_anim_timer"):
                bob_offset = math.sin(self.time_elapsed * 4.0) * 5.0
                self.lock_sprite.center_y = self.lock_sprite.base_y + bob_offset

            if hasattr(self, "lock_anim_timer") and self.lock_anim_timer > 0:
                self.lock_anim_timer -= delta_time
                if self.lock_anim_timer <= 0:
                    self.game_unlocked = True
                    self.indicators.clear()  # Remove lock sprite once unlocked!
                    self.lock_sprite = None
                elif self.lock_anim_timer <= 2.0:
                    try:
                        self.lock_sprite.texture = textures.ui_image("Lock_unlocked.png")
                    except Exception:
                        pass
                    self.lock_sprite.scale = 0.22
                    self.lock_sprite.center_y = self.lock_sprite.base_y
                else:
                    progress = 4.0 - self.lock_anim_timer
                    pop_curve = math.sin(progress * math.pi)
                    self.lock_sprite.scale = 0.22 + (pop_curve * 0.08)
                    self.lock_sprite.center_y = self.lock_sprite.base_y + (pop_curve * 14.0)

        # Generous patio detection box
        in_circle_x = 50 <= self.terry.center_x <= 360
        in_circle_y = 180 <= self.terry.ground_y <= 530
        self.near_circle = in_circle_x and in_circle_y

        if self.near_circle:
            if not self.game_unlocked:
                if hasattr(self, "lock_anim_timer") and self.lock_anim_timer > 0:
                    self.hint.text = "Unlocking..."
                else:
                    self.hint.text = "Press Enter to unlock the produce stall!"
            else:
                self.hint.text = "Press Enter to start catching ingredients!"
        else:
            self.hint.text = "WASD to move    Space to jump    Esc to pause"

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

        if self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.SPACE):
                self.dialog.advance()
            return

        # Mini-game trigger (strictly Enter keys)
        if key in (arcade.key.ENTER, arcade.key.NUM_ENTER) and self.near_circle:
            if self.game_unlocked:
                self.held.clear()
                audio.play("ui_click")
                from .market_dash_catch import MarketCatchView
                self.window.show_view(MarketCatchView())
                return

            if not hasattr(self, "lock_anim_timer"):
                audio.play("ui_click")
                self.lock_anim_timer = 4.0
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
            self.dialog.advance()

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