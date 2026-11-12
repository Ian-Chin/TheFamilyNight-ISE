"""The startup trailer, between the studio card and the title menu.

The splash builds it while the studio card is up, so frames are decoded
ahead, then hands over with the card still showing. The card fades out over
the trailer already playing, which plays once with its soundtrack started on
the first frame and hands over to the menu with its flash zoom. A click or any key skips to the menu. Without PyAV, or
without the file, it goes straight to the menu.
"""

import queue

import arcade

from ...config import HEIGHT, VIDEO_DIR, WIDTH
from ...core import audio
from ...core.stage import StageView
from ..ending.view import _OneShot, av
from .config import (
    PAPER, SKIP_GRACE, SKIP_HINT, TRAILER_FADE, TRAILER_SOUND, TRAILER_VIDEO,
)


class TrailerView(StageView):
    def __init__(self, cover=None, music=None):
        """`cover` is the (logo, width) card the trailer fades in from under,
        `music` the splash's cue, faded out with it."""
        super().__init__()
        self.cover = cover
        self.music = music
        self.music_volume = music.volume if music is not None else 0.0
        self.background_color = arcade.color.BLACK
        path = VIDEO_DIR / TRAILER_VIDEO
        self.decoder = None
        self.length = 0.0
        if av is not None and path.exists():
            try:
                with av.open(str(path)) as container:
                    self.length = container.duration / av.time_base
            except (OSError, av.FFmpegError, TypeError):
                pass
            if self.length:
                self.decoder = _OneShot(path)
                self.decoder.start()
        self.frame = None
        self.frame_clock = 0.0
        self.clock = 0.0
        self.done = False
        self.skipped = True   # anything short of the last frame cuts the sound
        self.sound = None   # the soundtrack, started with the first frame
        self.menu = None      # built ahead by `prepare_menu`
        self.relayout()

    def prepare_menu(self):
        """Build the menu now rather than on the trailer's last frame.

        The work stalls for a moment, and at the handover it lands right on
        the reveal's flash. The splash calls this while the studio card is
        holding still, where a stall cannot be seen.
        """
        if self.menu is None:
            from ..menu.view import MenuView
            self.menu = MenuView(reveal=True)
            self.menu.prepare()

    def relayout(self):
        super().relayout()
        self.skip_text = self.stage.text(
            SKIP_HINT, WIDTH - 36, 30, (200, 200, 208), 12,
            anchor_x="right", anchor_y="center",
        )

    def on_hide_view(self):
        if self.decoder is not None:
            self.decoder.stopped.set()
        if self.skipped:
            audio.bank().stop(self.sound)
        # Played through, the score's last hit rings on under the menu.
        self.sound = None
        audio.bank().stop(self.music)
        self.music = None

    def finish(self, skipped=False):
        if self.done:
            return
        self.done = True
        self.skipped = skipped
        if self.menu is None:
            self.prepare_menu()
        menu = self.menu
        if (menu.stage.window_w, menu.stage.window_h) != self.window.get_size():
            menu.on_resize(*self.window.get_size())
        self.window.show_view(menu)

    def show(self, image):
        atlas = self.window.ctx.default_atlas
        if self.frame is None or self.frame.image.size != image.size:
            self.frame = arcade.Texture(
                image, hash="video:trailer",
                hit_box_algorithm=arcade.hitbox.algo_bounding_box,
            )
            atlas.add(self.frame)
        else:
            self.frame.image = image
        atlas.update_texture_image(self.frame)

    def on_update(self, delta_time):
        if self.done:
            return
        delta_time = min(delta_time, 1 / 30)
        self.clock += delta_time
        if self.decoder is None or self.decoder.failed or self.clock >= self.length + 1.0:
            # A decoder that failed or stalled does not hold the game up.
            self.finish()
            return
        if self.music is not None and self.frame is not None:
            left = 1 - min(1.0, self.clock / TRAILER_FADE)
            self.music.volume = self.music_volume * left
            if left <= 0:
                audio.bank().stop(self.music)
                self.music = None
        self.frame_clock -= delta_time
        if self.frame is not None and self.frame_clock > 0:
            return
        try:
            image = self.decoder.frames.get_nowait()
        except queue.Empty:
            return
        if image is None:
            self.finish(skipped=False)
            return
        if self.frame is None:
            self.sound = audio.play(TRAILER_SOUND)
            # The card's fade starts with the picture, not with the decoder.
            self.clock = 0.0
        self.show(image)
        self.frame_clock = max(0.0, self.frame_clock + self.decoder.period)

    def on_draw(self):
        self.clear()
        if self.frame is not None:
            arcade.draw_texture_rect(self.frame, self.stage.viewport())
        # The studio card, held until the first frame, then faded away.
        fade = 0.0 if self.frame is None else min(1.0, self.clock / TRAILER_FADE)
        if self.cover is not None and fade < 1.0:
            alpha = round(255 * (1 - fade) ** 2)
            arcade.draw_rect_filled(
                arcade.LBWH(0, 0, self.stage.window_w, self.stage.window_h),
                (*PAPER, alpha),
            )
            logo, width = self.cover
            height = width * logo.height / logo.width
            arcade.draw_texture_rect(logo, self.stage.rect(
                (WIDTH - width) / 2, (HEIGHT - height) / 2, width, height,
            ), alpha=alpha)
        if self.frame is not None and self.clock > SKIP_GRACE:
            self.skip_text.draw()

    def on_key_press(self, key, modifiers):
        if self.clock > SKIP_GRACE:
            self.finish(skipped=True)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.clock > SKIP_GRACE:
            self.finish(skipped=True)
