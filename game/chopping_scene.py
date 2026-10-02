import math
import random
import arcade

from . import audio, textures
from .config import (
    CHOP_MEAT_BG_1, CHOP_MEAT_BG_2, CHOP_MEAT_BG_3, CHOP_MEAT_BG_4, CHOP_MEAT_RUINED,
    CHOP_CARROT_BG_1, CHOP_CARROT_BG_2, CHOP_CARROT_BG_3, CHOP_CARROT_RUINED,
    CHOP_ONION_BG_1, CHOP_ONION_BG_2, CHOP_ONION_BG_3, CHOP_ONION_RUINED,
    CHOP_PEPPER_BG_1, CHOP_PEPPER_BG_2, CHOP_PEPPER_BG_3, CHOP_PEPPER_RUINED,
    CHOP_EGGPLANT_BG_1, CHOP_EGGPLANT_BG_2, CHOP_EGGPLANT_BG_3, CHOP_EGGPLANT_BG_4, CHOP_EGGPLANT_RUINED,
    CHOP_FINISH_BG, CHOP_FAILED_BG,
    WIDTH, HEIGHT
)
from .dialogue import DialogBox
from .views import StageView
from .bbq_scene import BbqView

def cover_rect(texture, rect):
    scale = max(rect.width / texture.width, rect.height / texture.height)
    return arcade.XYWH(rect.x, rect.y, texture.width * scale, texture.height * scale)

class ChoppingView(StageView):
    def __init__(self):
        super().__init__()
        
        self.backgrounds = [
            # Meat Sequence (0 - 4)
            textures.background(CHOP_MEAT_BG_1),      # 0
            textures.background(CHOP_MEAT_BG_2),      # 1
            textures.background(CHOP_MEAT_BG_3),      # 2
            textures.background(CHOP_MEAT_BG_4),      # 3
            textures.background(CHOP_MEAT_RUINED),    # 4
            
            # Carrot Sequence (5 - 8)
            textures.background(CHOP_CARROT_BG_1),    # 5
            textures.background(CHOP_CARROT_BG_2),    # 6
            textures.background(CHOP_CARROT_BG_3),    # 7
            textures.background(CHOP_CARROT_RUINED),  # 8
            
            # Onion Sequence (9 - 12)
            textures.background(CHOP_ONION_BG_1),     # 9
            textures.background(CHOP_ONION_BG_2),     # 10
            textures.background(CHOP_ONION_BG_3),     # 11
            textures.background(CHOP_ONION_RUINED),   # 12
            
            # Green Pepper Sequence (13 - 16)
            textures.background(CHOP_PEPPER_BG_1),    # 13
            textures.background(CHOP_PEPPER_BG_2),    # 14
            textures.background(CHOP_PEPPER_BG_3),    # 15
            textures.background(CHOP_PEPPER_RUINED),  # 16
            
            # Eggplant Sequence (17 - 21)
            textures.background(CHOP_EGGPLANT_BG_1),  # 17
            textures.background(CHOP_EGGPLANT_BG_2),  # 18
            textures.background(CHOP_EGGPLANT_BG_3),  # 19
            textures.background(CHOP_EGGPLANT_BG_4),  # 20
            textures.background(CHOP_EGGPLANT_RUINED),# 21
            
            # Final Scenes (22 - 23)
            textures.background(CHOP_FINISH_BG),      # 22 (Total Success)
            textures.background(CHOP_FAILED_BG),      # 23 (Total Failure)
        ]
        self.stage_idx = 0  
        
        # --- Core Game Stats ---
        self.progress = 0       
        self.max_lives = 3
        self.lives = self.max_lives
        self.streak = 0  # Tracks consecutive successful hits
        
        # --- UI Sprites ---
        # 1. Start with Terry Original
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
        self.widgets = [self.dialog]
        self.typing_player = None
        self.relayout()

    def set_emotion(self, emotion_name):
        """Helper to quickly change Terry's portrait texture."""
        self.terry_portrait.texture = arcade.load_texture(f"assets/emotions/{emotion_name}.png")

    def on_show_view(self):
        self.trigger_dialog("Let's prep! The CHOP button will appear randomly. Click it within 2 seconds, or you lose a heart!")

    def trigger_dialog(self, text):
        audio.play("dialog_open")
        self.dialog.open("Terry", text)
        self.typing_player = audio.play("dialog_type", loop=True)

    def stop_typing_sound(self):
        if self.typing_player:
            audio.bank().stop(self.typing_player)
            self.typing_player = None

    def spawn_button(self):
        self.chop_button.center_x = random.randint(200, WIDTH - 300)
        self.chop_button.center_y = random.randint(200, HEIGHT - 200)
        self.button_active = True
        self.slice_timer = 2.0

    def fail_slice(self):
        self.button_active = False
        self.lives -= 1
        self.streak = 0  # Reset streak on failure
        
        self.breaking_idx = self.max_lives - self.lives - 1
        if 0 <= self.breaking_idx < self.max_lives:
            self.hearts[self.breaking_idx].texture = textures.ui_image("Character_HP_broke_into_half.png")
            self.heart_anim_timer = 0.2  
            self.heart_anim_state = 1
            self.pending_fail_dialog = True 
            
            if self.stage_idx < 5:
                self.stage_idx = 4   
            elif 5 <= self.stage_idx < 9:
                self.stage_idx = 8   
            elif 9 <= self.stage_idx < 13:
                self.stage_idx = 12  
            elif 13 <= self.stage_idx < 17:
                self.stage_idx = 16  
            elif 17 <= self.stage_idx < 22:
                self.stage_idx = 21  

    def on_update(self, delta_time):
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
                            # 6. Failed and lost 3 HP -> Terry Sad
                            self.stage_idx = 23
                            self.set_emotion("Terry_sad")
                            self.trigger_dialog("I ruined too much food! I have to restart the whole prep...")
                        else:
                            # 4. Lost an HP -> Terry Shocked
                            self.set_emotion("Terry_shocked")
                            self.trigger_dialog("Oh no! I missed the cut and ruined this piece. Moving to the next food...")

        if self.dialog.visible:
            self.dialog.update(delta_time)
            if not self.dialog.typing:
                self.stop_typing_sound()
            return

        if self.button_active:
            self.slice_timer -= delta_time
            if self.slice_timer <= 0:
                self.fail_slice()

    def on_draw(self):
        self.clear()
        
        current_bg = self.backgrounds[self.stage_idx]
        arcade.draw_texture_rect(current_bg, cover_rect(current_bg, self.stage.viewport()))
        
        self.window.default_camera.use()
        
        # Hide the dynamic portrait ONLY on the Finish screen (22)
        if self.stage_idx != 22:
            self.portrait_list.draw(pixelated=True)
            
        # Hide the rest of the HUD completely on both Finish (22) and Fail (23) screens
        if self.stage_idx < 22:
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
            
        self.dialog.draw()
        
    def on_mouse_press(self, x, y, button, modifiers):
        if self.dialog.visible or not self.button_active:
            return
            
        canvas_x, canvas_y = self.stage.to_canvas(x, y)
        
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.chop_button.collides_with_point((canvas_x, canvas_y)):
                audio.play("ui_click")
                self.button_active = False
                self.stage_idx += 1
                
                # Successful Click Emotion Handling
                self.streak += 1
                if self.streak > 1:
                    # 3. Continuous streak -> Terry Excited
                    self.set_emotion("Terry_excited")
                else:
                    # 2. Single successful click -> Terry Smile Excited
                    self.set_emotion("Terry_smile_excited")
                
                if self.stage_idx == 3:
                    self.progress += 20
                    self.trigger_dialog("Perfect! Meat is prepped. (Progress 20%)")
                elif self.stage_idx == 7:
                    self.progress += 20
                    self.trigger_dialog("Nice and crunchy! Carrots are done. (Progress 40%)")
                elif self.stage_idx == 11:
                    self.progress += 20
                    self.trigger_dialog("My eyes are watering... but the onions are done! (Progress 60%)")
                elif self.stage_idx == 15:
                    self.progress += 20
                    self.trigger_dialog("Green peppers are sliced perfectly! (Progress 80%)")
                elif self.stage_idx == 20:
                    self.progress += 20
                    self.trigger_dialog("The eggplant is ready! (Progress 100%)")
                else:
                    self.spawn_button()

    def on_key_press(self, key, modifiers):
        if self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.RETURN):
                self.stop_typing_sound()
                self.dialog.advance()
                
                if not self.dialog.visible:
                    # Restart Game if they just closed the Total Failure dialogue
                    if self.lives <= 0:
                        self.window.show_view(ChoppingView())
                        return
                        
                    # Meat finished (3) or ruined (4) -> Move to Carrots
                    if self.stage_idx in (3, 4):
                        # 5. Determine emotion based on previous success/fail
                        self.set_emotion("Terry_nervous" if self.stage_idx == 4 else "Terry_original")
                        self.streak = 0
                        self.stage_idx = 5
                        self.trigger_dialog("Let's slice up these fresh carrots next!")
                    
                    # Carrots finished (7) or ruined (8) -> Move to Onions
                    elif self.stage_idx in (7, 8):
                        self.set_emotion("Terry_nervous" if self.stage_idx == 8 else "Terry_original")
                        self.streak = 0
                        self.stage_idx = 9
                        self.trigger_dialog("Alright, onions are next. Let's chop fast before I cry!")
                        
                    # Onions finished (11) or ruined (12) -> Move to Green Peppers
                    elif self.stage_idx in (11, 12):
                        self.set_emotion("Terry_nervous" if self.stage_idx == 12 else "Terry_original")
                        self.streak = 0
                        self.stage_idx = 13
                        self.trigger_dialog("Time for the green peppers!")
                        
                    # Peppers finished (15) or ruined (16) -> Move to Eggplant
                    elif self.stage_idx in (15, 16):
                        self.set_emotion("Terry_nervous" if self.stage_idx == 16 else "Terry_original")
                        self.streak = 0
                        self.stage_idx = 17
                        self.trigger_dialog("Last but not least, the eggplant!")
                        
                    # Eggplant finished (20) or ruined (21) -> Show FINISH SCENE
                    elif self.stage_idx in (20, 21):
                        self.stage_idx = 22
                        self.trigger_dialog("All ingredients are prepped! Time to fire up the BBQ.")
                        
                    # Finish screen closed (22) -> Exit to Garden
                    elif self.stage_idx == 22:
                        self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=False))

                    elif self.stage_idx in (0, 5, 9, 13, 17) and not self.button_active:
                        self.spawn_button()
            return

        if key == arcade.key.ESCAPE:
            self.window.show_view(BbqView(chop_unlocked=True))