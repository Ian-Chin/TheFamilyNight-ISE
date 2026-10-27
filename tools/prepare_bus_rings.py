"""Prepare the supplied ring artwork for the native bus minigame.

python tools/prepare_bus_rings.py --pirate-sheet PATH --tesla PATH --fire-sheet PATH
The source sheet is a concept; the live game rotates one cleaned, fixed sprite.
"""
import argparse
import json
import math
from pathlib import Path
import wave

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "assets/ui/bus-scene/target-rings"


def clean(image, threshold=8):
    data = np.array(image.convert("RGBA"))
    data[data[:, :, 3] <= threshold] = 0
    return Image.fromarray(data)


def pirate(path):
    sheet = Image.open(path).convert("RGBA")
    tile = sheet.crop((0, 0, round(sheet.width / 4), round(sheet.height / 2)))
    # Canonical source geometry is the first frame of the supplied 4x2 sheet.
    tile = tile.resize((444, 444), Image.Resampling.LANCZOS)
    data = np.array(tile)
    yy, xx = np.mgrid[:444, :444]
    interior = ((xx - 222) / 108) ** 2 + ((yy - 245) / 100) ** 2 < 1
    interior &= ~((xx < 185) & (yy < 206))  # preserve the doll's tongue
    red = ((data[:, :, 0] > 100) &
           (data[:, :, 1].astype(float) < data[:, :, 0] * .53) &
           (data[:, :, 2].astype(float) < data[:, :, 0] * .68))
    data[interior & (red | (data[:, :, 3] < 225))] = 0
    # Remove the concept frame's muzzle flash. The live renderer supplies it.
    flash = (xx >= 399) | ((xx >= 392) & (yy >= 154) & (yy < 242) &
                          (data[:, :, 0] > 160) & (data[:, :, 1] > 60))
    data[flash] = 0
    tile = clean(Image.fromarray(data))
    draw = ImageDraw.Draw(tile)
    draw.ellipse((387, 180, 404, 217), fill=(30, 40, 51, 255),
                 outline=(114, 134, 148, 255), width=3)
    draw.ellipse((392, 186, 402, 211), fill=(13, 19, 27, 255))
    scale = 1.4
    canvas = Image.new("RGBA", (640, 640))
    tile = tile.resize((round(444 * scale), round(444 * scale)), Image.Resampling.LANCZOS)
    canvas.alpha_composite(tile, (round(320 - 222 * scale), round(320 - 244 * scale)))
    return clean(canvas)


def tesla(path):
    image = clean(Image.open(path))
    image = image.crop(image.getchannel("A").getbbox())
    image = image.resize((400, 400), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (640, 640))
    canvas.alpha_composite(image, (120, 120))
    return clean(canvas)


def fire(path):
    source = Image.open(path).convert("RGBA")
    result = Image.new("RGBA", (128 * 4, 128 * 2))
    for index in range(8):
        col, row = index % 4, index // 4
        tile = source.crop((round(col * source.width / 4), round(row * source.height / 2),
                            round((col + 1) * source.width / 4), round((row + 1) * source.height / 2)))
        mask = tile.getchannel("A").point(lambda a: 255 if a > 30 else 0)
        bounds = mask.getbbox()
        if bounds:
            tile = clean(tile.crop(bounds), 14)
            factor = min(96 / tile.width, 106 / tile.height)
            tile = tile.resize((round(tile.width * factor), round(tile.height * factor)), Image.Resampling.LANCZOS)
            result.alpha_composite(tile, (col * 128 + (128 - tile.width) // 2,
                                         row * 128 + 116 - tile.height))
    return clean(result)


def sounds():
    folder = ROOT / "assets/audio/bus-scene/target-rings"
    folder.mkdir(parents=True, exist_ok=True)
    rate = 22050
    rng = np.random.default_rng(274)
    for kind, duration in (("cannon", .42), ("charge", .34), ("warp", .38), ("burn", .7)):
        t = np.arange(round(rate * duration)) / rate
        noise = rng.normal(0, 1, len(t))
        if kind == "cannon":
            signal = (.65 * noise + .6 * np.sin(math.tau * (95 * t - 70 * t * t))) * np.exp(-t * 13)
        elif kind == "charge":
            signal = (np.sin(math.tau * (280 * t + 1250 * t * t)) + .14 * noise) * np.sin(math.pi * t / duration) * .35
        elif kind == "warp":
            signal = (np.sin(math.tau * (1400 * t - 1450 * t * t)) + .25 * noise) * np.exp(-t * 10) * .45
        else:
            signal = noise * (1 - np.exp(-t * 30)) * np.exp(-t * 5) * .3
        samples = (np.clip(signal, -1, 1) * 22000).astype("<i2")
        with wave.open(str(folder / f"{kind}.wav"), "wb") as sound:
            sound.setnchannels(1)
            sound.setsampwidth(2)
            sound.setframerate(rate)
            sound.writeframes(samples.tobytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pirate-sheet", type=Path, required=True)
    parser.add_argument("--tesla", type=Path, required=True)
    parser.add_argument("--fire-sheet", type=Path, required=True)
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    pirate(args.pirate_sheet).save(DEST / "pirate.png")
    tesla(args.tesla).save(DEST / "tesla.png")
    fire(args.fire_sheet).save(DEST / "fire.png")
    manifest = {
        "canvas": 640, "pivot": [320, 320],
        "pirate": {"file": "pirate.png", "inner_radius": 137, "muzzle": [568, 258]},
        "tesla": {"file": "tesla.png", "inner_radius": 132},
        "fire": {"file": "fire.png", "columns": 4, "frames": 8, "frame_size": 128, "fps": 12},
        "source": "User-supplied pirate, Tesla coil and fire references; cleaned and aligned for runtime animation.",
    }
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    sounds()
    print(DEST)


if __name__ == "__main__":
    main()
