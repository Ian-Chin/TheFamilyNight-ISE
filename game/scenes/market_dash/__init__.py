"""
Scene 1: Market Dash
Main entry module imported by test.py.
"""

from .intro import StorySlideView
from .stage import MarketStageView
from .catch import MarketCatchView
from .ending import MarketEndingView


# ============================================================================
# Main Scene Export (Directly opened by test.py)
# ============================================================================
class MarketDashView(StorySlideView):
    """Entry point matching ('Scene 1: Market Dash', 'game.scenes.market_dash', 'MarketDashView')."""
    pass


__all__ = [
    "MarketDashView",
    "StorySlideView",
    "MarketStageView",
    "MarketCatchView",
    "MarketEndingView",
]