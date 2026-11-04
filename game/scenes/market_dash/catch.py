from pathlib import Path
import math
import random
import time
import arcade

from .prep_sprites import run_prep
from ...core import textures
from ...core import audio
from ...config import HEIGHT, WIDTH
from ...core.dialogue import DialogBox
from ...core.options import SettingsPanel
from ...core.pause import PauseMenu
from ..menu.view import MenuView
from ...core.stage import StageView
from .common import (
    ASSETS_DIR, TERRY_GAME_DIR, SNATCHERS_BASE_DIR,
    INGREDIENTS_BASE_DIR, cover_rect,
    PLAY_LEFT, PLAY_RIGHT, PLAY_BOTTOM, PLAY_TOP,
    SHELF_LEFT_X, SHELF_RIGHT_X, SHELF_Y_LEVELS, SHELF_SLOTS,
    SHELF_SLOT_WEIGHTS, pick_weighted_shelf_slot,
    AISLE_MIN_X, AISLE_MAX_X, AISLE_MIN_Y, AISLE_MAX_Y,
    CHECKOUT_MIN_X, CHECKOUT_MAX_X, CHECKOUT_MIN_Y,
    DialogueController, RetryModal, InstructionModal
)
from .sprites import (
    SnatcherSprite, DroppedIngredient, IngredientDrop,
    STATE_WANDERING, STATE_RUSHING_SHELF, STATE_FLEEING_WITH_ITEM, STATE_STUNNED
)


class MarketCatchView(StageView):
    """Top-down Wall-Shelf Restock & Crowd Rush Scramble minigame."""

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
        self.instruction_modal = InstructionModal()
        self.instruction_modal.open(mode=self.mode)
        self.widgets = [self.dialog, self.pause_menu, self.settings_panel]

        # Duration: 60s for gathering, 50s for defend checkout escape
        self.duration = 50.0 if self.mode == "defend" else 60.0
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

        # Shelf restock cycle timers & active slot
        self.active_restock = None  # Dict of restock state when an ingredient is on shelf
        self.restock_interval = 4.5 if self.mode == "veg" else 3.8 # next ingredients spawn time interval
        self.restock_timer = 1.2    # Initial delay before first restock
        self.shopper_rush_speed = 4.6 if self.mode == "veg" else 4.6 # shoppers rush speed

        # Terry Action Mechanics (Defend mode Spin Attack / Gathering Block)
        self.swinging = False
        self.swing_timer = 0.0
        self.swing_duration = 0.30
        self.spin_cooldown = 0.0
        self.exit_warn_timer = 0.0

        # Terry Block & Speed Boost Mechanics
        self.blocking = False
        self.block_timer = 0.0
        self.block_duration = 0.45
        self.block_cooldown = 0.0
        self.base_speed = 8.5 if self.mode == "defend" else 7.5
        self.boost_speed = 13.0
        self.speed_boosted = False
        self.invuln_timer = 0.0
        self.touching_crowd_timer = 0.0

        # Visual juice & floating popups
        self.floating_popups = []
        self.shake_timer = 0.0
        self.shake_intensity = 0.0

        # Load Terry Sprites
        tex_without_fish = arcade.load_texture(str(TERRY_GAME_DIR / "sprite without fish.png"))
        tex_holding_fish = arcade.load_texture(str(TERRY_GAME_DIR / "sprite holding fish.png"))
        tex_defending    = arcade.load_texture(str(TERRY_GAME_DIR / "sprite defending.png"))

        self.terry_tex_normal = tex_without_fish
        self.terry_tex_defend = tex_holding_fish
        self.terry_tex_action = tex_defending

        active_tex = self.terry_tex_defend if self.mode == "defend" else self.terry_tex_normal
        self.player_scale = 0.15
        self.player = arcade.Sprite(active_tex, scale=self.player_scale)
        self.player.angle = 180  
        if self.mode == "defend":
            self.player.center_x = 640
            self.player.center_y = 95
        else:
            self.player.center_x = (AISLE_MIN_X + AISLE_MAX_X) / 2
            self.player.center_y = (AISLE_MIN_Y + AISLE_MAX_Y) / 2
        self.player_move_x = 0
        self.player_move_y = 0
        self.player_list = arcade.SpriteList()
        self.player_list.append(self.player)

        # Load Ingredients
        self.all_ingredients = {}
        for f in sorted(list(INGREDIENTS_BASE_DIR.glob("*.png"))):
            name = f.stem.replace("_", " ").title()
            self.all_ingredients[name] = arcade.load_texture(str(f))

        veg_names = ["Cabbage", "Carrot", "Eggplant", "Green Pepperbell", "Red Onion"]
        meat_names = ["Beef Steak", "Angus Beef Steak", "Mackerel", "Raw Lamb Steak", "Egg"]

        self.veg_keys = [k for k in veg_names if k in self.all_ingredients][:5]
        self.meat_keys = [k for k in meat_names if k in self.all_ingredients][:5]

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

        # Defend Mode Basket Setup (Terry starts with 5 gathered items)
        if self.mode == "defend":
            self.basket_keys = list(self.meat_keys[:3] + self.veg_keys[:2])[:5]
            self.basket_items = list(self.basket_keys)
        else:
            self.basket_keys = []
            self.basket_items = []

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

        self.snatchers_list = arcade.SpriteList()
        self.dropped_items = arcade.SpriteList()
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
        self.snatchers_list.clear()
        self.dropped_items.clear()
        self.active_restock = None
        self.upcoming_restock = None
        self.time_left = self.duration
        self.restock_timer = 4.0 
        self.phase_spawn_timer = 8.0 # spawn new shoppers
        self.max_shoppers = 15 # maximum shoppers on screen at once
        self.invuln_timer = 0.0
        self.touching_crowd_timer = 0.0

        if self.mode == "defend":
            self.basket_items = list(self.basket_keys)
            self.player.center_x = 640
            self.player.center_y = 95
            self.swinging = False
            self.swing_timer = 0.0
            self.exit_warn_timer = 0.0

        if self.mode in ("veg", "meat"):
            count = 8 #Intitial shoppers for gathering game
        else:
            count = 10 # Intitial shoppers for defend game

        if self.mode == "veg":
            self.shopper_rush_speed = 4.6 # veg shoppers rush speed
        elif self.mode == "meat":
            self.shopper_rush_speed = 4.6 # meat shoppers rush speed
        else:
            self.shopper_rush_speed = 4.5

        for _ in range(count):
            falls, grabs = random.choice(self.snatcher_types)
            shopper = SnatcherSprite(
                falls,
                grabs,
                rush_speed=self.shopper_rush_speed,
                player_pos=(self.player.center_x, self.player.center_y),
                min_dist=200
            )
            self.snatchers_list.append(shopper)

    def trigger_mackerel_swing(self):
        """Spins 180 degrees clockwise to stun and knock back shoppers in Defend mode."""
        if self.swinging or self.spin_cooldown > 0:
            return False
        audio.play("swing_sword")
        self.swinging = True
        self.swing_duration = 0.30
        self.swing_timer = self.swing_duration
        self.spin_cooldown = 0.45
        self.shake_timer = 0.15
        self.shake_intensity = 4.0

        swing_radius = 85.0

        for shopper in self.snatchers_list:
            dist = math.hypot(shopper.center_x - self.player.center_x, shopper.center_y - self.player.center_y)
            if dist <= swing_radius:
                dropped = shopper.trigger_stun(self.player.center_x, self.player.center_y, is_defending=True)
                # Knockback 110px away from Terry
                angle = math.atan2(shopper.center_y - self.player.center_y, shopper.center_x - self.player.center_x)
                shopper.center_x += math.cos(angle) * 110.0
                shopper.center_y += math.sin(angle) * 110.0
                shopper.center_x = max(AISLE_MIN_X - 10, min(AISLE_MAX_X + 10, shopper.center_x))
                shopper.center_y = max(AISLE_MIN_Y - 10, min(AISLE_MAX_Y + 10, shopper.center_y))

                self.floating_popups.append({
                    "text": "SMACK!",
                    "x": shopper.center_x,
                    "y": shopper.center_y + 40,
                    "timer": 0.45,
                    "max_timer": 0.45,
                    "color": (255, 230, 120)
                })

                if dropped:
                    drop_name, drop_tex = dropped
                    floor_item = DroppedIngredient(drop_name, drop_tex, shopper.center_x, shopper.center_y, persists_indefinitely=True)
                    self.dropped_items.append(floor_item)
                    self.floating_popups.append({
                        "text": f"RECOVERED: {drop_name}!",
                        "x": shopper.center_x,
                        "y": shopper.center_y + 60,
                        "timer": 0.75,
                        "max_timer": 0.75,
                        "color": (120, 255, 140)
                    })
        return True

    def trigger_block_or_spin(self):
        """Triggers Terry's block in gathering modes or mackerel swing in defend mode."""
        if self.mode == "defend":
            return self.trigger_mackerel_swing()
        elif self.mode in ("veg", "meat") and not self.blocking and self.block_cooldown <= 0:
            audio.play("block")
            self.blocking = True
            self.block_timer = self.block_duration
            self.block_cooldown = self.block_duration + 0.15 
            return True
        return False

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

    def show_retry_prompt(self, reason=None):
        """Shows the Try Again / Give Up modal on defeat or timeout."""
        if self.retry_modal.visible:
            return

        self.shake_timer = 0.0
        self.camera.position = (WIDTH / 2, HEIGHT / 2)
        audio.play("game_failed")

        def do_retry():
            self.retry_modal.close()
            self.window.show_view(MarketCatchView(self.mode, self.veg_done, self.meat_done))

        def do_give_up():
            self.retry_modal.close()
            from .stage import MarketStageView
            self.window.show_view(MarketStageView(veg_done=self.veg_done, meat_done=self.meat_done))

        mode_name = "Fresh Vegetables" if self.mode == "veg" else "Prime Meats" if self.mode == "meat" else "Basket Defense"
        if reason is None:
            if self.lives <= 0:
                reason = "Terry was overwhelmed by shoppers."
            else:
                reason = "You failed to gather all the ingredients."

        self.retry_modal.open(
            on_retry=do_retry,
            on_give_up=do_give_up,
            title=f"{mode_name.upper()} FAILED!",
            message=f"{reason}\nWould you like to try again or return to market?"
        )

    def try_grab_shelf(self):
        """Grabs the item from the active shelf slot (gathering) or picks up nearest floor item (defend)."""
        if self.mode == "defend":
            for item in list(self.dropped_items):
                d = math.hypot(self.player.center_x - item.center_x, self.player.center_y - item.center_y)
                if d <= 70:
                    audio.play("ingredient_get")
                    self.basket_items.append(item.item_name)
                    self.floating_popups.append({
                        "text": f"+ {item.item_name} SECURED!",
                        "x": self.player.center_x,
                        "y": self.player.center_y + 65,
                        "timer": 0.85,
                        "max_timer": 0.85,
                        "color": (120, 255, 140)
                    })
                    item.remove_from_sprite_lists()
                    return True
            return False

        if not self.active_restock:
            return False

        slot_x = self.active_restock["x"]
        slot_y = self.active_restock["y"]
        dist = math.hypot(self.player.center_x - slot_x, self.player.center_y - slot_y)

        if dist <= 140:
            item_name = self.active_restock["item_name"]
            self.collected_status[item_name] = True
            audio.play("ingredient_get")
            self.floating_popups.append({
                "text": f"+ {item_name}",
                "x": self.player.center_x,
                "y": self.player.center_y + 65,
                "timer": 0.85,
                "max_timer": 0.85,
                "color": (120, 255, 140)
            })

            # Clear active slot and cancel rushing shoppers
            self.active_restock = None
            self.upcoming_restock = None
            self.restock_timer = self.restock_interval
            for shopper in self.snatchers_list:
                shopper.cancel_rush()

            if all(self.collected_status.values()) and not self.completed:
                self.completed = True
                self.complete_game_mode()
            return True
        return False

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

        if self.instruction_modal.visible or self.pause_menu.visible or self.settings_panel.visible or self.retry_modal.visible:
            return

        if self.in_wave_dialogue:
            if self.dialog.visible:
                self.dialog.update(delta_time)
            self.dialog_ctrl.update(delta_time, is_dialog_visible=self.dialog.visible, is_typing=self.dialog.typing)
            return

        # Cooldown decays
        if self.block_cooldown > 0:
            self.block_cooldown = max(0.0, self.block_cooldown - delta_time)
        if self.spin_cooldown > 0:
            self.spin_cooldown = max(0.0, self.spin_cooldown - delta_time)
        if self.invuln_timer > 0:
            self.invuln_timer = max(0.0, self.invuln_timer - delta_time)
            self.player.alpha = 130 if int(self.invuln_timer * 14) % 2 == 0 else 255
        else:
            self.player.alpha = 255
        if self.touching_crowd_timer > 0:
            self.touching_crowd_timer = max(0.0, self.touching_crowd_timer - delta_time)

        # Screenshake update
        if self.shake_timer > 0:
            self.shake_timer -= delta_time
            offset_x = (random.random() * 2 - 1) * self.shake_intensity
            offset_y = (random.random() * 2 - 1) * self.shake_intensity
            self.camera.position = (WIDTH / 2 + offset_x, HEIGHT / 2 + offset_y)
        else:
            self.camera.position = (WIDTH / 2, HEIGHT / 2)

        # Floating popups update
        for popup in list(self.floating_popups):
            popup["timer"] -= delta_time
            popup["y"] += 35.0 * delta_time
            if popup["timer"] <= 0:
                self.floating_popups.remove(popup)

        # 1. Timer countdown
        if not self.completed:
            self.time_left -= delta_time
            if self.time_left <= 0:
                self.time_left = 0
                if self.mode in ("veg", "meat") and not all(self.collected_status.values()):
                    self.show_retry_prompt("Time's up! Ingredients were not gathered in time.")
                elif self.mode == "defend":
                    self.show_retry_prompt("Time's up! Terry couldn't reach the checkout doors in time.")
                else:
                    self.completed = True
                    self.complete_game_mode()
                return

        # Exit warning timer decay
        if self.exit_warn_timer > 0:
            self.exit_warn_timer = max(0.0, self.exit_warn_timer - delta_time)

        # Defend Mode Victory Trigger: Reaching checkout doors at top
        if self.mode == "defend" and not self.completed:
            if CHECKOUT_MIN_X <= self.player.center_x <= CHECKOUT_MAX_X and self.player.center_y >= 620:
                if len(self.dropped_items) > 0:
                    if self.exit_warn_timer <= 0:
                        self.exit_warn_timer = 1.4
                        audio.play("hp_reduced")
                        self.floating_popups.append({
                            "text": "DON'T LEAVE YOUR FOOD BEHIND!",
                            "x": self.player.center_x,
                            "y": self.player.center_y + 65,
                            "timer": 1.2,
                            "max_timer": 1.2,
                            "color": (255, 120, 60)
                        })
                elif len(self.basket_items) >= 1:
                    self.completed = True
                    self.complete_game_mode()
                    return

        # 2. Player Movement & Actions
        if self.swinging:
            self.swing_timer -= delta_time
            self.player.texture = self.terry_tex_action
            # 180 degree clockwise spin during attack
            progress = max(0.0, min(1.0, 1.0 - (self.swing_timer / self.swing_duration)))
            self.player.angle = 180.0 - (progress * 180.0)
            if self.swing_timer <= 0:
                self.swinging = False
                self.player.angle = 180.0
                self.player.texture = self.terry_tex_defend if self.mode == "defend" else self.terry_tex_normal
        elif self.blocking:
            self.block_timer -= delta_time
            self.player.texture = self.terry_tex_action
            self.player.angle = 180.0
            if self.block_timer <= 0:
                self.blocking = False
                self.player.texture = self.terry_tex_defend if self.mode == "defend" else self.terry_tex_normal
        else:
            self.player.angle = 180.0
            self.player.texture = self.terry_tex_defend if self.mode == "defend" else self.terry_tex_normal

        # 2D Top-Down Movement with diagonal normalization, Shift speed boost, and crowd slowdown
        step = delta_time * 60.0
        if self.touching_crowd_timer > 0:
            crowd_slow = 0.40  # Heavy slowdown when touching/ramming shoppers
            current_speed = self.base_speed * crowd_slow  # Break sprint boost and slow Terry down
        else:
            current_speed = self.boost_speed if self.speed_boosted else self.base_speed
        norm = 0.7071 if (self.player_move_x != 0 and self.player_move_y != 0) else 1.0

        self.player.center_x += self.player_move_x * current_speed * norm * step
        self.player.center_y += self.player_move_y * current_speed * norm * step

        # Constrain within checkered aisle bounds
        self.player.center_x = max(AISLE_MIN_X, min(AISLE_MAX_X, self.player.center_x))
        self.player.center_y = max(AISLE_MIN_Y, min(AISLE_MAX_Y, self.player.center_y))

        # Horizontal facing orientation
        if self.player_move_x < 0:
            self.player.scale_x = -abs(self.player_scale)
        elif self.player_move_x > 0:
            self.player.scale_x = abs(self.player_scale)

        # Shopper wave increase by duration phase (Veg & Meat Modes)
        # Initial 3 shoppers, increasing by 1 or 2 every 10 seconds up to max 8 shoppers
        if self.mode in ("veg", "meat") and not self.completed:
            self.phase_spawn_timer -= delta_time
            if self.phase_spawn_timer <= 0:
                self.phase_spawn_timer = 6.0
                if len(self.snatchers_list) < self.max_shoppers:
                    needed = min(random.randint(1, 2), self.max_shoppers - len(self.snatchers_list))
                    for _ in range(needed):
                        falls, grabs = random.choice(self.snatcher_types)
                        new_shopper = SnatcherSprite(
                            falls,
                            grabs,
                            rush_speed=self.shopper_rush_speed,
                            player_pos=(self.player.center_x, self.player.center_y),
                            min_dist=200
                        )
                        self.snatchers_list.append(new_shopper)

        # 3. Shelf Restock Cycle (Veg & Meat Modes)
        if self.mode in ("veg", "meat") and not self.completed:
            # Active shelf slot timer update
            if self.active_restock is not None:
                self.active_restock["anim_timer"] += delta_time
                self.active_restock["timer"] -= delta_time
                if self.active_restock["timer"] <= 0:
                    # Urgency expired - shoppers cleared the shelf
                    self.active_restock = None
                    self.upcoming_restock = None
                    self.restock_timer = self.restock_interval
                    for shopper in self.snatchers_list:
                        shopper.cancel_rush()
            else:
                # Countdown to next restock
                uncollected = [k for k in self.active_keys if not self.collected_status[k]]
                floor_names = [d.item_name for d in self.dropped_items]
                carried_names = [s.carried_item for s in self.snatchers_list if s.carried_item]
                candidates = [k for k in uncollected if k not in floor_names and k not in carried_names]
                if not candidates:
                    candidates = uncollected

                if candidates:
                    self.restock_timer -= delta_time

                    # 3 seconds before restock: determine upcoming shelf slot & item for hint
                    if self.restock_timer <= 1.0: # restock hint seconds
                        if self.upcoming_restock is None:
                            pick_name = random.choice(candidates)
                            slot_x, slot_y = pick_weighted_shelf_slot()
                            self.upcoming_restock = {
                                "x": slot_x,
                                "y": slot_y,
                                "side": "left" if slot_x == SHELF_LEFT_X else "right",
                                "item_name": pick_name,
                                "texture": self.all_ingredients[pick_name],
                            }

                    if self.restock_timer <= 0:
                        if self.upcoming_restock is not None:
                            slot_x = self.upcoming_restock["x"]
                            slot_y = self.upcoming_restock["y"]
                            side = self.upcoming_restock["side"]
                            pick_name = self.upcoming_restock["item_name"]
                            item_tex = self.upcoming_restock["texture"]
                            self.upcoming_restock = None
                        else:
                            pick_name = random.choice(candidates)
                            slot_x, slot_y = pick_weighted_shelf_slot()
                            side = "left" if slot_x == SHELF_LEFT_X else "right"
                            item_tex = self.all_ingredients[pick_name]

                        self.active_restock = {
                            "x": slot_x,
                            "y": slot_y,
                            "side": side,
                            "item_name": pick_name,
                            "texture": item_tex,
                            "timer": 6.0,
                            "max_timer": 6.0,
                            "anim_timer": 0.0,
                        }

                        # Trigger shoppers on that side to rush the shelf with reaction delay
                        for shopper in self.snatchers_list:
                            delay = random.uniform(0.1, 0.3) # reactive delay before rushing to shelf
                            if slot_x < 640 and shopper.center_x < 640:
                                shopper.trigger_rush(slot_x, slot_y, pick_name, item_tex, delay=delay)
                            elif slot_x >= 640 and shopper.center_x >= 640:
                                shopper.trigger_rush(slot_x, slot_y, pick_name, item_tex, delay=delay)

        # 4. Floor Dropped Pickups Update
        for item in list(self.dropped_items):
            expired = item.update_timer(delta_time)
            if expired:
                item.remove_from_sprite_lists()
            else:
                dist_item = math.hypot(self.player.center_x - item.center_x, self.player.center_y - item.center_y)
                if arcade.check_for_collision(self.player, item) or dist_item < 55:
                    audio.play("ingredient_get")
                    if self.mode == "defend":
                        self.basket_items.append(item.item_name)
                        self.floating_popups.append({
                            "text": f"+ {item.item_name} SECURED!",
                            "x": self.player.center_x,
                            "y": self.player.center_y + 65,
                            "timer": 0.85,
                            "max_timer": 0.85,
                            "color": (120, 255, 140)
                        })
                    else:
                        self.collected_status[item.item_name] = True
                        self.floating_popups.append({
                            "text": f"+ {item.item_name}",
                            "x": self.player.center_x,
                            "y": self.player.center_y + 65,
                            "timer": 0.85,
                            "max_timer": 0.85,
                            "color": (120, 255, 140)
                        })
                    item.remove_from_sprite_lists()
                    if self.mode in ("veg", "meat") and all(self.collected_status.values()) and not self.completed:
                        self.completed = True
                        self.complete_game_mode()
                        return

        # 5. Shopper Behavior, Shelf Claim, and Collisions
        for shopper in list(self.snatchers_list):
            shopper.update_behavior(delta_time, self.player.center_y, self.player.center_x, dropped_items=self.dropped_items)

            # Check if shopper successfully fled off screen with a stolen ingredient
            if shopper.has_fled_with_item:
                lost_item = shopper.carried_item or "Ingredient"
                if self.mode == "defend":
                    self.take_damage(ignore_invuln=True)
                    self.floating_popups.append({
                        "text": f"PERMANENTLY LOST: {lost_item}!",
                        "x": self.player.center_x,
                        "y": self.player.center_y + 65,
                        "timer": 1.0,
                        "max_timer": 1.0,
                        "color": (255, 60, 60)
                    })
                    shopper.reset_pos(
                        rush_speed=self.shopper_rush_speed,
                        player_pos=(self.player.center_x, self.player.center_y),
                        min_dist=200
                    )
                    # Check if all 5 items permanently stolen
                    if len(self.basket_items) == 0 and len(self.dropped_items) == 0 and not any(s.carried_item for s in self.snatchers_list):
                        self.show_retry_prompt("All 5 ingredients were stolen! Your basket is empty.")
                        return
                    if self.lives <= 0:
                        return
                else:
                    # In Veg & Meat modes: Reduce 1 HP when shopper flees outside the scene with an ingredient (no time reduction)
                    self.take_damage(ignore_invuln=True)
                    self.floating_popups.append({
                        "text": f"-1 HP! {lost_item} LOST!",
                        "x": self.player.center_x,
                        "y": self.player.center_y + 65,
                        "timer": 1.0,
                        "max_timer": 1.0,
                        "color": (255, 60, 60)
                    })
                    shopper.reset_pos(
                        rush_speed=self.shopper_rush_speed,
                        player_pos=(self.player.center_x, self.player.center_y),
                        min_dist=200
                    )
                    if self.lives <= 0:
                        return

            # Check if rushing shopper reached the active shelf slot before Terry
            if self.active_restock and shopper.state == STATE_RUSHING_SHELF:
                dist_shelf = math.hypot(shopper.center_x - self.active_restock["x"], shopper.center_y - self.active_restock["y"])
                if dist_shelf < 125:
                    claimed_name = self.active_restock["item_name"]
                    claimed_tex = self.active_restock["texture"]
                    shopper.claim_item(claimed_name, claimed_tex)

                    self.floating_popups.append({
                        "text": f"STOLEN: {claimed_name}!",
                        "x": shopper.center_x,
                        "y": shopper.center_y + 45,
                        "timer": 0.75,
                        "max_timer": 0.75,
                        "color": (255, 140, 60)
                    })

                    self.active_restock = None
                    self.upcoming_restock = None
                    self.restock_timer = self.restock_interval
                    for other in self.snatchers_list:
                        other.cancel_rush()

            # Terry & Shopper Collisions
            dist_x = abs(self.player.center_x - shopper.center_x)
            dist_y = abs(self.player.center_y - shopper.center_y)
            dist_total = math.hypot(dist_x, dist_y)
            is_colliding = arcade.check_for_collision(self.player, shopper) or (dist_total < 55)

            if shopper.state != STATE_STUNNED:
                # Terry Block / Parry (no screen shake when blocking)
                if self.blocking and self.mode in ("veg", "meat") and (is_colliding or dist_total < 80):
                    audio.play("block")
                    dropped = shopper.trigger_stun(self.player.center_x, self.player.center_y)
                    self.floating_popups.append({
                        "text": "DEFLECTED!",
                        "x": self.player.center_x,
                        "y": self.player.center_y + 65,
                        "timer": 0.5,
                        "max_timer": 0.5,
                        "color": (160, 230, 255)
                    })

                    if dropped:
                        drop_name, drop_tex = dropped
                        floor_item = DroppedIngredient(drop_name, drop_tex, shopper.center_x, shopper.center_y)
                        self.dropped_items.append(floor_item)
                        self.floating_popups.append({
                            "text": f"DROPPED: {drop_name}!",
                            "x": shopper.center_x,
                            "y": shopper.center_y + 40,
                            "timer": 0.75,
                            "max_timer": 0.75,
                            "color": (120, 255, 140)
                        })

                # Mackerel Swing active hit in Defend mode
                elif self.swinging and self.mode == "defend" and is_colliding:
                    dropped = shopper.trigger_stun(self.player.center_x, self.player.center_y, is_defending=True)
                    self.floating_popups.append({
                        "text": "SMACK!",
                        "x": shopper.center_x,
                        "y": shopper.center_y + 40,
                        "timer": 0.45,
                        "max_timer": 0.45,
                        "color": (255, 230, 120)
                    })
                    if dropped:
                        drop_name, drop_tex = dropped
                        floor_item = DroppedIngredient(drop_name, drop_tex, shopper.center_x, shopper.center_y, persists_indefinitely=True)
                        self.dropped_items.append(floor_item)

                # Unblocked Collision
                elif is_colliding:
                    # Character speed is reduced when touching or ramming into shoppers
                    self.touching_crowd_timer = 0.4

                    # Shaking effect triggers when touching or ramming into shopper
                    self.shake_timer = 0.2
                    self.shake_intensity = 5.0

                    if self.mode == "defend" and shopper.ram_cooldown <= 0:
                        shopper.ram_cooldown = 1.0
                        # Stumble backward slightly with 0.8s invulnerability
                        push_angle = math.atan2(self.player.center_y - shopper.center_y, self.player.center_x - shopper.center_x)
                        self.player.center_x += math.cos(push_angle) * 25.0
                        self.player.center_y += math.sin(push_angle) * 25.0
                        self.player.center_x = max(AISLE_MIN_X, min(AISLE_MAX_X, self.player.center_x))
                        self.player.center_y = max(AISLE_MIN_Y, min(AISLE_MAX_Y, self.player.center_y))
                        self.invuln_timer = 0.8

                        if self.basket_items:
                            # Spill 1 item from basket onto the floor - drop far away
                            spilled_idx = random.randrange(len(self.basket_items))
                            spilled_item = self.basket_items.pop(spilled_idx)

                            scatter_x, scatter_y = self.player.center_x, self.player.center_y
                            for _ in range(12):
                                drop_angle = random.uniform(0, 2 * math.pi)
                                drop_dist = random.uniform(160.0, 240.0)
                                cand_x = self.player.center_x + math.cos(drop_angle) * drop_dist
                                cand_y = self.player.center_y + math.sin(drop_angle) * drop_dist
                                cand_x = max(AISLE_MIN_X + 25, min(AISLE_MAX_X - 25, cand_x))
                                cand_y = max(AISLE_MIN_Y + 25, min(AISLE_MAX_Y - 25, cand_y))
                                if math.hypot(cand_x - self.player.center_x, cand_y - self.player.center_y) >= 120.0:
                                    scatter_x, scatter_y = cand_x, cand_y
                                    break
                            else:
                                center_aisle_x = (AISLE_MIN_X + AISLE_MAX_X) / 2
                                center_aisle_y = (AISLE_MIN_Y + AISLE_MAX_Y) / 2
                                to_center_angle = math.atan2(center_aisle_y - self.player.center_y, center_aisle_x - self.player.center_x)
                                scatter_x = self.player.center_x + math.cos(to_center_angle) * 180.0
                                scatter_y = self.player.center_y + math.sin(to_center_angle) * 180.0
                                scatter_x = max(AISLE_MIN_X + 25, min(AISLE_MAX_X - 25, scatter_x))
                                scatter_y = max(AISLE_MIN_Y + 25, min(AISLE_MAX_Y - 25, scatter_y))

                            spilled_tex = self.all_ingredients.get(spilled_item)
                            floor_item = DroppedIngredient(spilled_item, spilled_tex, scatter_x, scatter_y, persists_indefinitely=True)
                            self.dropped_items.append(floor_item)

                            audio.play("get_snatched")
                            self.floating_popups.append({
                                "text": f"-1 {spilled_item} DROPPED!",
                                "x": self.player.center_x,
                                "y": self.player.center_y + 65,
                                "timer": 0.8,
                                "max_timer": 0.8,
                                "color": (255, 70, 70)
                            })
                        else:
                            # Basket is empty, Terry takes damage!
                            self.take_damage()
                            self.floating_popups.append({
                                "text": "OUCH!",
                                "x": self.player.center_x,
                                "y": self.player.center_y + 65,
                                "timer": 0.6,
                                "max_timer": 0.6,
                                "color": (255, 70, 70)
                            })
                            if self.lives <= 0:
                                return

                    elif self.mode in ("veg", "meat"):
                        # Touching or ramming into shoppers slows character speed with screen shake (no HP lost)
                        if shopper.ram_cooldown <= 0:
                            shopper.ram_cooldown = 0.8
                            popup_text = "RAMMED!" if shopper.state == STATE_RUSHING_SHELF else "BUMP!"
                            self.floating_popups.append({
                                "text": popup_text,
                                "x": self.player.center_x,
                                "y": self.player.center_y + 65,
                                "timer": 0.5,
                                "max_timer": 0.5,
                                "color": (255, 180, 80)
                            })

    def complete_game_mode(self):
        audio.play("game_success")
        if self.mode == "veg":
            dialogue = [
                ("Terry", "Phew! All fresh vegetables secured!"),
                ("Terry", "These look crisp and fresh. Mum will be pleased."),
                ("Terry", "Let's head back to the aisle to get the rest of our items."),
            ]
            def to_stage():
                from .stage import MarketStageView
                self.window.show_view(MarketStageView(veg_done=True, meat_done=self.meat_done, last_completed="veg"))
            self.trigger_wave_dialogue(dialogue, to_stage)

        elif self.mode == "meat":
            dialogue = [
                ("Terry", "Got the prime meats! Those shoppers were aggressive!"),
                ("Terry", "The steaks and ribs are safely in our basket."),
                ("Terry", "Alright, let's head back out to the main market aisle."),
            ]
            def to_stage():
                from .stage import MarketStageView
                self.window.show_view(MarketStageView(veg_done=self.veg_done, meat_done=True, last_completed="meat"))
            self.trigger_wave_dialogue(dialogue, to_stage)

        elif self.mode == "defend":
            dialogue = [
                ("Terry", "I made it through the checkout exit doors!"),
                ("Terry", "The groceries survived the mob unscratched!"),
                ("Terry", "Time to head home for the Family Night dinner!"),
            ]
            def to_ending():
                from .ending import MarketEndingView
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
            # Active Wall-Shelf Restock Slot Indicator
            if self.active_restock:
                rx = self.active_restock["x"]
                ry = self.active_restock["y"]
                tex = self.active_restock["texture"]
                t_left = self.active_restock["timer"]
                t_max = self.active_restock["max_timer"]
                anim_t = self.active_restock["anim_timer"]

                # 1. Floor Light Projection Beam
                # Soft, semi-translucent light cone (70px wide, RGBA(255, 220, 80, 40..90))
                # extending outward from crate into the checkered floor
                beam_alpha = int(40 + 50 * (0.5 + 0.5 * math.sin(time.time() * 7.0)))
                beam_color = (255, 220, 80, beam_alpha)
                if rx < 640:
                    # Left wall shelf: projects rightward across aisle floor
                    beam_origin_x = rx + 70  # right edge of crate
                    beam_end_x = beam_origin_x + 300
                    beam_pts = [
                        (beam_origin_x, ry - 35),
                        (beam_origin_x, ry + 35),
                        (beam_end_x, ry + 48),
                        (beam_end_x, ry - 48)
                    ]
                else:
                    # Right wall shelf: projects leftward across aisle floor
                    beam_origin_x = rx - 70  # left edge of crate
                    beam_end_x = beam_origin_x - 300
                    beam_pts = [
                        (beam_origin_x, ry - 35),
                        (beam_origin_x, ry + 35),
                        (beam_end_x, ry + 48),
                        (beam_end_x, ry - 48)
                    ]
                arcade.draw_polygon_filled(beam_pts, beam_color)

                # 2. Backdrop Plate & Pulsing Golden Highlight Box (140 x 80 px)
                crate_w = 140
                crate_h = 80
                pulse_alpha = int(155 + 85 * math.sin(time.time() * 7.0))  # 70..240

                # Dark golden backing rectangle over crate art
                arcade.draw_rect_filled(arcade.XYWH(rx, ry, crate_w, crate_h), (35, 22, 12, 215))
                arcade.draw_rect_filled(arcade.XYWH(rx, ry, crate_w - 6, crate_h - 6), (75, 48, 22, 170))
                # Pulsing outline with warm golden hue
                arcade.draw_rect_outline(arcade.XYWH(rx, ry, crate_w, crate_h), (255, 205, 55, pulse_alpha), border_width=3)
                arcade.draw_rect_outline(arcade.XYWH(rx, ry, crate_w + 4, crate_h + 4), (255, 230, 110, int(pulse_alpha * 0.35)), border_width=1)

                # 3. Floating Target Item Sprite inside Crate with subtle sine-wave bobbing (+/- 4px)
                pop_scale = min(1.0, anim_t / 0.25)
                bob_y = math.sin(time.time() * 5.0) * 4.0
                target_size = 52.0 * pop_scale
                if target_size > 1.0:
                    arcade.draw_texture_rect(tex, arcade.XYWH(rx, ry + bob_y, target_size, target_size))

                # 4. Urgency Progress Bar directly above crate (110 x 8 px)
                bar_w = 110
                bar_h = 8
                bar_y = ry + 49
                arcade.draw_rect_filled(arcade.XYWH(rx, bar_y, bar_w, bar_h), (20, 16, 12, 230))
                arcade.draw_rect_outline(arcade.XYWH(rx, bar_y, bar_w, bar_h), (50, 42, 34), 1)

                pct = max(0.0, min(1.0, t_left / t_max))
                fill_w = max(2.0, (bar_w - 2) * pct)
                fill_x = (rx - (bar_w - 2) / 2) + fill_w / 2
                if pct > 0.5:
                    bar_col = (100, 240, 110)
                elif pct > 0.25:
                    bar_col = (255, 215, 60)
                else:
                    bar_col = (255, 60, 60) if int(time.time() * 8) % 2 == 0 else (180, 25, 25)
                arcade.draw_rect_filled(arcade.XYWH(fill_x, bar_y, fill_w, bar_h - 2), bar_col)

                # 5. Context-Sensitive Beacon Prompt right above urgency bar
                tag_y = bar_y + 17 + (math.sin(time.time() * 6.0) * 2.0)
                dist_to_player = math.hypot(self.player.center_x - rx, self.player.center_y - ry)

                if dist_to_player > 140:
                    # Far away (>140px): Red warning badge "⚡ FRESH DROP"
                    badge_w = 114
                    badge_h = 22
                    arcade.draw_rect_filled(arcade.XYWH(rx, tag_y, badge_w, badge_h), (55, 14, 14, 230))
                    arcade.draw_rect_outline(arcade.XYWH(rx, tag_y, badge_w, badge_h), (255, 75, 75, pulse_alpha), border_width=2)
                    arcade.draw_text("⚡ FRESH DROP", rx, tag_y - 4, (255, 225, 225), 10, bold=True, anchor_x="center")
                else:
                    # In range (<=140px): Bright green interaction badge "[E] GRAB!"
                    badge_w = 98
                    badge_h = 22
                    arcade.draw_rect_filled(arcade.XYWH(rx, tag_y, badge_w, badge_h), (18, 65, 28, 240))
                    arcade.draw_rect_outline(arcade.XYWH(rx, tag_y, badge_w, badge_h), (100, 255, 140, pulse_alpha), border_width=2)
                    arcade.draw_text("[E] GRAB!", rx, tag_y - 4, (240, 255, 220), 11, bold=True, anchor_x="center")

            # 3-Second Warning Hint (Blinking Exclamation Mark) before Food Drops on Shelf
            elif self.mode in ("veg", "meat") and getattr(self, "upcoming_restock", None) is not None and self.restock_timer <= 1.0: # restock hint seconds
                ux = self.upcoming_restock["x"]
                uy = self.upcoming_restock["y"]
                crate_w = 140
                crate_h = 80

                # Rapid blinking state
                blink_on = int(time.time() * 7.0) % 2 == 0
                alert_col = (255, 60, 60) if blink_on else (255, 220, 40)
                glow_alpha = 230 if blink_on else 120

                # Pulsing warning highlight around the target shelf crate
                arcade.draw_rect_filled(arcade.XYWH(ux, uy, crate_w, crate_h), (40, 20, 10, 180))
                arcade.draw_rect_outline(arcade.XYWH(ux, uy, crate_w, crate_h), (alert_col[0], alert_col[1], alert_col[2], glow_alpha), border_width=3)

                # Centered blinking exclamation mark bubble
                bob = math.sin(time.time() * 12.0) * 3.0
                bubble_y = uy + bob
                arcade.draw_circle_filled(ux, bubble_y, 22, (25, 18, 12, 230))
                arcade.draw_circle_outline(ux, bubble_y, 22, alert_col, border_width=2.5)
                arcade.draw_text("!", ux, bubble_y - 12, alert_col, 26, bold=True, anchor_x="center")

                # Floating "INCOMING! X.Xs" countdown banner right above crate
                sec_left = max(0.1, self.restock_timer)
                banner_y = uy + 50
                arcade.draw_rect_filled(arcade.XYWH(ux, banner_y, 116, 22), (25, 15, 12, 240))
                arcade.draw_rect_outline(arcade.XYWH(ux, banner_y, 116, 22), alert_col, border_width=1.5)
                arcade.draw_text(f"INCOMING! {sec_left:.1f}s", ux, banner_y - 4, (255, 235, 180), 10, bold=True, anchor_x="center")

            # Defend Mode: Exit Mat & Chevron Floor Guide
            if self.mode == "defend":
                exit_w = CHECKOUT_MAX_X - CHECKOUT_MIN_X
                exit_cx = (CHECKOUT_MIN_X + CHECKOUT_MAX_X) / 2
                exit_cy = 655
                exit_h = 75

                pulse_a = int(140 + 90 * math.sin(time.time() * 6.0))
                # Glowing green exit mat
                arcade.draw_rect_filled(arcade.XYWH(exit_cx, exit_cy, exit_w, exit_h), (18, 75, 35, 160))
                arcade.draw_rect_outline(arcade.XYWH(exit_cx, exit_cy, exit_w, exit_h), (80, 240, 120, pulse_a), border_width=3)

                # Pulsing chevron arrows pointing up to the checkout doors
                chev_y_offsets = [-18, 0, 18]
                for dy in chev_y_offsets:
                    arrow_y = exit_cy + dy + (math.sin(time.time() * 6.0 + dy) * 3.0)
                    arcade.draw_text("▲   ▲   ▲", exit_cx, arrow_y - 7, (120, 255, 160, pulse_a), 13, bold=True, anchor_x="center")

                # Arcade label: "CHECKOUT EXIT DOORS"
                label_y = CHECKOUT_MIN_Y + 12
                arcade.draw_rect_filled(arcade.XYWH(exit_cx, label_y, 190, 22), (12, 45, 22, 230))
                arcade.draw_rect_outline(arcade.XYWH(exit_cx, label_y, 190, 22), (100, 255, 150, pulse_a), border_width=1.5)
                arcade.draw_text("CHECKOUT EXIT DOORS", exit_cx, label_y - 5, (230, 255, 230), 10, bold=True, anchor_x="center")

            # Draw floor dropped items, shoppers, and player
            self.dropped_items.draw()
            self.snatchers_list.draw()
            for s in self.snatchers_list:
                s.draw_overlays()
            self.player_list.draw()

            # Visual shield aura while Terry is actively blocking (Veg & Meat)
            if self.blocking and self.mode in ("veg", "meat"):
                cx, cy = self.player.center_x, self.player.center_y
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

            banner_title = "PRIME STEAKS" if self.mode == "meat" else "VEGETABLE HARVEST" if self.mode == "veg" else "CHECKOUT ESCAPE!"
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

            # --- Top-Right Horizontal Shopping Checklist / Basket Ribbon ---
            if self.mode == "defend" and self.basket_keys:
                item_count = len(self.basket_keys)
                slot_step = 42
                ribbon_w = (item_count * slot_step) + 16
                ribbon_h = 46
                ribbon_x = WIDTH - (ribbon_w / 2) - 18
                ribbon_y = HEIGHT - 35

                # Basket count tag
                basket_count = len(self.basket_items)
                count_col = (130, 255, 150) if basket_count > 0 else (255, 90, 90)
                arcade.draw_text(
                    f"BASKET: {basket_count}/5",
                    ribbon_x,
                    ribbon_y + 30,
                    count_col,
                    11,
                    bold=True,
                    anchor_x="center",
                    anchor_y="center"
                )

                # Semi-translucent dark pill with subtle wooden border
                arcade.draw_rect_filled(arcade.XYWH(ribbon_x, ribbon_y, ribbon_w, ribbon_h), (25, 15, 10, 190))
                arcade.draw_rect_outline(arcade.XYWH(ribbon_x, ribbon_y, ribbon_w, ribbon_h), (180, 140, 90, 200), border_width=2)

                start_slot_x = (ribbon_x - ribbon_w / 2) + 21
                for i, name in enumerate(self.basket_keys):
                    slot_cx = start_slot_x + (i * slot_step)
                    slot_cy = ribbon_y
                    in_basket = name in self.basket_items
                    tex = self.all_ingredients.get(name)

                    if in_basket:
                        # Carried: subtle green backdrop circle + full opacity icon + bright green checkmark badge
                        arcade.draw_circle_filled(slot_cx, slot_cy, 16, (40, 120, 60, 220))
                        arcade.draw_circle_outline(slot_cx, slot_cy, 16, (90, 210, 110, 200), border_width=1.5)
                        if tex:
                            arcade.draw_texture_rect(tex, arcade.XYWH(slot_cx, slot_cy, 24, 24))

                        # Checkmark badge at bottom-right
                        chk_x = slot_cx + 10
                        chk_y = slot_cy - 10
                        arcade.draw_circle_filled(chk_x, chk_y, 7, (20, 75, 30, 255))
                        arcade.draw_circle_outline(chk_x, chk_y, 7, (120, 255, 150, 255), border_width=1)
                        arcade.draw_text("✔", chk_x, chk_y - 5, (130, 255, 150), 8, bold=True, anchor_x="center")
                    else:
                        # Spilled: dark red slot backdrop with warning red border + reduced opacity icon + red ! badge
                        arcade.draw_circle_filled(slot_cx, slot_cy, 16, (55, 15, 15, 210))
                        arcade.draw_circle_outline(slot_cx, slot_cy, 16, (230, 60, 60, 200), border_width=1.5)
                        if tex:
                            arcade.draw_texture_rect(
                                tex,
                                arcade.XYWH(slot_cx, slot_cy, 22, 22),
                                color=arcade.types.Color(160, 140, 140, 100)
                            )

                        chk_x = slot_cx + 10
                        chk_y = slot_cy - 10
                        arcade.draw_circle_filled(chk_x, chk_y, 7, (80, 15, 15, 255))
                        arcade.draw_circle_outline(chk_x, chk_y, 7, (255, 90, 90, 255), border_width=1)
                        arcade.draw_text("!", chk_x, chk_y - 5, (255, 120, 120), 9, bold=True, anchor_x="center")

            elif self.mode in ("veg", "meat") and self.active_keys:
                item_count = len(self.active_keys)
                slot_step = 42
                ribbon_w = (item_count * slot_step) + 16
                ribbon_h = 46
                ribbon_x = WIDTH - (ribbon_w / 2) - 18
                ribbon_y = HEIGHT - 35

                # Semi-translucent dark pill with subtle wooden border
                arcade.draw_rect_filled(arcade.XYWH(ribbon_x, ribbon_y, ribbon_w, ribbon_h), (25, 15, 10, 190))
                arcade.draw_rect_outline(arcade.XYWH(ribbon_x, ribbon_y, ribbon_w, ribbon_h), (180, 140, 90, 200), border_width=2)

                start_slot_x = (ribbon_x - ribbon_w / 2) + 21
                for i, name in enumerate(self.active_keys):
                    slot_cx = start_slot_x + (i * slot_step)
                    slot_cy = ribbon_y
                    collected = self.collected_status.get(name, False)
                    tex = self.all_ingredients.get(name)

                    if collected:
                        # Collected: subtle green backdrop circle + full opacity icon + bright green checkmark badge
                        arcade.draw_circle_filled(slot_cx, slot_cy, 16, (40, 120, 60, 220))
                        arcade.draw_circle_outline(slot_cx, slot_cy, 16, (90, 210, 110, 200), border_width=1.5)
                        if tex:
                            arcade.draw_texture_rect(tex, arcade.XYWH(slot_cx, slot_cy, 24, 24))

                        # Checkmark badge at bottom-right of circle
                        chk_x = slot_cx + 10
                        chk_y = slot_cy - 10
                        arcade.draw_circle_filled(chk_x, chk_y, 7, (20, 75, 30, 255))
                        arcade.draw_circle_outline(chk_x, chk_y, 7, (120, 255, 150, 255), border_width=1)
                        arcade.draw_text("✔", chk_x, chk_y - 5, (130, 255, 150), 8, bold=True, anchor_x="center")
                    else:
                        # Uncollected: dark circular slot backdrop + icon at reduced opacity (alpha=110)
                        arcade.draw_circle_filled(slot_cx, slot_cy, 16, (18, 12, 10, 190))
                        arcade.draw_circle_outline(slot_cx, slot_cy, 16, (60, 48, 38, 140), border_width=1)
                        if tex:
                            arcade.draw_texture_rect(
                                tex,
                                arcade.XYWH(slot_cx, slot_cy, 22, 22),
                                color=arcade.types.Color(160, 150, 140, 110)
                            )

            # --- Floating popups (pickups, deflections, etc.) ---
            for popup in self.floating_popups:
                alpha = max(0, min(255, int(255 * (popup["timer"] / popup["max_timer"]))))
                r, g, b = popup.get("color", (255, 255, 255))
                arcade.draw_text(
                    popup["text"],
                    popup["x"],
                    popup["y"],
                    arcade.types.Color(r, g, b, alpha),
                    13,
                    bold=True,
                    anchor_x="center",
                    anchor_y="center"
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

        # Draw Retry Modal
        self.retry_modal.draw(ui_camera=self.camera)

        # Draw Instruction Modal Board
        self.instruction_modal.draw(ui_camera=self.camera)

    def on_key_press(self, key, modifiers):
        if self.instruction_modal.visible:
            self.instruction_modal.handle_key_press(key)
            return

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
            self.player_move_x = 0
            self.player_move_y = 0
            self.pause_menu.open()
            return

        # Shelf grab interaction with Enter / Num_Enter / E
        if key in (arcade.key.ENTER, arcade.key.NUM_ENTER, arcade.key.E):
            if self.try_grab_shelf():
                return

        # Space key for Block (gathering modes) or Spin & Defend (defend mode)
        if key == arcade.key.SPACE:
            self.trigger_block_or_spin()
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
        dy = (arcade.key.W in self.held or arcade.key.UP in self.held) - \
             (arcade.key.S in self.held or arcade.key.DOWN in self.held)
        self.player_move_x = dx
        self.player_move_y = dy

    def on_mouse_press(self, x, y, button, modifiers):
        canvas_x, canvas_y = self.canvas_point(x, y)

        if self.instruction_modal.visible:
            self.instruction_modal.handle_mouse_press(canvas_x, canvas_y)
            return

        if self.retry_modal.visible:
            self.retry_modal.handle_mouse_press(canvas_x, canvas_y)
            return

        if self.settings_panel.on_mouse_press(canvas_x, canvas_y, button):
            return

        if self.pause_menu.visible:
            action = self.pause_menu.on_mouse_press(canvas_x, canvas_y, button)
            self.run_action(action)
            return

        if button == arcade.MOUSE_BUTTON_LEFT:
            self.trigger_block_or_spin()

    def on_mouse_motion(self, x, y, dx, dy):
        self.pause_menu.on_mouse_motion(*self.canvas_point(x, y))

    def run_action(self, action):
        if action == "resume":
            self.pause_menu.close()
        elif action == "settings":
            self.settings_panel.open()
        elif action == "menu":
            from ..menu.view import MenuView
            self.window.show_view(MenuView())
        elif action == "quit":
            self.window.close()

    def take_damage(self, ignore_invuln: bool = False):
        if self.lives <= 0 or (self.invuln_timer > 0 and not ignore_invuln):
            return
        self.invuln_timer = 1.0
        audio.play("get_snatched")
        audio.play("hp_reduced")
        self.lives -= 1
        self.damage_alpha = 140.0
        self.shake_timer = 0.3
        self.shake_intensity = 8.0

        # Target the lost heart
        self.breaking_idx = self.lives
        if 0 <= self.breaking_idx < self.max_lives:
            self.hearts[self.breaking_idx].texture = textures.ui_image("Character_HP_broke_into_half.png")
            self.heart_anim_timer = 0.18
            self.heart_anim_state = 1

        if self.lives <= 0:
            self.show_retry_prompt("Out of HP! Terry was overwhelmed by shoppers.")
