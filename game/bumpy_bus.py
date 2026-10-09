"""Native Arcade bus trip followed by the existing BBQ scene."""
import arcade
from .config import ASSETS, CHAO_FADE_IN, HEIGHT
from .views import StageView
from .bus_runtime.game import Game


class BumpyBusView(StageView):
    def __init__(self):
        super().__init__()
        self.engine = Game(ASSETS, self.stage)
        self.pointer = (-9999,-9999)
        self.destination = None

    def on_update(self, delta_time):
        self.engine.update(min(.05,delta_time),self.pointer)
        if self.engine.mode == 'arrival' and self.destination is None:
            from .bbq_scene import BbqView
            self.destination = BbqView()
            self.destination.fade_clock = CHAO_FADE_IN
        if self.engine.arrival_done:
            self.window.bus_delivery = {'remaining_food':self.engine.food,
                'damaged_ingredients':[self.engine.damaged_food_name(i) for i in sorted(self.engine.damaged_food)],
                'life':self.engine.balance}
            self.window.show_view(self.destination)

    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
        self.engine.draw(self.pointer)

    def on_mouse_motion(self,x,y,dx,dy):
        x,y = self.canvas_point(x,y)
        self.pointer = (x,HEIGHT-y)

    def on_mouse_drag(self,x,y,dx,dy,buttons,modifiers):
        self.on_mouse_motion(x,y,dx,dy)

    def on_mouse_press(self,x,y,button,modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            x,y = self.canvas_point(x,y)
            self.engine.click(x,HEIGHT-y)

    def on_key_press(self,key,modifiers):
        if key not in self.engine.held:
            self.engine.held.add(key)
            self.engine.key(key)

    def on_key_release(self,key,modifiers):
        self.engine.held.discard(key)

    def on_hide_view(self):
        self.engine.dispose()
