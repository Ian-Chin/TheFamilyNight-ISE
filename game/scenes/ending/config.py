"""Constants only the ending scene uses. Shared ones stay in game/config.py."""

# --- Ending video -----------------------------------------------------------
# The closing cut scene, played once after the leftover feast, pre-rendered.
# Without PyAV the title fades over black for
# ENDING_FALLBACK seconds instead.
ENDING_VIDEO = "ending.mp4"
ENDING_FALLBACK = 5.0
