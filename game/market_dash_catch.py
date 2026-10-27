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
    PLAY_LEFT, PLAY_RIGHT, PLAY_BOTTOM, PLAY_TOP,
    DialogueController, RetryModal
)
from .market_dash_sprites import (
    SnatcherSprite, IngredientDrop, get_separated_x
)


class MarketCatchView(StageView):
    """Stand-alone stage for either Veg, Meat, or Defend mode."""

    def __init__(self, mode="veg", veg_done=False, meat_done=False):
        super().__init__()
        run_prep()

        self.mode = mode  # 'veg', 'meat', or 'defend'
        self.veg_done = veg_done
        self.meat_done = meat_done
        self.completed = False

        self.bg_texture = textures.background("market-dash/Scene 2.5 - game background.jpg")

        self.dialog = DialogBox()
        self.pause_menu = PauseMenu()
        self.settings_panel = SettingsPanel()
        self.retry_modal = RetryModal()
        self.widgets = [self.dialog, self.pause_menu, self.settings_panel]

        # Duration: 30s for gathering, 45s for defend
        self.duration = 45.0 if self.mode == "defend" else 30.0
        self.time_left = self.duration

        # HP, Heart animation, and Damage Flash variables
        self.max_lives = 3
        self.lives = self.max_lives
        self.damage_alpha = 0.0      
        self.heart_anim_timer = 0.0
        self.heart_anim_state = 0
        self.breaking_idx = -1

        # Setup Heart sprites
        self.hearts = arcade.SpriteList()
        hp_start_x = PLAY_LEFT + 28
        hp_y = HEIGHT - 32
        for i in range(self.max_lives):
            heart = arcade.Sprite(textures.ui_image("Character_HP.png"), scale=0.14)
            heart.center_x = hp_start_x + (i * 38)
            heart.center_y = hp_y
            self.hearts.append(heart)

        self.ingredient_spawn_timer = 0.0
        self.snatcher_spawn_timer = 0.0

        # Terry Spin Mechanics (Defend mode)
        self.spinning = False
        self.spin_timer = 0.0
        self.spin_angle = 180.0

        # Terry Block & Speed Boost Mechanics
        self.blocking = False
        self.block_timer = 0.0
        self.block_duration = 0.45  # Increased slightly for comfortable parry timing
        self.base_speed = 10.0
        self.boost_speed = 17.0
        self.speed_boosted = False

        # Load Terry Sprites
        tex_without_fish = arcade.load_texture(str(TERRY_GAME_DIR / "sprite without fish.png"))
        tex_holding_fish = arcade.load_texture(str(TERRY_GAME_DIR / "sprite holding fish.png"))
        tex_defending    = arcade.load_texture(str(TERRY_GAME_DIR / "sprite defending.png"))

        self.terry_tex_normal = tex_without_fish
        self.terry_tex_defend = tex_holding_fish
        self.terry_tex_action = tex_defending      # Used when blocking/defending

        active_tex = self.terry_tex_defend if self.mode == "defend" else self.terry_tex_normal
        self.player = arcade.Sprite(active_tex, scale=0.15)
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

        # Explicitly categorize meat vs vegetable items by key name
        veg_names = ["Cabbage", "Carrot", "Eggplant", "Green Pepperbell", "Onion"]
        meat_names = ["Beef Steak", "Angus Beef Steak", "Mackerel", "Raw Lamb Steak", "Egg"]

        self.veg_keys = [k for k in veg_names if k in self.all_ingredients][:5]
        self.meat_keys = [k for k in meat_names if k in self.all_ingredients][:5]

        # Fallback if filenames differ slightly
        if not self.veg_keys or not self.meat_keys:
            all_keys = list(self.all_ingredients.keys())
            half = len(all_keys) // 2
            self.veg_keys = all_keys[:half]
            self.meat_keys = all_keys[half:]

        if self.mode == "meat":
            self.active_keys = self.meat_keys
        elif self.mode == "veg":
            self.active_keys = self.veg_keys
        else:
            self.active_keys = []

        self.collected_status = {k: False for k in self.active_keys}

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

        # Inter-session dialogue support
        def catch_advance():
            if self.dialog.typing:
                self.dialog.advance()
            else:
                self.advance_wave_dialogue()

        def catch_skip():
            self.dialog.close()
            self.in_wave_dialogue = False
            self.dialogue_bg = None
            if hasattr(self, "dialogue_on_finish") and self.dialogue_on_finish:
                cb = self.dialogue_on_finish
                self.dialogue_on_finish = None
                cb()

        self.dialog_ctrl = DialogueController(catch_advance, catch_skip)
        self.in_wave_dialogue = False
        self.dialogue_queue = []
        self.dialogue_bg = None

        self.camera = arcade.camera.Camera2D(
            position=(WIDTH / 2, HEIGHT / 2),
            projection=arcade.LRBT(-WIDTH / 2, WIDTH / 2, -HEIGHT / 2, HEIGHT / 2),
            viewport=self.stage.viewport()
        )
        self.spawn_initial_entities()
        self.relayout()

    def relayout(self):
        super().relayout()
        if hasattr(self, "camera"):
            self.camera.viewport = self.stage.viewport()

    def spawn_initial_entities(self):
        self.items_list.clear()
        self.snatchers_list.clear()
        self.time_left = self.duration

        if self.mode in ("veg", "meat"):
            for name in self.active_keys[:2]:
                spawn_x = get_separated_x(self.items_list)
                self.items_list.append(IngredientDrop(name, self.all_ingredients[name], initial_x=spawn_x))
            for _ in range(3):
                falls, grabs = random.choice(self.snatcher_types)
                spawn_x = get_separated_x(list(self.items_list) + list(self.snatchers_list))
                self.snatchers_list.append(SnatcherSprite(falls, grabs, initial_x=spawn_x))
        else:
            # Defend mode
            for _ in range(6):
                falls, grabs = random.choice(self.snatcher_types)
                spawn_x = get_separated_x(self.snatchers_list)
                self.snatchers_list.append(SnatcherSprite(falls, grabs, initial_x=spawn_x))

    def trigger_wave_dialogue(self, lines, on_finish_callback):
        self.in_wave_dialogue = True
        self.dialogue_queue = list(lines)
        self.dialogue_on_finish = on_finish_callback

        item = self.dialogue_queue.pop(0)
        speaker, text = item[0], item[1]
        img = item[2] if len(item) > 2 else None

        if img and Path(str(img)).exists():
            self.dialogue_bg = arcade.load_texture(str(img))
        else:
            self.dialogue_bg = None

        self.dialog.open(speaker, text)
        self.dialog_ctrl.record(speaker, text)

    def advance_wave_dialogue(self):
        if self.dialogue_queue:
            item = self.dialogue_queue.pop(0)
            speaker, text = item[0], item[1]
            img = item[2] if len(item) > 2 else None

            if img and Path(str(img)).exists():
                self.dialogue_bg = arcade.load_texture(str(img))
            else:
                self.dialogue_bg = None

            self.dialog.open(speaker, text)
            self.dialog_ctrl.record(speaker, text)
        else:
            self.dialog.close()
            self.in_wave_dialogue = False
            self.dialogue_bg = None
            if hasattr(self, "dialogue_on_finish") and self.dialogue_on_finish:
                cb = self.dialogue_on_finish
                self.dialogue_on_finish = None
                cb()

    def show_retry_prompt(self):
        """Shows the Try Again / Give Up modal on defeat or timeout."""
        if self.retry_modal.visible:
            return

        def do_retry():
            self.retry_modal.close()
            # Launch fresh stage of the same minigame
            self.window.show_view(MarketCatchView(self.mode, self.veg_done, self.meat_done))

        def do_give_up():
            self.retry_modal.close()
            # Return to market interior aisle
            from .market_dash_stage import MarketStageView
            self.window.show_view(MarketStageView(veg_done=self.veg_done, meat_done=self.meat_done))

        mode_name = "Fresh Vegetables" if self.mode == "veg" else "Prime Meats" if self.mode == "meat" else "Basket Defense"
        self.retry_modal.open(
            on_retry=do_retry,
            on_give_up=do_give_up,
            title=f"{mode_name.upper()} FAILED!",
            message="Would you like to try again or return to market?"
        )


    def on_update(self, delta_time):
        # Decay red damage flash
        if self.damage_alpha > 0:
            self.damage_alpha = max(0.0, self.damage_alpha - (280.0 * delta_time))

        # Heart breaking sequence
        if self.heart_anim_timer > 0:
            self.heart_anim_timer -= delta_time
            if self.heart_anim_timer <= 0 and self.breaking_idx != -1:
                if self.heart_anim_state == 1:
                    self.hearts[self.breaking_idx].texture = textures.ui_image("Character_HP_Fragmented.png")
                    self.heart_anim_timer = 0.18
                    self.heart_anim_state = 2
                elif self.heart_anim_state == 2:
                    self.hearts[self.breaking_idx].alpha = 0
                    self.heart_anim_state = 0

        if self.pause_menu.visible or self.settings_panel.visible or self.retry_modal.visible:
            return

        if self.in_wave_dialogue:
            if self.dialog.visible:
                self.dialog.update(delta_time)
            self.dialog_ctrl.update(delta_time, is_dialog_visible=self.dialog.visible, is_typing=self.dialog.typing)
            return

        # 1. Timer countdown
        if not self.completed:
            self.time_left -= delta_time
            if self.time_left <= 0:
                self.time_left = 0
                if self.mode in ("veg", "meat") and not all(self.collected_status.values()):
                    self.show_retry_prompt()
                else:
                    self.completed = True
                    self.complete_game_mode()
                return

        # 2. Player Movement & Spinning
        if self.spinning:
            self.spin_timer -= delta_time
            self.spin_angle -= 1440.0 * delta_time
            self.player.angle = self.spin_angle
            if self.spin_timer <= 0:
                self.spinning = False
                self.player.angle = 180
        else:
            self.player.angle = 180

        # Block state tick
        if self.blocking:
            self.block_timer -= delta_time
            self.player.texture = self.terry_tex_action
            if self.block_timer <= 0:
                self.blocking = False
                self.player.texture = self.terry_tex_defend if self.mode == "defend" else self.terry_tex_normal
        else:
            if not self.spinning:
                self.player.texture = self.terry_tex_defend if self.mode == "defend" else self.terry_tex_normal

        # Movement with Shift speed boost
        current_speed = self.boost_speed if self.speed_boosted else self.base_speed
        self.player.center_x += self.player_move_dir * current_speed
        self.player.center_x = max(PLAY_LEFT + 40, min(PLAY_RIGHT - 40, self.player.center_x))

        # 3. Dynamic Hazard & Ingredient Spawning
        self.snatcher_spawn_timer += delta_time
        if self.snatcher_spawn_timer >= 2.2:
            self.snatcher_spawn_timer = 0.0
            max_snatchers = 5 if self.mode in ("veg", "meat") else 8
            if len(self.snatchers_list) < max_snatchers:
                falls, grabs = random.choice(self.snatcher_types)
                all_obstacles = list(self.items_list) + list(self.snatchers_list)
                spawn_x = get_separated_x(all_obstacles)
                self.snatchers_list.append(SnatcherSprite(falls, grabs, initial_x=spawn_x))

        if self.mode in ("veg", "meat"):
            self.ingredient_spawn_timer += delta_time
            if self.ingredient_spawn_timer >= 3.8:
                self.ingredient_spawn_timer = 0.0
                uncollected = [k for k in self.active_keys if not self.collected_status[k]]
                if uncollected and len(self.items_list) < 4:
                    pick_name = random.choice(uncollected)
                    if not any(item.item_name == pick_name for item in self.items_list):
                        spawn_x = get_separated_x(self.items_list)
                        self.items_list.append(IngredientDrop(pick_name, self.all_ingredients[pick_name], initial_x=spawn_x))

        # 4. Ingredients Movement & Collection
        for item in list(self.items_list):
            item.center_y += item.change_y
            if item.top < PLAY_BOTTOM:
                if self.collected_status.get(item.item_name, False):
                    item.remove_from_sprite_lists()
                else:
                    item.reset_pos(existing_list=self.items_list)

            if arcade.check_for_collision(self.player, item):
                audio.play("ingredient_get") # check
                self.collected_status[item.item_name] = True
                item.remove_from_sprite_lists()

                if all(self.collected_status[k] for k in self.active_keys) and not self.completed:
                    self.completed = True
                    self.items_list.clear()
                    self.snatchers_list.clear()
                    self.complete_game_mode()
                    return

        # 5. Snatcher Collisions & Defeat Check (with Blocking)
        for snatcher in list(self.snatchers_list):
            snatcher.update_behavior(delta_time, self.player.center_y, self.player.center_x, is_wave_3=(self.mode == "defend"))

            if snatcher.top < PLAY_BOTTOM or snatcher.bottom > HEIGHT + 200 or snatcher.right < 0 or snatcher.left > WIDTH:
                if snatcher.knocked_out:
                    snatcher.remove_from_sprite_lists()
                else:
                    all_entities = list(self.items_list) + [s for s in self.snatchers_list if s != snatcher]
                    snatcher.reset_pos(existing_list=all_entities)

            if not snatcher.knocked_out:
                # Calculate distance between player and snatcher
                dist_x = abs(self.player.center_x - snatcher.center_x)
                dist_y = abs(self.player.center_y - snatcher.center_y)
                is_colliding = arcade.check_for_collision(self.player, snatcher)

                # Match these thresholds to your expanded shield_radius
                if self.blocking and (is_colliding or (dist_x < 75 and dist_y < 85)):
                    audio.play("block")
                    snatcher.trigger_knockout(self.player.center_x)

                # Spin attack in defend mode
                elif self.spinning and is_colliding:
                    audio.play("ui_click")
                    snatcher.trigger_knockout(self.player.center_x)

                # Unblocked hit
                elif is_colliding and not self.retry_modal.visible:
                    self.take_damage()
                    all_entities = list(self.items_list) + [s for s in self.snatchers_list if s != snatcher]
                    snatcher.reset_pos(existing_list=all_entities)

                    if self.lives <= 0:
                        self.show_retry_prompt()
                        return

    def complete_game_mode(self):
        if self.mode == "veg":
            dialogue = [
                ("Terry", "Phew! All fresh vegetables secured!"),
                ("Terry", "These look crisp and fresh. Mum will be pleased."),
                ("Terry", "Let's head back to the aisle to get the rest of our items."),
            ]
            def to_stage():
                from .market_dash_stage import MarketStageView
                self.window.show_view(MarketStageView(veg_done=True, meat_done=self.meat_done, last_completed="veg"))
            self.trigger_wave_dialogue(dialogue, to_stage)

        elif self.mode == "meat":
            dialogue = [
                ("Terry", "Got the prime meats! Those shoppers were aggressive!"),
                ("Terry", "The steaks and ribs are safely in our basket."),
                ("Terry", "Alright, let's head back out to the main market aisle."),
            ]
            def to_stage():
                from .market_dash_stage import MarketStageView
                self.window.show_view(MarketStageView(veg_done=self.veg_done, meat_done=True, last_completed="meat"))
            self.trigger_wave_dialogue(dialogue, to_stage)

        elif self.mode == "defend":
            dialogue = [
                ("Terry", "I dodged them all! The last of the mob finally gave up chasing!"),
                ("Terry", "My basket survived unscratched! Let's get out of here!"),
            ]
            def to_ending():
                from .market_dash_ending import MarketEndingView
                self.window.show_view(MarketEndingView())
            self.trigger_wave_dialogue(dialogue, to_ending)

    def on_draw(self):
        self.clear()

        # 1. Gameplay & HUD in Camera Space
        self.camera.use()

        if self.in_wave_dialogue and getattr(self, "dialogue_bg", None):
            arcade.draw_texture_rect(self.dialogue_bg, arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT))
        elif self.bg_texture:
            arcade.draw_texture_rect(self.bg_texture, arcade.XYWH(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT))

        if not (self.in_wave_dialogue and getattr(self, "dialogue_bg", None)):
            self.items_list.draw()
            self.snatchers_list.draw()
            self.player_list.draw()

            # Visual shield aura while Terry is actively blocking
            if self.blocking and self.mode in ("veg", "meat"):
                cx, cy = self.player.center_x, self.player.center_y + 10
                shield_radius = 65
                arcade.draw_circle_filled(cx, cy, shield_radius, (160, 230, 255, 60))
                arcade.draw_circle_outline(cx, cy, shield_radius, (130, 220, 255, 220), border_width=3)

            # Progress Bar Plaque
            progress = max(0.0, min(1.0, self.time_left / self.duration))
            panel_w = 460
            panel_h = 58
            panel_x = (WIDTH / 2) - 30
            panel_y = HEIGHT - 38

            arcade.draw_rect_filled(arcade.XYWH(panel_x, panel_y - 2, panel_w, panel_h), (25, 14, 8, 230))
            arcade.draw_rect_filled(arcade.XYWH(panel_x, panel_y, panel_w, panel_h), (85, 48, 24, 255))
            arcade.draw_rect_filled(arcade.XYWH(panel_x, panel_y, panel_w - 6, panel_h - 6), (138, 88, 48, 255))
            arcade.draw_rect_outline(arcade.XYWH(panel_x, panel_y, panel_w, panel_h), (42, 22, 10), 2)

            banner_title = "PRIME STEAKS" if self.mode == "meat" else "VEGETABLE HARVEST" if self.mode == "veg" else "DEFEND BASKET!"
            arcade.draw_text(banner_title, panel_x, panel_y + 13, (255, 238, 185), 12, bold=True, anchor_x="center", anchor_y="center")

            bar_w = 420
            bar_h = 16
            bar_y = panel_y - 12
            arcade.draw_rect_filled(arcade.XYWH(panel_x, bar_y, bar_w, bar_h), (24, 20, 18, 250))
            arcade.draw_rect_outline(arcade.XYWH(panel_x, bar_y, bar_w, bar_h), (50, 42, 36), 2)

            fill_w = max(4.0, bar_w * progress)
            fill_center_x = (panel_x - bar_w / 2) + fill_w / 2
            c_main = (235, 75, 75) if self.mode == "defend" else (225, 175, 55)
            c_hi = (255, 130, 130) if self.mode == "defend" else (255, 225, 120)
            arcade.draw_rect_filled(arcade.XYWH(fill_center_x, bar_y, fill_w, bar_h - 2), c_main)
            arcade.draw_rect_filled(arcade.XYWH(fill_center_x, bar_y + 4, fill_w, 3), c_hi)

            seconds_left = max(0, int(self.time_left))
            arcade.draw_text(f"{seconds_left:02d}s", panel_x + (bar_w / 2) - 24, panel_y + 13, (255, 215, 110), 11, bold=True, anchor_x="center", anchor_y="center")

            # --- Wooden HP Plaque & Heart Sprites ---
            hp_w = 146
            hp_h = 42
            hp_x = PLAY_LEFT + 66
            hp_y = HEIGHT - 32
            arcade.draw_rect_filled(arcade.XYWH(hp_x, hp_y, hp_w, hp_h), (85, 48, 24, 220))
            arcade.draw_rect_filled(arcade.XYWH(hp_x, hp_y, hp_w - 4, hp_h - 4), (138, 88, 48, 240))
            arcade.draw_rect_outline(arcade.XYWH(hp_x, hp_y, hp_w, hp_h), (42, 22, 10), 2)
            self.hearts.draw()

            # --- Shopping Checklist Board on the Right ---
            if self.mode in ("veg", "meat"):
                board_w = 255
                board_h = 44 + (len(self.active_keys) * 30)
                board_x = PLAY_RIGHT - (board_w / 2) - 8
                board_y = HEIGHT - (board_h / 2) - 15

                arcade.draw_rect_filled(arcade.XYWH(board_x, board_y, board_w, board_h), (85, 48, 24, 240))
                arcade.draw_rect_filled(arcade.XYWH(board_x, board_y, board_w - 8, board_h - 8), (138, 88, 48, 245))
                arcade.draw_rect_outline(arcade.XYWH(board_x, board_y, board_w, board_h), (50, 28, 14), 3)
                arcade.draw_text("SHOPPING LIST:", board_x - (board_w / 2) + 14, board_y + (board_h / 2) - 22, (255, 240, 195), 13, bold=True)

                draw_y = board_y + (board_h / 2) - 50
                for name in self.active_keys:
                    collected = self.collected_status.get(name, False)
                    tex = self.all_ingredients.get(name)
                    if tex:
                        icon_col = (255, 255, 255, 255) if collected else (95, 90, 85, 140)
                        arcade.draw_texture_rect(tex, arcade.XYWH(board_x - (board_w / 2) + 26, draw_y, 24, 24), color=arcade.types.Color(*icon_col))
                    txt_col = (130, 255, 150) if collected else (210, 190, 170)
                    sym = "✔" if collected else "○"
                    arcade.draw_text(f"{sym} {name}", board_x - (board_w / 2) + 48, draw_y - 7, txt_col, 13, bold=True)
                    draw_y -= 30

            # --- Bottom Key Hints ---
            if self.mode in ("veg", "meat"):
                arcade.draw_text(
                    "Left Click: Block   |   Hold Shift: Speed Boost",
                    WIDTH / 2 - 40, 25, (255, 235, 175), 13, anchor_x="center", bold=True
                )
            elif self.mode == "defend":
                arcade.draw_text(
                    "Left Click: Spin & Defend   |   Hold Shift: Speed Boost",
                    WIDTH / 2 - 40, 25, (255, 230, 140), 13, anchor_x="center", bold=True
                )

        # 2. Screen-Space Overlays & UI
        self.window.default_camera.use()

        # Red damage flash
        if self.damage_alpha > 0:
            flash_rect = arcade.XYWH(self.window.width / 2, self.window.height / 2, self.window.width, self.window.height)
            arcade.draw_rect_filled(flash_rect, (255, 30, 30, int(self.damage_alpha)))

        # Dialogue
        if self.in_wave_dialogue and self.dialog.visible:
            self.dialog.draw()

        # Pause and settings
        if not self.settings_panel.visible:
            self.pause_menu.draw()
        self.settings_panel.draw()

        # DRAW RETRY MODAL HERE (ON THE DEFAULT CAMERA)
        self.retry_modal.draw()

    def on_key_press(self, key, modifiers):
        if self.retry_modal.visible:
            return

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

        # Shift speed boost
        if key in (arcade.key.LSHIFT, arcade.key.RSHIFT):
            self.speed_boosted = True

        self.held.add(key)
        self.update_movement()

    def on_key_release(self, key, modifiers):
        if key in (arcade.key.LSHIFT, arcade.key.RSHIFT):
            self.speed_boosted = False

        self.held.discard(key)
        self.update_movement()

    def update_movement(self):
        dx = (arcade.key.D in self.held or arcade.key.RIGHT in self.held) - \
             (arcade.key.A in self.held or arcade.key.LEFT in self.held)
        self.player_move_dir = dx

    def on_mouse_press(self, x, y, button, modifiers):
        canvas_x, canvas_y = self.canvas_point(x, y)

        # 1. Handle RetryModal click
        if self.retry_modal.visible:
            self.retry_modal.handle_mouse_press(canvas_x, canvas_y)
            return

        # 2. Settings & Pause
        if self.settings_panel.on_mouse_press(canvas_x, canvas_y, button):
            return

        if self.pause_menu.visible:
            action = self.pause_menu.on_mouse_press(canvas_x, canvas_y, button)
            self.run_action(action)
            return

        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.mode == "defend" and not self.spinning:
                audio.play("swing_sword")
                self.spinning = True
                self.spin_timer = 0.35
            elif self.mode in ("veg", "meat") and not self.blocking:
                audio.play("block")
                self.blocking = True
                self.block_timer = self.block_duration


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

    def take_damage(self):
        if self.lives <= 0:
            return
        audio.play("get_snatched")
        self.lives -= 1
        self.damage_alpha = 140.0

        # Target the lost heart
        self.breaking_idx = self.lives
        if 0 <= self.breaking_idx < self.max_lives:
            self.hearts[self.breaking_idx].texture = textures.ui_image("Character_HP_broke_into_half.png")
            self.heart_anim_timer = 0.18
            self.heart_anim_state = 1