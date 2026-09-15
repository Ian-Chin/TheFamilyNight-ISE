"""Turning scanned-looking white-paper art into clean cut-outs."""

import PIL.ImageChops

from ..config import CLEAR_ABOVE, OPAQUE_BELOW, SOLID_ALPHA


def key_out_white(image):
    """Return an RGBA copy with the white paper background keyed out."""
    image = image.convert("RGBA")
    red, green, blue, _ = image.split()
    darkest = PIL.ImageChops.darker(PIL.ImageChops.darker(red, green), blue)
    span = CLEAR_ABOVE - OPAQUE_BELOW
    alpha = darkest.point(
        lambda v: 0 if v >= CLEAR_ABOVE
        else 255 if v <= OPAQUE_BELOW
        else round(255 * (CLEAR_ABOVE - v) / span)
    )
    image.putalpha(alpha)
    return image


def solid_bbox(image):
    """Bounds of the clearly visible pixels, ignoring faint keyed-out edges."""
    solid = image.split()[3].point(lambda v: 255 if v > SOLID_ALPHA else 0)
    return solid.getbbox()


def trim(image):
    bounds = solid_bbox(image)
    return image.crop(bounds) if bounds else image
