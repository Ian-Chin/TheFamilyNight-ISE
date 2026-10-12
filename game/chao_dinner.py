"""The Chao family dinner scene.

Terry walks in down the night garden path while the opening black fades away.
As he walks, the "Scene 4 / Chao Dinner" title drifts up over a blurred
garden and fades off again; once he has settled by the dinner table he says
his opening line. The player takes over from there: a quest panel in the top
right asks him to start the dinner at the table (marked with a "!"), and
walking up to the table or to a family member brings up an
"Interact [Enter]" prompt. Talking to someone plays a short exchange with
Terry standing on the left of the dialogue box and them on the right.
"""

import math

import arcade

from . import textures
from . import audio
from .audio import Footsteps
from .backdrop import Backdrop
from .chao_widgets import InteractPrompt, Portraits, QuestPanel, TitleCard
from .config import (
    CHAO_DINNER_BG, CHAO_DINNER_START_DIALOG, CHAO_ENTRY_Y, CHAO_FADE_IN,
    CHAO_MARK_BOB, CHAO_MARK_BOB_TIME, CHAO_NPC_DIALOG, CHAO_NPCS,
    CHAO_OBSTACLES, CHAO_OPENING_DIALOG, CHAO_PATH_X, CHAO_STONE_AREAS,
    CHAO_STOP_Y, CHAO_TABLE_MARK, CHAO_TABLE_MARK_H, CHAO_TABLE_MARK_POS,
    CHAO_TABLE_RANGE, CHAO_TALK_RANGE, CHAO_TITLE_BLUR, CHAO_WALK_BOUNDS,
    HEIGHT, WIDTH,
)
from .dialogue import DialogBox
from .effects import WalkDust
from .options import SettingsPanel
from .pause import PauseMenu
from .sprites import NPC, Terry
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
        self.held = set()

        self.panel = None   # the label of the open HUD popup, or None
        self.title_card = TitleCard()
        self.prompt = InteractPrompt()
        self.quests = QuestPanel()
        self.quests.set_progress("family", f"0/{len(self.npcs)}")
        self.portraits = Portraits(textures.terry_frames(glow=False)[2][0])
        self.dialog = DialogBox()
        self.pause_menu = PauseMenu()
        self.settings_panel = SettingsPanel()
        self.widgets = [
            self.title_card, self.prompt, self.quests, self.portraits,
            self.dialog, self.pause_menu, self.settings_panel,
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
        self.relayout()

    def on_show_view(self):
        audio.ambience().start()

    def on_hide_view(self):
        self.backdrop.stop()
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

    @property
    def fade_alpha(self):
        if self.fade_clock >= CHAO_FADE_IN:
            return 0
        return round(255 * (1 - self.fade_clock / CHAO_FADE_IN))

    @property
    def entrance_over(self):
        return not self.walking_in and not self.opening_pending

    @property
    def playing(self):
        """True once the scripted entrance and any dialogue are out of the way."""
        return self.entrance_over and not self.dialog.visible

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
        arcade.draw_texture_rect(background, cover_rect(background, viewport))

        self.camera.use()
        for character in self.sprites:
            character.draw_shadow()
        # Kicked up behind the feet, so the legs are drawn over it.
        self.dust.draw()
        self.sprites.draw(pixelated=True)
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

        if self.entrance_over:
            self.quests.draw()
        if self.playing:
            self.hint.draw()
            if self.target is not None:
                self.prompt.draw(*self.target_tip())
            # HUD: drawn once the scripted entrance is over, and under the fade
            # so the opening black covers it too.
            # self.hud.draw()
            # if self.panel:
            #     self.placeholder.set_title(self.panel)
            #     self.placeholder.draw()

        alpha = self.fade_alpha
        if alpha:
            arcade.draw_rect_filled(
                arcade.LBWH(0, 0, self.window.width, self.window.height),
                (0, 0, 0, alpha),
            )
        self.title_card.draw()

        if self.dialog.visible:
            partner = self.partner.texture if self.partner else None
            self.portraits.draw(partner, self.dialog.side)
        self.dialog.draw()
        # Settings is reached through the pause menu, which stays open behind
        # it; the glass is see-through enough that both at once is a mess.
        if not self.settings_panel.visible:
            self.pause_menu.draw()
        self.settings_panel.draw()

    # --- dialogue and interactions -----------------------------------------

    def start_dialog(self, speaker, text):
        # Terry speaks from the left of the box, everyone else from the right.
        side = "left" if speaker == "Terry" else "right"
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
            self.start_dinner()
        else:
            self.talk_to(npc)

    def talk_to(self, npc):
        self.talked.add(npc.name)
        self.quests.set_progress("family", f"{len(self.talked)}/{len(self.npcs)}")
        if len(self.talked) == len(self.npcs):
            self.quests.complete("family")
        lines = CHAO_NPC_DIALOG.get(npc.name, ((npc.name, "..."),))
        self.partner = npc
        self.script = list(lines[1:])
        self.start_dialog(*lines[0])

    def advance_dialog(self):
        """Enter in a dialogue: finish the line, or move on to the next one."""
        self.stop_typing_sound()
        if not self.dialog.advance():
            return
        if self.script:
            self.start_dialog(*self.script.pop(0))
        else:
            self.partner = None

    def start_dinner(self):
        # The dinner itself is still to be built; for now the quest is ticked
        # off and Terry calls everyone over.
        self.dinner_started = True
        self.quests.complete("dinner")
        self.start_dialog(*CHAO_DINNER_START_DIALOG)

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
        # Ahead of the pause check: the birds keep coming up under an overlay
        # opened during the opening seconds, rather than freezing part-faded.
        audio.ambience().update(delta_time)

        if self.pause_menu.visible or self.settings_panel.visible or self.panel:
            return

        # The first frame of a view carries the window's load time, which would
        # otherwise eat most of the opening fade in one step.
        delta_time = min(delta_time, 1 / 30)
        self.clock += delta_time
        self.fade_clock += delta_time
        self.title_card.update(delta_time)
        self.prompt.update(delta_time)

        if self.dialog.visible:
            # Dust already in the air settles while the dialogue is up.
            self.update_dust(delta_time, False, 0, 0)
            self.dialog.update(delta_time)
            if not self.dialog.typing:
                self.stop_typing_sound()
            return

        if self.opening_pending:
            self.update_dust(delta_time, False, 0, 0)
            if self.title_card.finished:
                self.opening_pending = False
                self.start_dialog(*CHAO_OPENING_DIALOG)
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

        if key == arcade.key.ESCAPE:
            self.held.clear()
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
        # HUD: only light its buttons up when nothing is over the scene.
        # if self.pause_menu.visible or self.panel or self.walking_in:
        #     self.hud.clear_hover()
        # else:
        #     self.hud.on_mouse_motion(canvas_x, canvas_y)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.settings_panel.on_mouse_drag(*self.canvas_point(x, y))

    def on_mouse_release(self, x, y, button, modifiers):
        self.settings_panel.on_mouse_release()

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
        if not self.playing:
            return
        if (self.target is not None
                and self.prompt.contains(*self.target_tip(), canvas_x, canvas_y)):
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
        elif action == "settings":
            self.settings_panel.open()
        elif action == "menu":
            from .views import MenuView

            self.window.show_view(MenuView())
        elif action == "quit":
            self.window.close()
