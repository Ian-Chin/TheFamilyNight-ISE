import PIL.Image
import PIL.ImageChops
import PIL.ImageDraw
import PIL.ImageFilter

from ...config import (
    GLASS_EDGE, GLASS_EDGE_HOVER, GLASS_FILL, GLASS_FILL_HOVER, GLASS_FILL_PANEL,
    GLASS_SHADOW, GLASS_SHEEN, KEYCAP_EDGE, KEYCAP_FACE, KEYCAP_LIP, TITLE_BAND_ALPHA,
    TITLE_BAND_COLOR,
)

SUPERSAMPLE = 4  # drawn large, then shrunk, for clean edges


def layer(size, shape, **kwargs):
    image = PIL.Image.new("RGBA", size, (0, 0, 0, 0))
    shape(PIL.ImageDraw.Draw(image), **kwargs)
    return image


def rounded(box, radius):
    def shape(pen, **kwargs):
        pen.rounded_rectangle(box, radius, **kwargs)
    return shape


def ellipse(box):
    def shape(pen, **kwargs):
        pen.ellipse(box, **kwargs)
    return shape


def add_drop_shadow(art, mask, blur, drop):
    shadow = PIL.Image.new("RGBA", art.size, (0, 0, 0, 0))
    shadow.paste(GLASS_SHADOW, (0, 0), mask)
    shadow = shadow.transform(art.size, PIL.Image.AFFINE, (1, 0, 0, 0, 1, -drop))
    shadow = shadow.filter(PIL.ImageFilter.GaussianBlur(blur))
    return PIL.Image.alpha_composite(shadow, art)


def add_sheen(panel, shape):
    width, height = panel.size
    band = PIL.Image.new("RGBA", panel.size, (0, 0, 0, 0))
    PIL.ImageDraw.Draw(band).rectangle(
        (0, 0, width, height * 0.42), fill=GLASS_SHEEN,
    )
    clip = layer(panel.size, shape, fill=255).split()[3]
    band.putalpha(PIL.ImageChops.multiply(band.split()[3], clip))
    return PIL.Image.alpha_composite(panel, band)


def glass_panel(size, shape, hovered, edge_width=2, sheen=True, fill=None):
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
    mask = layer(panel.size, shape, fill=255).split()[3]
    art = add_drop_shadow(panel, mask, blur * SUPERSAMPLE, drop * SUPERSAMPLE)
    return art.resize((width + 2 * pad, height + 2 * pad), PIL.Image.LANCZOS)


def geometry(width, height, pad):
    scaled_pad = pad * SUPERSAMPLE
    body_w, body_h = width * SUPERSAMPLE, height * SUPERSAMPLE
    size = (body_w + 2 * scaled_pad, body_h + 2 * scaled_pad)
    box = (scaled_pad, scaled_pad, scaled_pad + body_w, scaled_pad + body_h)
    return size, box


def draw_plank(width, height, pad, hovered):
    size, box = geometry(width, height, pad)
    shape = rounded(box, round(height * SUPERSAMPLE * 0.28))
    return finish(glass_panel(size, shape, hovered), shape, width, height, pad)


def draw_disc(diameter, pad, hovered):
    size, box = geometry(diameter, diameter, pad)
    shape = ellipse(box)
    return finish(
        glass_panel(size, shape, hovered), shape, diameter, diameter, pad
    )


def draw_hud_plate(width, height, pad, hovered):
    size, box = geometry(width, height, pad)
    shape = rounded(box, round(min(width, height) * SUPERSAMPLE * 0.3))
    return finish(glass_panel(size, shape, hovered), shape, width, height, pad)


def draw_card(width, height, pad):
    size, box = geometry(width, height, pad)
    radius = round(height * SUPERSAMPLE * 0.07)
    shape = rounded(box, radius)
    panel = glass_panel(size, shape, False, edge_width=1, fill=GLASS_FILL_PANEL)
    panel = add_inner_frame(panel, box, radius, 8 * SUPERSAMPLE)
    return finish(panel, shape, width, height, pad, blur=3.0, drop=3.0)


def draw_dialog_box(width, height, pad):
    size, box = geometry(width, height, pad)
    radius = round(height * SUPERSAMPLE * 0.13)
    shape = rounded(box, radius)
    panel = glass_panel(size, shape, False, edge_width=1, fill=GLASS_FILL_PANEL)
    panel = add_inner_frame(panel, box, radius, 10 * SUPERSAMPLE)
    return finish(panel, shape, width, height, pad, blur=3.0, drop=3.0)


def draw_keycap(width, height, pad):
    size, box = geometry(width, height, pad)
    radius = round(height * SUPERSAMPLE * 0.22)
    lip = round(height * SUPERSAMPLE * 0.14)
    shape = rounded(box, radius)
    base = layer(size, shape, fill=KEYCAP_LIP)
    top = layer(
        size, rounded((box[0], box[1], box[2], box[3] - lip), radius),
        fill=KEYCAP_FACE,
    )
    edge = layer(size, shape, outline=KEYCAP_EDGE, width=SUPERSAMPLE)
    art = PIL.Image.alpha_composite(PIL.Image.alpha_composite(base, top), edge)
    return finish(art, shape, width, height, pad)


def draw_title_band(width, height):
    band = PIL.Image.new("L", (1, height))
    for y in range(height):
        share = min(y, height - 1 - y) / (height / 3)
        band.putpixel((0, y), round(TITLE_BAND_ALPHA * min(1.0, share)))
    art = PIL.Image.new("RGBA", (width, height), (*TITLE_BAND_COLOR, 0))
    art.putalpha(band.resize((width, height)))
    return art
