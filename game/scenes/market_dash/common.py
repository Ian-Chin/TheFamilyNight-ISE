import math
import time
import arcade
from ...config import ASSETS, HEIGHT, WIDTH
from ...core import audio

MARKET_AMBIENCE = "market_ambience"


def market_ambience():
    return audio.ambience(MARKET_AMBIENCE)

ASSETS_DIR = ASSETS
BG_DIR = ASSETS_DIR / "backgrounds" / "market-dash"
TERRY_GAME_DIR = ASSETS_DIR / "sprites" / "terry market game"
SNATCHERS_BASE_DIR = ASSETS_DIR / "market snatchers"
INGREDIENTS_BASE_DIR = ASSETS_DIR / "market ingredients"

MARKET_WALK_BOUNDS = (72, 1280 - 40, 0, 720 - 40)

MARKET_OBSTACLES = (
    (0, 10, 0, 720),

    (0, 155, 540, 720),

    (78, 705, 510, 720),

    (470, 580, 220, 530),

    (705, 805, 220, 530),

    (705, 1280, 200, 395),

    (185, 230, 0, 205),

    (300, 465, 0, 160),

    (815, 990, 0, 160), 

    (1120, 1280, 0, 160), 
)

MARKET_STONE_AREAS = (
    (450, 560, 0, 720),   # Middle cobblestone path
    (65, 375, 145, 510),     # Left patio area (red circle)
)

PLAY_LEFT = 155
PLAY_RIGHT = 1125
PLAY_BOTTOM = 45
PLAY_TOP = 675

SHELF_LEFT_X = 85
SHELF_RIGHT_X = 1195
SHELF_Y_LEVELS = [68, 148, 232, 314, 398, 480, 562, 644]
SHELF_Y_WEIGHTS = [0.0, 1.6, 4.0, 4.4, 4.4, 4.0, 1.6, 0.0]

SHELF_SLOTS = [(SHELF_LEFT_X, y) for y in SHELF_Y_LEVELS] + [(SHELF_RIGHT_X, y) for y in SHELF_Y_LEVELS]
SHELF_SLOT_WEIGHTS = SHELF_Y_WEIGHTS + SHELF_Y_WEIGHTS


def pick_weighted_shelf_slot():
    import random
    return random.choices(SHELF_SLOTS, weights=SHELF_SLOT_WEIGHTS, k=1)[0]

AISLE_MIN_X = PLAY_LEFT + 15  
AISLE_MAX_X = PLAY_RIGHT - 15 
AISLE_MIN_Y = 55
AISLE_MAX_Y = 665

CHECKOUT_MIN_X = 480
CHECKOUT_MAX_X = 800
CHECKOUT_MIN_Y = 615


def cover_rect(texture, rect):
    scale = max(rect.width / texture.width, rect.height / texture.height)
    return arcade.XYWH(
        rect.x, rect.y, texture.width * scale, texture.height * scale
    )


class DialogueHistoryPanel:
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

        
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, panel_w, panel_h), (18, 14, 12, 245))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, panel_w, panel_h), (180, 130, 70), 2)

        
        arcade.draw_text("DIALOGUE LOG / HISTORY", cx, cy + (panel_h / 2) - 30, (255, 220, 150), 16, bold=True, anchor_x="center")
        arcade.draw_text("Scroll: Wheel | Click anywhere or Esc to close", cx, cy - (panel_h / 2) + 20, (170, 160, 150), 12, anchor_x="center")

       
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
    def __init__(self, on_advance_cb, on_skip_cb):
        self.on_advance = on_advance_cb
        self.on_skip = on_skip_cb

        self.auto_mode = False
        self.auto_timer = 0.0
        self.auto_delay_text = 2.0   
        self.auto_delay_silent = 1.4

        self.history_panel = DialogueHistoryPanel()

        
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

        
        window.default_camera.use()
        arcade.draw_rect_filled(
            arcade.XYWH(window.width / 2, window.height / 2, window.width, window.height),
            (0, 0, 0, 185)
        )

        
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

        
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w, box_h), (50, 30, 20, 245))
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w - 6, box_h - 6), (75, 45, 30, 250))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, box_w, box_h), (180, 140, 90, 220), 2)

       
        arcade.draw_text(
            self.title, cx, cy + 68, (235, 75, 75), 16, bold=True,
            anchor_x="center", anchor_y="center"
        )

       
        arcade.draw_text(
            self.message, cx, cy + 16, (240, 230, 215), 11,
            width=box_w - 60, align="center", anchor_x="center", anchor_y="center",
            multiline=True
        )

       
        btn_w, btn_h = 136, 38
        btn_y = cy - 50
        retry_x = cx - 85
        giveup_x = cx + 85

        
        arcade.draw_rect_filled(arcade.XYWH(retry_x, btn_y, btn_w, btn_h), (40, 140, 65, 230))
        arcade.draw_rect_outline(arcade.XYWH(retry_x, btn_y, btn_w, btn_h), (100, 220, 130), 2)
        arcade.draw_text("TRY AGAIN", retry_x, btn_y, (255, 255, 255), 11, bold=True, anchor_x="center", anchor_y="center")

       
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

       
        if (retry_x - btn_w / 2 <= mouse_x <= retry_x + btn_w / 2) and \
           (btn_y - btn_h / 2 <= mouse_y <= btn_y + btn_h / 2):
            callback = self.on_retry
            self.close()
            if callback:
                callback()
            return True

   
        if (giveup_x - btn_w / 2 <= mouse_x <= giveup_x + btn_w / 2) and \
           (btn_y - btn_h / 2 <= mouse_y <= btn_y + btn_h / 2):
            callback = self.on_give_up
            self.close()
            if callback:
                callback()
            return True

     
        return True

class SkipConfirmModal:
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

     
        window.default_camera.use()
        arcade.draw_rect_filled(
            arcade.XYWH(window.width / 2, window.height / 2, window.width, window.height),
            (0, 0, 0, 185)
        )

     
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

     
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w, box_h), (50, 30, 20, 245))
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w - 6, box_h - 6), (75, 45, 30, 250))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, box_w, box_h), (180, 140, 90, 220), 2)

       
        arcade.draw_text(
            self.title, cx, cy + 120, (255, 235, 185), 15, bold=True,
            anchor_x="center", anchor_y="center"
        )

       
        arcade.draw_text(
            self.message, cx - (box_w / 2) + 32, cy + 80, (235, 225, 210), 11,
            width=box_w - 64, multiline=True
        )

        btn_w, btn_h = 120, 36
        btn_y = cy - 115
        skip_x = cx - 75
        cancel_x = cx + 75

        arcade.draw_rect_filled(arcade.XYWH(skip_x, btn_y, btn_w, btn_h), (160, 45, 45, 230))
        arcade.draw_rect_outline(arcade.XYWH(skip_x, btn_y, btn_w, btn_h), (230, 100, 100), 2)
        arcade.draw_text("Skip", skip_x, btn_y, (255, 255, 255), 11, bold=True, anchor_x="center", anchor_y="center")

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

       
        if (skip_x - btn_w / 2 <= mouse_x <= skip_x + btn_w / 2) and \
           (btn_y - btn_h / 2 <= mouse_y <= btn_y + btn_h / 2):
            self.close()
            if self.on_confirm:
                self.on_confirm()
            return True

     
        if (cancel_x - btn_w / 2 <= mouse_x <= cancel_x + btn_w / 2) and \
           (btn_y - btn_h / 2 <= mouse_y <= btn_y + btn_h / 2):
            self.close()
            if self.on_cancel:
                self.on_cancel()
            return True

        
        return True


class InstructionModal:
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

       
        window.default_camera.use()
        arcade.draw_rect_filled(
            arcade.XYWH(window.width / 2, window.height / 2, window.width, window.height),
            (0, 0, 0, 195)
        )

      
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

        arcade.draw_rect_filled(arcade.XYWH(cx, cy - 4, box_w + 10, box_h + 10), (12, 6, 3, 190))
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w, box_h), (48, 28, 16, 255))
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w - 8, box_h - 8), (78, 48, 28, 255))
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, box_w - 18, box_h - 18), (110, 68, 38, 255))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, box_w - 8, box_h - 8), (180, 140, 90, 220), 2)
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, box_w, box_h), (35, 18, 10, 255), 2)

        
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

        arcade.draw_text(
            title, cx, cy + 200, (255, 235, 175), 16, bold=True,
            anchor_x="center", anchor_y="center"
        )
       
        arcade.draw_line(cx - 330, cy + 175, cx + 330, cy + 175, (180, 140, 90, 180), 2)

       
        obj_box_y = cy + 130
        obj_box_w = box_w - 48
        obj_box_h = 60
        arcade.draw_rect_filled(arcade.XYWH(cx, obj_box_y, obj_box_w, obj_box_h), (36, 20, 12, 230))
        arcade.draw_rect_outline(arcade.XYWH(cx, obj_box_y, obj_box_w, obj_box_h), (150, 110, 70, 180), 1.5)
        obj_left = cx - (obj_box_w / 2) + 20
        arcade.draw_text(obj_title, obj_left, obj_box_y + 14, (255, 215, 110), 11, bold=True, anchor_y="center")
        arcade.draw_text(obj_desc, obj_left, obj_box_y - 12, (230, 225, 215), 10, width=obj_box_w - 40, anchor_y="center")

        
        arcade.draw_text("CONTROLS & ACTIONS", cx, cy + 78, (255, 215, 110), 12, bold=True, anchor_x="center", anchor_y="center")

        
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
         
            arcade.draw_rect_filled(arcade.XYWH(cx, ry, row_w, 34), (42, 24, 14, 180))
            arcade.draw_rect_outline(arcade.XYWH(cx, ry, row_w, 34), (90, 60, 40, 140), 1)

          
            badge_w = 170
            badge_h = 24
            badge_x = row_left + 14 + (badge_w / 2)
            arcade.draw_rect_filled(arcade.XYWH(badge_x, ry, badge_w, badge_h), (22, 14, 8, 255))
            arcade.draw_rect_outline(arcade.XYWH(badge_x, ry, badge_w, badge_h), (210, 160, 90, 220), 1.5)
            arcade.draw_text(badge_text, badge_x, ry, (255, 240, 200), 10, bold=True, anchor_x="center", anchor_y="center")

         
            act_x = row_left + 14 + badge_w + 16
            arcade.draw_text(act_label, act_x, ry, (255, 220, 130), 11, bold=True, anchor_x="left", anchor_y="center")

           
            desc_x = act_x + 130
            desc_w = (row_left + row_w - 14) - desc_x
            arcade.draw_text(desc_text, desc_x, ry, (225, 220, 210), 10, anchor_x="left", anchor_y="center", width=int(desc_w))

     
        btn_w, btn_h = 180, 42
        btn_y = cy - 188
        btn_x = cx

      
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
