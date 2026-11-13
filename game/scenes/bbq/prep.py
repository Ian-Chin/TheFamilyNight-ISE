import arcade

from ...core import achievements, audio, textures
from ...config import HEIGHT, WIDTH
from .config import BBQ_PREP_SCENE_BG
from ...core.dialogue import DialogBox
from ...core.stage import StageView
from .hub import BbqView
from ...core.widgets import Portraits
from ...core.backdrop import Backdrop

def cover_rect(texture, rect):
    scale = max(rect.width / texture.width, rect.height / texture.height)
    return arcade.XYWH(rect.x, rect.y, texture.width * scale, texture.height * scale)


class BBQPrepView(StageView):
    def __init__(self):
        super().__init__()
        self.backdrop = Backdrop(BBQ_PREP_SCENE_BG)

        self.button_list = arcade.SpriteList()
        self.start_button = arcade.Sprite(textures.ui_image("Start_Prep_button.png"), scale=0.6)
        self.start_button.center_x = WIDTH - 150
        self.start_button.center_y = 60
        self.button_list.append(self.start_button)

        self.dialog = DialogBox()

        self.default_face = textures.terry_frames(glow=False)[2][0]
        self.terry_faces = textures.terry_faces()
        
        self.portraits = Portraits(self.default_face)
        
        self.widgets = [self.dialog, self.portraits]
        self.typing_player = None

        self.camera = arcade.camera.Camera2D(
            position=(WIDTH / 2, HEIGHT / 2),
            projection=arcade.LRBT(-WIDTH / 2, WIDTH / 2, -HEIGHT / 2, HEIGHT / 2),
            viewport=self.stage.viewport(),
        )
        self.relayout()

    def play_script(self, lines, then=None):
        self.script = list(lines[1:])
        self.after_script = then
        self.start_dialog(*lines[0])

    def start_dialog(self, speaker, text, face=None):
        side = "left" if speaker == "Terry" else "right"
        if speaker == "Terry":
            self.portraits.terry = self.terry_faces.get(face, self.default_face)
            
        audio.play("dialog_open")
        self.dialog.open(speaker, text, side)
        self.typing_player = audio.play("dialog_type", loop=True)

    def advance_dialog(self):
        self.stop_typing_sound()
        if not self.dialog.advance():
            return
        if hasattr(self, 'script') and self.script:
            self.start_dialog(*self.script.pop(0))
            return
        then = getattr(self, 'after_script', None)
        self.after_script = None
        if then is not None:
            then()

    def relayout(self):
        super().relayout()
        if hasattr(self, 'camera'):
            self.camera.viewport = self.stage.viewport()

    def on_show_view(self):
        audio.ambience().start()
        self.play_script([("Terry", "Hmm, there is a lot of food. I need to chop it first...", "unimpressed")])

    def on_hide_view(self):
        self.backdrop.stop()
        self.stop_typing_sound()

    def stop_typing_sound(self):
        if self.typing_player:
            audio.bank().stop(self.typing_player)
            self.typing_player = None

    def on_update(self, delta_time):
        self.backdrop.update(delta_time)
        audio.ambience().update(delta_time)
        if self.dialog.visible:
            self.dialog.update(delta_time)
            if not self.dialog.typing:
                self.stop_typing_sound()

    def on_draw(self):
        self.clear()

        self.window.default_camera.use()
        background = self.backdrop.texture
        arcade.draw_texture_rect(
            background, 
            cover_rect(background, self.stage.viewport())
        )

        self.camera.use()
        if not self.dialog.visible:
            self.button_list.draw(pixelated=True)

        self.window.default_camera.use()
        if self.dialog.visible:
            self.portraits.draw(partner=None, speaking="left")
            self.dialog.draw()
        
    def on_key_press(self, key, modifiers):
        if self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.SPACE):
                self.advance_dialog()
            return

        if key == arcade.key.ESCAPE:
            self.window.show_view(BbqView())

    def on_mouse_press(self, x, y, button, modifiers):
        if self.dialog.visible:
            if button == arcade.MOUSE_BUTTON_LEFT:
                self.advance_dialog()
            return
            
        canvas_x, canvas_y = self.stage.to_canvas(x, y)
        
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.start_button.collides_with_point((canvas_x, canvas_y)):
                audio.play("click_button")
                achievements.unlock("bbq_prep")
                self.window.show_view(BbqView(chop_unlocked=True, play_chop_unlock=True))
