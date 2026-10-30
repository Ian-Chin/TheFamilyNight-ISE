"""Achievements page: every scene's achievements, unlocked or still locked.

Scenes run down the left with their own counts; the picked scene's
achievements fill a grid of cards on the right. The total and a progress bar
sit along the top. Hidden achievements read "???" until they are earned.
Up/Down or the scene number picks a scene, Esc goes back to the title menu.
"""

import arcade

from ...config import (
    ACHIEVEMENT_SCENES, HEIGHT, PLANK_PAD, TEXT_BRIGHT, TEXT_DIM, TEXT_HOVER, WIDTH,
)
from ...core import achievements, audio, textures
from ...core.stage import StageView

# --- Layout, in canvas units -------------------------------------------------
LIST_LEFT = 56
LIST_W = 330
ROW_H = 70
ROW_GAP = 14
LIST_TOP = 520
GRID_LEFT = 430
GRID_TOP = 600
CARD_W = 384
CARD_H = 74
CARD_GAP_X = 16
CARD_GAP_Y = 8
COLUMNS = 2
ICON = 40
BAR_LEFT = LIST_LEFT
BAR_W = LIST_W
BAR_Y = 568
BAR_H = 10

ACCENT = (255, 196, 92)
CARD_FILL = (18, 22, 32, 215)
CARD_FILL_LOCKED = (14, 16, 22, 170)
LOCKED_TINT = arcade.types.Color(110, 116, 130)
GOLD = arcade.types.Color(*TEXT_HOVER)


class AchievementsView(StageView):
    def __init__(self):
        super().__init__()
        self.background_color = (10, 12, 18)
        self.backdrop = textures.background("menu-bg.jpg")
        # Open on the first scene that has something to show.
        self.scene = next(
            (i for i, name in enumerate(ACHIEVEMENT_SCENES)
             if achievements.for_scene(name)), 0)
        self.relayout()

    # --- Layout -------------------------------------------------------------

    def row_rect(self, index):
        top = LIST_TOP - index * (ROW_H + ROW_GAP)
        return LIST_LEFT, top - ROW_H, LIST_W, ROW_H

    def card_rect(self, index):
        column, row = index % COLUMNS, index // COLUMNS
        left = GRID_LEFT + column * (CARD_W + CARD_GAP_X)
        top = GRID_TOP - row * (CARD_H + CARD_GAP_Y)
        return left, top - CARD_H, CARD_W, CARD_H

    def back_rect(self):
        return WIDTH - 200, HEIGHT - 76, 156, 40

    def relayout(self):
        super().relayout()
        stage = self.stage
        self.row_plank = textures.plank(
            stage.px(LIST_W), stage.px(ROW_H), stage.px(PLANK_PAD), False)
        self.row_plank_hot = textures.plank(
            stage.px(LIST_W), stage.px(ROW_H), stage.px(PLANK_PAD), True)
        self.medal = textures.icon("medal", stage.px(ICON))
        self.lock = textures.ui_cutout("Lock Symbol.png")

        got, total = achievements.count()
        self.got, self.total = got, total
        self.title_text = stage.text(
            "Achievements", LIST_LEFT, HEIGHT - 58, TEXT_HOVER, 38,
            anchor_y="center", bold=True)
        self.subtitle_text = stage.text(
            "Play well and hunt for the hidden ones.",
            LIST_LEFT, HEIGHT - 96, TEXT_DIM, 14, anchor_y="center")
        self.total_text = stage.text(
            f"{got} / {total} unlocked", BAR_LEFT, BAR_Y + 24, TEXT_BRIGHT, 16,
            anchor_y="center", bold=True)
        self.percent_text = stage.text(
            f"{round(100 * got / total) if total else 0}%", BAR_LEFT + BAR_W,
            BAR_Y + 24, ACCENT, 16, anchor_x="right", anchor_y="center", bold=True)
        left, bottom, width, height = self.back_rect()
        self.back_text = stage.text(
            "Esc   Back", left + width / 2, bottom + height / 2, TEXT_BRIGHT, 15,
            anchor_x="center", anchor_y="center", bold=True)

        self.row_texts = []
        for index, name in enumerate(ACHIEVEMENT_SCENES):
            left, bottom, _, height = self.row_rect(index)
            middle = bottom + height / 2
            scene_got, scene_total = achievements.count(name)
            note = f"{scene_got} / {scene_total}" if scene_total else "Coming soon"
            self.row_texts.append((
                stage.text(str(index + 1), left + 34, middle, ACCENT, 28,
                           anchor_x="center", anchor_y="center", bold=True),
                stage.text(name, left + 70, middle + 11, TEXT_BRIGHT, 20,
                           anchor_y="center", bold=True),
                stage.text(note, left + 70, middle - 15, TEXT_DIM, 13,
                           anchor_y="center"),
            ))

        self.cards = []
        entries = achievements.for_scene(ACHIEVEMENT_SCENES[self.scene])
        for index, (key, _, title, how, hidden) in enumerate(entries):
            left, bottom, _, height = self.card_rect(index)
            done = achievements.unlocked(key)
            if not done and hidden:
                title, how = "???", "Hidden. Keep exploring."
            text_left = left + 18 + ICON + 14
            self.cards.append({
                "done": done,
                "title": stage.text(title, text_left, bottom + height - 22,
                                    TEXT_BRIGHT if done else TEXT_DIM, 16,
                                    anchor_y="center", bold=True),
                "how": stage.text(how, text_left, bottom + height - 36, TEXT_DIM, 11,
                                  anchor_y="top", multiline=True,
                                  width=stage.px(CARD_W - (text_left - left) - 14)),
            })
        self.empty_text = stage.text(
            "No achievements here yet. Coming soon.",
            GRID_LEFT + CARD_W + CARD_GAP_X / 2, GRID_TOP - 120, TEXT_DIM, 16,
            anchor_x="center", anchor_y="center")
        self.footer_text = stage.text(
            "Up / Down  scene      Esc  back", WIDTH / 2, 18, TEXT_DIM, 12,
            anchor_x="center", anchor_y="center")

    # --- Drawing ------------------------------------------------------------

    def draw_backdrop(self):
        texture = self.backdrop
        scale = max(self.window.width / texture.width, self.window.height / texture.height)
        arcade.draw_texture_rect(texture, arcade.XYWH(
            self.window.width / 2, self.window.height / 2,
            texture.width * scale, texture.height * scale))
        arcade.draw_rect_filled(
            arcade.LBWH(0, 0, self.window.width, self.window.height), (8, 10, 16, 200))

    def draw_rows(self):
        for index, (number, name, note) in enumerate(self.row_texts):
            left, bottom, width, height = self.row_rect(index)
            picked = index == self.scene
            grow = 6 if picked else 0
            arcade.draw_texture_rect(
                self.row_plank_hot if picked else self.row_plank,
                self.stage.rect(left - PLANK_PAD, bottom - PLANK_PAD - grow / 2,
                                width + 2 * PLANK_PAD + grow,
                                height + 2 * PLANK_PAD + grow))
            if picked:
                arcade.draw_rect_filled(
                    self.stage.rect(left - 14, bottom + 10, 5, height - 20), ACCENT)
            name.color = TEXT_HOVER if picked else TEXT_BRIGHT
            number.draw()
            name.draw()
            note.draw()

    def draw_bar(self):
        self.total_text.draw()
        self.percent_text.draw()
        arcade.draw_rect_filled(
            self.stage.rect(BAR_LEFT, BAR_Y - BAR_H / 2, BAR_W, BAR_H), (255, 255, 255, 40))
        if self.got:
            arcade.draw_rect_filled(self.stage.rect(
                BAR_LEFT, BAR_Y - BAR_H / 2, BAR_W * self.got / self.total, BAR_H), ACCENT)

    def draw_cards(self):
        if not self.cards:
            self.empty_text.draw()
            return
        for index, card in enumerate(self.cards):
            left, bottom, width, height = self.card_rect(index)
            done = card["done"]
            if done:
                arcade.draw_rect_filled(
                    self.stage.rect(left - 2, bottom - 2, width + 4, height + 4), ACCENT)
            arcade.draw_rect_filled(self.stage.rect(left, bottom, width, height),
                                    CARD_FILL if done else CARD_FILL_LOCKED)
            icon_rect = self.stage.rect(left + 18, bottom + (height - ICON) / 2, ICON, ICON)
            if done:
                arcade.draw_texture_rect(self.medal, icon_rect, color=GOLD)
            else:
                arcade.draw_texture_rect(self.lock, icon_rect, color=LOCKED_TINT)
            card["title"].draw()
            card["how"].draw()

    def on_draw(self):
        self.clear()
        self.draw_backdrop()
        self.title_text.draw()
        self.subtitle_text.draw()
        arcade.draw_rect_filled(self.stage.rect(*self.back_rect()), (255, 255, 255, 28))
        self.back_text.draw()
        self.draw_rows()
        self.draw_bar()
        self.draw_cards()
        self.footer_text.draw()

    # --- Input --------------------------------------------------------------

    @staticmethod
    def inside(rect, x, y):
        left, bottom, width, height = rect
        return left <= x <= left + width and bottom <= y <= bottom + height

    def pick(self, scene):
        scene %= len(ACHIEVEMENT_SCENES)
        if scene != self.scene:
            audio.play("ui_hover")
            self.scene = scene
            self.relayout()

    def back(self):
        audio.play("ui_click")
        from .view import MenuView
        self.window.show_view(MenuView())

    def on_mouse_motion(self, x, y, dx, dy):
        x, y = self.canvas_point(x, y)
        for index in range(len(ACHIEVEMENT_SCENES)):
            if self.inside(self.row_rect(index), x, y):
                self.pick(index)
                return

    def on_mouse_press(self, x, y, button, modifiers):
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        if self.inside(self.back_rect(), *self.canvas_point(x, y)):
            self.back()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            self.back()
        elif key in (arcade.key.UP, arcade.key.W):
            self.pick(self.scene - 1)
        elif key in (arcade.key.DOWN, arcade.key.S):
            self.pick(self.scene + 1)
        elif arcade.key.KEY_1 <= key <= arcade.key.KEY_9:
            index = key - arcade.key.KEY_1
            if index < len(ACHIEVEMENT_SCENES):
                self.pick(index)
