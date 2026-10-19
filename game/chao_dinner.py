"""The Chao family dinner scene.

Terry walks in down the night garden path while the opening black fades away.
As he walks, the "Scene 4 / Chao Dinner" title drifts up over a blurred
garden and fades off again; once he has settled by the dinner table he says
his opening line. The player takes over from there: a quest panel in the top
right asks him to start the dinner at the table (marked with a "!"), and
walking up to the table or to a family member brings up an
"Interact [Enter]" prompt. Talking to someone plays a short exchange with
Terry standing on the left of the dialogue box and them on the right.

Terry arrives to find the family already there, and pulls a shocked face
with a few hops before his opening lines.

Once the kids are dealt with, the clock skips on half an hour. The family
are full and head off, leaving Terry alone with a table of food; he gets up,
and the table now offers the leftover feast typing game (feast_typing.py),
which the player can start straight away or after a wander.

Setting up the dinner at the table first asks whether to start the mini game.
Going ahead fades the food onto the table, dips to black and comes back up
with the whole family sat on the stools round it, tucking in. A little table
talk later, Jess and Tom run off, and the player has to keep catching them
and sending them back to their seats until the clock runs out
(see chao_kids.py).
"""

import math

import arcade

from . import textures
from . import audio
from .audio import Footsteps
from .backdrop import Backdrop
from .art.keying import solid_bbox
from .chao_kids import KidsGame
from .chao_widgets import (
    InteractPrompt, KidsHud, Portraits, QuestPanel, TitleCard,
)
from .config import (
    CHAO_AFTER_GAME_DIALOG, CHAO_ALONE_DIALOG, CHAO_ALONE_SPOT,
    CHAO_FEAST_ITEMS, CHAO_FEAST_MESSAGE, CHAO_FEAST_PROMPT, CHAO_FEAST_TITLE,
    CHAO_FULL_DIALOG, CHAO_LEAVE_FADE, CHAO_LEFTOVER_QUESTS, CHAO_SKIP_FADE,
    CHAO_SKIP_HOLD, CHAO_SKIP_TEXT, CHAO_DINNER_BG, CHAO_DINNER_SERVED_BG,
    CHAO_ENTRY_Y, CHAO_FADE_IN, CHAO_MARK_BOB, CHAO_MARK_BOB_TIME,
    CHAO_NPC_DIALOG, CHAO_NPCS, CHAO_OBSTACLES, CHAO_PATH_X, CHAO_SEAT_FADE,
    CHAO_SEATED_HOLD, CHAO_SEATS, CHAO_SERVE_FADE, CHAO_SERVE_HOLD,
    CHAO_SETUP_ITEMS, CHAO_SETUP_MESSAGE, CHAO_SETUP_TITLE, CHAO_SHOCK_DIALOG,
    CHAO_SHOCK_HOP, CHAO_SHOCK_HOP_TIME, CHAO_SHOCK_HOPS, CHAO_SHOCK_LEAD,
    CHAO_STONE_AREAS, CHAO_STOP_Y, CHAO_ZOOM, CHAO_ZOOM_ORIGIN, CHAO_TABLE_MARK, CHAO_TABLE_MARK_H,
    CHAO_TABLE_MARK_POS, CHAO_TABLE_PROMPT, CHAO_TABLE_RANGE, CHAO_TABLE_TALK,
    CHAO_TALK_RANGE, CHAO_TITLE_BLUR, CHAO_WALK_BOUNDS, HEIGHT,
    KIDS_GOOD_SHARE, KIDS_LOSE_ITEMS, KIDS_LOSE_TITLE, KIDS_RESULT_MESSAGE,
    KIDS_RETRY_MESSAGE, KIDS_WIN_ITEMS, KIDS_WIN_TITLE, TERRY_HEIGHT,
    TEXT_BRIGHT, TEXT_HOVER, TEXT_SHADOW, WIDTH,
)
from .dialogue import DialogBox
from .effects import WalkDust
from .options import SettingsPanel
from .pause import PauseMenu
from .sprites import NPC, Diner, Terry
from .views import StageView

# --- HUD, parked ------------------------------------------------------------
# The day cycle badge, settings, backpack and map are built and working in
# game/hud.py, but kept out of the scene for now. To put them back, uncomment
# the four blocks marked "HUD:" below and these two imports.
# from .config import PANEL_H, PANEL_W
# from .hud import HUD
# from .ui import Card

TABLE = CHAO_OBSTACLES[0]   # (left, right, bottom, top) of the dinner table


def cover_rect(texture, rect):
    """Fill `rect` with `texture` without distorting it."""
    scale = max(rect.width / texture.width, rect.height / texture.height)
    return arcade.XYWH(
        rect.x, rect.y, texture.width * scale, texture.height * scale
    )


def distance_to_box(x, y, box):
    left, right, bottom, top = box
    dx = max(left - x, 0, x - right)
    dy = max(bottom - y, 0, y - top)
    return math.hypot(dx, dy)


class ChaoDinnerView(StageView):
    """Scripted entrance, then free roaming with quests and interactions."""

    def __init__(self):
        super().__init__()
        self.backdrop = Backdrop(CHAO_DINNER_BG)
        self.served = Backdrop(CHAO_DINNER_SERVED_BG)
        # Cut everyone into seated parts now, not under the dip to black.
        seated_art = {name: art for name, art, *_ in CHAO_NPCS}
        for name, *_ in CHAO_SEATS:
            textures.diner_parts(seated_art.get(name, name))
        self.blurred = textures.blurred_background(CHAO_DINNER_BG, CHAO_TITLE_BLUR)
        self.table_mark = textures.ui_cutout(CHAO_TABLE_MARK)

        # The night garden is dark enough that the pale halo around the
        # characters reads as a glow, so this scene draws them without it.
        self.terry = Terry(CHAO_PATH_X, CHAO_ENTRY_Y, glow=False)
        self.npcs = [NPC(*entry, glow=False) for entry in CHAO_NPCS]
        self.sprites = arcade.SpriteList()
        for character in (self.terry, *self.npcs):
            self.sprites.append(character)
        self.sort_by_depth()

        self.footsteps = Footsteps(CHAO_STONE_AREAS)
        self.dust = WalkDust(CHAO_STONE_AREAS)
        self.typing_player = None
        self.script = []      # lines still to come in the current exchange
        self.partner = None   # the NPC Terry is talking to, if any

        self.clock = 0.0
        self.fade_clock = 0.0
        self.walking_in = True
        self.opening_pending = False   # Terry is in place, the title is not done
        # What Enter would interact with: ("table", None), ("npc", npc) or None.
        self.target = None
        self.talked = set()
        self.dinner_started = False
        # Seconds since the dinner was started, while the food and the
        # family are being brought on; None before and after.
        self.serve_clock = None
        self.diners = None   # the family at the table, once they are seated
        self.diner_by_name = {}
        self.kids = None     # the mini game, once the family is seated
        self.game_over = False
        # Called once the current run of dialogue lines is finished.
        self.after_script = None
        self.held = set()
        # A dip to black with something done under it, or None. See start_dip.
        self.dip = None
        # Everyone has gone and Terry is up again, with the food to finish.
        self.leftovers = False

        # Terry's shocked face, sized so his body matches the idle art and
        # stood on the same spot. Seconds since it came up, or None.
        self.shock_clock = None
        self.shocked = False
        self.shocked_face = textures.terry_shocked()
        idle = textures.terry_frames(glow=False)[2][0]
        idle_box = solid_bbox(idle.image)
        idle_scale = TERRY_HEIGHT / idle.height
        shock_box = solid_bbox(self.shocked_face.image)
        shock_scale = (idle_box[3] - idle_box[1]) * idle_scale / (shock_box[3] - shock_box[1])
        self.shock_w = self.shocked_face.width * shock_scale
        self.shock_h = self.shocked_face.height * shock_scale
        # Sprite bottom to the shoes, for each, so the shoes stay planted.
        self.shock_drop = ((idle.height - idle_box[3]) * idle_scale
                           - (self.shocked_face.height - shock_box[3]) * shock_scale)

        self.panel = None   # the label of the open HUD popup, or None
        self.title_card = TitleCard()
        self.prompt = InteractPrompt()
        self.table_prompt = InteractPrompt(CHAO_TABLE_PROMPT)
        self.quests = QuestPanel()
        self.quests.set_progress("family", f"0/{len(self.npcs)}")
        self.terry_portrait = textures.terry_frames(glow=False)[2][0]
        self.portraits = Portraits(self.terry_portrait)
        self.dialog = DialogBox()
        self.setup_card = PauseMenu(
            CHAO_SETUP_ITEMS, CHAO_SETUP_TITLE, CHAO_SETUP_MESSAGE, width=440,
        )
        # Seated enough of the time, the scene carries on; short of
        # KIDS_GOOD_SHARE, the only way is to try the mini game again.
        self.win_card = PauseMenu(
            KIDS_WIN_ITEMS, KIDS_WIN_TITLE,
            KIDS_RESULT_MESSAGE.format(share=100), width=460,
        )
        self.lose_card = PauseMenu(
            KIDS_LOSE_ITEMS, KIDS_LOSE_TITLE,
            KIDS_RETRY_MESSAGE.format(share=100, need=100), width=700,
        )
        self.feast_card = PauseMenu(
            CHAO_FEAST_ITEMS, CHAO_FEAST_TITLE, CHAO_FEAST_MESSAGE, width=480,
        )
        self.kids_hud = KidsHud()
        self.pause_menu = PauseMenu()
        self.settings_panel = SettingsPanel()
        self.widgets = [
            self.title_card, self.prompt, self.table_prompt, self.quests,
            self.portraits, self.dialog, self.setup_card, self.win_card,
            self.lose_card, self.feast_card,
            self.kids_hud, self.pause_menu, self.settings_panel,
        ]
        # HUD: build it and lay it out with the other widgets.
        # self.hud = HUD()
        # self.placeholder = Card(PANEL_W, PANEL_H, "", ["Nothing here yet."])
        # self.widgets = [self.hud, self.placeholder, self.pause_menu]

        # The camera projects the fixed canvas into the letterboxed stage, so
        # Terry's coordinates stay in canvas units whatever the window size.
        self.camera = arcade.camera.Camera2D(
            position=(WIDTH / 2, HEIGHT / 2),
            projection=arcade.LRBT(-WIDTH / 2, WIDTH / 2, -HEIGHT / 2, HEIGHT / 2),
            viewport=self.stage.viewport(),
        )
        self.zoomed = False   # the camera has closed in on the table
        self.relayout()

    def on_show_view(self):
        audio.ambience().start()

    def on_hide_view(self):
        self.backdrop.stop()
        self.served.stop()
        # The garden is the only place with birds, so they leave with it.
        audio.ambience().stop()
        self.stop_typing_sound()

    def sort_by_depth(self):
        """Back to front, so whoever stands lower down overlaps the rest."""
        self.sprites.sort(key=lambda sprite: -sprite.ground_y)

    def relayout(self):
        super().relayout()
        self.camera.viewport = self.stage.viewport()
        self.hint = self.stage.text(
            "WASD to move    Space to jump    Enter to interact    Esc to pause",
            WIDTH / 2, 26, (238, 240, 246), 14,
            anchor_x="center", anchor_y="center",
        )
        self.skip_texts = [
            self.stage.text(
                CHAO_SKIP_TEXT, WIDTH / 2 + offset, HEIGHT / 2 - 90 - offset,
                shade, 30, anchor_x="center", anchor_y="center", italic=True,
            )
            for offset, shade in ((2, TEXT_SHADOW), (0, TEXT_BRIGHT))
        ]

    def zoom_in(self):
        """Close the camera in on the table, so CHAO_ZOOM_VIEW fills the stage."""
        self.zoomed = True
        left, bottom = CHAO_ZOOM_ORIGIN
        self.camera.position = (left + WIDTH / CHAO_ZOOM / 2,
                                bottom + HEIGHT / CHAO_ZOOM / 2)
        self.camera.zoom = CHAO_ZOOM

    def scene_point(self, x, y):
        """Window pixels to scene units, through the camera's zoom."""
        x, y = self.canvas_point(x, y)
        if not self.zoomed:
            return x, y
        left, bottom = CHAO_ZOOM_ORIGIN
        return left + x / CHAO_ZOOM, bottom + y / CHAO_ZOOM

    def scene_to_screen(self, x, y):
        if self.zoomed:
            left, bottom = CHAO_ZOOM_ORIGIN
            x, y = (x - left) * CHAO_ZOOM, (y - bottom) * CHAO_ZOOM
        return self.stage.to_screen(x, y)

    @property
    def fade_alpha(self):
        if self.fade_clock >= CHAO_FADE_IN:
            return 0
        return round(255 * (1 - self.fade_clock / CHAO_FADE_IN))

    @property
    def serve_share(self):
        """How far the food has faded onto the table, 0 to 1."""
        if self.diners is not None:
            return 1.0
        if self.serve_clock is None:
            return 0.0
        return min(self.serve_clock / CHAO_SERVE_FADE, 1.0)

    @property
    def seat_alpha(self):
        """The black dipped to while everyone takes their seat."""
        if self.serve_clock is None:
            return 0
        t = self.serve_clock - CHAO_SERVE_FADE - CHAO_SERVE_HOLD
        if t <= 0 or t >= 2 * CHAO_SEAT_FADE:
            return 0
        return round(255 * (1 - abs(t - CHAO_SEAT_FADE) / CHAO_SEAT_FADE))

    @property
    def dip_alpha(self):
        if self.dip is None:
            return 0
        t, fade, hold = self.dip["clock"], self.dip["fade"], self.dip["hold"]
        if t < fade:
            return round(255 * t / fade)
        if t < fade + hold:
            return 255
        return round(255 * max(0.0, 1 - (t - fade - hold) / fade))

    @property
    def card_open(self):
        """The set-up question or the results are up, holding the scene."""
        return any(card.visible for card in self.cards)

    @property
    def cards(self):
        return (self.setup_card, self.win_card, self.lose_card, self.feast_card)

    @property
    def entrance_over(self):
        return not self.walking_in and not self.opening_pending

    @property
    def playing(self):
        """True while Terry is free to roam: after the entrance, outside any
        dialogue, and before he sits down to dinner."""
        return (self.entrance_over and not self.dialog.visible
                and not self.dinner_started)

    # --- drawing ------------------------------------------------------------

    def mark_center(self):
        x, y = CHAO_TABLE_MARK_POS
        bob = math.sin(self.clock * 2 * math.pi / CHAO_MARK_BOB_TIME)
        return x, y + bob * CHAO_MARK_BOB

    def mark_width(self):
        return CHAO_TABLE_MARK_H * self.table_mark.width / self.table_mark.height

    def target_tip(self):
        """Canvas point the interact prompt points down at."""
        kind, npc = self.target
        if kind == "table":
            x, y = CHAO_TABLE_MARK_POS
            return x, y + CHAO_TABLE_MARK_H / 2 + CHAO_MARK_BOB
        return npc.center_x, npc.ground_y + abs(npc.height) / 2

    def on_draw(self):
        self.clear()
        viewport = self.stage.viewport()
        background = self.backdrop.texture
        if self.zoomed:
            # Closed in, the backdrop goes through the camera with everyone
            # else; the camera's viewport crops what falls off the stage.
            self.camera.use()
            canvas = arcade.LBWH(0, 0, WIDTH, HEIGHT)
            arcade.draw_texture_rect(background, cover_rect(background, canvas))
        else:
            arcade.draw_texture_rect(background, cover_rect(background, viewport))
        # Until the family sits down, the table with the food on it is a
        # second backdrop faded in over the bare one.
        served = self.serve_share
        if served > 0 and self.diners is None:
            food = self.served.texture
            arcade.draw_texture_rect(
                food, cover_rect(food, viewport), alpha=round(255 * served),
            )

        self.camera.use()
        if self.diners is not None:
            # The kids out running are sorted in with the family at the
            # table, so they pass in front of and behind the stools. A kid
            # being carried is in the player's hand, so they and the box to
            # drop them on go over everyone.
            carried = self.kids.carried if self.kids is not None else None
            people = list(self.diners)
            if self.kids is not None:
                people += [r for r in self.kids.runners if r is not carried]
            for person in sorted(people, key=lambda p: -p.ground_y):
                person.draw()
            if carried is not None:
                self.kids.draw_targets()
                carried.draw()
        else:
            for character in self.sprites:
                character.draw_shadow()
            # Kicked up behind the feet, so the legs are drawn over it.
            self.dust.draw()
            self.sprites.draw(pixelated=True)
            if self.shocked:
                self.draw_shocked()
        if not self.dinner_started:
            x, y = self.mark_center()
            arcade.draw_texture_rect(
                self.table_mark,
                arcade.XYWH(x, y, self.mark_width(), CHAO_TABLE_MARK_H),
                pixelated=True,
            )
        self.window.default_camera.use()

        # The garden, characters and all, softens behind the title card. The
        # blurred still is not quite opaque, so the family show faintly
        # through it, under the words.
        blur = self.title_card.share
        if blur > 0:
            arcade.draw_texture_rect(
                self.blurred, cover_rect(self.blurred, viewport),
                alpha=round(235 * blur),
            )

        if self.entrance_over and not self.game_running:
            self.quests.draw()
        if self.game_running:
            self.kids_hud.draw(
                self.kids.time_left, self.kids.seated, len(self.kids.runners),
            )
        if self.playing and not self.card_open:
            self.hint.draw()
            if self.target is not None:
                prompt = self.table_prompt if self.target[0] == "table" else self.prompt
                prompt.draw(*self.target_tip())
            # HUD: drawn once the scripted entrance is over, and under the fade
            # so the opening black covers it too.
            # self.hud.draw()
            # if self.panel:
            #     self.placeholder.set_title(self.panel)
            #     self.placeholder.draw()

        alpha = max(self.fade_alpha, self.seat_alpha, self.dip_alpha)
        if alpha:
            arcade.draw_rect_filled(
                arcade.LBWH(0, 0, self.window.width, self.window.height),
                (0, 0, 0, alpha),
            )
        if self.dip is not None and self.dip["time_skip"]:
            self.draw_time_skip(self.dip_alpha)
        self.title_card.draw()

        if self.dialog.visible:
            partner = self.partner.texture if self.partner else None
            self.portraits.draw(partner, self.dialog.side)
        self.dialog.draw()
        for card in self.cards:
            card.draw()
        # Settings is reached through the pause menu, which stays open behind
        # it; the glass is see-through enough that both at once is a mess.
        if not self.settings_panel.visible:
            self.pause_menu.draw()
        self.settings_panel.draw()

    def draw_time_skip(self, alpha):
        """A clock face with its hands spinning round, over the black."""
        stage = self.stage
        s = stage.scale
        x, y = stage.to_screen(WIDTH / 2, HEIGHT / 2 + 20)
        radius = 70 * s
        rim = (*TEXT_HOVER, alpha)
        arcade.draw_circle_filled(x, y, radius, (20, 22, 30, alpha))
        arcade.draw_circle_outline(x, y, radius, rim, 5 * s)
        for hour in range(12):
            angle = hour * math.pi / 6
            inner = radius * (0.78 if hour % 3 else 0.68)
            arcade.draw_line(x + math.sin(angle) * inner, y + math.cos(angle) * inner,
                             x + math.sin(angle) * radius * 0.88,
                             y + math.cos(angle) * radius * 0.88, rim, 3 * s)
        # Half an hour goes by: the minute hand makes several quick turns.
        spin = self.dip["clock"] * 2 * math.pi * 1.6
        for angle, length, width in ((spin, 0.75, 4), (spin / 12 + 1.2, 0.48, 6)):
            arcade.draw_line(x, y, x + math.sin(angle) * radius * length,
                             y + math.cos(angle) * radius * length,
                             (*TEXT_BRIGHT, alpha), width * s)
        arcade.draw_circle_filled(x, y, 6 * s, rim)
        for text in self.skip_texts:
            text.color = (*text.color[:3], alpha)
            text.draw()

    # --- dialogue and interactions -----------------------------------------

    def draw_shocked(self):
        """Terry's shocked face in place of his sprite, hopping as it lands."""
        hop = 0.0
        if self.shock_clock < CHAO_SHOCK_HOPS * CHAO_SHOCK_HOP_TIME:
            index = int(self.shock_clock / CHAO_SHOCK_HOP_TIME)
            part = self.shock_clock / CHAO_SHOCK_HOP_TIME - index
            hop = CHAO_SHOCK_HOP * 0.55 ** index * math.sin(math.pi * part)
        bottom = (self.terry.ground_y - TERRY_HEIGHT / 2 + self.shock_drop + hop)
        arcade.draw_texture_rect(
            self.shocked_face,
            arcade.LBWH(self.terry.center_x - self.shock_w / 2, bottom,
                        self.shock_w, self.shock_h),
            pixelated=True,
        )

    def start_shock(self):
        self.shocked = True
        self.shock_clock = 0.0
        self.terry.visible = False
        self.portraits.terry = self.shocked_face
        audio.play("dialog_open")

    def end_shock(self):
        self.shocked = False
        self.terry.visible = True
        self.portraits.terry = self.terry_portrait

    def play_script(self, lines, then=None):
        """Run lines of dialogue in order, then call `then`, if given."""
        self.script = list(lines[1:])
        self.after_script = then
        self.start_dialog(*lines[0])

    def start_dialog(self, speaker, text):
        # Terry speaks from the left of the box, everyone else from the right,
        # with their portrait opposite his.
        side = "left" if speaker == "Terry" else "right"
        if speaker != "Terry":
            self.partner = next(
                (npc for npc in self.npcs if npc.name == speaker), self.partner,
            )
        audio.play("dialog_open")
        self.dialog.open(speaker, text, side)
        self.typing_player = audio.play("dialog_type", loop=True)

    def stop_typing_sound(self):
        audio.bank().stop(self.typing_player)
        self.typing_player = None

    def find_target(self):
        """The table or the nearest family member within reach, if any."""
        feet_y = self.terry.ground_y - abs(self.terry.height) / 2
        if (not self.dinner_started
                and distance_to_box(self.terry.center_x, feet_y, TABLE)
                <= CHAO_TABLE_RANGE):
            return ("table", None)
        best, best_distance = None, CHAO_TALK_RANGE
        for npc in self.npcs:
            distance = math.hypot(
                npc.center_x - self.terry.center_x,
                npc.ground_y - self.terry.ground_y,
            )
            if distance <= best_distance:
                best, best_distance = npc, distance
        return ("npc", best) if best else None

    def interact(self):
        kind, npc = self.target
        self.held.clear()
        self.target = None
        if kind == "table":
            (self.feast_card if self.leftovers else self.setup_card).open()
        else:
            self.talk_to(npc)

    def talk_to(self, npc):
        self.talked.add(npc.name)
        self.quests.set_progress("family", f"{len(self.talked)}/{len(self.npcs)}")
        if len(self.talked) == len(self.npcs):
            self.quests.complete("family")
        lines = CHAO_NPC_DIALOG.get(npc.name, ((npc.name, "..."),))
        self.partner = npc
        self.play_script(lines)

    def advance_dialog(self):
        """Enter in a dialogue: finish the line, or move on to the next one."""
        self.stop_typing_sound()
        if not self.dialog.advance():
            return
        if self.shocked:
            # The shocked face only lasts the first line.
            self.end_shock()
        if self.script:
            self.start_dialog(*self.script.pop(0))
            return
        self.partner = None
        then, self.after_script = self.after_script, None
        if then is not None:
            then()

    def start_dinner(self):
        """Bring the food on; update_serving seats everyone after it."""
        self.dinner_started = True
        self.quests.complete("dinner")
        self.serve_clock = 0.0

    def seat_family(self):
        """Swap the people standing about for the family sat at the table."""
        art = {name: art_file for name, art_file, *_ in CHAO_NPCS}
        middle = (TABLE[0] + TABLE[1]) / 2
        self.diner_by_name = {}
        for index, (name, x, y, height, eating) in enumerate(CHAO_SEATS):
            toward = 1 if x < middle else -1
            self.diner_by_name[name] = Diner(
                art.get(name, name), x, y, height, eating, toward, index * 0.7,
            )
        self.diners = list(self.diner_by_name.values())
        self.kids = KidsGame(self.diner_by_name)
        # Under the black, so the cut comes up already close on the table.
        self.zoom_in()

    @property
    def game_running(self):
        return self.kids is not None and self.kids.active

    def start_kids_game(self):
        self.kids.start()

    def end_kids_game(self):
        """Time is up: everyone sits back down and the results come up."""
        share = round(100 * self.kids.share)
        passed = self.kids.share >= KIDS_GOOD_SHARE
        self.kids.stop()
        if passed:
            self.win_card.set_text(KIDS_WIN_TITLE, KIDS_RESULT_MESSAGE.format(share=share))
            self.win_card.open()
        else:
            self.lose_card.set_text(KIDS_LOSE_TITLE, KIDS_RETRY_MESSAGE.format(
                share=share, need=round(100 * KIDS_GOOD_SHARE)))
            self.lose_card.open()

    def update_serving(self, delta_time):
        """Step the food fading in, then the dip to black that seats everyone."""
        self.serve_clock += delta_time
        seat_at = CHAO_SERVE_FADE + CHAO_SERVE_HOLD + CHAO_SEAT_FADE
        if self.diners is None and self.serve_clock >= seat_at:
            self.seat_family()
            # The bare table is under black and never comes back.
            self.backdrop.stop()
            self.backdrop = self.served
        if self.serve_clock >= seat_at + CHAO_SEAT_FADE + CHAO_SEATED_HOLD:
            self.serve_clock = None
            self.play_script(CHAO_TABLE_TALK, then=self.start_kids_game)

    # --- after the dinner --------------------------------------------------

    def start_dip(self, fade, hold, at_black=None, after=None, time_skip=False):
        """Dip to black over `fade` seconds, hold, and come back up.

        `at_black` is called once the screen is fully black, `after` once it
        is clear again. With `time_skip`, a spinning clock and "30 minutes
        later" show on the black.
        """
        self.held.clear()
        self.target = None
        self.dip = {"clock": 0.0, "fade": fade, "hold": hold, "at_black": at_black,
                    "after": after, "time_skip": time_skip}

    def update_dip(self, delta_time):
        dip = self.dip
        dip["clock"] += delta_time
        if dip["at_black"] is not None and dip["clock"] >= dip["fade"]:
            then, dip["at_black"] = dip["at_black"], None
            then()
            if self.dip is not dip:
                return
        if dip["clock"] >= 2 * dip["fade"] + dip["hold"]:
            self.dip = None
            if dip["after"] is not None:
                dip["after"]()

    def time_skip(self):
        """Half an hour on: everyone is full."""
        self.start_dip(CHAO_SKIP_FADE, CHAO_SKIP_HOLD, time_skip=True,
                       after=lambda: self.play_script(CHAO_FULL_DIALOG, then=self.family_leaves))

    def family_leaves(self):
        self.start_dip(CHAO_LEAVE_FADE, 0.5, at_black=self.leave_table,
                       after=lambda: self.play_script(CHAO_ALONE_DIALOG, then=self.get_up))

    def leave_table(self):
        """Under the black: only Terry is left on his stool, looking shocked."""
        for name, diner in self.diner_by_name.items():
            diner.visible = name == "Terry"
        self.kids = None
        self.shocked = True
        self.shock_clock = 0.0
        self.portraits.terry = self.shocked_face

    def get_up(self):
        self.start_dip(CHAO_LEAVE_FADE, 0.3, at_black=self.stand_alone,
                       after=self.feast_card.open)

    def stand_alone(self):
        """Under the black: Terry stands by the table, free to walk again."""
        self.diners = None
        self.diner_by_name = {}
        self.zoomed = False
        self.camera.position = (WIDTH / 2, HEIGHT / 2)
        self.camera.zoom = 1.0
        self.npcs = []
        self.sprites = arcade.SpriteList()
        self.sprites.append(self.terry)
        self.terry.visible = True
        self.terry.center_x, self.terry.ground_y = CHAO_ALONE_SPOT
        self.terry.center_y = self.terry.ground_y
        self.dinner_started = False
        self.leftovers = True
        self.table_prompt = InteractPrompt(CHAO_FEAST_PROMPT)
        self.quests = QuestPanel(CHAO_LEFTOVER_QUESTS)
        self.widgets += [self.table_prompt, self.quests]
        self.table_prompt.layout(self.stage)
        self.quests.layout(self.stage)

    def start_feast(self):
        from .feast_typing import TypingFeastView

        self.start_dip(0.6, 1.0, at_black=lambda: self.window.show_view(TypingFeastView()))

    def update_dust(self, delta_time, moving, dx, dy):
        feet_y = self.terry.ground_y - abs(self.terry.height) / 2
        self.dust.update(delta_time, moving, self.terry.center_x, feet_y, dx, dy)

    def finish_entrance(self):
        """Terry is in place: say the opening line, now or after the title."""
        self.walking_in = False
        self.opening_pending = True

    def skip_entrance(self):
        self.title_card.skip()
        self.fade_clock = CHAO_FADE_IN
        self.terry.ground_y = self.terry.center_y = CHAO_STOP_Y
        self.walking_in = False
        self.opening_pending = True
        self.sort_by_depth()

    # --- update and input ---------------------------------------------------

    def on_update(self, delta_time):
        self.backdrop.update(delta_time)
        if self.serve_clock is not None and self.diners is None:
            # Both videos run while the food fades in over the bare table.
            self.served.update(delta_time)
        # Ahead of the pause check: the birds keep coming up under an overlay
        # opened during the opening seconds, rather than freezing part-faded.
        audio.ambience().update(delta_time)

        if (self.pause_menu.visible or self.settings_panel.visible or self.panel
                or self.card_open):
            return

        # The first frame of a view carries the window's load time, which would
        # otherwise eat most of the opening fade in one step.
        delta_time = min(delta_time, 1 / 30)
        self.clock += delta_time
        self.fade_clock += delta_time
        self.title_card.update(delta_time)
        self.prompt.update(delta_time)
        if self.diners is not None:
            for diner in self.diners:
                diner.update_seat(delta_time)
        if self.shock_clock is not None:
            self.shock_clock += delta_time
        for npc in self.npcs:
            npc.animate(delta_time)

        if self.dip is not None:
            self.update_dust(delta_time, False, 0, 0)
            self.update_dip(delta_time)
            return

        if self.dialog.visible:
            # Dust already in the air settles while the dialogue is up.
            self.update_dust(delta_time, False, 0, 0)
            self.dialog.update(delta_time)
            if not self.dialog.typing:
                self.stop_typing_sound()
            return

        if self.serve_clock is not None:
            self.update_dust(delta_time, False, 0, 0)
            self.update_serving(delta_time)
            return

        if self.diners is not None:
            # Everyone is sat down; only the kids get up to anything.
            if self.kids is not None:
                self.kids.update(delta_time)
                if self.kids.pointer_moved:
                    # The carried kid tugged; the real cursor goes with them.
                    x, y = self.scene_to_screen(*self.kids.pointer)
                    self.window.set_mouse_position(round(x), round(y))
                if self.kids.finished:
                    self.end_kids_game()
            return

        if self.opening_pending:
            self.update_dust(delta_time, False, 0, 0)
            if not self.title_card.finished:
                return
            if self.shock_clock is None:
                self.start_shock()
            elif self.shock_clock >= CHAO_SHOCK_LEAD:
                self.opening_pending = False
                self.play_script(CHAO_SHOCK_DIALOG)
            return

        if self.walking_in:
            # Walk south along the path; the entry point sits above the canvas,
            # so the bounds are opened up to let Terry step in from off-screen.
            self.terry.update_movement(
                delta_time, 0, -1, (0, WIDTH, 0, CHAO_ENTRY_Y + self.terry.height),
            )
            self.footsteps.update(
                delta_time, True, self.terry.center_x, self.terry.ground_y,
            )
            self.update_dust(delta_time, True, 0, -1)
            if self.terry.ground_y <= CHAO_STOP_Y:
                self.terry.ground_y = CHAO_STOP_Y
                self.finish_entrance()
            self.sort_by_depth()
            return

        dx = (arcade.key.D in self.held) - (arcade.key.A in self.held)
        dy = (arcade.key.W in self.held) - (arcade.key.S in self.held)
        self.terry.update_movement(
            delta_time, dx, dy, CHAO_WALK_BOUNDS, CHAO_OBSTACLES,
        )
        moving = bool(dx or dy) and not self.terry.jumping
        self.footsteps.update(
            delta_time, moving, self.terry.center_x, self.terry.ground_y,
        )
        self.update_dust(delta_time, moving, dx, dy)
        if dy:
            self.sort_by_depth()
        self.target = self.find_target()

    def on_key_press(self, key, modifiers):
        # Settings first: it can be opened from the pause menu, which stays
        # visible underneath it.
        if self.settings_panel.visible:
            if self.settings_panel.on_key_press(key) == "close":
                self.settings_panel.close()
            return

        if self.pause_menu.visible:
            self.run_action(self.pause_menu.on_key_press(key))
            return

        if self.card_open:
            # Enter takes the first button, Esc the last.
            card = next(card for card in self.cards if card.visible)
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER):
                self.run_action(card.buttons[0].action)
            elif key == arcade.key.ESCAPE:
                self.run_action(card.buttons[-1].action)
            return

        if key == arcade.key.ESCAPE:
            self.held.clear()
            if self.kids is not None:
                self.kids.release()
            if self.panel:
                self.panel = None
            else:
                self.pause_menu.open()
            return

        if self.panel:
            return

        if self.dialog.visible:
            if key in (arcade.key.ENTER, arcade.key.NUM_ENTER):
                self.advance_dialog()
            return

        if not self.entrance_over:
            if key == arcade.key.SPACE:
                # Skip the title card and the entrance.
                self.skip_entrance()
            return

        if self.dinner_started:
            # Terry has sat down; there is nowhere left to walk.
            return

        if key in (arcade.key.ENTER, arcade.key.NUM_ENTER):
            if self.target is not None:
                self.interact()
            return

        if key == arcade.key.SPACE:
            self.terry.start_jump()
            return
        self.held.add(key)

    def on_key_release(self, key, modifiers):
        self.held.discard(key)

    def on_mouse_motion(self, x, y, dx, dy):
        canvas_x, canvas_y = self.canvas_point(x, y)
        self.pause_menu.on_mouse_motion(canvas_x, canvas_y)
        for card in self.cards:
            card.on_mouse_motion(canvas_x, canvas_y)
        # HUD: only light its buttons up when nothing is over the scene.
        # if self.pause_menu.visible or self.panel or self.walking_in:
        #     self.hud.clear_hover()
        # else:
        #     self.hud.on_mouse_motion(canvas_x, canvas_y)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.settings_panel.on_mouse_drag(*self.canvas_point(x, y))
        if self.kids is not None and not self.pause_menu.visible:
            self.kids.drag(*self.scene_point(x, y))

    def on_mouse_release(self, x, y, button, modifiers):
        self.settings_panel.on_mouse_release()
        if self.kids is not None:
            self.kids.release()

    def on_mouse_press(self, x, y, button, modifiers):
        canvas_x, canvas_y = self.canvas_point(x, y)
        if self.settings_panel.on_mouse_press(canvas_x, canvas_y, button):
            return
        if self.pause_menu.visible:
            self.run_action(self.pause_menu.on_mouse_press(canvas_x, canvas_y, button))
            return
        if self.panel:
            # Any click dismisses an open popup.
            self.panel = None
            return
        for card in self.cards:
            if card.visible:
                self.run_action(card.on_mouse_press(canvas_x, canvas_y, button))
                return
        if (self.game_running and not self.dialog.visible
                and button == arcade.MOUSE_BUTTON_LEFT):
            self.kids.press(*self.scene_point(x, y))
            return
        if not self.playing:
            return
        prompt = None
        if self.target is not None:
            prompt = self.table_prompt if self.target[0] == "table" else self.prompt
        if prompt is not None and prompt.contains(*self.target_tip(), canvas_x, canvas_y):
            self.interact()
            return
        # HUD: a click on an icon opens its popup; the badge handles its own.
        # clicked = self.hud.on_mouse_press(canvas_x, canvas_y, button)
        # if clicked and clicked != "day":
        #     self.held.clear()
        #     self.panel = clicked.capitalize()

    def run_action(self, action):
        if action is None:
            return
        if action == "resume":
            self.pause_menu.close()
        elif action == "setup":
            self.setup_card.close()
            self.start_dinner()
        elif action == "wait":
            self.setup_card.close()
            self.feast_card.close()
        elif action == "feast":
            self.feast_card.close()
            self.start_feast()
        elif action == "retry":
            self.win_card.close()
            self.lose_card.close()
            self.kids.start()
        elif action == "continue":
            self.win_card.close()
            self.game_over = True
            self.play_script(CHAO_AFTER_GAME_DIALOG, then=self.time_skip)
        elif action == "settings":
            self.settings_panel.open()
        elif action == "menu":
            from .views import MenuView

            self.window.show_view(MenuView())
        elif action == "quit":
            self.window.close()
