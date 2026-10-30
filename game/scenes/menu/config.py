"""Constants only the menu scene uses. Shared ones stay in game/config.py."""

from ...config import WIDTH


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
MENU_BUTTON_GAP = 16
CREDIT_MARGIN = 34
CREDIT_ICON = "award"
CREDITS_W = 560
CREDITS_H = 320


# --- Story screen ------------------------------------------------------------
# (scene title, blurb, chapters). Each chapter is
# (title, blurb, module, view class, constructor kwargs, preview still).
# Previews are paths under assets/backgrounds. A chapter whose module or
# class is missing shows as locked instead of crashing.
STORY = (
    ("Market Dash", "A Saturday morning call sends Terry racing to the market.", (
        ("Wake-up Call", "An early phone call drags Terry out of bed.",
         "game.scenes.market_dash", "MarketDashView", {},
         "market-dash/Scene 1.4 - phone ringing.jpg"),
        ("The Market", "Find the way round the crowded market floor.",
         "game.scenes.market_dash", "MarketStageView", {},
         "market-dash/Scene 2.1 - supermarket overview.jpg"),
        ("Veggie Catch", "Catch the falling vegetables before the snatchers do.",
         "game.scenes.market_dash", "MarketCatchView", {"mode": "veg"},
         "market-dash/Scene 2.2 - crowd in front door.jpg"),
        ("Meat Catch", "Same rush, now at the meat stall.",
         "game.scenes.market_dash", "MarketCatchView",
         {"mode": "meat", "veg_done": True},
         "market-dash/Scene 2.3 - chaos scene in market.jpg"),
        ("Heading Home", "Shopping done, time to catch the bus.",
         "game.scenes.market_dash", "MarketEndingView", {},
         "market-dash/Scene 3 - returning home.jpg"),
    )),
    ("Bumpy Bus", "Keep the shopping safe on a rough ride home.", (
        ("The Ride", "Guard the food from everything the bus throws at it.",
         "game.scenes.bumpy_bus", "BumpyBusView", {},
         "bus-scene/waiting_bus/pasar-station.png"),
    )),
    ("Backyard BBQ", "Get the garden ready and cook for the family.", (
        ("The Garden", "The backyard hub where every job starts.",
         "game.scenes.bbq", "BbqView", {},
         "bbq-scene-bg.jpeg"),
        ("Prep", "Lay the ingredients out for the grill.",
         "game.scenes.bbq.prep", "BBQPrepView", {},
         "BBQ-Scene/BBQ_Prep_BG.jpg"),
        ("Chopping", "Slice the vegetables and meat cleanly.",
         "game.scenes.bbq.chopping", "ChoppingView", {},
         "BBQ-Scene/Chopping_carrot_begin.jpg"),
        ("Grilling", "Keep the heat right so nothing burns.",
         "game.scenes.bbq.grilling", "GrillingView", {},
         "BBQ-Scene/BBQ_20%_grilled.jpg"),
    )),
    ("Chaos Dinner", "Night falls and the whole family sits down to eat.", (
        ("Dinner Table", "Keep the kids in their seats through dinner.",
         "game.scenes.chao_dinner", "ChaoDinnerView", {},
         "chao-dinner-served.png"),
        ("Typing Feast", "Type fast to clear the leftovers.",
         "game.scenes.chao_dinner", "TypingFeastView", {},
         "chao-dinner-keyword-game/feast-1-full.jpg"),
    )),
    ("Epilogue", "How the day ends.", (
        ("The End", "The closing cut scene.",
         "game.scenes.ending", "EndingView", {},
         "chao-dinner-night.png"),
    )),
)


# --- Credits -----------------------------------------------------------------
CREDITS_NAMES = (
    ("TP076848", "Ee Jin Xing"),
    ("TP076218", "Ian Chin Jun Sheng"),
    ("TP075642", "Tang Chee Kin"),
    ("TP075320", "Timothy Ng Chong Sheng"),
)
