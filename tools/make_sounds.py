"""Bake the interface sound effects as .wav files, with no dependencies.

These are synthesised, not recorded: simple tones and clicks for the dialogue
box. `tools/fetch_sounds.py` lists recorded Pixabay clips that can be dropped
in on top; the loader prefers .mp3 and .ogg over the .wav written here, so a
downloaded file wins without any code change.

The footsteps and the garden ambience are real recordings and are deliberately
not generated here, so that re-running this does not throw them away. The
footsteps are cut down by `tools/cut_footsteps.py`; the ambience is used whole.

    python tools/make_sounds.py
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


CLIPS = {
    "dialog-type": typing_loop,
    "dialog-open": popup,
    "ui-hover": ui_hover,
    "ui-click": ui_click,
}


def main():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    for name, build in CLIPS.items():
        path = AUDIO_DIR / f"{name}.wav"
        write_wav(path, build())
        print(f"wrote {path.relative_to(ROOT)}  ({path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
