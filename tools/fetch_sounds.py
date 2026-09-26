"""Where the game's sound effects come from, and a go at downloading them.

Every clip is a free Pixabay sound effect. Pixabay sits behind a Cloudflare
check that a script cannot pass, so this usually cannot fetch them for you:
run it to see the list, then download the files in a browser and save them
into assets/audio/ under the names below.

The footsteps and the ambience are already in place, from these recordings,
with the originals kept in assets/audio/sources:

    https://pixabay.com/sound-effects/film-special-effects-walking-on-grass-363353/
    https://pixabay.com/sound-effects/walking-on-gravel-295852/
    https://pixabay.com/sound-effects/backyard-birds-001-33337/

The two footstep files are cut down by `tools/cut_footsteps.py`; the ambience
is used whole.

    python tools/fetch_sounds.py
"""

import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "assets" / "audio"

# (saved filename, what it is used for, the Pixabay page to download from)
SOUNDS = [
    (
        "dialog-type.mp3",
        "keyboard tapping, looped while a line types on",
        "https://pixabay.com/sound-effects/film-special-effects-keyboard-typing-sound-effect-335503/",
    ),
    (
        "dialog-open.mp3",
        "blip when the dialogue box appears",
        "https://pixabay.com/sound-effects/film-special-effects-ui-pop-up-1-197886/",
    ),
]

BROWSER = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
}


def slug_download_url(page_url):
    """Pixabay's download route for a sound-effect page."""
    slug = page_url.rstrip("/").rsplit("/", 1)[-1]
    return f"https://pixabay.com/sound-effects/download/{slug}.mp3"


def try_download(page_url, target):
    request = urllib.request.Request(slug_download_url(page_url), headers=BROWSER)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as error:
        return f"blocked ({error})"
    if not data.startswith(b"ID3") and b"mpeg" not in data[:64].lower():
        return "blocked (got a Cloudflare page, not audio)"
    target.write_bytes(data)
    return None


def main():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    missing = []
    for filename, purpose, page_url in SOUNDS:
        target = AUDIO_DIR / filename
        if target.exists():
            print(f"have  {filename}")
            continue
        problem = try_download(page_url, target)
        if problem is None:
            print(f"got   {filename}")
        else:
            print(f"MISS  {filename}  {problem}")
            missing.append((filename, purpose, page_url))

    if not missing:
        return 0

    print("\nDownload these by hand and save them into assets/audio/:")
    for filename, purpose, page_url in missing:
        print(f"\n  {filename}   ({purpose})")
        print(f"  {page_url}")
    print("\nThe game runs without them; those effects are just silent.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
