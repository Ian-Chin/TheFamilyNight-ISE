"""The inside of the bus, played from frame sheets.

Each scene (the idle ride and the four things that go wrong) is one big sheet
of 48 frames. A sheet is about 90 MB once decoded, so only the ones in use are
kept: the idle sheet stays, a reaction sheet is read in the background while
its alert is still counting down and dropped once it has played.

The frames do not fit in the texture atlas all at once, so one texture is kept
and its picture is swapped in place whenever the frame changes.
"""

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

    # --- Sheets -------------------------------------------------------------

    def prepare(self, kind):
        """Start reading `kind`'s sheet in the background, if it is not already."""
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

    def release(self, kind):
        """Let go of a reaction sheet once its scene has played."""
        if kind != "idle":
            self.sheets.pop(kind, None)
            self.threads.pop(kind, None)

    # --- Frames -------------------------------------------------------------

    def duration(self, kind):
        return sum(self.scenes[kind]["durationsMs"]) / 1000

    def frame_at(self, kind, seconds):
        """Which frame `kind` is on `seconds` in; the idle scene loops."""
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

    def at(self, kind, seconds):
        """The texture showing `kind` at `seconds`."""
        frame = (kind, self.frame_at(kind, seconds))
        if frame == self.shown:
            return self.texture
        image = self.frame_image(*frame)
        atlas = arcade.get_window().ctx.default_atlas
        if self.texture is None:
            self.texture = arcade.Texture(image)
            atlas.add(self.texture)
        else:
            self.texture.image = image
        atlas.update_texture_image(self.texture)
        self.shown = frame
        return self.texture
