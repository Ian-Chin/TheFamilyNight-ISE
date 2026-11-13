import PIL.Image
import PIL.ImageDraw
import PIL.ImageEnhance

INK = (22, 26, 42, 255)
GLASS = (44, 66, 110, 255)
GLASS_SHINE = (120, 160, 212, 255)
TYRE = (26, 28, 38, 255)
HUB = (96, 102, 118, 255)
BUMPER = (62, 68, 84, 255)
CHROME = (176, 184, 198, 255)
TAIL = (232, 62, 62, 255)
TAIL_GLOW = (255, 150, 130, 255)
AMBER = (255, 176, 46, 255)
PLATE = (240, 240, 232, 255)
SHADOW = (10, 12, 22, 110)


def shade(color, amount):
    target = 255 if amount > 0 else 0
    return (*(round(c + (target - c) * abs(amount)) for c in color[:3]), 255)


def canvas(width, height):
    image = PIL.Image.new("RGBA", (width, height), (0, 0, 0, 0))
    return image, PIL.ImageDraw.Draw(image)


def box(pen, x0, y0, x1, y1, fill):
    pen.rectangle((x0, y0, x1, y1), fill=fill)


def framed(pen, x0, y0, x1, y1, fill):
    box(pen, x0 + 1, y0, x1 - 1, y1, INK)
    box(pen, x0, y0 + 1, x1, y1 - 1, INK)
    box(pen, x0 + 1, y0 + 1, x1 - 1, y1 - 1, fill)


def wheels(pen, left, right, top, bottom, width):
    for x in (left, right - width + 1):
        box(pen, x, top, x + width - 1, bottom, TYRE)
        box(pen, x + 1, top + 1, x + width - 2, top + 1, HUB)


BUS_BODY_W = 44      # the bus itself
BUS_MARGIN = 12      # clear art either side, where the driver leans out


def bus_rear(driver=False, braking=False):
    body = bus_body()
    image, pen = canvas(BUS_BODY_W + 2 * BUS_MARGIN, body.height)
    image.alpha_composite(body, (BUS_MARGIN, 0))
    o = BUS_MARGIN
    if braking:
        for x in (6, 34):
            box(pen, o + x - 1, 27, o + x + 4, 33, (255, 70, 60, 120))
            box(pen, o + x, 28, o + x + 3, 32, (255, 96, 84, 255))
            box(pen, o + x + 1, 29, o + x + 2, 31, (255, 226, 200, 255))
    if driver:
        uniform, cap = (58, 110, 200, 255), (34, 62, 140, 255)
        skin, hair = (244, 196, 160, 255), (40, 40, 56, 255)
        framed(pen, o + 38, 12, o + 47, 21, uniform)
        framed(pen, o + 42, 5, o + 51, 15, hair)
        box(pen, o + 43, 6, o + 50, 10, cap)
        box(pen, o + 43, 13, o + 50, 14, skin)
        box(pen, o + 49, 10, o + 53, 11, cap)
        framed(pen, o + 48, 8, o + 52, 19, uniform)
        box(pen, o + 47, 16, o + 48, 19, uniform)
        framed(pen, o + 51, 1, o + 55, 9, uniform)
        framed(pen, o + 50, -1, o + 56, 4, skin)
    return image


def bus_body():
    width, height = 44, 47
    image, pen = canvas(width, height)
    yellow, cream = (250, 198, 44, 255), (252, 240, 214, 255)
    box(pen, 3, 44, 40, 46, SHADOW)
    wheels(pen, 6, 37, 38, 45, 8)
    framed(pen, 7, 0, 36, 7, cream)
    box(pen, 9, 1, 34, 1, shade(cream, .5))
    framed(pen, 15, 1, 28, 5, GLASS)
    for y in (3, 4):
        box(pen, 17, y, 26, y, shade(GLASS, -.35) if y == 3 else GLASS_SHINE)
    framed(pen, 4, 5, 39, 39, yellow)
    box(pen, 5, 6, 38, 7, shade(yellow, .4))
    box(pen, 5, 23, 38, 24, shade(yellow, -.22))
    box(pen, 5, 34, 38, 34, shade(yellow, -.22))
    framed(pen, 8, 9, 35, 21, GLASS)
    box(pen, 10, 11, 14, 12, GLASS_SHINE)
    box(pen, 11, 13, 13, 13, GLASS_SHINE)
    box(pen, 21, 10, 22, 20, INK)
    for x in (6, 34):
        box(pen, x, 25, x + 3, 26, AMBER)
        box(pen, x, 28, x + 3, 32, TAIL)
        box(pen, x + 1, 29, x + 2, 30, TAIL_GLOW)
    box(pen, 12, 27, 31, 28, INK)
    framed(pen, 16, 29, 27, 34, PLATE)
    box(pen, 18, 31, 25, 32, shade(INK, .45))
    framed(pen, 3, 36, 40, 40, BUMPER)
    box(pen, 5, 37, 38, 37, CHROME)
    box(pen, 28, 41, 31, 42, shade(BUMPER, -.4))
    return image


def car_rear(paint):
    width, height = 34, 27
    image, pen = canvas(width, height)
    paint = (*paint, 255)
    box(pen, 2, 24, 31, 26, SHADOW)
    wheels(pen, 3, 30, 19, 25, 6)
    framed(pen, 6, 0, 27, 12, shade(paint, -.12))
    box(pen, 8, 1, 25, 1, shade(paint, .35))
    framed(pen, 8, 3, 25, 10, GLASS)
    box(pen, 10, 5, 13, 5, GLASS_SHINE)
    box(pen, 10, 6, 11, 6, GLASS_SHINE)
    framed(pen, 1, 10, 32, 21, paint)
    box(pen, 2, 11, 31, 11, shade(paint, .4))
    box(pen, 2, 17, 31, 17, shade(paint, -.25))
    for x in (2, 26):
        box(pen, x, 13, x + 5, 15, TAIL)
        box(pen, x + 1, 13, x + 3, 13, TAIL_GLOW)
    framed(pen, 12, 13, 21, 17, PLATE)
    framed(pen, 1, 19, 32, 22, BUMPER)
    box(pen, 3, 20, 30, 20, CHROME)
    return image


def van_rear(paint):
    width, height = 36, 36
    image, pen = canvas(width, height)
    paint = (*paint, 255)
    box(pen, 2, 33, 33, 35, SHADOW)
    wheels(pen, 4, 31, 28, 34, 6)
    framed(pen, 2, 0, 33, 30, paint)
    box(pen, 4, 1, 31, 2, shade(paint, .4))
    box(pen, 3, 22, 32, 22, shade(paint, -.25))
    box(pen, 17, 3, 18, 27, shade(paint, -.4))
    for x in (5, 20):
        framed(pen, x, 4, x + 10, 13, GLASS)
        box(pen, x + 2, 6, x + 4, 6, GLASS_SHINE)
    for x in (3, 29):
        box(pen, x, 16, x + 3, 21, TAIL)
        box(pen, x + 1, 17, x + 2, 18, TAIL_GLOW)
        box(pen, x, 23, x + 3, 24, AMBER)
    framed(pen, 13, 22, 22, 26, PLATE)
    framed(pen, 1, 28, 34, 31, BUMPER)
    box(pen, 3, 29, 32, 29, CHROME)
    return image


def truck_rear(paint):
    width, height = 42, 50
    image, pen = canvas(width, height)
    paint = (*paint, 255)
    crate = (232, 230, 220, 255)
    box(pen, 2, 47, 39, 49, SHADOW)
    wheels(pen, 4, 37, 40, 48, 10)
    for x in (8, 32):
        box(pen, x, 41, x, 48, shade(TYRE, .25))
    framed(pen, 1, 0, 40, 37, crate)
    box(pen, 3, 1, 38, 2, shade(crate, .6))
    box(pen, 2, 30, 39, 33, paint)
    box(pen, 20, 3, 21, 36, shade(crate, -.3))
    for x in (12, 29):
        box(pen, x, 4, x, 35, shade(crate, -.22))
        box(pen, x - 1, 18, x + 1, 19, BUMPER)
    for y in (8, 16, 24):
        box(pen, 2, y, 3, y + 1, BUMPER)
        box(pen, 38, y, 39, y + 1, BUMPER)
    framed(pen, 2, 36, 39, 42, BUMPER)
    for x in (4, 33):
        box(pen, x, 38, x + 4, 40, TAIL)
        box(pen, x + 1, 38, x + 2, 38, TAIL_GLOW)
    framed(pen, 16, 37, 25, 41, PLATE)
    for x in (5, 30):
        box(pen, x, 43, x + 6, 46, INK)
    return image


def tree():
    image, pen = canvas(30, 46)
    leaf, dark, light = (62, 142, 84, 255), (40, 104, 70, 255), (112, 186, 108, 255)
    box(pen, 5, 43, 25, 45, SHADOW)
    framed(pen, 12, 26, 17, 44, (122, 84, 56, 255))
    box(pen, 13, 27, 13, 43, (156, 112, 74, 255))
    for x0, y0, x1, y1 in ((3, 10, 26, 29), (7, 2, 22, 14), (0, 16, 10, 27), (19, 15, 29, 27)):
        pen.ellipse((x0, y0, x1, y1), fill=leaf, outline=INK)
    pen.ellipse((5, 12, 24, 27), fill=leaf)
    pen.ellipse((9, 4, 20, 13), fill=leaf)
    for x0, y0, x1, y1 in ((9, 5, 15, 9), (5, 13, 11, 17), (16, 12, 21, 15)):
        pen.ellipse((x0, y0, x1, y1), fill=light)
    for x0, y0, x1, y1 in ((14, 21, 24, 27), (3, 21, 9, 26)):
        pen.ellipse((x0, y0, x1, y1), fill=dark)
    return image


def lamp(side=1):
    image, pen = canvas(22, 58)
    pole, lit = (92, 100, 120, 255), (255, 238, 160, 255)
    box(pen, 2, 55, 12, 57, SHADOW)
    box(pen, 4, 4, 6, 56, INK)
    box(pen, 5, 5, 5, 55, pole)
    box(pen, 3, 52, 7, 56, INK)
    box(pen, 4, 2, 17, 4, INK)
    box(pen, 5, 3, 16, 3, pole)
    framed(pen, 13, 3, 20, 7, pole)
    box(pen, 14, 6, 19, 7, lit)
    if side < 0:
        image = image.transpose(PIL.Image.FLIP_LEFT_RIGHT)
    return image


def sign(color=(46, 140, 96)):
    image, pen = canvas(34, 36)
    color = (*color, 255)
    box(pen, 5, 33, 28, 35, SHADOW)
    for x in (7, 25):
        box(pen, x, 18, x + 1, 34, INK)
    framed(pen, 0, 0, 33, 20, color)
    pen.rectangle((2, 2, 31, 18), outline=PLATE)
    box(pen, 16, 6, 17, 15, PLATE)
    box(pen, 14, 8, 19, 8, PLATE)
    box(pen, 15, 7, 18, 7, PLATE)
    box(pen, 12, 9, 13, 9, PLATE)
    box(pen, 20, 9, 21, 9, PLATE)
    for x in (5, 8, 24, 27):
        box(pen, x, 12, x + 1, 13, PLATE)
    return image


def bush():
    image, pen = canvas(22, 13)
    box(pen, 2, 11, 19, 12, SHADOW)
    pen.ellipse((0, 3, 12, 11), fill=(58, 136, 82, 255), outline=INK)
    pen.ellipse((8, 0, 21, 11), fill=(58, 136, 82, 255), outline=INK)
    pen.ellipse((3, 5, 17, 10), fill=(58, 136, 82, 255))
    pen.ellipse((10, 2, 15, 5), fill=(112, 186, 108, 255))
    pen.ellipse((3, 5, 6, 7), fill=(112, 186, 108, 255))
    return image


def backdrop(width=320, height=100):
    image, pen = canvas(width, height)
    bands = ((86, 146, 220), (106, 164, 228), (132, 184, 234), (164, 204, 238),
             (198, 220, 236), (232, 226, 214), (250, 222, 184), (255, 212, 160))
    edges = (0, 14, 28, 40, 51, 61, 70, 78, height)
    for band, top, bottom in zip(bands, edges, edges[1:]):
        box(pen, 0, top, width, bottom, (*band, 255))
    pen.ellipse((222, 46, 258, 82), fill=(255, 232, 178, 255))
    pen.ellipse((227, 51, 253, 77), fill=(255, 246, 214, 255))
    for x, y, w in ((24, 18, 44), (96, 34, 30), (168, 12, 52), (268, 30, 36), (132, 56, 24)):
        box(pen, x + 3, y + 5, x + w - 3, y + 7, (206, 212, 236, 255))
        box(pen, x, y + 3, x + w, y + 5, (252, 252, 255, 255))
        box(pen, x + 5, y, x + w * 2 // 3, y + 3, (252, 252, 255, 255))
        box(pen, x + w // 2, y + 1, x + w - 6, y + 3, (252, 252, 255, 255))
    far, near, front = (128, 152, 196, 255), (96, 148, 132, 255), (78, 150, 92, 255)
    for peak, top, half in ((40, 62, 46), (118, 56, 58), (206, 66, 50), (286, 58, 54)):
        pen.polygon(((peak - half, 90), (peak, top), (peak + half, 90)), fill=far)
        pen.polygon(((peak - 6, top + 8), (peak, top), (peak + 9, top + 12),
                     (peak + 2, top + 9)), fill=(236, 240, 250, 255))
    for x0, top, x1 in ((-30, 78, 110), (70, 82, 210), (180, 76, 350)):
        pen.ellipse((x0, top, x1, top + 44), fill=near)
    for x0, top, x1 in ((-50, 86, 150), (120, 88, 300), (250, 85, 380)):
        pen.ellipse((x0, top, x1, top + 40), fill=front)
    return image


def house():
    image, pen = canvas(150, 100)
    wall, wall_dark = (246, 232, 204, 255), (222, 204, 172, 255)
    roof, roof_dark = (198, 78, 64, 255), (160, 58, 52, 255)
    wood, wood_dark = (150, 104, 68, 255), (112, 76, 52, 255)
    lit = (255, 226, 132, 255)
    lawn, lawn_dark = (126, 196, 110, 255), (98, 170, 92, 255)
    leaf, leaf_light = (62, 142, 84, 255), (112, 186, 108, 255)
    fence = (244, 240, 230, 255)

    box(pen, 0, 76, 149, 99, lawn)
    for x in range(4, 150, 13):
        box(pen, x, 88 + x % 3 * 3, x + 3, 88 + x % 3 * 3, lawn_dark)
    box(pen, 15, 82, 27, 99, (214, 198, 160, 255))

    framed(pen, 42, 46, 47, 84, wood)
    for x0, y0, x1, y1 in ((28, 20, 62, 50), (34, 10, 56, 28), (24, 30, 40, 46), (50, 28, 66, 46)):
        pen.ellipse((x0, y0, x1, y1), fill=leaf, outline=INK)
    pen.ellipse((30, 22, 60, 46), fill=leaf)
    pen.ellipse((36, 13, 46, 20), fill=leaf_light)
    pen.ellipse((30, 28, 38, 34), fill=leaf_light)
    for index, x in enumerate(range(60, 84, 4)):
        y = 44 + (2 if index in (2, 3) else 1 if index in (1, 4) else 0)
        box(pen, x, y, x, y, INK)
        box(pen, x, y + 1, x, y + 2, (lit, (255, 150, 130, 255), (150, 220, 255, 255))[index % 3])

    for x, y, size in ((10, 50, 3), (7, 43, 4), (11, 35, 5)):
        box(pen, x, y, x + size, y + size, (236, 236, 236, 170))
    framed(pen, 5, 58, 15, 64, (44, 46, 58, 255))
    box(pen, 6, 59, 14, 59, (200, 70, 60, 255))
    for x in (6, 13):
        box(pen, x, 65, x, 76, INK)

    framed(pen, 70, 40, 144, 84, wall)
    box(pen, 71, 76, 143, 83, wall_dark)
    framed(pen, 122, 8, 131, 30, (176, 96, 80, 255))
    box(pen, 121, 7, 132, 9, INK)
    pen.polygon(((64, 42), (107, 12), (150, 42)), fill=roof, outline=INK)
    for row in range(18, 42, 6):
        half = (row - 12) * 43 // 30
        box(pen, 107 - half + 2, row, 107 + half - 2, row, roof_dark)
    box(pen, 64, 41, 149, 43, INK)
    framed(pen, 100, 56, 114, 84, wood)
    box(pen, 102, 58, 112, 70, wood_dark)
    box(pen, 111, 71, 112, 72, lit)
    box(pen, 98, 84, 116, 86, (190, 186, 176, 255))
    for x in (76, 121):
        framed(pen, x, 52, x + 16, 68, lit)
        box(pen, x + 8, 53, x + 8, 67, INK)
        box(pen, x + 1, 60, x + 15, 60, INK)
        box(pen, x - 1, 69, x + 17, 70, wall_dark)

    for x in range(0, 150, 5):
        if 14 <= x <= 27:
            continue
        box(pen, x, 74, x + 3, 90, INK)
        box(pen, x + 1, 75, x + 2, 89, fence)
        box(pen, x + 1, 73, x + 2, 73, INK)
    for x0, x1 in ((0, 13), (29, 149)):
        box(pen, x0, 79, x1, 80, fence)
        box(pen, x0, 85, x1, 86, fence)
    for x in (12, 28):
        framed(pen, x, 70, x + 3, 91, wood)
    box(pen, 0, 97, 149, 99, SHADOW)
    return image


def bread_states(path):
    with PIL.Image.open(path) as source:
        bread = source.convert("RGBA")
    bread = bread.crop(bread.getchannel("A").point(lambda v: 255 if v >= 100 else 0).getbbox())
    states = []
    for fresh in range(4):
        image = bread.copy()
        for index in range(fresh, 3):
            part = (round(bread.width * index / 3), 0,
                    round(bread.width * (index + 1) / 3), bread.height)
            stale = PIL.ImageEnhance.Color(image.crop(part)).enhance(.15)
            image.paste(PIL.ImageEnhance.Brightness(stale).enhance(.25), part)
        states.append(image)
    return states
