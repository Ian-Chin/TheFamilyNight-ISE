"""The one place PIL images become arcade textures, and files become assets.

Widget art is cached by the pixel size it was built at, so a resize rebuilds
each texture once and reuses it from then on.
"""

import functools

import arcade
import PIL.Image

from .art.spritesheet import load_terry_frames
from .art.widgets import draw_card, draw_disc, draw_plank
from .config import BACKGROUND_DIR, ICON_DIR, UI_DIR


def _texture(image):
    return arcade.Texture(image)


@functools.lru_cache(maxsize=None)
def terry_frames():
    """(walk, jump, idle) texture lists, built once per run."""
    return tuple(
        [_texture(frame) for frame in group] for group in load_terry_frames()
    )


@functools.lru_cache(maxsize=64)
def plank(width, height, pad, hovered):
    return _texture(draw_plank(width, height, pad, hovered))


@functools.lru_cache(maxsize=32)
def disc(diameter, pad, hovered):
    return _texture(draw_disc(diameter, pad, hovered))


@functools.lru_cache(maxsize=16)
def card(width, height, pad):
    return _texture(draw_card(width, height, pad))


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
