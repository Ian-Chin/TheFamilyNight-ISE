import queue
import threading

import arcade
import PIL.Image

from . import textures
from ..config import BACKGROUND_VIDEOS, VIDEO_DIR, VIDEO_QUEUE
from .settings import graphics

try:
    import av
except ImportError:
    av = None


class _Decoder(threading.Thread):
    def __init__(self, path):
        super().__init__(daemon=True)
        self.path = path
        self.period = 1 / 15
        self.failed = False
        self.frames = queue.Queue(VIDEO_QUEUE)
        self.stopped = threading.Event()

    def run(self):
        try:
            self.container = av.open(str(self.path))
            self.stream = self.container.streams.video[0]
        except (OSError, av.FFmpegError, IndexError):
            self.failed = True
            return
        self.stream.thread_type = "AUTO"
        rate = self.stream.average_rate
        if rate:
            self.period = 1 / float(rate)
        try:
            while not self.stopped.is_set():
                for frame in self.container.decode(self.stream):
                    image = PIL.Image.fromarray(frame.to_ndarray(format="rgba"))
                    if not self.put(image):
                        return
                self.container.seek(0)
        except av.FFmpegError:
            pass
        finally:
            self.container.close()

    def put(self, image):
        while not self.stopped.is_set():
            try:
                self.frames.put(image, timeout=0.2)
                return True
            except queue.Full:
                pass
        return False


class Backdrop:
    def __init__(self, still):
        self.still = textures.background(still)
        video = BACKGROUND_VIDEOS.get(still)
        self.video = VIDEO_DIR / video if video and av else None
        self.decoder = None
        self.frame = None   # the atlas texture each decoded frame is copied into
        self.failed = False
        self.clock = 0.0
        self.reserved = None   # an atlas slot made ahead by `reserve`

    def reserve(self):
        atlas = arcade.get_window().ctx.default_atlas
        atlas.add(self.still)
        if self.video is None or self.reserved is not None:
            return
        try:
            with av.open(str(self.video)) as container:
                stream = container.streams.video[0]
                size = (stream.width, stream.height)
        except (OSError, av.FFmpegError, IndexError):
            return
        self.reserved = arcade.Texture(
            PIL.Image.new("RGBA", size), hash=f"video:{self.video.name}",
            hit_box_algorithm=arcade.hitbox.algo_bounding_box,
        )
        atlas.add(self.reserved)

    @property
    def texture(self):
        if graphics.animated and self.frame is not None:
            return self.frame
        return self.still

    def update(self, delta_time):
        if not graphics.animated or self.video is None or self.failed:
            self.stop()
            return
        if self.decoder is None:
            self.start()
            if self.decoder is None:
                return

        if self.decoder.failed:
            self.failed = True
            self.stop()
            return
        self.clock -= delta_time
        if self.frame is not None and self.clock > 0:
            return
        try:
            image = self.decoder.frames.get_nowait()
        except queue.Empty:
            return
        self.show(image)
        self.clock = max(0.0, self.clock + self.decoder.period)

    def start(self):
        self.decoder = _Decoder(self.video)
        self.decoder.start()

    def stop(self):
        if self.decoder is not None:
            self.decoder.stopped.set()
            self.decoder = None

    def show(self, image):
        atlas = arcade.get_window().ctx.default_atlas
        if (self.frame is None and self.reserved is not None
                and self.reserved.image.size == image.size):
            self.frame = self.reserved
            self.frame.image = image
        elif self.frame is None or self.frame.image.size != image.size:
            self.frame = arcade.Texture(
                image, hash=f"video:{self.video.name}",
                hit_box_algorithm=arcade.hitbox.algo_bounding_box,
            )
            atlas.add(self.frame)
        else:
            self.frame.image = image
        atlas.update_texture_image(self.frame)
