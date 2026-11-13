import math
import random
import arcade

from ...core import achievements, audio, textures
from ...config import HEIGHT, WIDTH
from .config import (
    CHOP_CARROT_BG_1, CHOP_CARROT_BG_2, CHOP_CARROT_BG_3, CHOP_CARROT_RUINED,
    CHOP_EGGPLANT_BG_1, CHOP_EGGPLANT_BG_2, CHOP_EGGPLANT_BG_3, CHOP_EGGPLANT_BG_4,
    CHOP_EGGPLANT_RUINED, CHOP_FAILED_BG, CHOP_FINISH_BG, CHOP_MEAT_BG_1,
    CHOP_MEAT_BG_2, CHOP_MEAT_BG_3, CHOP_MEAT_RUINED, CHOP_ONION_BG_1, CHOP_ONION_BG_2,
    CHOP_ONION_BG_3, CHOP_ONION_RUINED, CHOP_PEPPER_BG_1, CHOP_PEPPER_BG_2,
    CHOP_PEPPER_BG_3, CHOP_PEPPER_RUINED,
)
from ...core.dialogue import DialogBox
from ...core.stage import StageView
from .hub import BbqView
from ...core.widgets import Portraits
from ...core.pause import PauseMenu

def cover_rect(texture, rect):
    scale = max(rect.width / texture.width, rect.height / texture.height)
    return arcade.XYWH(rect.x, rect.y, texture.width * scale, texture.height * scale)

# --- NEW: Light Slash Visual Effect ---
class SlashEffect:
    def __init__(self, x, y):
        self.x = x + random.uniform(-15, 15)
        self.y = y + random.uniform(-15, 15)
        self.lifetime = 0.15
        self.age = 0.0
        
        self.angle = random.uniform(120, 150)
        self.length = random.uniform(120, 160)

    def update(self, dt):
        self.age += dt
        self.length += 400 * dt  

    def draw(self):
        progress = self.age / self.lifetime
        if progress >= 1.0:
            return
            
        alpha = max(0, int(255 * (1.0 - progress)))
        thickness = max(1, int(15 * (1.0 - (progress ** 1.5))))
        
        angle_rad = math.radians(self.angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        x1 = self.x - cos_a * (self.length / 2)
        y1 = self.y - sin_a * (self.length / 2)
        x2 = self.x + cos_a * (self.length / 2)
        y2 = self.y + sin_a * (self.length / 2)
        
        arcade.draw_line(x1, y1, x2, y2, (255, 255, 150, int(alpha * 0.4)), thickness + 8)
        arcade.draw_line(x1, y1, x2, y2, (255, 255, 255, alpha), thickness)

    @property
    def is_dead(self):
        return self.age >= self.lifetime

# --- Food Particle System for Chopping Visual Effects ---
class FoodParticle:
    def __init__(self, x, y, color):
        self.x = x + random.uniform(-30, 30)
        self.y = y + random.uniform(-10, 20)
        
        self.vx = random.uniform(-300, 300)
        self.vy = random.uniform(150, 450)
        
        self.color = color
        self.size = random.uniform(8, 16)
        self.angle = random.uniform(0, 360)
        self.spin = random.uniform(-300, 300)
        
        self.lifetime = random.uniform(0.4, 0.8)
        self.age = 0.0

    def update(self, dt):
        self.age += dt
        
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy -= 1200 * dt  
        self.angle += self.spin * dt

    def draw(self):
        progress = self.age / self.lifetime
        alpha = max(0, int(255 * (1.0 - progress)))
        
        if alpha > 0:
            rect = arcade.XYWH(self.x - self.size/2, self.y - self.size/2, self.size, self.size)
            arcade.draw_rect_filled(rect, (*self.color, alpha), tilt_angle=self.angle)

    @property
    def is_dead(self):
        return self.age >= self.lifetime
# -------------------------------------------------------------

class ChoppingView(StageView):
    def __init__(self):
        super().__init__()
        
        self.backgrounds = [
            textures.background(CHOP_MEAT_BG_1), textures.background(CHOP_MEAT_BG_2), textures.background(CHOP_MEAT_BG_3), textures.background(CHOP_MEAT_RUINED),
            textures.background(CHOP_CARROT_BG_1), textures.background(CHOP_CARROT_BG_2), textures.background(CHOP_CARROT_BG_3), textures.background(CHOP_CARROT_RUINED),
            textures.background(CHOP_ONION_BG_1), textures.background(CHOP_ONION_BG_2), textures.background(CHOP_ONION_BG_3), textures.background(CHOP_ONION_RUINED),
            textures.background(CHOP_PEPPER_BG_1), textures.background(CHOP_PEPPER_BG_2), textures.background(CHOP_PEPPER_BG_3), textures.background(CHOP_PEPPER_RUINED),
            textures.background(CHOP_EGGPLANT_BG_1), textures.background(CHOP_EGGPLANT_BG_2), textures.background(CHOP_EGGPLANT_BG_3), textures.background(CHOP_EGGPLANT_BG_4), textures.background(CHOP_EGGPLANT_RUINED),
            textures.background(CHOP_FINISH_BG), textures.background(CHOP_FAILED_BG),
        ]
        self.stage_idx = 0  
        
        self.progress = 0       
        self.max_lives = 3
        self.lives = self.max_lives
        self.streak = 0  
        self.damage_alpha = 0  
        
        self.success_timer = 0.0  
        self.fail_reason = ""
        self.board_hits = 0 
        
        self.shake_timer = 0.0
        self.shake_intensity = 0.0
        self.slashes = []
        
        self.particles = []
        self.knife_list = arcade.SpriteList()
        self.knife = arcade.Sprite(textures.ui_image("Knife_hand.png"), scale=0.8)
        self.knife_list.append(self.knife)
        
        self.knife_base_x = WIDTH - 200
        self.knife_base_y = HEIGHT / 2 + 100
        self.knife.center_x = self.knife_base_x
        self.knife.center_y = self.knife_base_y
        
        self.chop_anim_timer = 0.0  
        self.knife_target_x = self.knife_base_x
        self.knife_target_y = self.knife_base_y
        
        # --- Top-Right UI Sprite (Remains completely untouched) ---
        self.terry_portrait = arcade.Sprite("assets/emotions/Terry_original.png", scale=0.8)
        self.terry_portrait.center_x = 1150
        self.terry_portrait.center_y = 600
        
        self.portrait_list = arcade.SpriteList()
        self.portrait_list.append(self.terry_portrait)
        
        self.hearts = arcade.SpriteList()
        for i in range(self.max_lives):
            heart = arcade.Sprite(textures.ui_image("Character_HP.png"), scale=0.15)
            heart.center_x = 1090 + (i * 60)
            heart.center_y = 480
            self.hearts.append(heart)
            
        self.heart_anim_timer = 0.0
        self.heart_anim_state = 0  
        self.breaking_idx = -1
        self.pending_fail_dialog = False
        
        self.chop_button = arcade.Sprite(textures.ui_image("CHOP_button.png"), scale=0.7)
        self.button_list = arcade.SpriteList()
        self.button_list.append(self.chop_button)
        
        self.button_active = False
        self.slice_timer = 0.0
        
        self.dialog = DialogBox()

        # --- NEW: Exit confirmation popup menu ---
        self.exit_popup = PauseMenu(
            [
                ("Resume", "resume_chopping", "play"),
                ("Exit", "exit_chopping", "book"),
            ],
            "Exit Chopping",
            "Exit without completing the prep?",
            width=460,
        )
        
        # Load the base texture and dynamic faces for the dialogue box ONLY
        self.default_face = textures.terry_frames(glow=False)[2][0]
        self.terry_faces = textures.terry_faces()
        
        self.portraits = Portraits(self.default_face)
        
        self.widgets = [self.dialog, self.portraits, self.exit_popup]
        self.typing_player = None

        self.camera = arcade.camera.Camera2D(
            position=(WIDTH / 2, HEIGHT / 2),
            projection=arcade.LRBT(-WIDTH / 2, WIDTH / 2, -HEIGHT / 2, HEIGHT / 2),
            viewport=self.stage.viewport(),
        )

        self.relayout()

    def play_script(self, lines, then=None):
        self.script = list(lines[1:])
        self.after_script = then
        self.start_dialog(*lines[0])

    def start_dialog(self, speaker, text, face=None):
        side = "left" if speaker == "Terry" else "right"
        
        # --- FIX: Update only the Portraits widget without breaking DialogBox.open() ---
        if speaker == "Terry":
            self.portraits.terry = self.terry_faces.get(face, self.default_face)
            
        audio.play("dialog_open")
        self.dialog.open(speaker, text, side)
        self.typing_player = audio.play("dialog_type", loop=True)

    def advance_dialog(self):
        self.stop_typing_sound()
        if not self.dialog.advance():
            return
        if hasattr(self, 'script') and self.script:
            self.start_dialog(*self.script.pop(0))
            return
        then = getattr(self, 'after_script', None)
        self.after_script = None
        if then is not None:
            then()

    def relayout(self):
        super().relayout()
        if hasattr(self, 'camera'):
            self.camera.viewport = self.stage.viewport()

    def trigger_shake(self, intensity, duration):
        self.shake_intensity = intensity
        self.shake_timer = duration

    def set_emotion(self, emotion_name):
        self.terry_portrait.texture = arcade.load_texture(f"assets/emotions/{emotion_name}.png")

    def spawn_food_particles(self, x, y):
        if self.stage_idx <= 3: color = (220, 80, 80)        
        elif self.stage_idx <= 7: color = (255, 140, 0)      
        elif self.stage_idx <= 11: color = (230, 200, 240)   
        elif self.stage_idx <= 15: color = (50, 200, 50)     
        else: color = (100, 50, 120)                         
        
        for _ in range(15):
            self.particles.append(FoodParticle(x, y, color))

    def on_show_view(self):
        audio.ambience().start()
        self.play_script([("Terry", "Let's prep! Click exactly on the CHOP button. Don't miss, and don't chop too fast!", "happy")])

    def on_hide_view(self):
        self.stop_typing_sound()

    def stop_typing_sound(self):
        if self.typing_player:
            audio.bank().stop(self.typing_player)
            self.typing_player = None

    def spawn_button(self):
        safe_zones = [
            (400, 900, 580, 660),   
            (150, 350, 150, 500),   
            (350, 900, 150, 220),   
            (900, 1100, 150, 350),  
        ]
        
        for _ in range(15):
            zone = random.choice(safe_zones)
            new_x = random.randint(zone[0], zone[1])
            new_y = random.randint(zone[2], zone[3])
            
            dist = math.hypot(new_x - self.chop_button.center_x, new_y - self.chop_button.center_y)
            if dist > 200:
                break
                
        button_radius = 90
        new_x = max(button_radius, min(WIDTH - button_radius, new_x))
        new_y = max(button_radius, min(HEIGHT - button_radius, new_y))

        self.chop_button.center_x = new_x
        self.chop_button.center_y = new_y
        self.button_active = True
        self.slice_timer = 2.0

    def fail_slice(self, reason="timeout", click_x=None, click_y=None):
        self.button_active = False
        self.success_timer = 0.0  
        self.lives -= 1
        self.streak = 0  
        self.damage_alpha = 150  
        self.fail_reason = reason
        
        audio.play("hp_reduced")
        
        if reason == "misclick":
            audio.play("chop_table")
            self.trigger_shake(12.0, 0.2)
            
            self.board_hits += 1
            if self.board_hits >= 3:
                achievements.unlock("bbq_misclick")
        
        if reason == "misclick" and click_x is not None and click_y is not None:
            self.chop_anim_timer = 0.15
            self.knife_target_x = click_x
            self.knife_target_y = click_y
        elif reason == "overchop":
            self.chop_anim_timer = 0.15
            self.knife_target_x = WIDTH / 2 - 50
            self.knife_target_y = HEIGHT / 2 - 50
            self.spawn_food_particles(self.knife_target_x, self.knife_target_y)
            
            self.trigger_shake(15.0, 0.25)
            self.slashes.append(SlashEffect(self.knife_target_x, self.knife_target_y))
            
            achievements.unlock("bbq_overchop")
        
        self.breaking_idx = self.max_lives - self.lives - 1
        if 0 <= self.breaking_idx < self.max_lives:
            self.hearts[self.breaking_idx].texture = textures.ui_image("Character_HP_broke_into_half.png")
            self.heart_anim_timer = 0.2  
            self.heart_anim_state = 1
            self.pending_fail_dialog = True 
            
            if reason == "overchop":
                if self.stage_idx < 4: self.stage_idx = 3   
                elif 4 <= self.stage_idx < 8: self.stage_idx = 7   
                elif 8 <= self.stage_idx < 12: self.stage_idx = 11  
                elif 12 <= self.stage_idx < 16: self.stage_idx = 15  
                elif 16 <= self.stage_idx < 21: self.stage_idx = 20  

    def on_update(self, delta_time):
        audio.ambience().update(delta_time)
        if self.exit_popup.visible:
            return
        
        for p in self.particles:
            p.update(delta_time)
        self.particles = [p for p in self.particles if not p.is_dead]

        for slash in self.slashes:
            slash.update(delta_time)
        self.slashes = [s for s in self.slashes if not s.is_dead]

        if self.shake_timer > 0:
            self.shake_timer -= delta_time
            shake_x = random.uniform(-self.shake_intensity, self.shake_intensity)
            shake_y = random.uniform(-self.shake_intensity, self.shake_intensity)
            self.camera.position = (WIDTH / 2 + shake_x, HEIGHT / 2 + shake_y)
        else:
            self.camera.position = (WIDTH / 2, HEIGHT / 2)

        if self.chop_anim_timer > 0:
            self.chop_anim_timer -= delta_time
            progress = max(0, self.chop_anim_timer / 0.15) 
            
            if progress > 0.5: t = (1.0 - progress) * 2.0  
            else: t = progress * 2.0          
                
            self.knife.angle = -60 * t
            self.knife.center_x = self.knife_base_x + (self.knife_target_x - self.knife_base_x) * t
            self.knife.center_y = self.knife_base_y + (self.knife_target_y - self.knife_base_y) * t
        else:
            self.knife.angle = 0
            self.knife.center_x = self.knife_base_x
            self.knife.center_y = self.knife_base_y

        if self.damage_alpha > 0:
            self.damage_alpha = max(0, self.damage_alpha - (300 * delta_time))
            
        if self.success_timer > 0:
            self.success_timer -= delta_time
            if self.success_timer <= 0:
                if self.stage_idx == 2:
                    self.progress += 20
                    self.play_script([("Terry", "Perfect! Meat is prepped. (Progress 20%)", "happy")])
                elif self.stage_idx == 6:
                    self.progress += 20
                    self.play_script([("Terry", "Nice and crunchy! Carrots are done. (Progress 40%)", "happy")])
                elif self.stage_idx == 10:
                    self.progress += 20
                    self.play_script([("Terry", "My eyes are watering... but the onions are done! (Progress 60%)", "nervous")])
                elif self.stage_idx == 14:
                    self.progress += 20
                    self.play_script([("Terry", "Green peppers are sliced perfectly! (Progress 80%)", "happy")])
                elif self.stage_idx == 19:
                    self.progress += 20
                    self.play_script([("Terry", "The eggplant is ready! (Progress 100%)", "happy")])
                else:
                    self.spawn_button()

        if self.heart_anim_timer > 0:
            self.heart_anim_timer -= delta_time
            if self.heart_anim_timer <= 0 and self.breaking_idx != -1:
                
                if self.heart_anim_state == 1:
                    self.hearts[self.breaking_idx].texture = textures.ui_image("Character_HP_Fragmented.png")
                    self.heart_anim_timer = 0.2  
                    self.heart_anim_state = 2
                    
                elif self.heart_anim_state == 2:
                    self.hearts[self.breaking_idx].alpha = 0 
                    self.heart_anim_state = 0
                    
                    if self.pending_fail_dialog:
                        self.pending_fail_dialog = False
                        
                        if self.lives <= 0:
                            self.stage_idx = 22 
                            self.set_emotion("Terry_sad")
                            audio.play("game_failed")
                            self.play_script([("Terry", "I ruined too much food! I have to restart the whole prep...", "nervous")])
                        else:
                            self.set_emotion("Terry_shocked")
                            if self.fail_reason == "misclick":
                                self.play_script([("Terry", "Ouch! I completely missed the food and chopped the board! Let me try that again.", "nervous")])
                            elif self.fail_reason == "overchop":
                                self.play_script([("Terry", "Oh no! I chopped too fast and mashed it into pieces! Moving to next food...", "nervous")])
                            else:
                                self.play_script([("Terry", "I took too long and lost my focus. Let me try that again!", "nervous")])

        if self.dialog.visible:
            self.dialog.update(delta_time)
            if not self.dialog.typing:
                self.stop_typing_sound()
            return

        if self.button_active:
            self.slice_timer -= delta_time
            if self.slice_timer <= 0:
                self.fail_slice(reason="timeout")

    def on_draw(self):
        self.clear()
        
        self.window.default_camera.use()
        current_bg = self.backgrounds[self.stage_idx]
        arcade.draw_texture_rect(current_bg, cover_rect(current_bg, self.stage.viewport()))
        
        if self.damage_alpha > 0:
            flash_rect = arcade.XYWH(self.window.width / 2, self.window.height / 2, self.window.width, self.window.height)
            arcade.draw_rect_filled(flash_rect, (255, 0, 0, int(self.damage_alpha)))
        
        self.camera.use()
        
        if self.stage_idx < 21:
            for p in self.particles:
                p.draw()
            
            for slash in self.slashes:
                slash.draw()
                
            self.knife_list.draw(pixelated=True)
        
        if self.stage_idx != 21:
            self.portrait_list.draw(pixelated=True)
            
        if self.stage_idx < 21:
            self.hearts.draw(pixelated=True)
            
            arcade.draw_text("Chopping Progress", 40, HEIGHT - 35, arcade.color.WHITE, 16, bold=True, font_name="Kenney Pixel Square")
            
            bar_x = 40
            bar_y = HEIGHT - 70
            bar_width = 300
            bar_height = 24
            
            outline_rect = arcade.XYWH(bar_x + bar_width / 2, bar_y, bar_width, bar_height)
            arcade.draw_rect_outline(outline_rect, arcade.color.DARK_GRAY, 3)
            
            if self.progress > 0:
                fill_width = bar_width * (self.progress / 100.0)
                fill_rect = arcade.XYWH(bar_x + (fill_width / 2), bar_y, fill_width, bar_height - 4)
                arcade.draw_rect_filled(fill_rect, arcade.color.APPLE_GREEN)

        if self.button_active:
            self.button_list.draw(pixelated=True)
            timer_color = arcade.color.RED if self.slice_timer <= 1.0 else arcade.color.WHITE
            arcade.draw_text(
                f"{self.slice_timer:.1f}s",
                self.chop_button.center_x, 
                self.chop_button.center_y + 60,
                timer_color, font_size=20, anchor_x="center", bold=True
            )
            
        self.window.default_camera.use()
        if self.dialog.visible:
            self.portraits.draw(partner=None, speaking="left")
            self.dialog.draw()

        # --- NEW: Draw exit popup if open ---
        if self.exit_popup.visible:
            self.exit_popup.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        canvas_x, canvas_y = self.canvas_point(x, y)
        self.exit_popup.on_mouse_motion(canvas_x, canvas_y)

    def on_mouse_press(self, x, y, button, modifiers):
        canvas_x, canvas_y = self.canvas_point(x, y)
        
        if self.exit_popup.visible:
            self.run_action(self.exit_popup.on_mouse_press(canvas_x, canvas_y, button))
            return

        if self.dialog.visible:
            if button == arcade.MOUSE_BUTTON_LEFT:
                self.continue_dialog()
            return
        
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.success_timer > 0:
                audio.play("click_button")
                self.fail_slice(reason="overchop", click_x=canvas_x, click_y=canvas_y)
                return
            
            if self.button_active:
                if self.chop_button.collides_with_point((canvas_x, canvas_y)):
                    self.button_active = False
                    
                    if self.stage_idx in (0, 1):
                        audio.play("chop_meat")
                    elif self.stage_idx in (4, 5, 8, 9, 12, 13, 16, 17, 18):
                        audio.play(random.choice(["chop_vege_1", "chop_vege_2"]))
                    else:
                        audio.play("click_button")
                    
                    self.stage_idx += 1
                    
                    self.chop_anim_timer = 0.15
                    self.knife_target_x = WIDTH / 2 - 50
                    self.knife_target_y = HEIGHT / 2 - 50
                    
                    self.trigger_shake(6.0, 0.1)
                    self.slashes.append(SlashEffect(self.knife_target_x, self.knife_target_y))
                    self.spawn_food_particles(self.knife_target_x, self.knife_target_y)
                    
                    self.streak += 1
                    if self.streak > 1:
                        self.set_emotion("Terry_excited")
                    else:
                        self.set_emotion("Terry_smile_excited")
                    
                    self.success_timer = 0.3
                else:
                    self.fail_slice(reason="misclick", click_x=canvas_x, click_y=canvas_y)

    def on_key_press(self, key, modifiers):
        if self.exit_popup.visible:
            self.run_action(self.exit_popup.on_key_press(key))
            return

        if key == arcade.key.ESCAPE:
            self.stop_typing_sound()
            audio.play("ui_click")
            self.exit_popup.open()
            return
        
        if not self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.RETURN, arcade.key.SPACE):
                if self.lives <= 0:
                    self.window.show_view(ChoppingView())
                    return
                    
                if self.stage_idx in (2, 3):
                    self.set_emotion("Terry_nervous" if self.stage_idx == 3 else "Terry_original")
                    self.streak = 0
                    self.stage_idx = 4
                    emotion = "nervous" if self.stage_idx == 3 else "happy"
                    self.play_script([("Terry", "Let's slice up these fresh carrots next!", emotion)])
                
                elif self.stage_idx in (6, 7):
                    self.set_emotion("Terry_nervous" if self.stage_idx == 7 else "Terry_original")
                    self.streak = 0
                    self.stage_idx = 8
                    emotion = "nervous" if self.stage_idx == 7 else "happy"
                    self.play_script([("Terry", "Alright, onions are next. Let's chop fast before I cry!", emotion)])
                    
                elif self.stage_idx in (10, 11):
                    self.set_emotion("Terry_nervous" if self.stage_idx == 11 else "Terry_original")
                    self.streak = 0
                    self.stage_idx = 12
                    emotion = "nervous" if self.stage_idx == 11 else "happy"
                    self.play_script([("Terry", "Time for the green peppers!", emotion)])
                    
                elif self.stage_idx in (14, 15):
                    self.set_emotion("Terry_nervous" if self.stage_idx == 15 else "Terry_original")
                    self.streak = 0
                    self.stage_idx = 16
                    emotion = "nervous" if self.stage_idx == 15 else "happy"
                    self.play_script([("Terry", "Last but not least, the eggplant!", emotion)])
                    
                elif self.stage_idx in (19, 20):
                    self.stage_idx = 21
                    audio.play("game_success")
                    self.play_script([("Terry", "All ingredients are prepped! Time to fire up the BBQ.", "happy")])
                    
                elif self.stage_idx == 21:
                    if self.lives == self.max_lives:
                        achievements.unlock("bbq_flawless_chop")
                    
                    self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=False, play_grill_unlock=True))

                else:
                    if not self.button_active:
                        self.spawn_button()
            return
            
        if self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.SPACE):
                self.continue_dialog()
            return

    def continue_dialog(self):
        """Enter, Space or a click on an open line: finish it, or move on."""
        self.advance_dialog()

        if not self.dialog.visible:
            if self.lives <= 0:
                self.window.show_view(ChoppingView())
                return

            if self.stage_idx in (2, 3):
                self.set_emotion("Terry_nervous" if self.stage_idx == 3 else "Terry_original")
                self.streak = 0
                self.stage_idx = 4
                emotion = "nervous" if self.stage_idx == 3 else "happy"
                self.play_script([("Terry", "Let's slice up these fresh carrots next!", emotion)])
            elif self.stage_idx in (6, 7):
                self.set_emotion("Terry_nervous" if self.stage_idx == 7 else "Terry_original")
                self.streak = 0
                self.stage_idx = 8
                emotion = "nervous" if self.stage_idx == 7 else "happy"
                self.play_script([("Terry", "Alright, onions are next. Let's chop fast before I cry!", emotion)])
            elif self.stage_idx in (10, 11):
                self.set_emotion("Terry_nervous" if self.stage_idx == 11 else "Terry_original")
                self.streak = 0
                self.stage_idx = 12
                emotion = "nervous" if self.stage_idx == 11 else "happy"
                self.play_script([("Terry", "Time for the green peppers!", emotion)])
            elif self.stage_idx in (14, 15):
                self.set_emotion("Terry_nervous" if self.stage_idx == 15 else "Terry_original")
                self.streak = 0
                self.stage_idx = 16
                emotion = "nervous" if self.stage_idx == 15 else "happy"
                self.play_script([("Terry", "Last but not least, the eggplant!", emotion)])
            elif self.stage_idx in (19, 20):
                self.stage_idx = 21
                audio.play("game_success")
                self.play_script([("Terry", "All ingredients are prepped! Time to fire up the BBQ.", "happy")])
            elif self.stage_idx == 21:
                if self.lives == self.max_lives:
                    achievements.unlock("bbq_flawless_chop")

                self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=False, play_grill_unlock=True))
            else:
                if not self.button_active:
                    self.spawn_button()

    def run_action(self, action):
        if action is None:
            return
        if action in ("resume_chopping", "resume"):
            self.exit_popup.close()
            if self.dialog.visible and self.dialog.typing and self.typing_player is None:
                self.typing_player = audio.play("dialog_type", loop=True)
        elif action == "exit_chopping":
            self.exit_popup.close()
            self.stop_typing_sound()
            # Keep chopping station unlocked, but chopping progress is not completed
            self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=False, grill_completed=False))