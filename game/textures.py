"""The one place PIL images become arcade textures, and files become assets.

Widget art is cached by the pixel size it was built at, so a resize rebuilds
each texture once and reuses it from then on.
"""

import functools

import arcade
import PIL.Image
import PIL.ImageFilter

from .art.keying import add_rim, key_out_white, solid_bbox, to_art_height, trim
from .art.parts import face_frames, morsel, pale_edge, split_parts
from .art.spritesheet import (
    carry_group_sizes, group_sizes, load_carry_frames, load_idle_frames,
    load_kid_frames, load_terry_frames, terry_idle_cells,
)
from .art.widgets import (
    draw_card, draw_dialog_box, draw_disc, draw_hud_plate, draw_keycap,
    draw_plank, draw_title_band,
)
from .artcache import baked
from .config import (
    BACKGROUND_DIR, CARRY_DIR, CARRY_IDLE_FILES, CARRY_JUMP_FILES,
    CARRY_WALK_FILES, CHAO_FACES, CHARACTER_DIR, DAY_BADGE_BOXES,
    DAYCYCLE_SHEET, ICON_DIR, IDLE_SHEET, IDLE_SHEETS, KID_CAUGHT_FRAMES,
    KID_RUN_FRAMES,
    KID_SHEETS, MOVEMENT_SHEET, SPRITE_DIR, TERRY_SHOCKED, UI_DIR,
)


def _texture(image):
    # Nothing here uses arcade's own collision, so the cheap bounding box
    # stands in for tracing a hit box out of the alpha channel.
    return arcade.Texture(image, hit_box_algorithm=arcade.hitbox.algo_bounding_box)


@functools.lru_cache(maxsize=None)
def terry_frames(glow=True):
    """(walk, jump, idle) texture lists, built once per run."""
    sources = [SPRITE_DIR / MOVEMENT_SHEET, SPRITE_DIR / IDLE_SHEET]
    groups = group_sizes()

    def build():
        # Baked as one strip: the frames already share a canvas size.
        return [frame for group in load_terry_frames(glow) for frame in group]

    name = "terry-frames" if glow else "terry-frames-noglow"
    return _grouped(baked(name, sources, build), groups)


@functools.lru_cache(maxsize=None)
def terry_carry_frames():
    """(walk, jump, idle) texture lists of Terry holding the food tray."""
    names = (*CARRY_WALK_FILES, *CARRY_JUMP_FILES, *CARRY_IDLE_FILES)
    sources = [SPRITE_DIR / CARRY_DIR / name for name in names]

    def build():
        return [frame for group in load_carry_frames() for frame in group]

    # The frame lists are in the name, so regrouping the files rebakes.
    counts = carry_group_sizes()
    name = "terry-carry-" + "-".join(map(str, counts))
    return _grouped(baked(name, sources, build), counts)


@functools.lru_cache(maxsize=None)
def kid_frames(name):
    """(run, caught) texture lists for "Tom" or "Jess"."""
    counts = (KID_RUN_FRAMES, KID_CAUGHT_FRAMES)

    def build():
        return [frame for group in load_kid_frames(name) for frame in group]

    return _grouped(
        baked(f"kid-{name.lower()}", [SPRITE_DIR / KID_SHEETS[name]], build),
        counts,
    )


@functools.lru_cache(maxsize=None)
def idle_frames(art, glow=True):
    """A family member's breathing frames, or None if they have no sheet."""
    if art not in IDLE_SHEETS:
        return None
    source = SPRITE_DIR / IDLE_SHEETS[art]

    def build():
        return load_idle_frames(art, glow)

    name = f"idle-{source.stem}" + ("" if glow else "-noglow")
    return [_texture(frame) for frame in baked(name, [source], build)]


@functools.lru_cache(maxsize=None)
def terry_shocked():
    """Terry wide-eyed and sweating, cut out like the family's art."""
    source = SPRITE_DIR / TERRY_SHOCKED

    def build():
        image = PIL.Image.open(source).convert("RGBA")
        small, = to_art_height([trim(image)])
        return add_rim(small, glow=False)

    return _texture(baked("terry-shocked", [source], build))


def _grouped(frames, counts):
    textures, start = [], 0
    for count in counts:
        textures.append([_texture(f) for f in frames[start:start + count]])
        start += count
    return tuple(textures)


def body_share(texture):
    """Fraction of the frame's height the drawn character fills."""
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
        return add_rim(small, glow)

    name = f"character-{source.stem}" + ("" if glow else "-noglow")
    return _texture(baked(name, [source], build))


class DinerParts:
    """A character taken apart to sit at the table.

    `faces` maps (eyes shut, mouth) to a head texture, `hands` and `feet` are
    (left, right) textures, and every `*_at` is a part's centre in art pixels
    measured from the middle of the whole figure, y up.
    """

    def __init__(self, art_height, faces, head_at, hands, hands_at, feet,
                 feet_at, mouth_at):
        self.art_height = art_height
        self.faces = faces
        self.head_at = head_at
        self.hands = hands
        self.hands_at = hands_at
        self.feet = feet
        self.feet_at = feet_at
        self.mouth_at = mouth_at


@functools.lru_cache(maxsize=8)
def diner_parts(art):
    """`art` is "Terry" or a family member's art file, as in CHAO_FACES."""
    if art == "Terry":
        image = terry_idle_cells()[0]
    else:
        image = PIL.Image.open(CHARACTER_DIR / art)
        if not (image.mode == "RGBA" and image.getchannel("A").getextrema()[0] < 255):
            image = key_out_white(image)
    whole, = to_art_height([trim(image.convert("RGBA"))])
    head, hands, feet = split_parts(whole)

    def placed(x, y):
        return (x - whole.width / 2, whole.height / 2 - y)

    def on_head(box):
        """A box on the whole figure, in the head's own pixels."""
        return (box[0] - head.left, box[1] - head.top,
                box[2] - head.left, box[3] - head.top)

    eyes, mouth = CHAO_FACES[art]
    faces = face_frames(head.image, [on_head(box) for box in eyes], on_head(mouth))
    return DinerParts(
        whole.height,
        {key: _texture(add_rim(face, glow=False)) for key, face in faces.items()},
        placed(*head.center),
        tuple(_texture(add_rim(hand.image, glow=False)) for hand in hands),
        tuple(placed(*hand.center) for hand in hands),
        tuple(_texture(pale_edge(add_rim(foot.image, glow=False))) for foot in feet),
        tuple(placed(*foot.center) for foot in feet),
        placed((mouth[0] + mouth[2]) / 2, (mouth[1] + mouth[3]) / 2),
    )


@functools.lru_cache(maxsize=1)
def morsel_texture():
    return _texture(morsel(48))


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
def keycap(width, height, pad):
    return _texture(draw_keycap(width, height, pad))


@functools.lru_cache(maxsize=8)
def title_band(width, height):
    return _texture(draw_title_band(width, height))


@functools.lru_cache(maxsize=4)
def blurred_background(name, radius):
    """A background still, softened, to sit behind a title card."""
    image = PIL.Image.open(BACKGROUND_DIR / name).convert("RGBA")
    return _texture(image.filter(PIL.ImageFilter.GaussianBlur(radius)))


@functools.lru_cache(maxsize=16)
def ui_cutout(name):
    """A UI image with its transparent margin trimmed off."""
    image = PIL.Image.open(UI_DIR / name).convert("RGBA")
    return _texture(image.crop(image.getbbox()))


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
