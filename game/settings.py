"""Player settings, kept in one place and written back to disk.

Only the audio levels live here for now. `mixer` is a single shared instance:
the settings screen moves its sliders and the sound bank reads them, so a
change is heard straight away rather than on the next clip that happens to be
loaded.
"""

import json

from .config import SETTINGS_FILE, VOLUME_CHANNELS


class Mixer:
    """Master, sound and music levels, each 0.0 to 1.0."""

    def __init__(self):
        self.levels = dict(VOLUME_CHANNELS)
        self.listeners = []
        self.load()

    def on_change(self, callback):
        """Call `callback()` whenever a level moves.

        Anything already playing, like the looping ambience, has its volume
        baked in when it starts, so it has to be told to catch up.
        """
        self.listeners.append(callback)

    def get(self, channel):
        return self.levels.get(channel, 1.0)

    def set(self, channel, value):
        # Rounded so repeated nudges do not drift into 0.7999999999999999.
        value = round(min(1.0, max(0.0, value)), 2)
        if value == self.levels.get(channel):
            return
        self.levels[channel] = value
        self.save()
        for listener in self.listeners:
            listener()

    def nudge(self, channel, delta):
        self.set(channel, self.get(channel) + delta)

    def volume(self, channel, base=1.0):
        """What a clip on `channel` should actually be played at."""
        return base * self.get("master") * self.get(channel)

    def load(self):
        if not SETTINGS_FILE.exists():
            return
        try:
            stored = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # An unreadable settings file falls back to the defaults rather
            # than stopping the game from starting.
            return
        for channel in self.levels:
            value = stored.get("audio", {}).get(channel)
            if isinstance(value, (int, float)):
                self.levels[channel] = min(1.0, max(0.0, float(value)))

    def save(self):
        try:
            SETTINGS_FILE.write_text(
                json.dumps({"audio": self.levels}, indent=2), encoding="utf-8",
            )
        except OSError:
            pass


mixer = Mixer()
