import PIL.Image
import PIL.ImageChops
import PIL.ImageDraw
import PIL.ImageFilter
import PIL.ImageOps

from ...config import (
    CHARACTER_ART_HEIGHT, CLEAR_ABOVE, OPAQUE_BELOW, RIM_DARK, RIM_DARK_COLOR,
    RIM_GLOW, RIM_GLOW_COLOR, SOLID_ALPHA,
)


def key_out_white(image):
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


def key_out_paper(image):
    keyed = key_out_white(image)
    red, green, blue, _ = keyed.split()
    darkest = PIL.ImageChops.darker(PIL.ImageChops.darker(red, green), blue)
    pale = darkest.point(lambda v: 255 if v > OPAQUE_BELOW else 0)
    pale = PIL.ImageOps.expand(pale, 1, fill=255)
    PIL.ImageDraw.floodfill(pale, (0, 0), 128)
    pale = pale.crop((1, 1, pale.width - 1, pale.height - 1))
    enclosed = pale.point(lambda v: 0 if v == 128 else 255)
    keyed.putalpha(PIL.ImageChops.lighter(keyed.getchannel("A"), enclosed))
    return keyed


def solid_bbox(image):
    solid = image.split()[3].point(lambda v: 255 if v > SOLID_ALPHA else 0)
    return solid.getbbox()


def trim(image):
    bounds = solid_bbox(image)
    return image.crop(bounds) if bounds else image


def grown(alpha, radius):
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
    tallest = max(image.height for image in images)
    ratio = min(1.0, CHARACTER_ART_HEIGHT / tallest)
    return [scaled(image, ratio) for image in images]


def add_rim(image, glow=True):
    margin = RIM_DARK + RIM_GLOW
    padded = PIL.Image.new(
        "RGBA",
        (image.width + 2 * margin, image.height + 2 * margin),
        (0, 0, 0, 0),
    )
    padded.paste(image, (margin, margin))
    alpha = padded.split()[3]

    halo = PIL.Image.new("RGBA", padded.size, (0, 0, 0, 0))
    if glow:
        halo.paste(
            RIM_GLOW_COLOR, (0, 0),
            grown(alpha, margin).filter(PIL.ImageFilter.GaussianBlur(RIM_GLOW)),
        )
    ink = PIL.Image.new("RGBA", padded.size, (0, 0, 0, 0))
    ink.paste(RIM_DARK_COLOR, (0, 0), grown(alpha, RIM_DARK))

    return PIL.Image.alpha_composite(
        PIL.Image.alpha_composite(halo, ink), padded
    )
