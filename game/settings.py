"""Player settings, kept in one place and written back to disk.

Audio levels and the graphics mode live here. `mixer` and `graphics` are
single shared instances: the settings screen changes them and whatever reads
them sees the change straight away, so a new level is heard on the next clip
and a new mode shows on the next frame.
"""

import json

from .config import GRAPHICS_MODES, SETTINGS_FILE, VOLUME_CHANNELS


def _read():
    """The whole settings file, or {} when it is missing or unreadable."""
    if not SETTINGS_FILE.exists():
        return {}
    try:
        stored = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # An unreadable settings file falls back to the defaults rather
        # than stopping the game from starting.
        return {}
    return stored if isinstance(stored, dict) else {}


def _write(section, value):
    """Replace one section of the file, keeping the others as they were."""
    stored = _read()
    stored[section] = value
    try:
        SETTINGS_FILE.write_text(json.dumps(stored, indent=2), encoding="utf-8")
    except OSError:
        pass


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
        audio = _read().get("audio", {})
        if not isinstance(audio, dict):
            return
        for channel in self.levels:
            value = audio.get(channel)
            if isinstance(value, (int, float)):
                self.levels[channel] = min(1.0, max(0.0, float(value)))

    def save(self):
        _write("audio", self.levels)


class Graphics:
    """Which way the backgrounds are drawn, one of GRAPHICS_MODES.

    "quality" plays the animated backgrounds; "performance" shows the still
    art instead, so no video is decoded at all.
    """

    def __init__(self):
        self.mode = GRAPHICS_MODES[0]
        graphics = _read().get("graphics", {})
        if isinstance(graphics, dict) and graphics.get("mode") in GRAPHICS_MODES:
            self.mode = graphics["mode"]

    @property
    def animated(self):
        return self.mode == "quality"

    def set(self, mode):
        if mode not in GRAPHICS_MODES or mode == self.mode:
            return
        self.mode = mode
        _write("graphics", {"mode": mode})


mixer = Mixer()
graphics = Graphics()
