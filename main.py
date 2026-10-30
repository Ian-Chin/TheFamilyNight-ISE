"""Entry point. Run `python main.py`, or `python main.py --windowed`."""

import sys

import pyglet

# pyglet checks for an OpenGL error after every single GL call when this is
# on, which costs more than the drawing itself. Set before arcade loads.
pyglet.options.debug_gl = False

import arcade  # noqa: E402

from game.config import HEIGHT, TITLE, WIDTH
from game.core import achievements
from game.scenes.menu import MenuView


def warm_up():
    """Build the scene's art before the menu is on screen.

    Cutting the characters out and drawing the panels takes long enough to be
    felt, and doing it when Play is clicked puts that pause where it is most
    obvious. Building a scene here and dropping it on the floor leaves every
    texture cache full, so the real one opens straight away. The heavy
    cut-outs are baked to assets/.cache as well, so this only costs real time
    on the first run after the art changes.
    """
    # 1. Market Dash Scene (Scene 1)
    from game.scenes.market_dash import MarketDashView
    MarketDashView()

    # 2. BBQ Scene (Scene 3)
    from game.scenes.bbq import BbqView
    BbqView()

    # 3. Chao Dinner Scene (Scene 4 - Work in progress by teammate)
    # from game.scenes.chao_dinner import ChaoDinnerView
    # ChaoDinnerView()


def main():
    windowed = "--windowed" in sys.argv
    window = arcade.Window(
        WIDTH, HEIGHT, TITLE, fullscreen=not windowed, resizable=True,
    )
    # Before any view is shown, so unlock popups draw on top of every view.
    achievements.attach(window)
    warm_up()

    # CLI shortcuts for rapid scene testing
    if "--market" in sys.argv:
        from game.scenes.market_dash import MarketDashView
        window.show_view(MarketDashView())
    elif "--bus" in sys.argv:
        from game.scenes.bumpy_bus import BumpyBusView
        window.show_view(BumpyBusView())
    elif "--feast" in sys.argv:
        from game.scenes.chao_dinner import TypingFeastView
        window.show_view(TypingFeastView())
    elif "--bbq" in sys.argv or "--after-bus" in sys.argv:
        from game.scenes.bbq import BbqView
        from game.config import CHAO_FADE_IN
        view = BbqView()
        view.fade_clock = CHAO_FADE_IN
        window.show_view(view)
    else:
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
