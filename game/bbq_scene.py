"""The BBQ scene.

Terry walks in down the garden path from above the canvas while the opening
black fades away, settles by the dinner table and says his opening line. The
player takes over once that line is done.
"""
import math
import arcade

from . import textures
from . import audio
from .audio import Footsteps
from .config import (
    BBQ_SCENE_BG, BBQ_SCENE_EMPTY_BG, CHAO_ENTRY_Y, CHAO_FADE_IN, CHAO_OBSTACLES,
    BBQ_OPENING_DIALOG, CHAO_PATH_X, CHAO_STONE_AREAS, CHAO_STOP_Y,
    CHAO_WALK_BOUNDS, HEIGHT, WIDTH,
)
from .dialogue import DialogBox
from .options import SettingsPanel
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


class BbqView(StageView):
    """Scripted entrance: fade up from black as Terry walks down the path."""

    def __init__(self, chop_unlocked=False, grill_unlocked=False, grill_completed = False):
        super().__init__()
        
        # Track our two game states
        self.chop_unlocked = chop_unlocked
        self.grill_unlocked = grill_unlocked
        self.grill_completed = grill_completed
        
        if self.chop_unlocked:
            self.background = textures.background(BBQ_SCENE_EMPTY_BG)
        else:
            self.background = textures.background(BBQ_SCENE_BG)

        start_y = CHAO_STOP_Y if self.chop_unlocked else CHAO_ENTRY_Y
        self.terry = Terry(CHAO_PATH_X, start_y)
        
        self.sprites = arcade.SpriteList()
        self.sprites.append(self.terry)
        self.sort_by_depth()

        if self.chop_unlocked:
            self.fade_clock = CHAO_FADE_IN  
            self.walking_in = False         
        else:
            self.fade_clock = 0.0
            self.walking_in = True

        # --- Setup Floating Indicators ---
        self.indicators = arcade.SpriteList()
        self.time_elapsed = 0.0  
        
        # 1. Exclamation Mark 
        exclamation_tex = textures.ui_image("Exclamation Mark Symbol.png")
        self.table_marker = arcade.Sprite(exclamation_tex, scale=0.2)
        self.table_marker.center_x = 229
        self.table_marker.base_y = 450 
        self.table_marker.center_y = self.table_marker.base_y
        
        if not self.chop_unlocked:
            self.indicators.append(self.table_marker)

        # 2. Lock on the Grilling Machine
        if not self.grill_completed:
            self.grill_lock = arcade.Sprite(textures.ui_image("Lock Symbol.png"), scale=0.2)
            self.grill_lock.center_x = 880  
            self.grill_lock.base_y = 340
            self.grill_lock.center_y = self.grill_lock.base_y
            
            if self.grill_unlocked:
                self.grill_lock_timer = 5.0  # Animate it popping open!
            
            self.indicators.append(self.grill_lock)

        # 3. Lock on the Chopping Board
        self.board_lock = arcade.Sprite(textures.ui_image("Lock Symbol.png"), scale=0.2)
        self.board_lock.center_x = 1000 
        self.board_lock.base_y = 330
        self.board_lock.center_y = self.board_lock.base_y
        
        if self.chop_unlocked and not self.grill_unlocked:
            # Just came from the prep table! Animate the board unlock.
            self.board_lock_timer = 5.0 
            self.indicators.append(self.board_lock)
        elif not self.chop_unlocked:
            # Still locked completely
            self.indicators.append(self.board_lock)
        # (If BOTH are true, we don't append the board_lock at all because it's already gone!)

        # --- Base Scene State ---
        self.footsteps = Footsteps(CHAO_STONE_AREAS)
        self.typing_player = None
        self.held = set()
        self.near_table = False
        self.near_grill = False
        self.near_board = False
        self.panel = None

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

    def on_show_view(self):
        audio.ambience().start()

    def on_hide_view(self):
        # The garden is the only place with birds, so they leave with it.
        audio.ambience().stop()
        self.stop_typing_sound()

    def sort_by_depth(self):
        """Back to front, so whoever stands lower down overlaps the rest."""
        self.sprites.sort(key=lambda sprite: -sprite.ground_y)

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
        for character in self.sprites:
            character.draw_shadow()
        self.sprites.draw(pixelated=True)

        # --- UPDATE: Only draw indicators if the player has control ---
        if self.playing:
            self.indicators.draw(pixelated=True)
        # --------------------------------------------------------------
        
        self.window.default_camera.use()    

        if self.playing:
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

        self.dialog.draw()
        # Settings is reached through the pause menu, which stays open behind
        # it; the glass is see-through enough that both at once is a mess.
        if not self.settings_panel.visible:
            self.pause_menu.draw()
        self.settings_panel.draw()

    @property
    def playing(self):
        """True once the scripted entrance and its dialogue are out of the way."""
        return not self.walking_in and not self.dialog.visible

    def start_opening_dialog(self):
        audio.play("dialog_open")
        self.dialog.open(*BBQ_OPENING_DIALOG)
        self.typing_player = audio.play("dialog_type", loop=True)

    def stop_typing_sound(self):
        audio.bank().stop(self.typing_player)
        self.typing_player = None

    def on_update(self, delta_time):
        audio.ambience().update(delta_time)

        if self.pause_menu.visible or self.settings_panel.visible or self.panel:
            return

        delta_time = min(delta_time, 1 / 30)
        self.fade_clock += delta_time

        if self.dialog.visible:
            self.dialog.update(delta_time)
            if not self.dialog.typing:
                self.stop_typing_sound()
            return

        if self.walking_in:
            self.terry.update_movement(
                delta_time, 0, -1, (0, WIDTH, 0, CHAO_ENTRY_Y + self.terry.height),
            )
            self.footsteps.update(
                delta_time, True, self.terry.center_x, self.terry.ground_y,
            )
            if self.terry.ground_y <= CHAO_STOP_Y:
                self.terry.ground_y = CHAO_STOP_Y
                self.walking_in = False
                self.start_opening_dialog()
            self.sort_by_depth()
            return

        dx = (arcade.key.D in self.held) - (arcade.key.A in self.held)
        dy = (arcade.key.W in self.held) - (arcade.key.S in self.held)
        self.terry.update_movement(
            delta_time, dx, dy, CHAO_WALK_BOUNDS, CHAO_OBSTACLES,
        )
        self.footsteps.update(
            delta_time, bool(dx or dy) and not self.terry.jumping,
            self.terry.center_x, self.terry.ground_y,
        )
        if dy:
            self.sort_by_depth()

        # --- Animate the indicators ---
        if self.playing:
            self.time_elapsed += delta_time
            
            if not self.chop_unlocked:
                bob_offset = math.sin(self.time_elapsed * 4.0) * 6.0 
                self.table_marker.center_y = self.table_marker.base_y + bob_offset
                
            # --- Stage the Chopping Board unlocking ---
            if hasattr(self, 'board_lock_timer') and self.board_lock_timer > 0:
                self.board_lock_timer -= delta_time
                if self.board_lock_timer <= 0:
                    self.board_lock.alpha = 0  
                elif self.board_lock_timer <= 2.0:
                    self.board_lock.alpha = int(255 * (self.board_lock_timer / 2.0))
                    self.board_lock.scale = 0.2
                    self.board_lock.center_y = self.board_lock.base_y
                elif self.board_lock_timer <= 4.0:
                    self.board_lock.texture = textures.ui_image("Lock_unlocked.png")
                    self.board_lock.alpha = 255
                    self.board_lock.scale = 0.2
                    self.board_lock.center_y = self.board_lock.base_y
                else:
                    self.board_lock.alpha = 255
                    progress = 5.0 - self.board_lock_timer 
                    pop_curve = math.sin(progress * math.pi)
                    self.board_lock.scale = 0.2 + (pop_curve * 0.08)
                    self.board_lock.center_y = self.board_lock.base_y + (pop_curve * 15.0)

            # --- Stage the Grilling Machine unlocking ---
            if hasattr(self, 'grill_lock_timer') and self.grill_lock_timer > 0:
                self.grill_lock_timer -= delta_time
                if self.grill_lock_timer <= 0:
                    self.grill_lock.alpha = 0  
                elif self.grill_lock_timer <= 2.0:
                    self.grill_lock.alpha = int(255 * (self.grill_lock_timer / 2.0))
                    self.grill_lock.scale = 0.2
                    self.grill_lock.center_y = self.grill_lock.base_y
                elif self.grill_lock_timer <= 4.0:
                    self.grill_lock.texture = textures.ui_image("Lock_unlocked.png")
                    self.grill_lock.alpha = 255
                    self.grill_lock.scale = 0.2
                    self.grill_lock.center_y = self.grill_lock.base_y
                else:
                    self.grill_lock.alpha = 255
                    progress = 5.0 - self.grill_lock_timer 
                    pop_curve = math.sin(progress * math.pi)
                    self.grill_lock.scale = 0.2 + (pop_curve * 0.08)
                    self.grill_lock.center_y = self.grill_lock.base_y + (pop_curve * 15.0)

            # --- Check rectangular proximity to the zones ---
            # 1. Big Table
            in_table_x = 90 <= self.terry.center_x <= 368
            in_table_y = 208 <= self.terry.ground_y <= 595
            self.near_table = in_table_x and in_table_y
            
            # 2. Grilling Machine (Left side of the stone counter)
            in_grill_x = 800 <= self.terry.center_x <= 950
            in_grill_y = 180 <= self.terry.ground_y <= 450
            self.near_grill = in_grill_x and in_grill_y

            # 3. Chopping Board (Right side of the stone counter)
            in_board_x = 950 <= self.terry.center_x <= 1150
            in_board_y = 180 <= self.terry.ground_y <= 450
            self.near_board = in_board_x and in_board_y
            
            # --- Update UI Hints based on location ---
            if self.near_table:
                if not self.chop_unlocked:
                    self.hint.text = "Press E to prepare food"
                    self.table_marker.alpha = 0  
                else:
                    self.hint.text = "The food has been prepped!"
            elif self.near_grill:
                if not self.grill_unlocked:
                    self.hint.text = "This section hasn't unlocked yet..."
                elif not self.grill_completed:
                    self.hint.text = "Press Enter to start grilling!"
                else:
                    self.hint.text = "The BBQ is completely finished!"
            elif self.near_board:
                if not self.chop_unlocked:
                    self.hint.text = "This section hasn't unlocked yet..."
                elif not self.grill_unlocked:
                    self.hint.text = "Press Enter to start chopping"
                else:
                    self.hint.text = "The chopping is completely finished!"
            else:
                self.hint.text = "WASD to move    Space to jump    Esc to pause"
                if not self.chop_unlocked:
                    self.table_marker.alpha = 255

    def on_key_press(self, key, modifiers):
        # Settings first: it can be opened from the pause menu, which stays
        # visible underneath it.
        if self.settings_panel.visible:
            if self.settings_panel.on_key_press(key) == "close":
                self.settings_panel.close()
            return

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

        # --- Transition to the BBQ Prep Scene ---
        if key == arcade.key.E and self.near_table and self.playing and not self.chop_unlocked:
            self.held.clear() 
            from .bbq_prep_scene import BBQPrepView
            self.window.show_view(BBQPrepView())
            return
            
        # --- Transition to the Chopping Scene ---
        if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.RETURN) and self.near_board and self.playing and self.chop_unlocked and not self.grill_unlocked:
            self.held.clear()
            
            # Play a click sound so you immediately know it registered
            from . import audio
            audio.play("ui_click")
            
            # Transition to the actual chopping scene!
            from .chopping_scene import ChoppingView
            self.window.show_view(ChoppingView())
            return

        # --- Transition to the Grilling Scene ---
        if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.RETURN) and self.near_grill and self.playing and self.grill_unlocked and not self.grill_completed:
            self.held.clear()
            from . import audio
            audio.play("ui_click")
            from .grilling_scene import GrillingView
            self.window.show_view(GrillingView())
            return
        # ------------------------------------------------

        if self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER):
                self.stop_typing_sound()
                self.dialog.advance()
            return

        if self.walking_in:
            if key == arcade.key.SPACE:
                # Skip the entrance.
                self.fade_clock = CHAO_FADE_IN
                self.terry.ground_y = CHAO_STOP_Y
                self.walking_in = False
                self.sort_by_depth()
                self.start_opening_dialog()
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
        if self.panel:
            # Any click dismisses an open popup.
            self.panel = None
            return
        if self.dialog.visible or self.walking_in:
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
        elif action == "settings":
            self.settings_panel.open()
        elif action == "menu":
            from .views import MenuView

            self.window.show_view(MenuView())
        elif action == "quit":
            self.window.close()