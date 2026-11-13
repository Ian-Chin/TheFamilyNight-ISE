import functools

import arcade
import PIL.Image

from ...config import (
    HEIGHT, PLANK_PAD, TEXT_BRIGHT, TEXT_HOVER, UI_DIR, WIDTH,
)
from ...core import textures
from . import highway_art
from .config import ALERT_ICONS, INGREDIENTS

BREAD_ART = "bus-scene/ingredients-v4/bread-three-segments.png"
CARD_ART = "bus-scene/ingredients-v4/card-{}.png"
ICON_ART = "bus-scene/pixel-v3/warning-{}.png"

LIVES_PLATE = (24, HEIGHT - 84, 250, 62)
ALERTS_PLATE = (24, HEIGHT - 142, 250, 46)
TRIP_PLATE = (WIDTH / 2 - 215, HEIGHT - 68, 430, 46)
TRIP_BAR = (TRIP_PLATE[0] + 110, TRIP_PLATE[1] + 17, 222, 12)
SHOP_PLATE = (WIDTH - 24 - 270, HEIGHT - 104, 270, 82)
CARD_H = 58
BAR_TRACK = (255, 255, 255, 46)
BAR_FILL = (226, 186, 112)
RED = (230, 80, 80)


@functools.lru_cache(maxsize=1)
def bread_textures():
    return [arcade.Texture(image) for image in highway_art.bread_states(UI_DIR / BREAD_ART)]


@functools.lru_cache(maxsize=16)
def art(path, height, trim):
    with PIL.Image.open(UI_DIR / path) as source:
        image = source.convert("RGBA")
    if trim:
        image = image.crop(image.getchannel("A").point(lambda v: 255 if v >= 100 else 0).getbbox())
    width = max(1, round(height * image.width / image.height))
    return arcade.Texture(image.resize((width, height), PIL.Image.LANCZOS))


class BusHud:
    def __init__(self, label="ROUND 1", alerts=False):
        self.label = label
        self.alerts = alerts          # show the four warning icons
        self.lives = 3
        self.damaged = set()          # ingredient indexes crossed out
        self.alert = None             # the warning icon lit up, if any
        self.share = 0.0              # how far along, 0 to 1
        self.note = ""                # text at the right of the trip plate
        self.stage = None

    def layout(self, stage):
        self.stage = stage
        pad = stage.px(PLANK_PAD)
        boxes = [LIVES_PLATE, TRIP_PLATE, SHOP_PLATE] + ([ALERTS_PLATE] if self.alerts else [])
        self.plates = [
            (box, textures.hud_plate(stage.px(box[2]), stage.px(box[3]), pad, False))
            for box in boxes
        ]
        left, bottom, width, height = TRIP_PLATE
        middle = bottom + height / 2
        self.label_text = stage.text(
            self.label, left + 18, middle, TEXT_HOVER, 13, bold=True, anchor_y="center",
        )
        self.note_text = stage.text(
            self.note, left + width - 18, middle, TEXT_BRIGHT, 14,
            bold=True, anchor_x="right", anchor_y="center",
        )
        self.icons = [art(ICON_ART.format(name), stage.px(34), True) for name in ALERT_ICONS]
        self.cards = [art(CARD_ART.format(name), stage.px(CARD_H), True) for name in INGREDIENTS]

    def draw(self):
        stage = self.stage
        for (left, bottom, width, height), plate in self.plates:
            arcade.draw_texture_rect(plate, stage.rect(
                left - PLANK_PAD, bottom - PLANK_PAD,
                width + 2 * PLANK_PAD, height + 2 * PLANK_PAD,
            ))

        bread = bread_textures()[max(0, self.lives)]
        left, bottom, width, height = LIVES_PLATE
        bread_w = width - 28
        bread_h = bread_w * bread.height / bread.width
        arcade.draw_texture_rect(bread, stage.rect(
            left + 14, bottom + (height - bread_h) / 2, bread_w, bread_h,
        ), pixelated=True)

        left, bottom, width, height = TRIP_BAR
        arcade.draw_rect_filled(stage.rect(left, bottom, width, height), BAR_TRACK)
        if self.share > 0:
            arcade.draw_rect_filled(
                stage.rect(left, bottom, width * min(1.0, self.share), height), BAR_FILL,
            )
        if self.note_text.text != self.note:
            self.note_text.text = self.note
        self.label_text.draw()
        self.note_text.draw()

        left, bottom, width, height = SHOP_PLATE
        slot = (width - 20) / len(self.cards)
        for index, card in enumerate(self.cards):
            ratio = card.width / card.height
            card_w = CARD_H * ratio
            x = left + 10 + slot * index + (slot - card_w) / 2
            y = bottom + (height - CARD_H) / 2
            arcade.draw_texture_rect(card, stage.rect(x, y, card_w, CARD_H), pixelated=True)
            if index in self.damaged:
                for a, b in (((x + 4, y + 6), (x + card_w - 4, y + CARD_H - 6)),
                             ((x + card_w - 4, y + 6), (x + 4, y + CARD_H - 6))):
                    arcade.draw_line(*stage.to_screen(*a), *stage.to_screen(*b),
                                     RED, max(2, 4 * stage.scale))

        if self.alerts:
            left, bottom, width, height = ALERTS_PLATE
            for index, icon in enumerate(self.icons):
                ratio = icon.width / icon.height
                x = left + 20 + index * 58
                arcade.draw_texture_rect(icon, stage.rect(x, bottom + 8, 34 * ratio, 34),
                                         pixelated=True)
                if self.alert == index:
                    arcade.draw_rect_filled(
                        stage.rect(x - 2, bottom + 4, 34 * ratio + 4, 3), TEXT_HOVER,
                    )
