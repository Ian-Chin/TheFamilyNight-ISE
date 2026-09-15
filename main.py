"""Entry point. Run `python main.py`, or `python main.py --windowed`."""

import sys

import arcade

from game.config import HEIGHT, TITLE, WIDTH
from game.views import MenuView


def main():
    windowed = "--windowed" in sys.argv
    window = arcade.Window(
        WIDTH, HEIGHT, TITLE, fullscreen=not windowed, resizable=True,
    )
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
