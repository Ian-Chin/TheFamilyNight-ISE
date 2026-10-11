from pathlib import Path
import arcade

# Base asset paths
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
BG_DIR = ASSETS_DIR / "backgrounds" / "market-dash"
TERRY_GAME_DIR = ASSETS_DIR / "sprites" / "terry market game"
SNATCHERS_BASE_DIR = ASSETS_DIR / "market snatchers"
INGREDIENTS_BASE_DIR = ASSETS_DIR / "market ingredients"

# ============================================================================
# PART 2: Catcher Mini-Game (3 Waves)
# ============================================================================
# --- Cleaned Walk Bounds and Precise Obstacle Footprints ---
MARKET_WALK_BOUNDS = (72, 1280 - 40, 0, 720 - 40)

# Scenery obstacle boxes (left, right, bottom, top) blocking Terry's feet
MARKET_OBSTACLES = (
    # 1. Leftmost wall rack (Grains & Pasta / Canned Goods)
    (0, 20, 0, 720), #right: 78

    # 2. Canned Goods trellis hanging wall corner (top left corner)
    (0, 155, 540, 720),

    # 3. Top back wall & produce shelves (across the top behind the patio)
    (78, 705, 510, 720),

    # 4. Center aisle: Packaged Snacks shelf
    (470, 580, 220, 530),

    # 5. Center aisle: Cereals & Breakfast shelf
    (705, 805, 220, 530),

    # 6. Meat and deli counter (across the middle right)
    (705, 1280, 200, 395),

    # 7. Bottom-left vertical aisle rack
    (185, 230, 0, 205), # left: 130, right: 245

    # 8. Household Goods shelf (horizontal bottom shelf)
    (300, 465, 0, 160), # right: 285

    # 9. Bottom fruit bin 1 (left crate of the right corner)
    (815, 990, 0, 160), 

    # 10. Bottom fruit bin 2 (rightmost produce crates)
    (1120, 1280, 0, 160), 
)

MARKET_STONE_AREAS = (
    (450, 560, 0, 720),   # Middle cobblestone path
    (65, 375, 145, 510),     # Left patio area (red circle)
)

# Playfield bounding coordinates
PLAY_LEFT = 155
PLAY_RIGHT = 1125
PLAY_BOTTOM = 45
PLAY_TOP = 675


def cover_rect(texture, rect):
    """Fill `rect` with `texture` without distorting it."""
    scale = max(rect.width / texture.width, rect.height / texture.height)
    return arcade.XYWH(
        rect.x, rect.y, texture.width * scale, texture.height * scale
    )