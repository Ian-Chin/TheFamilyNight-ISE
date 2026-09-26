"""Sound effects, mixed through the player's volume settings.

Clips are looked up by base name, so a downloaded .mp3 in assets/audio quietly
replaces the .wav that the tools bake. Anything missing is skipped, and the
game runs the same with no audio at all.

One bank is shared by every screen: the interface clicks belong to no scene in
particular, and loading the same files per view would be wasteful.
"""

import arcade

from .config import (
    AMBIENCE, AMBIENCE_FADE, AUDIO_DIR, FOOTSTEP_CLIPS, SOUND_EXTENSIONS,
    SOUND_FILES, STEP_INTERVAL,
)
from .settings import mixer


def find_clip(base_name):
    """The first file in assets/audio called `base_name`, whatever its type."""
    for extension in SOUND_EXTENSIONS:
        path = AUDIO_DIR / f"{base_name}{extension}"
        if path.exists():
            return path
    return None


class SoundBank:
    """Every clip in `SOUND_FILES`, keyed by name."""

    def __init__(self):
        self.sounds = {}
        for name, (base_name, channel, loudness) in SOUND_FILES.items():
            path = find_clip(base_name)
            if path is None:
                continue
            try:
                self.sounds[name] = (arcade.load_sound(path), channel, loudness)
            except Exception:
                # A clip the audio backend will not decode is not worth
                # stopping the game over.
                pass

    def volume(self, name):
        entry = self.sounds.get(name)
        return 0.0 if entry is None else mixer.volume(entry[1], entry[2])

    def play(self, name, loop=False):
        """Start `name` and return its player, or None if there is no clip."""
        entry = self.sounds.get(name)
        if entry is None:
            return None
        volume = self.volume(name)
        if volume <= 0.0 and not loop:
            return None
        return entry[0].play(volume=volume, loop=loop)

    def stop(self, player):
        if player is not None:
            player.pause()
            player.delete()


_bank = None


def bank():
    """The shared SoundBank, built the first time something asks for it."""
    global _bank
    if _bank is None:
        _bank = SoundBank()
    return _bank


def play(name, loop=False):
    return bank().play(name, loop=loop)


class Ambience:
    """The looping background bed, faded up and kept in step with the mixer.

    It comes in over `AMBIENCE_FADE` seconds, the same way the scene fades up
    out of black, rather than arriving at full volume on the first frame.

    A player's volume is fixed when it starts, so the mixer is asked to tell
    us when a level moves and the running loop is corrected. Turning the music
    right down leaves the loop running at silence, which is what a volume
    control should do.
    """

    def __init__(self, name=AMBIENCE, fade=AMBIENCE_FADE):
        self.name = name
        self.fade = fade
        self.player = None
        self.fade_clock = 0.0
        mixer.on_change(self.refresh_volume)

    @property
    def fade_level(self):
        if self.fade <= 0:
            return 1.0
        return min(1.0, self.fade_clock / self.fade)

    def start(self):
        """Begin the loop, or carry on if it is already going."""
        if self.player is None:
            self.fade_clock = 0.0
            self.player = bank().play(self.name, loop=True)
            self.refresh_volume()

    def stop(self):
        bank().stop(self.player)
        self.player = None
        self.fade_clock = 0.0

    def update(self, delta_time):
        """Walk the fade along. Safe to call when nothing is playing."""
        if self.player is None or self.fade_level >= 1.0:
            return
        # The frame a view opens on carries its load time, which would jump
        # most of the way through the fade in one step.
        self.fade_clock += min(delta_time, 1 / 30)
        self.refresh_volume()

    def refresh_volume(self):
        if self.player is not None:
            self.player.volume = bank().volume(self.name) * self.fade_level


_ambience = None


def ambience():
    """The one background loop.

    Shared rather than one per view, so a view built and dropped for its side
    effects, as the startup warm-up does, cannot leave a second loop or a
    stale mixer listener behind.
    """
    global _ambience
    if _ambience is None:
        _ambience = Ambience()
    return _ambience


class Footsteps:
    """Ticks out a step sound at walking pace, picking the right surface."""

    def __init__(self, stone_areas=()):
        self.stone_areas = stone_areas
        self.timer = STEP_INTERVAL   # so the first step lands straight away
        self.surface = None
        self.steps_since_play = 0

    def on_stone(self, x, y):
        return any(
            left <= x <= right and bottom <= y <= top
            for left, right, bottom, top in self.stone_areas
        )

    def step(self, x, y):
        """One footfall: play a clip, unless the last one still covers it."""
        surface = "stone" if self.on_stone(x, y) else "grass"
        clip, covers = FOOTSTEP_CLIPS[surface]
        if surface != self.surface:
            # Changing surface starts the pattern again, so the new ground is
            # heard on the first step onto it.
            self.surface = surface
            self.steps_since_play = covers

        if self.steps_since_play >= covers:
            play(clip)
            self.steps_since_play = 1
        else:
            self.steps_since_play += 1

    def update(self, delta_time, moving, x, y):
        if not moving:
            self.timer = STEP_INTERVAL
            self.steps_since_play = 0
            self.surface = None
            return
        self.timer += delta_time
        if self.timer < STEP_INTERVAL:
            return
        self.timer -= STEP_INTERVAL
        self.step(x, y)
