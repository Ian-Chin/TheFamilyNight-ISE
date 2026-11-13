import math
import time
import arcade
from ...config import ASSETS, HEIGHT, WIDTH
from ...core import audio

# The market crowd loop. One shared loop runs on under the walk-around floor,
# every catch round and the ending, so it never drops out between views; only
# leaving the market for the bus or the menu stops it. Being an Ambience it
# fades in and follows the music slider.
MARKET_AMBIENCE = "market_ambience"


def market_ambience():
    return audio.ambience(MARKET_AMBIENCE)

# Base asset paths
ASSETS_DIR = ASSETS
BG_DIR = ASSETS_DIR / "backgrounds" / "market-dash"
TERRY_GAME_DIR = ASSETS_DIR / "sprites" / "terry market game"
SNATCHERS_BASE_DIR = ASSETS_DIR / "market snatchers"
INGREDIENTS_BASE_DIR = ASSETS_DIR / "market ingredients"

# ============================================================================
# PART 2: Catcher Mini-Game (3 Waves)
# ============================================================================
# --- Cleaned Walk Bounds and Precise Obstacle Footprints ---
MARKET_WALK_BOUNDS = (72, 1280 - 40, 0, 720 - 40)

# Scenery obstacle boxes (left, right, bottom, top) blocking Terry's feet
MARKET_OBSTACLES = (
    # 1. Leftmost wall rack (Grains & Pasta / Canned Goods)
    (0, 10, 0, 720), #right: 78

    # 2. Canned Goods trellis hanging wall corner (top left corner)
    (0, 155, 540, 720),

    # 3. Top back wall & produce shelves (across the top behind the patio)
    (78, 705, 510, 720),

    # 4. Center aisle: Packaged Snacks shelf
    (470, 580, 220, 530),

    # 5. Center aisle: Cereals & Breakfast shelf
    (705, 805, 220, 530),

    # 6. Meat and deli counter (across the middle right)
    (705, 1280, 200, 395),

    # 7. Bottom-left vertical aisle rack
    (185, 230, 0, 205), # left: 130, right: 245

    # 8. Household Goods shelf (horizontal bottom shelf)
    (300, 465, 0, 160), # right: 285

    # 9. Bottom fruit bin 1 (left crate of the right corner)
    (815, 990, 0, 160), 

    # 10. Bottom fruit bin 2 (rightmost produce crates)
    (1120, 1280, 0, 160), 
)

MARKET_STONE_AREAS = (
    (450, 560, 0, 720),   # Middle cobblestone path
    (65, 375, 145, 510),     # Left patio area (red circle)
)

# Playfield bounding coordinates
PLAY_LEFT = 155
PLAY_RIGHT = 1125
PLAY_BOTTOM = 45
PLAY_TOP = 675

# 16 Wall-Shelf slot anchor coordinates corresponding to the wooden shelf cubbies
SHELF_LEFT_X = 85
SHELF_RIGHT_X = 1195
SHELF_Y_LEVELS = [68, 148, 232, 314, 398, 480, 562, 644]
SHELF_Y_WEIGHTS = [0.0, 1.6, 4.0, 4.4, 4.4, 4.0, 1.6, 0.0]

SHELF_SLOTS = [(SHELF_LEFT_X, y) for y in SHELF_Y_LEVELS] + [(SHELF_RIGHT_X, y) for y in SHELF_Y_LEVELS]
SHELF_SLOT_WEIGHTS = SHELF_Y_WEIGHTS + SHELF_Y_WEIGHTS


def pick_weighted_shelf_slot():
    """Selects a random shelf slot with heavy bias toward the middle row levels."""
    import random
    return random.choices(SHELF_SLOTS, weights=SHELF_SLOT_WEIGHTS, k=1)[0]

# Top-down checkered aisle bounds for player and floor shoppers
AISLE_MIN_X = PLAY_LEFT + 15   # approx 170
AISLE_MAX_X = PLAY_RIGHT - 15  # approx 1110
AISLE_MIN_Y = 55
AISLE_MAX_Y = 665

# Checkout Exit Doors Zone (Defend Mode)
CHECKOUT_MIN_X = 480
CHECKOUT_MAX_X = 800
CHECKOUT_MIN_Y = 615


def cover_rect(texture, rect):
    """Fill `rect` with `texture` without distorting it."""
    scale = max(rect.width / texture.width, rect.height / texture.height)
    return arcade.XYWH(
        rect.x, rect.y, texture.width * scale, texture.height * scale
    )


class DialogueHistoryPanel:
    """Scrollable board displaying dialogue history read so far."""
    def __init__(self):
        self.visible = False
        self.history = []  # list of (speaker, text)
        self.scroll_offset = 0

    def add_entry(self, speaker, text):
        if speaker or text:
            clean_text = text.strip() if text else ""
            if not self.history or self.history[-1] != (speaker, clean_text):
                self.history.append((speaker, clean_text))

    def toggle(self):
        self.visible = not self.visible
        if self.visible:
            # Show up to 8 entries at once; scroll to the latest
            self.scroll_offset = max(0, len(self.history) - 8)

    def on_mouse_scroll(self, dy):
        if not self.visible:
            return
        max_offset = max(0, len(self.history) - 8)
        self.scroll_offset = max(0, min(max_offset, self.scroll_offset - int(dy)))

    def draw(self, stage=None):
        if not self.visible:
            return

        panel_w = 1000
        panel_h = 520
        cx = WIDTH / 2
        cy = HEIGHT / 2

        # 1. Dark Backdrop & Border
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, panel_w, panel_h), (18, 14, 12, 245))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, panel_w, panel_h), (180, 130, 70), 2)

        # 2. Header & Footer
        arcade.draw_text("DIALOGUE LOG / HISTORY", cx, cy + (panel_h / 2) - 30, (255, 220, 150), 16, bold=True, anchor_x="center")
        arcade.draw_text("Scroll: Wheel | Click anywhere or Esc to close", cx, cy - (panel_h / 2) + 20, (170, 160, 150), 12, anchor_x="center")

        # 3. Compact Entries (reduced gap: 44px step instead of 80px)
        visible_entries = self.history[self.scroll_offset:self.scroll_offset + 8]
        start_y = cy + (panel_h / 2) - 75

        for speaker, line in visible_entries:
            speaker_tag = f"{speaker}: " if speaker else ""
            if speaker:
                arcade.draw_text(speaker_tag, cx - (panel_w / 2) + 40, start_y, (255, 205, 90), 13, bold=True)
            body_x = cx - (panel_w / 2) + 40 + (100 if speaker else 0)
            arcade.draw_text(line, body_x, start_y, (240, 240, 240), 13, width=int(panel_w - 180))
            start_y -= 44


class DialogueController:
    """Manages Auto, Skip, and History UI buttons."""

    def __init__(self, on_advance_cb, on_skip_cb):
        self.on_advance = on_advance_cb
        self.on_skip = on_skip_cb

        self.auto_mode = False
        self.auto_timer = 0.0
        self.auto_delay_text = 2.0   # Delay after typing completes
        self.auto_delay_silent = 1.4 # Delay for picture-only slides

        self.history_panel = DialogueHistoryPanel()

        # Upper-right corner with balanced margin from the right edge
        btn_y = HEIGHT - 36
        btn_w = 88
        btn_h = 26
        self.buttons = [
            {"id": "log", "label": "📜 LOG", "x": WIDTH - 330, "y": btn_y, "w": btn_w, "h": btn_h},
            {"id": "auto", "label": "▶ AUTO", "x": WIDTH - 230, "y": btn_y, "w": btn_w, "h": btn_h},
            {"id": "skip", "label": "⏩ SKIP", "x": WIDTH - 130, "y": btn_y, "w": btn_w, "h": btn_h},
        ]

    def record(self, speaker, text):
        self.history_panel.add_entry(speaker, text)

    def update(self, delta_time, is_dialog_visible, is_typing):
        """Ticks auto-advance for both spoken dialogue and picture-only slides."""
        if not self.auto_mode or self.history_panel.visible:
            self.auto_timer = 0.0
            return

        if is_dialog_visible:
            if not is_typing:
                self.auto_timer += delta_time
                if self.auto_timer >= self.auto_delay_text:
                    self.auto_timer = 0.0
                    self.on_advance()
            else:
                self.auto_timer = 0.0
        else:
            # Picture-only slide (no dialog box): proceed automatically after short delay
            self.auto_timer += delta_time
            if self.auto_timer >= self.auto_delay_silent:
                self.auto_timer = 0.0
                self.on_advance()

    def draw(self, show_controls=True):
        if show_controls:
            for btn in self.buttons:
                is_active = (btn["id"] == "auto" and self.auto_mode)
                bg_col = (180, 100, 40, 240) if is_active else (25, 20, 18, 230)
                border_col = (255, 210, 120) if is_active else (100, 85, 75)
                text_col = (255, 255, 255) if is_active else (220, 215, 205)

                arcade.draw_rect_filled(arcade.XYWH(btn["x"], btn["y"], btn["w"], btn["h"]), bg_col)
                arcade.draw_rect_outline(arcade.XYWH(btn["x"], btn["y"], btn["w"], btn["h"]), border_col, 2)
                arcade.draw_text(
                    btn["label"],
                    btn["x"],
                    btn["y"],
                    text_col,
                    11,
                    bold=True,
                    anchor_x="center",
                    anchor_y="center"
                )

        self.history_panel.draw()

    def handle_mouse_press(self, canvas_x, canvas_y):
        if self.history_panel.visible:
            self.history_panel.toggle()
            return True

        for btn in self.buttons:
            bx, by, bw, bh = btn["x"], btn["y"], btn["w"], btn["h"]
            if (bx - bw / 2 - 8 <= canvas_x <= bx + bw / 2 + 8) and \
               (by - bh / 2 - 8 <= canvas_y <= by + bh / 2 + 8):
                if btn["id"] == "skip":
                    self.on_skip()
                elif btn["id"] == "auto":
                    self.auto_mode = not self.auto_mode
                elif btn["id"] == "log":
                    self.history_panel.toggle()
                return True
        return False

class RetryModal:
    """Centered confirmation modal for minigame retry/give-up."""
    def __init__(self):
        self.visible = False
        self.title = "FAILED!"
        self.message = "Would you like to try again or return to market?"
        self.on_retry = None
        self.on_give_up = None

    def open(self, on_retry, on_give_up, title="FAILED!", message="Would you like to try again or return to market?"):
        self.visible = True
        self.on_retry = on_retry
        self.on_give_up = on_give_up
        self.title = title
        self.message = message

    def close(self):
        self.visible = False

    def draw(self, ui_camera=None):
        if not self.visible:
            return

        window = arcade.get_window()

        # 1. Full-screen dimmer overlay (covers entire window)
        window.default_camera.use()
        arcade.draw_rect_filled(
            arcade.XYWH(window.width / 2, window.height / 2, window.width, window.height),
            (0, 0, 0, 185)
        )

        # 2. Centered Modal Box in canvas coordinates
        if ui_camera is None:
            current_view = getattr(window, 'current_view', None)
            if current_view is not None:
                ui_camera = getattr(current_view, 'ui_camera', getattr(current_view, 'camera', None))

        if ui_camera is not None:
            ui_camera.use()

        cx = WIDTH / 2
        cy = HEIGHT / 2
        box_w = 560
        box_h = 240

        # Wooden Box
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w, box_h), (50, 30, 20, 245))
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w - 6, box_h - 6), (75, 45, 30, 250))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, box_w, box_h), (180, 140, 90, 220), 2)

        # Title Text
        arcade.draw_text(
            self.title, cx, cy + 68, (235, 75, 75), 16, bold=True,
            anchor_x="center", anchor_y="center"
        )

        # Message Text (multiline & bounded to prevent exceeding box borders)
        arcade.draw_text(
            self.message, cx, cy + 16, (240, 230, 215), 11,
            width=box_w - 60, align="center", anchor_x="center", anchor_y="center",
            multiline=True
        )

        # Buttons
        btn_w, btn_h = 136, 38
        btn_y = cy - 50
        retry_x = cx - 85
        giveup_x = cx + 85

        # "TRY AGAIN" button
        arcade.draw_rect_filled(arcade.XYWH(retry_x, btn_y, btn_w, btn_h), (40, 140, 65, 230))
        arcade.draw_rect_outline(arcade.XYWH(retry_x, btn_y, btn_w, btn_h), (100, 220, 130), 2)
        arcade.draw_text("TRY AGAIN", retry_x, btn_y, (255, 255, 255), 11, bold=True, anchor_x="center", anchor_y="center")

        # "GIVE UP" button
        arcade.draw_rect_filled(arcade.XYWH(giveup_x, btn_y, btn_w, btn_h), (160, 45, 45, 230))
        arcade.draw_rect_outline(arcade.XYWH(giveup_x, btn_y, btn_w, btn_h), (230, 100, 100), 2)
        arcade.draw_text("GIVE UP", giveup_x, btn_y, (255, 255, 255), 11, bold=True, anchor_x="center", anchor_y="center")

    def handle_mouse_press(self, mouse_x, mouse_y):
        if not self.visible:
            return False

        btn_w, btn_h = 136, 38
        cx = WIDTH / 2
        cy = HEIGHT / 2
        btn_y = cy - 50
        retry_x = cx - 85
        giveup_x = cx + 85

        # Hit test for "TRY AGAIN"
        if (retry_x - btn_w / 2 <= mouse_x <= retry_x + btn_w / 2) and \
           (btn_y - btn_h / 2 <= mouse_y <= btn_y + btn_h / 2):
            callback = self.on_retry
            self.close()
            if callback:
                callback()
            return True

        # Hit test for "GIVE UP"
        if (giveup_x - btn_w / 2 <= mouse_x <= giveup_x + btn_w / 2) and \
           (btn_y - btn_h / 2 <= mouse_y <= btn_y + btn_h / 2):
            callback = self.on_give_up
            self.close()
            if callback:
                callback()
            return True

        # Absorb the click so it doesn't trigger game actions behind the modal
        return True

class SkipConfirmModal:
    """Centered confirmation modal for skipping intro cutscenes."""

    def __init__(self):
        self.visible = False
        self.on_confirm = None
        self.on_cancel = None
        self.title = "SKIP INTRO STORY?"
        self.message = (
            "After an abrupt morning wake up call from his cousin Dave, Terry realizes with horror that the\n"
            "big family BBQ feast is today—and his fridge is empty!\n\n"
            "With only six hours before his relatives arrive, Terry rushes to the local market only to find it\n"
            "overwhelmed by crazed discount shoppers. He must navigate the aisles to grab fresh vegetables\n"
            "and prime meats before they sell out!"
        )

    def open(self, on_confirm, on_cancel=None, synopsis=None, **kwargs):
        self.visible = True
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        if synopsis:
            self.message = synopsis
        elif "message" in kwargs and kwargs["message"]:
            self.message = kwargs["message"]
        if "title" in kwargs and kwargs["title"]:
            self.title = kwargs["title"]

    def close(self):
        self.visible = False

    def draw(self, ui_camera=None):
        if not self.visible:
            return

        window = arcade.get_window()

        # 1. Full-screen dimmer overlay (covers 100% of entire physical window)
        window.default_camera.use()
        arcade.draw_rect_filled(
            arcade.XYWH(window.width / 2, window.height / 2, window.width, window.height),
            (0, 0, 0, 185)
        )

        # 2. Centered Modal Box in canvas coordinates
        if ui_camera is None:
            current_view = getattr(window, 'current_view', None)
            if current_view is not None:
                ui_camera = getattr(current_view, 'ui_camera', getattr(current_view, 'camera', None))

        if ui_camera is not None:
            ui_camera.use()

        cx = WIDTH / 2
        cy = HEIGHT / 2
        box_w = 640
        box_h = 320

        # Outer border & dark wooden frame
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w, box_h), (50, 30, 20, 245))
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w - 6, box_h - 6), (75, 45, 30, 250))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, box_w, box_h), (180, 140, 90, 220), 2)

        # Title
        arcade.draw_text(
            self.title, cx, cy + 120, (255, 235, 185), 15, bold=True,
            anchor_x="center", anchor_y="center"
        )

        # Body text / synopsis
        arcade.draw_text(
            self.message, cx - (box_w / 2) + 32, cy + 80, (235, 225, 210), 11,
            width=box_w - 64, multiline=True
        )

        # Buttons geometry
        btn_w, btn_h = 120, 36
        btn_y = cy - 115
        skip_x = cx - 75
        cancel_x = cx + 75

        # Skip button (Red)
        arcade.draw_rect_filled(arcade.XYWH(skip_x, btn_y, btn_w, btn_h), (160, 45, 45, 230))
        arcade.draw_rect_outline(arcade.XYWH(skip_x, btn_y, btn_w, btn_h), (230, 100, 100), 2)
        arcade.draw_text("Skip", skip_x, btn_y, (255, 255, 255), 11, bold=True, anchor_x="center", anchor_y="center")

        # Cancel button (Green)
        arcade.draw_rect_filled(arcade.XYWH(cancel_x, btn_y, btn_w, btn_h), (40, 140, 65, 230))
        arcade.draw_rect_outline(arcade.XYWH(cancel_x, btn_y, btn_w, btn_h), (100, 220, 130), 2)
        arcade.draw_text("Cancel", cancel_x, btn_y, (255, 255, 255), 11, bold=True, anchor_x="center", anchor_y="center")

    def handle_mouse_press(self, mouse_x, mouse_y):
        if not self.visible:
            return False

        cx = WIDTH / 2
        cy = HEIGHT / 2

        btn_w, btn_h = 120, 36
        btn_y = cy - 115
        skip_x = cx - 75
        cancel_x = cx + 75

        # Hit test for Skip button
        if (skip_x - btn_w / 2 <= mouse_x <= skip_x + btn_w / 2) and \
           (btn_y - btn_h / 2 <= mouse_y <= btn_y + btn_h / 2):
            self.close()
            if self.on_confirm:
                self.on_confirm()
            return True

        # Hit test for Cancel button (closes modal regardless of whether callback exists)
        if (cancel_x - btn_w / 2 <= mouse_x <= cancel_x + btn_w / 2) and \
           (btn_y - btn_h / 2 <= mouse_y <= btn_y + btn_h / 2):
            self.close()
            if self.on_cancel:
                self.on_cancel()
            return True

        # Block mouse clicks from bleeding through to dialogue underneath
        return True


class InstructionModal:
    """Displays a wooden instruction board before gameplay starts with an OK button."""

    def __init__(self):
        self.visible = False
        self.mode = "veg"
        self.on_ok = None

    def open(self, mode="veg", on_ok=None):
        self.mode = mode
        self.on_ok = on_ok
        self.visible = True

    def close(self):
        self.visible = False
        if self.on_ok:
            cb = self.on_ok
            self.on_ok = None
            cb()

    def draw(self, ui_camera=None):
        if not self.visible:
            return

        window = arcade.get_window()

        # 1. Full-screen dimmer overlay
        window.default_camera.use()
        arcade.draw_rect_filled(
            arcade.XYWH(window.width / 2, window.height / 2, window.width, window.height),
            (0, 0, 0, 195)
        )

        # 2. Centered Modal Box in canvas coordinates
        if ui_camera is None:
            current_view = getattr(window, 'current_view', None)
            if current_view is not None:
                ui_camera = getattr(current_view, 'ui_camera', getattr(current_view, 'camera', None))

        if ui_camera is not None:
            ui_camera.use()

        cx = WIDTH / 2
        cy = HEIGHT / 2
        box_w = 760
        box_h = 500

        # Outer drop shadow & rich wooden frame
        arcade.draw_rect_filled(arcade.XYWH(cx, cy - 4, box_w + 10, box_h + 10), (12, 6, 3, 190))
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w, box_h), (48, 28, 16, 255))
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w - 8, box_h - 8), (78, 48, 28, 255))
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w - 18, box_h - 18), (110, 68, 38, 255))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, box_w - 8, box_h - 8), (180, 140, 90, 220), 2)
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, box_w, box_h), (35, 18, 10, 255), 2)

        # Title configuration
        if self.mode == "veg":
            title = "🥕 HOW TO PLAY: FRESH VEGETABLES 🥦"
            obj_title = "OBJECTIVE:"
            obj_desc = "Catch all 5 vegetables from the crates before time runs out! Touching shoppers slows you down. Prevents shoppers leave with foods"
        elif self.mode == "meat":
            title = "🥩 HOW TO PLAY: PRIME MEATS 🍖"
            obj_title = "OBJECTIVE:"
            obj_desc = "Secure all 5 meat cuts from the crates before time runs out! Touching shoppers slows you down. Prevents shoppers leave with foods"
        else:
            title = "🛒 HOW TO PLAY: CHECKOUT ESCAPE 🚪"
            obj_title = "OBJECTIVE:"
            obj_desc = "Escort your basket with all ingredients to the exit door!"

        # Title text
        arcade.draw_text(
            title, cx, cy + 200, (255, 235, 175), 16, bold=True,
            anchor_x="center", anchor_y="center"
        )
        # Decorative divider line
        arcade.draw_line(cx - 330, cy + 175, cx + 330, cy + 175, (180, 140, 90, 180), 2)

        # Objective Banner Box
        obj_box_y = cy + 130
        obj_box_w = box_w - 48
        obj_box_h = 60
        arcade.draw_rect_filled(arcade.XYWH(cx, obj_box_y, obj_box_w, obj_box_h), (36, 20, 12, 230))
        arcade.draw_rect_outline(arcade.XYWH(cx, obj_box_y, obj_box_w, obj_box_h), (150, 110, 70, 180), 1.5)
        obj_left = cx - (obj_box_w / 2) + 20
        arcade.draw_text(obj_title, obj_left, obj_box_y + 14, (255, 215, 110), 11, bold=True, anchor_y="center")
        arcade.draw_text(obj_desc, obj_left, obj_box_y - 12, (230, 225, 215), 10, width=obj_box_w - 40, anchor_y="center")

        # Controls Cards Header
        arcade.draw_text("CONTROLS & ACTIONS", cx, cy + 78, (255, 215, 110), 12, bold=True, anchor_x="center", anchor_y="center")

        # Control Rows
        if self.mode == "defend":
            controls = [
                ("WASD  /  ARROWS", "Move Terry", "Navigate through the crowded market aisle"),
                ("LEFT CLICK  /  SPACE", "180° Spin Attack", "Spin 180° clockwise to smack shoppers & recover food"),
                ("[ E ]  or  WALK OVER", "Pick Up Food", "Quickly recover spilled ingredients from the floor"),
                ("HOLD SHIFT", "Sprint Boost", "Run at high speed toward the checkout exit doors"),
            ]
        else:
            controls = [
                ("WASD  /  ARROWS", "Move Terry", "Navigate across aisle toward glowing restock shelves"),
                ("[ E ]  or  ENTER", "Grab Shelf Item", "Take the active ingredient from shelf crate when nearby"),
                ("SPACE  /  LEFT CLICK", "Shield Block", "Block & deflect aggressive shoppers; make them drop items"),
                ("HOLD SHIFT", "Sprint Boost", "Run at high speed to beat rushing shoppers to shelf"),
            ]

        row_start_y = cy + 46
        row_h = 42
        row_w = box_w - 48
        row_left = cx - (row_w / 2)

        for idx, (badge_text, act_label, desc_text) in enumerate(controls):
            ry = row_start_y - (idx * row_h)
            # Subtle row backdrop
            arcade.draw_rect_filled(arcade.XYWH(cx, ry, row_w, 34), (42, 24, 14, 180))
            arcade.draw_rect_outline(arcade.XYWH(cx, ry, row_w, 34), (90, 60, 40, 140), 1)

            # Key Badge pill (Column 1)
            badge_w = 170
            badge_h = 24
            badge_x = row_left + 14 + (badge_w / 2)
            arcade.draw_rect_filled(arcade.XYWH(badge_x, ry, badge_w, badge_h), (22, 14, 8, 255))
            arcade.draw_rect_outline(arcade.XYWH(badge_x, ry, badge_w, badge_h), (210, 160, 90, 220), 1.5)
            arcade.draw_text(badge_text, badge_x, ry, (255, 240, 200), 10, bold=True, anchor_x="center", anchor_y="center")

            # Action Label (Column 2)
            act_x = row_left + 14 + badge_w + 16
            arcade.draw_text(act_label, act_x, ry, (255, 220, 130), 11, bold=True, anchor_x="left", anchor_y="center")

            # Description (Column 3) - well spaced with ample width to prevent any overflow
            desc_x = act_x + 130
            desc_w = (row_left + row_w - 14) - desc_x
            arcade.draw_text(desc_text, desc_x, ry, (225, 220, 210), 10, anchor_x="left", anchor_y="center", width=int(desc_w))

        # OK / START Button
        btn_w, btn_h = 180, 42
        btn_y = cy - 188
        btn_x = cx

        # Pulsing gold/green button
        pulse = 0.5 + 0.5 * math.sin(time.time() * 5.0)
        btn_col = (38, 135, 62, 245)
        border_col = (110 + int(70 * pulse), 235, 140)

        arcade.draw_rect_filled(arcade.XYWH(btn_x, btn_y - 2, btn_w, btn_h), (18, 48, 24, 255))
        arcade.draw_rect_filled(arcade.XYWH(btn_x, btn_y, btn_w, btn_h), btn_col)
        arcade.draw_rect_filled(arcade.XYWH(btn_x, btn_y + (btn_h / 4), btn_w - 6, btn_h / 2), (65, 175, 95, 120))
        arcade.draw_rect_outline(arcade.XYWH(btn_x, btn_y, btn_w, btn_h), border_col, 2.5)

        arcade.draw_text(
            "OK - START!", btn_x, btn_y, (255, 255, 255), 13, bold=True,
            anchor_x="center", anchor_y="center"
        )
        arcade.draw_text(
            "(Press ENTER or SPACE to begin)", btn_x, btn_y - 28, (200, 185, 160), 9,
            anchor_x="center", anchor_y="center"
        )

    def handle_mouse_press(self, mouse_x, mouse_y):
        if not self.visible:
            return False

        cx = WIDTH / 2
        cy = HEIGHT / 2
        btn_w, btn_h = 180, 42
        btn_y = cy - 188
        btn_x = cx

        if (btn_x - btn_w / 2 <= mouse_x <= btn_x + btn_w / 2) and \
           (btn_y - btn_h / 2 <= mouse_y <= btn_y + btn_h / 2):
            from ...core import audio
            audio.play("ui_click")
            self.close()
            return True

        # Consume clicks on the modal so they don't bleed through
        return True

    def handle_key_press(self, key):
        if not self.visible:
            return False
        if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.SPACE, arcade.key.E, arcade.key.ESCAPE):
            from ...core import audio
            audio.play("ui_click")
            self.close()
            return True
        return True