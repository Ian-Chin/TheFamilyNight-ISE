"""Bake the family's breathing idle sheets from their standing art.

Each character is drawn as a round head with floating hands and shoes, so a
breath is the head rising a touch, the hands following it part of the way and
the shoes staying put. This takes each art file in assets/characters apart,
draws IDLE_OFFSETS as frames and lays them out left to right on white paper,
like the kids' run sheets, in assets/sprites.

Run from the repo root after changing a character's art:

    python tools/make_idle_sheets.py
"""

import sys
from pathlib import Path

import PIL.Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from game.art.keying import key_out_white, trim  # noqa: E402
from game.art.parts import split_parts  # noqa: E402
from game.config import CHARACTER_DIR, IDLE_SHEETS, SPRITE_DIR  # noqa: E402

# (head rise, hand rise) per frame, in pixels of the ~1000px source art: rest,
# breathing in, full breath, breathing out.
IDLE_OFFSETS = ((0, 0), (8, 5), (14, 9), (8, 5))
CELL_SCALE = 0.6   # the sheet does not need the full source size
CELL_PAD = 80      # white paper round each frame, in source pixels


def cut_out(path):
    image = PIL.Image.open(path)
    if not (image.mode == "RGBA" and image.getchannel("A").getextrema()[0] < 255):
        image = key_out_white(image)
    return trim(image.convert("RGBA"))


def breathing_frames(image):
    head, hands, feet = split_parts(image)
    rise = max(head_rise for head_rise, _ in IDLE_OFFSETS)
    width, height = image.width, image.height + rise
    frames = []
    for head_rise, hand_rise in IDLE_OFFSETS:
        frame = PIL.Image.new("RGBA", (width, height), (0, 0, 0, 0))
        for part, lift in ((head, head_rise), *((hand, hand_rise) for hand in hands),
                           *((foot, 0) for foot in feet)):
            frame.alpha_composite(part.image, (part.left, part.top + rise - lift))
        frames.append(frame)
    return frames


def sheet(frames):
    cell_w = frames[0].width + 2 * CELL_PAD
    cell_h = frames[0].height + 2 * CELL_PAD
    paper = PIL.Image.new("RGBA", (cell_w * len(frames), cell_h), (255, 255, 255, 255))
    for index, frame in enumerate(frames):
        paper.alpha_composite(frame, (index * cell_w + CELL_PAD, CELL_PAD))
    size = (round(paper.width * CELL_SCALE), round(paper.height * CELL_SCALE))
    return paper.convert("RGB").resize(size, PIL.Image.LANCZOS)


def main():
    for art, sheet_name in IDLE_SHEETS.items():
        frames = breathing_frames(cut_out(CHARACTER_DIR / art))
        sheet(frames).save(SPRITE_DIR / sheet_name, optimize=True)
        print(f"{art} -> {sheet_name} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
