import arcade

from . import audio, textures
from .config import BBQ_PREP_SCENE_BG
from .dialogue import DialogBox
from .views import StageView
from .bbq_scene import BbqView


def cover_rect(texture, rect):
    scale = max(rect.width / texture.width, rect.height / texture.height)
    return arcade.XYWH(rect.x, rect.y, texture.width * scale, texture.height * scale)


class BBQPrepView(StageView):
    def __init__(self):
        super().__init__()
        self.background = textures.background(BBQ_PREP_SCENE_BG)
        
        # --- Setup Dialogue ---
        self.dialog = DialogBox()
        self.widgets = [self.dialog]
        self.typing_player = None
        
        self.relayout()

    def on_show_view(self):
        # Trigger the dialogue as soon as the scene appears
        audio.play("dialog_open")
        self.dialog.open("Terry", "Hmm, there is a lot of food. I need to chop it first...")
        self.typing_player = audio.play("dialog_type", loop=True)

    def stop_typing_sound(self):
        if self.typing_player:
            audio.bank().stop(self.typing_player)
            self.typing_player = None

    def on_update(self, delta_time):
        # Update the dialogue typing animation
        if self.dialog.visible:
            self.dialog.update(delta_time)
            if not self.dialog.typing:
                self.stop_typing_sound()

    def on_draw(self):
        self.clear()
        arcade.draw_texture_rect(
            self.background, 
            cover_rect(self.background, self.stage.viewport())
        )
        self.window.default_camera.use()
        
        # Draw the dialogue box over the background
        self.dialog.draw()
        
    def on_key_press(self, key, modifiers):
        # Handle dialogue progression (Enter to skip/close)
        if self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER):
                self.stop_typing_sound()
                self.dialog.advance()
            return

        # Pressing Escape sends the player back to the main BBQ scene
        if key == arcade.key.ESCAPE:
            self.window.show_view(BbqView())

    def on_mouse_press(self, x, y, button, modifiers):
        # Ignore clicks if the dialog box is still open
        if self.dialog.visible:
            return
            
        # Convert the actual screen click into fixed canvas coordinates
        canvas_x, canvas_y = self.stage.to_canvas(x, y)
        
        # Define an invisible bounding box over the "START PREPARE" area
        # (Bottom-right corner of a 1280x720 canvas)
        if canvas_x > 950 and canvas_y < 120 and button == arcade.MOUSE_BUTTON_LEFT:
            from . import audio
            audio.play("ui_click")
            
            # Switch back to the main BBQ scene, and tell it the chopping board is unlocked!
            from .bbq_scene import BbqView
            self.window.show_view(BbqView(chop_unlocked=True))