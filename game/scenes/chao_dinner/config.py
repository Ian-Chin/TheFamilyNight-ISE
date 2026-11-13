"""Constants only the chao dinner scene uses. Shared ones stay in game/config.py."""

from ...config import HEIGHT, WIDTH


CHAO_DINNER_BG = "chao-dinner-night.png"
CHAO_TITLE_BLUR = 8
CHAO_SKY_BG = "chao-dinner-sky.png"
CHAO_SKY_HOLD = 0.0
CHAO_SKY_PAN = 3.0

CHAO_NPCS = (
    ("Dave", "Dave.png", 790, 318, 126),
    ("Christine", "Christine.png", 360, 205, 122),
    ("Jess", "jess.png", 640, 356, 100),
    ("Tom", "tom.png", 720, 560, 108),
)

CHAO_TABLE_MARK = "Exclamation Mark Symbol.png"
CHAO_TABLE_MARK_POS = (229, 478)
CHAO_TABLE_MARK_H = 72
CHAO_MARK_BOB = 6
CHAO_MARK_BOB_TIME = 1.2
CHAO_TABLE_RANGE = 70

CHAO_DINNER_SERVED_BG = "chao-dinner-served.png"
CHAO_SERVE_FADE = 0.9
CHAO_SERVE_HOLD = 0.8
CHAO_SEAT_FADE = 0.45
CHAO_SEATED_HOLD = 1.2
CHAO_SEATS = (
    ("Dave", 121, 462, 88, True),
    ("Christine", 121, 399, 84, False),
    ("Tom", 121, 336, 82, True),
    ("Jess", 332, 462, 78, False),
    ("Terry", 332, 399, 84, True),
)
CHAO_SHOCK_LEAD = 0.75
CHAO_SHOCK_HOP = 16
CHAO_SHOCK_HOP_TIME = 0.2
CHAO_SHOCK_HOPS = 3


KID_HEIGHT = 84
KID_RUN_SPEED = 175.0
KID_RUN_FRAME = 0.08
KID_CAUGHT_FRAME = 0.12
KID_SHAKE = 2.5
KID_SEATED_MIN = 2.5
KID_SEATED_MAX = 6.0
CHAO_ZOOM = 1.6
CHAO_ZOOM_ORIGIN = (0, 176)
CHAO_ZOOM_VIEW = (
    CHAO_ZOOM_ORIGIN[0], CHAO_ZOOM_ORIGIN[0] + WIDTH / CHAO_ZOOM,
    CHAO_ZOOM_ORIGIN[1], CHAO_ZOOM_ORIGIN[1] + HEIGHT / CHAO_ZOOM,
)
KID_BOUNDS = (
    CHAO_ZOOM_VIEW[0] + 36, CHAO_ZOOM_VIEW[1] - 36,
    CHAO_ZOOM_VIEW[2] + 16, CHAO_ZOOM_VIEW[3] - KID_HEIGHT - 30,
)
KID_RUN_AREA = KID_BOUNDS
KID_GRID = 20
KID_CLEARANCE = 24
KID_HIT_PAD = 10
KID_ESCAPE_TIME = 3.2
KID_ESCAPE_COOLDOWN = 0.8
KID_BAR_W = 74
KID_BAR_H = 9
KID_BAR_GAP = 10
KID_BAR_SAFE = (126, 214, 150)
KID_BAR_DANGER = (236, 92, 80)
KID_TUG_EVERY = (0.7, 1.5)
KID_TUG = (28, 48)
KID_TUG_TIME = 0.12
KID_SEAT_BOX = (84, 104)
KID_SEAT_BOX_RISE = 22
KID_SEAT_COLOR = (255, 214, 138)
KID_SEAT_READY = (126, 214, 150)
KIDS_GAME_TIME = 40.0
KIDS_HURRY = 10
KIDS_GOOD_SHARE = 0.75
KIDS_HUD_TOP = HEIGHT - 26
KIDS_HUD_W = 300
KIDS_HUD_H = 76
KIDS_TIMER_SIZE = 26
KIDS_HUD_NOTE_SIZE = 12
KIDS_HINT = "Drag a runaway kid onto their glowing seat before they wriggle free"

CHAO_TALK_RANGE = 120


PHASE_NAMES = ("Morning", "Afternoon", "Evening", "Night")
HUD_MARGIN = 22
HUD_GAP = 18
HUD_BADGE_H = 58
HUD_SETTINGS_H = 50
HUD_BACKPACK_H = 58
HUD_MAP_H = 104
HUD_HOVER_GROW = 1.06
HUD_PLATE_INSET = 12
HUD_PLATE_PAD = 8


FEAST_STAGE_LINES = (
    "Salad and pie, gone!",
    "The roast chicken is history!",
    "Just the bread and crumbs left...",
    "Clean plates! Every last bite!",
)
FEAST_TIME = 60.0
FEAST_GOAL_WORDS = 36
FEAST_MAX_EXTRA = 8
FEAST_STAGE_FADE = 0.9
FEAST_COUNT_STEP = 0.7
FEAST_HURRY = 10
FEAST_COMBO_EVERY = 10
FEAST_SCENE_BOTTOM = 286
FEAST_CROP = 0.33
FEAST_TABLE_AREA = (330, 1180, 360, 560)
FEAST_FLOOR = (13, 15, 21)
FEAST_FONT = ("Consolas", "Cascadia Mono", "Courier New", "monospace")
FEAST_WORD_SIZE = 46
FEAST_WORD_Y = 352
FEAST_QUEUE = ((290, 26, 215), (252, 21, 140), (220, 17, 75))
FEAST_SLIDE = 0.2
FEAST_OUT_TIME = 0.4
FEAST_UNTYPED = (118, 124, 140)
FEAST_CORRECT = (236, 232, 222)
FEAST_WRONG = (236, 92, 80)
FEAST_EXTRA = (150, 54, 50)
FEAST_CARET = (255, 204, 110)
FEAST_KEY_ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")
FEAST_KEY_W = 40
FEAST_KEY_H = 32
FEAST_KEY_GAP = 5
FEAST_KEY_TOP = 168
FEAST_SPACE_W = 250
FEAST_KEY_GLOW = 0.28
FEAST_KEY_HIT = (126, 214, 150)
FEAST_KEY_FACE = (26, 29, 38, 255)
FEAST_KEY_EDGE = (255, 255, 255, 46)
FEAST_WORDS = (
    "the", "be", "of", "and", "a", "to", "in", "he", "have", "it", "that",
    "for", "they", "with", "as", "not", "on", "she", "at", "by", "this",
    "we", "you", "do", "but", "from", "or", "which", "one", "would", "all",
    "will", "there", "say", "who", "make", "when", "can", "more", "if", "no",
    "man", "out", "other", "so", "what", "time", "up", "go", "about", "than",
    "into", "could", "state", "only", "new", "year", "some", "take", "come",
    "these", "know", "see", "use", "get", "like", "then", "first", "any",
    "work", "now", "may", "such", "give", "over", "think", "most", "even",
    "find", "day", "also", "after", "way", "many", "must", "look", "before",
    "great", "back", "through", "long", "where", "much", "should", "well",
    "people", "down", "own", "just", "because", "good", "each", "those",
    "feel", "seem", "how", "high", "too", "place", "little", "world", "very",
    "still", "hand", "old", "life", "tell", "write", "become", "here",
    "show", "house", "both", "between", "need", "mean", "call", "develop",
    "under", "last", "right", "move", "thing", "general", "school", "never",
    "same", "another", "begin", "while", "number", "part", "turn", "real",
    "leave", "might", "want", "point", "form", "off", "child", "few",
    "small", "since", "against", "ask", "late", "home", "interest", "large",
    "family", "dinner", "table", "chicken", "bread", "salad", "pie", "plate",
    "fork", "spoon", "knife", "cheese", "carrot", "steak", "garden", "lights",
    "lantern", "grill", "smoke", "night", "bite", "chew", "taste", "sweet",
    "salty", "crispy", "warm", "full", "hungry", "feast", "eat", "food",
    "crumb", "gravy", "roast", "butter", "pepper", "onion", "potato", "juice",
)


CHAO_SHOCK_DIALOG = (
    ("Terry", "Whoa! Everyone's here already? That was fast!"),
    ("Terry", "Okay, okay. Lights are up, Dave and the family are here. Time to set up dinner at the table.", "happy"),
)
CHAO_TABLE_PROMPT = "Set up"
CHAO_SETUP_TITLE = "Dinner Time"
CHAO_SETUP_MESSAGE = "You are about to enter a mini game."
CHAO_SETUP_ITEMS = [
    ("Set up", "setup", "play"),
    ("Wait", "wait", "book"),
]
CHAO_COUNTDOWN = 3
CHAO_COUNT_GO = 0.6
CHAO_COUNT_SIZE = 110
CHAO_TABLE_TALK = (
    ("Terry", "Dinner is served, everyone! Dig in before the food gets cold.", "happy"),
    ("Dave", "Now this is a proper feast. You really outdid yourself, cousin."),
    ("Christine", "Kids, vegetables first, then the chicken."),
    ("Jess", "Psst, Tom. Want to run around?"),
    ("Tom", "Yes! Race you to the grill!"),
)
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
CHAO_AFTER_GAME_DIALOG = (
    ("Terry", "Phew. Finally, a quiet dinner with the whole family.", "happy"),
)
CHAO_SKIP_TEXT = "30 minutes later..."
CHAO_SKIP_FADE = 0.6
CHAO_SKIP_HOLD = 2.4
CHAO_FULL_DIALOG = (
    ("Dave", "Ahh, I'm stuffed. I couldn't eat another bite if I tried."),
    ("Christine", "Me too. Thank you for having us, Terry. Lovely dinner!"),
    ("Dave", "Good job tonight, cousin. I'll go warm up the car."),
    ("Jess", "Can we go play now? Come on, Tom!"),
    ("Tom", "Yay! Bye Terry! Thanks for the food!"),
)
CHAO_LEAVE_FADE = 0.55
CHAO_ALONE_DIALOG = (
    ("Terry", "Wait... everyone's gone? But there's still SO much food left!"),
    ("Terry", "I'm not letting a single bite go to waste. Time to finish this feast.", "hungry"),
)
CHAO_ALONE_SPOT = (420, 392)
CHAO_FEAST_PROMPT = "Eat"
CHAO_FEAST_TITLE = "Leftover Feast"
CHAO_FEAST_MESSAGE = "You are about to enter a typing mini game."
CHAO_FEAST_ITEMS = [
    ("Start", "feast", "play"),
    ("Wait", "wait", "book"),
]
CHAO_NPC_DIALOG = {
    "Dave": (
        ("Dave", "Smells good, cousin. I told the whole family your steak was legendary, so no pressure."),
        ("Terry", "Thanks for that, Dave. I got the best cuts the market had left.", "nervous"),
    ),
    "Christine": (
        ("Christine", "Look at all these lights! Come, sit down. You must be starving after all that running around."),
        ("Terry", "Starving and a little sunburnt, Christine. Worth it though.", "hungry"),
    ),
    "Jess": (
        ("Jess", "Did you really survive the market this morning? I heard it was a total war zone."),
        ("Terry", "Barely. I had to wrestle a stranger for the last fish.", "nervous"),
    ),
    "Tom": (
        ("Tom", "Is the food ready yet? I have been smelling that grill since we got out of the car!"),
        ("Terry", "Almost, Tom. Hold on just a little longer.", "unimpressed"),
    ),
}


CHAO_AMBIENT = (0.72, 0.78, 1.0)
CHAO_LIGHTS = (
    (230, 395, 300, 1.0, (0.55, 0.36, 0.14), 0.06),
    (878, 370, 230, 1.2, (0.80, 0.30, 0.06), 0.22),
    (140, 72, 170, 0.7, (0.10, 0.26, 0.50), 0.0),
    (150, 708, 210, 0.6, (0.50, 0.38, 0.18), 0.10),
    (470, 708, 210, 0.6, (0.50, 0.38, 0.18), 0.10),
    (790, 708, 210, 0.6, (0.50, 0.38, 0.18), 0.10),
    (1110, 708, 210, 0.6, (0.50, 0.38, 0.18), 0.10),
    (330, 66, 190, 0.5, (0.50, 0.38, 0.18), 0.10),
    (720, 66, 190, 0.5, (0.50, 0.38, 0.18), 0.10),
    (1100, 66, 190, 0.5, (0.50, 0.38, 0.18), 0.10),
)
CHAO_VIGNETTE = 0.5

RESULT_STYLES = {
    "win": {"wash": (12, 60, 30, 150), "accent": (76, 186, 110), "title": (150, 236, 168)},
    "lose": {"wash": (70, 12, 16, 150), "accent": (214, 72, 72), "title": (250, 150, 146)},
}
RESULT_STRIPE_H = 6
RESULT_BADGE_R = 26
CHAO_GRAIN = 0.035

CHAO_FOCUS_BLUR = 5.0
CHAO_FOCUS_TIME = 1.4
CHAO_FOCUS_SPOT = (230, 400, 190, 420)

CHAO_SHOCK_FOCUS = 120
CHAO_SHOCK_FADE = 0.22
CHAO_SPEED_LINES = 44
CHAO_PUNCH = 0.09
CHAO_PUNCH_TIME = 0.5

CHAO_ESCAPE_SHAKE = 9.0
CHAO_ESCAPE_DECAY = 2.6
CHAO_SKIP_SPEED = 5.0

KID_TRAIL = 6
KID_TRAIL_EVERY = 0.035
KID_SPARKLES = 22
