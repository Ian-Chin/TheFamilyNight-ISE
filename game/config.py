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
MARKET_SPRITES_DIR = ROOT/ "sprites"
MARKET_PLAYER_DIR = MARKET_SPRITES_DIR / "terry market game"
MARKET_INGREDIENTS_DIR = ASSETS / "market ingredients"
MARKET_SNATCHERS_DIR = ASSETS / "market snatchers"

# The game is laid out on this fixed canvas and scaled to the real window.
WIDTH = 1280
HEIGHT = 720
TITLE = "Terry's Story"

# --- Sprite sources ----------------------------------------------------------
MOVEMENT_SHEET = "terry-movements.png"
# Terry's two idle drawings, side by side on one white sheet.
IDLE_SHEET = "terry-idle-sheet.png"
IDLE_SHEET_COLS = 2
SHEET_COLS = 4
SHEET_ROWS = 3
JUMP_ROW = 1
WALK_ROWS = (0, 2)

# Terry carrying the food tray from the prep table to the chopping board. One
# drawing per file; he walks with the tray held low and idles with it overhead.
CARRY_DIR = "terry-carry"
CARRY_WALK_FILES = tuple(f"terry-carry-walk-{n}.png" for n in range(1, 7))
CARRY_JUMP_FILES = tuple(f"terry-carry-jump-{n}.png" for n in range(1, 5))
CARRY_IDLE_FILES = ("terry-carry-idle-1.png", "terry-carry-idle-2.png")

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

# The family breathing while they stand about: one white sheet per character,
# frames left to right, baked from their art by tools/make_idle_sheets.py.
# Art file -> sheet; art without a sheet just stands still.
IDLE_SHEETS = {
    "Marcus(dad).png": "marcus-idle-sheet.png",
    "Christine(mom).png": "christine-idle-sheet.png",
    "jess.png": "jess-idle-sheet.png",
    "tom.png": "tom-idle-sheet.png",
}
IDLE_SHEET_FRAMES = 4
NPC_IDLE_FRAME = 0.32    # seconds per breathing frame

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
CHOP_MEAT_BG_1 = "BBQ-Scene/Chopping_meat_begin.jpg"
CHOP_MEAT_BG_2 = "BBQ-Scene/Chopping_meat_in_half.jpg"
CHOP_MEAT_BG_3 = "BBQ-Scene/Chopped_meat_pieces.jpg"
CHOP_MEAT_RUINED = "BBQ-Scene/Chopped_meat_ruined.jpg"

CHOP_CARROT_BG_1 = "BBQ-Scene/Chopping_carrot_begin.jpg"
CHOP_CARROT_BG_2 = "BBQ-Scene/Chopping_carrot_in_half.jpg"
CHOP_CARROT_BG_3 = "BBQ-Scene/Chopped_carrot_pieces.jpg"
CHOP_CARROT_RUINED = "BBQ-Scene/Chopped_carrot_ruined.jpg"

CHOP_ONION_BG_1 = "BBQ-Scene/Chopping_onion_begin.jpg"
CHOP_ONION_BG_2 = "BBQ-Scene/Chopping_onion_in_half.jpg"
CHOP_ONION_BG_3 = "BBQ-Scene/Chopped_onion_pieces.jpg"
CHOP_ONION_RUINED = "BBQ-Scene/Chopped_onion_ruined.jpg"

CHOP_PEPPER_BG_1 = "BBQ-Scene/Chopping_green_pepper_begin.jpg"
CHOP_PEPPER_BG_2 = "BBQ-Scene/Chopping_green_pepper_in_half.jpg"
CHOP_PEPPER_BG_3 = "BBQ-Scene/Chopped_green_pepper_pieces.jpg"
CHOP_PEPPER_RUINED = "BBQ-Scene/Chopped_green_pepper_ruined.jpg"

CHOP_EGGPLANT_BG_1 = "BBQ-Scene/Chopping_eggplant_begin.jpg"
CHOP_EGGPLANT_BG_2 = "BBQ-Scene/Chopping_eggplant_deep_into.jpg"
CHOP_EGGPLANT_BG_3 = "BBQ-Scene/Chopping_eggplant_in_half.jpg"
CHOP_EGGPLANT_BG_4 = "BBQ-Scene/Chopped_eggplant_pieces.jpg"
CHOP_EGGPLANT_RUINED = "BBQ-Scene/Chopped_eggplant_ruined.jpg"

CHOP_FINISH_BG = "BBQ-Scene/Finish_chopping_scene.jpg"
CHOP_FAILED_BG = "BBQ-Scene/Failed_chopping_scene.jpg"

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
# Same garden as the BBQ scene, after dark; the layout below still lines up.
CHAO_DINNER_BG = "chao-dinner-night.png"
# The title card comes up while Terry walks in: the garden behind it softens
# into a blur and the words drift up as they fade in, then up and away again.
CHAO_TITLE_KICKER = "S C E N E   4"
CHAO_TITLE = "Chao Dinner"
CHAO_TITLE_TAGLINE = "A family table under the garden lights"
CHAO_KICKER_SIZE = 17
CHAO_TITLE_SIZE = 64
CHAO_TAGLINE_SIZE = 18
CHAO_TITLE_Y = HEIGHT / 2 - 10    # middle of the title line
CHAO_TITLE_DELAY = 0.3   # seconds into the scene before the card starts
CHAO_TITLE_FADE = 0.8    # seconds to fade the card in, and again to fade it out
CHAO_TITLE_HOLD = 1.8    # seconds the card stays fully up
CHAO_TITLE_RISE = 22     # canvas units the words drift up while fading in
CHAO_TITLE_BLUR = 8      # blur radius on the background, in source pixels
CHAO_TITLE_BAND_H = 300  # height of the dark band behind the words
CHAO_TITLE_RULE = 120    # length of the hairline either side of the kicker
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
    ("Marcus", "Marcus(dad).png", 790, 318, 126),
    # Down in the bottom left corner, on the grass between the pond and path.
    ("Christine", "Christine(mom).png", 360, 205, 122),
    ("Jess", "jess.png", 640, 356, 100),
    # Out from under the quest panel in the top right.
    ("Tom", "tom.png", 720, 560, 108),
)

# The "!" over the dinner table, where the dinner is started from.
CHAO_TABLE_MARK = "Exclamation Mark Symbol.png"
CHAO_TABLE_MARK_POS = (229, 478)   # middle of the mark, resting
CHAO_TABLE_MARK_H = 72
CHAO_MARK_BOB = 6        # canvas units the mark bobs up and down
CHAO_MARK_BOB_TIME = 1.2 # seconds for one bob
# How far Terry's feet may stand from the table's edge to start the dinner.
CHAO_TABLE_RANGE = 70

# Starting the dinner: the food fades onto the table, then the screen dips to
# black and comes back up with the family sat round it.
CHAO_DINNER_SERVED_BG = "chao-dinner-served.png"
CHAO_SERVE_FADE = 0.9    # seconds for the food to fade onto the table
CHAO_SERVE_HOLD = 0.8    # seconds to look at the food before the dip
CHAO_SEAT_FADE = 0.45    # seconds down to black, and again back up
CHAO_SEATED_HOLD = 1.2   # seconds of the family at the table before Terry speaks
# Who sits where, as (name, stool x, stool y, height, eating). The stools are
# the six round seats either side of the table; the bottom right one is left
# free. Height is the whole figure, head to shoes, as if standing.
CHAO_SEATS = (
    ("Marcus", 121, 462, 88, True),
    ("Christine", 121, 399, 84, False),
    ("Tom", 121, 336, 82, True),
    ("Jess", 332, 462, 78, False),
    ("Terry", 332, 399, 84, True),
)
# Seated, the head rests just above the middle of the stool, and the shoes
# tuck in just under the head, shifted toward the table as if the legs go
# under it.
CHAO_SEAT_LIFT = 4       # stool middle to the bottom of the head
CHAO_FEET_DROP = 8       # stool middle to the middle of the shoes
CHAO_FEET_SHIFT = 20     # how far the shoes sit toward the table
CHAO_FEET_SWING = 1.5    # canvas units the shoes swing as the legs dangle
CHAO_FEET_SWING_TIME = 1.7
# Where each face's eyes and mouth are, as (left, top, right, bottom) boxes in
# pixels of the cut-out at CHARACTER_ART_HEIGHT, measured off the art. Blinks
# and chewing are painted over these.
CHAO_FACES = {
    "Marcus(dad).png": (((77, 140, 108, 164), (157, 140, 189, 164)), (101, 184, 171, 220)),
    "Christine(mom).png": (((76, 147, 115, 168), (162, 147, 201, 168)), (114, 190, 164, 213)),
    "jess.png": (((112, 120, 155, 146), (204, 120, 248, 146)), (152, 166, 207, 195)),
    "tom.png": (((79, 145, 111, 170), (164, 145, 196, 170)), (112, 183, 165, 213)),
    "Terry": (((99, 154, 108, 203), (156, 154, 164, 203)), (116, 216, 146, 232)),
}
# Terry's face when he arrives and the whole family is already there. It
# replaces his sprite with a few hops, then the opening lines start.
TERRY_SHOCKED = "terry-shocked.png"
CHAO_SHOCK_LEAD = 0.75   # seconds of the shocked face before he speaks
CHAO_SHOCK_HOP = 16      # canvas units of the first hop
CHAO_SHOCK_HOP_TIME = 0.2   # seconds per hop
CHAO_SHOCK_HOPS = 3      # each one lower than the last

# --- Kids at the table mini game --------------------------------------------
# Jess and Tom keep getting up to run around the garden. The player clicks a
# runaway and drags them back: they throw a tantrum all the way, now and then
# yanking the cursor aside, and wriggle free if the escape bar fills before
# they are dropped on the glowing box over their stool. After a while seated
# they run off again.

# One white sheet per kid, like Terry's movement sheet: read left to right,
# top to bottom, the running frames come first and the tantrum frames after.
KID_SHEETS = {"Tom": "tom-run-sheet.png", "Jess": "jess-run-sheet.png"}
KID_SHEET_COLS = 5
KID_SHEET_ROWS = 2
KID_RUN_FRAMES = 7
KID_CAUGHT_FRAMES = 3
KID_HEIGHT = 84          # canvas units, head to shoes, while running
KID_RUN_SPEED = 175.0
KID_RUN_FRAME = 0.08     # seconds per running frame
KID_CAUGHT_FRAME = 0.12  # seconds per tantrum frame
KID_SHAKE = 2.5          # canvas units a carried kid shakes
KID_SEATED_MIN = 2.5     # seconds a returned kid stays put, at least
KID_SEATED_MAX = 6.0     # and at most
# Once the family is seated the camera closes in on the table: the canvas is
# shown CHAO_ZOOM times larger, with CHAO_ZOOM_ORIGIN as the bottom left of
# what is still on screen. CHAO_ZOOM_VIEW is that part, as (left, right,
# bottom, top).
CHAO_ZOOM = 1.6
CHAO_ZOOM_ORIGIN = (0, 176)
CHAO_ZOOM_VIEW = (
    CHAO_ZOOM_ORIGIN[0], CHAO_ZOOM_ORIGIN[0] + WIDTH / CHAO_ZOOM,
    CHAO_ZOOM_ORIGIN[1], CHAO_ZOOM_ORIGIN[1] + HEIGHT / CHAO_ZOOM,
)
# Where a kid's feet may go, kept far enough in from the edges of the zoomed
# view that the whole kid, and the escape bar over their head, stay on screen.
KID_BOUNDS = (
    CHAO_ZOOM_VIEW[0] + 36, CHAO_ZOOM_VIEW[1] - 36,
    CHAO_ZOOM_VIEW[2] + 16, CHAO_ZOOM_VIEW[3] - KID_HEIGHT - 30,
)
# Ground the kids run about on, as (left, right, bottom, top); targets are
# picked in here. They path round the scenery in CHAO_OBSTACLES on a grid of
# KID_GRID cells, keeping KID_CLEARANCE between their feet and its edges.
KID_RUN_AREA = KID_BOUNDS
KID_GRID = 20
KID_CLEARANCE = 24
KID_HIT_PAD = 10         # extra canvas units round a kid that still grabs
# Carrying: the escape bar fills over KID_ESCAPE_TIME; full, they get away and
# cannot be grabbed again for KID_ESCAPE_COOLDOWN.
KID_ESCAPE_TIME = 3.2
KID_ESCAPE_COOLDOWN = 0.8
KID_BAR_W = 74
KID_BAR_H = 9
KID_BAR_GAP = 10         # top of the kid's head to the bar
KID_BAR_SAFE = (126, 214, 150)
KID_BAR_DANGER = (236, 92, 80)
# Every so often a carried kid tugs the cursor: a short shove in a random
# direction, spread over a few frames so it reads as a yank, not a teleport.
KID_TUG_EVERY = (0.7, 1.5)   # seconds between tugs, picked at random
KID_TUG = (28, 48)           # canvas units a tug moves the cursor
KID_TUG_TIME = 0.12
# The drop box over each kid's stool while they are being carried.
KID_SEAT_BOX = (84, 104)     # width and height, canvas units
KID_SEAT_BOX_RISE = 22       # stool middle to the middle of the box
KID_SEAT_COLOR = (255, 214, 138)
KID_SEAT_READY = (126, 214, 150)   # once the kid is over it
KIDS_GAME_TIME = 40.0    # seconds the mini game lasts
KIDS_GOOD_SHARE = 0.75   # share of the time seated needed to move on
# The timer plank at the top middle of the screen.
KIDS_HUD_TOP = HEIGHT - 26
KIDS_HUD_W = 300
KIDS_HUD_H = 76
KIDS_TIMER_SIZE = 26
KIDS_HUD_NOTE_SIZE = 12
KIDS_HINT = "Drag a runaway kid onto their glowing seat before they wriggle free"

# Eating, one bite at a time: the hand on the table side reaches for the
# plate, brings a morsel up to the mouth, and the mouth chews it while the
# hand settles back. Then a pause before the next bite.
CHAO_REACH_TIME = 0.45   # seconds out to the plate, and again up to the mouth
CHAO_CHEW_TIME = 0.26    # seconds per chew
CHAO_CHEWS = 4
CHAO_BITE_GAP = 1.3      # seconds of rest between one bite and the next
CHAO_PLATE_REACH = 22    # canvas units past the head's side the plate is
CHAO_CHEW_BOB = 2.5      # canvas units a chew lifts the head
CHAO_CHEW_SQUASH = 0.04  # share of the head's height a chew squashes away
CHAO_BITE_LEAN = 6       # degrees leaned toward the table over a bite
CHAO_MORSEL = 9          # canvas units across the bite of food
# Those not eating chat: the mouth flaps in bursts and the hands gesture.
CHAO_TALK_FLAP = 0.14    # seconds per mouth open or shut while talking
CHAO_TALK_BURST = 1.6    # seconds of talking, then the same again quiet
CHAO_GESTURE = 3         # canvas units the hands bob while talking
CHAO_SWAY_TIME = 2.8
CHAO_SWAY_ANGLE = 2.5
CHAO_SWAY_BOB = 1.2
# Everyone blinks every few seconds, each on their own beat.
CHAO_BLINK_EVERY = 3.4
CHAO_BLINK_TIME = 0.13

# How close Terry's feet must be to someone's for the interact prompt to show.
CHAO_TALK_RANGE = 120
CHAO_PROMPT_LABEL = "Interact"
CHAO_PROMPT_KEY = "Enter"
CHAO_PROMPT_H = 42
CHAO_PROMPT_SIZE = 16
CHAO_PROMPT_KEY_SIZE = 13
CHAO_PROMPT_PAD = 14     # plank edge to the label, and label to the key
CHAO_KEYCAP_W = 58
CHAO_KEYCAP_H = 26
CHAO_PROMPT_GAP = 16     # top of a character's head to the pointer's tip
CHAO_PROMPT_POINTER = 9  # height of the little arrow under the prompt
CHAO_PROMPT_BOB = 3

# Quest tracker in the top right corner, dropped a little below the edge.
# Bare text on the scene, right aligned, with a drop shadow to keep it legible.
CHAO_QUEST_RIGHT = WIDTH - 30
CHAO_QUEST_TOP = HEIGHT - 92
CHAO_QUEST_HEADER = "QUESTS"
CHAO_QUEST_HEADER_SIZE = 11
CHAO_QUEST_TITLE_SIZE = 14
CHAO_QUEST_NOTE_SIZE = 11
CHAO_QUEST_ROW_GAP = 44  # top of one quest to the top of the next
CHAO_QUEST_MARKER = 5    # radius of the circle beside each quest
# (key, title, note under the title, optional)
CHAO_QUESTS = (
    ("dinner", "Start the Chao dinner", "Head to the dinner table", False),
    ("family", "Talk to the family", "Say hi to everyone", True),
)
QUEST_DONE = (126, 214, 150)

# Dust kicked up behind Terry's feet while he walks.
DUST_INTERVAL = 0.07     # seconds between puffs
DUST_LIFE = 0.55         # seconds a puff lasts
DUST_GRAVITY = 520.0     # pulls the stone chips back down
DUST_GRASS_COLOR = (214, 204, 164, 210)
DUST_STONE_COLOR = (196, 198, 210, 210)
DUST_STONE_CHIP = (138, 140, 156, 255)

# Standing portraits over the dialogue box: Terry on the left, whoever he is
# talking to on the right. The one not speaking is dimmed.
PORTRAIT_H = 230
PORTRAIT_INSET = 70      # canvas edge to the near side of a portrait
PORTRAIT_SINK = 40       # how far a portrait tucks down behind the box
PORTRAIT_DIM = (95, 98, 112)
PORTRAIT_SPEAKING_GROW = 1.04

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

# --- Animated backgrounds ----------------------------------------------------
VIDEO_DIR = BACKGROUND_DIR / "video"
# Still art -> the looping video drawn in its place in quality mode. The still
# stays the fallback: performance mode, or a video that fails to open.
BACKGROUND_VIDEOS = {
    "menu-bg.jpg": "menu.mp4",
    "bbq-scene-bg.jpeg": "garden-food.mp4",
    "chao-dinner-bg.jpg": "garden-empty.mp4",
    "chao-dinner-night.png": "garden-night.mp4",
    "chao-dinner-served.png": "garden-night-dinner.mp4",
}
GRAPHICS_MODES = ("quality", "performance")
VIDEO_QUEUE = 4   # decoded frames held ahead of the one on screen

# --- Settings screen, in canvas units ----------------------------------------
SETTINGS_TITLE = "Settings"
# (mixer channel, label, note under the label)
SETTINGS_ROWS = (
    ("master", "Master", "everything at once"),
    ("sound", "Sound", "footsteps and the interface"),
    ("music", "Music", "the garden ambience"),
)
# (value, caption) for the graphics row under the sliders.
GRAPHICS_CHOICES = (("quality", "Quality"), ("performance", "Performance"))
SETTINGS_PANEL_W = 780
SETTINGS_TITLE_GAP = 84     # panel top to the middle of the title
SETTINGS_ROW_GAP = 108      # between one slider row and the next
SETTINGS_PANEL_PAD = 52     # panel edge to the rows
SETTINGS_LABEL_SIZE = 23
SETTINGS_NOTE_SIZE = 15
SETTINGS_VALUE_SIZE = 20
SETTINGS_HINT_SIZE = 15
SETTINGS_CHOICE_H = 38      # height of the graphics mode switch
SETTINGS_CHOICE_SIZE = 16
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
# Terry arrives to find everyone already in the garden. The first line is
# said with the shocked face.
CHAO_SHOCK_DIALOG = (
    ("Terry", "Whoa! Everyone's here already? That was fast!"),
    ("Terry", "Okay, okay. Lights are up, family's here. Time to set up dinner at the table."),
)
# The table prompt, and the card that asks before the mini game starts.
CHAO_TABLE_PROMPT = "Set up"
CHAO_SETUP_TITLE = "Dinner Time"
CHAO_SETUP_MESSAGE = "You are about to enter a mini game."
CHAO_SETUP_ITEMS = [
    ("Set up", "setup", "play"),
    ("Wait", "wait", "book"),
]
# Table talk once everyone is seated, ending with the kids running off.
CHAO_TABLE_TALK = (
    ("Terry", "Dinner is served, everyone! Dig in before the food gets cold."),
    ("Marcus", "Now this is a proper feast. Well done, son."),
    ("Christine", "Kids, vegetables first, then the chicken."),
    ("Jess", "Psst, Tom. Want to run around?"),
    ("Tom", "Yes! Race you to the grill!"),
)
# The results card at the end of the mini game.
KIDS_WIN_TITLE = "Dinner Saved!"
KIDS_LOSE_TITLE = "What a Mess!"
KIDS_RESULT_MESSAGE = "The kids stayed seated {share}% of the time."
KIDS_RETRY_MESSAGE = "The kids stayed seated {share}% of the time. You need {need}% to move on."
KIDS_WIN_ITEMS = [
    ("Continue", "continue", "book"),
    ("Play again", "retry", "play"),
]
KIDS_LOSE_ITEMS = [
    ("Try again", "retry", "play"),
]
# Terry once the mini game is over and he carries on.
CHAO_AFTER_GAME_DIALOG = (
    ("Terry", "Phew. Finally, a quiet dinner with the whole family."),
)
PAUSE_MESSAGE_SIZE = 16
PAUSE_MESSAGE_GAP = 40   # room the message line takes under the title
# Sample lines, one per family member, said when Terry talks to them.
# A short exchange with each family member: their line, then Terry's reply.
CHAO_NPC_DIALOG = {
    "Marcus": (
        ("Marcus", "Smells good, son. Your steak has a reputation to live up to tonight, you know."),
        ("Terry", "No pressure then, Dad. I got the best cuts the market had left."),
    ),
    "Christine": (
        ("Christine", "Look at all these lights! Come, sit down. You must be starving after all that running around."),
        ("Terry", "Starving and a little sunburnt, Mom. Worth it though."),
    ),
    "Jess": (
        ("Jess", "Did you really survive the market this morning? I heard it was a total war zone."),
        ("Terry", "Barely. I had to wrestle a stranger for the last fish."),
    ),
    "Tom": (
        ("Tom", "Is the food ready yet? I have been smelling that grill for an hour!"),
        ("Terry", "Almost, Tom. Hold on just a little longer."),
    ),
}

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

    #market dash scene
    "phone_ring": ("phone-ring", "sound", 0.75),
    "phone_pickup": ("phone-pickup", "sound", 0.8),
    "door_slam": ("door-slam", "sound", 0.85),
    "market_ambience": ("market-ambience", "music", 0.85),
    "get_snatched": ("get-snatched", "sound", 0.75),
    "ingredient_get": ("ingredient-get", "sound", 0.75),
    "swing_sword": ("swing-sword", "sound", 0.75),
    "block": ("block", "sound", 0.75)
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

KEYCAP_FACE = (244, 238, 226, 255)
KEYCAP_LIP = (176, 164, 146, 255)
KEYCAP_EDGE = (40, 34, 30, 160)
KEYCAP_TEXT = (36, 30, 26)
TITLE_BAND_COLOR = (6, 8, 14)
TITLE_BAND_ALPHA = 170
