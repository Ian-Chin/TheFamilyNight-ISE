"""Entry point. Run `python main.py`, or `python main.py --windowed`."""

import sys

import arcade

from game.config import HEIGHT, TITLE, WIDTH
from game.views import MenuView


def warm_up():
    """Build the scene's art before the menu is on screen.

    Cutting the characters out and drawing the panels takes long enough to be
    felt, and doing it when Play is clicked puts that pause where it is most
    obvious. Building a scene here and dropping it on the floor leaves every
    texture cache full, so the real one opens straight away. The heavy
    cut-outs are baked to assets/.cache as well, so this only costs real time
    on the first run after the art changes.
    """
    # Imported here so the window exists before any texture is uploaded.
    from game.chao_dinner import ChaoDinnerView

    ChaoDinnerView()


def main():
    windowed = "--windowed" in sys.argv
    window = arcade.Window(
        WIDTH, HEIGHT, TITLE, fullscreen=not windowed, resizable=True,
    )
    warm_up()
    window.show_view(MenuView())

    if "--screenshot" in sys.argv:
        out = sys.argv[sys.argv.index("--screenshot") + 1]

        def shot(_delta):
            arcade.get_image().save(out)
            window.close()

        arcade.schedule_once(shot, 0.6)

    arcade.run()


if __name__ == "__main__":
    main()
