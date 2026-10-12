from pathlib import Path
import random
import arcade

from tools.prep_sprites import run_prep
from . import textures
from . import audio
from .config import HEIGHT, WIDTH
from .dialogue import DialogBox
from .options import SettingsPanel
from .pause import PauseMenu
from .views import MenuView, StageView
from .market_dash_common import (
    ASSETS_DIR, TERRY_GAME_DIR, SNATCHERS_BASE_DIR,
    INGREDIENTS_BASE_DIR, cover_rect,
    PLAY_LEFT, PLAY_RIGHT, PLAY_BOTTOM, PLAY_TOP
)
from .market_dash_sprites import (
    SnatcherSprite, IngredientDrop, get_separated_x
)


# ============================================================================
# PART 3: Catcher Mini-Game (3 Waves with Snatcher & Ingredient Checklist)
# ============================================================================
class MarketCatchView(StageView):
    """3-Wave mini-game catching items, defending with spin, and dialog cutscenes."""

    def __init__(self):
        super().__init__()
        run_prep()

        self.bg_texture = textures.background("market-dash/Scene 2.5 - game background.jpg")

        self.dialog = DialogBox()
        self.pause_menu = PauseMenu()
        self.settings_panel = SettingsPanel()
        self.widgets = [self.dialog, self.pause_menu, self.settings_panel]

        # Wave Durations: Wave 1 = 30s, Wave 2 = 30s, Wave 3 = 60s
        self.wave = 1
        self.wave_durations = {1: 30.0, 2: 30.0, 3: 5.0} # wave durations
        self.time_left = self.wave_durations[1]
        self.lives = 3

        # Spawning timers to control rates
        self.ingredient_spawn_timer = 0.0
        self.snatcher_spawn_timer = 0.0

        # Terry Spinning Defense state
        self.spinning = False
        self.spin_timer = 0.0
        self.spin_angle = 180.0

        # Load Terry Sprites
        terry_files = sorted(list(TERRY_GAME_DIR.glob("*.png")))
        if len(terry_files) >= 2:
            self.terry_tex_normal = arcade.load_texture(str(terry_files[1]))
            self.terry_tex_defend = arcade.load_texture(str(terry_files[0]))
        elif len(terry_files) == 1:
            self.terry_tex_normal = arcade.load_texture(str(terry_files[0]))
            self.terry_tex_defend = self.terry_tex_normal
        else:
            self.terry_tex_normal = arcade.make_circle_texture(32, (230, 60, 60))
            self.terry_tex_defend = self.terry_tex_normal

        self.player = arcade.Sprite(self.terry_tex_normal, scale=0.15)
        self.player.angle = 180
        self.player.center_x = (PLAY_LEFT + PLAY_RIGHT) / 2
        self.player.center_y = 80
        self.player_move_dir = 0
        self.player_list = arcade.SpriteList()
        self.player_list.append(self.player)

        # Load Ingredients
        self.all_ingredients = {}
        for f in sorted(list(INGREDIENTS_BASE_DIR.glob("*.png"))):
            name = f.stem.replace("_", " ").title()
            self.all_ingredients[name] = arcade.load_texture(str(f))

        all_keys = list(self.all_ingredients.keys())
        self.meat_keys = all_keys[:5] if len(all_keys) >= 5 else all_keys
        self.veg_keys = all_keys[5:10] if len(all_keys) >= 10 else all_keys[len(self.meat_keys):]
        self.collected_status = {k: False for k in all_keys}

        # Load Snatchers
        self.snatcher_types = []
        if SNATCHERS_BASE_DIR.exists():
            for folder in sorted([p for p in SNATCHERS_BASE_DIR.iterdir() if p.is_dir()]):
                falls = [arcade.load_texture(str(folder / f"fall_{i}.png")) for i in range(6) if (folder / f"fall_{i}.png").exists()]
                grabs = [arcade.load_texture(str(folder / f"grab_{i}.png")) for i in range(6) if (folder / f"grab_{i}.png").exists()]
                if falls and grabs:
                    self.snatcher_types.append((falls, grabs))

        if not self.snatcher_types:
            dummy_fall = [arcade.make_circle_texture(32, (200, 40, 40))] * 6
            dummy_grab = [arcade.make_circle_texture(32, (240, 20, 20))] * 6
            self.snatcher_types.append((dummy_fall, dummy_grab))

        self.items_list = arcade.SpriteList()
        self.snatchers_list = arcade.SpriteList()
        self.held = set()

        # Inter-Wave Dialogue Queue
        self.in_wave_dialogue = False
        self.dialogue_queue = []
        self.dialogue_bg = None

        # Setup 1280x720 letterboxed camera
        self.camera = arcade.camera.Camera2D(
            position=(WIDTH / 2, HEIGHT / 2),
            projection=arcade.LRBT(-WIDTH / 2, WIDTH / 2, -HEIGHT / 2, HEIGHT / 2),
            viewport=self.stage.viewport()
        )
        self.spawn_wave()
        self.relayout()

    def spawn_wave(self):
        self.items_list.clear()
        self.snatchers_list.clear()
        self.time_left = self.wave_durations[self.wave]
        self.ingredient_spawn_timer = 0.0
        self.snatcher_spawn_timer = 0.0

        if self.wave == 3:
            self.player.texture = self.terry_tex_defend
        else:
            self.player.texture = self.terry_tex_normal

        # Initial seed
        if self.wave == 1:
            for name in self.meat_keys[:2]:
                spawn_x = get_separated_x(self.items_list)
                self.items_list.append(IngredientDrop(name, self.all_ingredients[name], initial_x=spawn_x))
            for _ in range(3):
                falls, grabs = random.choice(self.snatcher_types)
                spawn_x = get_separated_x(list(self.items_list) + list(self.snatchers_list))
                self.snatchers_list.append(SnatcherSprite(falls, grabs, initial_x=spawn_x))

        elif self.wave == 2:
            for name in self.veg_keys[:2]:
                spawn_x = get_separated_x(self.items_list)
                self.items_list.append(IngredientDrop(name, self.all_ingredients[name], initial_x=spawn_x))
            for _ in range(4):
                falls, grabs = random.choice(self.snatcher_types)
                spawn_x = get_separated_x(list(self.items_list) + list(self.snatchers_list))
                self.snatchers_list.append(SnatcherSprite(falls, grabs, initial_x=spawn_x))

        elif self.wave == 3:
            for _ in range(6):
                falls, grabs = random.choice(self.snatcher_types)
                spawn_x = get_separated_x(self.snatchers_list)
                self.snatchers_list.append(SnatcherSprite(falls, grabs, initial_x=spawn_x))

    def trigger_wave_dialogue(self, lines, on_finish_callback):
        self.in_wave_dialogue = True
        self.dialogue_queue = list(lines)
        self.dialogue_on_finish = on_finish_callback

        # Pop the first entry
        item = self.dialogue_queue.pop(0)
        speaker, text = item[0], item[1]
        img = item[2] if len(item) > 2 else None

        if img:
            self.dialogue_bg = arcade.load_texture(str(img)) if isinstance(img, (str, Path)) else img
        else:
            self.dialogue_bg = None

        self.dialog.open(speaker, text)

    def advance_wave_dialogue(self):
        if self.dialogue_queue:
            item = self.dialogue_queue.pop(0)
            speaker, text = item[0], item[1]
            img = item[2] if len(item) > 2 else None

            if img:
                self.dialogue_bg = arcade.load_texture(str(img)) if isinstance(img, (str, Path)) else img
            # If img is None, keep the existing dialogue_bg or reset as desired

            self.dialog.open(speaker, text)
        else:
            self.dialog.close()
            self.in_wave_dialogue = False
            self.dialogue_bg = None
            if hasattr(self, "dialogue_on_finish") and self.dialogue_on_finish:
                cb = self.dialogue_on_finish
                self.dialogue_on_finish = None
                cb()

    def on_update(self, delta_time):
        if self.pause_menu.visible or self.settings_panel.visible:
            return

        if self.in_wave_dialogue:
            self.dialog.update(delta_time)
            return

        # 1. Timer countdown & Timeout Handling
        self.time_left -= delta_time
        if self.time_left <= 0:
            active_pool = self.meat_keys if self.wave == 1 else self.veg_keys if self.wave == 2 else []
            # In Wave 1 or 2, verify if all required items were collected
            if self.wave < 3 and not all(self.collected_status[k] for k in active_pool):
                timeout_lines = [
                    ("Terry", "Time's up! The shelves were cleared before I could get everything!", None),
                    ("Terry", "I need to take a breath and try again!", None),
                ]
                def return_to_market_timeout():
                    from .market_dash_stage import MarketStageView
                    self.window.show_view(MarketStageView(unlocked=True))
                self.trigger_wave_dialogue(timeout_lines, return_to_market_timeout)
                return

            self.complete_or_advance_wave()
            return

        # 2. Player Movement & Spinning
        if self.spinning:
            self.spin_timer -= delta_time
            self.spin_angle += 1440.0 * delta_time  # Rapid spin
            self.player.angle = self.spin_angle
            if self.spin_timer <= 0:
                self.spinning = False
                self.player.angle = 180  # Reset facing UP
        else:
            self.player.angle = 180

        self.player.center_x += self.player_move_dir * 10.0
        self.player.center_x = max(PLAY_LEFT + 40, min(PLAY_RIGHT - 40, self.player.center_x))

        # 3. Dynamic Spawning: Snatchers spawn more frequently than vegetables
        self.snatcher_spawn_timer += delta_time
        if self.snatcher_spawn_timer >= 2.2:
            self.snatcher_spawn_timer = 0.0
            max_snatchers = 4 if self.wave == 1 else 6 if self.wave == 2 else 9
            if len(self.snatchers_list) < max_snatchers:
                falls, grabs = random.choice(self.snatcher_types)
                all_obstacles = list(self.items_list) + list(self.snatchers_list)
                spawn_x = get_separated_x(all_obstacles)
                self.snatchers_list.append(SnatcherSprite(falls, grabs, initial_x=spawn_x))

        if self.wave < 3:
            self.ingredient_spawn_timer += delta_time
            if self.ingredient_spawn_timer >= 4.0:  # Reduced vegetable/meat spawn rate
                self.ingredient_spawn_timer = 0.0
                active_pool = self.meat_keys if self.wave == 1 else self.veg_keys
                uncollected = [k for k in active_pool if not self.collected_status[k]]
                if uncollected and len(self.items_list) < 4:
                    pick_name = random.choice(uncollected)
                    if not any(item.item_name == pick_name for item in self.items_list):
                        spawn_x = get_separated_x(self.items_list)
                        self.items_list.append(IngredientDrop(pick_name, self.all_ingredients[pick_name], initial_x=spawn_x))

        # 4. Ingredients Movement & Collision
        for item in list(self.items_list):
            item.center_y += item.change_y
            if item.top < PLAY_BOTTOM:
                if self.collected_status.get(item.item_name, False):
                    item.remove_from_sprite_lists()
                else:
                    item.reset_pos(existing_list=self.items_list)

            if arcade.check_for_collision(self.player, item):
                audio.play("ui_click")
                self.collected_status[item.item_name] = True
                item.remove_from_sprite_lists()

                for duplicate in list(self.items_list):
                    if duplicate.item_name == item.item_name:
                        duplicate.remove_from_sprite_lists()

                # Check if all items in active pool have been collected
                active_pool = self.meat_keys if self.wave == 1 else self.veg_keys
                if all(self.collected_status[k] for k in active_pool):
                    self.complete_or_advance_wave()
                    return

        # 5. Snatchers Hazard Update
        for snatcher in list(self.snatchers_list):
            snatcher.update_behavior(delta_time, self.player.center_y, self.player.center_x, is_wave_3=(self.wave == 3))

            if snatcher.top < PLAY_BOTTOM or snatcher.bottom > HEIGHT + 200 or snatcher.right < 0 or snatcher.left > WIDTH:
                if snatcher.knocked_out:
                    snatcher.remove_from_sprite_lists()
                else:
                    all_entities = list(self.items_list) + [s for s in self.snatchers_list if s != snatcher]
                    snatcher.reset_pos(existing_list=all_entities)

            if not snatcher.knocked_out and arcade.check_for_collision(self.player, snatcher):
                if self.spinning:
                    audio.play("ui_click")
                    snatcher.trigger_knockout(self.player.center_x)
                else:
                    audio.play("ui_click")
                    self.lives -= 1
                    all_entities = list(self.items_list) + [s for s in self.snatchers_list if s != snatcher]
                    snatcher.reset_pos(existing_list=all_entities)

                    if self.lives <= 0:
                        defeat_lines = [
                            ("Terry", "Oof! That frantic mob completely trampled me!", None),
                            ("Terry", "I need to take a breath and try again!", None),
                        ]
                        def return_to_market():
                            from .market_dash_stage import MarketStageView
                            self.window.show_view(MarketStageView(unlocked=True))

                        self.trigger_wave_dialogue(defeat_lines, return_to_market)
                        return

    def complete_or_advance_wave(self):
        if self.wave == 1:
            dialogue = [
                ("Terry", "Phew! Got all the prime meat before that mob snatched them!", None),
                ("Terry", "Now I need to sprint to the produce racks for fresh vegetables!", None),
            ]
            def next_wave():
                self.wave = 2
                self.spawn_wave()
            self.trigger_wave_dialogue(dialogue, next_wave)

        elif self.wave == 2:
            fish_img = ASSETS_DIR / "backgrounds" / "market-dash" / "fish obtained.jpg"
            if not fish_img.exists():
                fish_img = ASSETS_DIR / "market-dash" / "fish obtained.jpg"

            dialogue = [
                ("Terry", "Fresh vegetables secured! But wait... the crowd noticed my full basket!", None),
                ("Terry", "They're rushing at me! I have to defend myself and dodge through!", None),
                ("Terry", "I need something to help knock them away!", None),
                ("Terry", "Hmmmmmmmm...", None),
                ("Terry", "It's not a good idea... but this is all I've got...", None),
                ("Terry", "The one and only frozen mackerel... It was quite expensive though!", fish_img if fish_img.exists() else None),
                ("Terry", "Here they come! Left-click to swing the fish and knock them away!", None),
            ]
            def next_wave():
                self.wave = 3
                self.spawn_wave()
            self.trigger_wave_dialogue(dialogue, next_wave)

        elif self.wave == 3:
            dialogue = [
                ("Terry", "I dodged them all! The last of the mob gave up chasing!", None),
            ]
            def finish():
                from .market_dash_ending import MarketEndingView
                self.window.show_view(MarketEndingView())
            self.trigger_wave_dialogue(dialogue, finish)

    def on_draw(self):
        self.clear()

        # --- 1. GAMEPLAY & HUD IN CAMERA SPACE (1280 x 720) ---
        self.camera.use()

        # Background selection: Dialogue image > Game background
        if self.in_wave_dialogue and getattr(self, "dialogue_bg", None):
            arcade.draw_texture_rect(
                self.dialogue_bg,
                arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
            )
        elif self.bg_texture:
            arcade.draw_texture_rect(
                self.bg_texture,
                arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
            )

        # Only draw game sprites & HUD when not displaying a full-screen story image
        if not (self.in_wave_dialogue and getattr(self, "dialogue_bg", None)):
            self.items_list.draw()
            self.snatchers_list.draw()
            self.player_list.draw()

            # =================================================================
            # REDESIGNED WOODEN/METALLIC HUD PROGRESS BAR
            # =================================================================
            total_time = self.wave_durations[self.wave]
            progress = max(0.0, min(1.0, self.time_left / total_time))

            panel_w = 460
            panel_h = 58
            panel_x = (WIDTH / 2) - 30
            panel_y = HEIGHT - 38

            # 1. Outer Heavy Wooden Plaque (Shadow & Border)
            arcade.draw_rect_filled(arcade.XYWH(panel_x, panel_y - 2, panel_w, panel_h), (25, 14, 8, 230))
            arcade.draw_rect_filled(arcade.XYWH(panel_x, panel_y, panel_w, panel_h), (85, 48, 24, 255))
            arcade.draw_rect_filled(arcade.XYWH(panel_x, panel_y, panel_w - 6, panel_h - 6), (138, 88, 48, 255))
            arcade.draw_rect_outline(arcade.XYWH(panel_x, panel_y, panel_w, panel_h), (42, 22, 10), 2)

            # 2. Wave Label Banner Header
            wave_name = "WAVE 1: VEGETABLE HARVEST" if self.wave == 1 else "WAVE 2: PRIME STEAKS" if self.wave == 2 else "WAVE 3: DEFEND BASKET!"
            arcade.draw_text(
                wave_name,
                panel_x,
                panel_y + 13,
                (255, 238, 185),
                12,
                bold=True,
                anchor_x="center",
                anchor_y="center"
            )

            # 3. Recessed Slot Gauge Background
            bar_w = 420
            bar_h = 16
            bar_y = panel_y - 12
            arcade.draw_rect_filled(arcade.XYWH(panel_x, bar_y, bar_w, bar_h), (24, 20, 18, 250))
            arcade.draw_rect_outline(arcade.XYWH(panel_x, bar_y, bar_w, bar_h), (50, 42, 36), 2)

            # 4. Two-Tone Gradient Fill with Warning State
            fill_w = max(4.0, bar_w * progress)
            fill_center_x = (panel_x - bar_w / 2) + fill_w / 2

            if self.wave == 3:
                c_main = (235, 75, 75)
                c_hi = (255, 130, 130)
            elif progress < 0.25:
                c_main = (235, 100, 50)
                c_hi = (255, 160, 90)
            else:
                c_main = (225, 175, 55)
                c_hi = (255, 225, 120)

            # Gauge Body
            arcade.draw_rect_filled(arcade.XYWH(fill_center_x, bar_y, fill_w, bar_h - 2), c_main)
            # Specular top highlight line
            arcade.draw_rect_filled(arcade.XYWH(fill_center_x, bar_y + 4, fill_w, 3), c_hi)

            # 5. Timer Badge on Right Side
            seconds_left = max(0, int(self.time_left))
            arcade.draw_text(
                f"{seconds_left:02d}s",
                panel_x + (bar_w / 2) - 24,
                panel_y + 13,
                (255, 215, 110),
                11,
                bold=True,
                anchor_x="center",
                anchor_y="center"
            )

            # 6. Polished HP Display with Backdrop
            hp_w = 115
            hp_h = 36
            hp_x = PLAY_LEFT + 60
            hp_y = HEIGHT - 32
            arcade.draw_rect_filled(arcade.XYWH(hp_x, hp_y, hp_w, hp_h), (85, 48, 24, 220))
            arcade.draw_rect_filled(arcade.XYWH(hp_x, hp_y, hp_w - 4, hp_h - 4), (138, 88, 48, 240))
            arcade.draw_rect_outline(arcade.XYWH(hp_x, hp_y, hp_w, hp_h), (42, 22, 10), 2)
            hearts = "♥ " * self.lives + "♡ " * (3 - self.lives)
            arcade.draw_text(f"HP: {hearts}", hp_x, hp_y, (255, 85, 85), 14, bold=True, anchor_x="center", anchor_y="center")

            # =================================================================
            # RESTORED WOODEN SHOPPING LIST CHECKLIST
            # =================================================================
            active_keys = self.meat_keys if self.wave == 1 else self.veg_keys if self.wave == 2 else list(self.all_ingredients.keys())
            board_w = 255
            board_h = 44 + (len(active_keys) * 30)
            board_x = PLAY_RIGHT - (board_w / 2) - 8
            board_y = HEIGHT - (board_h / 2) - 15

            arcade.draw_rect_filled(arcade.XYWH(board_x, board_y, board_w, board_h), (85, 48, 24, 240))
            arcade.draw_rect_filled(arcade.XYWH(board_x, board_y, board_w - 8, board_h - 8), (138, 88, 48, 245))
            arcade.draw_rect_outline(arcade.XYWH(board_x, board_y, board_w, board_h), (50, 28, 14), 3)

            header_text = "SHOPPING LIST:" if self.wave < 3 else "ALL ITEMS SECURED:"
            arcade.draw_text(header_text, board_x - (board_w / 2) + 14, board_y + (board_h / 2) - 22, (255, 240, 195), 13, bold=True)

            draw_y = board_y + (board_h / 2) - 50
            for name in active_keys:
                collected = self.collected_status.get(name, False)
                tex = self.all_ingredients.get(name)

                if tex:
                    icon_color = arcade.types.Color(255, 255, 255, 255) if collected else arcade.types.Color(95, 90, 85, 140)
                    arcade.draw_texture_rect(
                        tex,
                        arcade.XYWH(board_x - (board_w / 2) + 26, draw_y, 24, 24),
                        color=icon_color
                    )

                txt_color = (130, 255, 150) if collected else (210, 190, 170)
                status_symbol = "✔" if collected else "○"
                arcade.draw_text(f"{status_symbol} {name}", board_x - (board_w / 2) + 48, draw_y - 7, txt_color, 13, bold=True)
                draw_y -= 30

            # Wave 3 Hint
            if self.wave == 3:
                arcade.draw_text("Left Click to Spin & Defend!", WIDTH / 2 - 40, 30, (255, 230, 140), 14, anchor_x="center")

        # --- 2. UI WIDGETS IN SCREEN SPACE ---
        self.window.default_camera.use()

        if self.in_wave_dialogue and self.dialog.visible:
            self.dialog.draw()

        if not self.settings_panel.visible:
            self.pause_menu.draw()
        self.settings_panel.draw()

    def on_key_press(self, key, modifiers):
        if self.in_wave_dialogue:
            if key in (arcade.key.ENTER, arcade.key.SPACE, arcade.key.NUM_ENTER):
                if self.dialog.typing:
                    self.dialog.advance()
                else:
                    self.advance_wave_dialogue()
            return

        if self.settings_panel.visible:
            if self.settings_panel.on_key_press(key) == "close":
                self.settings_panel.close()
            return
        if self.pause_menu.visible:
            self.run_action(self.pause_menu.on_key_press(key))
            return
        if key == arcade.key.ESCAPE:
            self.held.clear()
            self.player_move_dir = 0
            self.pause_menu.open()
            return

        self.held.add(key)
        self.update_movement()

    def on_key_release(self, key, modifiers):
        self.held.discard(key)
        self.update_movement()

    def update_movement(self):
        dx = (arcade.key.D in self.held or arcade.key.RIGHT in self.held) - \
             (arcade.key.A in self.held or arcade.key.LEFT in self.held)
        self.player_move_dir = dx

    def on_mouse_press(self, x, y, button, modifiers):
        canvas_x, canvas_y = self.canvas_point(x, y)
        if self.in_wave_dialogue:
            if button == arcade.MOUSE_BUTTON_LEFT:
                if self.dialog.typing:
                    self.dialog.advance()
                else:
                    self.advance_wave_dialogue()
            return

        if self.settings_panel.on_mouse_press(canvas_x, canvas_y, button):
            return
        if self.pause_menu.visible:
            self.run_action(self.pause_menu.on_mouse_press(canvas_x, canvas_y, button))
            return

        # Terry can ONLY spin-defend in Wave 3 after obtaining the mackerel
        if button == arcade.MOUSE_BUTTON_LEFT and not self.spinning and self.wave == 3:
            audio.play("ui_click")
            self.spinning = True
            self.spin_timer = 0.35

    def on_mouse_motion(self, x, y, dx, dy):
        self.pause_menu.on_mouse_motion(*self.canvas_point(x, y))

    def run_action(self, action):
        if action == "resume":
            self.pause_menu.close()
        elif action == "settings":
            self.settings_panel.open()
        elif action == "menu":
            from .views import MenuView
            self.window.show_view(MenuView())
        elif action == "quit":
            self.window.close()