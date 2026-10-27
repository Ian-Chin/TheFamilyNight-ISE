"""The closing cut scene, after the leftover feast.

Terry has eaten until he is full; the camera tilts up from the cleared table
into the night sky, the title fades in among the stars and out again, and the
game ends on black. The whole thing is one pre-rendered video
(ENDING_VIDEO, baked by tools/make_ending.py) played through once, with the
night ambience underneath it fading away as it ends, and its sound effects
(ending-sfx, baked alongside it) started with the first frame. Any key or a click skips
it. Either way the player lands back on the title menu.

Without PyAV the video cannot be played, so the title just fades in and out
over black instead.
"""

import queue
import threading

import arcade
import PIL.Image

from . import audio, textures
from .config import (
    AMBIENCE_NIGHT, ENDING_FALLBACK, ENDING_VIDEO, HEIGHT, VIDEO_DIR, VIDEO_QUEUE, WIDTH,
)
from .views import StageView

try:
    import av
except ImportError:
    av = None


class _OneShot(threading.Thread):
    """Decodes a video once, start to finish, into `frames`; then None."""

    def __init__(self, path):
        super().__init__(daemon=True)
        self.path = path
        self.period = 1 / 30
        self.failed = False
        self.frames = queue.Queue(VIDEO_QUEUE)
        self.stopped = threading.Event()

    def run(self):
        try:
            container = av.open(str(self.path))
            stream = container.streams.video[0]
        except (OSError, av.FFmpegError, IndexError):
            self.failed = True
            return
        stream.thread_type = "AUTO"
        if stream.average_rate:
            self.period = 1 / float(stream.average_rate)
        try:
            for frame in container.decode(stream):
                if not self.put(PIL.Image.fromarray(frame.to_ndarray(format="rgba"))):
                    return
        except av.FFmpegError:
            pass
        finally:
            container.close()
        self.put(None)

    def put(self, item):
        while not self.stopped.is_set():
            try:
                self.frames.put(item, timeout=0.2)
                return True
            except queue.Full:
                pass
        return False


class EndingView(StageView):
    def __init__(self):
        super().__init__()
        path = VIDEO_DIR / ENDING_VIDEO
        self.decoder = None
        if av is not None and path.exists():
            self.decoder = _OneShot(path)
            self.decoder.start()
        self.length = self.video_length(path)
        self.logo = textures.ui_image("logo.png")
        self.frame = None
        self.frame_clock = 0.0
        self.clock = 0.0
        self.done = False
        self.sfx = None   # the effects track, started with the first frame

    @staticmethod
    def video_length(path):
        if av is None or not path.exists():
            return ENDING_FALLBACK
        try:
            with av.open(str(path)) as container:
                return container.duration / av.time_base
        except (OSError, av.FFmpegError, TypeError):
            return ENDING_FALLBACK

    def on_show_view(self):
        audio.ambience(AMBIENCE_NIGHT).start()

    def on_hide_view(self):
        if self.decoder is not None:
            self.decoder.stopped.set()
        audio.bank().stop(self.sfx)
        self.sfx = None
        audio.ambience(AMBIENCE_NIGHT).stop()

    def finish(self):
        if self.done:
            return
        self.done = True
        from .views import MenuView
        self.window.show_view(MenuView())

    def show(self, image):
        atlas = self.window.ctx.default_atlas
        if self.frame is None or self.frame.image.size != image.size:
            self.frame = arcade.Texture(
                image, hash="video:ending",
                hit_box_algorithm=arcade.hitbox.algo_bounding_box,
            )
            atlas.add(self.frame)
        else:
            self.frame.image = image
        atlas.update_texture_image(self.frame)

    def on_update(self, delta_time):
        ambience = audio.ambience(AMBIENCE_NIGHT)
        ambience.update(delta_time)
        delta_time = min(delta_time, 1 / 30)
        self.clock += delta_time
        # The crickets fade out with the picture over the last seconds.
        left = self.length - self.clock
        if ambience.player is not None and left < 1.5:
            ambience.player.volume = (audio.bank().volume(AMBIENCE_NIGHT)
                                      * ambience.fade_level * max(0.0, left / 1.5))

        if self.decoder is None or self.decoder.failed:
            if self.clock >= ENDING_FALLBACK:
                self.finish()
            return
        if self.clock >= self.length + 1.0:
            # A decoder that fell behind or stalled does not hold the game up.
            self.finish()
            return
        self.frame_clock -= delta_time
        if self.frame is not None and self.frame_clock > 0:
            return
        try:
            image = self.decoder.frames.get_nowait()
        except queue.Empty:
            return
        if image is None:
            self.finish()
            return
        if self.frame is None:
            # In step with the picture: the burp lands on the burp.
            self.sfx = audio.play("ending_sfx")
        self.show(image)
        self.frame_clock = max(0.0, self.frame_clock + self.decoder.period)

    def on_draw(self):
        self.clear()
        if self.frame is not None:
            arcade.draw_texture_rect(self.frame, self.stage.viewport())
            return
        if self.decoder is None or self.decoder.failed:
            # The title alone, faded in and out over black.
            t = self.clock / ENDING_FALLBACK
            alpha = round(255 * max(0.0, min(1.0, t * 4, (1 - t) * 3)))
            width = 720
            height = width * self.logo.height / self.logo.width
            arcade.draw_texture_rect(self.logo, self.stage.rect(
                (WIDTH - width) / 2, (HEIGHT - height) / 2, width, height), alpha=alpha)

    # A moment's grace first, so the key that pressed Continue cannot skip it.
    def on_key_press(self, key, modifiers):
        if self.clock > 0.5:
            self.finish()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.clock > 0.5:
            self.finish()
