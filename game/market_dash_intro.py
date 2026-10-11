import math
import arcade

from . import audio
from .config import HEIGHT, WIDTH
from .dialogue import DialogBox
from .options import SettingsPanel
from .pause import PauseMenu
from .views import MenuView, StageView
from .market_dash_common import BG_DIR


# ============================================================================
# PART 1: Story Intro (Slideshow + Dialogue)
# ============================================================================
class StorySlideView(StageView):
    """Part 1: Dialogue slideshow switching background images and conversation lines."""

    def __init__(self):
        super().__init__()
        self.dialog = DialogBox()
        self.pause_menu = PauseMenu()
        self.settings_panel = SettingsPanel()
        self.widgets = [self.dialog, self.pause_menu, self.settings_panel]

        self.slides = [
            # Fully asleep
            ("", None, BG_DIR / "Scene 1.1 - Sleep.jpg"),

            # Half awake
            ("", "*BRRRRR! BRRRRR!*", BG_DIR / "Scene 1.2 - half sleep.jpg"),
            ("Terry", "...Five more minutes, Mom...", BG_DIR / "Scene 1.2 - half sleep.jpg"),

            # Blur awake
            ("", None, BG_DIR / "Scene 1.3 - blur awake.jpg"),

            # Show phone ringing
            ("Phone", "*BRRRRRR*", BG_DIR / "Scene 1.4 - phone ringing.jpg"),

            # Terry confused to mad
            ("Terry", "Ugh... who has the audacity to call this early on a Saturday?", BG_DIR / "Scene 1.5 - confused toward phone.jpg"),
            ("Terry", "If this is CelcomDigi or Maxis asking me to upgrade my plan again, I swear...", BG_DIR / "Scene 1.6 - question towards phone.jpg"),
            (None, None, BG_DIR / "Scene 1.7 - mad towards phone.jpg"),

            # Picking up aggressively
            ("Terry", "Let's see who's volunteering to get chewed out.", BG_DIR / "Scene 1.8 - pick up phone.jpg"),
            ("Terry", "Speak! You have ten seconds before I block this number forever.", BG_DIR / "Scene 1.9 - shout to answer.jpg"),

            # Cousin cheerful contrast
            ("Cousin", "Whoa, morning grumpy! Just checking in—how's prep for the big BBQ tonight?", BG_DIR / "Scene 1.10 - answering phone.jpg"),
            ("Terry", "(...Wait. The BBQ. The family BBQ. TODAY?!)", BG_DIR / "Scene 1.10 - answering phone.jpg"),
            ("Terry", "(I haven't bought a single piece of meat! The fridge is completely empty!)", BG_DIR / "Scene 1.10 - answering phone.jpg"),

            # Terry faking composure on the line
            ("Terry", "Pfft, Dave! My favorite cousin! Haha... prep? Everything is... totally under control. Prime cuts, secret sauce, the works.", BG_DIR / "Scene 1.11 - answering panickly.jpg"),
            ("Cousin", "Awesome! The whole family is hyped. Your legendary grilled steak was the talk of the month last year!", BG_DIR / "Scene 1.11 - answering panickly.jpg"),
            ("Cousin", "We're packing into the car now. See you around 6:00 PM with the kids!", BG_DIR / "Scene 1.11 - answering panickly.jpg"),
            ("Terry", "Haha... yeah. Can't wait. Bring your appetites! Bye!", BG_DIR / "Scene 1.11 - answering panickly.jpg"),

            # Realizing the deadline & rushing
            (None, None, BG_DIR / "Scene 1.12 - standing out bed.jpg"),
            ("Terry", "Six hours. I have exactly six hours before four relatives storm this house.", BG_DIR / "Scene 1.12 - standing out bed.jpg"),
            ("Terry", "If I don't sprint to the market right now, I'm a dead man!", BG_DIR / "Scene 1.12 - standing out bed.jpg"),

            # Running out the door
            (None, None, BG_DIR / "Scene 1.13 - go out.jpg"),

            # Approaching the market
            (None, None, BG_DIR / "Scene 2.1 - supermarket overview.jpg"),
            ("Terry", "Why is the market so crowded today?", BG_DIR / "Scene 2.2 - crowd in front door.jpg"),
            ("Terry", "Okay, okay, I can do this. Just a few more items and I'll be home free.", BG_DIR / "Scene 2.2 - crowd in front door.jpg"),
            ("Terry", "I just need to get through this crowd and grab the ingredients.", BG_DIR / "Scene 2.3 - chaos scene in market.jpg"),
        ]
        self.current_slide = 0
        self.current_texture = None
        self.typing_player = None
        self.ring_player = None

        self.shake_time = 0.0
        self.is_shaking = False
        self.shake_intensity = 0.0

        # Camera setup
        self.camera = arcade.camera.Camera2D(
            position=(WIDTH / 2, HEIGHT / 2),
            projection=arcade.LRBT(-WIDTH / 2, WIDTH / 2, -HEIGHT / 2, HEIGHT / 2),
            viewport=self.stage.viewport()
        )
        self.relayout()

    def on_show_view(self):
        self.trigger_slide(0)

    def cleanup_audio(self):
        self.stop_typing_sound()
        if self.ring_player:
            audio.bank().stop(self.ring_player)
            self.ring_player = None

    def on_hide_view(self):
        self.cleanup_audio()

    def relayout(self):
        super().relayout()
        if hasattr(self, "camera"):
            self.camera.viewport = self.stage.viewport()
        self.hint = self.stage.text(
            "Press Enter/Space to advance    Esc to pause",
            WIDTH / 2, 28, (230, 235, 245), 14,
            anchor_x="center", anchor_y="center"
        )

    def trigger_slide(self, index):
        if index >= len(self.slides):
            self.cleanup_audio()
            from .market_dash_stage import MarketStageView
            self.window.show_view(MarketStageView())
            return

        self.current_slide = index
        speaker, text, img_target = self.slides[index]

        # --- Screen Shake & Looping Phone Ring ---
        # Slides 0 to 3 are the ringing sequence
        if 0 <= index <= 3:
            self.is_shaking = True
            self.shake_intensity = 6.0
            if not self.ring_player:
                self.ring_player = audio.play("phone_ring", loop=True)
        else:
            self.is_shaking = False
            # Stop the ringing once Terry picks up the receiver
            if self.ring_player:
                audio.bank().stop(self.ring_player)
                self.ring_player = None

        # --- One-Shot Sound Triggers ---
        if index == 7:  # Terry picks up the phone
            audio.play("phone_pickup")
        elif index == len(self.slides) - 1:  # Door slams on exit
            audio.play("door_slam")

        # --- Texture & Dialog Rendering ---
        if img_target:
            self.current_texture = arcade.load_texture(str(img_target))

        if text:
            audio.play("dialog_open")
            self.dialog.open(speaker or "", text)
            self.stop_typing_sound()
            self.typing_player = audio.play("dialog_type", loop=True)
        else:
            self.stop_typing_sound()
            self.dialog.close()

    def stop_typing_sound(self):
        if self.typing_player:
            audio.bank().stop(self.typing_player)
            self.typing_player = None

    def on_update(self, delta_time):
        if self.pause_menu.visible or self.settings_panel.visible:
            return

        # Advance dialog typewriter
        if self.dialog.visible:
            self.dialog.update(delta_time)
            if not self.dialog.typing:
                self.stop_typing_sound()

        # Handle screen shake
        if self.is_shaking:
            self.shake_time += delta_time
            # Rapid vibration back and forth (frequency = 35)
            offset_x = math.sin(self.shake_time * 35.0) * self.shake_intensity
            offset_y = math.cos(self.shake_time * 30.0) * (self.shake_intensity * 0.5)
            self.camera.position = (WIDTH / 2 + offset_x, HEIGHT / 2 + offset_y)
        else:
            self.camera.position = (WIDTH / 2, HEIGHT / 2)

    def on_draw(self):
        self.clear()

        # 1. World & Background in Camera space (shakes with phone ring)
        self.camera.use()

        if self.current_texture:
            arcade.draw_texture_rect(
                self.current_texture,
                arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
            )

        # 2. Switch to window default camera for UI widgets & dialog
        self.window.default_camera.use()
        self.hint.draw()

        if self.dialog.visible:
            self.dialog.draw()

        if not self.settings_panel.visible:
            self.pause_menu.draw()
        self.settings_panel.draw()

    def on_key_press(self, key, modifiers):
        if self.settings_panel.visible:
            if self.settings_panel.on_key_press(key) == "close":
                self.settings_panel.close()
            return

        if self.pause_menu.visible:
            self.run_action(self.pause_menu.on_key_press(key))
            return

        if key == arcade.key.ESCAPE:
            self.pause_menu.open()
            return

        if key in (arcade.key.ENTER, arcade.key.SPACE, arcade.key.NUM_ENTER):
            if self.dialog.visible:
                if self.dialog.typing:
                    self.stop_typing_sound()
                    self.dialog.advance()  # Finishes current typing line
                else:
                    self.stop_typing_sound()
                    self.trigger_slide(self.current_slide + 1)
            else:
                # For silent slides where dialog is closed
                self.stop_typing_sound()
                self.trigger_slide(self.current_slide + 1)

    def run_action(self, action):
        if action == "resume":
            self.pause_menu.close()
        elif action == "settings":
            self.settings_panel.open()
        elif action == "menu":
            self.window.show_view(MenuView())
        elif action == "quit":
            self.window.close()

    def on_mouse_motion(self, x, y, dx, dy):
        canvas_x, canvas_y = self.canvas_point(x, y)
        self.pause_menu.on_mouse_motion(canvas_x, canvas_y)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.settings_panel.on_mouse_drag(*self.canvas_point(x, y))

    def on_mouse_release(self, x, y, button, modifiers):
        self.settings_panel.on_mouse_release()

    def on_mouse_press(self, x, y, button, modifiers):
        canvas_x, canvas_y = self.canvas_point(x, y)

        # 1. Check settings panel interactions
        if self.settings_panel.on_mouse_press(canvas_x, canvas_y, button):
            return

        # 2. Check pause menu buttons (Resume, Settings, Main Menu, Quit)
        if self.pause_menu.visible:
            action = self.pause_menu.on_mouse_press(canvas_x, canvas_y, button)
            self.run_action(action)
            return

        # 3. Normal story progression on left click (when pause menu is closed)
        if button == arcade.MOUSE_BUTTON_LEFT and not self.pause_menu.visible:
            if self.dialog.visible:
                if self.dialog.typing:
                    self.stop_typing_sound()
                    self.dialog.advance()
                else:
                    self.stop_typing_sound()
                    self.trigger_slide(self.current_slide + 1)
            else:
                self.stop_typing_sound()
                self.trigger_slide(self.current_slide + 1)