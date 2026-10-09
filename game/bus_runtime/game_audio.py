"""One-shot local foley and animation-relative cues used by the Python game."""
import json
from pathlib import Path
import pygame as pg

ALIASES = {'boy-scares':'boyScares', 'cane-hit':'caneHit', 'worker-steals':'workerSteals', 'fart-poison':'poison'}

class GameAudio:
    def __init__(self, root, volume):
        self.volume = volume
        self.enabled = True
        self.sounds = {}
        self.meta = {'assets':{}, 'timelines':{}}
        self.kind = None
        self.fired = set()
        self.history = []
        folder = Path(root) / 'audio/bus-scene/sfx'
        path = folder / 'manifest.json'
        if path.exists() and pg.mixer.get_init():
            self.meta = json.loads(path.read_text(encoding='utf-8'))
            for name, asset in self.meta['assets'].items():
                self.sounds[name] = pg.mixer.Sound(str(folder / asset['file']))

    def play(self, name, gain=1):
        if not self.enabled or name not in self.sounds:
            return
        for i in range(1, pg.mixer.get_num_channels()):
            channel = pg.mixer.Channel(i)
            if not channel.get_busy():
                channel.set_volume(max(0,min(1,self.volume()*self.meta['assets'][name]['gain']*gain)))
                channel.play(self.sounds[name])
                self.history.append(name)
                self.history = self.history[-80:]
                return

    def stop(self, clear=True):
        if pg.mixer.get_init():
            for i in range(1, pg.mixer.get_num_channels()):pg.mixer.Channel(i).stop()
        if clear:
            self.kind = None
            self.fired.clear()

    def begin(self, kind):
        self.stop()
        self.kind = ALIASES.get(kind, kind)

    def update(self, elapsed, total):
        for i, cue in enumerate(self.meta['timelines'].get(self.kind, [])):
            if i not in self.fired and elapsed+1e-9 >= cue['at']*total:
                self.fired.add(i)
                self.play(cue['sound'], cue.get('gain',1))
