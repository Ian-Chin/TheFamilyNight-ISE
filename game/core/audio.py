import arcade

from ..config import (
    AMBIENCE, AMBIENCE_FADE, AUDIO_DIR, FOOTSTEP_CLIPS, SOUND_EXTENSIONS, SOUND_FILES,
    STEP_INTERVAL,
)
from .settings import mixer


def find_clip(base_name):
    for extension in SOUND_EXTENSIONS:
        path = AUDIO_DIR / f"{base_name}{extension}"
        if path.exists():
            return path
    return None


class SoundBank:
    def __init__(self):
        self.sounds = {}
        for name, (base_name, channel, loudness) in SOUND_FILES.items():
            path = find_clip(base_name)
            if path is None:
                continue
            try:
                self.sounds[name] = (arcade.load_sound(path), channel, loudness)
            except Exception:
                pass

    def volume(self, name):
        entry = self.sounds.get(name)
        return 0.0 if entry is None else mixer.volume(entry[1], entry[2])

    def play(self, name, loop=False, speed=1.0, gain=1.0):
        entry = self.sounds.get(name)
        if entry is None:
            return None
        volume = self.volume(name) * gain
        if volume <= 0.0 and not loop:
            return None
        return entry[0].play(volume=volume, loop=loop, speed=speed)

    def stop(self, player):
        if player is not None:
            player.pause()
            player.delete()


_bank = None


def bank():
    global _bank
    if _bank is None:
        _bank = SoundBank()
    return _bank


def play(name, loop=False, speed=1.0, gain=1.0):
    return bank().play(name, loop=loop, speed=speed, gain=gain)


def stop(player):
    bank().stop(player)


class Ambience:
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
        if self.player is None:
            self.fade_clock = 0.0
            self.player = bank().play(self.name, loop=True)
            self.refresh_volume()

    def stop(self):
        bank().stop(self.player)
        self.player = None
        self.fade_clock = 0.0

    def update(self, delta_time):
        if self.player is None or self.fade_level >= 1.0:
            return
        self.fade_clock += min(delta_time, 1 / 30)
        self.refresh_volume()

    def refresh_volume(self):
        if self.player is not None:
            self.player.volume = bank().volume(self.name) * self.fade_level


_ambiences = {}


def ambience(name=AMBIENCE):
    if name not in _ambiences:
        _ambiences[name] = Ambience(name)
    return _ambiences[name]


class Footsteps:
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
        surface = "stone" if self.on_stone(x, y) else "grass"
        clip, covers = FOOTSTEP_CLIPS[surface]
        if surface != self.surface:
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
