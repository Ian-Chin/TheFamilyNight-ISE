"""Constants only the splash scene uses. Shared ones stay in game/config.py."""

# --- Logo cards -------------------------------------------------------------
# Each card fades up out of the paper, holds, and fades back.
CARD_IN = 0.45
CARD_HOLD = 1.7
CARD_OUT = 0.4
PAPER = (246, 243, 236)
PAPER_IN = 0.35          # black to paper, as the splash opens
INK = (34, 36, 44)
INK_DIM = (120, 122, 132)

STUDIO_LOGO = "splash/group2-studio.png"
STUDIO_WIDTH = 640

APU_LOGO = "splash/apu-logo.png"
APU_WIDTH = 620

CODED_WITH = "Coded with"
# (logo, name) for each library the game is built on.
LIBRARIES = (
    ("splash/python.png", "Python"),
    ("splash/arcade.png", "Arcade"),
    ("splash/pyglet.png", "pyglet"),
    ("splash/pillow.png", "Pillow"),
)
LIBRARY_ICON = 128
LIBRARY_GAP = 92

SKIP_HINT = "Click to skip"
SKIP_GRACE = 0.3         # so the click that launched the game cannot skip it
