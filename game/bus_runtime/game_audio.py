"""Arcade sound effects with animation-relative cues and pause support."""
import json
import arcade

ALIASES = {'boy-scares': 'boyScares', 'cane-hit': 'caneHit',
           'worker-steals': 'workerSteals', 'fart-poison': 'poison'}


class GameAudio:
    def __init__(self, root, volume):
        self.volume = volume
        self.enabled = True
        self.kind = None
        self.fired = set()
        self.players = []
        folder = root / 'audio/bus-scene/sfx'
        self.meta = json.loads((folder / 'manifest.json').read_text())
        self.sounds = {key: arcade.Sound(str(folder / item['file']))
                       for key, item in self.meta['assets'].items()}

    def play(self, name, gain=1):
        if not self.enabled or name not in self.sounds:
            return
        self.players = [player for player in self.players if player.playing]
        player = self.sounds[name].play(volume=max(0, min(1,
            self.volume() * self.meta['assets'][name]['gain'] * gain)))
        self.players.append(player)

    def stop(self, clear=True):
        for player in self.players:
            player.delete()
        self.players.clear()
        if clear:
            self.kind = None
            self.fired.clear()

    def pause(self):
        for player in self.players:
            player.pause()

    def resume(self):
        for player in self.players:
            player.play()

    def begin(self, kind):
        self.stop()
        self.kind = ALIASES.get(kind, kind)

    def update(self, elapsed, total):
        for index, cue in enumerate(self.meta['timelines'].get(self.kind, [])):
            if index not in self.fired and elapsed + 1e-9 >= cue['at'] * total:
                self.fired.add(index)
                self.play(cue['sound'], cue.get('gain', 1))
