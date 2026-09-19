"""Turning scanned-looking white-paper art into clean cut-outs."""

import PIL.Image
import PIL.ImageChops
import PIL.ImageFilter

from ..config import (
    CHARACTER_ART_HEIGHT, CLEAR_ABOVE, OPAQUE_BELOW, RIM_DARK, RIM_DARK_COLOR,
    RIM_GLOW, RIM_GLOW_COLOR, SOLID_ALPHA,
)


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


def grown(alpha, radius):
    """The alpha channel spread outwards by `radius` pixels."""
    if radius < 1:
        return alpha
    return alpha.filter(PIL.ImageFilter.MaxFilter(2 * radius + 1))


def scaled(image, ratio):
    if ratio == 1.0:
        return image
    return image.resize(
        (max(1, round(image.width * ratio)), max(1, round(image.height * ratio))),
        PIL.Image.LANCZOS,
    )


def to_art_height(images):
    """Bring a set of cut-outs down together, keeping their relative sizes.

    Scaling as a group matters: the walk, jump and idle frames are measured
    against each other later, so they have to come out of the same divide.
    """
    tallest = max(image.height for image in images)
    ratio = min(1.0, CHARACTER_ART_HEIGHT / tallest)
    return [scaled(image, ratio) for image in images]


def add_rim(image):
    """Ring a cut-out in dark ink inside a soft pale halo.

    The garden art is busy and mid-green, and the characters are drawn in
    much the same value range, so they sink into it. A hard dark line holds
    their silhouette and the halo behind it separates them from whatever
    they happen to be standing on.

    Call this on art already brought down to `CHARACTER_ART_HEIGHT`: the rim
    is in pixels, and dilating a full-size source image is far slower for no
    visible gain.
    """
    margin = RIM_DARK + RIM_GLOW
    padded = PIL.Image.new(
        "RGBA",
        (image.width + 2 * margin, image.height + 2 * margin),
        (0, 0, 0, 0),
    )
    padded.paste(image, (margin, margin))
    alpha = padded.split()[3]

    halo = PIL.Image.new("RGBA", padded.size, (0, 0, 0, 0))
    halo.paste(
        RIM_GLOW_COLOR, (0, 0),
        grown(alpha, margin).filter(PIL.ImageFilter.GaussianBlur(RIM_GLOW)),
    )
    ink = PIL.Image.new("RGBA", padded.size, (0, 0, 0, 0))
    ink.paste(RIM_DARK_COLOR, (0, 0), grown(alpha, RIM_DARK))

    return PIL.Image.alpha_composite(
        PIL.Image.alpha_composite(halo, ink), padded
    )
