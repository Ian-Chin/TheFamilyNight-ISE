"""Render the closing cut scene: assets/backgrounds/video/ending.mp4.

Also writes its sound effects, timed to the picture, as
assets/audio/ending-sfx.wav (the game plays that alongside the video) and
muxes them, over the night ambience, into the mp4 so the file previews with
sound. The effects are real recordings: CC0 clips from Freesound, kept in
assets/audio/sources/ending with their credits in CREDITS.json.

The story, about 31 seconds:

    close on Terry, sat on his stool at the cleared table, patting a full belly
    two hiccups, cheeks puffing up... then one huge BURP
    embarrassed: hand over mouth, blushing, a sweat drop
    the family walk back in, laughing at the burp, amazed the table is clear
    Terry, proud: "Ahh... I'm SO full.", hearts, a big yawn and a stretch
    everyone looks up; the camera tilts into the sky as fireflies rise
    the stars draw the five of them, round heads, floating hands held
    the stars swirl together and the title bursts out, then fades to black

Everyone is a puppet cut from their idle art: the head, two hands and two
shoes, each moved separately. Terry's face is wiped and drawn on frame by
frame for his expressions. Development time only; needs Pillow, NumPy, SciPy
and PyAV.

    py -3.12 tools/make_ending.py
"""

import math
import random
import wave
from pathlib import Path

import av
import numpy
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
OUT = ASSETS / "backgrounds" / "video" / "ending.mp4"
SFX_OUT = ASSETS / "audio" / "ending-sfx.wav"
TABLE = ASSETS / "backgrounds" / "chao-dinner-keyword-game" / "Gemini_Generated_Image_rpphyjrpphyjrpph.jpg"
TERRY = ASSETS / "sprites" / "terry-idle.png"
LOGO = ASSETS / "ui" / "logo.png"
FONTS = Path("C:/Windows/Fonts")
CHARACTERS = ASSETS / "characters"
SFX_DIR = ASSETS / "audio" / "sources" / "ending"
STEP_CLIP = ASSETS / "audio" / "step-grass.wav"
NIGHT_BED = ASSETS / "audio" / "ambience-night.mp3"

W, H = 1280, 720
FPS = 30
RATE = 44100
SKY_H = 1000         # sky painted above the table art
SEAM = 240           # rows the sky blends down into the art over
TABLE_H = 715        # the table art, scaled to the frame's width

# Terry, in world units (frame pixels when the camera is at zoom 1).
SEAT = (250, SKY_H + 606)    # the top of the stool at the near end of the table
ART_SCALE = 0.29             # source art pixels to world units
HEAD_BOX = (170, 81, 820, 791)
FACE_RES = 0.5               # the face is drawn at this fraction of the source art

INK = (43, 26, 40, 255)
SKIN = (253, 190, 146, 255)
MOUTH = (110, 28, 42, 255)
TONGUE = (232, 96, 104, 255)
BLUSH = (240, 104, 120)

# --- the timeline, in seconds ---------------------------------------------------
HICS = (3.05, 3.4)
BURP = 3.75
OOPS = (4.9, 6.4)            # hand over his mouth
PULL_OUT = (6.0, 7.4)        # the close-up opens out to the whole table
FULL_LINE = 11.9             # "Ahh... I'm SO full."
YAWN = (13.9, 15.6)
LOOK_UP = 15.6
TILT = (17.2, 21.4)          # up from the garden into the sky
FAMILY_START, FAMILY_DRAWN = 21.2, 23.8
CONVERGE = (24.4, 25.25)
LOGO_POP = 25.25
LOGO_OUT = 29.4
LENGTH = 31.2
# Shooting stars: (when, from, to) in world units.
SHOOTING = ((TILT[0] + 0.9, (150, 120), (560, 300)), (LOGO_POP + 2.6, (1150, 90), (820, 240)))


# --- small helpers -----------------------------------------------------------

def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def ease(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ramp(t, a, b):
    """0 before a, 1 after b, eased between."""
    return ease((t - a) / (b - a))


def back_out(t):
    t = clamp(t)
    c = 1.9
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def window(t, start, fade_in, end, fade_out):
    """0 to 1 to 0: up over fade_in from start, down over fade_out to end."""
    if t < start or t > end:
        return 0.0
    return min(1.0, (t - start) / fade_in if fade_in else 1.0,
               (end - t) / fade_out if fade_out else 1.0)


def lerp(a, b, k):
    return a + (b - a) * k


def lerp2(p, q, k):
    return (lerp(p[0], q[0], k), lerp(p[1], q[1], k))


def font(name, size):
    try:
        return ImageFont.truetype(str(FONTS / name), size)
    except OSError:
        return ImageFont.load_default()


def text_image(text, face, fill, stroke=0, stroke_fill=(0, 0, 0), shadow=0):
    box = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox(
        (0, 0), text, font=face, stroke_width=stroke)
    pad = stroke + shadow + 4
    image = Image.new("RGBA", (box[2] - box[0] + 2 * pad, box[3] - box[1] + 2 * pad))
    draw = ImageDraw.Draw(image)
    origin = (pad - box[0], pad - box[1])
    if shadow:
        draw.text((origin[0] + shadow, origin[1] + shadow), text, font=face,
                  fill=(0, 0, 0, 170), stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
    draw.text(origin, text, font=face, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return image


def faded(image, alpha):
    if alpha >= 1:
        return image
    image = image.copy()
    image.putalpha(image.getchannel("A").point(lambda v: round(v * alpha)))
    return image


def paste_center(frame, image, x, y, alpha=1.0, scale=1.0, angle=0.0):
    if alpha <= 0.01 or scale <= 0.01:
        return
    if scale != 1.0:
        image = image.resize((max(1, round(image.width * scale)),
                              max(1, round(image.height * scale))), Image.LANCZOS)
    if angle:
        image = image.rotate(angle, Image.BICUBIC, expand=True)
    image = faded(image, alpha)
    frame.alpha_composite(image, (round(x - image.width / 2), round(y - image.height / 2)))


def star_shape(draw, x, y, r, fill):
    """A four pointed sparkle."""
    k = r * 0.28
    draw.polygon(((x, y - r), (x + k, y - k), (x + r, y), (x + k, y + k),
                  (x, y + r), (x - k, y + k), (x - r, y), (x - k, y - k)), fill=fill)


def heart_shape(draw, x, y, r, fill, outline):
    draw.ellipse((x - r, y - r * 0.8, x, y + r * 0.2), fill=fill)
    draw.ellipse((x, y - r * 0.8, x + r, y + r * 0.2), fill=fill)
    draw.polygon(((x - r * 0.97, y - r * 0.15), (x + r * 0.97, y - r * 0.15), (x, y + r)), fill=fill)
    draw.arc((x - r, y - r * 0.8, x, y + r * 0.2), 150, 360, fill=outline, width=2)
    draw.arc((x, y - r * 0.8, x + r, y + r * 0.2), 180, 30, fill=outline, width=2)
    draw.line(((x - r * 0.95, y), (x, y + r), (x + r * 0.95, y)), fill=outline, width=2)


# --- the world: night sky over the cleared table ----------------------------

SKY_TOP = numpy.array((4, 6, 20))
SKY_LOW = numpy.array((24, 32, 66))


def build_world():
    table = Image.open(TABLE).convert("RGB").resize((W, TABLE_H), Image.LANCZOS)
    world = Image.new("RGB", (W, SKY_H + TABLE_H))
    rows = numpy.linspace(0, 1, SKY_H + SEAM)[:, None] ** 1.4
    sky = (SKY_TOP * (1 - rows) + SKY_LOW * rows).astype("uint8")
    sky = numpy.repeat(sky[:, None, :], W, axis=1)
    world.paste(Image.fromarray(sky), (0, 0))

    # A faint milky way band across the upper sky.
    band = Image.new("L", (W, SKY_H), 0)
    rng = random.Random(3)
    bd = ImageDraw.Draw(band)
    for _ in range(900):
        x = rng.uniform(-100, W + 100)
        y = 120 + (x / W) * 260 + rng.gauss(0, 60)
        r = rng.uniform(20, 70)
        bd.ellipse((x - r, y - r * 0.5, x + r, y + r * 0.5), fill=rng.randint(4, 10))
    band = band.filter(ImageFilter.GaussianBlur(30))
    world.paste((90, 100, 170), (0, 0), band)

    mask = Image.new("L", table.size, 255)
    mask.paste(Image.linear_gradient("L").resize((W, SEAM)), (0, 0))
    world.paste(table, (0, SKY_H), mask)

    # The moon, high on the right, with a soft halo.
    glow = Image.new("L", (W, SKY_H), 0)
    ImageDraw.Draw(glow).ellipse((900, 70, 1180, 350), fill=80)
    world.paste((80, 92, 150), (0, 0), glow.filter(ImageFilter.GaussianBlur(70)))
    moon = Image.new("L", (W, SKY_H), 0)
    ImageDraw.Draw(moon).ellipse((1000, 170, 1084, 254), fill=255)
    ImageDraw.Draw(moon).ellipse((1024, 156, 1108, 240), fill=0)
    world.paste((250, 238, 196), (0, 0), moon.filter(ImageFilter.GaussianBlur(0.8)))
    return world


def make_stars():
    rng = random.Random(7)
    stars = []
    for _ in range(320):
        y = rng.uniform(0, SKY_H + 80)
        stars.append((rng.uniform(0, W), y, rng.choice((1, 1, 1, 2, 2, 3)),
                      rng.uniform(0, math.tau), rng.uniform(1.0, 3.6),
                      rng.uniform(0, 1)))
    return stars


# --- Terry, the puppet --------------------------------------------------------

def load_parts():
    art = Image.open(TERRY).convert("RGBA")
    clean = art.getchannel("A").point(lambda v: v if v > 30 else 0)
    art.putalpha(clean)

    head = art.crop(HEAD_BOX)
    left0, top0 = HEAD_BOX[:2]
    # Out with the hands either side of the head, and with the face.
    eraser = ImageDraw.Draw(head)
    eraser.rectangle((0, 670 - top0, 246 - left0, 772 - top0), fill=(0, 0, 0, 0))
    eraser.rectangle((777 - left0, 670 - top0, head.width, 772 - top0), fill=(0, 0, 0, 0))
    face_mask = Image.new("L", head.size, 0)
    fm = ImageDraw.Draw(face_mask)
    # Eyes, brows (and the shading under them) and mouth.
    for box in ((414, 482, 456, 628), (562, 482, 606, 628), (350, 454, 444, 494),
                (576, 452, 702, 500), (460, 660, 572, 700)):
        fm.rounded_rectangle(tuple(v - (left0 if i % 2 == 0 else top0) for i, v in enumerate(box)),
                             12, fill=255)
    head.paste(Image.new("RGBA", head.size, SKIN), (0, 0), face_mask)
    head.putalpha(ImageChops.multiply(head.getchannel("A"), art.crop(HEAD_BOX).getchannel("A")))
    head_small = head.resize((round(head.width * FACE_RES), round(head.height * FACE_RES)),
                             Image.LANCZOS)

    def part(box):
        return art.crop(box)

    hand_l = part((156, 680, 248, 771))
    hand_r = part((776, 670, 869, 763))
    shoe_l = rimmed(part((352, 858, 490, 933)))
    shoe_r = rimmed(part((568, 855, 707, 930)))
    return head_small, hand_l, hand_r, shoe_l, shoe_r


def rimmed(image, width=10, color=(150, 140, 180)):
    """A pale edge round a dark part, so it reads against dark scenery."""
    pad = width + 2
    big = Image.new("RGBA", (image.width + 2 * pad, image.height + 2 * pad))
    big.paste(image, (pad, pad))
    edge = big.getchannel("A").filter(ImageFilter.MaxFilter(2 * (width // 2) + 1))
    rim = Image.new("RGBA", big.size, (*color, 255))
    rim.putalpha(edge.point(lambda v: round(v * 0.85)))
    rim.alpha_composite(big)
    return rim


# Where the features sit on each character's art, in source art pixels:
# eye, brow and cheek centres (left, right), the mouth, and how big the drawn
# features are against Terry's.
TERRY_FACE = {
    "origin": HEAD_BOX[:2], "size": 1.0, "skin": SKIN,
    "eyes": ((434, 555), (584, 555)), "brows": ((400, 474), (632, 474)),
    "cheeks": ((346, 646), (670, 646)), "mouth": (512, 682),
    "crumb": (586, 708), "sweat": (720, 430),
}


def face_point(face, x, y, look):
    """A point on the source art's face, moved by where they are looking, in
    the small head's pixels."""
    ox, oy = face["origin"]
    return ((x - ox + look[0]) * FACE_RES, (y - oy + look[1]) * FACE_RES)


def neutral_face(**changes):
    e = {"eyes": "happy", "mouth": "smile", "mouth_size": 1.0, "blush": 0.0, "puff": 0.0,
         "sweat": None, "look": (0, 0), "pupil": (0, 0), "lid": 0.0, "crumb": False,
         "brows": None, "tears": 0.0}
    e.update(changes)
    return e


def draw_face(head, e, face=TERRY_FACE):
    """Draw expression `e` onto a copy of a blank head."""
    head = head.copy()
    over = Image.new("RGBA", head.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(over)
    k = FACE_RES * face["size"]
    look = e["look"]

    # Cheeks first, so everything else sits on top of them.
    if e["blush"] > 0 or e["puff"] > 0:
        blush = Image.new("RGBA", head.size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(blush)
        rx, ry = (46 + 22 * e["puff"]) * k, (24 + 12 * e["puff"]) * k
        alpha = round(150 * clamp(e["blush"] + 0.3 * e["puff"]))
        for c in face["cheeks"]:
            x, y = face_point(face, *c, look)
            bd.ellipse((x - rx, y - ry, x + rx, y + ry), fill=(*BLUSH, alpha))
        blush = blush.filter(ImageFilter.GaussianBlur(5 * k * 2))
        head.alpha_composite(blush)
        if e["blush"] > 0.6:
            # Little embarrassed hatching on the cheeks.
            for c in face["cheeks"]:
                x, y = face_point(face, *c, look)
                for i in range(3):
                    ox = (i - 1) * 16 * k
                    draw.line((x + ox - 6 * k, y + 8 * k, x + ox + 6 * k, y - 8 * k),
                              fill=(200, 60, 80, 200), width=round(5 * k))

    w = max(2, round(12 * k))
    brows = e["brows"]
    if brows and face["brows"]:
        for side, b in zip((-1, 1), face["brows"]):
            x, y = face_point(face, *b, look)
            inner, outer = {"raised": (-26, -26), "worried": (-16, 6), "relaxed": (2, 0),
                            "up": (-14, -14)}[brows]
            # Inner end towards the middle of the face.
            x_in, x_out = x - side * 26 * k, x + side * 26 * k
            draw.line((x_in, y + inner * k, x_out, y + outer * k), fill=INK, width=round(9 * k))
    for side, eye in zip((-1, 1), face["eyes"]):
        x, y = face_point(face, *eye, look)
        kind = e["eyes"]
        if kind == "happy":
            draw.arc((x - 36 * k, y - 4 * k, x + 36 * k, y + 52 * k), 200, 340, fill=INK, width=w)
        elif kind == "closed":
            draw.arc((x - 34 * k, y - 34 * k, x + 34 * k, y + 22 * k), 25, 155, fill=INK, width=w)
        elif kind == "open":
            draw.ellipse((x - 15 * k, y - 34 * k, x + 15 * k, y + 34 * k), fill=INK)
            draw.ellipse((x - 6 * k, y - 24 * k, x + 5 * k, y - 11 * k), fill=(255, 255, 255, 255))
        elif kind == "sparkle":
            draw.ellipse((x - 20 * k, y - 36 * k, x + 20 * k, y + 36 * k), fill=INK)
            star_shape(draw, x - 2 * k, y - 10 * k, 14 * k, (255, 255, 255, 255))
            draw.ellipse((x + 4 * k, y + 12 * k, x + 10 * k, y + 18 * k), fill=(255, 255, 255, 255))
        elif kind == "wide":
            draw.ellipse((x - 34 * k, y - 40 * k, x + 34 * k, y + 40 * k),
                         fill=(255, 255, 255, 255), outline=INK, width=round(8 * k))
            px, py = e["pupil"]
            draw.ellipse((x + (px - 11) * k, y + (py - 11) * k, x + (px + 11) * k, y + (py + 11) * k),
                         fill=INK)
        elif kind == "squint":
            d = side
            draw.line(((x - 24 * k * d, y - 26 * k), (x + 20 * k * d, y), (x - 24 * k * d, y + 26 * k)),
                      fill=INK, width=w, joint="curve")
        elif kind == "half":
            draw.ellipse((x - 16 * k, y - 26 * k, x + 16 * k, y + 30 * k), fill=INK)
            lid = e["lid"]
            draw.rectangle((x - 20 * k, y - 30 * k, x + 20 * k, y - 26 * k + lid * 54 * k),
                           fill=face["skin"])
            draw.line((x - 20 * k, y - 26 * k + lid * 54 * k, x + 20 * k, y - 26 * k + lid * 54 * k),
                      fill=INK, width=round(8 * k))

        if e.get("tears", 0) > 0:
            # Tears of laughter at the outer corners.
            a = round(230 * e["tears"])
            tx, ty = x + side * 40 * k, y + 6 * k + 10 * k * e["tears"]
            draw.ellipse((tx - 9 * k, ty - 9 * k, tx + 9 * k, ty + 11 * k), fill=(150, 210, 255, a))
            draw.polygon(((tx - 8 * k, ty - 2 * k), (tx + 8 * k, ty - 2 * k), (tx, ty - 22 * k)),
                         fill=(150, 210, 255, a))

    mx, my = face_point(face, *face["mouth"], look)
    kind = e["mouth"]
    if kind == "smile":
        draw.arc((mx - 62 * k, my - 52 * k, mx + 62 * k, my + 30 * k), 25, 155, fill=INK, width=w)
    elif kind == "grin":
        draw.chord((mx - 58 * k, my - 46 * k, mx + 58 * k, my + 46 * k), 0, 180, fill=MOUTH,
                   outline=INK, width=round(9 * k))
        draw.chord((mx - 30 * k, my + 10 * k, mx + 30 * k, my + 44 * k), 180, 360, fill=TONGUE)
        draw.chord((mx - 58 * k, my - 46 * k, mx + 58 * k, my + 46 * k), 0, 180, outline=INK,
                   width=round(9 * k))
    elif kind == "laugh":
        # Wide open, head-back laughing; mouth_size bounces it.
        a = e["mouth_size"]
        box = (mx - 64 * k, my - 40 * k * a, mx + 64 * k, my + 56 * k * a)
        draw.chord(box, 0, 180, fill=MOUTH, outline=INK, width=round(9 * k))
        draw.rectangle((mx - 56 * k, my - 4 * k, mx + 56 * k, my + 6 * k), fill=(255, 255, 255, 255))
        draw.chord((mx - 32 * k, my + 18 * k * a, mx + 32 * k, my + 54 * k * a), 180, 360, fill=TONGUE)
        draw.chord(box, 0, 180, outline=INK, width=round(9 * k))
        draw.line((box[0], my, box[2], my), fill=INK, width=round(8 * k))
    elif kind in ("O", "yawn"):
        a = e["mouth_size"]
        rx, ry = 26 * a * k, (34 if kind == "O" else 46) * a * k
        draw.ellipse((mx - rx, my - ry, mx + rx, my + ry), fill=MOUTH, outline=INK, width=round(8 * k))
        draw.chord((mx - rx * 0.7, my + ry * 0.2, mx + rx * 0.7, my + ry * 0.95), 0, 180, fill=TONGUE)
    elif kind == "puff":
        draw.line((mx - 22 * k, my, mx + 22 * k, my), fill=INK, width=w)
    elif kind == "wobble":
        points = [(mx + (i - 10) * 5 * k, my + math.sin(i * 0.9) * 7 * k) for i in range(21)]
        draw.line(points, fill=INK, width=round(10 * k), joint="curve")
    elif kind == "flat":
        draw.line((mx - 30 * k, my + 4 * k, mx + 30 * k, my + 4 * k), fill=INK, width=w)

    if e["crumb"] and face.get("crumb"):
        cx, cy = face_point(face, *face["crumb"], look)
        draw.ellipse((cx - 9 * k, cy - 7 * k, cx + 9 * k, cy + 7 * k), fill=(196, 92, 52, 255))

    if e["sweat"] is not None:
        sx, sy = face_point(face, face["sweat"][0], face["sweat"][1] + 120 * e["sweat"], (0, 0))
        r = 20 * k
        drop = [(sx, sy - r * 2.2), (sx + r, sy), (sx, sy + r), (sx - r, sy)]
        draw.polygon(drop, fill=(150, 210, 255, 235))
        draw.ellipse((sx - r, sy - r, sx + r, sy + r), fill=(150, 210, 255, 235), outline=INK,
                     width=round(5 * k))
        draw.line((sx - r * 0.95, sy - r * 0.3, sx, sy - r * 2.2, sx + r * 0.95, sy - r * 0.3),
                  fill=INK, width=round(5 * k))
        draw.ellipse((sx - r * 0.5, sy - r * 0.5, sx - r * 0.1, sy - r * 0.05), fill=(255, 255, 255, 255))

    head.alpha_composite(over)
    return head


def expression(t):
    """Everything about Terry at time t: face, squash, tilt and pose."""
    e = {"eyes": "happy", "mouth": "smile", "mouth_size": 1.0, "blush": 0.45, "puff": 0.0,
         "sweat": None, "look": (0, 0), "pupil": (0, 0), "lid": 0.0, "crumb": t < BURP,
         "brows": None, "tears": 0.0,
         "sx": 1.06, "sy": 1.0, "tilt": 0.0, "hop": 0.0, "pose": [("pat", 1.0)], "kick": 1.0}
    breathe = math.sin(t * 2.2)
    e["sx"] += 0.025 * breathe
    e["sy"] -= 0.02 * breathe

    if t < 2.9:
        # Content, patting the belly, a happy little sway.
        e["tilt"] = 3 * math.sin(t * 1.6)
        if 1.6 < t < 2.9:
            e["mouth"] = "grin"
    elif t < BURP:
        # Hic... hic: eyes pop, cheeks fill.
        e["eyes"] = "wide"
        e["brows"] = "raised"
        e["mouth"] = "puff"
        u = ramp(t, 2.9, BURP - 0.05)
        e["puff"] = u
        e["sx"] += 0.1 * u
        e["sy"] -= 0.05 * u
        for hic in HICS:
            if hic <= t < hic + 0.22:
                e["hop"] = 16 * math.sin(math.pi * (t - hic) / 0.22)
        e["pupil"] = (0, -6 if t < 3.3 else 4)
        e["pose"] = [("pat", 1 - u), ("rest", u)]
        e["kick"] = 0.0
    elif t < OOPS[0]:
        # BURP: stretch tall, head thrown back, mouth wide.
        u = (t - BURP) / (OOPS[0] - BURP)
        punch = math.exp(-u * 3.2)
        e["eyes"] = "squint"
        e["mouth"] = "O"
        e["mouth_size"] = 1.5 + 0.25 * math.sin(t * 40) * punch
        e["blush"] = 0.2
        e["sx"] = 1.06 - 0.1 * punch + 0.03 * math.sin(t * 34) * punch
        e["sy"] = 1.0 + 0.14 * punch
        e["tilt"] = -10 * ease(u * 4) + 4 * u
        e["look"] = (0, -16)
        e["pose"] = [("jolt", 1.0)]
        e["hop"] = 10 * punch
        e["kick"] = 0.0
    elif t < OOPS[1]:
        # Oops. Hand over the mouth, blushing, sweating.
        u = ramp(t, OOPS[0], OOPS[0] + 0.3)
        e["eyes"] = "squint" if t < 5.9 else "open"
        e["brows"] = "worried"
        e["mouth"] = "wobble"
        e["blush"] = 0.45 + 0.55 * u
        e["sweat"] = clamp((t - 5.0) / 1.4)
        e["pose"] = [("jolt", 1 - u), ("mouth", u)]
        e["tilt"] = 4 * math.sin((t - OOPS[0]) * 9) * math.exp(-(t - OOPS[0]) * 2)
        e["look"] = (-14, 6) if t >= 5.9 else (0, 0)
        e["kick"] = 0.0
    elif t < 9.0:
        # The family are back and laughing: caught out, then laughing along.
        u = ramp(t, OOPS[1], OOPS[1] + 0.4)
        e["blush"] = 0.95
        e["look"] = (22, 0)
        e["pose"] = [("mouth", 1 - u), ("rest", u)]
        e["kick"] = 0.0
        if t < 7.6:
            e["eyes"] = "open"
            e["brows"] = "worried"
            e["mouth"] = "wobble"
        else:
            e["eyes"] = "happy"
            e["mouth"] = "grin"
            e["tilt"] = 3 * math.sin(t * 13)
            e["hop"] = 4 * abs(math.sin(t * 12))
            e["pose"] = [("rub", 1.0)]
    elif t < FULL_LINE:
        # "You finished ALL of it?" Proud as anything, rubbing his belly.
        e["eyes"] = "happy" if t < 10.4 else "sparkle"
        e["brows"] = "up" if t >= 10.4 else None
        e["mouth"] = "grin"
        e["blush"] = 0.6
        e["look"] = (14, 0)
        e["pose"] = [("rub", 1.0)]
        e["tilt"] = -3 + 2 * math.sin(t * 1.4)
    elif t < YAWN[0]:
        # Ahh. Leaning back, all smiles.
        e["eyes"] = "happy" if t < FULL_LINE + 1.4 else "sparkle"
        e["mouth"] = "grin" if t < FULL_LINE + 1.2 else "smile"
        e["blush"] = 0.55
        e["pose"] = [("rub", 1.0)]
        e["tilt"] = -4 * ramp(t, FULL_LINE, FULL_LINE + 0.4) + 2 * math.sin(t * 1.4)
    elif t < YAWN[1]:
        # A big yawn and a stretch.
        u = ramp(t, YAWN[0], YAWN[0] + 0.5)
        s = window(t, YAWN[0], 0.5, YAWN[1] - 0.2, 0.5)
        e["eyes"] = "closed"
        e["mouth"] = "yawn" if t < YAWN[1] - 0.4 else "smile"
        e["mouth_size"] = 0.6 + 0.8 * s
        e["sy"] += 0.1 * s
        e["sx"] -= 0.06 * s
        e["tilt"] = -6 * s
        e["pose"] = [("rub", 1 - u), ("stretch", s), ("rest", u * (1 - s))]
        e["kick"] = 0.0
    else:
        # Looking up at the sky in wonder.
        u = ramp(t, LOOK_UP, LOOK_UP + 0.8)
        e["eyes"] = "open" if t < LOOK_UP + 1.2 else "sparkle"
        e["brows"] = "up"
        e["mouth"] = "smile" if t < LOOK_UP + 1.2 else "grin"
        e["look"] = (0, -40 * u)
        e["tilt"] = -8 * u
        e["pose"] = [("rest", 1.0)]
        e["kick"] = 0.5
    return e


def hand_pose(name, t):
    """(left, right) hand centres relative to the head centre, in world units."""
    if name == "pat":
        return ((-82, 62 - 12 * max(0.0, math.sin(t * 8))),
                (82, 62 - 12 * max(0.0, math.sin(t * 8 + math.pi))))
    if name == "rub":
        a = t * 5
        return ((-46 + 14 * math.cos(a), 68 + 9 * math.sin(a)),
                (46 + 14 * math.cos(a + math.pi), 68 + 9 * math.sin(a + math.pi)))
    if name == "mouth":
        return ((-82, 62), (22 + 3 * math.sin(t * 20), 70))
    if name == "stretch":
        w = 6 * math.sin(t * 9)
        return ((-96 + w, -150), (96 - w, -150))
    if name == "jolt":
        return ((-128, 6 + 6 * math.sin(t * 30)), (128, 6 - 6 * math.sin(t * 30)))
    return ((-91, 57), (89, 57))   # rest


class Terry:
    def __init__(self):
        self.head, self.hand_l, self.hand_r, self.shoe_l, self.shoe_r = load_parts()
        self.head_w = (HEAD_BOX[2] - HEAD_BOX[0]) * ART_SCALE
        self.head_h = (HEAD_BOX[3] - HEAD_BOX[1]) * ART_SCALE

    def layout(self, t):
        """World positions this frame: head centre, size, tilt, hands, shoes, mouth."""
        e = expression(t)
        w, h = self.head_w * e["sx"], self.head_h * e["sy"]
        bottom = SEAT[1] + 10 - e["hop"]
        theta = math.radians(e["tilt"])
        cx = SEAT[0] - h / 2 * math.sin(theta)
        cy = bottom - h / 2 * math.cos(theta)
        hands_l, hands_r = (0.0, 0.0), (0.0, 0.0)
        total = sum(weight for _, weight in e["pose"]) or 1
        for name, weight in e["pose"]:
            hl, hr = hand_pose(name, t)
            hands_l = (hands_l[0] + hl[0] * weight / total, hands_l[1] + hl[1] * weight / total)
            hands_r = (hands_r[0] + hr[0] * weight / total, hands_r[1] + hr[1] * weight / total)
        kick = e["kick"]
        shoes = (
            (SEAT[0] - 38 + 4 * kick * math.sin(t * 6), SEAT[1] + 40 - 9 * kick * max(0, math.sin(t * 6))),
            (SEAT[0] + 40 + 4 * kick * math.sin(t * 6 + 2), SEAT[1] + 42 - 9 * kick * max(0, math.sin(t * 6 + 2))),
        )
        # The mouth, for the burp cloud to come out of.
        my = (682 - (HEAD_BOX[1] + HEAD_BOX[3]) / 2 + e["look"][1]) * ART_SCALE * e["sy"]
        mouth = (cx - my * math.sin(theta), cy + my * math.cos(theta))
        return {"e": e, "center": (cx, cy), "size": (w, h), "tilt": e["tilt"],
                "hands": ((cx + hands_l[0] * e["sx"], cy + hands_l[1]),
                          (cx + hands_r[0] * e["sx"], cy + hands_r[1])),
                "shoes": shoes, "mouth": mouth}

    def draw(self, frame, cam, pose):
        z = cam.zoom
        s = ART_SCALE * z
        shade = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        x, y = cam.screen(SEAT[0], SEAT[1] + 8)
        rx, ry = pose["size"][0] * 0.42 * z, 16 * z
        ImageDraw.Draw(shade).ellipse((x - rx, y - ry, x + rx, y + ry), fill=(0, 0, 0, 120))
        frame.alpha_composite(shade.filter(ImageFilter.GaussianBlur(6 * z)))
        for shoe, (x, y) in zip((self.shoe_l, self.shoe_r), pose["shoes"]):
            paste_center(frame, shoe, *cam.screen(x, y), scale=s)
        head = draw_face(self.head, pose["e"])
        w, h = pose["size"]
        head = head.resize((max(1, round(w * z)), max(1, round(h * z))), Image.LANCZOS)
        paste_center(frame, head, *cam.screen(*pose["center"]), angle=pose["tilt"])
        for hand, (x, y) in zip((self.hand_l, self.hand_r), pose["hands"]):
            paste_center(frame, hand, *cam.screen(x, y), scale=s)


# --- the camera ---------------------------------------------------------------

# Each of the family's faces: anchors as for Terry, and the boxes their drawn
# features are wiped from (brows, eyes, mouth), in source art pixels.
FAMILY_FACES = {
    "Marcus": {"eyes": ((405, 487), (612, 487)), "brows": ((378, 402), (632, 404)),
               "mouth": (518, 598), "wipe": ((325, 352, 432, 434), (563, 352, 702, 437),
                                             (350, 440, 462, 537), (553, 440, 672, 537),
                                             (412, 548, 628, 670))},
    "Christine": {"eyes": ((402, 498), (630, 498)), "brows": ((400, 414), (632, 418)),
                  "mouth": (518, 612), "wipe": ((343, 390, 460, 438), (573, 390, 694, 444),
                                                (336, 456, 470, 534), (563, 456, 704, 536),
                                                (436, 572, 600, 680))},
    # Jess's brows run into her fringe, so she keeps her own and none are drawn.
    "Jess": {"eyes": ((410, 497), (625, 497)), "brows": None,
             "mouth": (518, 602), "wipe": ((346, 391, 444, 434), (580, 388, 694, 437),
                                           (350, 456, 470, 530), (566, 456, 684, 530),
                                           (446, 560, 592, 645))},
    "Tom": {"eyes": ((408, 508), (628, 508)), "brows": ((397, 420), (632, 414)),
            "mouth": (520, 610), "wipe": ((336, 391, 460, 442), (570, 386, 694, 438),
                                          (336, 466, 462, 547), (576, 466, 702, 547),
                                          (438, 566, 602, 655))},
}


def wipe_features(piece, origin, boxes):
    """Paint the drawn-on face out of a head, leaving skin. Any blob that is
    clearly not skin and fits inside one of the boxes goes; the hair is far
    bigger than any box, so it stays."""
    rgba = numpy.array(piece).astype(int)
    ox, oy = origin
    h, w = rgba.shape[:2]
    cx, cy = w // 2, int(h * 0.62)
    centre = rgba[cy - 20:cy + 20, cx - 20:cx + 20, :3].reshape(-1, 3)
    skin = numpy.median(centre, axis=0)
    distance = numpy.abs(rgba[:, :, :3] - skin).sum(axis=2)
    odd = (distance > 45) & (rgba[:, :, 3] > 40)
    labels, count = ndimage.label(odd)
    keep = numpy.zeros(count + 1, bool)
    margin = 25
    for index, (ys, xs) in enumerate(ndimage.find_objects(labels), start=1):
        for x0, y0, x1, y1 in boxes:
            if (xs.start >= x0 - ox - margin and xs.stop <= x1 - ox + margin
                    and ys.start >= y0 - oy - margin and ys.stop <= y1 - oy + margin):
                keep[index] = True
                break
    wipe = ndimage.binary_dilation(keep[labels], iterations=5) & (rgba[:, :, 3] > 200)
    out = rgba.copy()
    out[wipe, :3] = skin
    image = Image.fromarray(out.astype("uint8"))
    # Soften the patched edges into the shading round them.
    soft = image.filter(ImageFilter.GaussianBlur(3))
    mask = Image.fromarray((ndimage.binary_dilation(wipe, iterations=3) * 255).astype("uint8"))
    image.paste(soft, (0, 0), mask.filter(ImageFilter.GaussianBlur(2)))
    image.putalpha(piece.getchannel("A"))
    return image, tuple(int(v) for v in skin) + (255,)


class Puppet:
    """One of the family, cut into head, hands and shoes from their art."""

    def __init__(self, art_file, scale, name=None):
        art = Image.open(CHARACTERS / art_file).convert("RGBA")
        alpha = numpy.array(art.getchannel("A"))
        labels, count = ndimage.label(alpha > 40)
        boxes = ndimage.find_objects(labels)
        sizes = ndimage.sum(alpha > 40, labels, range(1, count + 1))
        head = int(numpy.argmax(sizes))
        self.scale = scale
        self.parts = {}
        hands, shoes = [], []
        for index, box in enumerate(boxes):
            if sizes[index] < 200:
                continue
            ys, xs = box
            mask = Image.fromarray(((labels[box] == index + 1) * 255).astype("uint8"))
            piece = art.crop((xs.start, ys.start, xs.stop, ys.stop))
            piece.putalpha(ImageChops.multiply(piece.getchannel("A"), mask))
            centre = ((xs.start + xs.stop) / 2, (ys.start + ys.stop) / 2)
            if index == head:
                self.parts["head"] = (piece, centre)
            elif centre[1] > 820:
                shoes.append((piece, centre))
            else:
                hands.append((piece, centre))
        hands.sort(key=lambda part: part[1][0])
        shoes.sort(key=lambda part: part[1][0])
        self.parts["hand_l"], self.parts["hand_r"] = hands
        self.parts["shoe_l"], self.parts["shoe_r"] = shoes
        self.ground = max(c[1] + p.height / 2 for p, c in shoes)
        self.mid = self.parts["head"][1][0]
        head_piece, head_centre = self.parts["head"]
        self.head_top = (head_centre[1] - head_piece.height / 2)
        origin = (round(head_centre[0] - head_piece.width / 2),
                  round(head_centre[1] - head_piece.height / 2))
        self.face = None
        if name in FAMILY_FACES:
            anchors = FAMILY_FACES[name]
            blank, skin = wipe_features(head_piece, origin, anchors["wipe"])
            (lx, ly), (rx, ry) = anchors["eyes"]
            self.face = {"origin": origin, "size": 1.25, "skin": skin,
                         "eyes": anchors["eyes"], "brows": anchors["brows"],
                         "mouth": anchors["mouth"],
                         "cheeks": ((lx - 30, ly + 80), (rx + 30, ry + 80))}
            self.blank = blank.resize((round(blank.width * FACE_RES), round(blank.height * FACE_RES)),
                                      Image.LANCZOS)

    def height(self):
        return (self.ground - self.head_top) * self.scale

    def draw(self, frame, cam, x, ground, pose):
        """`pose`: hop, tilt, squash, and per-part (dx, dy) in art pixels."""
        k = self.scale
        z = cam.zoom

        def place(name, offset=(0, 0)):
            piece, (cx, cy) = self.parts[name]
            wx = x + (cx - self.mid + offset[0]) * k
            wy = ground - pose["hop"] + (cy - self.ground + offset[1]) * k
            return piece, wx, wy

        for name in ("shoe_l", "shoe_r"):
            piece, wx, wy = place(name, pose[name])
            paste_center(frame, piece, *cam.screen(wx, wy + pose["hop"]), scale=k * z)
        piece, wx, wy = place("head")
        sx, sy = pose["squash"]
        if self.face is not None and pose.get("face") is not None:
            piece_face = draw_face(self.blank, pose["face"], self.face)
        else:
            piece_face = piece
        head = piece_face.resize((max(1, round(piece.width * k * z * sx)),
                             max(1, round(piece.height * k * z * sy))), Image.LANCZOS)
        bottom = wy + piece.height / 2 * k
        paste_center(frame, head, *cam.screen(wx, bottom - piece.height / 2 * k * sy),
                     angle=pose["tilt"])
        for name in ("hand_l", "hand_r"):
            piece, wx, wy = place(name, pose[name])
            paste_center(frame, piece, *cam.screen(wx, wy), scale=k * z)
        return cam.screen(x, ground - pose["hop"] - self.height())


FAMILY_GROUND = SKY_H + 418   # the lawn behind the table; the table hides their feet
# (name, art, scale, enters from x, stops at x, starts walking at, seconds walking)
FAMILY = (
    ("Jess", "jess.png", 0.205, -150, 515, 6.2, 2.2),
    ("Tom", "tom.png", 0.215, -330, 665, 6.35, 2.4),
    ("Christine", "Christine(mom).png", 0.235, 1430, 878, 6.3, 2.3),
    ("Marcus", "Marcus(dad).png", 0.245, 1600, 1040, 6.5, 2.4),
)
# When each of them is laughing, and when they jump with a "wow".
LAUGHS = {
    "Jess": ((7.3, 10.2), (FULL_LINE + 0.6, FULL_LINE + 1.8)),
    "Tom": ((7.1, 10.0), (FULL_LINE + 0.6, FULL_LINE + 1.8)),
}
KIDS = ("Jess", "Tom")
WOWS = {"Marcus": 9.35, "Christine": 9.5, "Jess": 10.5, "Tom": 10.6}
# What they say: (speaker, line, from, to).
FAMILY_LINES = (
    ("Tom", "HAHAHA! That burp!", 7.4, 8.6),
    ("Jess", "So LOUD!", 8.55, 9.4),
    ("Marcus", "WOW! You finished ALL of it?!", 9.35, 10.55),
    ("Christine", "Not a single crumb left!", 10.5, 11.8),
)
STEP_RATE = 7.0               # radians of the walk cycle per second; a step each half turn


def family_pose(member, t):
    """Where one of the family is and how they hold themselves at time t."""
    name, _, _, x0, x1, start, seconds = member
    p = clamp((t - start) / seconds)
    x = lerp(x0, x1, 1 - (1 - p) ** 2)
    walking = 0 < p < 1
    pose = {"hop": 0.0, "tilt": 0.0, "squash": (1.0, 1.0),
            "hand_l": (0, 0), "hand_r": (0, 0), "shoe_l": (0, 0), "shoe_r": (0, 0)}
    breathe = math.sin(t * 2.0 + x0)
    pose["squash"] = (1 + 0.015 * breathe, 1 - 0.015 * breathe)
    if walking:
        phase = (t - start) * STEP_RATE
        direction = 1 if x1 > x0 else -1
        pose["hop"] = 7 * abs(math.sin(phase))
        pose["tilt"] = -4 * direction
        lift = 26
        pose["shoe_l"] = (direction * 22 * math.sin(phase), -lift * max(0.0, math.sin(phase)))
        pose["shoe_r"] = (-direction * 22 * math.sin(phase), -lift * max(0.0, -math.sin(phase)))
        pose["hand_l"] = (0, 30 * math.sin(phase))
        pose["hand_r"] = (0, -30 * math.sin(phase))
    for a, b in LAUGHS.get(name, ()):
        if a <= t <= b:
            level = window(t, a, 0.15, b, 0.2)
            pose["tilt"] = 7 * math.sin(t * 15) * level
            pose["hop"] += 6 * abs(math.sin(t * 13)) * level
            pose["squash"] = (1 + 0.04 * abs(math.sin(t * 13)) * level,
                              1 - 0.04 * abs(math.sin(t * 13)) * level)
            # Hands to the belly, holding it while they laugh.
            pose["hand_l"] = (150 * level, -40 * level + 14 * math.sin(t * 13))
            pose["hand_r"] = (-150 * level, -40 * level - 14 * math.sin(t * 13))
    wow = WOWS.get(name)
    if wow is not None and wow <= t <= wow + 0.9:
        u = (t - wow) / 0.9
        pose["hop"] += 34 * math.sin(math.pi * clamp(u * 1.6))
        up = math.sin(math.pi * u)
        pose["hand_l"] = (-40 * up, -330 * up)
        pose["hand_r"] = (40 * up, -330 * up)
        pose["squash"] = (1 - 0.05 * up, 1 + 0.06 * up)
    # The parents give a fond little nod at "I'm SO full".
    if name not in KIDS and FULL_LINE + 0.7 <= t <= FULL_LINE + 1.9:
        pose["tilt"] += 4 * math.sin((t - FULL_LINE - 0.7) * 8) * window(t, FULL_LINE + 0.7, 0.2, FULL_LINE + 1.9, 0.3)
    # Everyone gazes upward with Terry at the end: a little lean back.
    if t > LOOK_UP:
        pose["tilt"] += -3 * ramp(t, LOOK_UP, LOOK_UP + 0.8)
    pose["face"] = family_face(name, t)
    return x, pose


def family_face(name, t):
    """What each of the family's faces is doing at time t."""
    kid = name in KIDS
    wow = WOWS[name]
    if t >= LOOK_UP:
        u = ramp(t, LOOK_UP, LOOK_UP + 0.8)
        return neutral_face(eyes="sparkle" if t > LOOK_UP + 1.0 else "open", mouth="smile",
                            brows="up", look=(0, -40 * u))
    if wow <= t < wow + 1.1:
        # WOW: eyes like saucers, jaw dropped.
        return neutral_face(eyes="wide", mouth="O", mouth_size=1.3 if kid else 1.5, brows="raised",
                            look=(-18, 10), blush=0.2)
    if kid:
        for a, b in LAUGHS[name]:
            if a - 0.4 <= t <= b:
                bounce = abs(math.sin(t * 13))
                big = a == LAUGHS[name][0][0]
                return neutral_face(eyes="happy", mouth="laugh" if big else "grin",
                                    mouth_size=0.8 + 0.35 * bounce, blush=0.5 if big else 0.3,
                                    tears=ramp(t, a + 0.8, a + 1.6) if big else 0.0,
                                    brows="up" if big else None)
        if t > wow:
            return neutral_face(eyes="sparkle", mouth="grin", blush=0.3, look=(-14, 0))
        return neutral_face(eyes="happy", mouth="grin", blush=0.2)
    # The parents: walking in pleased, then the burp and the empty table
    # register, the WOW, then proud of him.
    if t < 7.9:
        return neutral_face(eyes="open" if name == "Marcus" else "happy", mouth="smile")
    if t < wow:
        return neutral_face(eyes="open", mouth="O", mouth_size=0.55, brows="raised",
                            look=(-24, 18), pupil=(-8, 6))
    if name == "Christine" and 10.45 <= t < FULL_LINE:
        return neutral_face(eyes="happy", mouth="grin", blush=0.45, brows="up")
    if t < FULL_LINE + 0.6:
        return neutral_face(eyes="happy", mouth="grin", blush=0.3, look=(-14, 0))
    if t < FULL_LINE + 2.0:
        # A fond, closed-eyed smile at "I'm SO full".
        return neutral_face(eyes="happy", mouth="smile", blush=0.35, brows="relaxed")
    return neutral_face(eyes="open" if name == "Marcus" else "happy", mouth="smile", blush=0.2)


def table_mask():
    """The table and everything on it, in world units: what hides the family's feet."""
    mask = Image.new("L", (W, SKY_H + TABLE_H), 0)
    outline = [(300, 715), (318, 600), (405, 445), (436, 392), (446, 372), (600, 372),
               (640, 386), (800, 384), (1000, 380), (1120, 362), (1210, 356), (1280, 366),
               (1280, 715)]
    ImageDraw.Draw(mask).polygon([(x, SKY_H + y) for x, y in outline], fill=255)
    return mask.filter(ImageFilter.GaussianBlur(1.2))


def bubble_image(text, face, tail=True):
    box = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=face)
    bw, bh = box[2] + 44, box[3] + 34
    image = Image.new("RGBA", (bw + 6, bh + 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((3, 3, bw, bh), 22, fill=(252, 248, 238, 245),
                           outline=(40, 30, 40, 255), width=4)
    if tail:
        mid = bw / 2
        draw.polygon(((mid - 16, bh - 2), (mid + 16, bh - 2), (mid - 4, bh + 28)),
                     fill=(252, 248, 238, 245))
        draw.line(((mid - 16, bh), (mid - 4, bh + 28), (mid + 16, bh)),
                  fill=(40, 30, 40, 255), width=4)
    draw.text((25 - box[0] + 2, 18 - box[1] + 4), text, font=face, fill=(40, 30, 40, 255))
    return image


class Camera:
    def __init__(self, cx, cy, zoom):
        self.zoom = zoom
        half_w, half_h = W / 2 / zoom, H / 2 / zoom
        world_h = SKY_H + TABLE_H
        self.cx = clamp(cx, half_w, W - half_w)
        self.cy = clamp(cy, half_h, world_h - half_h)
        self.x0 = self.cx - half_w
        self.y0 = self.cy - half_h

    def screen(self, x, y):
        return (x - self.x0) * self.zoom, (y - self.y0) * self.zoom

    def view(self, world):
        z = self.zoom
        return world.transform((W, H), Image.AFFINE, (1 / z, 0, self.x0, 0, 1 / z, self.y0),
                               Image.BILINEAR)


CLOSE = (420, SKY_H + 520, 1.75)
WIDE = (W / 2, SKY_H + TABLE_H - H / 2, 1.0)
SKY = (W / 2, H / 2, 1.0)


def camera_at(t, shake):
    if t < PULL_OUT[0]:
        cx, cy, z = CLOSE
        # A slow push in while he is enjoying himself.
        z += 0.08 * ramp(t, 0, PULL_OUT[0])
    elif t < PULL_OUT[1]:
        k = ramp(t, *PULL_OUT)
        cx, cy, z = (lerp(CLOSE[0], WIDE[0], k), lerp(CLOSE[1], WIDE[1], k),
                     lerp(CLOSE[2] + 0.08, WIDE[2], k))
    else:
        k = ramp(t, *TILT)
        cx, cy, z = WIDE[0], lerp(WIDE[1], SKY[1], k), 1.0
    return Camera(cx + shake[0], cy + shake[1], z)


def shake_at(t):
    if not BURP <= t <= OOPS[0]:
        return (0.0, 0.0)
    amp = 9 * math.exp(-(t - BURP) * 3.5)
    return (amp * math.sin(t * 71), amp * math.cos(t * 53))


# --- effects ------------------------------------------------------------------

def burp_clouds(seed=11):
    rng = random.Random(seed)
    return [(BURP + 0.05 + i * 0.045, rng.uniform(40, 150), rng.uniform(-150, -40),
             rng.uniform(0.9, 1.6), rng.uniform(0.8, 1.3)) for i in range(18)]


def crumbs(seed=5):
    rng = random.Random(seed)
    out = []
    for _ in range(40):
        out.append((rng.uniform(380, 760), SKY_H + rng.uniform(470, 600),
                    rng.uniform(-140, 140), rng.uniform(-420, -200),
                    rng.choice(((150, 96, 52), (214, 182, 120), (90, 150, 60), (230, 220, 200))),
                    rng.uniform(3, 7)))
    return out


def fireflies(seed=21):
    rng = random.Random(seed)
    out = []
    for i in range(70):
        rising = i >= 18
        out.append({
            "x": rng.uniform(20, W - 20),
            "y": SKY_H + rng.uniform(140, 470),
            "start": rng.uniform(TILT[0] - 1.5, TILT[0] + 3.0) if rising else -1.0,
            "speed": rng.uniform(40, 95),
            "phase": rng.uniform(0, math.tau),
            "sway": rng.uniform(10, 30),
            "rising": rising,
        })
    return out


def firefly_pos(f, t):
    sway = f["sway"] * math.sin(t * 1.3 + f["phase"])
    if not f["rising"] or t < f["start"]:
        return (f["x"] + sway, f["y"] + 14 * math.sin(t * 0.9 + f["phase"] * 2))
    up = f["speed"] * (t - f["start"]) * (1 + 0.25 * (t - f["start"]))
    return (f["x"] + sway, f["y"] - up)


# The family drawn in stars, left to right: (head radius, hair). They are
# drawn the way they look: round heads, hands floating beside them, two shoes
# underneath; neighbours' hands meet, so they are holding hands.
SKY_FAMILY = ((72, "dad"), (68, "mom"), (66, "terry"), (56, "tom"), (56, "jess"))
SKY_FEET = 468
HAND_REACH = 1.42             # hand distance from the head centre, in head radii
LOGO_CENTER = (W / 2, H / 2 - 10)


def circle(x, y, r, start=-90, end=270, count=32):
    return [(x + r * math.cos(math.radians(a)), y + r * math.sin(math.radians(a)))
            for a in numpy.linspace(start, end, count)]


def sky_family():
    """Constellation strokes as (points, delay), the stars on them, and the joined hands."""
    xs, x = [], 0.0
    for i, (r, _) in enumerate(SKY_FAMILY):
        if i:
            x += (SKY_FAMILY[i - 1][0] + r) * HAND_REACH
        xs.append(x)
    shift = W / 2 - (xs[0] + xs[-1]) / 2
    xs = [x + shift for x in xs]

    figures = []
    for (r, hair), x in zip(SKY_FAMILY, xs):
        cy = SKY_FEET - r * 0.45 - r
        figures.append((x, cy, r, hair))
    # Hands: each pair of neighbours shares one, halfway between them.
    hands = []
    for i, (x, cy, r, _) in enumerate(figures):
        hands.append(((x - r * HAND_REACH, cy + r * 0.55), (x + r * HAND_REACH, cy + r * 0.55)))
    joined = []
    for i in range(len(figures) - 1):
        a, b = hands[i][1], hands[i + 1][0]
        joined.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))

    strokes, stars = [], []
    for i, (x, cy, r, hair) in enumerate(figures):
        d = i * 0.34
        ring = circle(x, cy, r, count=40)
        strokes.append((ring, d))
        stars += ring[::5]
        if hair == "terry":
            spikes = []
            for k, a in enumerate(numpy.linspace(200, 340, 9)):
                rr = r * (1.32 if k % 2 else 1.0)
                spikes.append((x + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a))))
            strokes.append((spikes, d + 0.6))
            stars += spikes[1::2]
        elif hair == "jess":
            strokes.append((circle(x, cy, r * 1.08, 195, 345, 16), d + 0.6))
            for a in (200, 340):
                px = x + r * 1.25 * math.cos(math.radians(a))
                py = cy + r * 1.25 * math.sin(math.radians(a))
                tail = circle(px, py, r * 0.3, count=14)
                strokes.append((tail, d + 0.75))
                stars.append((px, py - r * 0.3))
        elif hair == "mom":
            strokes.append((circle(x, cy, r * 1.08, 185, 355, 16), d + 0.6))
            px = x + r * 1.15 * math.cos(math.radians(215))
            py = cy + r * 1.15 * math.sin(math.radians(215))
            strokes.append((circle(px, py, r * 0.28, count=14), d + 0.75))
            stars.append((px, py))
        elif hair == "tom":
            arc = circle(x, cy, r * 1.08, 190, 350, 16)
            tufts = [arc[6], (x - r * 0.15, cy - r * 1.42), arc[8], (x + r * 0.2, cy - r * 1.38), arc[10]]
            strokes.append((arc, d + 0.6))
            strokes.append((tufts, d + 0.8))
            stars += [tufts[1], tufts[3]]
        else:
            strokes.append((circle(x, cy, r * 1.1, 190, 350, 16), d + 0.6))
            stars.append((x, cy - r * 1.1))
        # Shoes: two little domes on the ground line.
        for side in (-1, 1):
            sx = x + side * r * 0.42
            dome = [(sx + r * 0.24 * math.cos(math.radians(a)),
                     SKY_FEET + r * 0.16 * math.sin(math.radians(a)))
                    for a in numpy.linspace(180, 360, 10)]
            dome.append(dome[0])
            strokes.append((dome, d + 0.9))
            stars.append((sx, SKY_FEET - r * 0.08))
    # Floating hands: the two outside ones, and the ones held between them.
    outer = [hands[0][0], hands[-1][1]]
    for i, (hx, hy) in enumerate(outer + joined):
        hr = 13 if i >= 2 else 11
        strokes.append((circle(hx, hy, hr, count=14), 1.2 + i * 0.15))
        stars.append((hx, hy))
    return strokes, stars, joined


def polyline_part(points, k):
    """The first k (0..1) of a polyline, by length."""
    if k <= 0:
        return []
    seg = [math.dist(a, b) for a, b in zip(points, points[1:])]
    total = sum(seg) * k
    out = [points[0]]
    for (a, b), d in zip(zip(points, points[1:]), seg):
        if total >= d:
            out.append(b)
            total -= d
        else:
            out.append(lerp2(a, b, total / d if d else 0))
            break
    return out


class Glow:
    """A quarter resolution light layer, blurred and added over the frame."""

    def __init__(self):
        self.image = Image.new("RGB", (W // 4, H // 4))
        self.draw = ImageDraw.Draw(self.image)
        self.used = False
        # Big soft lights go on their own layer, blurred far wider.
        self.halo = Image.new("RGB", (W // 8, H // 8))
        self.halo_used = False

    def soft(self, x, y, r, color, alpha=1.0):
        if alpha <= 0:
            return
        self.halo_used = True
        c = tuple(round(v * alpha) for v in color)
        x, y, r = x / 8, y / 8, r / 8
        # Added, not painted over, so overlapping lights build up.
        layer = Image.new("RGB", self.halo.size)
        ImageDraw.Draw(layer).ellipse((x - r, y - r, x + r, y + r), fill=c)
        self.halo = ImageChops.add(self.halo, layer)

    def dot(self, x, y, r, color, alpha=1.0):
        if alpha <= 0:
            return
        self.used = True
        c = tuple(round(v * alpha) for v in color)
        x, y, r = x / 4, y / 4, r / 4
        self.draw.ellipse((x - r, y - r, x + r, y + r), fill=c)

    def apply(self, frame, blur=3):
        if not self.used and not self.halo_used:
            return frame
        light = self.image.filter(ImageFilter.GaussianBlur(blur)).resize((W, H), Image.BILINEAR)
        if self.halo_used:
            halo = self.halo.filter(ImageFilter.GaussianBlur(self.halo.width / 16))
            light = ImageChops.add(light, halo.resize((W, H), Image.BICUBIC))
        rgb = ImageChops.add(frame.convert("RGB"), light)
        rgb.putalpha(255)
        return rgb


# --- sound --------------------------------------------------------------------

_CLIPS = {}


def decode(path):
    """Any audio file as mono float samples at RATE."""
    container = av.open(str(path))
    resampler = av.AudioResampler(format="flt", layout="mono", rate=RATE)
    chunks = []
    for frame in container.decode(audio=0):
        for out in resampler.resample(frame):
            chunks.append(out.to_ndarray().reshape(-1))
    for out in resampler.resample(None):
        chunks.append(out.to_ndarray().reshape(-1))
    container.close()
    return numpy.concatenate(chunks).astype("float64")


def clip(name, start=0.0, end=None, speed=1.0):
    """A recording from SFX_DIR (or a path), cut, sped up or slowed, peak 1."""
    path = name if isinstance(name, Path) else SFX_DIR / f"{name}.mp3"
    if path not in _CLIPS:
        _CLIPS[path] = decode(path)
    x = _CLIPS[path][int(start * RATE): None if end is None else int(end * RATE)]
    if speed != 1.0:
        x = numpy.interp(numpy.arange(0, len(x) - 1, speed), numpy.arange(len(x)), x)
    fade = min(len(x) // 4, int(0.008 * RATE))
    if fade:
        x = x.copy()
        x[:fade] *= numpy.linspace(0, 1, fade)
        x[-fade:] *= numpy.linspace(1, 0, fade)
    peak = numpy.abs(x).max()
    return x / peak if peak else x


def build_sound():
    """The effects track, timed to the picture, peaking at 0.9."""
    track = numpy.zeros(int((LENGTH + 2) * RATE))

    def add(at, samples, gain=1.0):
        i = int(at * RATE)
        if i >= len(track):
            return
        samples = samples[: len(track) - i]
        track[i:i + len(samples)] += samples * gain

    # Belly pats: the hands come down every 0.39 s or so.
    slaps = (clip("tummy", 1.78, 2.15), clip("tummy", 3.40, 3.76), clip("tummy", 5.03, 5.40))
    for k in range(1, 8):
        at = k * math.pi / 8
        if at < 2.85:
            add(at - 0.02, slaps[k % 3], 0.32)
    add(HICS[0] - 0.06, clip("hiccup_a"), 0.55)
    add(HICS[1] - 0.06, clip("hiccup_a", speed=1.08), 0.5)
    add(BURP - 0.12, clip("burp_b"), 1.0)
    add(BURP + 0.08, clip("boing", 0.1, 1.0), 0.16)
    add(5.02, clip("drop"), 0.3)

    # The family walking in over the grass, then laughing and amazed.
    step = clip(STEP_CLIP)
    step = step[: int(0.35 * RATE)]
    for member in FAMILY:
        _, _, _, _, _, start, seconds = member
        n = int(seconds * STEP_RATE / math.pi)
        for k in range(n):
            add(start + (k + 0.5) * math.pi / STEP_RATE, step, 0.16)
    add(7.15, clip("kids_laugh"), 0.55)
    add(7.6, clip("kids_laugh_b", 0.0, 2.6), 0.32)
    add(9.0, clip("group_wow", 0.1, 2.4), 0.7)
    add(10.25, clip("kids_wow", 0.0, 0.8), 0.45)
    add(10.6, clip("pop"), 0.25)
    add(FULL_LINE, clip("pop"), 0.3)
    add(FULL_LINE + 0.65, clip("kids_laugh_b", 3.4, 5.4), 0.32)
    add(FULL_LINE + 1.35, clip("wink"), 0.5)
    add(FULL_LINE + 1.5, clip("achieve"), 0.35)
    add(YAWN[0], clip("yawn_b", 0.15, 1.3), 0.6)
    add(LOOK_UP + 1.1, clip("twinkle", 0.1, 2.5), 0.35)

    # Up into the sky, the family in the stars, and the title.
    add(TILT[0] + 0.1, clip("whoosh", 0.2, 1.0, speed=0.55), 0.45)
    add(TILT[0] + 1.4, clip("twinkle_b"), 0.3)
    add(SHOOTING[0][0] - 0.05, clip("shooting", 0.0, 1.1), 0.4)
    add(FAMILY_START, clip("flourish", 0.0, 5.3), 0.45)
    add(CONVERGE[0] + 0.2, clip("shimmer", 0.0, 0.7), 0.55)
    add(LOGO_POP - 1.3, clip("gleam", 0.0, 3.6), 0.85)
    add(LOGO_POP + 0.05, clip("achieve"), 0.4)
    add(SHOOTING[1][0] - 0.05, clip("shooting", 0.0, 1.1), 0.25)
    add(LOGO_POP + 2.2, clip("twinkle", 0.1, 2.5), 0.22)

    track = track[: int(LENGTH * RATE)]
    peak = numpy.abs(track).max()
    return (track / peak * 0.9 if peak else track).astype("float32")


def with_bed(sound):
    """The effects over the night ambience, for the mp4's own sound track."""
    bed = clip(NIGHT_BED)
    reps = int(math.ceil(len(sound) / len(bed)))
    bed = numpy.tile(bed, reps)[: len(sound)]
    t = numpy.arange(len(sound)) / RATE
    bed *= numpy.clip(t / 1.5, 0, 1) * numpy.clip((LENGTH - t) / 2.0, 0, 1) * 0.22
    mix = sound + bed
    peak = numpy.abs(mix).max()
    return (mix / peak * 0.92 if peak > 0.92 else mix).astype("float32")


def write_wav(path, samples):
    data = (numpy.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(data)


# --- the frames ---------------------------------------------------------------

def render(times=None):
    """Yield the frames, or with `times` only the frames at those seconds."""
    world = build_world()
    mask = table_mask()
    stars = make_stars()
    terry = Terry()
    family = [(member, Puppet(member[1], member[2], member[0])) for member in FAMILY]
    clouds = burp_clouds()
    bits = crumbs()
    flies = fireflies()
    strokes, joints, held = sky_family()
    logo = Image.open(LOGO).convert("RGBA")
    logo = logo.resize((760, round(logo.height * 760 / logo.width)), Image.LANCZOS)

    comic = font("comicbd.ttf", 92)
    burp_letters = [text_image(c, comic, (255, 214, 92), stroke=7, stroke_fill=(70, 30, 20), shadow=4)
                    for c in "BUUURP!"]
    hic = text_image("hic!", font("comicbd.ttf", 38), (255, 255, 255), stroke=4,
                     stroke_fill=(40, 30, 40))
    excuse = text_image("...excuse me.", font("comici.ttf", 34), (255, 236, 220), stroke=3,
                        stroke_fill=(40, 30, 40))
    has = [text_image(word, font("comicbd.ttf", 30), (255, 250, 240), stroke=4, stroke_fill=(40, 30, 40))
           for word in ("HA!", "HAHA!", "hehe")]
    bubble_face = font("comicbd.ttf", 30)
    lines = [(who, bubble_image(text, bubble_face), a, b) for who, text, a, b in FAMILY_LINES]
    words = "Ahh... I'm SO full."
    terry_face = font("comicbd.ttf", 34)

    rng = random.Random(1)
    sparkles = [(rng.uniform(-430, 430), rng.uniform(-250, 250), rng.uniform(0, math.tau),
                 rng.uniform(5, 13)) for _ in range(26)]
    burst = [(rng.uniform(0, math.tau), rng.uniform(220, 620), rng.uniform(6, 16)) for _ in range(46)]

    if times is None:
        times = [index / FPS for index in range(round(LENGTH * FPS))]
    for t in times:
        cam = camera_at(t, shake_at(t))
        base = cam.view(world).convert("RGBA")
        frame = base.copy()
        glow = Glow()
        draw = ImageDraw.Draw(frame)

        # Stars: brighter and more of them as the camera reaches the sky.
        reveal = 0.35 + 0.65 * ramp(t, TILT[0] - 1, TILT[1])
        converge = ramp(t, *CONVERGE)
        for x, y, size, phase, speed, rank in stars:
            if rank > reveal:
                continue
            sx, sy = cam.screen(x, y)
            if not -6 <= sy <= H + 6:
                continue
            level = 0.55 + 0.45 * math.sin(phase + t * speed)
            if t > FAMILY_START:
                level *= 1 - 0.5 * ramp(t, FAMILY_START, FAMILY_DRAWN) * (1 - converge)
            shade = round(130 + 125 * level)
            color = (shade, shade, min(255, shade + 25), 255)
            if size == 3:
                draw.line((sx - 4, sy, sx + 4, sy), fill=color)
                draw.line((sx, sy - 4, sx, sy + 4), fill=color)
            draw.rectangle((sx - size / 2, sy - size / 2, sx + size / 2, sy + size / 2), fill=color)

        for start, a, b in SHOOTING:
            p = (t - start) / 0.75
            if 0 <= p <= 1:
                hx, hy = cam.screen(*lerp2(a, b, p))
                tx, ty = cam.screen(*lerp2(a, b, max(0, p - 0.25)))
                fade = math.sin(math.pi * p)
                draw.line((tx, ty, hx, hy), fill=(255, 255, 255, round(200 * fade)), width=2)
                glow.dot(hx, hy, 16, (200, 210, 255), fade)

        # The lantern, flickering hard when the burp rattles the table.
        lx, ly = cam.screen(1165, SKY_H + 488)
        flicker = 0.7 + 0.15 * math.sin(t * 13) + 0.1 * math.sin(t * 29)
        if BURP <= t <= OOPS[0]:
            flicker *= 0.4 + 0.6 * abs(math.sin(t * 47))
        glow.soft(lx, ly, 90 * cam.zoom, (150, 100, 30), flicker)

        # The family, behind the table: drawn, then the table put back over
        # their feet.
        tops = {}
        if 6.0 <= t <= TILT[0] + 3.5:
            for member, puppet in family:
                x, pose = family_pose(member, t)
                sx, _ = cam.screen(x, FAMILY_GROUND)
                if -200 <= sx <= W + 200:
                    tops[member[0]] = puppet.draw(frame, cam, x, FAMILY_GROUND, pose)
            view = mask.transform((W, H), Image.AFFINE,
                                  (1 / cam.zoom, 0, cam.x0, 0, 1 / cam.zoom, cam.y0),
                                  Image.BILINEAR)
            frame.paste(base, (0, 0), view)
            draw = ImageDraw.Draw(frame)

        # Fireflies: a few drift by the bushes all along, then a swarm rises.
        for f in flies:
            if f["rising"] and t < f["start"]:
                continue
            x, y = firefly_pos(f, t)
            sx, sy = cam.screen(x, y)
            if not -20 <= sy <= H + 20 or not -20 <= sx <= W + 20:
                continue
            blink = 0.5 + 0.5 * math.sin(t * 3 + f["phase"])
            fade_in = clamp((t - f["start"]) / 0.6) if f["rising"] else 1.0
            fade_out = 1 - ramp(t, FAMILY_START - 1.0, FAMILY_START + 1.0)
            a = blink * fade_in * fade_out
            glow.dot(sx, sy, 9 * cam.zoom, (110, 150, 40), a * 0.8)
            r = 1.6 * cam.zoom
            draw.ellipse((sx - r, sy - r, sx + r, sy + r), fill=(240, 255, 170, round(255 * a)))

        # Terry, until the camera has left him behind.
        if t < TILT[0] + 3.0:
            pose = terry.layout(t)
            terry.draw(frame, cam, pose)
            draw = ImageDraw.Draw(frame)
            hx, hy = cam.screen(*pose["center"])
            head_top = hy - pose["size"][1] / 2 * cam.zoom

            # Crumbs jump off the plates at the burp.
            if BURP + 0.05 <= t <= BURP + 1.45:
                u = t - BURP - 0.05
                for x, y, vx, vy, color, size in bits:
                    px, py = cam.screen(x + vx * u, y + vy * u + 700 * u * u)
                    sz = size * 0.6 * cam.zoom
                    draw.rectangle((px - sz, py - sz, px + sz, py + sz), fill=(*color, 255))

            # The burp cloud.
            if BURP <= t <= BURP + 2.0:
                over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                od = ImageDraw.Draw(over)
                mx, my = pose["mouth"]
                for start, vx, vy, life, grow in clouds:
                    u = (t - start) / life
                    if not 0 <= u <= 1:
                        continue
                    age = t - start
                    px, py = cam.screen(mx + vx * age * 1.4, my + vy * age - 40 * age * age)
                    r = (10 + 46 * grow * ease(u * 1.5)) * cam.zoom
                    a = (1 - u) ** 1.5
                    for k, shade in ((1.0, 90), (0.75, 140), (0.45, 190)):
                        od.ellipse((px - r * k, py - r * k * 0.85, px + r * k, py + r * k * 0.85),
                                   fill=(200, 230, 160, round(shade * a)))
                frame.alpha_composite(over.filter(ImageFilter.GaussianBlur(3)))

            for at, ox in zip(HICS, (-1, 1)):
                a = window(t, at, 0.05, at + 0.5, 0.25)
                if a:
                    paste_center(frame, hic, hx + ox * 120, head_top - 10 - 60 * (t - at), a,
                                 scale=0.9 + 0.3 * back_out((t - at) / 0.2), angle=-ox * 12)

            for i, letter in enumerate(burp_letters):
                at = BURP + 0.07 + i * 0.05
                a = window(t, at, 0.04, BURP + 1.55, 0.35)
                if not a:
                    continue
                pop = back_out((t - at) / 0.28)
                wob = math.sin(t * 18 + i) * 8 * math.exp(-(t - at) * 2)
                lx = hx + 150 + i * 58
                ly = hy - 120 - 30 * math.sin(i / 6 * math.pi) + wob - 20 * (t - at)
                paste_center(frame, letter, lx, ly, a, scale=0.4 + 0.6 * pop, angle=10 - i * 4 + wob)

            a = window(t, 5.2, 0.3, OOPS[1], 0.3)
            if a:
                paste_center(frame, excuse, hx + 280, hy - 150, a)

            # "Ahh... I'm SO full.", typed on.
            a = window(t, FULL_LINE, 0.2, YAWN[0] - 0.2, 0.3)
            if a:
                shown = words[: max(1, int(len(words) * clamp((t - FULL_LINE - 0.1) / 1.0)))]
                box = ImageDraw.Draw(frame).textbbox((0, 0), words, font=terry_face)
                bw, bh = box[2] + 50, box[3] + 40
                bub = Image.new("RGBA", (bw + 6, bh + 34), (0, 0, 0, 0))
                bd = ImageDraw.Draw(bub)
                bd.rounded_rectangle((3, 3, bw, bh), 24, fill=(252, 248, 238, 245),
                                     outline=(40, 30, 40, 255), width=4)
                bd.polygon(((40, bh - 2), (74, bh - 2), (28, bh + 30)), fill=(252, 248, 238, 245))
                bd.line(((40, bh), (28, bh + 30), (74, bh)), fill=(40, 30, 40, 255), width=4)
                bd.text((28, 18), shown, font=terry_face, fill=(40, 30, 40, 255))
                pop = back_out((t - FULL_LINE) / 0.3)
                paste_center(frame, bub, hx + 110 + bw / 2, head_top - 40, a, scale=0.6 + 0.4 * pop)

            for i in range(4):
                at = FULL_LINE + 1.4 + i * 0.35
                u = (t - at) / 1.6
                if 0 <= u <= 1:
                    x = hx + (i - 1.5) * 50 + 14 * math.sin(t * 4 + i)
                    y = head_top - 10 - 140 * u
                    a = round(255 * math.sin(math.pi * u))
                    heart_shape(ImageDraw.Draw(frame), x, y, 16 + 4 * i % 3,
                                (255, 110, 140, a), (90, 30, 50, a))

            if LOOK_UP + 1.0 <= t <= TILT[0] + 1.5:
                sd = ImageDraw.Draw(frame)
                for i in range(5):
                    a = max(0.0, math.sin(t * 4 + i * 1.7)) * window(t, LOOK_UP + 1.0, 0.4, TILT[0] + 1.5, 0.6)
                    star_shape(sd, hx + math.cos(i * 1.3) * 140 * cam.zoom,
                               head_top - 30 - i * 14, 9, (255, 240, 180, round(255 * a)))

        # The family's laughter and lines, over everything in the garden.
        if tops:
            # Only the kids get the floating "HA!"s, every so often.
            for name, (a, b) in ((n, LAUGHS[n][0]) for n in ("Jess", "Tom")):
                if name not in tops:
                    continue
                x, y = tops[name]
                k = 0
                while a + k * 0.75 < b:
                    at = a + k * 0.75
                    u = (t - at) / 0.9
                    if 0 <= u <= 1:
                        side = -1 if k % 2 else 1
                        paste_center(frame, has[(k + len(name)) % 3], x + side * 70,
                                     y - 10 - 70 * u, math.sin(math.pi * u) ** 0.5,
                                     scale=0.8 + 0.2 * back_out(u * 3), angle=side * 10)
                    k += 1
            for name, at in WOWS.items():
                u = (t - at) / 0.7
                if name in tops and 0 <= u <= 1:
                    x, y = tops[name]
                    sd = ImageDraw.Draw(frame)
                    for i in range(7):
                        ang = i * math.tau / 7 - math.pi / 2
                        d = 30 + 50 * ease(u)
                        star_shape(sd, x + math.cos(ang) * d, y + 30 + math.sin(ang) * d,
                                   10 * (1 - u) + 3, (255, 236, 150, round(255 * (1 - u))))
            for who, image, a, b in lines:
                level = window(t, a, 0.15, b, 0.25)
                if level and who in tops:
                    x, y = tops[who]
                    x = clamp(x, image.width / 2 + 12, W - image.width / 2 - 12)
                    pop = back_out((t - a) / 0.3)
                    paste_center(frame, image, x, y - image.height / 2 - 6, level,
                                 scale=0.6 + 0.4 * pop)

        # The five of them in the stars, then everything pulled into the title.
        if FAMILY_START <= t <= CONVERGE[1] + 0.1:
            line_alpha = 1 - ramp(t, CONVERGE[0], CONVERGE[0] + 0.3)
            if line_alpha > 0:
                ld = ImageDraw.Draw(frame)
                for points, delay in strokes:
                    k = clamp((t - FAMILY_START - delay) / 0.8)
                    part = polyline_part([cam.screen(*q) for q in points], k)
                    if len(part) > 1:
                        ld.line(part, fill=(180, 210, 255, round(200 * line_alpha)), width=3,
                                joint="curve")
                        for q in part[::3]:
                            glow.dot(q[0], q[1], 10, (60, 80, 140), line_alpha * 0.5)
                # The held hands pulse once the hands are in.
                for i, (x, y) in enumerate(held):
                    pulse = clamp((t - FAMILY_START - 1.6 - i * 0.15) / 0.4)
                    if pulse > 0:
                        px, py = cam.screen(x, y)
                        glow.dot(px, py, 26 + 6 * math.sin(t * 5 + i), (150, 130, 90),
                                 pulse * line_alpha)
            jd = ImageDraw.Draw(frame)
            for i, (x, y) in enumerate(joints):
                appear = clamp((t - FAMILY_START - (i % 14) * 0.08) / 0.4)
                if appear <= 0:
                    continue
                # Swirl into the centre: in along a spiral, faster at the end.
                spin = 2.2 + 2.4 * (i % 7) / 7
                ang = math.atan2(y - LOGO_CENTER[1], x - LOGO_CENTER[0]) + spin * converge ** 1.5
                rad = math.dist((x, y), LOGO_CENTER) * (1 - converge ** 1.6)
                px, py = cam.screen(LOGO_CENTER[0] + rad * math.cos(ang),
                                    LOGO_CENTER[1] + rad * math.sin(ang))
                twinkle = 0.7 + 0.3 * math.sin(t * 6 + i)
                star_shape(jd, px, py, 5 + 3 * twinkle, (255, 250, 220, round(255 * appear)))
                glow.dot(px, py, 16, (150, 160, 220), appear * twinkle)

        # The title bursts out of the stars, floats, and fades.
        if t >= CONVERGE[1] - 0.2:
            flash = window(t, CONVERGE[1] - 0.15, 0.15, CONVERGE[1] + 0.9, 0.75)
            glow.soft(*LOGO_CENTER, 420 * flash, (255, 230, 170), flash * 0.45)
            level = window(t, LOGO_POP, 0.25, LOGO_OUT, 1.6)
            if level:
                pop = back_out((t - LOGO_POP) / 0.6)
                bob = 6 * math.sin((t - LOGO_POP) * 1.8)
                halo = 0.5 + 0.15 * math.sin(t * 2.4)
                glow.soft(LOGO_CENTER[0], LOGO_CENTER[1] + bob, 380, (70, 56, 30), level * halo)
                paste_center(frame, logo, LOGO_CENTER[0], LOGO_CENTER[1] + bob, level,
                             scale=(0.55 + 0.45 * pop) * (1 + 0.03 * ramp(t, LOGO_OUT - 1.6, LOGO_OUT)))
                sd = ImageDraw.Draw(frame)
                for x, y, phase, r in sparkles:
                    a = max(0.0, math.sin(t * 2.2 + phase)) ** 3 * level
                    star_shape(sd, LOGO_CENTER[0] + x, LOGO_CENTER[1] + y + bob, r,
                               (255, 244, 200, round(255 * a)))
            u = t - LOGO_POP
            if 0 <= u <= 1.8:
                sd = ImageDraw.Draw(frame)
                for ang, speed, r in burst:
                    d = speed * (1 - math.exp(-u * 2.5))
                    a = (1 - u / 1.8) ** 1.5
                    x = LOGO_CENTER[0] + math.cos(ang) * d
                    y = LOGO_CENTER[1] + math.sin(ang) * d + 30 * u * u
                    star_shape(sd, x, y, r * (1 - u / 2.2), (255, 236, 170, round(255 * a)))
                    glow.dot(x, y, r * 2, (120, 100, 50), a)

        frame = glow.apply(frame)

        dark = max(1 - t / 1.0, (t - LOGO_OUT - 0.2) / 1.4, 0)
        if dark > 0:
            frame = Image.blend(frame, Image.new("RGBA", (W, H), (0, 0, 0, 255)), min(1.0, dark))
        yield frame.convert("RGB")


def main():
    sound = build_sound()
    SFX_OUT.parent.mkdir(parents=True, exist_ok=True)
    write_wav(SFX_OUT, sound)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    container = av.open(str(OUT), "w")
    video = container.add_stream("libx264", rate=FPS)
    video.width, video.height = W, H
    video.pix_fmt = "yuv420p"
    video.options = {"crf": "19", "preset": "slow"}
    audio = container.add_stream("aac", rate=RATE)
    audio.layout = "mono"

    for frame in render():
        for packet in video.encode(av.VideoFrame.from_image(frame)):
            container.mux(packet)
    for packet in video.encode():
        container.mux(packet)

    mixed = with_bed(sound)
    step = 1024
    for i in range(0, len(mixed), step):
        chunk = mixed[i:i + step]
        if len(chunk) < step:
            chunk = numpy.pad(chunk, (0, step - len(chunk)))
        frame = av.AudioFrame.from_ndarray(chunk[None, :], format="fltp", layout="mono")
        frame.sample_rate = RATE
        frame.pts = i
        for packet in audio.encode(frame):
            container.mux(packet)
    for packet in audio.encode():
        container.mux(packet)
    container.close()
    print(f"wrote {OUT} and {SFX_OUT}")


if __name__ == "__main__":
    main()
