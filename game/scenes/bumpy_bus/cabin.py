import json
import threading

import arcade
import PIL.Image

from ...config import BACKGROUND_DIR
from .config import CABIN_DIR


class Cabin:
    def __init__(self):
        folder = BACKGROUND_DIR / CABIN_DIR
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        self.folder = folder
        self.frame_w = manifest["frameWidth"]
        self.frame_h = manifest["frameHeight"]
        self.columns = manifest["columns"]
        self.scenes = {scene["id"]: scene for scene in manifest["scenes"]}
        self.sheets = {}
        self.threads = {}
        self.texture = None
        self.shown = None
        self.prepare("idle")


    def prepare(self, kind):
        if kind in self.sheets or kind in self.threads:
            return
        thread = threading.Thread(target=self.read, args=(kind,), daemon=True)
        self.threads[kind] = thread
        thread.start()

    def read(self, kind):
        with PIL.Image.open(self.folder / self.scenes[kind]["sheet"]) as image:
            self.sheets[kind] = image.convert("RGBA")

    def sheet(self, kind):
        if kind not in self.sheets:
            self.prepare(kind)
            self.threads[kind].join()
        return self.sheets[kind]

    def ready(self, kind):
        return kind in self.sheets

    def release(self, kind):
        if kind != "idle":
            self.sheets.pop(kind, None)
            self.threads.pop(kind, None)


    def duration(self, kind):
        return sum(self.scenes[kind]["durationsMs"]) / 1000

    def frame_at(self, kind, seconds):
        durations = self.scenes[kind]["durationsMs"]
        ms = seconds * 1000
        if kind == "idle":
            ms %= sum(durations)
        for index, length in enumerate(durations):
            if ms < length:
                return index
            ms -= length
        return len(durations) - 1

    def frame_image(self, kind, index):
        x = index % self.columns * self.frame_w
        y = index // self.columns * self.frame_h
        return self.sheet(kind).crop((x, y, x + self.frame_w, y + self.frame_h))

    def idle_frame(self):
        return self.frame_image("idle", 0)

    def image_at(self, kind, seconds):
        return self.frame_image(kind, self.frame_at(kind, seconds))

    def show(self, image, key):
        if key != self.shown:
            self.upload(image)
            self.shown = key
        return self.texture

    def upload(self, image):
        atlas = arcade.get_window().ctx.default_atlas
        if self.texture is None:
            self.texture = arcade.Texture(image)
            atlas.add(self.texture)
        else:
            self.texture.image = image
        atlas.update_texture_image(self.texture)

    def at(self, kind, seconds):
        frame = (kind, self.frame_at(kind, seconds))
        if frame == self.shown:
            return self.texture
        self.upload(self.frame_image(*frame))
        self.shown = frame
        return self.texture
