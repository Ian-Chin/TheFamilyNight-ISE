"""Shared constants: asset paths, design canvas, tuning and palette."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SPRITE_DIR = ASSETS / "sprites"
BACKGROUND_DIR = ASSETS / "backgrounds"
UI_DIR = ASSETS / "ui"
ICON_DIR = ASSETS / "icons"
CHARACTER_DIR = ASSETS / "characters"

# The game is laid out on this fixed canvas and scaled to the real window.
WIDTH = 1280
HEIGHT = 720
TITLE = "Terry's Story"

# --- Sprite sources ----------------------------------------------------------
MOVEMENT_SHEET = "terry-movements.png"
IDLE_FILES = ("terry-idle-1.png", "terry-idle-2.png")
SHEET_COLS = 4
SHEET_ROWS = 3
JUMP_ROW = 1
WALK_ROWS = (0, 2)

# The art sits on white paper, so the background is keyed out on a ramp:
# brighter than CLEAR_ABOVE fades away, darker than OPAQUE_BELOW stays solid.
# The ramp stops the anti-aliased outline leaving a white fringe.
CLEAR_ABOVE = 250
OPAQUE_BELOW = 214
SOLID_ALPHA = 40

# --- Gameplay tuning ---------------------------------------------------------
WALK_SPEED = 260.0
WALK_FRAME_TIME = 0.11
IDLE_PERIOD = 1.6
JUMP_DURATION = 0.5
JUMP_HEIGHT = 70.0
TERRY_HEIGHT = 96

# --- Menu layout, in canvas units --------------------------------------------
MENU_ITEMS = [
    ("Play", "play", "play"),
    ("Story", "story", "book"),
    ("Achievement", "achievement", "medal"),
    ("Settings", "settings", "gear"),
    ("Quit", "quit", "power"),
]
LOGO_WIDTH = 310
LOGO_TOP_MARGIN = 18
MENU_RIGHT = WIDTH - 150
MENU_BUTTON_W = 300
MENU_BUTTON_H = 62
MENU_BUTTON_GAP = 16
MENU_TEXT_SIZE = 22
MENU_ICON = 30
MENU_ICON_PAD = 22
MENU_ICON_GAP = 18
MENU_FONT = ("Georgia", "Times New Roman", "serif")

CREDIT_SIZE = 86
CREDIT_MARGIN = 34
CREDIT_ICON = "award"

PANEL_W = 380
PANEL_H = 200
CREDITS_W = 560
CREDITS_H = 320
PLANK_PAD = 10   # room around a widget for its shadow

# --- Chao dinner scene, in canvas units --------------------------------------
CHAO_DINNER_BG = "chao-dinner-bg.jpg"
# The stone path runs down the middle of the art; Terry enters along it from
# above the canvas and stops level with the dinner table.
CHAO_PATH_X = 528
CHAO_ENTRY_Y = HEIGHT + 80
CHAO_STOP_Y = 470
CHAO_FADE_IN = 1.6   # seconds of black at the top of the scene
# The garden is fenced in, so Terry walks the ground inside it.
CHAO_WALK_BOUNDS = (60, WIDTH - 60, 60, HEIGHT - 60)

# --- Pause overlay, in canvas units ------------------------------------------
PAUSE_ITEMS = [
    ("Resume", "resume", "play"),
    ("Settings", "settings", "gear"),
    ("Main Menu", "menu", "book"),
    ("Quit", "quit", "power"),
]
PAUSE_TITLE = "Paused"
PAUSE_BUTTON_W = 280
PAUSE_BUTTON_H = 56
PAUSE_BUTTON_GAP = 14
PAUSE_PANEL_W = 380
PAUSE_TITLE_SIZE = 27
PAUSE_TITLE_GAP = 62   # panel top to the middle of the title
PAUSE_PANEL_PAD = 34   # panel edge to the button stack
PAUSE_DIM = (0, 0, 0, 150)

CREDITS_NAMES = (
    ("TP076848", "Ee Jin Xing"),
    ("TP076218", "Ian Chin Jun Sheng"),
    ("TP075642", "Tang Chee Kin"),
    ("TP075320", "Timothy Ng Chong Sheng"),
)

# --- Palette -----------------------------------------------------------------
INK = (38, 42, 54)
WOOD_BASE = ((162, 110, 62), (94, 58, 30))
WOOD_HOVER = ((206, 150, 78), (128, 82, 38))
STUD_BASE = (206, 170, 104, 255)
STUD_HOVER = (248, 214, 132, 255)
PLANK_EDGE = (52, 30, 14, 255)
CARVED = (247, 231, 197)
CARVED_HOVER = (255, 247, 219)
PARCHMENT_LIGHT = (252, 242, 219)
PARCHMENT_DARK = (228, 207, 168)
