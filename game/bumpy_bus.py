"""Bus shopping trip, hosted in the same Arcade window as the cooking scenes."""
import importlib.util
import os
import sys
from pathlib import Path
import arcade
from .config import ASSETS, CHAO_FADE_IN, WIDTH, HEIGHT
from .views import StageView

def bus_engine_module():
    name = '_family_bus_engine'
    if name in sys.modules:
        return sys.modules[name]
    root = ASSETS
    # SDL only paints an offscreen canvas. Arcade owns the sole visible window.
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['IMAGING_GAME_ASSET_ROOT'] = str(root)
    runtime = Path(__file__).resolve().parent / 'bus_runtime'
    sys.path.insert(0, str(runtime))
    spec = importlib.util.spec_from_file_location(name, runtime / 'game.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

class BumpyBusView(StageView):
    """Waiting stop -> bus -> horn and wipe -> the existing BbqView."""
    def __init__(self):
        super().__init__()
        module = bus_engine_module()
        self.pg = module.pg
        self.engine = module.Game()
        self.pointer = (-9999, -9999)
        self.engine.mouse = lambda: self.pointer
        self.destination = None
        ctx = self.window.ctx
        self.frame_texture = ctx.texture((WIDTH, HEIGHT), components=4)
        self.frame_texture.filter = (ctx.NEAREST, ctx.NEAREST)
        self.quad = arcade.gl.geometry.quad_2d_fs()
        self.program = ctx.program(vertex_shader='''#version 330
in vec2 in_vert;
in vec2 in_uv;
out vec2 uv;
void main(){uv=in_uv;gl_Position=vec4(in_vert,0.0,1.0);}
''', fragment_shader='''#version 330
uniform sampler2D bus_frame;
in vec2 uv;
out vec4 colour;
void main(){colour=texture(bus_frame,uv);}
''')
        self.program['bus_frame'] = 0

    def on_update(self, delta_time):
        self.engine.update(min(.05, delta_time), self.pointer)
        if self.engine.mode == 'arrival' and self.destination is None:
            from .bbq_scene import BbqView
            self.destination = BbqView()
            # The bus has already revealed the garden; do not fade back to black.
            self.destination.fade_clock = CHAO_FADE_IN
        if self.engine.arrival_done:
            self.window.bus_delivery = {'remaining_food':self.engine.food,
                'damaged_ingredients':sorted(self.engine.damaged_food), 'life':self.engine.balance}
            self.window.show_view(self.destination)

    def on_draw(self):
        self.clear()
        self.engine.draw()
        self.frame_texture.write(self.pg.image.tobytes(self.engine.canvas, 'RGBA', True))
        ctx = self.window.ctx
        viewport = ctx.viewport
        ctx.viewport = (round(self.stage.left), round(self.stage.bottom), round(self.stage.width), round(self.stage.height))
        self.frame_texture.use(0)
        self.quad.render(self.program)
        ctx.viewport = viewport
        self.window.default_camera.use()

    def on_mouse_motion(self, x, y, dx, dy):
        x, y = self.canvas_point(x, y)
        self.pointer = (x, HEIGHT-y)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.on_mouse_motion(x,y,dx,dy)

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            from comic_ui import menu_click
            x,y = self.canvas_point(x,y)
            menu_click(self.engine,self.pg,x,HEIGHT-y)

    def on_key_press(self, key, modifiers):
        mapping = {arcade.key.A:self.pg.K_a, arcade.key.D:self.pg.K_d,
            arcade.key.J:self.pg.K_j, arcade.key.K:self.pg.K_k,
            arcade.key.L:self.pg.K_l, arcade.key.I:self.pg.K_i,
            arcade.key.ENTER:self.pg.K_RETURN, arcade.key.SPACE:self.pg.K_SPACE, arcade.key.ESCAPE:self.pg.K_ESCAPE,
            arcade.key.R:self.pg.K_r, arcade.key.B:self.pg.K_b, arcade.key.P:self.pg.K_p}
        value = mapping.get(key)
        if value is not None and value not in self.engine.held:
            self.engine.held.add(value)
            self.engine.key(value)

    def on_key_release(self, key, modifiers):
        mapping = {arcade.key.A:self.pg.K_a, arcade.key.D:self.pg.K_d,
            arcade.key.J:self.pg.K_j, arcade.key.K:self.pg.K_k,
            arcade.key.L:self.pg.K_l, arcade.key.I:self.pg.K_i,
            arcade.key.ENTER:self.pg.K_RETURN, arcade.key.SPACE:self.pg.K_SPACE, arcade.key.ESCAPE:self.pg.K_ESCAPE,
            arcade.key.R:self.pg.K_r, arcade.key.B:self.pg.K_b, arcade.key.P:self.pg.K_p}
        if key in mapping:self.engine.held.discard(mapping[key])

    def on_hide_view(self):
        self.engine.audio.stop()
        if self.engine.bgm:self.engine.bgm.stop()
        self.pg.mixer.unpause()
        self.frame_texture.delete()
