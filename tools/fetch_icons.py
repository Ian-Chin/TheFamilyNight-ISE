"""Fetch Bootstrap Icons and save them as PNGs in assets/icons.

Development-time only: the game just loads the PNGs. The SVG sources are
downloaded, rendered in memory and thrown away, so nothing but the finished
PNGs is kept in the repo.

    pip install -r requirements-dev.txt
    python tools/fetch_icons.py

Re-run to refresh the icons or after changing the ICONS table below.
"""

import io
import sys
import urllib.request
from pathlib import Path

import PIL.Image
import PIL.ImageChops
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "assets" / "icons"
SOURCE_URL = "https://raw.githubusercontent.com/twbs/icons/main/icons/{name}.svg"
SIZE = 256

# Game name -> Bootstrap Icons name.
ICONS = {
    "play": "play-fill",
    "book": "book-half",
    "medal": "trophy-fill",
    "gear": "gear-fill",
    "power": "power",
    "award": "award-fill",
}


def render(svg_bytes, size):
    """Render an SVG as a white silhouette with an alpha channel.

    White pixels let the game tint the icon with a draw colour, so one file
    serves both the resting and the hovered look.
    """
    drawing = svg2rlg(io.BytesIO(svg_bytes))
    factor = size / max(drawing.width, drawing.height)
    drawing.scale(factor, factor)
    drawing.width *= factor
    drawing.height *= factor

    flat = renderPM.drawToPIL(drawing, bg=0xFFFFFF).convert("L")
    icon = PIL.Image.new("RGBA", flat.size, (255, 255, 255, 0))
    icon.putalpha(PIL.ImageChops.invert(flat))
    return icon


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    for game_name, icon_name in ICONS.items():
        url = SOURCE_URL.format(name=icon_name)
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                svg_bytes = response.read()
        except OSError as error:
            print(f"could not fetch {url}: {error}")
            return 1

        out = TARGET / f"{game_name}.png"
        render(svg_bytes, SIZE).save(out)
        print(f"{icon_name} -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
