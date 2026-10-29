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
# frames left to right, baked from their art.
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
MENU_BUTTON_W = 300
MENU_BUTTON_H = 62
MENU_TEXT_SIZE = 22
MENU_ICON = 30
MENU_ICON_PAD = 22
MENU_ICON_GAP = 18
# One clean sans across the whole game. Segoe UI is the Windows system face
# and is the nicest of these on screen; Arial and Helvetica cover everywhere
# else, with the generic family as a last resort.
MENU_FONT = ("Segoe UI", "Arial", "Helvetica", "sans-serif")

CREDIT_SIZE = 86

PANEL_W = 380
PANEL_H = 200
PLANK_PAD = 10   # room around a widget for its shadow


# --- Chao dinner scene, in canvas units --------------------------------------
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
    (825, 1115, 210, 370),    # barbecue and the stone counter
    (20, 258, 30, 150),       # pond
    (1025, 1220, 530, 720),   # woodpile and the hut
)

# Ground that rings out as stone under Terry's feet; everywhere else is grass.
CHAO_STONE_AREAS = (
    (478, 566, 0, HEIGHT),    # the path down the middle of the garden
    (40, 420, 228, 560),      # the patio the dinner table stands on
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

# --- Leftover feast typing game ---------------------------------------------
# Everyone has gone and Terry is left with the food. The table empties a
# course at a time as words are typed: (still, its looping video), full first.
FEAST_STAGES = (
    ("chao-dinner-keyword-game/Gemini_Generated_Image_5npgt25npgt25npg.jpg", "env-stage2.mp4"),
    ("chao-dinner-keyword-game/Gemini_Generated_Image_aqqpzraqqpzraqqp.jpg", "env-stage3.mp4"),
    ("chao-dinner-keyword-game/Gemini_Generated_Image_tupohwtupohwtupo.jpg", "env-stage5.mp4"),
    ("chao-dinner-keyword-game/Gemini_Generated_Image_1u1t7m1u1t7m1u1t.jpg", "env-stage1.mp4"),
    ("chao-dinner-keyword-game/Gemini_Generated_Image_rpphyjrpphyjrpph.jpg", "env-stage4.mp4"),
)

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
    "BBQ-Scene/BBQ_Prep_BG.jpg": "BBQ_Prep_BG.mp4",
    **dict(FEAST_STAGES),
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

PAUSE_MESSAGE_SIZE = 16
PAUSE_MESSAGE_GAP = 40   # room the message line takes under the title

# --- Sound -------------------------------------------------------------------
# Clips are looked up by base name: a .mp3 or .ogg dropped into assets/audio
# wins over a .wav of the same name, so a downloaded sound replaces the
# generated one without any code change. Anything missing
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
    "ambience_night": ("ambience-night", "music", 0.6),
    # The ending cut scene's burp, chimes and whooshes, timed to its video.
    "ending_sfx": ("ending-sfx", "sound", 1.0),

    #market dash scene
    "phone_ring": ("phone-ring", "sound", 0.75),
    "phone_pickup": ("phone-pickup", "sound", 0.8),
    "door_slam": ("door-slam", "sound", 0.85),
    "market_ambience": ("market-ambience", "music", 0.85),
    "get_snatched": ("get-snatched", "sound", 0.75),
    "ingredient_get": ("ingredient-get", "sound", 0.75),
    "swing_sword": ("swing-sword", "sound", 0.75),
    "block": ("block", "sound", 0.75),

    # leftover feast typing game
    "feast_key": ("feast-key", "sound", 0.55),
    "feast_error": ("feast-error", "sound", 0.7),
    "feast_word": ("feast-word", "sound", 0.5),
    "feast_chomp": ("feast-chomp", "sound", 0.8),
    "feast_stage": ("feast-stage", "sound", 0.75),
    "feast_combo": ("feast-combo", "sound", 0.6),
    "feast_count": ("feast-count", "sound", 0.7),
    "feast_go": ("feast-go", "sound", 0.75),
    "feast_tick": ("feast-tick", "sound", 0.6),
    "feast_whoosh": ("feast-whoosh", "sound", 0.6),
    "feast_win": ("feast-win", "sound", 0.8),
    "feast_lose": ("feast-lose", "sound", 0.8),

    "chop_meat": ("Chop_meat", "sfx", 1.2),
    "chop_table": ("Chop_table", "sfx", 1.0),
    "chop_vege_1": ("Chop_vege_1", "sfx", 2.2),
    "chop_vege_2": ("Chop_vege_2", "sfx", 2.0),
    "click_button": ("Click_Button_Wodden", "sfx", 1.0),
    "game_failed": ("Game_failed", "sfx", 0.3),
    "game_success": ("Game_success", "sfx", 0.8),
    "grilling": ("Grilling_sound", "sfx", 0.6),
    "hp_reduced": ("HP_reduced", "sfx", 1.0),
    "locked": ("Locked_sound", "sfx", 1.0),
    "unlocked": ("Unlocked_sound", "sfx", 1.0),
}
STEP_INTERVAL = 0.32   # seconds between footsteps while walking
# surface -> (clip, how many of Terry's steps one play of that clip covers).
# The grass recording is a left-right pair, so it only fires every other step.
FOOTSTEP_CLIPS = {
    "grass": ("step_grass", 2),
    "stone": ("step_stone", 1),
}
AMBIENCE = "ambience_day"
# Scene 4 and everything after it happens after dark.
AMBIENCE_NIGHT = "ambience_night"
# The garden fades up out of black over CHAO_FADE_IN; the birds come up the
# same way, a little slower, so the scene does not arrive with a bang.
AMBIENCE_FADE = 3.0

# The mixer's channels and the level each starts at.
VOLUME_CHANNELS = (
    ("master", 0.8),
    ("sound", 0.9),
    ("music", 0.7),
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
