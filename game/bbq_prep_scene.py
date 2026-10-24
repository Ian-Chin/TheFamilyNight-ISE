import arcade

from . import audio, textures
from .config import BBQ_PREP_SCENE_BG, WIDTH, HEIGHT
from .dialogue import DialogBox
from .views import StageView
from .bbq_scene import BbqView
from .chao_widgets import Portraits

def cover_rect(texture, rect):
    scale = max(rect.width / texture.width, rect.height / texture.height)
    return arcade.XYWH(rect.x, rect.y, texture.width * scale, texture.height * scale)


class BBQPrepView(StageView):
    def __init__(self):
        super().__init__()
        self.background = textures.background(BBQ_PREP_SCENE_BG)
        
        # --- Setup the Start Button Sprite at virtual canvas coordinates ---
        self.button_list = arcade.SpriteList()
        self.start_button = arcade.Sprite(textures.ui_image("Start_Prep_button.png"), scale=0.6)
        self.start_button.center_x = WIDTH - 150
        self.start_button.center_y = 60
        self.button_list.append(self.start_button)
        
        # --- Setup Dialogue and Portraits ---
        self.dialog = DialogBox()
        
        try:
            terry_tex = arcade.load_texture("assets/sprites/Terry-idle.png")
        except Exception:
            terry_tex = None
        self.portraits = Portraits(terry_tex)
        
        self.widgets = [self.dialog, self.portraits]
        self.typing_player = None

        # --- Setup stage camera for responsive scaling across windowed & fullscreen ---
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

    def on_show_view(self):
        audio.play("dialog_open")
        self.dialog.open("Terry", "Hmm, there is a lot of food. I need to chop it first...")
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
        
        # 1. Draw Background
        self.window.default_camera.use()
        arcade.draw_texture_rect(
            self.background, 
            cover_rect(self.background, self.stage.viewport())
        )
        
        # 2. Use stage camera so the button scales and locks to the corner responsively
        self.camera.use()
        if not self.dialog.visible:
            self.button_list.draw(pixelated=True)
        
        # 3. Draw Dialogue and Portrait
        self.window.default_camera.use()
        if self.dialog.visible:
            self.portraits.draw(partner=None, speaking="left")
            self.dialog.draw()
        
    def on_key_press(self, key, modifiers):
        if self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.SPACE):
                self.stop_typing_sound()
                self.dialog.advance()
            return

        if key == arcade.key.ESCAPE:
            self.window.show_view(BbqView())

    def on_mouse_press(self, x, y, button, modifiers):
        if self.dialog.visible:
            return
            
        canvas_x, canvas_y = self.stage.to_canvas(x, y)
        
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.start_button.collides_with_point((canvas_x, canvas_y)):
                audio.play("click_button")
                self.window.show_view(BbqView(chop_unlocked=True, play_chop_unlock=True))