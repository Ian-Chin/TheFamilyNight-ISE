"""Procedurally drawn menu furniture: wooden planks, medallions, parchment.

Every function returns a PIL image drawn at the pixel size it is asked for,
so callers can build art that matches the real window instead of scaling a
small image up.
"""

import numpy
import PIL.Image
import PIL.ImageChops
import PIL.ImageDraw
import PIL.ImageFilter

from ..config import (
    HUD_PLATE_EDGE, HUD_PLATE_FILL, HUD_PLATE_HOVER, PARCHMENT_DARK,
    PARCHMENT_LIGHT, PLANK_EDGE, STUD_BASE, STUD_HOVER, WOOD_BASE, WOOD_HOVER,
)

SUPERSAMPLE = 4  # drawn large, then shrunk, for clean edges


def wood_fill(size, hovered):
    """A vertical wood gradient, lightest along the middle."""
    width, height = size
    top_wood, bottom_wood = WOOD_HOVER if hovered else WOOD_BASE
    rows = numpy.linspace(0.0, 1.0, height)[:, None]
    lit = 1.0 - numpy.abs(2.0 * rows - 1.0) ** 1.6
    gradient = numpy.zeros((height, width, 3), dtype=numpy.uint8)
    for channel, (dark, light) in enumerate(zip(bottom_wood, top_wood)):
        gradient[:, :, channel] = (dark + (light - dark) * lit).astype(numpy.uint8)
    return PIL.Image.fromarray(gradient)


def add_drop_shadow(art, mask, blur, drop):
    """Composite `art` over a blurred, offset silhouette of `mask`."""
    shadow = PIL.Image.new("RGBA", art.size, (0, 0, 0, 0))
    shadow.paste((18, 10, 4, 150), (0, 0), mask)
    shadow = shadow.transform(art.size, PIL.Image.AFFINE, (1, 0, 0, 0, 1, -drop))
    shadow = shadow.filter(PIL.ImageFilter.GaussianBlur(blur))
    return PIL.Image.alpha_composite(shadow, art)


def draw_plank(width, height, pad, hovered):
    """A rectangular wooden plank with corner rivets and a drop shadow."""
    scaled_pad = pad * SUPERSAMPLE
    body_w, body_h = width * SUPERSAMPLE, height * SUPERSAMPLE
    w, h = body_w + 2 * scaled_pad, body_h + 2 * scaled_pad
    box = (scaled_pad, scaled_pad, scaled_pad + body_w, scaled_pad + body_h)
    radius = round(body_h * 0.22)

    mask = PIL.Image.new("L", (w, h), 0)
    PIL.ImageDraw.Draw(mask).rounded_rectangle(box, radius, fill=255)

    plank = PIL.Image.new("RGBA", (w, h), (0, 0, 0, 0))
    plank.paste(wood_fill((w, h), hovered), (0, 0), mask)

    detail = PIL.Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pen = PIL.ImageDraw.Draw(detail)
    for fraction, alpha in ((0.24, 44), (0.5, 28), (0.78, 50)):
        y = scaled_pad + body_h * fraction
        pen.line([(0, y), (w, y)], fill=(64, 36, 16, alpha), width=SUPERSAMPLE)
    pen.rounded_rectangle(box, radius, outline=PLANK_EDGE, width=3 * SUPERSAMPLE)
    pen.line(
        [(scaled_pad + radius, scaled_pad + 4 * SUPERSAMPLE),
         (scaled_pad + body_w - radius, scaled_pad + 4 * SUPERSAMPLE)],
        fill=(255, 236, 196, 70), width=2 * SUPERSAMPLE,
    )
    rivet_r = body_h * 0.065
    inset = radius * 0.8
    stud_fill = STUD_HOVER if hovered else STUD_BASE
    for cx in (scaled_pad + inset, scaled_pad + body_w - inset):
        for cy in (scaled_pad + inset, scaled_pad + body_h - inset):
            pen.ellipse(
                [cx - rivet_r, cy - rivet_r, cx + rivet_r, cy + rivet_r],
                fill=stud_fill, outline=PLANK_EDGE, width=2 * SUPERSAMPLE,
            )
    detail.putalpha(PIL.ImageChops.multiply(detail.split()[3], mask))
    plank = PIL.Image.alpha_composite(plank, detail)

    art = add_drop_shadow(plank, mask, 2.0 * SUPERSAMPLE, 2.0 * SUPERSAMPLE)
    return art.resize((width + 2 * pad, height + 2 * pad), PIL.Image.LANCZOS)


def draw_disc(diameter, pad, hovered):
    """A round wooden medallion button."""
    scaled_pad = pad * SUPERSAMPLE
    body = diameter * SUPERSAMPLE
    w = h = body + 2 * scaled_pad
    box = (scaled_pad, scaled_pad, scaled_pad + body, scaled_pad + body)

    mask = PIL.Image.new("L", (w, h), 0)
    PIL.ImageDraw.Draw(mask).ellipse(box, fill=255)

    disc = PIL.Image.new("RGBA", (w, h), (0, 0, 0, 0))
    disc.paste(wood_fill((w, h), hovered), (0, 0), mask)

    pen = PIL.ImageDraw.Draw(disc)
    pen.ellipse(box, outline=PLANK_EDGE, width=3 * SUPERSAMPLE)
    inner = body * 0.11
    pen.ellipse(
        (box[0] + inner, box[1] + inner, box[2] - inner, box[3] - inner),
        outline=STUD_HOVER if hovered else STUD_BASE, width=2 * SUPERSAMPLE,
    )

    art = add_drop_shadow(disc, mask, 2.0 * SUPERSAMPLE, 2.0 * SUPERSAMPLE)
    return art.resize((diameter + 2 * pad, diameter + 2 * pad), PIL.Image.LANCZOS)


def draw_hud_plate(width, height, pad, hovered):
    """A dark translucent tile that lifts a HUD icon off the scene behind it."""
    scaled_pad = pad * SUPERSAMPLE
    body_w, body_h = width * SUPERSAMPLE, height * SUPERSAMPLE
    w, h = body_w + 2 * scaled_pad, body_h + 2 * scaled_pad
    box = (scaled_pad, scaled_pad, scaled_pad + body_w, scaled_pad + body_h)
    radius = round(min(body_w, body_h) * 0.3)

    mask = PIL.Image.new("L", (w, h), 0)
    PIL.ImageDraw.Draw(mask).rounded_rectangle(box, radius, fill=255)

    plate = PIL.Image.new("RGBA", (w, h), (0, 0, 0, 0))
    PIL.ImageDraw.Draw(plate).rounded_rectangle(
        box, radius,
        fill=HUD_PLATE_HOVER if hovered else HUD_PLATE_FILL,
        outline=HUD_PLATE_EDGE, width=2 * SUPERSAMPLE,
    )

    art = add_drop_shadow(plate, mask, 2.0 * SUPERSAMPLE, 2.0 * SUPERSAMPLE)
    return art.resize((width + 2 * pad, height + 2 * pad), PIL.Image.LANCZOS)


def draw_card(width, height, pad):
    """A parchment card in a wooden frame."""
    scaled_pad = pad * SUPERSAMPLE
    body_w, body_h = width * SUPERSAMPLE, height * SUPERSAMPLE
    w, h = body_w + 2 * scaled_pad, body_h + 2 * scaled_pad
    box = (scaled_pad, scaled_pad, scaled_pad + body_w, scaled_pad + body_h)
    radius = round(body_h * 0.08)

    mask = PIL.Image.new("L", (w, h), 0)
    PIL.ImageDraw.Draw(mask).rounded_rectangle(box, radius, fill=255)

    rows = numpy.linspace(0.0, 1.0, h)[:, None]
    paper = numpy.zeros((h, w, 3), dtype=numpy.uint8)
    for channel, (light, dark) in enumerate(zip(PARCHMENT_LIGHT, PARCHMENT_DARK)):
        paper[:, :, channel] = (light + (dark - light) * rows).astype(numpy.uint8)

    card = PIL.Image.new("RGBA", (w, h), (0, 0, 0, 0))
    card.paste(PIL.Image.fromarray(paper), (0, 0), mask)

    pen = PIL.ImageDraw.Draw(card)
    pen.rounded_rectangle(box, radius, outline=PLANK_EDGE, width=5 * SUPERSAMPLE)
    inset = 7 * SUPERSAMPLE
    pen.rounded_rectangle(
        (box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset),
        round(radius * 0.8), outline=STUD_BASE, width=2 * SUPERSAMPLE,
    )

    art = add_drop_shadow(card, mask, 3.0 * SUPERSAMPLE, 3.0 * SUPERSAMPLE)
    return art.resize((width + 2 * pad, height + 2 * pad), PIL.Image.LANCZOS)
