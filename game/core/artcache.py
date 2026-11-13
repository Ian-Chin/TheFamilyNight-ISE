import hashlib

import PIL.Image
import PIL.PngImagePlugin

from ..config import (
    ASSETS, CHARACTER_ART_HEIGHT, CLEAR_ABOVE, OPAQUE_BELOW, RIM_DARK, RIM_DARK_COLOR,
    RIM_GLOW, RIM_GLOW_COLOR, SOLID_ALPHA,
)

CACHE_DIR = ASSETS / ".cache"

RECIPE = (
    CHARACTER_ART_HEIGHT, RIM_DARK, RIM_GLOW, RIM_DARK_COLOR, RIM_GLOW_COLOR,
    CLEAR_ABOVE, OPAQUE_BELOW, SOLID_ALPHA,
)
STAMP = hashlib.sha1(repr(RECIPE).encode()).hexdigest()[:8]


def is_fresh(path, sources):
    if not path.exists():
        return False
    baked = path.stat().st_mtime
    return all(source.stat().st_mtime <= baked for source in sources)


def strip(images):
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
    path = CACHE_DIR / f"{name}.{STAMP}.png"
    frames = None
    if is_fresh(path, sources):
        try:
            sheet = PIL.Image.open(path)
            sheet.load()
        except OSError:
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
