import numpy
import PIL.Image

from ...config import (
    CARRY_DIR, CARRY_IDLE_FILES, CARRY_JUMP_FILES, CARRY_WALK_FILES, IDLE_SHEET,
    IDLE_SHEETS, IDLE_SHEET_COLS, IDLE_SHEET_FRAMES, JUMP_ROW, KID_CAUGHT_FRAMES,
    KID_RUN_FRAMES, KID_SHEETS, KID_SHEET_COLS, KID_SHEET_ROWS, MOVEMENT_SHEET,
    SHEET_COLS, SHEET_ROWS, SOLID_ALPHA, SPRITE_DIR, WALK_ROWS,
)
from .keying import add_rim, key_out_white, to_art_height, trim


def band_cuts(occupied, count, size):
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
    every_cell = [cell for group in groups for cell in group]
    frame_w = max(cell.width for cell in every_cell)
    frame_h = max(cell.height for cell in every_cell)

    def place(cell):
        canvas = PIL.Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        canvas.paste(cell, ((frame_w - cell.width) // 2, frame_h - cell.height))
        return canvas

    return tuple([place(cell) for cell in group] for group in groups)


def terry_idle_cells():
    sheet = key_out_white(PIL.Image.open(SPRITE_DIR / IDLE_SHEET))
    cells = slice_sheet(sheet, IDLE_SHEET_COLS, 1)
    return [cells[(0, col)] for col in range(IDLE_SHEET_COLS)]


def load_idle_frames(art, glow=True):
    sheet = key_out_white(PIL.Image.open(SPRITE_DIR / IDLE_SHEETS[art]))
    cells = slice_sheet(sheet, IDLE_SHEET_FRAMES, 1)
    small = to_art_height([cells[(0, col)] for col in range(IDLE_SHEET_FRAMES)])
    frames, = align_frames(([add_rim(cell, glow) for cell in small],))
    return frames


def load_kid_frames(name):
    sheet = key_out_white(PIL.Image.open(SPRITE_DIR / KID_SHEETS[name]))
    cells = slice_sheet(sheet, KID_SHEET_COLS, KID_SHEET_ROWS)
    ordered = [cells[(row, col)] for row in range(KID_SHEET_ROWS)
               for col in range(KID_SHEET_COLS)]
    run = ordered[:KID_RUN_FRAMES]
    caught = ordered[KID_RUN_FRAMES:KID_RUN_FRAMES + KID_CAUGHT_FRAMES]
    small = to_art_height(run + caught)
    rimmed = [add_rim(cell, glow=False) for cell in small]
    return align_frames((rimmed[:len(run)], rimmed[len(run):]))


def group_sizes():
    return (len(WALK_ROWS) * SHEET_COLS, SHEET_COLS, IDLE_SHEET_COLS)


def load_terry_frames(glow=True):
    sheet = key_out_white(PIL.Image.open(SPRITE_DIR / MOVEMENT_SHEET))
    cells = slice_sheet(sheet, SHEET_COLS, SHEET_ROWS)

    walk = [cells[(row, col)] for row in WALK_ROWS for col in range(SHEET_COLS)]
    jump = [cells[(JUMP_ROW, col)] for col in range(SHEET_COLS)]

    reference_h = sum(cell.height for cell in walk) / len(walk)
    idle = []
    for cell in terry_idle_cells():
        ratio = reference_h / cell.height
        idle.append(cell.resize(
            (max(1, round(cell.width * ratio)), max(1, round(cell.height * ratio))),
            PIL.Image.LANCZOS,
        ))

    groups = (walk, jump, idle)
    sizes = [len(group) for group in groups]
    small = to_art_height([cell for group in groups for cell in group])
    rimmed, start = [], 0
    for count in sizes:
        rimmed.append([add_rim(cell, glow) for cell in small[start:start + count]])
        start += count
    return align_frames(tuple(rimmed))


def carry_group_sizes():
    return (len(CARRY_WALK_FILES), len(CARRY_JUMP_FILES), len(CARRY_IDLE_FILES))


def load_carry_frames():
    groups = (CARRY_WALK_FILES, CARRY_JUMP_FILES, CARRY_IDLE_FILES)
    names = [name for group in groups for name in group]
    cells = [
        trim(key_out_white(PIL.Image.open(SPRITE_DIR / CARRY_DIR / name)))
        for name in names
    ]
    small = to_art_height(cells)
    rimmed, start = [], 0
    for group in groups:
        rimmed.append([add_rim(cell) for cell in small[start:start + len(group)]])
        start += len(group)
    return align_frames(tuple(rimmed))
