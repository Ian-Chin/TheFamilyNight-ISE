import math
import arcade

from . import audio, textures
from .config import (
    GRILL_0_BG, GRILL_20_BG, GRILL_50_BG, GRILL_100_BG,
    BURN_10_BG, BURN_20_BG, BURN_50_BG, BURN_100_BG,
    GRILL_FINISH_BG
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
        
        # We add the Finish screen as Index 5 to both arrays so it triggers regardless of performance
        self.grilled_bgs = [
            textures.background(GRILL_0_BG),      # 0: Start
            textures.background(GRILL_20_BG),     # 1: Progress 1
            textures.background(GRILL_50_BG),     # 2: Progress 2
            textures.background(GRILL_100_BG),    # 3: Progress 3
            textures.background(GRILL_100_BG),    # 4: Perfect Finish
            textures.background(GRILL_FINISH_BG)  # 5: Final Completion Showcase
        ]
        
        self.burned_bgs = [
            textures.background(GRILL_0_BG),      # 0: Start (Shared)
            textures.background(BURN_10_BG),      # 1: Burn 1
            textures.background(BURN_20_BG),      # 2: Burn 2
            textures.background(BURN_50_BG),      # 3: Burn 3
            textures.background(BURN_100_BG),     # 4: Ruined Finish
            textures.background(GRILL_FINISH_BG)  # 5: Final Completion Showcase
        ]
        
        self.stage_idx = 0  
        self.is_burned = False
        self.timer = 10.0  # 10 second countdown
        
        self.dialog = DialogBox()
        self.widgets = [self.dialog]
        self.typing_player = None
        self.relayout()

    def on_show_view(self):
        self.trigger_dialog("Time to BBQ! Click the SPIN button within 10 seconds before the food burns!")

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
            return  # Timer pauses while Terry is speaking!

        # Countdown Logic stops once we hit the final grilled/burned state (Index 4)
        if self.stage_idx < 4:
            self.timer -= delta_time
            if self.timer <= 0:
                self.is_burned = True
                self.stage_idx += 1
                self.timer = 10.0
                
                if self.stage_idx < 4:
                    self.trigger_dialog("It burned a bit, gotta be careful on the fire...")
                else:
                    self.trigger_dialog("Oh no... it's completely charred! Well, extra crunchy I guess?")

    def on_draw(self):
        self.clear()
        
        if self.is_burned:
            current_bg = self.burned_bgs[self.stage_idx]
        else:
            current_bg = self.grilled_bgs[self.stage_idx]
            
        arcade.draw_texture_rect(current_bg, cover_rect(current_bg, self.stage.viewport()))
        
        self.window.default_camera.use()
        
        # Only draw the timer while actively playing the mini-game (Indices 0-3)
        if not self.dialog.visible and self.stage_idx < 4:
            color = arcade.color.RED if self.timer <= 3 else arcade.color.WHITE
            arcade.draw_text(
                f"Time Left: {int(math.ceil(self.timer))}s",
                self.window.width / 2,
                self.window.height - 60,
                color,
                font_size=36,
                anchor_x="center",
                bold=True
            )
            
        self.dialog.draw()
        
    def on_mouse_press(self, x, y, button, modifiers):
        if self.dialog.visible:
            return
            
        canvas_x, canvas_y = self.stage.to_canvas(x, y)
        
        if canvas_x > 950 and canvas_y < 250 and button == arcade.MOUSE_BUTTON_LEFT:
            if self.stage_idx < 4:
                audio.play("ui_click")
                
                self.is_burned = False
                self.stage_idx += 1
                self.timer = 10.0
                
                if self.stage_idx < 4:
                    self.trigger_dialog("Nice spin! It's looking good, keep an eye on it.")
                else:
                    self.trigger_dialog("Perfectly grilled! Looks amazing.")

    def on_key_press(self, key, modifiers):
        if self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.RETURN):
                self.stop_typing_sound()
                self.dialog.advance()
                
                if not self.dialog.visible:
                    # Transition to the final completion screen after clearing the result dialogue
                    if self.stage_idx == 4:
                        self.stage_idx = 5
                        self.trigger_dialog("Finally, all the food is fully grilled! Let's dig in and enjoy the BBQ.")
                    
                    # Return to the backyard after clearing the final completion screen dialogue
                    elif self.stage_idx == 5:
                        self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=True))
            return

        if key == arcade.key.ESCAPE:
            self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True, grill_completed=True))