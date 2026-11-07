import math
import random
import arcade

# --- NEW: Added achievements to the core imports ---
from ...core import achievements, audio, textures
from ...config import HEIGHT, WIDTH
from .config import (
    BURN_100_BG, BURN_10_BG, BURN_20_BG, BURN_50_BG, GRILL_0_BG, GRILL_100_BG,
    GRILL_20_BG, GRILL_50_BG, GRILL_FAILED_BG, GRILL_FINISH_BG,
)
from ...core.dialogue import DialogBox
from ...core.stage import StageView
from .hub import BbqView
from ...core.widgets import Portraits

def cover_rect(texture, rect):
    scale = max(rect.width / texture.width, rect.height / texture.height)
    return arcade.XYWH(rect.x, rect.y, texture.width * scale, texture.height * scale)

# --- NEW: Floating Combat/Action Text ---
class FloatingText:
    def __init__(self, text, x, y, color):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.lifetime = 1.0
        self.age = 0.0
        self.vy = 50.0  

    def update(self, dt):
        self.age += dt
        self.y += self.vy * dt

    def draw(self):
        progress = self.age / self.lifetime
        if progress >= 1.0: return
        
        alpha = max(0, int(255 * (1.0 - (progress ** 2))))
        
        arcade.draw_text(self.text, self.x + 2, self.y - 2, (0, 0, 0, alpha), 
                         22, bold=True, anchor_x="center", font_name="Kenney Pixel Square")
        arcade.draw_text(self.text, self.x, self.y, (*self.color, alpha), 
                         22, bold=True, anchor_x="center", font_name="Kenney Pixel Square")

    @property
    def is_dead(self):
        return self.age >= self.lifetime


# --- Customizable Layered Smoke Particle (Bigger & Color-Tinted) ---
class SmokeParticle:
    def __init__(self, x, y, color=(160, 160, 160)):
        self.x = x + random.uniform(-8, 8)
        self.y = y + random.uniform(-5, 5)
        self.vx = random.uniform(-30, 30)
        self.vy = random.uniform(70, 110)
        self.radius = random.uniform(14, 24)
        self.max_radius = random.uniform(90, 150)
        self.age = 0.0
        self.lifetime = random.uniform(2.5, 4.0)
        self.drift = random.uniform(-30, 30)
        self.color = color 

    def update(self, dt):
        self.age += dt
        progress = min(self.age / self.lifetime, 1.0)
        self.y += self.vy * dt
        spread = 0.3 + progress
        self.x += (self.vx + self.drift * spread) * dt
        self.radius = 14 + (self.max_radius - 14) * progress
        self.drift += random.uniform(-12, 12) * dt
        self.drift = max(-45, min(45, self.drift))

    def draw(self):
        progress = min(self.age / self.lifetime, 1.0)
        fade = (1.0 - progress) ** 1.5
        layers = [(1.00, 12), (0.82, 16), (0.64, 20), (0.46, 25), (0.28, 30)]
        r, g, b = self.color
        for scale, base_alpha in layers:
            radius = self.radius * scale
            alpha = int(base_alpha * fade)
            if alpha > 0:
                arcade.draw_circle_filled(self.x, self.y, radius, (r, g, b, alpha))

    @property
    def is_dead(self):
        return self.age >= self.lifetime


# --- Continuous Smoke Emitter for Realistic BBQ Smoking ---
class SmokeEmitter:
    def __init__(self, x, y, color=(160, 160, 160)):
        self.x = x
        self.y = y
        self.color = color
        self.emit_timer = 0.0
        self.emit_interval = 0.18  

    def update(self, dt, particles):
        self.emit_timer += dt
        if self.emit_timer >= self.emit_interval:
            self.emit_timer = 0.0
            particles.append(SmokeParticle(self.x, self.y, self.color))


class GrillingView(StageView):
    def __init__(self):
        super().__init__()
        
        self.grill_progress = 0   
        self.burn_strikes = 0     
        self.game_over = False
        self.end_phase = 0  
        self.has_spun = False
        
        self.time_since_last_action = 0.0
        self.smoke_tier = 0
        self.smoke_emitters = []
        
        self.smoke_min_x = WIDTH / 2 - 360
        self.smoke_max_x = WIDTH / 2 + 360
        self.smoke_min_y = HEIGHT / 2 - 240
        self.smoke_max_y = HEIGHT / 2 + 220
        
        self.temperature = 150.0  
        self.temp_textures = {
            "low": textures.ui_image("Temperature_bar_low_heat.png"),
            "normal": textures.ui_image("Temperature_bar_normal.png"),
            "maxed": textures.ui_image("Temperature_bar_maxed_heat.png"),
        }
        
        self.bar_width = 400
        self.bar_height = 30
        self.bar_x = WIDTH / 2
        self.bar_y = 100
        self.arrow_x = self.bar_x - (self.bar_width / 2)
        self.arrow_dir = 1
        self.arrow_base_speed = 500.0  
        
        self.particles = []
        self.floating_texts = []         
        self.fire_flash_alpha = 0.0      

        # --- NEW: Dialogue Delay System ---
        self.pending_dialog = None
        self.pending_emotion = None
        self.dialog_timer = 0.0

        self.terry_portrait = arcade.Sprite("assets/emotions/Terry_original.png", scale=0.7)
        self.terry_portrait.center_x = 1170
        self.terry_portrait.center_y = 600
        
        self.portrait_list = arcade.SpriteList()
        self.portrait_list.append(self.terry_portrait)

        self.spin_button = arcade.Sprite(textures.ui_image("SPIN_button.png"), scale=0.7)
        self.spin_button.center_x = 1170
        self.spin_button.center_y = 120
        
        self.button_list = arcade.SpriteList()
        self.button_list.append(self.spin_button)

        self.temp_bar = arcade.Sprite(self.temp_textures["normal"], scale=1.2)
        self.temp_bar.center_x = 80
        self.temp_bar.center_y = HEIGHT / 2
        
        self.ui_list = arcade.SpriteList()
        self.ui_list.append(self.temp_bar)

        self.dialog = DialogBox()

        self.terry_faces = textures.terry_faces()
        self.pending_dialog_face = None
        
        try:
            terry_tex = arcade.load_texture("assets/sprites/Terry-idle.png")
        except Exception:
            terry_tex = self.terry_portrait.texture
        self.portraits = Portraits(terry_tex)
        
        self.widgets = [self.dialog, self.portraits]
        self.typing_player = None
        self.grilling_player = None
        
        self.camera = arcade.camera.Camera2D(
            position=(WIDTH / 2, HEIGHT / 2),
            projection=arcade.LRBT(-WIDTH / 2, WIDTH / 2, -HEIGHT / 2, HEIGHT / 2),
            viewport=self.stage.viewport(),
        )
        self.relayout()

    def relayout(self):
        super().relayout()
        if hasattr(self, 'camera'):
            self.camera.viewport = self.stage.viewport()

    def set_emotion(self, emotion_name):
        self.terry_portrait.texture = arcade.load_texture(f"assets/emotions/{emotion_name}.png")

    def spawn_burst_smoke(self, color=(180, 180, 180), count=10):
        for _ in range(count):
            self.particles.append(SmokeParticle(WIDTH / 2, HEIGHT / 2 - 50, color))

    def _get_random_smoke_position(self, min_x, max_x, min_y, max_y):
        min_dist = 160.0
        for _ in range(50):
            cx = random.uniform(min_x, max_x)
            cy = random.uniform(min_y, max_y)
            too_close = False
            for em in self.smoke_emitters:
                if math.hypot(cx - em.x, cy - em.y) < min_dist:
                    too_close = True
                    break
            if not too_close:
                return cx, cy
        return random.uniform(min_x, max_x), random.uniform(min_y, max_y)

    def on_show_view(self):
        self.trigger_dialog("Click SPIN when the arrow hits the green zone! Watch the heat so we don't burn the skewers!", dialog_face="happy")

    def on_hide_view(self):
        if self.grilling_player is not None:
            audio.bank().stop(self.grilling_player)
            self.grilling_player = None
        self.stop_typing_sound()

    def trigger_dialog(self, text, dialog_face=None):
        if dialog_face and dialog_face in self.terry_faces:
            self.portraits.terry = self.terry_faces[dialog_face]
            
        audio.play("dialog_open")
        self.dialog.open("Terry", text)
        self.typing_player = audio.play("dialog_type", loop=True)

    def stop_typing_sound(self):
        if self.typing_player:
            audio.bank().stop(self.typing_player)
            self.typing_player = None

    def get_current_bg(self):
        if self.game_over:
            if self.end_phase == 1:
                if self.burn_strikes >= 3: return textures.background(BURN_100_BG) 
                elif self.burn_strikes == 2: return textures.background(BURN_50_BG)  
                else: return textures.background(GRILL_100_BG) 
            elif self.end_phase == 2:
                if self.burn_strikes >= 3: return textures.background(GRILL_FAILED_BG) 
                else: return textures.background(GRILL_FINISH_BG) 
                
        if self.burn_strikes > 0:
            if self.grill_progress >= 50: return textures.background(BURN_50_BG)
            elif self.grill_progress >= 20: return textures.background(BURN_20_BG)
            elif self.grill_progress >= 10: return textures.background(BURN_10_BG)
            else: return textures.background(GRILL_0_BG)
        else:
            if self.grill_progress >= 50: return textures.background(GRILL_50_BG)
            elif self.grill_progress >= 20: return textures.background(GRILL_20_BG)
            else: return textures.background(GRILL_0_BG)

    def get_zone_widths(self):
        heat_ratio = max(0.0, min(1.0, (self.temperature - 100.0) / 200.0))
        green_w = max(20.0, 70.0 - (50.0 * heat_ratio))
        yellow_w = max(80.0, 260.0 - (180.0 * heat_ratio))
        return yellow_w, green_w

    def on_update(self, delta_time):
        # 1. Always update active visual effects
        for p in self.particles:
            p.update(delta_time)
        self.particles = [p for p in self.particles if not p.is_dead]

        for ft in self.floating_texts:
            ft.update(delta_time)
        self.floating_texts = [ft for ft in self.floating_texts if not ft.is_dead]

        if self.fire_flash_alpha > 0:
            self.fire_flash_alpha = max(0.0, self.fire_flash_alpha - (400.0 * delta_time))

        for emitter in self.smoke_emitters:
            emitter.update(delta_time, self.particles)

        # Ambient grilling sound
        if not self.game_over and not self.dialog.visible:
            if self.grilling_player is None:
                self.grilling_player = audio.play("grilling", loop=True)
        else:
            if self.grilling_player is not None:
                audio.bank().stop(self.grilling_player)
                self.grilling_player = None

        # 2. Block game logic if dialog is actively visible
        if self.dialog.visible:
            self.dialog.update(delta_time)
            if not self.dialog.typing:
                self.stop_typing_sound()
            return  

        # 3. Block game logic if we are in the "Freeze Frame" dialog delay
        #    This allows the floating text and fire flashes to animate before dialog blocks the screen.
        if self.dialog_timer > 0:
            self.dialog_timer -= delta_time
            if self.dialog_timer <= 0 and self.pending_dialog:
                if self.pending_emotion:
                    self.set_emotion(self.pending_emotion)
                    self.pending_emotion = None
                self.trigger_dialog(self.pending_dialog, dialog_face=self.pending_dialog_face)
                self.pending_dialog = None
            return

        # 4. Standard Game Logic
        if not self.game_over:
            self.temperature = min(300.0, self.temperature + (15.0 * delta_time))
            self.time_since_last_action += delta_time
            
            min_x, max_x = self.smoke_min_x, self.smoke_max_x
            min_y, max_y = self.smoke_min_y, self.smoke_max_y

            if self.smoke_tier == 0 and self.time_since_last_action >= 2.0:
                x1 = random.uniform(min_x, max_x)
                y1 = random.uniform(min_y, max_y)
                self.smoke_emitters.append(SmokeEmitter(x1, y1, color=(200, 200, 200)))
                self.smoke_tier = 1
            elif self.smoke_tier == 1 and self.time_since_last_action >= 5.0:
                x2, y2 = self._get_random_smoke_position(min_x, max_x, min_y, max_y)
                self.smoke_emitters.append(SmokeEmitter(x2, y2, color=(150, 150, 150)))
                self.smoke_tier = 2
            elif self.smoke_tier == 2 and self.time_since_last_action >= 8.0:
                x3, y3 = self._get_random_smoke_position(min_x, max_x, min_y, max_y)
                self.smoke_emitters.append(SmokeEmitter(x3, y3, color=(100, 90, 90)))
                self.smoke_tier = 3
            
            if self.temperature < 160:
                self.temp_bar.texture = self.temp_textures["low"]
            elif self.temperature < 250:
                self.temp_bar.texture = self.temp_textures["normal"]
            else:
                self.temp_bar.texture = self.temp_textures["maxed"]

            # --- 300°C OVERHEAT / BURN STRIKE CHECK ---
            if self.temperature >= 300.0:
                self.burn_strikes += 1
                
                if not self.has_spun:
                    achievements.unlock("bbq_staredown")
                
                self.temperature = 150.0  
                self.time_since_last_action = 0.0
                self.smoke_tier = 0
                self.smoke_emitters.clear()
                
                # --- NEW: Trigger Grease Fire Flash on Overheat ---
                self.fire_flash_alpha = 200.0
                self.spawn_burst_smoke(color=(50, 40, 40), count=25)
                
                if self.burn_strikes >= 3:
                    self.game_over = True
                    self.end_phase = 1
                    self.pending_emotion = "Terry_shocked"
                    self.pending_dialog_face = "unimpressed"
                    if not self.has_spun:
                        self.pending_dialog = "Note to self: staring blankly at the tachometer doesn't stop the heat."
                    else:
                        self.pending_dialog = "Well... on the bright side, we won't need any charcoal for the next BBQ."
                else:
                    self.pending_emotion = "Terry_nervous"
                    self.pending_dialog_face = "nervous"
                    audio.play("hp_reduced")
                    self.pending_dialog = "The grill flared up because we waited too long! A burn strike added."
                
                # Activate the visual delay timer!
                self.dialog_timer = 0.8
                return

            current_speed = self.arrow_base_speed + (self.grill_progress * 3.0) + ((self.temperature - 100) * 0.8)
            self.arrow_x += current_speed * self.arrow_dir * delta_time
            
            left_edge = self.bar_x - (self.bar_width / 2)
            right_edge = self.bar_x + (self.bar_width / 2)
            
            if self.arrow_x >= right_edge:
                self.arrow_x = right_edge
                self.arrow_dir = -1
            elif self.arrow_x <= left_edge:
                self.arrow_x = left_edge
                self.arrow_dir = 1


        self.clear()
        
        self.window.default_camera.use()
        current_bg = self.get_current_bg()
        arcade.draw_texture_rect(current_bg, cover_rect(current_bg, self.stage.viewport()))

        # --- MOVED: Draw Overlays here so they scale perfectly with the virtual bounds ---
        self.camera.use()
        
        if not self.game_over and self.temperature >= 200:
            heat_alpha = min(150, int((self.temperature - 200) * 1.5))
            pulse = math.sin(self.time_since_last_action * 4.0) * 25
            final_alpha = max(0, min(255, int(heat_alpha + pulse)))
            
            thickness = 100 
            vignette_color = (255, 80, 0, final_alpha) 
            vignette_rect = arcade.XYWH(WIDTH/2, HEIGHT/2, WIDTH - thickness, HEIGHT - thickness)
            
            arcade.draw_rect_outline(vignette_rect, vignette_color, border_width=thickness)
        
        if self.fire_flash_alpha > 0:
            flash_rect = arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
            arcade.draw_rect_filled(flash_rect, (255, 180, 50, int(self.fire_flash_alpha)))
        
        for p in self.particles:
            p.draw()
            
        self.portrait_list.draw(pixelated=True)
        
        if not self.game_over:
            self.ui_list.draw(pixelated=True)
            
            arcade.draw_text("TEMP", self.temp_bar.center_x, self.temp_bar.top + 50,
                             arcade.color.WHITE, 20, bold=True, anchor_x="center", font_name="Kenney Pixel Square")
            
            temp_color = arcade.color.RED if self.temperature >= 250 else arcade.color.WHITE
            arcade.draw_text(f"{int(self.temperature)}°C", self.temp_bar.center_x, self.temp_bar.top + 20, 
                             temp_color, 24, bold=True, anchor_x="center", font_name="Kenney Pixel Square")

            yellow_w, green_w = self.get_zone_widths()

            arcade.draw_rect_filled(arcade.XYWH(self.bar_x, self.bar_y, self.bar_width, self.bar_height), arcade.color.CRIMSON)
            arcade.draw_rect_filled(arcade.XYWH(self.bar_x, self.bar_y, yellow_w, self.bar_height), arcade.color.GOLD)
            arcade.draw_rect_filled(arcade.XYWH(self.bar_x, self.bar_y, green_w, self.bar_height), arcade.color.APPLE_GREEN)
            
            arcade.draw_rect_outline(arcade.XYWH(self.bar_x, self.bar_y, self.bar_width, self.bar_height), arcade.color.DARK_GRAY, 4)
            
            arcade.draw_triangle_filled(
                self.arrow_x - 15, self.bar_y + 35,
                self.arrow_x + 15, self.bar_y + 35,
                self.arrow_x, self.bar_y + 5,
                arcade.color.WHITE
            )
            
            arcade.draw_text(f"Strikes: {self.burn_strikes}/3", self.bar_x - 180, self.bar_y + 40, arcade.color.RED, 16, bold=True, font_name="Kenney Pixel Square")
            arcade.draw_text(f"Progress: {self.grill_progress}%", self.bar_x + 30, self.bar_y + 40, arcade.color.WHITE, 16, bold=True, font_name="Kenney Pixel Square")
            
            for ft in self.floating_texts:
                ft.draw()
            
            if not self.dialog.visible:
                self.button_list.draw(pixelated=True)
            
        self.window.default_camera.use()
        if self.dialog.visible:
            self.portraits.draw(partner=None, speaking="left")
            self.dialog.draw()

    def on_draw(self):
        self.clear()
        
        self.window.default_camera.use()
        current_bg = self.get_current_bg()
        arcade.draw_texture_rect(current_bg, cover_rect(current_bg, self.stage.viewport()))

        self.camera.use()
        
        if not self.game_over and self.temperature >= 200:
            heat_alpha = min(150, int((self.temperature - 200) * 1.5))
            pulse = math.sin(self.time_since_last_action * 4.0) * 25
            final_alpha = max(0, min(255, int(heat_alpha + pulse)))
            thickness = 100 
            vignette_color = (255, 80, 0, final_alpha) 
            vignette_rect = arcade.XYWH(WIDTH/2, HEIGHT/2, WIDTH - thickness, HEIGHT - thickness)
            arcade.draw_rect_outline(vignette_rect, vignette_color, border_width=thickness)
        
        if self.fire_flash_alpha > 0:
            flash_rect = arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
            arcade.draw_rect_filled(flash_rect, (255, 180, 50, int(self.fire_flash_alpha)))
        
        for p in self.particles:
            p.draw()
            
        self.portrait_list.draw(pixelated=True)
        
        if not self.game_over:
            self.ui_list.draw(pixelated=True)
            
            arcade.draw_text("TEMP", self.temp_bar.center_x, self.temp_bar.top + 50,
                             arcade.color.WHITE, 20, bold=True, anchor_x="center", font_name="Kenney Pixel Square")
            
            temp_color = arcade.color.RED if self.temperature >= 250 else arcade.color.WHITE
            arcade.draw_text(f"{int(self.temperature)}°C", self.temp_bar.center_x, self.temp_bar.top + 20, 
                             temp_color, 24, bold=True, anchor_x="center", font_name="Kenney Pixel Square")

            yellow_w, green_w = self.get_zone_widths()

            arcade.draw_rect_filled(arcade.XYWH(self.bar_x, self.bar_y, self.bar_width, self.bar_height), arcade.color.CRIMSON)
            arcade.draw_rect_filled(arcade.XYWH(self.bar_x, self.bar_y, yellow_w, self.bar_height), arcade.color.GOLD)
            arcade.draw_rect_filled(arcade.XYWH(self.bar_x, self.bar_y, green_w, self.bar_height), arcade.color.APPLE_GREEN)
            
            arcade.draw_rect_outline(arcade.XYWH(self.bar_x, self.bar_y, self.bar_width, self.bar_height), arcade.color.DARK_GRAY, 4)
            
            arcade.draw_triangle_filled(
                self.arrow_x - 15, self.bar_y + 35,
                self.arrow_x + 15, self.bar_y + 35,
                self.arrow_x, self.bar_y + 5,
                arcade.color.WHITE
            )
            
            arcade.draw_text(f"Strikes: {self.burn_strikes}/3", self.bar_x - 180, self.bar_y + 40, arcade.color.RED, 16, bold=True, font_name="Kenney Pixel Square")
            arcade.draw_text(f"Progress: {self.grill_progress}%", self.bar_x + 30, self.bar_y + 40, arcade.color.WHITE, 16, bold=True, font_name="Kenney Pixel Square")
            
            if not self.dialog.visible:
                self.button_list.draw(pixelated=True)
                
        # --- FIX: Moved floating_texts loop OUTSIDE the `if not self.game_over:` block! ---
        # This ensures the popup text still renders during the 0.8s pause on the final frame.
        for ft in self.floating_texts:
            ft.draw()
            
        self.window.default_camera.use()
        if self.dialog.visible:
            self.portraits.draw(partner=None, speaking="left")
            self.dialog.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        # --- PREVENT clicks if dialogue is up, game is over, or we are in the freeze-frame delay! ---
        if self.dialog.visible or self.game_over or self.dialog_timer > 0:
            return
            
        canvas_x, canvas_y = self.stage.to_canvas(x, y)
        
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.spin_button.collides_with_point((canvas_x, canvas_y)):
                audio.play("click_button")
                
                self.has_spun = True
                self.time_since_last_action = 0.0
                self.smoke_tier = 0
                self.smoke_emitters.clear()  
                
                yellow_w, green_w = self.get_zone_widths()
                dist_from_center = abs(self.arrow_x - self.bar_x)
                
                if dist_from_center <= (green_w / 2):
                    self.grill_progress = min(100, self.grill_progress + 25)
                    self.spawn_burst_smoke(color=(220, 220, 220), count=8)
                    
                    self.pending_emotion = "Terry_excited"
                    self.pending_dialog_face = "happy"
                    self.pending_dialog = "Flawless timing! The coals are perfectly aerated."
                    self.floating_texts.append(FloatingText("PERFECT!", self.arrow_x, self.bar_y + 40, (0, 255, 0)))
                    
                elif dist_from_center <= (yellow_w / 2):
                    self.grill_progress = min(100, self.grill_progress + 10)
                    self.spawn_burst_smoke(color=(170, 170, 170), count=8)
                    
                    self.pending_emotion = "Terry_smile_excited"
                    self.pending_dialog_face = "happy"
                    self.pending_dialog = "Good spin! Cooking evenly."
                    self.floating_texts.append(FloatingText("GOOD", self.arrow_x, self.bar_y + 40, (255, 215, 0)))
                    
                else:
                    self.burn_strikes += 1
                    self.pending_emotion = "Terry_nervous"
                    self.pending_dialog_face = "nervous"
                    audio.play("hp_reduced")
                    self.pending_dialog = "Ouch! Missed the green zone—hit a red area and got a burn strike!"
                    
                    # Trigger grease fire flash + miss text
                    self.floating_texts.append(FloatingText("MISS!", self.arrow_x, self.bar_y + 40, (255, 50, 50)))
                    self.fire_flash_alpha = 200.0
                    self.spawn_burst_smoke(color=(50, 40, 40), count=25)

                self.temperature = 150.0

                if self.burn_strikes >= 3:
                    self.game_over = True
                    self.end_phase = 1
                    self.pending_emotion = "Terry_shocked"
                    self.pending_dialog_face = "unimpressed"
                    self.pending_dialog = "Well... on the bright side, we won't need any charcoal for the next BBQ."
                elif self.grill_progress >= 100:
                    self.game_over = True
                    self.end_phase = 1
                    if self.burn_strikes <= 1:
                        self.pending_emotion = "Terry_excited"
                        self.pending_dialog_face = "happy"
                        self.pending_dialog = "Absolute perfection! I should open a roadside stall after this, if I can't get a job after graduated."
                    else:
                        self.pending_emotion = "Terry_nervous"
                        self.pending_dialog_face = "nervous"
                        self.pending_dialog = "Well, the food is burned a bit, but extra crunchy I guess?"

                # Set the delay timer so the player can see the floating text/flash!
                self.dialog_timer = 0.8

    def on_key_press(self, key, modifiers):
        if self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.RETURN, arcade.key.SPACE):
                self.stop_typing_sound()
                self.dialog.advance()
                
                if not self.dialog.visible and self.game_over:
                    if self.end_phase == 1:
                        self.end_phase = 2
                        if self.burn_strikes >= 3:
                            audio.play("game_failed")
                            self.set_emotion("Terry_sad")
                            self.trigger_dialog("Total failure at the grill... Time to clean up and head back.", dialog_face="nervous")
                        else:
                            audio.play("game_success")
                            self.set_emotion("Terry_smile_excited")
                            self.trigger_dialog("All done! Time to serve the delicious barbecue feast.",dialog_face="happy")
                    elif self.end_phase == 2:
                        if self.burn_strikes >= 3:
                            achievements.unlock("bbq_charcoal")
                            self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=False))
                        else:
                            if self.burn_strikes == 0:
                                achievements.unlock("bbq_perfect_grill")
                            elif self.burn_strikes in (1, 2):
                                achievements.unlock("bbq_crunchy")
                            self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=True))
            return

        if key == arcade.key.ESCAPE:
            self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=False))