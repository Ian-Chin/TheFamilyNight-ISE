"""Constants only the chao dinner scene uses. Shared ones stay in game/config.py."""

from ...config import HEIGHT, WIDTH


# --- Chao dinner scene, in canvas units --------------------------------------
# Same garden as the BBQ scene, after dark; the layout below still lines up.
CHAO_DINNER_BG = "chao-dinner-night.png"
CHAO_TITLE_BLUR = 8      # blur radius on the background, in source pixels

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
CHAO_SHOCK_LEAD = 0.75   # seconds of the shocked face before he speaks
CHAO_SHOCK_HOP = 16      # canvas units of the first hop
CHAO_SHOCK_HOP_TIME = 0.2   # seconds per hop
CHAO_SHOCK_HOPS = 3      # each one lower than the last


# --- Kids at the table mini game --------------------------------------------
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

# How close Terry's feet must be to someone's for the interact prompt to show.
CHAO_TALK_RANGE = 120


# --- In-scene HUD, in canvas units -------------------------------------------
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


# --- Leftover feast typing game ---------------------------------------------
# Said as each course goes, for stages 1 to 4.
FEAST_STAGE_LINES = (
    "Salad and pie, gone!",
    "The roast chicken is history!",
    "Just the bread and crumbs left...",
    "Clean plates! Every last bite!",
)
FEAST_TIME = 60.0         # seconds on the clock
FEAST_GOAL_WORDS = 36     # correct words that clear the whole table
FEAST_MAX_EXTRA = 8       # extra letters allowed past the end of a word
FEAST_STAGE_FADE = 0.9    # seconds one course crossfades into the next
FEAST_COUNT_STEP = 0.7    # seconds per number of the count in
FEAST_HURRY = 10          # seconds left when the clock turns red and ticks
FEAST_COMBO_EVERY = 10    # clean words in a row between combo fanfares
# The garden fills the top of the screen, cropped to the table: the top
# FEAST_CROP of the art is cut off and its foot stops at FEAST_SCENE_BOTTOM.
FEAST_SCENE_BOTTOM = 286
FEAST_CROP = 0.33
FEAST_TABLE_AREA = (330, 1180, 360, 560)   # where the crumbs fly from
FEAST_FLOOR = (13, 15, 21)       # the dark ground the keyboard sits on
# Words come one at a time: the one to type sits big in the middle, and the
# next few wait in a stack under it, each sliding up a place as a word is done.
FEAST_FONT = ("Consolas", "Cascadia Mono", "Courier New", "monospace")
FEAST_WORD_SIZE = 46      # the word being typed
FEAST_WORD_Y = 352        # middle of the word being typed
# The waiting words under it: (canvas y, font size, opacity), nearest first.
FEAST_QUEUE = ((290, 26, 215), (252, 21, 140), (220, 17, 75))
FEAST_SLIDE = 0.2         # seconds for the stack to move up a place
FEAST_OUT_TIME = 0.4      # seconds the finished word floats up and fades
FEAST_UNTYPED = (118, 124, 140)
FEAST_CORRECT = (236, 232, 222)
FEAST_WRONG = (236, 92, 80)
FEAST_EXTRA = (150, 54, 50)
FEAST_CARET = (255, 204, 110)
# On-screen keyboard under the words.
FEAST_KEY_ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")
FEAST_KEY_W = 40
FEAST_KEY_H = 32
FEAST_KEY_GAP = 5
FEAST_KEY_TOP = 168       # top of the first row
FEAST_SPACE_W = 250
FEAST_KEY_GLOW = 0.28     # seconds a pressed key stays lit
FEAST_KEY_HIT = (126, 214, 150)
FEAST_KEY_FACE = (26, 29, 38)
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


# --- Dialogue lines ----------------------------------------------------------
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
# The count in before each round of the kids game: seconds of 3, 2, 1, then
# how long "GO!" stays up once they are off.
CHAO_COUNTDOWN = 3
CHAO_COUNT_GO = 0.6
CHAO_COUNT_SIZE = 110
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
# A while later: the screen dips to black over a clock, and the family are
# full. They head off one by one and leave Terry with the rest of the food.
CHAO_SKIP_TEXT = "30 minutes later..."
CHAO_SKIP_FADE = 0.6     # seconds down to black, and again back up
CHAO_SKIP_HOLD = 2.4     # seconds the clock spins on the black
CHAO_FULL_DIALOG = (
    ("Marcus", "Ahh, I'm stuffed. I couldn't eat another bite if I tried."),
    ("Christine", "Me too. I'll go put my feet up and catch my drama. Lovely dinner, Terry!"),
    ("Marcus", "Good job tonight, son. I'm off to watch the match."),
    ("Jess", "Can we go play now? Come on, Tom!"),
    ("Tom", "Yay! Bye Terry! Thanks for the food!"),
)
CHAO_LEAVE_FADE = 0.55   # seconds down to black while the family leave
# Terry alone at the table, the first line with the shocked face.
CHAO_ALONE_DIALOG = (
    ("Terry", "Wait... everyone's gone? But there's still SO much food left!"),
    ("Terry", "I'm not letting a single bite go to waste. Time to finish this feast."),
)
# Where Terry stands once he gets up from the table, beside its right end.
CHAO_ALONE_SPOT = (420, 392)
CHAO_FEAST_PROMPT = "Eat"
CHAO_FEAST_TITLE = "Leftover Feast"
CHAO_FEAST_MESSAGE = "You are about to enter a typing mini game."
CHAO_FEAST_ITEMS = [
    ("Start", "feast", "play"),
    ("Wait", "wait", "book"),
]
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
