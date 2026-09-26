"""A disk cache for the art that is expensive to build.

Cutting a character out, ringing it and bringing it down to drawing size takes
long enough to be felt as a stall when a scene is opened. The result only ever
changes when the source file changes or when the settings that shape it do, so
it is baked into assets/.cache the first time and read back after that.

The cache key carries a digest of those settings, so editing the rim or the
art height leaves the old files behind unused rather than serving them.
"""

import hashlib

import PIL.Image
import PIL.PngImagePlugin

from .config import (
    ASSETS, CHARACTER_ART_HEIGHT, CLEAR_ABOVE, OPAQUE_BELOW, RIM_DARK,
    RIM_DARK_COLOR, RIM_GLOW, RIM_GLOW_COLOR, SOLID_ALPHA,
)

CACHE_DIR = ASSETS / ".cache"

# Everything that changes what a baked cut-out looks like.
RECIPE = (
    CHARACTER_ART_HEIGHT, RIM_DARK, RIM_GLOW, RIM_DARK_COLOR, RIM_GLOW_COLOR,
    CLEAR_ABOVE, OPAQUE_BELOW, SOLID_ALPHA,
)
STAMP = hashlib.sha1(repr(RECIPE).encode()).hexdigest()[:8]


def is_fresh(path, sources):
    """True when `path` exists and no source has been touched since."""
    if not path.exists():
        return False
    baked = path.stat().st_mtime
    return all(source.stat().st_mtime <= baked for source in sources)


def strip(images):
    """Lay equally sized frames out in a row, so a set is one file."""
    width, height = images[0].size
    sheet = PIL.Image.new("RGBA", (width * len(images), height), (0, 0, 0, 0))
    for index, image in enumerate(images):
        sheet.paste(image, (index * width, 0))
    return sheet


def unstrip(sheet, count):
    width = sheet.width // count
    return [
        sheet.crop((index * width, 0, (index + 1) * width, sheet.height))
        for index in range(count)
    ]


def baked(name, sources, build):
    """`build()` once, then read the result back from disk from then on.

    `build` returns either a single image or a list of equally sized frames;
    a list comes back as a list.
    """
    path = CACHE_DIR / f"{name}.{STAMP}.png"
    frames = None
    if is_fresh(path, sources):
        try:
            sheet = PIL.Image.open(path)
            sheet.load()
        except OSError:
            # A half-written or corrupt cache file is just a cache miss.
            path.unlink(missing_ok=True)
        else:
            count = int(sheet.info.get("frames", 1))
            frames = unstrip(sheet, count) if count > 1 else sheet

    if frames is None:
        frames = build()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        sheet = strip(frames) if isinstance(frames, list) else frames
        count = len(frames) if isinstance(frames, list) else 1
        sheet.save(path, pnginfo=_frame_count(count))

    return frames


def _frame_count(count):
    info = PIL.PngImagePlugin.PngInfo()
    info.add_text("frames", str(count))
    return info
