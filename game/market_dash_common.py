from pathlib import Path
import arcade
from .config import HEIGHT, WIDTH

# Base asset paths
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
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

    def draw(self):
        if not self.visible:
            return

        window = arcade.get_window()

        # 1. Full-screen dimmer overlay
        arcade.draw_rect_filled(
            arcade.XYWH(window.width / 2, window.height / 2, window.width, window.height),
            (0, 0, 0, 185)
        )

        # 2. Centered Modal Box in Window/Screen coordinates
        cx = window.width / 2
        cy = window.height / 2
        box_w = 480
        box_h = 240

        # Wooden Box
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w, box_h), (50, 30, 20, 245))
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w - 6, box_h - 6), (75, 45, 30, 250))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, box_w, box_h), (180, 140, 90, 220), 2)

        # Title Text
        arcade.draw_text(
            self.title, cx, cy + 65, (235, 75, 75), 16, bold=True,
            anchor_x="center", anchor_y="center"
        )

        # Message Text
        arcade.draw_text(
            self.message, cx, cy + 20, (240, 230, 215), 11,
            anchor_x="center", anchor_y="center"
        )

        # Buttons
        btn_w, btn_h = 130, 38
        btn_y = cy - 45
        retry_x = cx - 80
        giveup_x = cx + 80

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

        window = arcade.get_window()
        btn_w, btn_h = 130, 38

        # Test both Screen Coordinates AND Virtual Canvas Coordinates:
        test_centers = [
            (window.width / 2, window.height / 2),
            (WIDTH / 2, HEIGHT / 2)
        ]

        for cx, cy in test_centers:
            btn_y = cy - 45
            retry_x = cx - 80
            giveup_x = cx + 80

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

    def draw(self):
        if not self.visible:
            return

        # Use virtual canvas center so it aligns with stage canvas coordinates
        cx = (WIDTH / 2) + 200
        cy = (HEIGHT / 2) + 120

        # 1. Full-screen dimmer overlay
        arcade.draw_rect_filled(
            arcade.XYWH(cx, cy, WIDTH, HEIGHT),
            (0, 0, 0, 180)
        )

        # 2. Centered Modal Box
        box_w = 580
        box_h = 300

        # Outer border & dark wooden frame
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w, box_h), (50, 30, 20, 245))
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w - 6, box_h - 6), (75, 45, 30, 250))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, box_w, box_h), (180, 140, 90, 220), 2)

        # Title
        arcade.draw_text(
            self.title, cx, cy + 115, (255, 235, 185), 14, bold=True,
            anchor_x="center", anchor_y="center"
        )

        # Body text / synopsis
        arcade.draw_text(
            self.message, cx - (box_w / 2) + 24, cy + 70, (235, 225, 210), 10,
            width=box_w - 48, multiline=True
        )

        # Buttons geometry
        btn_w, btn_h = 120, 36
        btn_y = cy - 105
        skip_x = cx - 70
        cancel_x = cx + 80

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
        btn_y = cy - 105
        skip_x = cx - 75
        cancel_x = cx + 65

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