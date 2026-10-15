import math
import random
import arcade

from . import audio, textures
from .config import (
    GRILL_0_BG, GRILL_20_BG, GRILL_50_BG, GRILL_100_BG,
    BURN_10_BG, BURN_20_BG, BURN_50_BG, BURN_100_BG,
    GRILL_FINISH_BG, GRILL_FAILED_BG,
    WIDTH, HEIGHT
)
from .dialogue import DialogBox
from .views import StageView
from .bbq_scene import BbqView

def cover_rect(texture, rect):
    scale = max(rect.width / texture.width, rect.height / texture.height)
    return arcade.XYWH(rect.x, rect.y, texture.width * scale, texture.height * scale)

# --- Procedural Smoke Particle (Adapted from Lab09.py) ---
class SmokeParticle:
    def __init__(self, x, y, color):
        self.x = x + random.uniform(-10, 10)
        self.y = y + random.uniform(-10, 10)

        self.vx = random.uniform(-25, 25)
        self.vy = random.uniform(60, 100)

        self.radius = random.uniform(8, 16)
        self.max_radius = random.uniform(60, 120)

        self.age = 0.0
        self.lifetime = random.uniform(2.0, 4.0)

        self.drift = random.uniform(-25, 25)
        self.color = color

    def update(self, dt):
        self.age += dt
        progress = min(self.age / self.lifetime, 1.0)

        self.y += self.vy * dt
        spread = 0.3 + progress
        self.x += (self.vx + self.drift * spread) * dt
        self.radius = 10 + (self.max_radius - 10) * progress

        self.drift += random.uniform(-12, 12) * dt
        self.drift = max(-45, min(45, self.drift))

    def draw(self):
        progress = min(self.age / self.lifetime, 1.0)
        fade = (1.0 - progress) ** 1.5

        layers = [
            (1.00, 8),
            (0.82, 10),
            (0.64, 12),
            (0.46, 15),
            (0.28, 18),
        ]

        for scale, base_alpha in layers:
            radius = self.radius * scale
            alpha = int(base_alpha * fade)

            if alpha > 0:
                arcade.draw_circle_filled(self.x, self.y, radius, (*self.color, alpha))

    @property
    def is_dead(self):
        return self.age >= self.lifetime


class GrillingView(StageView):
    def __init__(self):
        super().__init__()
        
        # --- Core Two-Track Game Stats ---
        self.grill_progress = 0   
        self.burn_strikes = 0     
        self.game_over = False
        
        # --- Temperature State & Heat Textures ---
        # Starts at a comfortable baseline
        self.temperature = 150.0  
        self.temp_textures = {
            "low": textures.ui_image("Temperature_bar_low_heat.png"),
            "normal": textures.ui_image("Temperature_bar_normal.png"),
            "maxed": textures.ui_image("Temperature_bar_maxed_heat.png"),
        }
        
        # --- Tachometer Layout ---
        self.bar_width = 400
        self.bar_height = 30
        self.bar_x = WIDTH / 2
        self.bar_y = 100
        
        self.arrow_x = self.bar_x - (self.bar_width / 2)
        self.arrow_dir = 1
        self.arrow_base_speed = 500.0  
        
        # Particle System
        self.particles = []

        # --- UI Sprites ---
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

        # --- Scene State ---
        self.dialog = DialogBox()
        self.widgets = [self.dialog]
        self.typing_player = None
        
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

    def spawn_smoke(self, color):
        for _ in range(25):
            self.particles.append(SmokeParticle(WIDTH / 2, HEIGHT / 2 - 50, color))

    def on_show_view(self):
        self.trigger_dialog("Click SPIN when the arrow hits the green zone! If you wait too long, the grill overheats!")

    def trigger_dialog(self, text):
        audio.play("dialog_open")
        self.dialog.open("Terry", text)
        self.typing_player = audio.play("dialog_type", loop=True)

    def stop_typing_sound(self):
        if self.typing_player:
            audio.bank().stop(self.typing_player)
            self.typing_player = None

    def get_current_bg(self):
        if self.game_over:
            if self.burn_strikes >= 3:
                return textures.background(GRILL_FAILED_BG)
            elif self.burn_strikes > 0:
                return textures.background(BURN_100_BG)
            else:
                return textures.background(GRILL_FINISH_BG)
                
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
        """Calculates current yellow and green widths based on heat."""
        # Heat factor: 0.0 (cold) to 1.0 (overheated)
        heat_ratio = max(0.0, min(1.0, (self.temperature - 100.0) / 250.0))
        
        # Green shrinks from 70px down to 20px
        green_w = max(20.0, 70.0 - (50.0 * heat_ratio))
        # Yellow shrinks from 260px down to 80px
        yellow_w = max(80.0, 260.0 - (180.0 * heat_ratio))
        
        return yellow_w, green_w

    def on_update(self, delta_time):
        for p in self.particles:
            p.update(delta_time)
        self.particles = [p for p in self.particles if not p.is_dead]

        if self.dialog.visible:
            self.dialog.update(delta_time)
            if not self.dialog.typing:
                self.stop_typing_sound()
            return  

        if not self.game_over:
            # 1. Temperature builds up over time SLOWER (Reduced from 15.0 to 6.0)
            self.temperature = min(400.0, self.temperature + (6.0 * delta_time))
            
            # Update physical sprite texture based on heat thresholds
            if self.temperature < 160:
                self.temp_bar.texture = self.temp_textures["low"]
            elif self.temperature < 280:
                self.temp_bar.texture = self.temp_textures["normal"]
            else:
                self.temp_bar.texture = self.temp_textures["maxed"]

            # Overheat penalty if left completely unattended
            if self.temperature >= 380.0:
                self.burn_strikes += 1
                self.temperature = 150.0  # Full reset back to safe levels
                self.spawn_smoke((30, 25, 25))
                self.set_emotion("Terry_shocked")
                
                if self.burn_strikes >= 3:
                    self.game_over = True
                    self.set_emotion("Terry_sad")
                    self.trigger_dialog("The grill caught fire from waiting too long! The food is ruined.")
                else:
                    self.trigger_dialog("The heat flared up because we waited too long! It got charred!")
                return

            # 2. Dynamic Arrow Movement
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

    def on_draw(self):
        self.clear()
        
        # 1. Background
        self.window.default_camera.use()
        current_bg = self.get_current_bg()
        arcade.draw_texture_rect(current_bg, cover_rect(current_bg, self.stage.viewport()))
        
        # 2. Scaled Canvas UI & Particles
        self.camera.use()
        
        for p in self.particles:
            p.draw()
            
        self.portrait_list.draw(pixelated=True)
        
        if not self.game_over:
            self.ui_list.draw(pixelated=True)
            
            arcade.draw_text(
                "TEMP", 
                self.temp_bar.center_x, 
                self.temp_bar.top + 50,
                arcade.color.WHITE, 
                20, 
                bold=True, 
                anchor_x="center", 
                font_name="Kenney Pixel Square"
            )
            
            temp_color = arcade.color.RED if self.temperature >= 280 else arcade.color.WHITE
            arcade.draw_text(
                f"{int(self.temperature)}°C", 
                self.temp_bar.center_x, 
                self.temp_bar.top + 20, 
                temp_color, 
                24, 
                bold=True, 
                anchor_x="center", 
                font_name="Kenney Pixel Square"
            )

            # --- Dynamically Sized Tachometer ---
            yellow_w, green_w = self.get_zone_widths()

            # Red Base (Full Bar Width)
            arcade.draw_rect_filled(arcade.XYWH(self.bar_x, self.bar_y, self.bar_width, self.bar_height), arcade.color.CRIMSON)
            # Yellow Safe Zone (Shrinking)
            arcade.draw_rect_filled(arcade.XYWH(self.bar_x, self.bar_y, yellow_w, self.bar_height), arcade.color.GOLD)
            # Green Sweet Spot (Shrinking)
            arcade.draw_rect_filled(arcade.XYWH(self.bar_x, self.bar_y, green_w, self.bar_height), arcade.color.APPLE_GREEN)
            
            # Frame
            arcade.draw_rect_outline(arcade.XYWH(self.bar_x, self.bar_y, self.bar_width, self.bar_height), arcade.color.DARK_GRAY, 4)
            
            # Arrow Indicator
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
            
        # 3. Dialogue
        self.window.default_camera.use()
        self.dialog.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.dialog.visible or self.game_over:
            return
            
        canvas_x, canvas_y = self.stage.to_canvas(x, y)
        
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.spin_button.collides_with_point((canvas_x, canvas_y)):
                audio.play("ui_click")
                
                yellow_w, green_w = self.get_zone_widths()
                dist_from_center = abs(self.arrow_x - self.bar_x)
                
                if dist_from_center <= (green_w / 2):
                    self.grill_progress = min(100, self.grill_progress + 25)
                    self.spawn_smoke((220, 230, 240))
                    self.set_emotion("Terry_excited")
                    dialog_text = "Flawless timing! The coals are perfectly aerated."
                    
                elif dist_from_center <= (yellow_w / 2):
                    self.grill_progress = min(100, self.grill_progress + 10)
                    self.spawn_smoke((140, 140, 140))
                    self.set_emotion("Terry_smile_excited")
                    dialog_text = "Good spin! Cooking evenly."
                    
                else:
                    self.burn_strikes += 1
                    self.spawn_smoke((40, 30, 30))
                    self.set_emotion("Terry_nervous")
                    dialog_text = "Ouch! Hit the danger zone—it charred the skewers!"

                # --- NEW: Fully reset the temperature and tachometer sizes ---
                self.temperature = 150.0

                if self.burn_strikes >= 3:
                    self.game_over = True
                    self.set_emotion("Terry_sad")
                    self.trigger_dialog("Oh no... the food is completely ruined! I have to start over.")
                elif self.grill_progress >= 100:
                    self.game_over = True
                    if self.burn_strikes == 0:
                        self.set_emotion("Terry_excited")
                        self.trigger_dialog("Flawless! This BBQ looks absolutely perfect!")
                    else:
                        self.set_emotion("Terry_nervous")
                        self.trigger_dialog("It's a bit extra crispy... but it still smells great!")
                else:
                    self.trigger_dialog(dialog_text)

    def on_key_press(self, key, modifiers):
        if self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.RETURN):
                self.stop_typing_sound()
                self.dialog.advance()
                
                if not self.dialog.visible and self.game_over:
                    if self.burn_strikes >= 3:
                        self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=False))
                    else:
                        self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=True))
            return

        if key == arcade.key.ESCAPE:
            self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=False))