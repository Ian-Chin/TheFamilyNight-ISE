"""The dialogue box: a speaker's nameplate over a typed-out line."""

import arcade

from . import textures
from .config import (
    DIALOG_ARROW, DIALOG_BLINK, DIALOG_BOTTOM, DIALOG_CHAR_TIME,
    DIALOG_FIRST_LINE, DIALOG_H, DIALOG_HINT_SIZE, DIALOG_LINE_GAP,
    DIALOG_NAME_DROP, DIALOG_NAME_SIZE, DIALOG_PAD, DIALOG_TEXT_SIZE, DIALOG_W,
    PLANK_PAD, TEXT_BRIGHT, TEXT_DIM, TEXT_HOVER, WIDTH,
)

WRAP_CHARS = 74   # characters per line before the text is broken


def wrap(text, limit=WRAP_CHARS):
    """Break `text` into lines of at most `limit` characters, on spaces."""
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split():
            candidate = f"{line} {word}".strip()
            if len(candidate) > limit and line:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


class DialogBox:
    """A speech panel that types its line out and waits for Enter.

    While `typing`, Enter fills the line in at once; once it is complete,
    Enter closes the box. The scene decides what that means.
    """

    def __init__(self):
        self.visible = False
        self.stage = None
        self.speaker = ""
        self.lines = []
        self.revealed = 0
        self.total = 0
        self.clock = 0.0
        self.blink = 0.0
        self.left = (WIDTH - DIALOG_W) / 2
        self.bottom = DIALOG_BOTTOM
        self.top = self.bottom + DIALOG_H

    @property
    def typing(self):
        return self.revealed < self.total

    def open(self, speaker, text):
        self.visible = True
        self.speaker = speaker
        self.lines = wrap(text)
        self.total = sum(len(line) for line in self.lines)
        self.revealed = 0
        self.clock = 0.0
        self.blink = 0.0
        if self.stage is not None:
            self.layout(self.stage)

    def close(self):
        self.visible = False

    def finish_typing(self):
        self.revealed = self.total

    def advance(self):
        """Handle Enter. Returns True when the box has just closed."""
        if self.typing:
            self.finish_typing()
            return False
        self.close()
        return True

    def layout(self, stage):
        self.stage = stage
        self.texture = textures.dialog_box(
            stage.px(DIALOG_W), stage.px(DIALOG_H), stage.px(PLANK_PAD)
        )
        # The speaker's name floats on the panel itself, with no plate of its
        # own; the box is dark enough for it to read.
        self.name_text = stage.text(
            self.speaker, self.left + DIALOG_PAD, self.top - DIALOG_NAME_DROP,
            TEXT_HOVER, DIALOG_NAME_SIZE, anchor_y="center", bold=True,
        )

        # One Text object per line, refilled as characters are revealed.
        first_y = self.top - DIALOG_FIRST_LINE
        self.line_texts = [
            stage.text(
                "", self.left + DIALOG_PAD, first_y - index * DIALOG_LINE_GAP,
                TEXT_BRIGHT, DIALOG_TEXT_SIZE, anchor_y="center",
            )
            for index in range(max(1, len(self.lines)))
        ]
        self.hint_text = stage.text(
            "", self.left + DIALOG_PAD, self.bottom + 30,
            TEXT_DIM, DIALOG_HINT_SIZE, anchor_y="center",
        )
        self.arrow_x = self.left + DIALOG_W - DIALOG_PAD
        self.arrow_y = self.bottom + 30

    def update(self, delta_time):
        if not self.visible:
            return
        self.blink += delta_time
        if not self.typing:
            return
        self.clock += delta_time
        while self.clock >= DIALOG_CHAR_TIME and self.typing:
            self.clock -= DIALOG_CHAR_TIME
            self.revealed += 1

    def visible_lines(self):
        """The lines as far as the typing has got."""
        left = self.revealed
        for line in self.lines:
            if left >= len(line):
                left -= len(line)
                yield line
            else:
                yield line[:left]
                left = 0

    def draw(self):
        if not self.visible:
            return
        arcade.draw_texture_rect(self.texture, self.stage.rect(
            self.left - PLANK_PAD, self.bottom - PLANK_PAD,
            DIALOG_W + 2 * PLANK_PAD, DIALOG_H + 2 * PLANK_PAD,
        ))
        self.name_text.draw()

        for text, content in zip(self.line_texts, self.visible_lines()):
            text.text = content
            text.draw()

        self.hint_text.text = (
            "Enter to skip" if self.typing else "Enter to continue"
        )
        self.hint_text.draw()
        if not self.typing and self.blink % (2 * DIALOG_BLINK) < DIALOG_BLINK:
            self.draw_arrow()

    def draw_arrow(self):
        """A small triangle in the bottom right, nudging the player on."""
        half = DIALOG_ARROW / 2
        points = [
            self.stage.to_screen(self.arrow_x - half, self.arrow_y + half),
            self.stage.to_screen(self.arrow_x + half, self.arrow_y + half),
            self.stage.to_screen(self.arrow_x, self.arrow_y - half),
        ]
        arcade.draw_polygon_filled(points, TEXT_HOVER)
