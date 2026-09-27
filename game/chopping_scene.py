import arcade

from . import audio, textures
from .config import (
    CHOP_MEAT_BG_1, CHOP_MEAT_BG_2, CHOP_MEAT_BG_3, CHOP_MEAT_BG_4,
    CHOP_CARROT_BG_1, CHOP_CARROT_BG_2, CHOP_CARROT_BG_3,
    CHOP_ONION_BG_1, CHOP_ONION_BG_2, CHOP_ONION_BG_3,
    CHOP_PEPPER_BG_1, CHOP_PEPPER_BG_2, CHOP_PEPPER_BG_3,
    CHOP_EGGPLANT_BG_1, CHOP_EGGPLANT_BG_2, CHOP_EGGPLANT_BG_3, CHOP_EGGPLANT_BG_4,
    CHOP_FINISH_BG
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
        
        # Load all 18 stages into the master sequence list
        self.backgrounds = [
            textures.background(CHOP_MEAT_BG_1),      # 0: Meat Begin
            textures.background(CHOP_MEAT_BG_2),      # 1: Meat Deep
            textures.background(CHOP_MEAT_BG_3),      # 2: Meat Half
            textures.background(CHOP_MEAT_BG_4),      # 3: Meat Pieces
            
            textures.background(CHOP_CARROT_BG_1),    # 4: Carrot Begin
            textures.background(CHOP_CARROT_BG_2),    # 5: Carrot Half
            textures.background(CHOP_CARROT_BG_3),    # 6: Carrot Pieces
            
            textures.background(CHOP_ONION_BG_1),     # 7: Onion Begin
            textures.background(CHOP_ONION_BG_2),     # 8: Onion Half
            textures.background(CHOP_ONION_BG_3),     # 9: Onion Pieces
            
            textures.background(CHOP_PEPPER_BG_1),    # 10: Pepper Begin
            textures.background(CHOP_PEPPER_BG_2),    # 11: Pepper Half
            textures.background(CHOP_PEPPER_BG_3),    # 12: Pepper Pieces
            
            textures.background(CHOP_EGGPLANT_BG_1),  # 13: Eggplant Begin
            textures.background(CHOP_EGGPLANT_BG_2),  # 14: Eggplant Deep
            textures.background(CHOP_EGGPLANT_BG_3),  # 15: Eggplant Half
            textures.background(CHOP_EGGPLANT_BG_4),  # 16: Eggplant Pieces
            
            textures.background(CHOP_FINISH_BG),      # 17: Final Completion Screen
        ]
        self.stage_idx = 0  
        
        self.dialog = DialogBox()
        self.widgets = [self.dialog]
        self.typing_player = None
        
        self.relayout()

    def on_show_view(self):
        self.trigger_dialog("Let's start chopping the big meat...")

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

    def on_draw(self):
        self.clear()
        
        current_bg = self.backgrounds[self.stage_idx]
        arcade.draw_texture_rect(
            current_bg, 
            cover_rect(current_bg, self.stage.viewport())
        )
        
        self.window.default_camera.use()
        self.dialog.draw()
        
    def on_mouse_press(self, x, y, button, modifiers):
        if self.dialog.visible:
            return
            
        canvas_x, canvas_y = self.stage.to_canvas(x, y)
        
        if canvas_x > 950 and canvas_y < 250 and button == arcade.MOUSE_BUTTON_LEFT:
            audio.play("ui_click")
            
            if self.stage_idx in (0, 1, 2, 4, 5, 7, 8, 10, 11, 13, 14, 15):
                self.stage_idx += 1
                
                if self.stage_idx == 1:
                    self.trigger_dialog("This meat is too big, I need to chop it into half then only can chop to the smaller pieces.")
                elif self.stage_idx == 3:
                    self.trigger_dialog("Finally the meat is chopped, now is vegetables time.")
                    
                elif self.stage_idx == 5:
                    self.trigger_dialog("Nice and crunchy! Just a few more chops to get them bite-sized.")
                elif self.stage_idx == 6:
                    self.trigger_dialog("Perfect! That's it for the carrots.")
                    
                elif self.stage_idx == 8:
                    self.trigger_dialog("Ouch, my eyes are starting to water already!")
                elif self.stage_idx == 9:
                    self.trigger_dialog("Phew! Finished the onions. What is next?")
                    
                elif self.stage_idx == 11:
                    self.trigger_dialog("Crunchy green peppers. These will look great on the grill.")
                elif self.stage_idx == 12:
                    self.trigger_dialog("Peppers are done! Only one vegetable left.")
                    
                elif self.stage_idx == 14:
                    self.trigger_dialog("This eggplant is pretty thick...")
                elif self.stage_idx == 15:
                    self.trigger_dialog("Almost there, just need to slice these into rounds.")
                elif self.stage_idx == 16:
                    self.trigger_dialog("Perfect, that's the last of the eggplant.")

    def on_key_press(self, key, modifiers):
        if self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.RETURN):
                self.stop_typing_sound()
                self.dialog.advance()
                
                # Automatic scene transitions after clearing specific dialogues
                if not self.dialog.visible:
                    if self.stage_idx == 3:
                        self.stage_idx = 4
                        self.trigger_dialog("Let's slice up these fresh carrots next! Gotta make sure they are chopped evenly.")
                    
                    elif self.stage_idx == 6:
                        self.stage_idx = 7
                        self.trigger_dialog("Alright, let's tackle the onions. I hope these don't make me cry...")
                        
                    elif self.stage_idx == 9:
                        self.stage_idx = 10
                        self.trigger_dialog("Now for the green peppers! Let's get these sliced up.")
                        
                    elif self.stage_idx == 12:
                        self.stage_idx = 13
                        self.trigger_dialog("Last but not least, the eggplant!")
                    
                    elif self.stage_idx == 16:
                        # Auto-transition to the final "Finish Chopping" art screen
                        self.stage_idx = 17
                        self.trigger_dialog("Finally, all the ingredients are chopped! Time to fire up the BBQ.")
                        
                    elif self.stage_idx == 17:
                        # Prep completely finished, return to the BBQ view
                        self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True))
            return

        if key == arcade.key.ESCAPE:
            self.window.show_view(BbqView(chop_unlocked=True, grill_unlocked=True))