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

        panel_w = 980
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
    """Confirmation modal shown when Terry fails an ingredient or defense mini-game."""
    def __init__(self):
        self.visible = False
        self.title = "WAVE FAILED!"
        self.message = "You lost all lives! Try again?"
        self.on_retry = None
        self.on_give_up = None

        # Modal Dimensions
        self.w = 420
        self.h = 220
        self.cx = WIDTH / 2
        self.cy = HEIGHT / 2

        # Buttons (Canvas Space)
        btn_y = self.cy - 45
        self.btn_retry = {"id": "retry", "label": "TRY AGAIN", "x": self.cx - 95, "y": btn_y, "w": 140, "h": 40}
        self.btn_give_up = {"id": "give_up", "label": "GIVE UP", "x": self.cx + 95, "y": btn_y, "w": 140, "h": 40}
        self.buttons = [self.btn_retry, self.btn_give_up]

    def open(self, on_retry_cb, on_give_up_cb, title="CHALLENGE FAILED!", message="Would you like to try again?"):
        self.visible = True
        self.on_retry = on_retry_cb
        self.on_give_up = on_give_up_cb
        self.title = title
        self.message = message

    def close(self):
        self.visible = False

    def draw(self):
        if not self.visible:
            return

        # Dimmed backdrop
        arcade.draw_rect_filled(arcade.XYWH(self.cx, self.cy, WIDTH, HEIGHT), (0, 0, 0, 160))

        # Main frame
        arcade.draw_rect_filled(arcade.XYWH(self.cx, self.cy, self.w, self.h), (35, 24, 18, 250))
        arcade.draw_rect_filled(arcade.XYWH(self.cx, self.cy, self.w - 8, self.h - 8), (70, 46, 32, 255))
        arcade.draw_rect_outline(arcade.XYWH(self.cx, self.cy, self.w, self.h), (195, 140, 80), 3)

        # Texts
        arcade.draw_text(self.title, self.cx, self.cy + 60, (255, 95, 95), 16, bold=True, anchor_x="center", anchor_y="center")
        arcade.draw_text(self.message, self.cx, self.cy + 18, (240, 235, 225), 12, anchor_x="center", anchor_y="center")

        # Buttons
        for btn in self.buttons:
            is_retry = (btn["id"] == "retry")
            bg_col = (48, 120, 52) if is_retry else (135, 42, 38)
            border_col = (115, 230, 125) if is_retry else (240, 110, 105)

            arcade.draw_rect_filled(arcade.XYWH(btn["x"], btn["y"], btn["w"], btn["h"]), bg_col)
            arcade.draw_rect_outline(arcade.XYWH(btn["x"], btn["y"], btn["w"], btn["h"]), border_col, 2)
            arcade.draw_text(btn["label"], btn["x"], btn["y"], (255, 255, 255), 12, bold=True, anchor_x="center", anchor_y="center")

    def handle_mouse_press(self, canvas_x, canvas_y):
        if not self.visible:
            return False

        for btn in self.buttons:
            bx, by, bw, bh = btn["x"], btn["y"], btn["w"], btn["h"]
            if (bx - bw / 2 <= canvas_x <= bx + bw / 2) and (by - bh / 2 <= canvas_y <= by + bh / 2):
                if btn["id"] == "retry" and self.on_retry:
                    self.close()
                    self.on_retry()
                elif btn["id"] == "give_up" and self.on_give_up:
                    self.close()
                    self.on_give_up()
                return True
        return True  # Absorb click while modal is visible

class SkipConfirmModal:
    """Modal dialog asking to confirm skipping with a synopsis preview."""

    def __init__(self):
        self.visible = False
        self.on_confirm = None
        self.on_cancel = None
        self.title = "SKIP STORY?"
        self.synopsis = ""

        # Button dimensions
        self.btn_w = 130
        self.btn_h = 38

    def open(self, on_confirm, on_cancel, synopsis, title="SKIP STORY?"):
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.synopsis = synopsis
        self.title = title
        self.visible = True

    def close(self):
        self.visible = False
        self.on_confirm = None
        self.on_cancel = None

    def draw(self):
        if not self.visible:
            return

        from .config import WIDTH, HEIGHT

        # 1. Dark overlay backdrop
        arcade.draw_rect_filled(
            arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT),
            (0, 0, 0, 180)
        )

        # 2. Expanded Wooden Panel Board
        modal_w = 700   # Expanded from 540 for comfortable reading width
        modal_h = 360   # Expanded from 240 so text doesn't hit buttons
        cx, cy = WIDTH / 2, HEIGHT / 2

        # Outer border & wood background
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, modal_w, modal_h), (85, 48, 24, 250))
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, modal_w - 8, modal_h - 8), (138, 88, 48, 250))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, modal_w, modal_h), (42, 22, 10), 3)

        # Title
        arcade.draw_text(
            self.title,
            cx, cy + (modal_h / 2) - 28,
            (255, 238, 185), 17, bold=True,
            anchor_x="center", anchor_y="center"
        )

        # 3. Expanded Dark Synopsis Body Box
        box_w = modal_w - 48
        box_h = 205     # Plenty of vertical room for multiline text
        box_y = cy + 18
        arcade.draw_rect_filled(arcade.XYWH(cx, box_y, box_w, box_h), (40, 24, 14, 220))
        arcade.draw_rect_outline(arcade.XYWH(cx, box_y, box_w, box_h), (70, 42, 24), 2)

        # Synopsis text (multiline with safe internal margins)
        arcade.draw_text(
            self.synopsis,
            cx - (box_w / 2) + 20,
            box_y + (box_h / 2) - 22,
            (240, 225, 205),
            12,
            width=int(box_w - 40),
            multiline=True
        )

        # 4. Buttons (lowered below the expanded content box)
        btn_y = cy - (modal_h / 2) + 38
        skip_x = cx - 95
        cancel_x = cx + 95

        # Skip button (Reddish / Wood)
        arcade.draw_rect_filled(arcade.XYWH(skip_x, btn_y, self.btn_w, self.btn_h), (140, 45, 45, 240))
        arcade.draw_rect_outline(arcade.XYWH(skip_x, btn_y, self.btn_w, self.btn_h), (220, 110, 110), 2)
        arcade.draw_text("Skip", skip_x, btn_y, (255, 240, 240), 13, bold=True, anchor_x="center", anchor_y="center")

        # Cancel button (Greenish / Wood)
        arcade.draw_rect_filled(arcade.XYWH(cancel_x, btn_y, self.btn_w, self.btn_h), (50, 75, 45, 240))
        arcade.draw_rect_outline(arcade.XYWH(cancel_x, btn_y, self.btn_w, self.btn_h), (110, 180, 110), 2)
        arcade.draw_text("Cancel", cancel_x, btn_y, (240, 255, 240), 13, bold=True, anchor_x="center", anchor_y="center")

    def handle_mouse_press(self, x, y):
        """Separate handler specifically for SkipConfirmModal's buttons."""
        if not self.visible:
            return False

        from .config import WIDTH, HEIGHT
        cx, cy = WIDTH / 2, HEIGHT / 2
        modal_h = 360
        btn_y = cy - (modal_h / 2) + 38
        skip_x = cx - 95
        cancel_x = cx + 95

        # Click Skip
        if (skip_x - self.btn_w / 2 <= x <= skip_x + self.btn_w / 2) and \
           (btn_y - self.btn_h / 2 <= y <= btn_y + self.btn_h / 2):
            if self.on_confirm:
                cb = self.on_confirm
                self.close()
                cb()
            return True

        # Click Cancel
        if (cancel_x - self.btn_w / 2 <= x <= cancel_x + self.btn_w / 2) and \
           (btn_y - self.btn_h / 2 <= y <= btn_y + self.btn_h / 2):
            if self.on_cancel:
                cb = self.on_cancel
                self.close()
                cb()
            return True

        return True  # Consume all other clicks so background elements aren't triggered