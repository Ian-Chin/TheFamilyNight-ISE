import math

import numpy
import PIL.Image
import PIL.ImageChops
import PIL.ImageDraw
import PIL.ImageFilter
from scipy import ndimage

from . import granny_art

ART = 2                    # the cabin's art pixels are about two frame pixels
FLOOR_TOP = 312            # frame row where the crowd ends and the floor starts
FLOOR_REF = (300, 326)     # columns of clear floor, to patch holes with
CROWD = (9, 9, 9, 255)     # the silhouettes behind everyone
KID_BOX = (326, 204, 411, 354)
GRANNY_BOX = (492, 190, 566, 354)
HEAD_BOX = (698, 194, 756, 252)       # the man in glasses, for turning him green
BAG = (586, 326)           # middle of Terry's shopping bag
GRANNY_FEET = (529, 352)   # where she stands, for her drawn poses
SPOTS = ((372, 262), (529, 262), (626, 262), (727, 262))

DURATION = (1.7, 1.6, 1.8, 1.8)
REWIND = 0.25              # every culprit is back in their idle pose by now

INK = (16, 14, 24, 255)
WHITE = (250, 250, 246, 255)
VIOLET = (164, 110, 255, 255)
SHADOW_BODY = (38, 24, 66, 255)
YELLOW = (255, 226, 96, 255)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def span(t, start, end):
    return max(0.0, min(1.0, (t - start) / (end - start)))


def stamp(frame, art, x, y, scale=ART, alpha=1.0):
    if scale != 1:
        art = art.resize((art.width * scale, art.height * scale), PIL.Image.NEAREST)
    if alpha < 1:
        art = art.copy()
        art.putalpha(art.getchannel("A").point(lambda v: round(v * alpha)))
    x, y = round(x), round(y)
    left, top = max(0, -x), max(0, -y)
    right, bottom = min(art.width, frame.width - x), min(art.height, frame.height - y)
    if right > left and bottom > top:
        frame.alpha_composite(art.crop((left, top, right, bottom)), (x + left, y + top))


def outlined(art, color):
    rim = art.getchannel("A").filter(PIL.ImageFilter.MaxFilter(3))
    backing = PIL.Image.new("RGBA", art.size, color)
    backing.putalpha(rim)
    return PIL.Image.alpha_composite(backing, art)


def shadow(looking_down=False, roar=False):
    art = PIL.Image.new("RGBA", (20, 22), (0, 0, 0, 0))
    pen = PIL.ImageDraw.Draw(art)
    pen.ellipse((4, 5, 15, 21), fill=SHADOW_BODY)
    pen.rectangle((4, 14, 15, 21), fill=SHADOW_BODY)
    pen.polygon(((5, 6), (4, 1), (8, 5)), fill=SHADOW_BODY)       # horns
    pen.polygon(((14, 6), (15, 1), (11, 5)), fill=SHADOW_BODY)
    for x0, x1, tip in ((1, 4, 0), (15, 18, 19)):                 # arms up, claws out
        pen.rectangle((x0, 8, x1, 11), fill=SHADOW_BODY)
        pen.rectangle((tip, 5, tip, 8), fill=SHADOW_BODY)
        pen.point(((tip + (1 if tip == 0 else -1), 6), (tip, 4)), fill=SHADOW_BODY)
    for x in (4, 8, 12):                                          # ragged hem
        pen.rectangle((x, 20, x + 1, 21), fill=(0, 0, 0, 0))
    art = outlined(art, VIOLET)
    pen = PIL.ImageDraw.Draw(art)
    drop = 1 if looking_down else 0
    for x in (6, 11):
        pen.rectangle((x, 9, x + 2, 11), fill=YELLOW)
        pen.point((x + (2 if looking_down else 1), 10 + drop), fill=INK)
    if roar:
        pen.rectangle((7, 14, 12, 18), fill=(214, 52, 78, 255))
        for x in (7, 9, 11):
            pen.point(((x, 14), (x + 1, 18)), fill=WHITE)
    else:
        pen.rectangle((7, 15, 12, 15), fill=(214, 52, 78, 255))
        pen.point(((8, 16), (11, 16)), fill=WHITE)
    return art


def bubble(width=40, height=25):
    art = PIL.Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pen = PIL.ImageDraw.Draw(art)
    pen.rounded_rectangle((1, 3, width - 2, height - 4), 8, fill=WHITE)
    for x in range(4, width - 9, 8):
        pen.ellipse((x, 0, x + 9, 8), fill=WHITE)
        pen.ellipse((x + 2, height - 9, x + 11, height - 1), fill=WHITE)
    return outlined(art, INK)


def blob(size, color, edge):
    art = PIL.Image.new("RGBA", (size + 2, size + 2), (0, 0, 0, 0))
    PIL.ImageDraw.Draw(art).ellipse((1, 1, size, size), fill=color)
    return outlined(art, edge)


def trap():
    art = PIL.Image.new("RGBA", (14, 9), (0, 0, 0, 0))
    pen = PIL.ImageDraw.Draw(art)
    pen.rectangle((1, 4, 12, 7), fill=(204, 160, 104, 255))
    pen.rectangle((1, 7, 12, 7), fill=(160, 118, 76, 255))
    pen.rectangle((2, 2, 11, 3), fill=(190, 196, 208, 255))      # the bar, snapped shut
    pen.rectangle((2, 2, 2, 5), fill=(190, 196, 208, 255))
    pen.rectangle((11, 2, 11, 5), fill=(190, 196, 208, 255))
    pen.rectangle((6, 4, 7, 5), fill=(120, 126, 140, 255))       # spring
    return outlined(art, INK)


def star(color=YELLOW):
    art = PIL.Image.new("RGBA", (5, 5), (0, 0, 0, 0))
    pen = PIL.ImageDraw.Draw(art)
    pen.rectangle((2, 0, 2, 4), fill=color)
    pen.rectangle((0, 2, 4, 2), fill=color)
    return art


def bang():
    art = PIL.Image.new("RGBA", (3, 8), (0, 0, 0, 0))
    pen = PIL.ImageDraw.Draw(art)
    pen.rectangle((0, 0, 2, 4), fill=(255, 90, 90, 255))
    pen.rectangle((0, 6, 2, 7), fill=(255, 90, 90, 255))
    return outlined(art, INK)


def cheese():
    art = PIL.Image.new("RGBA", (10, 7), (0, 0, 0, 0))
    pen = PIL.ImageDraw.Draw(art)
    pen.polygon(((0, 6), (9, 6), (9, 1)), fill=(255, 214, 80, 255))
    pen.rectangle((0, 5, 9, 6), fill=(236, 180, 50, 255))
    pen.point(((6, 4), (8, 3), (4, 5)), fill=(214, 156, 40, 255))
    return outlined(art, INK)


def mark(char):
    art = PIL.Image.new("RGBA", (5, 8), (0, 0, 0, 0))
    pen = PIL.ImageDraw.Draw(art)
    color = (255, 226, 96, 255) if char == "?" else (255, 90, 90, 255)
    if char == "?":
        pen.rectangle((0, 0, 4, 1), fill=color)
        pen.rectangle((3, 1, 4, 3), fill=color)
        pen.rectangle((2, 3, 3, 4), fill=color)
        pen.rectangle((2, 6, 3, 7), fill=color)
    else:
        pen.rectangle((1, 0, 3, 4), fill=color)
        pen.rectangle((1, 6, 3, 7), fill=color)
    return outlined(art, INK)


def drop():
    art = PIL.Image.new("RGBA", (2, 3), (150, 214, 255, 255))
    art.putpixel((0, 0), (0, 0, 0, 0))
    return art


class Payback:
    def __init__(self, idle_frame):
        self.idle = idle_frame.convert("RGBA")
        self.cuts = {}
        self.art = {
            "shadow": shadow(), "shadow_down": shadow(looking_down=True),
            "shadow_roar": shadow(looking_down=True, roar=True), "bubble": bubble(),
            "dot": blob(4, WHITE, INK), "dot_small": blob(2, WHITE, INK),
            "trap": trap(), "cheese": cheese(), "question": mark("?"), "alarm": mark("!"),
            "big_bubble": bubble(52, 32), "star": star(), "spark": star(WHITE), "bang": bang(),
            "drop": drop(), "dust": blob(5, (206, 200, 186, 255), (120, 116, 108, 255)),
            "gas": blob(8, (178, 208, 74, 235), (104, 136, 40, 255)),
            "gas_small": blob(5, (198, 222, 96, 235), (104, 136, 40, 255)),
        }


    def cut(self, box):
        if box in self.cuts:
            return self.cuts[box]
        left, top, right, bottom = box
        pixels = numpy.asarray(self.idle.crop(box).convert("RGB")).astype(int)
        height, width = pixels.shape[:2]
        strip = numpy.asarray(self.idle.crop((FLOOR_REF[0], top, FLOOR_REF[1], bottom)).convert("RGB"))
        behind = numpy.tile(strip, (1, width // strip.shape[1] + 1, 1))[:, :width].astype(int)
        floor = (numpy.arange(height) + top >= FLOOR_TOP)[:, None]
        solid = numpy.where(floor, numpy.abs(pixels - behind).max(axis=2) > 34,
                            pixels.max(axis=2) > 28)
        solid = ndimage.binary_fill_holes(ndimage.binary_dilation(solid, iterations=2))
        labels, count = ndimage.label(solid)
        if count > 1:
            sizes = ndimage.sum(solid, labels, range(1, count + 1))
            solid = labels == 1 + int(numpy.argmax(sizes))

        figure = self.idle.crop(box)
        figure.putalpha(PIL.Image.fromarray((solid * 255).astype("uint8")))
        cover = ndimage.binary_dilation(solid, iterations=2)
        patch = numpy.zeros((height, width, 4), dtype="uint8")
        patch[..., :3] = numpy.where(floor[..., None], behind, numpy.array(CROWD[:3]))
        patch[..., 3] = cover * 255
        self.cuts[box] = figure, PIL.Image.fromarray(patch)
        return self.cuts[box]

    def move(self, frame, box, dx=0.0, dy=0.0, angle=0.0):
        figure, patch = self.cut(box)
        frame.alpha_composite(patch, box[:2])
        if angle:
            figure = figure.rotate(angle, PIL.Image.NEAREST, expand=True)
        x = box[0] + (box[2] - box[0] - figure.width) / 2 + dx
        y = box[1] + (box[3] - box[1] - figure.height) / 2 + dy
        stamp(frame, figure, x, y, scale=1)


    def thought(self, frame, taps, clock, jolt=False):
        art = self.art
        bob = round(math.sin(clock * 3.2) * 2)
        shake = round(math.sin(clock * 90) * 2) if jolt or taps >= 3 else 0
        x, y = 318 + shake, 150 + bob
        stamp(frame, art["dot_small"], 398, 204)
        stamp(frame, art["dot"], 390 + shake, 194 + bob // 2)
        if taps < 2:
            stamp(frame, art["bubble"], x, y)
            look = "shadow_down" if taps >= 1 else "shadow"
            stamp(frame, art[look], x + 20 + round(math.sin(clock * 6) * 2), y + 3)
            return
        stamp(frame, art["big_bubble"], x - 12, y - 12)
        if taps == 2:
            stamp(frame, art["shadow_down"], x + 12, y - 26, scale=3)
            return
        stamp(frame, art["shadow_roar"], x + 22 + shake, y - 16, scale=3)
        fall = (clock * 1.6) % 1
        stamp(frame, art["drop"], 410, 214 + fall * 22, alpha=1 - fall)
        if (clock * 4) % 1 < 0.6:
            stamp(frame, art["alarm"], 420, 190)

    def granny_pose(self, frame, name, dx=0.0, dy=0.0):
        _, patch = self.cut(GRANNY_BOX)
        frame.alpha_composite(patch, GRANNY_BOX[:2])
        pose = granny_art.poses()[name]
        canvas_w, canvas_h = (size * granny_art.SCALE for size in granny_art.SIZE)
        feet_x, feet_y = (size * granny_art.SCALE for size in granny_art.FEET)
        cx = GRANNY_FEET[0] - feet_x + canvas_w / 2 + dx
        cy = GRANNY_FEET[1] - feet_y + canvas_h / 2 + dy
        stamp(frame, pose, cx - pose.width / 2, cy - pose.height / 2, scale=1)

    def stage(self, frame, event, taps, clock, since):
        art = self.art
        kick = math.exp(-since * 9)          # 1 just after a press, gone in a moment
        if event == 0:
            self.thought(frame, taps, clock)
        elif event == 1:
            if taps == 0:
                return
            if taps == 1:
                self.granny_pose(frame, "stand_wide", dy=-14 * kick)
                stamp(frame, art["question"], 552, 168 - 4 * kick)
            elif taps == 2:
                name = "stretch" if (clock * 2.5) % 1 < 0.5 else "stand"
                self.granny_pose(frame, name, dy=-8 * kick)
            else:
                self.granny_pose(frame, "crouch", dx=round(math.sin(clock * 70)))
                for index, (x, y) in enumerate(((486, 250), (566, 240), (530, 222))):
                    if (clock * 8 + index) % 2 < 1:
                        stamp(frame, art["spark"], x, y)
        elif event == 2:
            bx, by = BAG
            if taps >= 1:
                wiggle = round(math.sin(clock * 30) * 2 * max(kick, 0.3))
                for index, (x, y) in enumerate(((-24, -14), (16, -18), (-6, -26))):
                    if (clock * 6 + index) % 2 < 1.2:
                        stamp(frame, art["spark"], bx + x + wiggle, by + y, alpha=0.8)
            if taps >= 2:
                stamp(frame, art["cheese"], bx - 22, by - 30 - 6 * kick)      # bait
            if taps >= 3:
                stamp(frame, art["trap"], bx - 4, by - 26, alpha=0.9)          # and the trap under it
                if (clock * 3) % 1 < 0.3:
                    stamp(frame, art["star"], bx + 22, by - 32)
            if taps >= 4:
                stamp(frame, art["question"], 646, 150 - 4 * kick)
                fall = (clock * 1.5) % 1
                stamp(frame, art["drop"], 660, 170 + fall * 20, alpha=1 - fall)
        elif event == 3:
            if taps == 0:
                return
            left, top, right, bottom = HEAD_BOX
            if taps >= 2:
                head = frame.crop(HEAD_BOX)
                mask = head.convert("L").point(lambda v: 255 if v > 30 else 0)
                red = PIL.ImageChops.multiply(head, PIL.Image.new("RGBA", head.size, (255, 140, 120, 255)))
                red.putalpha(mask.point(lambda v: round(v * min(1.0, 0.35 * taps))))
                jitter = round(math.sin(clock * 60) * 1.5) if taps >= 3 else 0
                stamp(frame, red, left + jitter, top, scale=1)
            for x in (left + 14, right - 18):
                stamp(frame, art["dot_small"], x, bottom - 22 - 2 * kick)
            stamp(frame, art["alarm"], right + 6, top - 4 - 4 * kick)
            if taps >= 3:
                fall = (clock * 1.8) % 1
                stamp(frame, art["drop"], right - 4, top + 16 + fall * 22, alpha=1 - fall)
            if taps >= 4:
                puff = (clock * 1.2) % 1
                stamp(frame, art["gas_small"], 752 + 10 * puff, 300 - 14 * puff, alpha=1 - puff)


    def creep_at(self, event, t, start):
        if event == 1:
            return 0.0              # she is already in her own drawn poses
        if event == 2:
            if t < 0.15:
                return start + (1 - start) * (t / 0.15)
            if t < 0.32:
                return 1.0
            return 1 - ease(span(t, 0.32, 0.8))
        return start * (1 - span(t, 0, REWIND))

    def play(self, frame, event, t):
        (self.kid, self.granny, self.suit, self.glasses)[event](frame, t)

    def kid(self, frame, t):
        art = self.art
        if t < REWIND:
            self.thought(frame, 1.0, t * 4, jolt=True)
            return
        out = span(t, REWIND, REWIND + 0.18)
        gone = span(t, 1.3, DURATION[0])
        big = art["shadow_roar"]
        scale = 2 + round(2 * ease(out))
        lunge = math.sin(span(t, REWIND, 1.3) * math.pi) * 10
        stamp(frame, big, 256 + lunge + round(math.sin(t * 40) * 1.5), 268 - 22 * scale,
              scale=scale, alpha=1 - gone)
        hop = span(t, REWIND + 0.05, REWIND + 0.5)
        dy = -30 * 4 * hop * (1 - hop)
        dx = round(math.sin(t * 70) * 2) if t < 1.3 else 0
        self.move(frame, KID_BOX, dx + 4 * ease(out) * (1 - gone), dy)
        if t < 1.3:
            for index, (x, y) in enumerate(((404, 196), (414, 206), (396, 188))):
                if (t * 9 + index) % 3 < 2:
                    stamp(frame, art["bang"], x + dx, y + dy)
            fall = (t * 1.6) % 1
            stamp(frame, art["drop"], 372, 214 + fall * 26 + dy, alpha=1 - fall)
            stamp(frame, art["drop"], 410, 220 + ((fall + 0.5) % 1) * 26 + dy, alpha=fall)

    def granny(self, frame, t):
        art = self.art
        if t < 0.15:
            self.granny_pose(frame, "crouch", dy=4 * span(t, 0, 0.15))
            return
        if t < 1.0:
            air = span(t, 0.15, 1.0)
            dy = -96 * 4 * air * (1 - air)
            if air < 0.18:
                name = "launch"
            elif air < 0.86:
                name = "tuck_%d" % min(3, int((air - 0.18) / 0.68 * 4 + 1) % 4)
            else:
                name = "launch"
            self.granny_pose(frame, name, dy=dy)
            if 0.18 < air < 0.86:
                for index in range(4):
                    back = air - index * 0.05
                    angle = back * math.tau * 1.2
                    stamp(frame, art["spark"], 529 + math.cos(angle) * 46,
                          262 + dy * 0.6 + math.sin(angle) * 38, alpha=0.8 - index * 0.18)
            return
        landed = span(t, 1.0, 1.18)
        self.granny_pose(frame, "land" if landed < 1 else "tada")
        settle = span(t, 1.0, DURATION[1])
        for side in (-1, 1):
            stamp(frame, art["dust"], 524 + side * (20 + 30 * settle), 340 - 8 * settle,
                  alpha=1 - settle)
        if landed >= 1:
            for index, (x, y) in enumerate(((492, 196), (566, 176), (530, 160))):
                if (t * 10 + index) % 2 < 1.3:
                    stamp(frame, art["star"], x, y - 8 * settle)

    def suit(self, frame, t):
        art = self.art
        if t < 0.15:
            return
        gone = span(t, 1.55, DURATION[2])
        up = ease(span(t, 0.32, 0.8))
        shake = round(math.sin(t * 60) * 2) if t > 0.3 else 0
        x = 574 + (604 - 574) * up + shake
        y = 298 + (208 - 298) * up
        if up >= 1:
            pen = PIL.ImageDraw.Draw(frame)
            sleeve = (38, 52, 112, round(255 * (1 - gone)))
            pen.polygon(((632, 246), (642, 240), (620 + shake, 216), (610 + shake, 224)),
                        fill=sleeve, outline=(16, 14, 24, round(255 * (1 - gone))))
            pen.rectangle((608 + shake, 214, 620 + shake, 226),
                          fill=(244, 196, 160, round(255 * (1 - gone))),
                          outline=(16, 14, 24, round(255 * (1 - gone))))
        stamp(frame, art["trap"], x - 7, y - 4, scale=3, alpha=1 - gone)
        if t < 0.5:
            burst = span(t, 0.15, 0.5)
            for index in range(6):
                angle = index * math.tau / 6
                stamp(frame, art["spark"], 586 + math.cos(angle) * 34 * burst,
                      300 + math.sin(angle) * 26 * burst, alpha=1 - burst)
        elif gone < 1:
            for index, (dx, dy) in enumerate(((-18, -8), (30, -14), (6, -24))):
                if (t * 10 + index) % 3 < 2:
                    stamp(frame, art["bang"], x + dx, y + dy, alpha=1 - gone)
            fall = (t * 1.8) % 1
            stamp(frame, art["drop"], 660, 176 + fall * 24, alpha=(1 - fall) * (1 - gone))

    def glasses(self, frame, t):
        art = self.art
        gone = span(t, 1.45, DURATION[3])
        rise = ease(span(t, 0.15, 0.9))
        for index in range(5):
            wobble = math.sin(t * 7 + index * 1.9) * 9
            x = 752 + (722 - 752) * rise + wobble * (1 - rise * 0.5) + index % 3 * 5
            y = 302 + (212 - 302) * rise + index * 6 * (1 - rise) + math.cos(t * 5 + index) * 5
            stamp(frame, art["gas" if index % 2 else "gas_small"], x, y, alpha=(1 - gone) * 0.92)
        sick = span(t, 0.6, 0.95) * (1 - gone)
        if sick > 0:
            head = frame.crop(HEAD_BOX)
            mask = head.convert("L").point(lambda v: 255 if v > 30 else 0)
            green = PIL.ImageChops.multiply(head, PIL.Image.new("RGBA", head.size, (150, 232, 120, 255)))
            green.putalpha(mask.point(lambda v: round(v * sick)))
            jitter = round(math.sin(t * 50) * 1.5) if t < 1.45 else 0
            stamp(frame, green, HEAD_BOX[0] + jitter, HEAD_BOX[1], scale=1)
            for index in range(3):
                angle = t * 6 + index * math.tau / 3
                stamp(frame, art["star"], 722 + math.cos(angle) * 26, 186 + math.sin(angle) * 7,
                      alpha=sick)
