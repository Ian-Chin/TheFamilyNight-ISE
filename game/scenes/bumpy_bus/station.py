"""The bus station: talk to the officer, then walk to the door and board.

Built like the walking scenes: Terry and the officer are sprites with ground
shadows, the same footsteps and dust, the shared dialogue box, portraits and
interact prompts. Boarding sweeps the bus across the screen, and the cabin
behind it is round 1.
"""

import functools
import math

import arcade
import PIL.Image

from ...config import (
    ASSETS, FEET_HEIGHT, HEIGHT, TERRY_HEIGHT, TEXT_BRIGHT, WIDTH,
)
from ...core import achievements, audio, textures
from ...core.audio import Footsteps
from ...core.dialogue import DialogBox
from ...core.effects import WalkDust
from ...core.sprites import Character, Terry
from ...core.widgets import InteractPrompt, Portraits, TitleCard
from .base import BusView
from .cabin import Cabin
from .config import (
    ARROW, ARROW_H, BOARD_ZONE, CABIN_BOTTOM, CABIN_DARK, CABIN_SIZE, DEPARTURE_TIME,
    OFFICER_H, OFFICER_LINES, OFFICER_NAME, OFFICER_RANGE, OFFICER_X, STATION_BG,
    STATION_FEET_Y, STATION_HINT, STATION_KICKER, STATION_START_X, STATION_TAGLINE,
    STATION_TITLE, STATION_WALK, WIPE_H,
)
from .hud import BusHud

OFFICER_ART = "sprites/bus-scene/npcs/police.png"
ARROW_ART = "backgrounds/bus-scene/waiting_bus/start-arrow-down.png"
WIPE_ART = "sprites/bus-scene/transitions/bus-top-down-right.png"
EVERYWHERE = ((0, WIDTH, 0, HEIGHT),)     # the whole pavement rings as stone


@functools.lru_cache(maxsize=8)
def trimmed(path):
    """A picture with its transparent margin cut off."""
    with PIL.Image.open(ASSETS / path) as source:
        image = source.convert("RGBA")
    box = image.getchannel("A").point(lambda v: 255 if v >= 100 else 0).getbbox()
    return arcade.Texture(image.crop(box) if box else image)


class BusStationView(BusView):
    def __init__(self):
        super().__init__("Try Again", "")
        self.background = textures.background(STATION_BG)
        # The cabin is read in the background now, ready for the wipe.
        self.cabin = Cabin()

        feet = STATION_FEET_Y
        self.terry = Terry(STATION_START_X, feet + TERRY_HEIGHT / 2)
        self.officer_texture = trimmed(OFFICER_ART)
        self.officer = Character(
            self.officer_texture, OFFICER_H, OFFICER_X, feet + OFFICER_H / 2,
        )
        self.sprites = arcade.SpriteList()
        self.sprites.append(self.officer)
        self.sprites.append(self.terry)

        arrow = trimmed(ARROW_ART)
        self.arrow = arcade.Sprite(arrow, scale=ARROW_H / arrow.height)
        self.arrow.center_x = ARROW[0]
        self.arrows = arcade.SpriteList()
        self.arrows.append(self.arrow)
        self.wipe = trimmed(WIPE_ART)

        half_w, half_h = abs(self.terry.width) / 2, abs(self.terry.height) / 2
        ground = self.terry.ground_y
        self.bounds = (
            STATION_WALK[0] - half_w, STATION_WALK[1] + half_w, ground - half_h, ground + half_h,
        )
        # The officer is solid at the feet, so Terry walks round rather than through.
        self.obstacles = ((OFFICER_X - 26, OFFICER_X + 26, feet - 6, feet + FEET_HEIGHT + 6),)

        self.footsteps = Footsteps(EVERYWHERE)
        self.dust = WalkDust(EVERYWHERE)
        self.talk_prompt = InteractPrompt("Talk")
        self.board_prompt = InteractPrompt("Board")
        self.dialog = DialogBox()
        self.portraits = Portraits(textures.terry_frames(glow=False)[2][0])
        self.title_card = TitleCard(STATION_KICKER, STATION_TITLE, STATION_TAGLINE)
        self.hud = BusHud("BUS STOP")
        self.hud.note = "Find the bus"
        self.widgets += [
            self.dialog, self.portraits, self.talk_prompt, self.board_prompt,
            self.title_card, self.hud,
        ]

        self.mode = "title"
        self.line = None             # which of the officer's lines is up
        self.clock = 0.0
        self.departure = 0.0
        self.typing_player = None
        self.relayout()

    def relayout(self):
        super().relayout()
        self.hint = self.stage.text(
            STATION_HINT, WIDTH / 2, 26, TEXT_BRIGHT, 14, anchor_x="center", anchor_y="center",
        )

    # --- State --------------------------------------------------------------

    @property
    def talking(self):
        return self.dialog.visible

    @property
    def near_officer(self):
        return (self.mode == "walk" and not self.talking and not self.terry.jumping
                and abs(self.terry.center_x - OFFICER_X) <= OFFICER_RANGE)

    @property
    def can_board(self):
        return (self.mode == "walk" and not self.talking and not self.terry.jumping
                and BOARD_ZONE[0] <= self.terry.center_x <= BOARD_ZONE[1])

    def on_hide_view(self):
        super().on_hide_view()
        self.stop_typing()

    def stop_typing(self):
        if self.typing_player is not None:
            audio.bank().stop(self.typing_player)
            self.typing_player = None

    # --- Officer ------------------------------------------------------------

    def talk(self):
        self.held.clear()
        self.line = 0
        # Terry turns to face the officer.
        facing = -1 if self.terry.center_x > OFFICER_X else 1
        self.terry.scale_x = abs(self.terry.scale_x) * facing
        self.say()

    def say(self):
        audio.play("dialog_open")
        self.dialog.open(OFFICER_NAME, OFFICER_LINES[self.line], "right")
        self.typing_player = audio.play("dialog_type", loop=True)

    def advance(self):
        self.stop_typing()
        if not self.dialog.advance():
            return
        self.line += 1
        if self.line < len(OFFICER_LINES):
            self.say()
        else:
            self.line = None
            achievements.unlock("egg_bus_officer")

    def board(self):
        self.held.clear()
        self.mode = "departure"
        self.departure = 0.0
        audio.play("bus_engine")
        achievements.unlock("bus_board")

    # --- Frame --------------------------------------------------------------

    def on_update(self, delta_time):
        self.music.update(delta_time)
        self.talk_prompt.update(delta_time)
        self.board_prompt.update(delta_time)
        if self.held_up:
            return
        delta_time = min(delta_time, 1 / 30)
        self.clock += delta_time

        if self.mode == "title":
            self.title_card.update(delta_time)
            if self.title_card.finished:
                self.mode = "walk"
            return
        if self.mode == "departure":
            self.departure += delta_time
            if self.departure >= DEPARTURE_TIME:
                from .ride import BusRideView
                self.go(BusRideView(self.cabin))
            return

        self.arrow.center_y = ARROW[1] + math.sin(self.clock * 4) * 6
        if self.talking:
            self.dialog.update(delta_time)
            if not self.dialog.typing:
                self.stop_typing()
            dx = 0
        else:
            dx = (any(k in self.held for k in (arcade.key.D, arcade.key.RIGHT))
                  - any(k in self.held for k in (arcade.key.A, arcade.key.LEFT)))
        was_jumping = self.terry.jumping
        self.terry.update_movement(delta_time, dx, 0, self.bounds, self.obstacles)
        if was_jumping and not self.terry.jumping:
            audio.play("bus_land")
        moving = bool(dx) and not self.terry.jumping
        self.footsteps.update(delta_time, moving, self.terry.center_x, self.terry.ground_y)
        feet = self.terry.ground_y - abs(self.terry.height) / 2
        self.dust.update(delta_time, moving, self.terry.center_x, feet, dx, 0)
        # The officer bobs on the spot, unless Terry is talking to him.
        bob = 0 if self.talking else abs(math.sin(self.clock * 3)) * 3
        self.officer.center_y = self.officer.ground_y + bob

    # --- Drawing ------------------------------------------------------------

    def draw_wipe(self, progress):
        """The bus sweeps right; the cabin shows behind it."""
        stage = self.stage
        width = self.wipe.width * WIPE_H / self.wipe.height
        x = -width + (WIDTH + width) * progress
        reveal = max(0, min(WIDTH, x + 64))
        context = self.window.ctx
        previous = context.scissor
        ratio = self.window.get_pixel_ratio()
        try:
            context.scissor = (
                round(stage.left * ratio), round(stage.bottom * ratio),
                round(reveal * stage.scale * ratio), round(stage.height * ratio),
            )
            arcade.draw_rect_filled(arcade.LBWH(0, 0, WIDTH, HEIGHT), CABIN_DARK)
            arcade.draw_texture_rect(
                self.cabin.at("idle", 0),
                arcade.LBWH(0, CABIN_BOTTOM, *CABIN_SIZE), pixelated=True,
            )
        finally:
            context.scissor = previous
        arcade.draw_texture_rect(
            self.wipe, arcade.LBWH(x, (HEIGHT - WIPE_H) / 2, width, WIPE_H), pixelated=True,
        )

    def on_draw(self):
        self.clear()
        self.camera.use()
        arcade.draw_texture_rect(self.background, arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT))
        self.officer.draw_shadow()
        self.terry.draw_shadow()
        self.dust.draw()
        if self.mode != "departure":
            self.arrows.draw(pixelated=True)
        self.sprites.draw(pixelated=True)
        if self.mode == "departure":
            self.draw_wipe(min(1.0, self.departure / DEPARTURE_TIME))

        self.window.default_camera.use()
        self.hud.draw()
        if self.mode == "walk" and not self.talking:
            self.hint.draw()
            if self.near_officer:
                self.talk_prompt.draw(OFFICER_X, STATION_FEET_Y + OFFICER_H + 8)
            elif self.can_board:
                self.board_prompt.draw(ARROW[0], ARROW[1] + ARROW_H / 2 + 8)
        self.title_card.draw()
        if self.talking:
            self.portraits.draw(partner=self.officer_texture, speaking="right")
            self.dialog.draw()
        self.draw_menus()

    # --- Input --------------------------------------------------------------

    def click(self, x, y, button):
        if self.mode == "walk" and self.talking and button == arcade.MOUSE_BUTTON_LEFT:
            self.advance()

    def key_down(self, key):
        enter =key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.RETURN)
        if self.mode == "title":
            if key == arcade.key.SPACE or enter:
                self.title_card.skip()
            return
        if self.mode != "walk":
            return
        if self.talking:
            if enter or key == arcade.key.SPACE:
                self.advance()
            return
        if enter:
            if self.near_officer:
                self.talk()
            elif self.can_board:
                self.board()
        elif key == arcade.key.SPACE:
            if not self.terry.jumping:
                self.terry.start_jump()
                audio.play("bus_jump")
        else:
            super().key_down(key)
