import math
import arcade

from ...core import textures
from ...core.backdrop import Backdrop
from ...core import audio
from ...config import HEIGHT, WIDTH
from ...core.dialogue import DialogBox
from ...core.options import SettingsPanel
from ...core.pause import PauseMenu
from ..menu.view import MenuView
from ...core.stage import StageView
from ...core.audio import Footsteps
from ...core.sprites import Terry
from .common import (
    MARKET_WALK_BOUNDS, MARKET_OBSTACLES,
    MARKET_STONE_AREAS, market_ambience,
)
from ...core.widgets import TitleCard, QuestPanel, Portraits


class MarketStageView(StageView):
    """Explorable market with 2 Red Exclamation zones and 1 Central Padlock defense zone."""
    def __init__(self, veg_done=False, meat_done=False, last_completed=None):
        super().__init__()
        self.veg_done = veg_done
        self.meat_done = meat_done
        self.defend_unlocked = self.veg_done and self.meat_done
        self.walking_player = None

      
        self.show_title_card = not (self.veg_done or self.meat_done)
        self.title_card = TitleCard(
            kicker="S C E N E   1",
            title="Market Dash",
            tagline="Gather and Defend Ingredients"
        )

        self.footsteps = Footsteps(MARKET_STONE_AREAS)
        self.dialog = DialogBox()
        self.pause_menu = PauseMenu()
        self.settings_panel = SettingsPanel()

       
        market_quests = (
            ("veg", "Gather Vegetables", "Head to the vegetable stalls", False),
            ("meat", "Gather Prime Meat", "Head to the meat deli counter", False),
            ("defend", "Defend Ingredients", "Escape through checkout", False),
        )

        self.quests = QuestPanel(quests=market_quests)

        if self.veg_done:
            self.quests.complete("veg")

        if self.meat_done:
            self.quests.complete("meat")

        if not self.defend_unlocked:
            self.quests.set_progress("defend", "Locked")
        else:
            self.quests.set_progress("defend", "Unlocked!")

        self.near_veg = False
        self.near_meat = False
        self.near_defend = False

        self.held = set()
        self.time_elapsed = 0.0

        self.backdrop = Backdrop("market-dash/Scene 2.4 - market interior.jpg")

     
        if self.defend_unlocked:
            spawn_x, spawn_y = 630, 90
        elif last_completed == "veg" or (self.veg_done and not self.meat_done):
            spawn_x, spawn_y = 1050, 75
        elif last_completed == "meat" or (self.meat_done and not self.veg_done):
            spawn_x, spawn_y = 210, 335
        else:
            spawn_x, spawn_y = 495, 180

    
        self.terry = Terry(spawn_x, spawn_y, carrying=False)
        self.sprites = arcade.SpriteList()
        self.sprites.append(self.terry)
        self.sort_by_depth()

      
        try:
            self.terry_portrait = textures.character("terry-idle-1.png")
        except Exception:
            self.terry_portrait = self.terry.texture

        try:
            self.shopper_portrait = textures.character("Unc John.png")
        except Exception:
            self.shopper_portrait = None

        self.portraits = Portraits(self.terry_portrait)
        self.current_speaker = None
        self.current_partner = None

     
        self.widgets = [
            self.dialog, self.pause_menu, self.settings_panel,
            self.title_card, self.quests, self.portraits
        ]

      
        self.indicators = arcade.SpriteList()
        exclamation_tex = textures.ui_image("Exclamation Mark Symbol.png")
        lock_tex = textures.ui_image("Lock Symbol.png")

        self.meat_marker = arcade.Sprite(exclamation_tex, scale=0.20)
        self.meat_marker.center_x = 210
        self.meat_marker.base_y = 355
        self.meat_marker.center_y = self.meat_marker.base_y
        if not self.meat_done:
            self.indicators.append(self.meat_marker)

        self.veg_marker = arcade.Sprite(exclamation_tex, scale=0.20)
        self.veg_marker.center_x = 1050
        self.veg_marker.base_y = 75
        self.veg_marker.center_y = self.veg_marker.base_y
        if not self.veg_done:
            self.indicators.append(self.veg_marker)

        self.defend_lock = arcade.Sprite(lock_tex, scale=0.22)
        self.defend_lock.center_x = 630
        self.defend_lock.base_y = 75
        self.defend_lock.center_y = self.defend_lock.base_y
        self.indicators.append(self.defend_lock)

        self.played_unlock_sound = False
        if last_completed == "defend_retry":
            self.lock_animating = False
            self.lock_anim_timer = 0.0
            if self.defend_lock in self.indicators:
                self.indicators.remove(self.defend_lock)
        elif self.defend_unlocked:
            self.lock_animating = True
            self.lock_anim_timer = 3.6
        else:
            self.lock_animating = False
            self.lock_anim_timer = 0.0

        self.stage_dialogue_queue = []
        self.stage_dialogue_callback = None
        self.stage_dialogue_bg = None

        self.camera = arcade.camera.Camera2D(
            position=(WIDTH / 2, HEIGHT / 2),
            projection=arcade.LRBT(-WIDTH / 2, WIDTH / 2, -HEIGHT / 2, HEIGHT / 2),
            viewport=self.stage.viewport(),
        )
        self.relayout()

    def start_ambience(self):
        market_ambience().start()

    def sort_by_depth(self):
        self.sprites.sort(key=lambda sprite: -sprite.ground_y)

    def relayout(self):
        super().relayout()
        if hasattr(self, "camera"):
            self.camera.viewport = self.stage.viewport()
        if hasattr(self, "title_card"):
            self.title_card.layout(self.stage)
        if hasattr(self, "quests"):
            self.quests.layout(self.stage)
        if hasattr(self, "portraits"):
            self.portraits.layout(self.stage)
        self.hint = self.stage.text(
            "WASD to move    Space to jump    Esc to pause",
            WIDTH / 2, 26, (238, 240, 246), 14,
            anchor_x="center", anchor_y="center",
        )

    def on_show_view(self):
        self.held.clear()
        self.relayout()
        self.start_ambience()
        
    def on_hide_view(self):                                                                                      
        if self.walking_player is not None:                                                                      
            audio.stop(self.walking_player)                                                                      
            self.walking_player = None                                                                           
        self.backdrop.stop() 

    def trigger_stage_dialogue(self, lines, on_finish):
        self.stage_dialogue_queue = list(lines)
        self.stage_dialogue_callback = on_finish
        self.advance_stage_dialogue()

    def advance_stage_dialogue(self):
        if self.stage_dialogue_queue:
            item = self.stage_dialogue_queue.pop(0)
            speaker, text = item[0], item[1]
            self.stage_dialogue_bg = item[2] if len(item) > 2 else None

           
            self.current_speaker = "left" if speaker == "Terry" else "right"
            self.current_partner = self.shopper_portrait

            self.dialog.open(speaker, text)
        else:
            self.dialog.close()
            self.stage_dialogue_bg = None
            self.current_speaker = None
            self.current_partner = None
            if self.stage_dialogue_callback:
                cb = self.stage_dialogue_callback
                self.stage_dialogue_callback = None
                cb()

    def on_update(self, delta_time):
        market_ambience().update(delta_time)
        if self.pause_menu.visible or self.settings_panel.visible:
            return

        delta_time = min(delta_time, 1 / 30)
        self.time_elapsed += delta_time
        self.backdrop.update(delta_time)

       
        if self.lock_animating:
            self.lock_anim_timer -= delta_time

            if self.lock_anim_timer <= 0:
                self.lock_animating = False
                self.defend_lock.alpha = 0
                if self.defend_lock in self.indicators:
                    self.indicators.remove(self.defend_lock)

                pre_defend_dialogue = [
                    ("Terry", "Phew! That's the last item on the list. Time to head to the counter."),
                    ("Cashier", "Beep... beep... That'll be—wait, congratulations young man!"),
                    ("Cashier", "You grabbed our lucky clearance bundle! That's a 50 percent discount on your entire basket!"),
                    ("Terry", "Fifty percent off?! Half price for all this prime meat and fresh veg?! Today is my lucky day!"),
                    ("Terry", "Paid and packed. All that's left is to walk out those front doors..."),
                    ("Terry", "Wait a minute... look at that crowd in front of the exit doors."),
                    ("Terry", "They're still in a complete frenzy, fighting over every scrap in the aisles!"),
                    ("Terry", "If I rush in recklessly and crash into them, my groceries are going to spill everywhere..."),
                    ("Terry", "And with all these shoppers around, someone will definitely scoop up my fallen groceries in the chaos!"),
                    (
                        "Terry",
                        "Good thing I kept this frozen Pacific Mackerel handy. Solid as iron, ice-cold, and ready for action.",
                        textures.background("market-dash/fish obtained.jpg")
                    ),
                    ("Terry", "I just need to weave past the mob, keep my basket safe, and break through the exit doors!"),
                    ("Terry", "Alright, let's get out of here in one piece!")
                ]

                def start_defend_game():
                    from .catch import MarketCatchView
                    self.window.show_view(MarketCatchView(mode="defend", veg_done=self.veg_done, meat_done=self.meat_done))

                self.trigger_stage_dialogue(pre_defend_dialogue, start_defend_game)
                return

            elif self.lock_anim_timer <= 1.0:
                self.defend_lock.alpha = max(0, int(255 * (self.lock_anim_timer / 1.0)))
                self.defend_lock.scale = 0.22
                self.defend_lock.center_y = self.defend_lock.base_y

            elif self.lock_anim_timer <= 2.0:
                try:
                    self.defend_lock.texture = textures.ui_image("Lock_unlocked.png")
                except Exception:
                    pass
                self.defend_lock.alpha = 255
                self.defend_lock.scale = 0.22
                self.defend_lock.center_y = self.defend_lock.base_y

            elif self.lock_anim_timer <= 3.0:
                if not self.played_unlock_sound:
                    self.played_unlock_sound = True
                    audio.play("unlocked_sound")
                progress = 3.0 - self.lock_anim_timer
                pop_curve = math.sin(progress * math.pi)
                self.defend_lock.scale = 0.22 + (pop_curve * 0.08)
                self.defend_lock.center_y = self.defend_lock.base_y + (pop_curve * 18.0)

            else:
                self.defend_lock.scale = 0.22
                self.defend_lock.center_y = self.defend_lock.base_y

            return

                                                                              
        if self.dialog.visible:                                                                                  
            if self.walking_player is not None:                                                                  
                audio.stop(self.walking_player)                                                                  
                self.walking_player = None                                                                       
            self.dialog.update(delta_time)                                                                       
            return 

       
        dx = (arcade.key.D in self.held) - (arcade.key.A in self.held)
        dy = (arcade.key.W in self.held) - (arcade.key.S in self.held)
        self.terry.update_movement(
            delta_time, dx, dy, MARKET_WALK_BOUNDS, MARKET_OBSTACLES
        )
        
        moving = bool(dx or dy) and not self.terry.jumping
        if moving:
            if self.walking_player is None:
                self.walking_player = audio.play("walking", loop=True)
        else:
            if self.walking_player is not None:
                audio.stop(self.walking_player)
                self.walking_player = None


        if dy:
            self.sort_by_depth()

       
        bob_offset = math.sin(self.time_elapsed * 4.0) * 6.0
        if not self.meat_done:
            self.meat_marker.center_y = self.meat_marker.base_y + bob_offset
        if not self.veg_done:
            self.veg_marker.center_y = self.veg_marker.base_y + bob_offset

       
        self.near_meat = (110 <= self.terry.center_x <= 310) and (230 <= self.terry.ground_y <= 480)
        self.near_veg = (1000 <= self.terry.center_x <= 1100) and (0 <= self.terry.ground_y <= 150)
        self.near_defend = (600 <= self.terry.center_x <= 660) and (0 <= self.terry.ground_y <= 150)

       
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
                self.veg_marker.alpha = 255

        if self.show_title_card:
            self.title_card.update(delta_time)
            if self.title_card.finished:
                self.show_title_card = False

    def on_draw(self):
        self.clear()

       
        self.camera.use()

        if self.dialog.visible and self.stage_dialogue_bg:
            arcade.draw_texture_rect(self.stage_dialogue_bg, arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT))
        elif self.backdrop:
            arcade.draw_texture_rect(self.backdrop.texture, arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT))

        if not (self.dialog.visible and self.stage_dialogue_bg):
            for character in self.sprites:
                character.draw_shadow()
            
            self.sprites.draw(pixelated=True)
            self.indicators.draw(pixelated=True)

     
        self.window.default_camera.use()
        self.hint.draw()

        
        if not self.dialog.visible and not self.pause_menu.visible and not self.settings_panel.visible:
          
            plate = self.quests.plate_rect()
            arcade.draw_rect_filled(plate, (12, 10, 14, 215))
            arcade.draw_rect_outline(plate, (180, 140, 90, 160), max(1, 2 * self.stage.scale))
            self.quests.draw()

        if self.show_title_card:
            self.title_card.draw()

      
        if self.dialog.visible and self.current_speaker:
            self.portraits.draw(partner=self.current_partner, speaking=self.current_speaker)

       
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

        if self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.SPACE):
                if self.dialog.typing:
                    self.dialog.advance()
                else:
                    self.advance_stage_dialogue()
            return

        if self.lock_animating:
            return

        if key in (arcade.key.ENTER, arcade.key.NUM_ENTER):
            from .catch import MarketCatchView

            if self.near_meat and not self.meat_done:
                self.held.clear()
                audio.play("ui_click")
                self.window.show_view(MarketCatchView(mode="meat", veg_done=self.veg_done, meat_done=self.meat_done))
                return

            if self.near_veg and not self.veg_done:
                self.held.clear()
                audio.play("ui_click")
                self.window.show_view(MarketCatchView(mode="veg", veg_done=self.veg_done, meat_done=self.meat_done))
                return

            if self.near_defend:
                if not self.defend_unlocked:
                    audio.play("locked_sound")
                    return
                else:
                    self.held.clear()
                    from .catch import MarketCatchView
                    self.window.show_view(MarketCatchView(mode="defend", veg_done=self.veg_done, meat_done=self.meat_done))
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

        if self.dialog.visible and button == arcade.MOUSE_BUTTON_LEFT:
            if self.dialog.typing:
                self.dialog.advance()
            else:
                self.advance_stage_dialogue()

    def run_action(self, action):
        if action == "resume":
            self.pause_menu.close()
        elif action == "settings":
            self.settings_panel.open()
        elif action == "menu":
            self.stop_ambience()
            from ..menu.view import MenuView
            self.window.show_view(MenuView())
        elif action == "quit":
            self.stop_ambience()
            self.window.close()

    def stop_ambience(self):
        market_ambience().stop()