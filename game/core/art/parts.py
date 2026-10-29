"""Taking a character apart, so they can sit at the table and eat.

Every character is drawn as a round head with two floating hands and two
floating shoes, none of them touching. `split_parts` pulls those five pieces
out of the cut-out by their connected outlines, and `face_frames` paints the
head over with shut eyes and a chewing or talking mouth, so the seated family
can blink, chew and chat.

Everything here works on art already brought down to CHARACTER_ART_HEIGHT and
not yet rimmed; each part gets its own rim afterwards.
"""

import numpy
import PIL.Image
import PIL.ImageChops
import PIL.ImageDraw
import PIL.ImageFilter
from scipy import ndimage

from ...config import SOLID_ALPHA
from .keying import grown

INK = (40, 28, 36, 255)        # eyes and mouth lines, the art's own dark
MOUTH_INSIDE = (92, 34, 42, 255)
PALE_EDGE = (226, 218, 236, 210)
TONGUE = (232, 112, 112, 255)


class Part:
    """One piece of the character and where it sat in the whole drawing."""

    def __init__(self, image, left, top):
        self.image = image
        self.left = left
        self.top = top

    @property
    def center(self):
        return (self.left + self.image.width / 2, self.top + self.image.height / 2)


def split_parts(image):
    """(head, (left hand, right hand), (left foot, right foot)) of the art.

    The four smallest pieces are the hands and feet, the feet being the lower
    pair; everything else, hair bows and all, stays with the head.
    """
    alpha = numpy.array(image.getchannel("A"))
    labels, count = ndimage.label(alpha > SOLID_ALPHA)
    if count < 5:
        raise ValueError("expected a head, two hands and two feet")
    sizes = ndimage.sum(numpy.ones_like(alpha), labels, range(1, count + 1))
    boxes = ndimage.find_objects(labels)
    limbs = sorted(range(count), key=lambda i: sizes[i])[:4]
    # Lower pair are the feet; each pair is then ordered left to right.
    limbs.sort(key=lambda i: boxes[i][0].start)
    hands = sorted(limbs[:2], key=lambda i: boxes[i][1].start)
    feet = sorted(limbs[2:], key=lambda i: boxes[i][1].start)

    # The anti-aliased fringe around each piece belongs to it too, so the
    # labels are grown a few pixels before they cut the image apart.
    owner = ndimage.grey_dilation(labels, size=5)
    owner = numpy.where(labels > 0, labels, owner)
    pixels = numpy.array(image)

    def cut(indices):
        mask = numpy.isin(owner, [i + 1 for i in indices])
        piece = pixels.copy()
        piece[~mask] = 0
        part = PIL.Image.fromarray(piece)
        box = part.getchannel("A").getbbox()
        return Part(part.crop(box), box[0], box[1])

    head = cut([i for i in range(count) if i not in limbs])
    return head, tuple(cut([i]) for i in hands), tuple(cut([i]) for i in feet)


def _skin_around(image, box):
    """Average colour of the face in a ring just outside `box`."""
    left, top, right, bottom = box
    pad = max(4, (bottom - top) // 3)
    ring = image.crop((left - pad, top - pad, right + pad, bottom + pad))
    pixels = numpy.array(ring).reshape(-1, 4).astype(float)
    # Skin is the light, warm, opaque part of the ring: not ink, not hair.
    light = pixels[(pixels[:, 3] > 250) & (pixels[:, :3].sum(axis=1) > 520)
                   & (pixels[:, 0] > pixels[:, 2] + 40)]
    if not len(light):
        light = pixels[pixels[:, 3] > 250]
    return tuple(int(v) for v in light[:, :3].mean(axis=0)) + (255,)


def _paint_over(image, box, grow=3):
    """Cover the feature in `box` with skin, feathered into the face."""
    left, top, right, bottom = box
    skin = _skin_around(image, box)
    mask = PIL.Image.new("L", image.size, 0)
    PIL.ImageDraw.Draw(mask).ellipse(
        (left - grow, top - grow, right + grow, bottom + grow), fill=255,
    )
    mask = mask.filter(PIL.ImageFilter.GaussianBlur(1.5))
    patch = PIL.Image.new("RGBA", image.size, skin)
    # Only where the head is already drawn, so the outline is never eaten.
    mask = PIL.ImageChops.multiply(mask, image.getchannel("A"))
    return PIL.Image.composite(patch, image, mask)


def _line_width(box):
    return max(3, round((box[3] - box[1]) / 6))


def shut_eyes(image, eyes):
    """Eyes closed: each one painted out and redrawn as a soft downward arc."""
    for box in eyes:
        image = _paint_over(image, box)
        left, top, right, bottom = box
        width = max(right - left, 18)
        middle_x = (left + right) / 2
        middle_y = (top + bottom) / 2 + 2
        arc = (middle_x - width / 2, middle_y - width / 4,
               middle_x + width / 2, middle_y + width / 4)
        PIL.ImageDraw.Draw(image).arc(
            arc, 15, 165, fill=INK, width=_line_width((0, 0, 0, width)),
        )
    return image


def open_mouth(image, mouth):
    """Mouth open wide, mid-chew or mid-word: dark inside, a bit of tongue."""
    image = _paint_over(image, mouth)
    left, top, right, bottom = mouth
    width = max((right - left) * 0.7, 26)
    height = max(bottom - top, 24) * 1.05
    cx, cy = (left + right) / 2, (top + bottom) / 2
    box = (cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2)
    draw = PIL.ImageDraw.Draw(image)
    draw.ellipse(box, fill=MOUTH_INSIDE, outline=INK, width=_line_width(mouth))
    draw.chord(
        (cx - width * 0.3, cy, cx + width * 0.3, cy + height * 0.42),
        180, 360, fill=TONGUE,
    )
    return image


def chew_mouth(image, mouth):
    """Mouth shut on a mouthful: a short wavy line with puffed cheeks."""
    image = _paint_over(image, mouth)
    left, top, right, bottom = mouth
    width = (right - left) * 0.5
    cx, cy = (left + right) / 2, (top + bottom) / 2
    step = width / 4
    points = [(cx - width / 2 + i * step, cy + (2 if i % 2 else -2))
              for i in range(5)]
    PIL.ImageDraw.Draw(image).line(
        points, fill=INK, width=_line_width(mouth), joint="curve",
    )
    return image


MOUTHS = ("drawn", "open", "chew")


def face_frames(head, eyes, mouth):
    """Every face the head can pull, keyed by (eyes shut, mouth).

    `eyes` and `mouth` are boxes in the head's own pixels.
    """
    frames = {}
    for shut in (False, True):
        base = shut_eyes(head.copy(), eyes) if shut else head
        frames[(shut, "drawn")] = base
        frames[(shut, "open")] = open_mouth(base.copy(), mouth)
        frames[(shut, "chew")] = chew_mouth(base.copy(), mouth)
    return frames


def morsel(size):
    """A bite of roast on the way to someone's mouth."""
    image = PIL.Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = PIL.ImageDraw.Draw(image)
    pad = max(2, size // 8)
    draw.ellipse((pad, pad, size - pad, size - pad),
                 fill=(196, 112, 52, 255), outline=INK, width=max(2, size // 10))
    shine = size // 4
    draw.ellipse((size // 3, size // 3, size // 3 + shine, size // 3 + shine // 2 + 1),
                 fill=(240, 176, 104, 255))
    return image


def pale_edge(image, width=3):
    """A thin light outline round a rimmed cut-out.

    The shoes are dark grey and hang over the dark stools and table, where the
    dark contour alone loses them; the soft halo is too wide for something so
    small, so they get this instead.
    """
    edge = PIL.Image.new("RGBA", image.size, (0, 0, 0, 0))
    edge.paste(PALE_EDGE, (0, 0), grown(image.getchannel("A"), width))
    return PIL.Image.alpha_composite(edge, image)
