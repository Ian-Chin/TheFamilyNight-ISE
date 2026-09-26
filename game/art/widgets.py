"""Procedurally drawn UI furniture: one piece of smoked glass, several shapes.

Every widget is the same thing at heart, a near-black translucent panel with a
thin bright edge, so buttons, plates, cards and the dialogue box all read as
one set. Each function returns a PIL image drawn at the pixel size it is asked
for, so callers can build art that matches the real window instead of scaling
a small image up.

Each pass is drawn on its own layer and composited, never painted straight
over the one below: ImageDraw replaces pixels rather than blending them, so a
faint edge drawn onto the body would punch a hole in it instead of lifting it.
"""

import PIL.Image
import PIL.ImageChops
import PIL.ImageDraw
import PIL.ImageFilter

from ..config import (
    GLASS_EDGE, GLASS_EDGE_HOVER, GLASS_FILL, GLASS_FILL_HOVER,
    GLASS_FILL_PANEL, GLASS_SHADOW, GLASS_SHEEN,
)

SUPERSAMPLE = 4  # drawn large, then shrunk, for clean edges


def layer(size, shape, **kwargs):
    """One drawing pass of `shape` on its own transparent image."""
    image = PIL.Image.new("RGBA", size, (0, 0, 0, 0))
    shape(PIL.ImageDraw.Draw(image), **kwargs)
    return image


def rounded(box, radius):
    """A rounded rectangle, as a shape callable."""
    def shape(pen, **kwargs):
        pen.rounded_rectangle(box, radius, **kwargs)
    return shape


def ellipse(box):
    """A circle or oval, as a shape callable."""
    def shape(pen, **kwargs):
        pen.ellipse(box, **kwargs)
    return shape


def add_drop_shadow(art, mask, blur, drop):
    """Composite `art` over a blurred, offset silhouette of `mask`."""
    shadow = PIL.Image.new("RGBA", art.size, (0, 0, 0, 0))
    shadow.paste(GLASS_SHADOW, (0, 0), mask)
    shadow = shadow.transform(art.size, PIL.Image.AFFINE, (1, 0, 0, 0, 1, -drop))
    shadow = shadow.filter(PIL.ImageFilter.GaussianBlur(blur))
    return PIL.Image.alpha_composite(shadow, art)


def add_sheen(panel, shape):
    """A soft band along the top, clipped to the body, as a lit upper edge."""
    width, height = panel.size
    band = PIL.Image.new("RGBA", panel.size, (0, 0, 0, 0))
    PIL.ImageDraw.Draw(band).rectangle(
        (0, 0, width, height * 0.42), fill=GLASS_SHEEN,
    )
    clip = layer(panel.size, shape, fill=255).split()[3]
    band.putalpha(PIL.ImageChops.multiply(band.split()[3], clip))
    return PIL.Image.alpha_composite(panel, band)


def glass_panel(size, shape, hovered, edge_width=2, sheen=True, fill=None):
    """A translucent dark panel in `shape`, edged and lit along the top."""
    if fill is None:
        fill = GLASS_FILL_HOVER if hovered else GLASS_FILL
    panel = layer(size, shape, fill=fill)
    if sheen:
        panel = add_sheen(panel, shape)
    edge = layer(
        size, shape,
        outline=GLASS_EDGE_HOVER if hovered else GLASS_EDGE,
        width=edge_width * SUPERSAMPLE,
    )
    return PIL.Image.alpha_composite(panel, edge)


def add_inner_frame(panel, box, radius, inset):
    """A hairline just inside the edge, for the larger panels."""
    frame = layer(
        panel.size,
        rounded(
            (box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset),
            round(radius * 0.7),
        ),
        outline=GLASS_EDGE, width=SUPERSAMPLE,
    )
    return PIL.Image.alpha_composite(panel, frame)


def finish(panel, shape, width, height, pad, blur=2.0, drop=2.0):
    """Drop-shadow a panel and bring it down to its real pixel size."""
    mask = layer(panel.size, shape, fill=255).split()[3]
    art = add_drop_shadow(panel, mask, blur * SUPERSAMPLE, drop * SUPERSAMPLE)
    return art.resize((width + 2 * pad, height + 2 * pad), PIL.Image.LANCZOS)


def geometry(width, height, pad):
    """The supersampled canvas size and body box for a widget."""
    scaled_pad = pad * SUPERSAMPLE
    body_w, body_h = width * SUPERSAMPLE, height * SUPERSAMPLE
    size = (body_w + 2 * scaled_pad, body_h + 2 * scaled_pad)
    box = (scaled_pad, scaled_pad, scaled_pad + body_w, scaled_pad + body_h)
    return size, box


def draw_plank(width, height, pad, hovered):
    """A button: a rounded slab of glass that brightens under the pointer."""
    size, box = geometry(width, height, pad)
    shape = rounded(box, round(height * SUPERSAMPLE * 0.28))
    return finish(glass_panel(size, shape, hovered), shape, width, height, pad)


def draw_disc(diameter, pad, hovered):
    """A round glass button."""
    size, box = geometry(diameter, diameter, pad)
    shape = ellipse(box)
    return finish(
        glass_panel(size, shape, hovered), shape, diameter, diameter, pad
    )


def draw_hud_plate(width, height, pad, hovered):
    """A small glass tile that lifts a HUD icon off the scene behind it."""
    size, box = geometry(width, height, pad)
    shape = rounded(box, round(min(width, height) * SUPERSAMPLE * 0.3))
    return finish(glass_panel(size, shape, hovered), shape, width, height, pad)


def draw_card(width, height, pad):
    """A popup panel: the same glass, squarer and a touch more opaque."""
    size, box = geometry(width, height, pad)
    radius = round(height * SUPERSAMPLE * 0.07)
    shape = rounded(box, radius)
    panel = glass_panel(size, shape, False, edge_width=1, fill=GLASS_FILL_PANEL)
    panel = add_inner_frame(panel, box, radius, 8 * SUPERSAMPLE)
    return finish(panel, shape, width, height, pad, blur=3.0, drop=3.0)


def draw_dialog_box(width, height, pad):
    """The speech panel: a wide sheet of glass with an inner hairline frame."""
    size, box = geometry(width, height, pad)
    radius = round(height * SUPERSAMPLE * 0.13)
    shape = rounded(box, radius)
    panel = glass_panel(size, shape, False, edge_width=1, fill=GLASS_FILL_PANEL)
    panel = add_inner_frame(panel, box, radius, 10 * SUPERSAMPLE)
    return finish(panel, shape, width, height, pad, blur=3.0, drop=3.0)
