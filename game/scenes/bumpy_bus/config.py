"""Constants only the bus scene uses. Shared ones stay in game/config.py."""

from ...config import HEIGHT, WIDTH

# --- Round 2: the highway ------------------------------------------------------
# The camera rides behind the bus. The road is flat and straight: a point `z`
# units ahead is drawn at scale VIEW_DEPTH / (VIEW_DEPTH + z), so the horizon
# is where that scale reaches zero. Across the road, -1 and +1 are its edges.
HIGHWAY_KICKER = "R O U N D   2"
HIGHWAY_TITLE = "Highway Dash"
HIGHWAY_TAGLINE = "Steer with A and D, and get the shopping home in one piece"
HIGHWAY_HINT = "A / D to steer        Q to shout the traffic aside        Esc to pause"
HIGHWAY_HINT_TIME = 9.0       # seconds the hint stays up
HIGHWAY_DURATION = 40.0       # seconds of traffic
HIGHWAY_FADE = 0.9            # seconds in from black, and out again at the end
HIGHWAY_MIN_LIVES = 2         # nobody starts this round on their last crumb

HORIZON = 400                 # canvas y of the vanishing line
ROW_H = 4                     # the ground is painted in strips this tall
ROAD_HALF = 560               # half the road's width at the bottom of the canvas
VIEW_DEPTH = 1.0
FAR_Z = 14.0                  # where traffic and scenery first appear
BACKDROP_SCALE = 4
BACKDROP_SINK = 18            # how far the hills dip below the horizon

LANE_X = (-2 / 3, 0.0, 2 / 3)     # lane centres
BUS_ART_SHARE = 68 / 44       # the bus art's canvas over the bus drawn on it
BUS_Z = 0.25
BUS_WIDTH = 0.50
BUS_REACH = 0.72              # how far from the middle the bus may steer
STEER_SPEED = 2.1             # across the road, per second
BUS_SPEED = (8.5, 11.5)       # down the road, at the start and by the end
KPH_PER_UNIT = 11             # only for the speed readout

# kind -> (width across the road, how often it turns up)
VEHICLE_KINDS = {"car": (0.40, 0.58), "van": (0.42, 0.26), "truck": (0.48, 0.16)}
CAR_PAINTS = ((222, 68, 68), (64, 134, 224), (240, 240, 244), (154, 102, 216), (72, 176, 116))
VAN_PAINTS = ((44, 168, 176), (242, 150, 52))
TRUCK_PAINTS = ((206, 62, 70), (58, 110, 200))
CLOSING_SPEED = (3.0, 4.4)    # how fast the bus gains on traffic, slowest to fastest
SPAWN_GAP = (1.15, 0.62)      # seconds between vehicles, at the start and by the end
CLEAR_TIME = 3.5              # no new traffic this close to the end
HALF_LENGTH = 0.30            # half a vehicle's depth on the road
HIT_FORGIVE = 0.07            # overlap across the road that still counts as a miss
NEAR_GAP = 0.09               # a pass closer than this is a near miss
HIT_GRACE = 1.6               # seconds of blinking after a crash
LANE_CHANGE = 0.32            # seconds to slide over one lane
SAFE_MARGIN = 0.30            # seconds kept clear either side of a vehicle
AIM_AT_BUS = 0.6              # share of traffic sent down the bus's own lane

# Scenery along the verges: (kind, width across the road).
PROPS = (("tree", 0.55), ("lamp", 0.30), ("bush", 0.36), ("tree", 0.62),
         ("sign", 0.60), ("bush", 0.30), ("lamp", 0.30), ("tree", 0.50))
PROP_GAP = 1.7                # road units between one prop and the next
PROP_X = (1.3, 1.75)          # how far out from the middle they stand

# Ground colours, as (even band, odd band). They alternate down the road.
GRASS = ((104, 170, 92), (92, 156, 82))
TARMAC = ((72, 76, 92), (66, 70, 86))
RUMBLE = ((230, 72, 72), (240, 240, 234))
LANE_PAINT = (238, 238, 230)
HAZE = (186, 206, 176)        # everything fades toward this at the horizon
BAND = 1.6                    # road units per grass and tarmac band
RUMBLE_BAND = 0.8
DASH_PERIOD = 1.2
DASH_ON = 0.5
RUMBLE_W = 46                 # canvas units at the bottom of the canvas
DASH_W = 14

HIGHWAY_LOSE_TITLE = "Crashed!"
HIGHWAY_LOSE_MESSAGE = "The shopping is all over the road."

NEAR_MISSES_FOR_ACHIEVEMENT = 3

# A rammed vehicle is thrown up and away down the road, spinning.
FLY_FORWARD = 5.0             # road units per second, away from the bus
FLY_SIDE = 1.7
FLY_RISE = 2.0                # how fast it leaves the ground
FLY_GRAVITY = 1.5
FLY_TIME = 1.0                # seconds before it is a twinkle in the distance

# Q: the driver leans out and yells, and whatever is close ahead in the bus's
# lane pulls over onto the verge.
SHOUT_RANGE = 7.0             # road units ahead that hear it
SHOUT_COOLDOWN = 5.0          # seconds before he has the breath for another
SHOUT_SHOW = 0.9              # seconds he stays hanging out of the window
SHOULDER_X = 1.3              # where a shouted-at vehicle ends up
PULL_SPEED = 2.6              # across the road, per second
SHOUTS_FOR_ACHIEVEMENT = 5

# Home. Once the traffic is behind, the house comes up on the left, the bus
# pulls over beside it and Terry walks in through the garden gate.
HOUSE_X = -2.95               # middle of the house and yard, across the road
HOUSE_WIDTH = 3.4
HOUSE_STOP_Z = 3.6            # how far ahead of the camera it is when the bus stops
PARK_X = LANE_X[0]
ARRIVE_PAUSE = 0.7            # seconds parked before Terry steps off
ARRIVE_WALK = 2.2             # seconds from the bus to the gate
TERRY_ROAD_W = 0.2
TERRY_PATH = ((-1.2, 0.3), (-4.17, 3.5))    # road points: kerb by the bus, then the gate
ARRIVAL_LINES = (
    ("Home at last, and every bit of the shopping made it!", "happy"),
    ("Right. Time to get the BBQ going before everyone turns up.", "hungry"),
)
ARRIVAL_LINES_SPOILED = (
    ("Home at last! And the shopping... mostly made it.", "nervous"),
    ("Nobody needs to know about the {spoiled}. Time to get the BBQ going.", "happy"),
)


# --- Shared by every view in the scene -------------------------------------------
LOSE_ITEMS = [
    ("Try Again", "retry", "play"),
    ("Main Menu", "menu", "book"),
]

# --- Station -----------------------------------------------------------------------
STATION_BG = "bus-scene/waiting_bus/pasar-station.png"
STATION_KICKER = "S C E N E   2"
STATION_TITLE = "Bumpy Bus"
STATION_TAGLINE = "Keep the shopping safe on a rough ride home"
STATION_HINT = "A / D to walk    Space to jump    Enter to talk or board    Esc to pause"
# The pavement, in canvas units (y runs up). Terry only walks along it.
STATION_FEET_Y = HEIGHT - 435
STATION_START_X = 1100
STATION_WALK = (60, WIDTH - 55)
BOARD_ZONE = (600, 760)               # stand here to board
ARROW = (680, HEIGHT - 380)           # middle of the bobbing arrow over the door
ARROW_H = 126
OFFICER_X = 400
OFFICER_H = 112
OFFICER_RANGE = 120                   # how close Terry has to be to talk
OFFICER_NAME = "Officer"
OFFICER_LINES = (
    "Halt, citizen! The bus is about to leave.",
    "This driver brakes hard and the road is rough. Lean with A and D to stay on your feet.",
    "Keep an eye on your food too. Kids, grannies and sneaky workers are everywhere.",
    "After that it is the highway: steer with A and D to dodge the traffic.",
    "And if someone will not budge, press Q. The driver has quite a voice.",
    "Walk to the arrow and press Enter to get on. Safe trip!",
)
DEPARTURE_TIME = 2.8                  # the bus sweeps across, revealing the cabin
WIPE_H = 1000                         # drawn height of the sweeping bus
CABIN_DARK = (9, 16, 26)              # behind the cabin, under the wipe

# --- Round 1: inside the bus ---------------------------------------------------------
RIDE_KICKER = "R O U N D   1"
RIDE_TITLE = "Keep Your Balance"
RIDE_TAGLINE = "Lean with A and D, and answer every alert"
RIDE_HINT = "A / D  or  Left / Right to lean against the bus        Esc to pause"
RIDE_HINT_TIME = 9.0
RIDE_LOSE_TITLE = "Shopping Spoiled"
RIDE_LOSE_MESSAGE = "Terry and the shopping did not survive the ride."
LEAVE_FADE = 0.6                      # seconds the cabin takes to fade out for round 2
BRAKES_FOR_ACHIEVEMENT = 4

# The cabin is played from frame sheets under this folder.
CABIN_DIR = "bus-scene/animations"
CABIN_BOTTOM = HEIGHT - 122 - 536     # where the cabin sits, y up
CABIN_SIZE = (WIDTH, 536)

# Things that go wrong in the cabin: each shows an alert for EVENT_TIME seconds,
# and if the key is not tapped enough in time the matching scene plays and the
# food takes the hit.
INGREDIENTS = ("eggs", "meat", "cabbage", "eggplant")
ALERT_ICONS = ("kid", "cane", "worker", "fart")
EVENT_SCENES = ("boy-scares", "cane-hit", "worker-steals", "fart-poison")
EVENT_NAMES = ("Mask Kid Scare", "Granny Cane", "Worker Steals Food", "Fart Attack")
EVENT_PRESSES = (4, 4, 5, 5)
# How much of each scene is the wind-up, before anything lands. While the alert
# counts down the culprit creeps through it; every tap shoves them back.
EVENT_APPROACH = (0.20, 0.40, 0.26, 0.15)
EVENT_WIN_WORDS = ("BOO BACK!", "BACKFLIP?!", "SNAP!", "SMELT IT!")
# What each tap before the last one does to the culprit, in order.
EVENT_TAP_WORDS = (
    ("It sees him...", "It's growing!", "It's getting out!"),
    ("Huh?", "Warming up?", "Ready...!"),
    ("Rustle!", "Cheese?", "...a trap?", "Gulp."),
    ("Hold it!", "Going red!", "Shaking!", "Leaking!"),
)
# Sounds in each payback, as (seconds in, sound, gain).
PAYBACK_CUES = (
    ((0.25, "bus_scare", 1.0), (0.3, "bus_swish", 1.0)),
    ((0.25, "bus_jump", 1.0), (0.6, "bus_swish", 1.0), (1.05, "bus_land", 1.0)),
    ((0.15, "bus_cane_hit", 1.0), (0.4, "bus_swish", 0.8)),
    ((0.1, "bus_fart", 1.0), (0.7, "bus_gas_fade", 1.0)),
)
EVENT_TAP_SHOVE = 0.7                 # how far a full set of taps holds them back
EVENT_TIME = 7.0
EVENT_KEYS = "FGHIJKLOUYT"
FOOD_LOSS = 25
FIRST_EVENT_DELAY = (2.5, 5.0)        # spacing is sampled again after every event;
SOLVED_EVENT_DELAY = (2.0, 4.0)       # animations never overlap
REACTION_EVENT_DELAY = (1.5, 3.0)
NO_EVENTS_LAST = 6.0                  # seconds before the end with no new alert
# Sounds in each scene, as (share of the way through, sound, gain).
REACTION_CUES = {
    "boy-scares": ((0.1, "bus_swish"), (0.25, "bus_scare"), (0.3, "bus_food_spill"),
                   (0.46, "bus_swish"), (0.72, "bus_paper")),
    "cane-hit": ((0.26, "bus_swish"), (0.455, "bus_cane_hit"), (0.49, "bus_food_spill"),
                 (0.69, "bus_land", 0.65)),
    "worker-steals": ((0.28, "bus_paper"), (0.46, "bus_chew"), (0.54, "bus_chew"),
                      (0.62, "bus_chew")),
    "fart-poison": ((0.19, "bus_fart"), (0.58, "bus_gas_fade")),
}

# The balance bar along the bottom, in canvas units (y runs up).
BAR_CENTER = WIDTH / 2
BAR_REACH = 244                       # how far Terry slides each way
BAR_BOTTOM = 40
BAR_H = 16
BAR_FIGURE_H = 78
BAR_RED = (214, 64, 64)
BAR_AMBER = (240, 196, 70)
BAR_GREEN = (88, 196, 112)
