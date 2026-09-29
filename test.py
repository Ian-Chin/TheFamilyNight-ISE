"""Developer test menu. Run `python test.py` (add `--fullscreen` if wanted).

Jumps straight into one scene so each dev can work on theirs without
playing through the others. Pick with the mouse, arrow keys + Enter, or the
number shown beside each entry. Esc quits.

To hook up a new scene, add a row to SCENES: (label, module, class, kwargs).
A module that does not exist yet shows as "not built yet" instead of crashing.
"Main Menu" inside a scene comes back here, not to the game's title menu.
"""

import importlib
import sys
import traceback

import arcade

from game.config import HEIGHT, TITLE, WIDTH
from game import views
from game.views import StageView

# (label, module, class name, constructor kwargs).
SCENES = [
    ("Scene 1: Market Dash", "game.market_dash", "MarketDashView", {}),
    ("Scene 2: Bumpy Bus", "game.bumpy_bus", "BumpyBusView", {}),
    ("Scene 3: Backyard BBQ", "game.bbq_scene", "BbqView", {}),
    ("Scene 4: Chaos Dinner", "game.chao_dinner", "ChaoDinnerView", {}),
]

ROW_H = 52
ROW_W = 560
TOP = HEIGHT - 170
BG = (24, 26, 32)
ROW = (44, 48, 58)
ROW_HOVER = (78, 110, 170)
TEXT = (235, 238, 245)
MUTED = (120, 126, 140)
ERROR = (235, 110, 110)


def find_view(module_name, class_name):
    """Return the view class, or None when the scene is not written yet."""
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name == module_name:
            return None
        raise
    return getattr(module, class_name, None)


class TestMenuView(StageView):
    def __init__(self):
        super().__init__()
        self.background_color = BG
        self.selected = 0
        self.message = ""
        self.entries = []
        for label, module_name, class_name, kwargs in SCENES:
            try:
                view_class = find_view(module_name, class_name)
            except Exception:
                traceback.print_exc()
                view_class = None
                label += "  (import error, see console)"
            self.entries.append((label, view_class, kwargs))
        self.relayout()

    def row_rect(self, index):
        left = (WIDTH - ROW_W) / 2
        bottom = TOP - (index + 1) * (ROW_H + 8)
        return left, bottom, ROW_W, ROW_H

    def relayout(self):
        super().relayout()
        self.title = self.stage.text(
            "Test Environment", WIDTH / 2, HEIGHT - 80, TEXT, 34,
            anchor_x="center", anchor_y="center",
        )
        self.hint = self.stage.text(
            "Click, or Up/Down + Enter, or press the number.   Esc to quit.",
            WIDTH / 2, HEIGHT - 125, MUTED, 14,
            anchor_x="center", anchor_y="center",
        )
        self.labels = []
        for index, (label, view_class, _) in enumerate(self.entries):
            left, bottom, _, _ = self.row_rect(index)
            text = f"{index + 1}.  {label}"
            if view_class is None and "error" not in label:
                text += "  (not built yet)"
            self.labels.append(self.stage.text(
                text, left + 20, bottom + ROW_H / 2,
                TEXT if view_class else MUTED, 18, anchor_y="center",
            ))
        self.status = self.stage.text(
            self.message, WIDTH / 2, 50, ERROR, 15,
            anchor_x="center", anchor_y="center",
        )

    def on_draw(self):
        self.clear()
        self.title.draw()
        self.hint.draw()
        for index, label in enumerate(self.labels):
            color = ROW_HOVER if index == self.selected else ROW
            arcade.draw_rect_filled(self.stage.rect(*self.row_rect(index)), color)
            label.draw()
        self.status.draw()

    def row_at(self, x, y):
        for index in range(len(self.entries)):
            left, bottom, width, height = self.row_rect(index)
            if left <= x <= left + width and bottom <= y <= bottom + height:
                return index
        return None

    def launch(self, index):
        label, view_class, kwargs = self.entries[index]
        if view_class is None:
            self.message = f"{label.strip()} is not available yet."
            self.relayout()
            return
        try:
            self.window.show_view(view_class(**kwargs))
        except Exception:
            traceback.print_exc()
            self.message = f"{label.strip()} crashed on start, see console."
            self.relayout()

    def on_mouse_motion(self, x, y, dx, dy):
        index = self.row_at(*self.canvas_point(x, y))
        if index is not None:
            self.selected = index

    def on_mouse_press(self, x, y, button, modifiers):
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        index = self.row_at(*self.canvas_point(x, y))
        if index is not None:
            self.launch(index)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            self.window.close()
        elif key in (arcade.key.UP, arcade.key.W):
            self.selected = (self.selected - 1) % len(self.entries)
        elif key in (arcade.key.DOWN, arcade.key.S):
            self.selected = (self.selected + 1) % len(self.entries)
        elif key in (arcade.key.ENTER, arcade.key.RETURN, arcade.key.SPACE):
            self.launch(self.selected)
        elif arcade.key.KEY_1 <= key <= arcade.key.KEY_9:
            index = key - arcade.key.KEY_1
            if index < len(self.entries):
                self.launch(index)


def main():
    # Scenes send "Main Menu" to game.views.MenuView (imported when pressed),
    # so pointing that name here brings devs back to this menu instead.
    views.MenuView = TestMenuView

    fullscreen = "--fullscreen" in sys.argv
    window = arcade.Window(
        WIDTH, HEIGHT, f"{TITLE} [TEST]", fullscreen=fullscreen, resizable=True,
    )
    window.show_view(TestMenuView())
    arcade.run()


if __name__ == "__main__":
    main()
