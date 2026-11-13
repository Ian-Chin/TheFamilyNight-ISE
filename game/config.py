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

WIDTH = 1280
HEIGHT = 720
TITLE = "Terry's Story"

MOVEMENT_SHEET = "terry-movements.png"
IDLE_SHEET = "terry-idle-sheet.png"
IDLE_SHEET_COLS = 2
SHEET_COLS = 4
SHEET_ROWS = 3
JUMP_ROW = 1
WALK_ROWS = (0, 2)

CARRY_DIR = "terry-carry"
CARRY_WALK_FILES = tuple(f"terry-carry-walk-{n}.png" for n in range(1, 7))
CARRY_JUMP_FILES = tuple(f"terry-carry-jump-{n}.png" for n in range(1, 5))
CARRY_IDLE_FILES = ("terry-carry-idle-1.png", "terry-carry-idle-2.png")

CLEAR_ABOVE = 250
OPAQUE_BELOW = 214
SOLID_ALPHA = 40

CHARACTER_ART_HEIGHT = 320

RIM_DARK = 4     # pixels of hard contour, at CHARACTER_ART_HEIGHT
RIM_GLOW = 9     # pixels of soft halo outside the contour
RIM_DARK_COLOR = (24, 18, 30, 255)
RIM_GLOW_COLOR = (255, 250, 232, 150)

IDLE_SHEETS = {
    "Dave.png": "dave-idle-sheet.png",
    "Christine.png": "christine-idle-sheet.png",
    "jess.png": "jess-idle-sheet.png",
    "tom.png": "tom-idle-sheet.png",
}
IDLE_SHEET_FRAMES = 4
NPC_IDLE_FRAME = 0.32    # seconds per breathing frame

WALK_SPEED = 260.0
WALK_FRAME_TIME = 0.11
IDLE_PERIOD = 1.6
JUMP_DURATION = 0.5
JUMP_HEIGHT = 70.0
TERRY_HEIGHT = 118

SHADOW_WIDTH = 0.58    # fraction of the sprite's width
SHADOW_ASPECT = 0.34   # ellipse height over its width
SHADOW_RISE = 4        # canvas units the ellipse sits above the sprite box
SHADOW_COLOR = (18, 14, 10)
SHADOW_ALPHA = 150
SHADOW_JUMP_SHRINK = 0.4   # how much of the shadow a full jump takes away

MENU_BUTTON_W = 300
MENU_BUTTON_H = 62
MENU_TEXT_SIZE = 22
MENU_ICON = 30
MENU_ICON_PAD = 22
MENU_ICON_GAP = 18
MENU_FONT = ("Segoe UI", "Arial", "Helvetica", "sans-serif")

CREDIT_SIZE = 86

PANEL_W = 380
PANEL_H = 200
PLANK_PAD = 10   # room around a widget for its shadow


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
CHAO_PATH_X = 528
CHAO_ENTRY_Y = HEIGHT + 80
CHAO_STOP_Y = 470
CHAO_FADE_IN = 1.6   # seconds of black at the top of the scene
CHAO_WALK_BOUNDS = (60, WIDTH - 60, 60, HEIGHT - 60)
CHAO_OBSTACLES = (
    (160, 298, 278, 525),     # the dinner table; the stools are walked over
    (825, 1115, 210, 370),    # barbecue and the stone counter
    (20, 258, 30, 150),       # pond
    (1025, 1220, 530, 720),   # woodpile and the hut
)

CHAO_STONE_AREAS = (
    (478, 566, 0, HEIGHT),    # the path down the middle of the garden
    (40, 420, 228, 560),      # the patio the dinner table stands on
)


CHAO_DINER_DIR = "chao-diner-frames"
CHAO_SHEET_COLS = 4
CHAO_SHEET_ROWS = 3
CHAO_SHEET_RES = 4       # sheet pixels per canvas unit
CHAO_HEAD_RISE = 0.47    # stool to the middle of the head, as a share of height
CHAO_EAT_FRAME_TIMES = (0.2, 0.2, 0.2, 0.15, 0.12, 0.12,
                        0.13, 0.13, 0.13, 0.13, 1.1, 0.15)
CHAO_TALK_FRAME_TIMES = (0.14,) * 8 + (0.5, 0.15, 0.5, 0.5)

TERRY_SHOCKED = "terry-shocked.png"
TERRY_FACES = {
    "happy": "terry-faces/terry-happy.jpg",
    "nervous": "terry-faces/terry-nervous.jpg",
    "hungry": "terry-faces/terry-hungry.jpg",
    "unimpressed": "terry-faces/terry-unimpressed.png",
}


KID_SHEETS = {"Tom": "tom-run-sheet.png", "Jess": "jess-run-sheet.png"}
KID_SHEET_COLS = 5
KID_SHEET_ROWS = 2
KID_RUN_FRAMES = 7
KID_CAUGHT_FRAMES = 3

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

CHAO_QUEST_RIGHT = WIDTH - 30
CHAO_QUEST_TOP = HEIGHT - 92
CHAO_QUEST_HEADER = "QUESTS"
CHAO_QUEST_HEADER_SIZE = 11
CHAO_QUEST_TITLE_SIZE = 14
CHAO_QUEST_NOTE_SIZE = 11
CHAO_QUEST_ROW_GAP = 44  # top of one quest to the top of the next
CHAO_QUEST_MARKER = 5    # radius of the circle beside each quest
CHAO_QUESTS = (
    ("dinner", "Start the Chao dinner", "Head to the dinner table", False),
    ("family", "Talk to the family", "Say hi to everyone", True),
)
QUEST_DONE = (126, 214, 150)

DUST_INTERVAL = 0.07     # seconds between puffs
DUST_LIFE = 0.55         # seconds a puff lasts
DUST_GRAVITY = 520.0     # pulls the stone chips back down
DUST_GRASS_COLOR = (214, 204, 164, 210)
DUST_STONE_COLOR = (196, 198, 210, 210)
DUST_STONE_CHIP = (138, 140, 156, 255)

PORTRAIT_H = 230
PORTRAIT_INSET = 70      # canvas edge to the near side of a portrait
PORTRAIT_SINK = 40       # how far a portrait tucks down behind the box
PORTRAIT_DIM = (95, 98, 112)
PORTRAIT_SPEAKING_GROW = 1.04

FEET_WIDTH = 0.5    # fraction of the sprite's width
FEET_HEIGHT = 20    # canvas units up from the bottom of the sprite box

DAYCYCLE_SHEET = "Daycycle.png"
DAY_BADGE_BOXES = (
    (71, 112, 838, 298),
    (71, 442, 838, 298),
    (71, 772, 838, 298),
    (71, 1099, 838, 298),
)

FEAST_STAGES = (
    ("chao-dinner-keyword-game/feast-1-full.jpg", "env-stage2.mp4"),
    ("chao-dinner-keyword-game/feast-2-started.jpg", "env-stage3.mp4"),
    ("chao-dinner-keyword-game/feast-3-half-eaten.jpg", "env-stage5.mp4"),
    ("chao-dinner-keyword-game/feast-4-nearly-done.jpg", "env-stage1.mp4"),
    ("chao-dinner-keyword-game/feast-5-cleared.jpg", "env-stage4.mp4"),
)

VIDEO_DIR = BACKGROUND_DIR / "video"
BACKGROUND_VIDEOS = {
    "menu-bg.jpg": "menu.mp4",
    "bbq-scene-bg.jpeg": "garden-food.mp4",
    "chao-dinner-bg.jpg": "garden-empty.mp4",
    "chao-dinner-night.png": "garden-night.mp4",
    "chao-dinner-served.png": "garden-night-dinner.mp4",
    "BBQ-Scene/BBQ_Prep_BG.jpg": "BBQ_Prep_BG.mp4",
    "market-dash/Scene 2.4 - market interior.jpg": "market-interior.mp4",
    **dict(FEAST_STAGES),
}
GRAPHICS_MODES = ("quality", "performance")
VIDEO_QUEUE = 4   # decoded frames held ahead of the one on screen

SETTINGS_TITLE = "Settings"
SETTINGS_ROWS = (
    ("master", "Master", "everything at once"),
    ("sound", "Sound", "footsteps and the interface"),
    ("music", "Music", "the garden ambience"),
)
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

SOUND_EXTENSIONS = (".mp3", ".ogg", ".wav")
SOUND_FILES = {
    "step_grass": ("step-grass", "sound", 0.5),
    "step_stone": ("step-stone", "sound", 0.55),
    "dialog_type": ("dialog-type", "sound", 0.4),
    "dialog_open": ("dialog-open", "sound", 0.7),
    "ui_hover": ("ui-hover", "sound", 0.5),
    "ui_click": ("ui-click", "sound", 0.6),
    "achievement": ("achievement-unlock", "sound", 0.8),
    "ambience_day": ("ambience-day", "music", 1.0),
    "ambience_night": ("ambience-night", "music", 0.6),
    "ending_sfx": ("ending-sfx", "sound", 1.0),
    "menu_music": ("menu-music", "music", 0.5),
    "trailer": ("trailer", "music", 0.8),
    "splash_music": ("splash-music", "music", 0.7),

    "phone_ring": ("phone-ring", "sound", 0.35),
    "phone_pickup": ("phone-pickup", "sound", 0.8),
    "door_slam": ("door-slam", "sound", 0.85),
    "market_ambience": ("market-ambience", "music", 0.55),
    "get_snatched": ("get-snatched", "sound", 0.75),
    "ingredient_get": ("ingredient-get", "sound", 0.75),
    "swing_sword": ("swing-sword", "sound", 0.75),
    "block": ("block", "sound", 0.75),
    "hp_reduced": ("HP_reduced", "sound", 0.8),
    "game_failed": ("Game_failed", "sound", 0.85),
    "game_success": ("Game_success", "sound", 0.85),
    "locked_sound": ("Locked_sound", "sound", 0.75),
    "unlocked_sound": ("Unlocked_sound", "sound", 0.85),
    "walking": ("walking", "sound", 5.10),

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

    "chao_title": ("chao-title", "sound", 0.8),
    "chao_descend": ("chao-descend", "sound", 0.6),
    "chao_shock": ("chao-shock", "sound", 0.8),
    "chao_popup": ("chao-popup", "sound", 0.6),
    "chao_win": ("chao-win", "sound", 0.75),
    "chao_lose": ("chao-lose", "sound", 0.7),
    "chao_laugh": ("chao-laugh", "sound", 0.55),
    "chao_laugh_b": ("chao-laugh-b", "sound", 0.55),
    "chao_whoops": ("chao-whoops", "sound", 0.6),
    "chao_grab": ("chao-grab", "sound", 0.5),
    "chao_seated": ("chao-seated", "sound", 0.6),
    "chao_tick": ("chao-tick", "sound", 0.55),
    "chao_whistle": ("chao-whistle", "sound", 0.6),
    "chao_serve": ("chao-serve", "sound", 0.65),
    "chao_clock": ("chao-clock", "sound", 0.6),
    "chao_swoosh": ("chao-swoosh", "sound", 0.6),

    "bus_music": ("bus-scene/bgm/arcade-rush-bgm", "music", 0.8),
    "bus_engine": ("bus-scene/sfx/bus-drive", "sound", 0.3),
    "bus_horn": ("bus-scene/sfx/bus-horn", "sound", 0.7),
    "bus_crash": ("bus-scene/target-rings/cannon", "sound", 0.7),
    "bus_swish": ("bus-scene/sfx/swish", "sound", 0.55),
    "bus_jump": ("bus-scene/sfx/jump", "sound", 0.58),
    "bus_land": ("bus-scene/sfx/land", "sound", 0.55),
    "bus_warning": ("bus-scene/sfx/warning", "sound", 0.5),
    "bus_protect": ("bus-scene/sfx/protect", "sound", 0.55),
    "bus_fail": ("bus-scene/sfx/fail", "sound", 0.55),
    "bus_cane_hit": ("bus-scene/sfx/cane-hit", "sound", 0.77),
    "bus_paper": ("bus-scene/sfx/paper", "sound", 0.4),
    "bus_chew": ("bus-scene/sfx/chew", "sound", 0.55),
    "bus_fart": ("bus-scene/sfx/fart", "sound", 0.65),
    "bus_gas_fade": ("bus-scene/sfx/gas-fade", "sound", 0.1),
    "bus_scare": ("bus-scene/sfx/scare", "sound", 0.68),
    "bus_food_spill": ("bus-scene/sfx/food-spill", "sound", 0.55),

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
FOOTSTEP_CLIPS = {
    "grass": ("step_grass", 2),
    "stone": ("step_stone", 1),
}
AMBIENCE = "ambience_day"
AMBIENCE_NIGHT = "ambience_night"
AMBIENCE_FADE = 3.0

VOLUME_CHANNELS = (
    ("master", 0.8),
    ("sound", 0.9),
    ("music", 0.7),
)


GLASS_FILL = (8, 10, 14, 165)
GLASS_FILL_HOVER = (26, 31, 40, 205)
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

ACHIEVEMENT_SCENES = ("Market Dash", "Bumpy Bus", "Backyard BBQ", "Chaos Dinner")
ACHIEVEMENTS = (
    ("market_veg", "Market Dash", "Fresh Greens",
     "Gather all 5 vegetables.", False),
    ("market_meat", "Market Dash", "Prime Cuts",
     "Gather all 5 meat items.", False),
    ("market_checkout", "Market Dash", "Checkout Run",
     "Escape through the exit doors.", False),
    ("market_done", "Market Dash", "Dinner Saved",
     "Clear all three market stages.", False),
    ("market_speed", "Market Dash", "Quick Hands",
     "Clear any stage with 20s+ left.", False),
    ("market_full_cart", "Market Dash", "Full Cart",
     "Escape with all 5 items intact.", False),
    ("market_fish_slap", "Market Dash", "Fish Slap",
     "Stun 10 shoppers with mackerel.", False),
    ("market_solid_guard", "Market Dash", "Solid Guard",
     "Block 5 rushing shoppers.", False),
    ("market_strike", "Market Dash", "Strike!",
     "Hit 3 shoppers in one swing.", False),
    ("market_mine_now", "Market Dash", "Mine Now!",
     "Reclaim a dropped item from a thief.", False),
    ("egg_clean_escape", "Market Dash", "Clean Escape",
     "Exit without swinging the fish.", True),
    ("egg_auntie_rush", "Market Dash", "Auntie Rush",
     "Bump into 10 shoppers.", True),
    ("egg_last_second", "Market Dash", "Last Second",
     "Escape with under 3s remaining.", True),

    ("bus_board", "Bumpy Bus", "All Aboard",
     "Board the bus at the station.", False),
    ("bus_brakes", "Bumpy Bus", "Brace Yourself",
     "Ride out 4 hard brakes without falling.", False),
    ("bus_surfer", "Bumpy Bus", "Bus Surfer",
     "Finish the ride without falling over once.", False),
    ("bus_guard", "Bumpy Bus", "Food Guardian",
     "Finish the ride with all the shopping untouched.", False),
    ("bus_dodger", "Bumpy Bus", "Road Warrior",
     "Get through the traffic without a single crash.", False),
    ("bus_arrive", "Bumpy Bus", "Special Delivery",
     "Pull up at home with the shopping.", False),
    ("egg_bus_officer", "Bumpy Bus", "Law Abiding",
     "Hear the officer out before boarding.", True),
    ("egg_bus_close", "Bumpy Bus", "Paint Scraper",
     "Squeeze past 3 vehicles with a near miss.", True),
    ("egg_bus_shout", "Bumpy Bus", "Road Rage",
     "Shout 5 vehicles off the road in one drive.", True),

    ("bbq_prep", "Backyard BBQ", "Prep Time!",
     "Unlock the chopping board to begin prep.", False),
    ("bbq_flawless_chop", "Backyard BBQ", "Master Chef",
     "Chop all ingredients without losing a single life.", False),
    ("bbq_overchop", "Backyard BBQ", "Mashed Potatoes",
     "Click too fast and mash the food into pieces.", True),
    ("bbq_misclick", "Backyard BBQ", "Watch the Fingers!",
     "Miss the food and chop the cutting board 3 times.", True),
    ("bbq_perfect_grill", "Backyard BBQ", "Flawless Flip",
     "Grill all the food perfectly without a single burn strike.", False),
    ("bbq_crunchy", "Backyard BBQ", "Extra Crunchy",
     "Finish the BBQ with 1 or 2 burn strikes.", False),
    ("bbq_charcoal", "Backyard BBQ", "Charcoal Maker",
     "Completely burn the food and fail the BBQ.", True),
    ("bbq_staredown", "Backyard BBQ", "Staring Contest",
     "Let the grill overheat because you forgot to press SPIN.", True),

    ("dinner_family", "Chaos Dinner", "Family Reunion",
     "Talk to everyone in the garden before dinner.", False),
    ("dinner_seated", "Chaos Dinner", "Seat Patrol",
     "Keep Tom and Jess seated long enough to pass.", False),
    ("dinner_perfect", "Chaos Dinner", "Glued to Their Seats",
     "Keep the kids seated 95% of the time.", False),
    ("dinner_done", "Chaos Dinner", "Chaos Dinner",
     "Finish the leftover feast to close the scene.", False),
    ("feast_clear", "Chaos Dinner", "Table Cleared",
     "Eat every leftover before the clock runs out.", False),
    ("feast_speed", "Chaos Dinner", "Speed Eater",
     "Reach 60 WPM in the leftover feast.", False),
    ("feast_flawless", "Chaos Dinner", "Clean Plate",
     "Clear the table with 100% accuracy.", False),
    ("feast_streak", "Chaos Dinner", "On a Roll",
     "Type 20 words in a row without a mistake.", False),
    ("egg_chatter", "Chaos Dinner", "Chatterbox",
     "Talk to the same relative five times.", True),
    ("egg_escape", "Chaos Dinner", "Wriggle Room",
     "Let the kids wriggle free three times in one round.", True),
    ("egg_fast", "Chaos Dinner", "Not Hungry",
     "Let the feast clock run out without eating a word.", True),
)
ACHIEVEMENT_SOUND = "achievement"
ACHIEVEMENT_TOAST_TIME = 3.4   # seconds each unlock popup stays up
