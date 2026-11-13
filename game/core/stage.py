import arcade

from .ui import Stage


class StageView(arcade.View):
    def __init__(self):
        super().__init__()
        self.stage = Stage(self.window.width, self.window.height)
        self.widgets = []

    def relayout(self):
        for widget in self.widgets:
            widget.layout(self.stage)

    def on_resize(self, width, height):
        super().on_resize(width, height)
        self.stage.resize(width, height)
        self.relayout()

    def canvas_point(self, x, y):
        return self.stage.to_canvas(x, y)
