"""
Scene 1: Market Dash
Main entry module imported by test.py.
"""

from .market_dash_intro import StorySlideView
from .market_dash_stage import MarketStageView
from .market_dash_catch import MarketCatchView
from .market_dash_ending import MarketEndingView


# ============================================================================
# Main Scene Export (Directly opened by test.py)
# ============================================================================
class MarketDashView(StorySlideView):
    """Entry point matching ('Scene 1: Market Dash', 'game.market_dash', 'MarketDashView')."""
    pass


__all__ = [
    "MarketDashView",
    "StorySlideView",
    "MarketStageView",
    "MarketCatchView",
    "MarketEndingView",
]