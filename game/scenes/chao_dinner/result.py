import arcade

from ...config import PLANK_PAD
from ...core.pause import PauseMenu
from .config import RESULT_BADGE_R, RESULT_STYLES, RESULT_STRIPE_H


class ResultCard(PauseMenu):
    def __init__(self, items, title, message, width, mood):
        super().__init__(items, title, message, width=width)
        self.style = RESULT_STYLES[mood]
        self.mood = mood

    def layout(self, stage):
        super().layout(stage)
        self.title_text.color = self.style["title"]

    def draw(self):
        if not self.visible:
            return
        stage = self.stage
        style = self.style
        top = self.bottom + self.height
        arcade.draw_rect_filled(
            arcade.LBWH(0, 0, stage.window_w, stage.window_h), style["wash"],
        )
        arcade.draw_texture_rect(self.texture, stage.rect(
            self.left - PLANK_PAD, self.bottom - PLANK_PAD,
            self.width + 2 * PLANK_PAD, self.height + 2 * PLANK_PAD,
        ))
        arcade.draw_rect_filled(
            stage.rect(self.left + 14, top - RESULT_STRIPE_H - 6,
                       self.width - 28, RESULT_STRIPE_H),
            style["accent"],
        )
        self.draw_badge(self.left + self.width / 2, top + 14)
        self.title_text.draw()
        if self.message_text is not None:
            self.message_text.draw()
        for button in self.buttons:
            button.draw()

    def draw_badge(self, cx, cy):
        stage = self.stage
        s = stage.scale
        x, y = stage.to_screen(cx, cy)
        r = RESULT_BADGE_R * s
        arcade.draw_circle_filled(x, y, r + 4 * s, (14, 16, 22, 235))
        arcade.draw_circle_filled(x, y, r, self.style["accent"])
        mark = (250, 252, 248)
        w = 5 * s
        if self.mood == "win":
            arcade.draw_line(x - r * 0.45, y + r * 0.02, x - r * 0.1, y - r * 0.35, mark, w)
            arcade.draw_line(x - r * 0.1, y - r * 0.35, x + r * 0.5, y + r * 0.35, mark, w)
        else:
            k = r * 0.38
            arcade.draw_line(x - k, y - k, x + k, y + k, mark, w)
            arcade.draw_line(x - k, y + k, x + k, y - k, mark, w)
