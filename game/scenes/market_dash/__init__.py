from .intro import StorySlideView
from .stage import MarketStageView
from .catch import MarketCatchView
from .ending import MarketEndingView


class MarketDashView(StorySlideView):
    pass


__all__ = [
    "MarketDashView",
    "StorySlideView",
    "MarketStageView",
    "MarketCatchView",
    "MarketEndingView",
]
