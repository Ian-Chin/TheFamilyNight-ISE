import functools

import PIL.Image
import PIL.ImageDraw
import PIL.ImageFilter

SCALE = 3
SIZE = (40, 62)            # every pose shares this canvas
FEET = (20, 60)            # where her feet meet the floor in it

INK = (24, 16, 30, 255)
HAIR = (182, 174, 206, 255)
HAIR_DARK = (146, 138, 178, 255)
HAIR_LIGHT = (214, 210, 232, 255)
SKIN = (248, 182, 132, 255)
SKIN_DARK = (222, 146, 102, 255)
BLUSH = (240, 120, 110, 255)
CARDIGAN = (106, 50, 124, 255)
CARDIGAN_DARK = (82, 36, 100, 255)
CARDIGAN_LIGHT = (134, 74, 154, 255)
COLLAR = (246, 244, 240, 255)
SCARF = (220, 66, 52, 255)
SKIRT = (42, 38, 92, 255)
SKIRT_DARK = (30, 28, 70, 255)
SHOE = (150, 86, 50, 255)
SHOE_LIGHT = (196, 124, 80, 255)
CANE = (232, 140, 82, 255)
CANE_DARK = (186, 98, 56, 255)


def blank():
    image = PIL.Image.new("RGBA", SIZE, (0, 0, 0, 0))
    return image, PIL.ImageDraw.Draw(image)


def finish(image):
    rim = image.getchannel("A").filter(PIL.ImageFilter.MaxFilter(3))
    backing = PIL.Image.new("RGBA", image.size, INK)
    backing.putalpha(rim)
    return PIL.Image.alpha_composite(backing, image)


def head(pen, x, y, mood="calm"):
    pen.ellipse((x, y, x + 8, y + 8), fill=HAIR)                  # the bun
    pen.ellipse((x + 1, y + 1, x + 4, y + 3), fill=HAIR_LIGHT)
    pen.ellipse((x + 3, y + 1, x + 22, y + 19), fill=HAIR)
    pen.rectangle((x + 5, y + 3, x + 12, y + 4), fill=HAIR_LIGHT)
    pen.rounded_rectangle((x + 10, y + 8, x + 22, y + 18), 3, fill=SKIN)
    pen.rectangle((x + 9, y + 6, x + 21, y + 8), fill=HAIR)         # fringe
    pen.rectangle((x + 9, y + 9, x + 10, y + 14), fill=HAIR_DARK)
    pen.rectangle((x + 10, y + 11, x + 11, y + 13), fill=SKIN_DARK)  # ear
    pen.point(((x + 18, y + 16), (x + 21, y + 16)), fill=BLUSH)
    if mood == "happy":
        for ex in (x + 15, x + 19):
            pen.point(((ex, y + 12), (ex + 1, y + 11), (ex + 2, y + 12)), fill=INK)
        pen.rectangle((x + 17, y + 15, x + 19, y + 15), fill=INK)
    elif mood == "shut":
        for ex in (x + 15, x + 19):
            pen.rectangle((ex, y + 12, ex + 2, y + 12), fill=INK)
    elif mood == "wide":
        for ex in (x + 15, x + 19):
            pen.rectangle((ex, y + 10, ex + 1, y + 13), fill=INK)
        pen.ellipse((x + 17, y + 15, x + 19, y + 17), fill=INK)
    elif mood == "fierce":
        for ex in (x + 15, x + 19):
            pen.rectangle((ex, y + 11, ex + 1, y + 13), fill=INK)
        pen.line((x + 14, y + 9, x + 17, y + 10), fill=INK)
        pen.line((x + 22, y + 9, x + 19, y + 10), fill=INK)
        pen.rectangle((x + 17, y + 15, x + 19, y + 15), fill=INK)
    else:
        for ex in (x + 16, x + 20):
            pen.rectangle((ex, y + 11, ex, y + 13), fill=INK)


def torso(pen, x, y, height=16):
    pen.rounded_rectangle((x, y, x + 16, y + height), 3, fill=CARDIGAN)
    pen.rectangle((x + 12, y + 2, x + 15, y + height - 2), fill=CARDIGAN_DARK)
    pen.rectangle((x + 2, y + 2, x + 3, y + height - 3), fill=CARDIGAN_LIGHT)
    pen.polygon(((x + 6, y), (x + 11, y), (x + 9, y + 4)), fill=COLLAR)
    pen.rectangle((x + 8, y + 1, x + 9, y + 3), fill=SCARF)
    for button in range(y + 6, y + height - 1, 4):
        pen.point((x + 9, button), fill=CARDIGAN_DARK)


def arm(pen, shoulder, hand, sleeve=CARDIGAN):
    pen.line((shoulder, hand), fill=sleeve, width=4)
    hx, hy = hand
    pen.ellipse((hx - 2, hy - 2, hx + 2, hy + 2), fill=SKIN)


def skirt(pen, top_left, top_right, bottom_right, bottom_left):
    pen.polygon((top_left, top_right, bottom_right, bottom_left), fill=SKIRT)
    pen.line((top_right, bottom_right), fill=SKIRT_DARK, width=2)


def shoe(pen, x, y, toes=1):
    if toes == 0:
        pen.rounded_rectangle((x, y, x + 3, y + 5), 1, fill=SHOE)
        pen.rectangle((x + 1, y + 1, x + 2, y + 1), fill=SHOE_LIGHT)
        return
    left = x if toes > 0 else x - 3
    pen.rounded_rectangle((left, y, left + 6, y + 3), 1, fill=SHOE)
    pen.rectangle((left + 2, y, left + 4, y), fill=SHOE_LIGHT)


def cane(pen, top, bottom, handle=1):
    pen.line((top, bottom), fill=CANE, width=2)
    tx, ty = top
    pen.line((tx, ty, tx - 4 * handle, ty), fill=CANE, width=2)
    pen.point((tx - 4 * handle, ty + 1), fill=CANE_DARK)
    bx, by = bottom
    pen.rectangle((bx - 1, by - 1, bx + 1, by), fill=CANE_DARK)


def stand(mood="calm"):
    image, pen = blank()
    cane(pen, (31, 33), (31, 59))
    skirt(pen, (11, 40), (25, 40), (27, 54), (9, 54))
    shoe(pen, 10, 55)
    shoe(pen, 18, 55)
    torso(pen, 10, 24)
    arm(pen, (23, 28), (30, 34))
    head(pen, 7, 6, mood)
    return finish(image)


def stretch():
    image, pen = blank()
    skirt(pen, (12, 40), (25, 40), (26, 54), (10, 54))
    shoe(pen, 11, 55)
    shoe(pen, 18, 55)
    torso(pen, 10, 24)
    arm(pen, (12, 26), (9, 5))
    arm(pen, (24, 26), (29, 5))
    cane(pen, (34, 4), (4, 4), handle=-1)
    head(pen, 7, 7, "fierce")
    return finish(image)


def crouch(mood="fierce"):
    image, pen = blank()
    skirt(pen, (9, 46), (27, 46), (31, 56), (5, 56))
    shoe(pen, 5, 56)
    shoe(pen, 22, 56)
    torso(pen, 10, 32, height=14)
    arm(pen, (12, 35), (7, 44))
    arm(pen, (24, 35), (30, 40))
    cane(pen, (30, 38), (33, 59))
    head(pen, 9, 14, mood)
    return finish(image)


def launch():
    image, pen = blank()
    skirt(pen, (13, 36), (25, 36), (24, 50), (14, 50))
    shoe(pen, 15, 51, toes=0)
    shoe(pen, 20, 51, toes=0)
    torso(pen, 11, 20)
    arm(pen, (13, 22), (6, 2))
    arm(pen, (25, 22), (31, 2))
    cane(pen, (33, 1), (30, 16))
    head(pen, 8, 3, "wide")
    return finish(image)


def tuck():
    image, pen = blank()
    ox, oy = 6, 18
    pen.ellipse((ox + 1, oy + 8, ox + 20, oy + 27), fill=CARDIGAN)          # back, curled
    pen.ellipse((ox + 3, oy + 10, ox + 8, oy + 22), fill=CARDIGAN_LIGHT)
    pen.ellipse((ox + 11, oy + 14, ox + 27, oy + 28), fill=SKIRT)           # knees up front
    pen.rectangle((ox + 13, oy + 25, ox + 24, oy + 27), fill=SKIRT_DARK)
    shoe(pen, ox + 8, oy + 27, toes=-1)
    shoe(pen, ox + 14, oy + 28, toes=-1)
    arm(pen, (ox + 12, oy + 12), (ox + 24, oy + 18))                         # hugging them
    pen.line((ox + 4, oy + 26, ox + 26, oy + 6), fill=CANE, width=2)         # cane tucked in
    pen.rectangle((ox + 25, oy + 5, ox + 28, oy + 6), fill=CANE)
    head(pen, ox + 6, oy - 8, "shut")
    return finish(image)


def land():
    image, pen = blank()
    skirt(pen, (10, 44), (26, 44), (29, 56), (7, 56))
    shoe(pen, 7, 56)
    shoe(pen, 21, 56)
    torso(pen, 10, 30, height=14)
    arm(pen, (12, 33), (2, 30))
    arm(pen, (24, 33), (35, 30))
    cane(pen, (38, 26), (36, 40))
    head(pen, 8, 12, "wide")
    return finish(image)


def tada():
    image, pen = blank()
    skirt(pen, (11, 40), (25, 40), (27, 54), (9, 54))
    shoe(pen, 9, 55, toes=-1)
    shoe(pen, 19, 55)
    torso(pen, 10, 24)
    arm(pen, (12, 27), (3, 22))
    arm(pen, (24, 26), (30, 9))
    cane(pen, (34, 0), (29, 18))
    head(pen, 7, 6, "happy")
    return finish(image)


@functools.lru_cache(maxsize=1)
def poses():
    raw = {
        "stand": stand(), "stand_wide": stand("wide"), "stretch": stretch(),
        "crouch": crouch(), "launch": launch(), "land": land(), "tada": tada(),
    }
    ball = tuck()
    raw["tuck_0"] = ball
    raw["tuck_1"] = ball.transpose(PIL.Image.ROTATE_90)
    raw["tuck_2"] = ball.transpose(PIL.Image.ROTATE_180)
    raw["tuck_3"] = ball.transpose(PIL.Image.ROTATE_270)
    return {name: image.resize((image.width * SCALE, image.height * SCALE), PIL.Image.NEAREST)
            for name, image in raw.items()}
