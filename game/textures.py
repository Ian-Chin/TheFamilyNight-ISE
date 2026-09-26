"""The one place PIL images become arcade textures, and files become assets.

Widget art is cached by the pixel size it was built at, so a resize rebuilds
each texture once and reuses it from then on.
"""

import functools

import arcade
import PIL.Image

from .art.keying import add_rim, key_out_white, to_art_height, trim
from .art.spritesheet import group_sizes, load_terry_frames
from .art.widgets import (
    draw_card, draw_dialog_box, draw_disc, draw_hud_plate, draw_plank,
)
from .artcache import baked
from .config import (
    BACKGROUND_DIR, CHARACTER_DIR, DAY_BADGE_BOXES, DAYCYCLE_SHEET, ICON_DIR,
    IDLE_FILES, MOVEMENT_SHEET, SPRITE_DIR, UI_DIR,
)


def _texture(image):
    # Nothing here uses arcade's own collision, so the cheap bounding box
    # stands in for tracing a hit box out of the alpha channel.
    return arcade.Texture(image, hit_box_algorithm=arcade.hitbox.algo_bounding_box)


@functools.lru_cache(maxsize=None)
def terry_frames():
    """(walk, jump, idle) texture lists, built once per run."""
    sources = [SPRITE_DIR / MOVEMENT_SHEET, *(SPRITE_DIR / n for n in IDLE_FILES)]
    groups = group_sizes()

    def build():
        # Baked as one strip: the frames already share a canvas size.
        return [frame for group in load_terry_frames() for frame in group]

    frames = baked("terry-frames", sources, build)
    textures, start = [], 0
    for count in groups:
        textures.append([_texture(f) for f in frames[start:start + count]])
        start += count
    return tuple(textures)


@functools.lru_cache(maxsize=64)
def plank(width, height, pad, hovered):
    return _texture(draw_plank(width, height, pad, hovered))


@functools.lru_cache(maxsize=32)
def disc(diameter, pad, hovered):
    return _texture(draw_disc(diameter, pad, hovered))


@functools.lru_cache(maxsize=32)
def hud_plate(width, height, pad, hovered):
    return _texture(draw_hud_plate(width, height, pad, hovered))


@functools.lru_cache(maxsize=16)
def card(width, height, pad):
    return _texture(draw_card(width, height, pad))


@functools.lru_cache(maxsize=8)
def dialog_box(width, height, pad):
    return _texture(draw_dialog_box(width, height, pad))


@functools.lru_cache(maxsize=16)
def character(filename):
    """A family member's art, cut out of its background and trimmed."""
    source = CHARACTER_DIR / filename

    def build():
        image = PIL.Image.open(source)
        cut_out = (
            image.mode == "RGBA"
            and image.getchannel("A").getextrema()[0] < 255
        )
        if not cut_out:
            # Art saved without transparency sits on white paper, like the
            # sprite sheet does.
            image = key_out_white(image)
        small, = to_art_height([trim(image.convert("RGBA"))])
        return add_rim(small)

    return _texture(baked(f"character-{source.stem}", [source], build))


@functools.lru_cache(maxsize=16)
def _icon_source(name):
    """The baked Bootstrap icon, as a white silhouette ready to tint."""
    return PIL.Image.open(ICON_DIR / f"{name}.png").convert("RGBA")


@functools.lru_cache(maxsize=64)
def icon(name, size):
    source = _icon_source(name)
    return _texture(source.resize((size, size), PIL.Image.LANCZOS))


@functools.lru_cache(maxsize=16)
def background(name):
    return arcade.load_texture(BACKGROUND_DIR / name)


@functools.lru_cache(maxsize=16)
def ui_image(name):
    return arcade.load_texture(UI_DIR / name)


@functools.lru_cache(maxsize=1)
def day_badges():
    """One texture per phase, sliced out of the day cycle sheet."""
    sheet = PIL.Image.open(UI_DIR / DAYCYCLE_SHEET).convert("RGBA")
    return tuple(
        _texture(sheet.crop((x, y, x + w, y + h)))
        for x, y, w, h in DAY_BADGE_BOXES
    )
