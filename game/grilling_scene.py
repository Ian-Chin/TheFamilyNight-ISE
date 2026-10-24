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
        self.color = color  # RGB Tuple (R, G, B)

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

        layers = [
            (1.00, 12),
            (0.82, 16),
            (0.64, 20),
            (0.46, 25),
            (0.28, 30),
        ]

        r, g, b = self.color
        for scale, base_alpha in layers:
            radius = self.radius * scale
            alpha = int(base_alpha * fade)

            if alpha > 0:
                arcade.draw_circle_filled(
                    self.x,
                    self.y,
                    radius,
                    (r, g, b, alpha),
                )

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
        self.emit_interval = 0.18  # Puffs new smoke particles continuously

    def update(self, dt, particles):
        self.emit_timer += dt
        if self.emit_timer >= self.emit_interval:
            self.emit_timer = 0.0
            particles.append(SmokeParticle(self.x, self.y, self.color))


class GrillingView(StageView):
    def __init__(self):
        super().__init__()
        
        # --- Core Two-Track Game Stats ---
        self.grill_progress = 0   
        self.burn_strikes = 0     
        self.game_over = False
        self.end_phase = 0  # 0: Playing, 1: Showing Result Food Image, 2: Showing Finish/Fail Scene
        
        self.has_spun = False
        
        # --- Progressive Smoke & Time Tracking ---
        self.time_since_last_action = 0.0
        self.smoke_tier = 0
        self.smoke_emitters = []
        
        # --- Smoke Spawn Area Bounds ---
        self.smoke_min_x = WIDTH / 2 - 360
        self.smoke_max_x = WIDTH / 2 + 360
        self.smoke_min_y = HEIGHT / 2 - 240
        self.smoke_max_y = HEIGHT / 2 + 220
        
        # --- Temperature State & Heat Textures ---
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
        self.trigger_dialog("Click SPIN when the arrow hits the green zone! Watch the heat so we don't burn the skewers!")

    def on_hide_view(self):
        audio.bank().stop(self.grilling_player)
        self.grilling_player = None
        self.stop_typing_sound()

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
            if self.end_phase == 1:
                if self.burn_strikes >= 3:
                    return textures.background(BURN_100_BG) 
                elif self.burn_strikes == 2:
                    return textures.background(BURN_50_BG)  
                else:
                    return textures.background(GRILL_100_BG) 
            elif self.end_phase == 2:
                if self.burn_strikes >= 3:
                    return textures.background(GRILL_FAILED_BG) 
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
        heat_ratio = max(0.0, min(1.0, (self.temperature - 100.0) / 200.0))
        green_w = max(20.0, 70.0 - (50.0 * heat_ratio))
        yellow_w = max(80.0, 260.0 - (180.0 * heat_ratio))
        return yellow_w, green_w

    def on_update(self, delta_time):
        for p in self.particles:
            p.update(delta_time)
        self.particles = [p for p in self.particles if not p.is_dead]

        for emitter in self.smoke_emitters:
            emitter.update(delta_time, self.particles)

        if not self.game_over and not self.dialog.visible:
            if self.grilling_player is None:
                self.grilling_player = audio.play("grilling", loop=True)
        else:
            if self.grilling_player is not None:
                audio.bank().stop(self.grilling_player)
                self.grilling_player = None

        if self.dialog.visible:
            self.dialog.update(delta_time)
            if not self.dialog.typing:
                self.stop_typing_sound()
            return  

        if not self.game_over:
            self.temperature = min(300.0, self.temperature + (15.0 * delta_time))
            self.time_since_last_action += delta_time
            
            min_x, max_x = self.smoke_min_x, self.smoke_max_x
            min_y, max_y = self.smoke_min_y, self.smoke_max_y

            # --- Progressive Smoke Milestones (2s, 5s, 8s) ---
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
                self.temperature = 150.0  
                self.time_since_last_action = 0.0
                self.smoke_tier = 0
                self.smoke_emitters.clear()
                self.spawn_burst_smoke(color=(70, 60, 60), count=15)
                
                if self.burn_strikes >= 3:
                    self.game_over = True
                    self.end_phase = 1
                    self.set_emotion("Terry_shocked")
                    if not self.has_spun:
                        self.trigger_dialog("Note to self: staring blankly at the tachometer doesn't stop the heat.")
                    else:
                        self.trigger_dialog("Well... on the bright side, we won't need any charcoal for the next BBQ.")
                else:
                    self.set_emotion("Terry_nervous")
                    audio.play("hp_reduced")
                    self.trigger_dialog("The grill flared up because we waited too long! A burn strike added.")
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

    def on_draw(self):
        self.clear()
        
        self.window.default_camera.use()
        current_bg = self.get_current_bg()
        arcade.draw_texture_rect(current_bg, cover_rect(current_bg, self.stage.viewport()))
        
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
            
            temp_color = arcade.color.RED if self.temperature >= 250 else arcade.color.WHITE
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
            
        self.window.default_camera.use()
        self.dialog.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.dialog.visible or self.game_over:
            return
            
        canvas_x, canvas_y = self.stage.to_canvas(x, y)
        
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.spin_button.collides_with_point((canvas_x, canvas_y)):
                audio.play("click_button")
                
                self.has_spun = True
                self.time_since_last_action = 0.0
                self.smoke_tier = 0
                self.smoke_emitters.clear()  # Reset smoke sources on spin action
                
                yellow_w, green_w = self.get_zone_widths()
                dist_from_center = abs(self.arrow_x - self.bar_x)
                
                if dist_from_center <= (green_w / 2):
                    self.grill_progress = min(100, self.grill_progress + 25)
                    self.spawn_burst_smoke(color=(220, 220, 220), count=8)
                    self.set_emotion("Terry_excited")
                    dialog_text = "Flawless timing! The coals are perfectly aerated."
                    
                elif dist_from_center <= (yellow_w / 2):
                    self.grill_progress = min(100, self.grill_progress + 10)
                    self.spawn_burst_smoke(color=(170, 170, 170), count=8)
                    self.set_emotion("Terry_smile_excited")
                    dialog_text = "Good spin! Cooking evenly."
                    
                else:
                    self.burn_strikes += 1
                    self.spawn_burst_smoke(color=(110, 90, 90), count=12)
                    self.set_emotion("Terry_nervous")
                    audio.play("hp_reduced")
                    dialog_text = "Ouch! Missed the green zone—hit a red area and got a burn strike!"

                self.temperature = 150.0

                if self.burn_strikes >= 3:
                    self.game_over = True
                    self.end_phase = 1
                    self.set_emotion("Terry_shocked")
                    if not self.has_spun:
                        self.trigger_dialog("Note to self: staring blankly at the tachometer doesn't stop the heat.")
                    else:
                        self.trigger_dialog("Well... on the bright side, we won't need any charcoal for the next BBQ.")
                elif self.grill_progress >= 100:
                    self.game_over = True
                    self.end_phase = 1
                    if self.burn_strikes <= 1:
                        self.set_emotion("Terry_excited")
                        self.trigger_dialog("Absolute perfection! I should open a roadside stall after this, if i can't get a job after graduated.")
                    else:
                        self.set_emotion("Terry_nervous")
                        self.trigger_dialog("Well, the food is burned a bit, but extra crunchy I guess?")
                else:
                    self.trigger_dialog(dialog_text)

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
                            self.trigger_dialog("Total failure at the grill... Time to clean up and head back.")
                        else:
                            audio.play("game_success")
                            self.set_emotion("Terry_smile_excited")
                            self.trigger_dialog("All done! Time to serve the delicious barbecue feast.")
                    elif self.end_phase == 2:
                        if self.burn_strikes >= 3:
                            self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=False))
                        else:
                            self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=True))
            return

        if key == arcade.key.ESCAPE:
            self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=False))