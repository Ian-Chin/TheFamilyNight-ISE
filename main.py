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
    # 1. Market Dash Scene (Scene 1)
    from game.market_dash import MarketDashView
    MarketDashView()

    # 2. BBQ Scene (Scene 3)
    from game.bbq_scene import BbqView
    BbqView()

    # 3. Chao Dinner Scene (Scene 4 - Work in progress by teammate)
    # from game.chao_dinner import ChaoDinnerView
    # ChaoDinnerView()


def main():
    windowed = "--windowed" in sys.argv
    window = arcade.Window(
        WIDTH, HEIGHT, TITLE, fullscreen=not windowed, resizable=True,
    )
    warm_up()

    # CLI shortcuts for rapid scene testing
    if "--market" in sys.argv:
        from game.market_dash import MarketDashView
        window.show_view(MarketDashView())
    elif "--bus" in sys.argv:
        from game.bumpy_bus import BumpyBusView
        window.show_view(BumpyBusView())
    elif "--bbq" in sys.argv or "--after-bus" in sys.argv:
        from game.bbq_scene import BbqView
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
