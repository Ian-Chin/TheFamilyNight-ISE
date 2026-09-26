"""Turn the walking recordings into clips the game can trigger.

Neither source is usable as it stands. The grass file is a left-right pair of
steps with a quiet run-up, spaced further apart than Terry walks. The gravel
file is a minute of continuous walking.

    grass   kept whole, both steps, with the run-up trimmed off the front and
            the whole thing sped up so the pair lands at Terry's pace
    gravel  a single well-isolated step cut out of the middle

Re-runnable: the sources live in assets/audio/sources.

    python tools/cut_footsteps.py
"""

import sys
import wave
from pathlib import Path

import numpy
import pyglet

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "assets" / "audio"
SOURCE_DIR = AUDIO_DIR / "sources"

STEP_LENGTH = 0.34    # seconds of audio kept around a single cut hit
LEAD_IN = 0.02        # seconds kept before it, so the attack is not clipped
FADE = 0.012          # seconds of fade at each end, to stop clicks
PEAK = 0.85           # what a finished clip is normalised to
QUIET = 0.04          # level below which the run-up counts as silence

# How far apart Terry's feet land, from game.config.STEP_INTERVAL.
GAME_STEP = 0.32

GRASS_SOURCE = "soumages-walking-on-grass-363353.mp3"
GRAVEL_SOURCE = "audiopapkin-walking-on-gravel-295852.mp3"


def decode(path):
    """A monophonic float array of a sound file, and its sample rate."""
    source = pyglet.media.load(str(path), streaming=False)
    samples = numpy.frombuffer(source._data, dtype="<i2").astype(numpy.float32)
    samples /= 32768.0
    if source.audio_format.channels == 2:
        samples = samples.reshape(-1, 2).mean(axis=1)
    return samples, source.audio_format.sample_rate


def envelope(samples, rate, hop_seconds=0.01):
    """Peak level per short window, for finding where the hits are."""
    hop = int(rate * hop_seconds)
    windows = len(samples) // hop
    return numpy.abs(samples[:windows * hop].reshape(windows, hop)).max(axis=1), hop


def onsets(samples, rate, threshold):
    """Where each hit starts, in samples."""
    levels, hop = envelope(samples, rate)
    loud = numpy.flatnonzero(levels > levels.max() * threshold)
    if not len(loud):
        return []
    starts = [loud[0]]
    for index in loud[1:]:
        if index - starts[-1] > 8:
            starts.append(index)
    return [start * hop for start in starts]


def best_onset(samples, rate, threshold):
    """The start of the most isolated loud moment in the recording.

    Isolated matters more than loudest: a step with quiet either side cuts
    cleanly, while one in the middle of a run drags its neighbours in.
    """
    levels, hop = envelope(samples, rate)
    loud = numpy.flatnonzero(levels > levels.max() * threshold)
    if not len(loud):
        return 0

    starts = [loud[0]]
    for index in loud[1:]:
        if index - starts[-1] > 8:
            starts.append(index)

    span = int(STEP_LENGTH / 0.01)
    quietest, chosen = None, starts[0]
    for start in starts:
        after = levels[start + span:start + 2 * span]
        before = levels[max(0, start - span):start]
        if not len(after) or not len(before):
            continue
        # How little is going on either side of this hit.
        noise = max(after.max(), before.max())
        if quietest is None or noise < quietest:
            quietest, chosen = noise, start
    return chosen * hop


def cut_one_step(samples, rate, at):
    """One hit, cut out with the attack intact."""
    start = max(0, at - int(rate * LEAD_IN))
    step = numpy.array(samples[start:start + int(rate * STEP_LENGTH)])
    return normalise(fade_ends(step, rate))


def whole_pair(samples, rate, threshold):
    """The whole recording, trimmed and sped up to walking pace.

    The two steps in it are further apart than Terry's feet land, so the clip
    is played faster until they line up. Returns the clip and how long one
    play covers, which is two of the game's steps.
    """
    samples = numpy.array(trim_run_up(samples, rate))
    hits = onsets(samples, rate, threshold)
    if len(hits) < 2:
        return normalise(fade_ends(samples, rate)), rate, None

    spacing = (hits[1] - hits[0]) / rate
    ratio = spacing / GAME_STEP
    sped_up = resample(samples, ratio)
    return normalise(fade_ends(sped_up, rate)), rate, (spacing, ratio)


def resample(samples, ratio):
    """Play the clip `ratio` times faster, pitch and all."""
    if ratio == 1.0:
        return samples
    length = int(len(samples) / ratio)
    positions = numpy.arange(length) * ratio
    return numpy.interp(positions, numpy.arange(len(samples)), samples)


def trim_run_up(samples, rate):
    """Drop the near-silence before the recording gets going."""
    levels, hop = envelope(samples, rate)
    audible = numpy.flatnonzero(levels > QUIET)
    if not len(audible):
        return samples
    # A little before the first audible window, so nothing is clipped off.
    start = max(0, (audible[0] - 1) * hop)
    return samples[start:]


def fade_ends(samples, rate):
    fade = int(rate * FADE)
    if len(samples) > 2 * fade:
        samples[:fade] *= numpy.linspace(0.0, 1.0, fade)
        samples[-fade:] *= numpy.linspace(1.0, 0.0, fade)
    return samples


def normalise(samples):
    loudest = numpy.abs(samples).max()
    return samples * (PEAK / loudest) if loudest > 0 else samples


def write_wav(path, samples, rate):
    frames = (numpy.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes()
    with wave.open(str(path), "w") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(frames)


def main():
    missing = [
        name for name in (GRASS_SOURCE, GRAVEL_SOURCE)
        if not (SOURCE_DIR / name).exists()
    ]
    if missing:
        print(f"Put these in {SOURCE_DIR.relative_to(ROOT)}:")
        for name in missing:
            print(f"  {name}")
        return 1

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    samples, rate = decode(SOURCE_DIR / GRASS_SOURCE)
    # The second step of the pair is softer than the first, so the bar for
    # counting as a hit sits lower here than for the gravel recording.
    clip, rate, timing = whole_pair(samples, rate, 0.35)
    write_wav(AUDIO_DIR / "step-grass.wav", clip, rate)
    detail = (
        f"steps {timing[0]:.2f}s apart, sped up {timing[1]:.2f}x"
        if timing else "kept as recorded"
    )
    print(
        f"step-grass.wav  <- {GRASS_SOURCE}"
        f"  whole clip, {detail}, now {len(clip) / rate:.2f}s"
    )

    samples, rate = decode(SOURCE_DIR / GRAVEL_SOURCE)
    at = best_onset(samples, rate, 0.5)
    write_wav(AUDIO_DIR / "step-stone.wav", cut_one_step(samples, rate, at), rate)
    print(
        f"step-stone.wav  <- {GRAVEL_SOURCE}"
        f"  one step at {at / rate:.2f}s of {len(samples) / rate:.1f}s"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
