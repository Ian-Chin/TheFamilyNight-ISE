"""Shared constants: asset paths, design canvas, tuning and palette."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SPRITE_DIR = ASSETS / "sprites"
BACKGROUND_DIR = ASSETS / "backgrounds"
UI_DIR = ASSETS / "ui"
ICON_DIR = ASSETS / "icons"
CHARACTER_DIR = ASSETS / "characters"
AUDIO_DIR = ASSETS / "audio"
SETTINGS_FILE = ROOT / "settings.json"

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

# The source art is around a thousand pixels tall but nothing is drawn taller
# than about 130 canvas units, so every cut-out is brought down to this height
# before it is rimmed and uploaded. Ringing a 1024px image costs seconds;
# ringing a 320px one costs milliseconds, and the result is the same on screen.
CHARACTER_ART_HEIGHT = 320

# Characters are drawn in the same value range as the garden they stand in, so
# every cut-out gets a dark contour inside a soft pale halo to hold it apart
# from the background.
RIM_DARK = 4     # pixels of hard contour, at CHARACTER_ART_HEIGHT
RIM_GLOW = 9     # pixels of soft halo outside the contour
RIM_DARK_COLOR = (24, 18, 30, 255)
RIM_GLOW_COLOR = (255, 250, 232, 150)

# --- Gameplay tuning ---------------------------------------------------------
WALK_SPEED = 260.0
WALK_FRAME_TIME = 0.11
IDLE_PERIOD = 1.6
JUMP_DURATION = 0.5
JUMP_HEIGHT = 70.0
TERRY_HEIGHT = 118

# The ground shadow is an ellipse under Terry's feet, sized off his sprite and
# shrinking as he leaves the ground.
SHADOW_WIDTH = 0.58    # fraction of the sprite's width
SHADOW_ASPECT = 0.34   # ellipse height over its width
# The ellipse sits just under the bottom of the sprite box, so it reads as
# ground under Terry's shoes rather than as a stain behind them.
# The rim pads the art, so the bottom of the sprite box now sits a little
# below the shoes and the ellipse is lifted back up to meet them.
SHADOW_RISE = 4        # canvas units the ellipse sits above the sprite box
SHADOW_COLOR = (18, 14, 10)
SHADOW_ALPHA = 150
SHADOW_JUMP_SHRINK = 0.4   # how much of the shadow a full jump takes away

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
# One clean sans across the whole game. Segoe UI is the Windows system face
# and is the nicest of these on screen; Arial and Helvetica cover everywhere
# else, with the generic family as a last resort.
MENU_FONT = ("Segoe UI", "Arial", "Helvetica", "sans-serif")

CREDIT_SIZE = 86
CREDIT_MARGIN = 34
CREDIT_ICON = "award"

PANEL_W = 380
PANEL_H = 200
CREDITS_W = 560
CREDITS_H = 320
PLANK_PAD = 10   # room around a widget for its shadow


# --- BBQ SCENE (CK) --------------------------------------
BBQ_SCENE_BG = "bbq-scene-bg.jpeg"
BBQ_PREP_SCENE_BG = "BBQ-Scene/First person view - Food on top table with Terry.jpg"
BBQ_SCENE_EMPTY_BG = "chao-dinner-bg.jpg"
# Chopping Scene Stages
CHOP_MEAT_BG_1 = "BBQ-Scene/Chopping_meat_begin(Big Knife).jpg"
CHOP_MEAT_BG_2 = "BBQ-Scene/Chopping_meat_deep_into1.jpg"
CHOP_MEAT_BG_3 = "BBQ-Scene/Chopping_meat_in_half.jpg"
CHOP_MEAT_BG_4 = "BBQ-Scene/Chopped_meat_pieces.jpg"

CHOP_CARROT_BG_1 = "BBQ-Scene/Chopping_carrots_begin.jpg"
CHOP_CARROT_BG_2 = "BBQ-Scene/Chopping_carrot_in_half.jpg"
CHOP_CARROT_BG_3 = "BBQ-Scene/Chopped_carrots_pieces.jpg"

CHOP_ONION_BG_1 = "BBQ-Scene/Chopping_onion_begin.jpg"
CHOP_ONION_BG_2 = "BBQ-Scene/Chopping_onion_in_half.jpg"
CHOP_ONION_BG_3 = "BBQ-Scene/Chopped_onion_pieces.jpg"

CHOP_PEPPER_BG_1 = "BBQ-Scene/Chopping_green_pepper_begin.jpg"
CHOP_PEPPER_BG_2 = "BBQ-Scene/Chopping_green_pepper_in_half.jpg"
CHOP_PEPPER_BG_3 = "BBQ-Scene/Chopped_green_pepper_pieces.jpg"

CHOP_EGGPLANT_BG_1 = "BBQ-Scene/Chopping_eggplant_begin.jpg"
CHOP_EGGPLANT_BG_2 = "BBQ-Scene/Chopping_eggplant_deep_into.jpg"
CHOP_EGGPLANT_BG_3 = "BBQ-Scene/Chopping_eggplant_in_half.jpg"
CHOP_EGGPLANT_BG_4 = "BBQ-Scene/Chopped_eggplant_pieces.jpg"

CHOP_FINISH_BG = "BBQ-Scene/Finish_chopping_scene.jpg"

# --- Grilling Scene Stages ---
# Grilled Sequence
GRILL_0_BG = "BBQ-Scene/BBQ_0%_grilled.jpg"
GRILL_20_BG = "BBQ-Scene/BBQ_20%_grilled.jpg"
GRILL_50_BG = "BBQ-Scene/BBQ_50%_grilled.jpg"
GRILL_100_BG = "BBQ-Scene/BBQ_100%_grilled.jpg"

# Burned Sequence
BURN_10_BG = "BBQ-Scene/BBQ_10%_burned_food.jpg"
BURN_20_BG = "BBQ-Scene/BBQ_20%_burned_food.jpg"
BURN_50_BG = "BBQ-Scene/BBQ_50%_burned_food.jpg"
BURN_100_BG = "BBQ-Scene/BBQ_100%_burned_food.jpg"

GRILL_FINISH_BG = "BBQ-Scene/Finish_bbq_scene.jpg"
GRILL_FAILED_BG = "BBQ-Scene/Failed_bbq_scene.jpg"


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
# Solid scenery painted into the background, as (left, right, bottom, top) in
# canvas units. Terry's feet are blocked by these, so he walks around them.
CHAO_OBSTACLES = (
    (160, 298, 278, 525),     # the dinner table; the stools are walked over
    (825, 1115, 210, 415),    # barbecue and the stone counter
    (20, 258, 30, 150),       # pond
    (1025, 1220, 530, 720),   # woodpile and the hut
)

# Ground that rings out as stone under Terry's feet; everywhere else is grass.
CHAO_STONE_AREAS = (
    (478, 566, 0, HEIGHT),    # the path down the middle of the garden
    (40, 420, 228, 560),      # the patio the dinner table stands on
)

# Family standing around the garden, as (name, art file, x, y, height).
CHAO_NPCS = (
    # Kept clear of the bottom of the canvas, so the dialogue box does not
    # cover anyone while the opening line is on screen.
    ("Marcus", "Marcus(dad).png", 790, 318, 126),
    ("Christine", "Christine(mom).png", 392, 432, 122),
    ("Jess", "jess.png", 640, 356, 100),
    ("Tom", "tom.png", 968, 566, 108),
)

# Collision uses a box around Terry's feet rather than the whole sprite, so
# his head can overlap scenery drawn behind him.
FEET_WIDTH = 0.5    # fraction of the sprite's width
FEET_HEIGHT = 20    # canvas units up from the bottom of the sprite box

# --- In-scene HUD, in canvas units -------------------------------------------
DAYCYCLE_SHEET = "Daycycle.png"
# Daycycle.png stacks one badge per phase; these are their boxes in the sheet.
DAY_BADGE_BOXES = (
    (71, 112, 838, 298),
    (71, 442, 838, 298),
    (71, 772, 838, 298),
    (71, 1099, 838, 298),
)
PHASE_NAMES = ("Morning", "Afternoon", "Evening", "Night")
HUD_MARGIN = 22
HUD_GAP = 18
HUD_BADGE_H = 58
HUD_SETTINGS_H = 50
HUD_BACKPACK_H = 58
HUD_MAP_H = 104
HUD_HOVER_GROW = 1.06
# The garden art is busy, so the bare icons sit on a dark plate to stand out.
HUD_PLATE_INSET = 12   # canvas units of plate around an icon
HUD_PLATE_PAD = 8      # room around the plate for its shadow

# --- Settings screen, in canvas units ----------------------------------------
SETTINGS_TITLE = "Audio"
# (mixer channel, label, note under the label)
SETTINGS_ROWS = (
    ("master", "Master", "everything at once"),
    ("sound", "Sound", "footsteps and the interface"),
    ("music", "Music", "the garden ambience"),
)
SETTINGS_PANEL_W = 780
SETTINGS_TITLE_GAP = 84     # panel top to the middle of the title
SETTINGS_ROW_GAP = 108      # between one slider row and the next
SETTINGS_PANEL_PAD = 52     # panel edge to the rows
SETTINGS_LABEL_SIZE = 23
SETTINGS_NOTE_SIZE = 15
SETTINGS_VALUE_SIZE = 20
SETTINGS_HINT_SIZE = 15
SETTINGS_STEP = 0.05        # how much an arrow key moves a slider

SLIDER_W = 340
SLIDER_TRACK_H = 10
SLIDER_KNOB = 24
SLIDER_TRACK = (255, 255, 255, 46)
SLIDER_FILL = (226, 186, 112)
SLIDER_FILL_DIM = (128, 134, 148)
SLIDER_KNOB_COLOR = (250, 244, 232)
SLIDER_KNOB_EDGE = (16, 18, 24)

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

# --- Dialogue box, in canvas units -------------------------------------------
# The box runs almost the full width of the canvas and sits close to the
# bottom edge, so the scene above it stays clear.
DIALOG_MARGIN = 22          # canvas edge to the box on the left, right, bottom
DIALOG_W = WIDTH - 2 * DIALOG_MARGIN
DIALOG_H = 196
DIALOG_BOTTOM = DIALOG_MARGIN
DIALOG_PAD = 40         # box edge to the first character of the line
DIALOG_TEXT_SIZE = 23
DIALOG_LINE_GAP = 36
DIALOG_CHAR_TIME = 0.03     # seconds a character takes to type on
DIALOG_NAME_SIZE = 22
DIALOG_NAME_DROP = 38       # box top to the middle of the speaker's name
DIALOG_FIRST_LINE = 86      # box top to the middle of the first line
DIALOG_HINT_SIZE = 14
DIALOG_ARROW = 17           # side of the blinking "go on" triangle
DIALOG_BLINK = 0.5

BBQ_OPENING_DIALOG = ("Terry", "The food ingredients is finally purchased, is time to start cooking!")
# The opening beat of the scene, once Terry has walked in.
CHAO_OPENING_DIALOG = ("Terry", "test")

# --- Sound -------------------------------------------------------------------
# Clips are looked up by base name: a .mp3 or .ogg dropped into assets/audio
# wins over the .wav that `tools/make_sounds.py` bakes, so a downloaded sound
# replaces the generated one without any code change. Anything missing
# entirely is simply silent.
SOUND_EXTENSIONS = (".mp3", ".ogg", ".wav")
# name -> (base filename, mixer channel, how loud that clip is on its channel)
SOUND_FILES = {
    "step_grass": ("step-grass", "sound", 0.5),
    "step_stone": ("step-stone", "sound", 0.55),
    "dialog_type": ("dialog-type", "sound", 0.4),
    "dialog_open": ("dialog-open", "sound", 0.7),
    "ui_hover": ("ui-hover", "sound", 0.5),
    "ui_click": ("ui-click", "sound", 0.6),
    "ambience_day": ("ambience-day", "music", 0.6),
}
STEP_INTERVAL = 0.32   # seconds between footsteps while walking
# surface -> (clip, how many of Terry's steps one play of that clip covers).
# The grass recording is a left-right pair, so it only fires every other step.
FOOTSTEP_CLIPS = {
    "grass": ("step_grass", 2),
    "stone": ("step_stone", 1),
}
AMBIENCE = "ambience_day"
# The garden fades up out of black over CHAO_FADE_IN; the birds come up the
# same way, a little slower, so the scene does not arrive with a bang.
AMBIENCE_FADE = 3.0

# The mixer's channels and the level each starts at.
VOLUME_CHANNELS = (
    ("master", 0.8),
    ("sound", 0.9),
    ("music", 0.7),
)

CREDITS_NAMES = (
    ("TP076848", "Ee Jin Xing"),
    ("TP076218", "Ian Chin Jun Sheng"),
    ("TP075642", "Tang Chee Kin"),
    ("TP075320", "Timothy Ng Chong Sheng"),
)

# --- Palette -----------------------------------------------------------------
# Every widget is the same piece of smoked glass: a near-black translucent
# panel with a thin bright edge, so the scene reads through it and the text on
# top stays legible over whatever is behind.
GLASS_FILL = (8, 10, 14, 165)
GLASS_FILL_HOVER = (26, 31, 40, 205)
# Panels that carry body text are darker: a busy scene reading through them
# would fight the words.
GLASS_FILL_PANEL = (8, 10, 14, 220)
GLASS_EDGE = (255, 255, 255, 92)
GLASS_EDGE_HOVER = (255, 214, 138, 200)
GLASS_SHEEN = (255, 255, 255, 30)   # the highlight along the top edge
GLASS_SHADOW = (0, 0, 0, 130)

TEXT_BRIGHT = (240, 242, 248)
TEXT_HOVER = (255, 220, 148)
TEXT_DIM = (168, 175, 190)
TEXT_SHADOW = (0, 0, 0)
