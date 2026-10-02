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

class GrillingView(StageView):
    def __init__(self):
        super().__init__()
        
        self.grilled_bgs = [
            textures.background(GRILL_0_BG),      
            textures.background(GRILL_20_BG),     
            textures.background(GRILL_50_BG),     
            textures.background(GRILL_100_BG),    
            textures.background(GRILL_100_BG),    
            textures.background(GRILL_FINISH_BG)  
        ]
        
        self.burned_bgs = [
            textures.background(GRILL_0_BG),      
            textures.background(BURN_10_BG),      
            textures.background(BURN_20_BG),      
            textures.background(BURN_50_BG),      
            textures.background(BURN_100_BG),     
            textures.background(GRILL_FAILED_BG)  
        ]
        
        self.stage_idx = 0  
        self.is_burned = False
        
        # --- NEW: Heat Mechanics ---
        self.current_heat = "normal"
        self.heat_timer = 0.5  # Switches every 0.5 second
        
        # Dictionary to store the textures and dynamic text for each state
        self.heat_data = {
            "low": {
                "texture": textures.ui_image("Temperature_bar_low_heat.png"), 
                "text": "100°C"
            },
            "normal": {
                "texture": textures.ui_image("Temperature_bar_normal.png"), 
                "text": "200°C"
            },
            "maxed": {
                "texture": textures.ui_image("Temperature_bar_maxed_heat.png"), 
                "text": "350°C"
            }
        }

        # --- UI Sprites ---
        # 1. Terry Portrait (Updated position/size)
        self.terry_portrait = arcade.Sprite("assets/emotions/Terry_original.png", scale=0.7)
        self.terry_portrait.center_x = 1170
        self.terry_portrait.center_y = 600
        
        self.portrait_list = arcade.SpriteList()
        self.portrait_list.append(self.terry_portrait)

        # 2. SPIN Button (Updated position/size)
        self.spin_button = arcade.Sprite(textures.ui_image("SPIN_button.png"), scale=0.7)
        self.spin_button.center_x = 1170
        self.spin_button.center_y = 120
        
        self.button_list = arcade.SpriteList()
        self.button_list.append(self.spin_button)

        # 3. Temperature Bar (Updated position/size)
        self.temp_bar = arcade.Sprite(self.heat_data[self.current_heat]["texture"], scale=1.2)
        self.temp_bar.center_x = 80
        self.temp_bar.center_y = HEIGHT / 2
        
        self.ui_list = arcade.SpriteList()
        self.ui_list.append(self.temp_bar)
        
        # --- Scene State ---
        self.dialog = DialogBox()
        self.widgets = [self.dialog]
        self.typing_player = None
        self.relayout()

    def on_show_view(self):
        self.trigger_dialog("Time to BBQ! Wait for the temperature to be normal (200°C) before you hit SPIN!")

    def trigger_dialog(self, text):
        audio.play("dialog_open")
        self.dialog.open("Terry", text)
        self.typing_player = audio.play("dialog_type", loop=True)

    def stop_typing_sound(self):
        if self.typing_player:
            audio.bank().stop(self.typing_player)
            self.typing_player = None

    def on_update(self, delta_time):
        if self.dialog.visible:
            self.dialog.update(delta_time)
            if not self.dialog.typing:
                self.stop_typing_sound()
            return  

        # --- NEW: Dynamic Heat Switching ---
        if self.stage_idx < 4:
            self.heat_timer -= delta_time
            if self.heat_timer <= 0:
                self.heat_timer = 0.5  # Reset timer to 0.5 second
                
                # Pick a random new heat state that is DIFFERENT from the current one
                options = ["low", "normal", "maxed"]
                options.remove(self.current_heat)
                self.current_heat = random.choice(options)
                
                # Update the texture immediately
                self.temp_bar.texture = self.heat_data[self.current_heat]["texture"]

    def on_draw(self):
        self.clear()
        
        # Draw dynamic background based on burn state
        if self.is_burned:
            current_bg = self.burned_bgs[self.stage_idx]
        else:
            current_bg = self.grilled_bgs[self.stage_idx]
            
        arcade.draw_texture_rect(current_bg, cover_rect(current_bg, self.stage.viewport()))
        
        self.window.default_camera.use()
        
        # Draw UI only if we are not on the final Finish/Fail screens (Index 5)
        if self.stage_idx < 5:
            self.portrait_list.draw(pixelated=True)
            self.ui_list.draw(pixelated=True)
            
            # --- Dynamic Temperature Labels ---
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
            
            arcade.draw_text(
                self.heat_data[self.current_heat]["text"], 
                self.temp_bar.center_x, 
                self.temp_bar.top + 20, 
                arcade.color.WHITE, 
                24, 
                bold=True, 
                anchor_x="center", 
                font_name="Kenney Pixel Square"
            )
            
            # Draw interactive elements when dialogue is not blocking
            if not self.dialog.visible and self.stage_idx < 4:
                self.button_list.draw(pixelated=True)
            
        self.dialog.draw()
        
    def on_mouse_press(self, x, y, button, modifiers):
        if self.dialog.visible:
            return
            
        canvas_x, canvas_y = self.stage.to_canvas(x, y)
        
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.stage_idx < 4 and self.spin_button.collides_with_point((canvas_x, canvas_y)):
                audio.play("ui_click")
                
                # --- NEW: Branching Logic based on Heat State ---
                if self.current_heat == "normal":
                    # Success
                    self.is_burned = False
                    self.stage_idx += 1
                    
                    if self.stage_idx < 4:
                        self.trigger_dialog("Nice spin! The temperature was perfect.")
                    else:
                        self.trigger_dialog("Perfectly grilled! Looks amazing.")
                        
                elif self.current_heat == "maxed":
                    # Failed/Burned
                    self.is_burned = True
                    self.stage_idx += 1
                    
                    if self.stage_idx < 4:
                        self.trigger_dialog("Ouch! The fire was way too hot and it burned a bit!")
                    else:
                        self.trigger_dialog("Oh no... it's completely charred! Well, extra crunchy I guess?")
                        
                elif self.current_heat == "low":
                    # Neutral/Retry (Do not advance the stage_idx)
                    self.trigger_dialog("The fire is too low right now... nothing happened. Wait for it to heat up!")

    def on_key_press(self, key, modifiers):
        if self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.RETURN):
                self.stop_typing_sound()
                self.dialog.advance()
                
                if not self.dialog.visible:
                    # Transition logic for the end of the game
                    if self.stage_idx == 4:
                        self.stage_idx = 5
                        if self.is_burned:
                            self.trigger_dialog("This is a disaster. I'll have to start over and try grilling it again.")
                        else:
                            self.trigger_dialog("Finally, all the food is fully grilled! Let's dig in and enjoy the BBQ.")
                    
                    elif self.stage_idx == 5:
                        if self.is_burned:
                            self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=False))
                        else:
                            self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=True))
            return

        if key == arcade.key.ESCAPE:
            self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=False))