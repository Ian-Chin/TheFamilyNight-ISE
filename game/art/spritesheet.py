"""Cutting Terry's animation frames out of the source art.

Returns PIL images; wrapping them into GPU textures is `game.textures`.
"""

import numpy
import PIL.Image

from ..config import (
    IDLE_FILES, JUMP_ROW, MOVEMENT_SHEET, SHEET_COLS, SHEET_ROWS, SOLID_ALPHA,
    SPRITE_DIR, WALK_ROWS,
)
from .keying import key_out_white, trim


def band_cuts(occupied, count, size):
    """Split an axis into `count` bands, cutting through the widest gaps.

    The drawn frames overflow an even grid, so cut lines come from the blank
    space in the sheet rather than from a fixed cell size.
    """
    runs = []
    start = None
    for index, filled in enumerate(occupied):
        if filled and start is None:
            start = index
        elif not filled and start is not None:
            runs.append([start, index])
            start = None
    if start is not None:
        runs.append([start, len(occupied)])

    if len(runs) < count:
        step = size / count
        return [round(i * step) for i in range(count + 1)]

    # Blank space also separates a character from its own feet, so close the
    # narrowest gaps first until only the gaps between frames remain.
    while len(runs) > count:
        gaps = [runs[i + 1][0] - runs[i][1] for i in range(len(runs) - 1)]
        i = gaps.index(min(gaps))
        runs[i][1] = runs[i + 1][1]
        del runs[i + 1]

    cuts = [0]
    for i in range(count - 1):
        cuts.append((runs[i][1] + runs[i + 1][0]) // 2)
    cuts.append(size)
    return cuts


def slice_sheet(image, cols, rows):
    """Cut a sheet into trimmed cells, keyed on (row, col)."""
    alpha = numpy.asarray(image.split()[3]) > SOLID_ALPHA
    col_cuts = band_cuts(alpha.any(axis=0), cols, image.width)
    row_cuts = band_cuts(alpha.any(axis=1), rows, image.height)
    return {
        (row, col): trim(image.crop(
            (col_cuts[col], row_cuts[row], col_cuts[col + 1], row_cuts[row + 1])
        ))
        for row in range(rows)
        for col in range(cols)
    }


def align_frames(groups):
    """Put every frame on one canvas with its feet on the bottom edge.

    A shared canvas keeps the sprite at a single size and stops it jumping
    around as frames change.
    """
    every_cell = [cell for group in groups for cell in group]
    frame_w = max(cell.width for cell in every_cell)
    frame_h = max(cell.height for cell in every_cell)

    def place(cell):
        canvas = PIL.Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        canvas.paste(cell, ((frame_w - cell.width) // 2, frame_h - cell.height))
        return canvas

    return tuple([place(cell) for cell in group] for group in groups)


def load_terry_frames():
    """Return (walk, jump, idle) frame lists as aligned PIL images."""
    sheet = key_out_white(PIL.Image.open(SPRITE_DIR / MOVEMENT_SHEET))
    cells = slice_sheet(sheet, SHEET_COLS, SHEET_ROWS)

    walk = [cells[(row, col)] for row in WALK_ROWS for col in range(SHEET_COLS)]
    jump = [cells[(JUMP_ROW, col)] for col in range(SHEET_COLS)]

    # The idle art is drawn far larger than a sheet cell, so bring it down to
    # the walk frames before anything is measured against them.
    reference_h = sum(cell.height for cell in walk) / len(walk)
    idle = []
    for name in IDLE_FILES:
        cell = trim(key_out_white(PIL.Image.open(SPRITE_DIR / name)))
        ratio = reference_h / cell.height
        idle.append(cell.resize(
            (max(1, round(cell.width * ratio)), max(1, round(cell.height * ratio))),
            PIL.Image.LANCZOS,
        ))

    return align_frames((walk, jump, idle))
