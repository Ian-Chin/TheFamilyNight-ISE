import arcade

from . import audio, textures
from .config import BBQ_PREP_SCENE_BG, WIDTH, HEIGHT
from .dialogue import DialogBox
from .views import StageView
from .bbq_scene import BbqView

# --- NEW: Import the Portraits widget ---
from .chao_widgets import Portraits

def cover_rect(texture, rect):
    scale = max(rect.width / texture.width, rect.height / texture.height)
    return arcade.XYWH(rect.x, rect.y, texture.width * scale, texture.height * scale)


class BBQPrepView(StageView):
    def __init__(self):
        super().__init__()
        self.background = textures.background(BBQ_PREP_SCENE_BG)
        
        # --- NEW: Setup the Start Button Sprite ---
        self.button_list = arcade.SpriteList()
        # Scale down slightly so it fits neatly into the corner
        self.start_button = arcade.Sprite(textures.ui_image("Start_Prep_button.png"), scale=0.6)
        
        # Place it in the bottom right corner (adjust these numbers if you want it moved)
        self.start_button.center_x = WIDTH - 150
        self.start_button.center_y = 50
        self.button_list.append(self.start_button)
        
        # --- Setup Dialogue and Portraits ---
        self.dialog = DialogBox()
        
        try:
            terry_tex = arcade.load_texture("assets/sprites/Terry-idle.png")
        except Exception:
            terry_tex = None
        self.portraits = Portraits(terry_tex)
        
        # Add portraits to the widgets list so it lays out properly
        self.widgets = [self.dialog, self.portraits]
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
        
        # 1. Draw Background
        arcade.draw_texture_rect(
            self.background, 
            cover_rect(self.background, self.stage.viewport())
        )
        
        # 2. Switch to UI Camera
        self.window.default_camera.use()
        
        # --- NEW: Only draw the button if the dialogue is finished ---
        if not self.dialog.visible:
            self.button_list.draw(pixelated=True)
        
        # 3. Draw Dialogue and Portrait
        if self.dialog.visible:
            self.portraits.draw(partner=None, speaking="left")
            self.dialog.draw()
        
    def on_key_press(self, key, modifiers):
        # --- NEW: Handle dialogue progression (Enter AND Space to skip/close) ---
        if self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.SPACE):
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
        
        if button == arcade.MOUSE_BUTTON_LEFT:
            # --- NEW: Check exact collision with the sprite instead of a hardcoded box ---
            if self.start_button.collides_with_point((canvas_x, canvas_y)):
                from . import audio
                audio.play("ui_click")
                
                # Switch back to the main BBQ scene, and tell it the chopping board is unlocked!
                from .bbq_scene import BbqView
                self.window.show_view(BbqView(chop_unlocked=True))