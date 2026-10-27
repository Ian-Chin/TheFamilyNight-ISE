"""Bake the interface sound effects as .wav files, with no dependencies.

These are synthesised, not recorded: simple tones and clicks for the dialogue
box. `tools/fetch_sounds.py` lists recorded Pixabay clips that can be dropped
in on top; the loader prefers .mp3 and .ogg over the .wav written here, so a
downloaded file wins without any code change.

The footsteps and the garden ambience are real recordings and are deliberately
not generated here, so that re-running this does not throw them away. The
footsteps are cut down by `tools/cut_footsteps.py`; the ambience is used whole.

    python tools/make_sounds.py            # every clip
    python tools/make_sounds.py feast-     # only the typing game's clips
"""

import sys
import wave
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "assets" / "audio"
RATE = 44100


def write_wav(path, samples):
    """Save a float array in -1..1 as 16-bit mono."""
    clipped = numpy.clip(samples, -1.0, 1.0)
    frames = (clipped * 32767).astype("<i2").tobytes()
    with wave.open(str(path), "w") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(frames)


def seconds(count):
    return numpy.arange(int(RATE * count)) / RATE


def noise(count, seed):
    return numpy.random.default_rng(seed).uniform(-1.0, 1.0, int(RATE * count))


def smooth(signal, window):
    """A cheap low pass: a running mean `window` samples wide."""
    if window < 2:
        return signal
    kernel = numpy.ones(window) / window
    return numpy.convolve(signal, kernel, mode="same")


def decay(count, power):
    """An envelope falling from 1 to 0 over the clip; higher power is snappier."""
    return (1.0 - numpy.linspace(0.0, 1.0, int(RATE * count))) ** power


def type_tick(seed=3):
    """One key tap, short enough to sit under a character appearing."""
    length = 0.045
    click = smooth(noise(length, seed), 2) * decay(length, 12.0)
    tone = numpy.sin(2 * numpy.pi * 1750 * seconds(length)) * decay(length, 18.0)
    return click * 0.5 + tone * 0.35


def typing_loop():
    """A run of taps, looped for as long as a line is typing itself on."""
    gap = 0.075
    track = numpy.zeros(int(RATE * gap * 8))
    for index in range(8):
        tap = type_tick(seed=10 + index) * (0.8 + 0.2 * (index % 3) / 2)
        start = int(RATE * gap * index)
        track[start:start + len(tap)] += tap[:len(track) - start]
    return track


def popup():
    """A two-note rise, for the dialogue box arriving."""
    parts = []
    for frequency, length in ((620, 0.07), (930, 0.13)):
        step = seconds(length)
        wave_form = (
            numpy.sin(2 * numpy.pi * frequency * step)
            + 0.3 * numpy.sin(4 * numpy.pi * frequency * step)
        )
        attack = numpy.minimum(1.0, step * 260)
        parts.append(wave_form * attack * decay(length, 3.2) * 0.45)
    return numpy.concatenate(parts)


def ui_hover():
    """A soft, quiet tick for the pointer passing over a button."""
    length = 0.06
    step = seconds(length)
    tone = (
        numpy.sin(2 * numpy.pi * 1040 * step)
        + 0.25 * numpy.sin(2 * numpy.pi * 1560 * step)
    )
    attack = numpy.minimum(1.0, step * 420)
    return tone * attack * decay(length, 4.5) * 0.16


def ui_click():
    """A rounded two-note confirm, still well short of a beep."""
    parts = []
    for frequency, length, level in ((520, 0.06, 0.3), (780, 0.12, 0.26)):
        step = seconds(length)
        tone = (
            numpy.sin(2 * numpy.pi * frequency * step)
            + 0.2 * numpy.sin(2 * numpy.pi * frequency * 2 * step)
        )
        attack = numpy.minimum(1.0, step * 380)
        parts.append(tone * attack * decay(length, 3.4) * level)
    return numpy.concatenate(parts)


# --- Leftover feast typing game ---------------------------------------------


def tone(frequency, length, harmonics=((1, 1.0),), attack=300, power=3.0):
    step = seconds(length)
    wave_form = sum(level * numpy.sin(2 * numpy.pi * frequency * mult * step)
                    for mult, level in harmonics)
    return wave_form * numpy.minimum(1.0, step * attack) * decay(length, power)


def sweep(start, end, length, power=2.5):
    """A sine gliding from `start` to `end` Hz."""
    step = seconds(length)
    frequency = numpy.linspace(start, end, len(step))
    phase = 2 * numpy.pi * numpy.cumsum(frequency) / RATE
    return numpy.sin(phase) * numpy.minimum(1.0, step * 400) * decay(length, power)


def place(track, clip, at):
    start = int(RATE * at)
    end = min(len(track), start + len(clip))
    track[start:end] += clip[:end - start]
    return track


def feast_key():
    """A soft mechanical thock: a dull body under a short bright click."""
    length = 0.07
    body = tone(210, length, ((1, 1.0), (2.1, 0.3)), attack=900, power=9.0)
    click = smooth(noise(length, 41), 3) * decay(length, 26.0)
    return body * 0.42 + click * 0.32


def feast_error():
    """A low, buzzy bump for a wrong key."""
    length = 0.14
    step = seconds(length)
    buzz = numpy.sign(numpy.sin(2 * numpy.pi * 118 * step)) * 0.5
    buzz += numpy.sin(2 * numpy.pi * 59 * step)
    return smooth(buzz, 6) * numpy.minimum(1.0, step * 500) * decay(length, 2.2) * 0.3


def feast_word():
    """A round little pop, one per word finished."""
    return sweep(480, 920, 0.09, power=2.0) * 0.32


def feast_chomp():
    """Three crunchy bites."""
    track = numpy.zeros(int(RATE * 0.5))
    for index, at in enumerate((0.0, 0.15, 0.3)):
        length = 0.11
        crunch = smooth(noise(length, 60 + index), 2 + index) * decay(length, 3.0)
        thud = tone(140 - index * 12, length, attack=800, power=5.0)
        place(track, crunch * 0.55 + thud * 0.4, at)
    return track


def feast_stage():
    """A bright rising arpeggio for a course cleared."""
    track = numpy.zeros(int(RATE * 0.7))
    for index, frequency in enumerate((523, 659, 784, 1047)):
        note = tone(frequency, 0.32, ((1, 1.0), (2, 0.25), (3, 0.1)), power=2.6)
        place(track, note * 0.24, index * 0.075)
    return track


def feast_combo():
    """A quick shimmer for a streak of clean words."""
    track = numpy.zeros(int(RATE * 0.45))
    for index, frequency in enumerate((1568, 1976, 2349, 2637, 3136)):
        place(track, tone(frequency, 0.18, power=3.5) * 0.12, index * 0.045)
    return track


def feast_count():
    """One beep of the count in."""
    return tone(660, 0.16, ((1, 1.0), (2, 0.2)), power=2.0) * 0.35


def feast_go():
    """The beep that starts the clock: higher, longer, with a fifth on top."""
    return (tone(990, 0.42, ((1, 1.0), (1.5, 0.5), (2, 0.2)), power=1.8)) * 0.3


def feast_tick():
    """A woody tick for each of the last seconds."""
    length = 0.05
    return (tone(1300, length, attack=2000, power=10.0) * 0.4
            + smooth(noise(length, 77), 4) * decay(length, 20.0) * 0.2)


def feast_whoosh():
    """Filtered noise rising and falling, for a panel sliding in."""
    length = 0.42
    swell = numpy.sin(numpy.linspace(0, numpy.pi, int(RATE * length))) ** 2
    return smooth(noise(length, 90), 14) * swell * 0.5


def feast_win():
    """A short fanfare: two chords, then the octave held."""
    track = numpy.zeros(int(RATE * 1.4))
    chords = ((0.0, (523, 659, 784), 0.22), (0.2, (587, 740, 880), 0.22),
              (0.42, (784, 988, 1175, 1568), 0.9))
    for at, notes, length in chords:
        for frequency in notes:
            place(track, tone(frequency, length, ((1, 1.0), (2, 0.3), (3, 0.12)),
                              power=1.6) * 0.14, at)
    return track


def feast_lose():
    """A deflating wah-wah, falling a semitone at a time."""
    track = numpy.zeros(int(RATE * 1.5))
    for index, (start, end) in enumerate(((392, 370), (370, 349), (349, 330),
                                          (330, 262))):
        length = 0.62 if index == 3 else 0.3
        step = seconds(length)
        frequency = numpy.linspace(start, end, len(step))
        wobble = 1 + 0.02 * numpy.sin(2 * numpy.pi * 6 * step) * (index == 3)
        phase = 2 * numpy.pi * numpy.cumsum(frequency * wobble) / RATE
        wave_form = numpy.sin(phase) + 0.5 * numpy.sin(2 * phase) + 0.25 * numpy.sin(3 * phase)
        envelope = numpy.minimum(1.0, step * 60) * decay(length, 1.2)
        place(track, smooth(wave_form, 8) * envelope * 0.22, index * 0.32)
    return track


CLIPS = {
    "dialog-type": typing_loop,
    "dialog-open": popup,
    "ui-hover": ui_hover,
    "ui-click": ui_click,
    "feast-key": feast_key,
    "feast-error": feast_error,
    "feast-word": feast_word,
    "feast-chomp": feast_chomp,
    "feast-stage": feast_stage,
    "feast-combo": feast_combo,
    "feast-count": feast_count,
    "feast-go": feast_go,
    "feast-tick": feast_tick,
    "feast-whoosh": feast_whoosh,
    "feast-win": feast_win,
    "feast-lose": feast_lose,
}


def main():
    """Bake every clip, or only the ones named on the command line."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    wanted = sys.argv[1:]
    for name, build in CLIPS.items():
        if wanted and not any(name.startswith(prefix) for prefix in wanted):
            continue
        path = AUDIO_DIR / f"{name}.wav"
        write_wav(path, build())
        print(f"wrote {path.relative_to(ROOT)}  ({path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
