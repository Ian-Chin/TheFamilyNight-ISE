"""Story select: jump to any scene, or any chapter inside one.

Scenes run down the left, the picked chapter fills a big preview on the
right, and a strip of thumbnails under it skips between chapters. The
preview also washes the whole screen behind everything, crossfading as the
pick moves. Mouse, arrows (Up/Down scene, Left/Right chapter), or the scene
number all work; Enter or a click plays, Esc goes back to the title menu.
"""

import importlib
import math
import traceback

import arcade

from ...config import (
    HEIGHT, PLANK_PAD, TEXT_BRIGHT, TEXT_DIM, TEXT_HOVER, WIDTH,
)
from ...core import audio, textures
from ...core.stage import StageView
from ...core.ui import MenuButton
from .config import STORY

# --- Layout, in canvas units -------------------------------------------------
LIST_LEFT = 56
LIST_W = 360
ROW_H = 70
ROW_GAP = 14
LIST_TOP = 592
FRAME_LEFT = 476
FRAME_W = 748
FRAME_H = FRAME_W * 9 / 16
FRAME_BOTTOM = 196
CAPTION_H = 100
CHIP_W = 138
CHIP_H = CHIP_W * 9 / 16
CHIP_GAP = 14
CHIP_BOTTOM = 70
PLAY_W = 300

ACCENT = (255, 196, 92)
ERROR = (235, 120, 110)
FADE_TIME = 0.28    # preview crossfade
LEAVE_TIME = 0.3    # fade to black before the scene opens


def find_view(module_name, class_name):
    """Return the view class, or None when that scene is not written yet."""
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name == module_name:
            return None
        raise
    return getattr(module, class_name, None)


class StoryView(StageView):
    def __init__(self):
        super().__init__()
        self.background_color = (10, 12, 18)
        self.scene = 0
        self.chapter = 0
        self.clock = 0.0
        self.fade = 1.0
        self.previous = None    # preview being faded out
        self.leaving = None     # (view class, kwargs, label) once Play is hit
        self.leave_clock = 0.0
        self.message = ""
        self.play_button = MenuButton(
            "Play chapter", "play", "play",
            LIST_LEFT + (LIST_W - PLAY_W) / 2, CHIP_BOTTOM - 4, width=PLAY_W,
        )
        self.widgets = [self.play_button]
        self.relayout()

    # --- Picking ------------------------------------------------------------

    @property
    def chapters(self):
        return STORY[self.scene][2]

    def preview_for(self, scene, chapter):
        return textures.preview(STORY[scene][2][chapter][5], self.stage.px(FRAME_W))

    def pick(self, scene, chapter=0):
        scene %= len(STORY)
        chapter = max(0, min(chapter, len(STORY[scene][2]) - 1))
        if (scene, chapter) == (self.scene, self.chapter):
            return
        audio.play("ui_hover")
        self.previous = self.preview_for(self.scene, self.chapter)
        self.fade = 0.0
        self.scene, self.chapter = scene, chapter
        self.message = ""
        self.relayout()

    def launch(self):
        if self.leaving:
            return
        title, _, module_name, class_name, kwargs, _ = self.chapters[self.chapter]
        try:
            view_class = find_view(module_name, class_name)
        except Exception:
            traceback.print_exc()
            view_class = None
        if view_class is None:
            self.message = f"{title} is not available yet."
            self.relayout()
            return
        audio.play("ui_click")
        self.leaving = (view_class, kwargs, title)
        self.leave_clock = 0.0

    def back(self):
        audio.play("ui_click")
        from .view import MenuView
        self.window.show_view(MenuView())

    # --- Layout -------------------------------------------------------------

    def row_rect(self, index):
        top = LIST_TOP - index * (ROW_H + ROW_GAP)
        return LIST_LEFT, top - ROW_H, LIST_W, ROW_H

    def chip_rect(self, index):
        return FRAME_LEFT + index * (CHIP_W + CHIP_GAP), CHIP_BOTTOM, CHIP_W, CHIP_H

    def back_rect(self):
        return WIDTH - 200, HEIGHT - 76, 156, 40

    def relayout(self):
        super().relayout()
        stage = self.stage
        self.row_plank = textures.plank(
            stage.px(LIST_W), stage.px(ROW_H), stage.px(PLANK_PAD), False)
        self.row_plank_hot = textures.plank(
            stage.px(LIST_W), stage.px(ROW_H), stage.px(PLANK_PAD), True)
        self.current = self.preview_for(self.scene, self.chapter)
        self.chip_textures = [
            self.preview_for(self.scene, i) for i in range(len(self.chapters))
        ]

        self.title_text = stage.text(
            "Story", LIST_LEFT, HEIGHT - 58, TEXT_HOVER, 38,
            anchor_y="center", bold=True,
        )
        self.subtitle_text = stage.text(
            "Pick a scene, then skip to any chapter.", LIST_LEFT, HEIGHT - 96,
            TEXT_DIM, 14, anchor_y="center",
        )
        left, bottom, width, height = self.back_rect()
        self.back_text = stage.text(
            "Esc   Back", left + width / 2, bottom + height / 2, TEXT_BRIGHT, 15,
            anchor_x="center", anchor_y="center", bold=True,
        )

        self.row_texts = []
        for index, (name, _, chapters) in enumerate(STORY):
            left, bottom, _, height = self.row_rect(index)
            middle = bottom + height / 2
            count = len(chapters)
            self.row_texts.append((
                stage.text(str(index + 1), left + 34, middle, ACCENT, 28,
                           anchor_x="center", anchor_y="center", bold=True),
                stage.text(name, left + 70, middle + 11, TEXT_BRIGHT, 20,
                           anchor_y="center", bold=True),
                stage.text(f"{count} chapter{'s' if count != 1 else ''}",
                           left + 70, middle - 15, TEXT_DIM, 13, anchor_y="center"),
            ))

        scene_name, scene_blurb, chapters = STORY[self.scene]
        title, blurb = chapters[self.chapter][:2]
        pad = 26
        self.kicker_text = stage.text(
            f"SCENE {self.scene + 1}  ·  {scene_name.upper()}  ·  "
            f"CHAPTER {self.chapter + 1} OF {len(chapters)}",
            FRAME_LEFT + pad, FRAME_BOTTOM + CAPTION_H - 24, ACCENT, 12,
            anchor_y="center", bold=True,
        )
        self.chapter_text = stage.text(
            title, FRAME_LEFT + pad, FRAME_BOTTOM + 46, TEXT_BRIGHT, 26,
            anchor_y="center", bold=True,
        )
        self.blurb_text = stage.text(
            blurb, FRAME_LEFT + pad, FRAME_BOTTOM + 18, TEXT_DIM, 14,
            anchor_y="center",
        )
        self.scene_blurb_text = stage.text(
            scene_blurb, FRAME_LEFT, FRAME_BOTTOM + FRAME_H + 22, TEXT_DIM, 14,
            anchor_y="center",
        )
        self.strip_text = stage.text(
            "CHAPTERS", FRAME_LEFT, CHIP_BOTTOM + CHIP_H + 20, TEXT_DIM, 12,
            anchor_y="center", bold=True,
        )
        self.chip_texts = [
            stage.text(f"{i + 1}  {chapter[0]}",
                       self.chip_rect(i)[0], CHIP_BOTTOM - 16,
                       TEXT_BRIGHT, 12, anchor_y="center")
            for i, chapter in enumerate(chapters)
        ]
        self.footer_text = stage.text(
            self.message or "Up / Down  scene      Left / Right  chapter      "
                            "Enter  play      Esc  back",
            WIDTH / 2, 18, ERROR if self.message else TEXT_DIM, 12,
            anchor_x="center", anchor_y="center",
        )

    # --- Drawing ------------------------------------------------------------

    def draw_backdrop(self):
        """The picked chapter, slowly drifting, washed out behind everything."""
        zoom = 1.06 + 0.03 * math.sin(self.clock * 0.25)
        width = self.stage.window_w * zoom
        height = width * 9 / 16
        if height < self.stage.window_h * zoom:
            height = self.stage.window_h * zoom
            width = height * 16 / 9
        rect = arcade.XYWH(self.stage.window_w / 2, self.stage.window_h / 2,
                           width, height)
        if self.previous is not None and self.fade < 1:
            arcade.draw_texture_rect(self.previous, rect)
        arcade.draw_texture_rect(self.current, rect, alpha=round(255 * self.fade))
        arcade.draw_rect_filled(
            arcade.LBWH(0, 0, self.stage.window_w, self.stage.window_h),
            (8, 10, 16, 190),
        )
        # A darker band under the scene list so it reads over busy art.
        arcade.draw_rect_filled(
            arcade.LBWH(0, 0, self.stage.left + (LIST_LEFT + LIST_W + 30)
                        * self.stage.scale, self.stage.window_h),
            (8, 10, 16, 90),
        )

    def draw_frame(self):
        stage = self.stage
        border = 3
        arcade.draw_rect_filled(
            stage.rect(FRAME_LEFT - border, FRAME_BOTTOM - border,
                       FRAME_W + 2 * border, FRAME_H + 2 * border),
            ACCENT,
        )
        frame = stage.rect(FRAME_LEFT, FRAME_BOTTOM, FRAME_W, FRAME_H)
        if self.previous is not None and self.fade < 1:
            arcade.draw_texture_rect(self.previous, frame)
        arcade.draw_texture_rect(self.current, frame, alpha=round(255 * self.fade))
        arcade.draw_rect_filled(
            stage.rect(FRAME_LEFT, FRAME_BOTTOM, FRAME_W, CAPTION_H),
            (6, 8, 14, 200),
        )
        self.kicker_text.draw()
        self.chapter_text.draw()
        self.blurb_text.draw()
        self.scene_blurb_text.draw()

    def draw_rows(self):
        for index, (number, name, count) in enumerate(self.row_texts):
            left, bottom, width, height = self.row_rect(index)
            picked = index == self.scene
            grow = 6 if picked else 0
            arcade.draw_texture_rect(
                self.row_plank_hot if picked else self.row_plank,
                self.stage.rect(left - PLANK_PAD, bottom - PLANK_PAD - grow / 2,
                                width + 2 * PLANK_PAD + grow,
                                height + 2 * PLANK_PAD + grow),
            )
            if picked:
                arcade.draw_rect_filled(
                    self.stage.rect(left - 14, bottom + 10, 5, height - 20), ACCENT)
            name.color = TEXT_HOVER if picked else TEXT_BRIGHT
            number.draw()
            name.draw()
            count.draw()

    def draw_chips(self):
        self.strip_text.draw()
        for index, texture in enumerate(self.chip_textures):
            left, bottom, width, height = self.chip_rect(index)
            picked = index == self.chapter
            if picked:
                arcade.draw_rect_filled(
                    self.stage.rect(left - 3, bottom - 3, width + 6, height + 6),
                    ACCENT)
            arcade.draw_texture_rect(
                texture, self.stage.rect(left, bottom, width, height),
                color=arcade.types.Color(255, 255, 255) if picked
                else arcade.types.Color(120, 124, 135),
            )
            label = self.chip_texts[index]
            label.color = TEXT_HOVER if picked else TEXT_DIM
            label.draw()

    def on_draw(self):
        self.clear()
        self.draw_backdrop()
        self.title_text.draw()
        self.subtitle_text.draw()
        arcade.draw_rect_filled(
            self.stage.rect(*self.back_rect()), (255, 255, 255, 28))
        self.back_text.draw()
        self.draw_rows()
        self.draw_frame()
        self.draw_chips()
        self.play_button.draw()
        self.footer_text.draw()
        if self.leaving:
            shade = min(1.0, self.leave_clock / LEAVE_TIME)
            arcade.draw_rect_filled(
                arcade.LBWH(0, 0, self.stage.window_w, self.stage.window_h),
                (0, 0, 0, round(255 * shade)),
            )

    def on_update(self, delta_time):
        self.clock += delta_time
        if self.fade < 1:
            self.fade = min(1.0, self.fade + delta_time / FADE_TIME)
        if self.leaving:
            self.leave_clock += delta_time
            # Wait one frame fully black, so the scene's build pause hides.
            if self.leave_clock >= LEAVE_TIME + 0.05:
                view_class, kwargs, title = self.leaving
                try:
                    self.window.show_view(view_class(**kwargs))
                except Exception:
                    traceback.print_exc()
                    self.leaving = None
                    self.message = f"{title} crashed on start, see console."
                    self.relayout()

    # --- Input --------------------------------------------------------------

    @staticmethod
    def inside(rect, x, y):
        left, bottom, width, height = rect
        return left <= x <= left + width and bottom <= y <= bottom + height

    def on_mouse_motion(self, x, y, dx, dy):
        if self.leaving:
            return
        x, y = self.canvas_point(x, y)
        self.play_button.hovered = self.play_button.contains(x, y)
        for index in range(len(STORY)):
            if self.inside(self.row_rect(index), x, y) and index != self.scene:
                self.pick(index)
                return
        for index in range(len(self.chapters)):
            if self.inside(self.chip_rect(index), x, y):
                self.pick(self.scene, index)
                return

    def on_mouse_press(self, x, y, button, modifiers):
        if button != arcade.MOUSE_BUTTON_LEFT or self.leaving:
            return
        x, y = self.canvas_point(x, y)
        if self.inside(self.back_rect(), x, y):
            self.back()
        elif self.play_button.contains(x, y):
            self.launch()
        elif self.inside((FRAME_LEFT, FRAME_BOTTOM, FRAME_W, FRAME_H), x, y):
            self.launch()
        elif any(self.inside(self.chip_rect(i), x, y)
                 for i in range(len(self.chapters))):
            self.launch()

    def on_key_press(self, key, modifiers):
        if self.leaving:
            return
        if key == arcade.key.ESCAPE:
            self.back()
        elif key in (arcade.key.UP, arcade.key.W):
            self.pick(self.scene - 1)
        elif key in (arcade.key.DOWN, arcade.key.S):
            self.pick(self.scene + 1)
        elif key in (arcade.key.LEFT, arcade.key.A):
            self.pick(self.scene, self.chapter - 1)
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self.pick(self.scene, self.chapter + 1)
        elif key in (arcade.key.ENTER, arcade.key.RETURN, arcade.key.SPACE):
            self.launch()
        elif arcade.key.KEY_1 <= key <= arcade.key.KEY_9:
            index = key - arcade.key.KEY_1
            if index < len(STORY):
                self.pick(index)
