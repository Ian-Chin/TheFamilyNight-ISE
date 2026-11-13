import arcade

from ...config import HEIGHT, WIDTH
from ...core import audio, textures
from ...core.stage import StageView
from .config import (
    APU_LOGO, APU_WIDTH, CARD_HOLD, CARD_IN, CARD_OUT, CODED_WITH, INK, INK_DIM,
    LIBRARIES, LIBRARY_GAP, LIBRARY_ICON, PAPER, PAPER_IN, SKIP_GRACE, SKIP_HINT, SPLASH_MUSIC,
    STUDIO_LOGO, STUDIO_WIDTH,
)

STEPS = ("apu", "libraries", "studio")
CARD_TIME = CARD_IN + CARD_HOLD + CARD_OUT


class SplashView(StageView):
    def __init__(self):
        super().__init__()
        self.background_color = arcade.color.BLACK
        self.logos = {
            "studio": (textures.ui_image(STUDIO_LOGO), STUDIO_WIDTH),
            "apu": (textures.ui_image(APU_LOGO), APU_WIDTH),
        }
        self.icons = [textures.ui_image(logo) for logo, _ in LIBRARIES]
        self.step = 0
        self.clock = 0.0          # seconds into the current step
        self.total = 0.0          # seconds since the splash opened
        self.done = False
        self.trailer = None       # built as the studio card arrives, to decode ahead
        self.music = None
        self.relayout()

    def on_show_view(self):
        self.music = audio.play(SPLASH_MUSIC)

    def relayout(self):
        super().relayout()
        stage = self.stage
        self.coded_text = stage.text(
            CODED_WITH.upper(), WIDTH / 2, HEIGHT / 2 + 150, INK_DIM, 16,
            anchor_x="center", anchor_y="center", bold=True,
        )
        self.name_texts = [
            stage.text(name, self.icon_center(i), HEIGHT / 2 - 104, INK, 20,
                       anchor_x="center", anchor_y="center", bold=True)
            for i, (_, name) in enumerate(LIBRARIES)
        ]
        self.skip_text = stage.text(
            SKIP_HINT, WIDTH - 36, 30, (150, 150, 158), 12,
            anchor_x="right", anchor_y="center",
        )

    @staticmethod
    def icon_center(index):
        count = len(LIBRARIES)
        row = count * LIBRARY_ICON + (count - 1) * LIBRARY_GAP
        return (WIDTH - row) / 2 + LIBRARY_ICON / 2 + index * (LIBRARY_ICON + LIBRARY_GAP)


    def finish(self):
        if self.done:
            return
        self.done = True
        self.window.show_view(self.trailer or self.make_trailer())

    def make_trailer(self):
        from .trailer import TrailerView
        return TrailerView(cover=self.logos["studio"], music=self.music)

    def on_update(self, delta_time):
        if self.done:
            return
        delta_time = min(delta_time, 1 / 30)
        self.clock += delta_time
        self.total += delta_time
        if STEPS[self.step] == "studio":
            if self.trailer is None:
                self.trailer = self.make_trailer()
            elif self.clock >= CARD_IN:
                self.trailer.prepare_menu()
            if self.clock >= CARD_IN + CARD_HOLD:
                self.finish()
        elif self.clock >= CARD_TIME:
            self.step += 1
            self.clock = 0.0


    def card_alpha(self):
        t = self.clock
        return max(0.0, min(1.0, t / CARD_IN, (CARD_TIME - t) / CARD_OUT))

    def on_draw(self):
        self.clear()
        step = STEPS[min(self.step, len(STEPS) - 1)]
        paper = min(1.0, self.total / PAPER_IN)
        arcade.draw_rect_filled(
            arcade.LBWH(0, 0, self.stage.window_w, self.stage.window_h),
            (*PAPER, round(255 * paper)),
        )
        alpha = round(255 * self.card_alpha())
        if step == "libraries":
            self.draw_libraries(alpha)
        else:
            logo, width = self.logos[step]
            height = width * logo.height / logo.width
            arcade.draw_texture_rect(logo, self.stage.rect(
                (WIDTH - width) / 2, (HEIGHT - height) / 2, width, height,
            ), alpha=alpha)
        if self.total > SKIP_GRACE:
            self.skip_text.draw()

    def draw_libraries(self, alpha):
        self.coded_text.color = (*INK_DIM, alpha)
        self.coded_text.draw()
        for index, icon in enumerate(self.icons):
            rise = min(1.0, max(0.0, 1 - (self.clock - index * 0.08) / CARD_IN))
            scale = LIBRARY_ICON / max(icon.width, icon.height)
            width, height = icon.width * scale, icon.height * scale
            center_y = HEIGHT / 2 + 20 - 18 * rise ** 2
            arcade.draw_texture_rect(icon, self.stage.rect(
                self.icon_center(index) - width / 2, center_y - height / 2, width, height,
            ), alpha=round(alpha * (1 - rise)))
            name = self.name_texts[index]
            name.color = (*INK, round(alpha * (1 - rise)))
            name.draw()


    def on_key_press(self, key, modifiers):
        if self.total > SKIP_GRACE:
            self.finish()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.total > SKIP_GRACE:
            self.finish()
