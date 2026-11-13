import sys

import pyglet

pyglet.options.debug_gl = False

import arcade

from game.config import HEIGHT, TITLE, WIDTH
from game.core import achievements
from game.scenes.menu import MenuView
from game.scenes.splash import SplashView


def warm_up():
    from game.scenes.market_dash import MarketDashView
    MarketDashView()
    from game.scenes.market_dash import catch
    catch.warm_up()

    from game.scenes.bbq import BbqView
    BbqView()


def main():
    windowed = "--windowed" in sys.argv
    window = arcade.Window(
        WIDTH, HEIGHT, TITLE, fullscreen=not windowed, resizable=True,
    )
    achievements.attach(window)
    warm_up()

    if "--market" in sys.argv:
        from game.scenes.market_dash import MarketDashView
        window.show_view(MarketDashView())
    elif "--bus" in sys.argv:
        from game.scenes.bumpy_bus import BumpyBusView
        window.show_view(BumpyBusView())
    elif "--highway" in sys.argv:
        from game.scenes.bumpy_bus import BusHighwayView
        window.show_view(BusHighwayView())
    elif "--feast" in sys.argv:
        from game.scenes.chao_dinner import TypingFeastView
        window.show_view(TypingFeastView())
    elif "--bbq" in sys.argv or "--after-bus" in sys.argv:
        from game.scenes.bbq import BbqView
        from game.config import CHAO_FADE_IN
        view = BbqView()
        view.fade_clock = CHAO_FADE_IN
        window.show_view(view)
    elif "--menu" in sys.argv:
        window.show_view(MenuView())
    else:
        window.show_view(SplashView())

    if "--screenshot" in sys.argv:
        out = sys.argv[sys.argv.index("--screenshot") + 1]

        def shot(_delta):
            arcade.get_image().save(out)
            window.close()

        arcade.schedule_once(shot, 0.6)

    arcade.run()


if __name__ == "__main__":
    main()
