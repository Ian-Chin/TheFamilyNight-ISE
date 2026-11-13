import functools

import arcade
import PIL.Image
import PIL.ImageFilter

from .art.keying import add_rim, key_out_paper, key_out_white, solid_bbox, to_art_height, trim
from .art.spritesheet import (
    carry_group_sizes, group_sizes, load_carry_frames, load_idle_frames,
    load_kid_frames, load_terry_frames,
)
from .art.widgets import (
    draw_card, draw_dialog_box, draw_disc, draw_hud_plate, draw_keycap,
    draw_plank, draw_title_band,
)
from .artcache import baked
from ..config import (
    BACKGROUND_DIR, CARRY_DIR, CARRY_IDLE_FILES, CARRY_JUMP_FILES, CARRY_WALK_FILES,
    CHAO_DINER_DIR, CHAO_SHEET_COLS, CHAO_SHEET_ROWS, CHARACTER_DIR, DAYCYCLE_SHEET, DAY_BADGE_BOXES, ICON_DIR, IDLE_SHEET,
    IDLE_SHEETS, KID_CAUGHT_FRAMES, KID_RUN_FRAMES, KID_SHEETS, MOVEMENT_SHEET,
    SPRITE_DIR, TERRY_FACES, TERRY_SHOCKED, UI_DIR,
)


def _texture(image):
    return arcade.Texture(image, hit_box_algorithm=arcade.hitbox.algo_bounding_box)


@functools.lru_cache(maxsize=None)
def terry_frames(glow=True):
    sources = [SPRITE_DIR / MOVEMENT_SHEET, SPRITE_DIR / IDLE_SHEET]
    groups = group_sizes()

    def build():
        return [frame for group in load_terry_frames(glow) for frame in group]

    name = "terry-frames" if glow else "terry-frames-noglow"
    return _grouped(baked(name, sources, build), groups)


@functools.lru_cache(maxsize=None)
def terry_carry_frames():
    names = (*CARRY_WALK_FILES, *CARRY_JUMP_FILES, *CARRY_IDLE_FILES)
    sources = [SPRITE_DIR / CARRY_DIR / name for name in names]

    def build():
        return [frame for group in load_carry_frames() for frame in group]

    counts = carry_group_sizes()
    name = "terry-carry-" + "-".join(map(str, counts))
    return _grouped(baked(name, sources, build), counts)


@functools.lru_cache(maxsize=None)
def kid_frames(name):
    counts = (KID_RUN_FRAMES, KID_CAUGHT_FRAMES)

    def build():
        return [frame for group in load_kid_frames(name) for frame in group]

    return _grouped(
        baked(f"kid-{name.lower()}", [SPRITE_DIR / KID_SHEETS[name]], build),
        counts,
    )


@functools.lru_cache(maxsize=None)
def idle_frames(art, glow=True):
    if art not in IDLE_SHEETS:
        return None
    source = SPRITE_DIR / IDLE_SHEETS[art]

    def build():
        return load_idle_frames(art, glow)

    name = f"idle-{source.stem}" + ("" if glow else "-noglow")
    return [_texture(frame) for frame in baked(name, [source], build)]


@functools.lru_cache(maxsize=None)
def _terry_face(filename, name):
    source = SPRITE_DIR / filename

    def build():
        image = PIL.Image.open(source)
        if image.mode != "RGBA" or image.getchannel("A").getextrema()[0] > 128:
            image = key_out_paper(image)
        small, = to_art_height([trim(image.convert("RGBA"))])
        return add_rim(small, glow=False)

    return _texture(baked(name, [source], build))


def terry_shocked():
    return _terry_face(TERRY_SHOCKED, "terry-shocked")


@functools.lru_cache(maxsize=None)
def terry_faces():
    idle = terry_frames(glow=False)[2][0].image
    left, top, right, bottom = solid_bbox(idle)
    middle = (left + right) / 2
    faces = {}
    for name, filename in TERRY_FACES.items():
        face = _terry_face(filename, f"terry-face-{name}").image
        face = face.crop(solid_bbox(face))
        height = bottom - top
        face = face.resize((round(face.width * height / face.height), height),
                           PIL.Image.LANCZOS)
        width = max(idle.width, face.width + 2 * left)
        canvas = PIL.Image.new("RGBA", (width, idle.height))
        shift = (width - idle.width) / 2
        canvas.paste(face, (round(shift + middle - face.width / 2), top), face)
        faces[name] = _texture(canvas)
    return faces


def _grouped(frames, counts):
    textures, start = [], 0
    for count in counts:
        textures.append([_texture(f) for f in frames[start:start + count]])
        start += count
    return tuple(textures)


def body_share(texture):
    bounds = solid_bbox(texture.image)
    return (bounds[3] - bounds[1]) / texture.height if bounds else 1.0


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
def character(filename, glow=True):
    source = CHARACTER_DIR / filename

    def build():
        image = PIL.Image.open(source)
        cut_out = (
            image.mode == "RGBA"
            and image.getchannel("A").getextrema()[0] < 255
        )
        if not cut_out:
            image = key_out_white(image)
        small, = to_art_height([trim(image.convert("RGBA"))])
        return add_rim(small, glow)

    name = f"character-{source.stem}" + ("" if glow else "-noglow")
    return _texture(baked(name, [source], build))


@functools.lru_cache(maxsize=None)
def diner_frames(name, kind):
    sheet = PIL.Image.open(SPRITE_DIR / CHAO_DINER_DIR / f"{name.lower()}-{kind}-sheet.png")
    sheet = sheet.convert("RGBA")
    width = sheet.width // CHAO_SHEET_COLS
    height = sheet.height // CHAO_SHEET_ROWS
    return [
        _texture(sheet.crop((col * width, row * height,
                             (col + 1) * width, (row + 1) * height)))
        for row in range(CHAO_SHEET_ROWS)
        for col in range(CHAO_SHEET_COLS)
    ]


@functools.lru_cache(maxsize=16)
def _icon_source(name):
    return PIL.Image.open(ICON_DIR / f"{name}.png").convert("RGBA")


@functools.lru_cache(maxsize=64)
def icon(name, size):
    source = _icon_source(name)
    return _texture(source.resize((size, size), PIL.Image.LANCZOS))


@functools.lru_cache(maxsize=16)
def background(name):
    return arcade.load_texture(BACKGROUND_DIR / name)


@functools.lru_cache(maxsize=16)
def keycap(width, height, pad):
    return _texture(draw_keycap(width, height, pad))


@functools.lru_cache(maxsize=8)
def title_band(width, height):
    return _texture(draw_title_band(width, height))


@functools.lru_cache(maxsize=4)
def blurred_background(name, radius):
    image = PIL.Image.open(BACKGROUND_DIR / name).convert("RGBA")
    return _texture(image.filter(PIL.ImageFilter.GaussianBlur(radius)))


@functools.lru_cache(maxsize=32)
def preview(name, width):
    image = PIL.Image.open(BACKGROUND_DIR / name).convert("RGBA")
    w, h = image.size
    if w * 9 > h * 16:
        crop_w = h * 16 // 9
        box = ((w - crop_w) // 2, 0, (w + crop_w) // 2, h)
    else:
        crop_h = w * 9 // 16
        box = (0, (h - crop_h) // 2, w, (h + crop_h) // 2)
    size = (width, max(1, round(width * 9 / 16)))
    return _texture(image.crop(box).resize(size, PIL.Image.LANCZOS))


@functools.lru_cache(maxsize=16)
def ui_cutout(name):
    image = PIL.Image.open(UI_DIR / name).convert("RGBA")
    return _texture(image.crop(image.getbbox()))


@functools.lru_cache(maxsize=16)
def ui_image(name):
    return arcade.load_texture(UI_DIR / name)


@functools.lru_cache(maxsize=1)
def day_badges():
    sheet = PIL.Image.open(UI_DIR / DAYCYCLE_SHEET).convert("RGBA")
    return tuple(
        _texture(sheet.crop((x, y, x + w, y + h)))
        for x, y, w, h in DAY_BADGE_BOXES
    )
