"""The scene's front door: the station, where the ride begins.

Other scenes (the market ending, the story menu) open `BumpyBusView`.
"""

from .station import BusStationView as BumpyBusView

__all__ = ["BumpyBusView"]
