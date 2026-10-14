import math
import arcade

from . import audio
from .config import HEIGHT, WIDTH
from .dialogue import DialogBox
from .options import SettingsPanel
from .pause import PauseMenu
from .views import MenuView, StageView
from .market_dash_common import BG_DIR, DialogueController, cover_rect, SkipConfirmModal
from .chao_widgets import TitleCard


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
        self.skip_modal = SkipConfirmModal()
        self.title_card = TitleCard()
        self.title_card_active = True

        # Include title_card so relayout() initializes self.band!
        self.widgets = [
            self.dialog, self.pause_menu, self.settings_panel, self.title_card
        ]

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

        def do_advance():
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

        def request_skip():
            synopsis_text = (
                "After an abrupt morning wake-up call from his cousin Dave, Terry realizes "
                "with horror that the big family BBQ feast is today—and his fridge is empty!\n\n"
                "With only six hours before his relatives arrive, Terry rushes to the local market "
                "only to find it overwhelmed by crazed discount shoppers. He must navigate the aisles "
                "to grab fresh vegetables and prime meats before they sell out!"
            )

            def do_confirm_skip():
                self.cleanup_audio()
                from .market_dash_stage import MarketStageView
                self.window.show_view(MarketStageView())

            def do_cancel():
                pass  # Modal closes and slideshow continues normally

            self.skip_modal.open(
                on_confirm=do_confirm_skip,
                on_cancel=do_cancel,
                synopsis=synopsis_text,
                title="SKIP INTRO STORY?"
            )

        self.dialog_ctrl = DialogueController(do_advance, request_skip)
        self.current_slide = 0
        self.current_texture = None
        self.typing_player = None
        self.ring_player = None

        self.shake_time = 0.0
        self.is_shaking = False
        self.shake_intensity = 0.0

        # 1. World Camera (vibrates with screen shake)
        self.camera = arcade.camera.Camera2D(
            position=(WIDTH / 2, HEIGHT / 2),
            projection=arcade.LRBT(-WIDTH / 2, WIDTH / 2, -HEIGHT / 2, HEIGHT / 2),
            viewport=self.stage.viewport()
        )

        # 2. UI Camera (stable in letterboxed canvas space for widgets/dialog)
        self.ui_camera = arcade.camera.Camera2D(
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
        if hasattr(self, "ui_camera"):
            self.ui_camera.viewport = self.stage.viewport()
        if hasattr(self, "title_card"):
            self.title_card.layout(self.stage)

        self.hint = self.stage.text(
            "Press Enter/Space to advance    Esc to pause",
            WIDTH - 80, 44, (200, 205, 215, 180), 12,
            anchor_x="right", anchor_y="center"
        )

    def trigger_slide(self, index):
        if index >= len(self.slides):
            self.cleanup_audio()
            from .market_dash_stage import MarketStageView
            self.window.show_view(MarketStageView())
            return

        self.current_slide = index
        speaker, text, img_target = self.slides[index]

        # Slides 0 to 3 are the ringing sequence
        if 0 <= index <= 7:
            self.is_shaking = True
            self.shake_intensity = 6.0
            if not self.ring_player:
                self.ring_player = audio.play("phone_ring", loop=True)
        else:
            self.is_shaking = False
            if self.ring_player:
                audio.bank().stop(self.ring_player)
                self.ring_player = None

        if index == 7:  # Terry picks up phone
            audio.play("phone_pickup")
        elif index == len(self.slides) - 1:  # Door slams on exit
            audio.play("door_slam")

        if img_target:
            self.current_texture = arcade.load_texture(str(img_target))

        if text:
            audio.play("dialog_open")
            self.dialog.open(speaker or "", text)
            self.dialog_ctrl.record(speaker, text)
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
        if self.pause_menu.visible or self.settings_panel.visible or self.skip_modal.visible:
            return

        if self.dialog.visible:
            self.dialog.update(delta_time)
            if not self.dialog.typing:
                self.stop_typing_sound()

        self.dialog_ctrl.update(
            delta_time,
            is_dialog_visible=self.dialog.visible,
            is_typing=self.dialog.typing
        )

        if self.is_shaking:
            self.shake_time += delta_time
            offset_x = math.sin(self.shake_time * 35.0) * self.shake_intensity
            offset_y = math.cos(self.shake_time * 30.0) * (self.shake_intensity * 0.5)
            self.camera.position = (WIDTH / 2 + offset_x, HEIGHT / 2 + offset_y)
        else:
            self.camera.position = (WIDTH / 2, HEIGHT / 2)

        if self.title_card_active:
            self.title_card.update(delta_time)
            if self.title_card.finished:
                self.title_card_active = False

    def on_draw(self):
        self.clear()

        # Draw entering board over the first scene
        if self.title_card_active:
            self.window.default_camera.use()
            self.title_card.draw()

        # 1. Background image (with camera shake)
        self.camera.use()
        if self.current_texture:
            arcade.draw_texture_rect(
                self.current_texture,
                arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
            )

        # 2. Dialog box & Hint in native screen space
        self.window.default_camera.use()
        if self.dialog.visible and getattr(self.dialog, "texture", None):
            self.dialog.draw()
            self.hint.draw()

        # 3. Canvas UI layer: Option buttons (upper-right) & History log panel
        self.ui_camera.use()
        self.dialog_ctrl.draw(show_controls=True)

        # 4. Modals in native screen space
        self.window.default_camera.use()
        if not self.settings_panel.visible:
            self.pause_menu.draw()
        self.settings_panel.draw()

        # 5. Skip confirmation modal (always on topmost layer)
        self.skip_modal.draw()

    def on_key_press(self, key, modifiers):
        # Prevent input if skip modal is active
        if self.skip_modal.visible:
            if key == arcade.key.ESCAPE:
                self.skip_modal.close()
            return

        if self.settings_panel.visible:
            if self.settings_panel.on_key_press(key) == "close":
                self.settings_panel.close()
            return

        if self.pause_menu.visible:
            self.run_action(self.pause_menu.on_key_press(key))
            return

        if key == arcade.key.ESCAPE:
            if self.dialog_ctrl.history_panel.visible:
                self.dialog_ctrl.history_panel.toggle()
                return
            self.pause_menu.open()
            return

        # Close history log with Enter/Space
        if self.dialog_ctrl.history_panel.visible:
            if key in (arcade.key.ENTER, arcade.key.SPACE, arcade.key.NUM_ENTER):
                self.dialog_ctrl.history_panel.toggle()
            return

        # Advance slides
        if key in (arcade.key.ENTER, arcade.key.SPACE, arcade.key.NUM_ENTER):
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

    def on_mouse_press(self, x, y, button, modifiers):
        canvas_x, canvas_y = self.canvas_point(x, y)

        # 1. Skip modal captures clicks first
        if self.skip_modal.visible:
            self.skip_modal.handle_mouse_press(canvas_x, canvas_y)
            return

        if self.settings_panel.on_mouse_press(canvas_x, canvas_y, button):
            return

        if self.pause_menu.visible:
            action = self.pause_menu.on_mouse_press(canvas_x, canvas_y, button)
            self.run_action(action)
            return

        # 2. UI Control buttons (LOG, AUTO, SKIP)
        if self.dialog_ctrl.handle_mouse_press(canvas_x, canvas_y):
            return

        # 3. Advance dialogue on left click
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

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.dialog_ctrl.history_panel.on_mouse_scroll(scroll_y)

    def on_mouse_motion(self, x, y, dx, dy):
        canvas_x, canvas_y = self.canvas_point(x, y)
        self.pause_menu.on_mouse_motion(canvas_x, canvas_y)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.settings_panel.on_mouse_drag(*self.canvas_point(x, y))

    def on_mouse_release(self, x, y, button, modifiers):
        self.settings_panel.on_mouse_release()

    def run_action(self, action):
        if action == "resume":
            self.pause_menu.close()
        elif action == "settings":
            self.settings_panel.open()
        elif action == "menu":
            self.cleanup_audio()
            self.window.show_view(MenuView())
        elif action == "quit":
            self.cleanup_audio()
            self.window.close()