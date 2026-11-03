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
    AISLE_MIN_X, AISLE_MAX_X, AISLE_MIN_Y, AISLE_MAX_Y,
    DialogueController, RetryModal
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
        self.widgets = [self.dialog, self.pause_menu, self.settings_panel]

        # Duration: 40s for gathering, 45s for defend
        self.duration = 45.0 if self.mode == "defend" else 40.0
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
        self.restock_interval = 4.5 if self.mode == "veg" else 3.8
        self.restock_timer = 1.2    # Initial delay before first restock
        self.shopper_rush_speed = 5.0 if self.mode == "veg" else 6.5

        # Terry Spin Mechanics (Defend mode)
        self.spinning = False
        self.spin_timer = 0.0
        self.spin_angle = 180.0
        self.spin_cooldown = 0.0

        # Terry Block & Speed Boost Mechanics
        self.blocking = False
        self.block_timer = 0.0
        self.block_duration = 0.45
        self.block_cooldown = 0.0
        self.base_speed = 7.5
        self.boost_speed = 13.0
        self.speed_boosted = False

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
        self.time_left = self.duration
        self.restock_timer = 1.2

        if self.mode == "veg":
            count = 3
            self.shopper_rush_speed = 5.0
        elif self.mode == "meat":
            count = 5
            self.shopper_rush_speed = 6.5
        else:
            count = 6
            self.shopper_rush_speed = 4.5

        for _ in range(count):
            falls, grabs = random.choice(self.snatcher_types)
            shopper = SnatcherSprite(
                falls,
                grabs,
                rush_speed=self.shopper_rush_speed,
                player_pos=(self.player.center_x, self.player.center_y),
                min_dist=240
            )
            self.snatchers_list.append(shopper)

    def trigger_block_or_spin(self):
        """Triggers Terry's block in gathering modes or spin attack in defend mode."""
        if self.mode == "defend" and not self.spinning and self.spin_cooldown <= 0:
            audio.play("swing_sword")
            self.spinning = True
            self.spin_timer = 0.35
            self.spin_cooldown = 0.55
            return True
        elif self.mode in ("veg", "meat") and not self.blocking and self.block_cooldown <= 0:
            audio.play("block")
            self.blocking = True
            self.block_timer = self.block_duration
            self.block_cooldown = self.block_duration + 0.30
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

    def show_retry_prompt(self):
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
        self.retry_modal.open(
            on_retry=do_retry,
            on_give_up=do_give_up,
            title=f"{mode_name.upper()} FAILED!",
            message="Would you like to try again or return to market?"
        )

    def try_grab_shelf(self):
        """Grabs the item from the active shelf slot if Terry is within 65px."""
        if not self.active_restock:
            return False

        slot_x = self.active_restock["x"]
        slot_y = self.active_restock["y"]
        dist = math.hypot(self.player.center_x - slot_x, self.player.center_y - slot_y)

        if dist <= 65:
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

        if self.pause_menu.visible or self.settings_panel.visible or self.retry_modal.visible:
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
                    self.show_retry_prompt()
                else:
                    self.completed = True
                    self.complete_game_mode()
                return

        # 2. Player Movement & Actions
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

        # 2D Top-Down Movement with diagonal normalization and Shift speed boost
        step = delta_time * 60.0
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

        # 3. Shelf Restock Cycle (Veg & Meat Modes)
        if self.mode in ("veg", "meat") and not self.completed:
            # Active shelf slot timer update
            if self.active_restock is not None:
                self.active_restock["anim_timer"] += delta_time
                self.active_restock["timer"] -= delta_time
                if self.active_restock["timer"] <= 0:
                    # Urgency expired - shoppers cleared the shelf
                    self.active_restock = None
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
                    if self.restock_timer <= 0:
                        pick_name = random.choice(candidates)
                        slot_x, slot_y = random.choice(SHELF_SLOTS)
                        self.active_restock = {
                            "x": slot_x,
                            "y": slot_y,
                            "side": "left" if slot_x == SHELF_LEFT_X else "right",
                            "item_name": pick_name,
                            "texture": self.all_ingredients[pick_name],
                            "timer": 6.0,
                            "max_timer": 6.0,
                            "anim_timer": 0.0,
                        }

                        # Trigger shoppers on that side to rush the shelf
                        for shopper in self.snatchers_list:
                            if slot_x < 640 and shopper.center_x < 640:
                                shopper.trigger_rush(slot_x, slot_y, pick_name, self.all_ingredients[pick_name])
                            elif slot_x >= 640 and shopper.center_x >= 640:
                                shopper.trigger_rush(slot_x, slot_y, pick_name, self.all_ingredients[pick_name])

        # 4. Floor Dropped Pickups Update
        for item in list(self.dropped_items):
            expired = item.update_timer(delta_time)
            if expired:
                item.remove_from_sprite_lists()
            else:
                dist_item = math.hypot(self.player.center_x - item.center_x, self.player.center_y - item.center_y)
                if arcade.check_for_collision(self.player, item) or dist_item < 50:
                    audio.play("ingredient_get")
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
                    if all(self.collected_status.values()) and not self.completed:
                        self.completed = True
                        self.complete_game_mode()
                        return

        # 5. Shopper Behavior, Shelf Claim, and Collisions
        for shopper in list(self.snatchers_list):
            shopper.update_behavior(delta_time, self.player.center_y, self.player.center_x, is_wave_3=(self.mode == "defend"))

            # Check if shopper successfully fled off screen with a stolen ingredient
            if shopper.has_fled_with_item:
                self.take_damage()
                self.floating_popups.append({
                    "text": "ITEM LOST!",
                    "x": self.player.center_x,
                    "y": self.player.center_y + 65,
                    "timer": 0.85,
                    "max_timer": 0.85,
                    "color": (255, 90, 90)
                })
                shopper.reset_pos(
                    rush_speed=self.shopper_rush_speed,
                    player_pos=(self.player.center_x, self.player.center_y),
                    min_dist=240
                )
                if self.lives <= 0:
                    self.show_retry_prompt()
                    return

            # Check if rushing shopper reached the active shelf slot before Terry
            if self.active_restock and shopper.state == STATE_RUSHING_SHELF:
                dist_shelf = math.hypot(shopper.center_x - self.active_restock["x"], shopper.center_y - self.active_restock["y"])
                if dist_shelf < 42:
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
                    self.restock_timer = self.restock_interval
                    for other in self.snatchers_list:
                        other.cancel_rush()

            # Terry & Shopper Collisions
            dist_x = abs(self.player.center_x - shopper.center_x)
            dist_y = abs(self.player.center_y - shopper.center_y)
            dist_total = math.hypot(dist_x, dist_y)
            is_colliding = arcade.check_for_collision(self.player, shopper) or (dist_total < 55)

            if shopper.state != STATE_STUNNED:
                # Terry Block / Parry
                if self.blocking and (is_colliding or dist_total < 80):
                    audio.play("block")
                    self.shake_timer = 0.25
                    self.shake_intensity = 6.0
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

                # Terry Spin attack in Defend mode
                elif self.spinning and is_colliding:
                    audio.play("ui_click")
                    self.shake_timer = 0.25
                    self.shake_intensity = 6.0
                    shopper.trigger_stun(self.player.center_x, self.player.center_y, is_defending=True)
                    self.floating_popups.append({
                        "text": "SMACK!",
                        "x": shopper.center_x,
                        "y": shopper.center_y + 40,
                        "timer": 0.45,
                        "max_timer": 0.45,
                        "color": (255, 230, 120)
                    })

                # Unblocked Collision with a RUSHING shopper
                elif is_colliding and shopper.state == STATE_RUSHING_SHELF and shopper.ram_cooldown <= 0:
                    shopper.ram_cooldown = 1.2
                    self.take_damage()
                    self.floating_popups.append({
                        "text": "RAMMED!",
                        "x": self.player.center_x,
                        "y": self.player.center_y + 65,
                        "timer": 0.6,
                        "max_timer": 0.6,
                        "color": (255, 70, 70)
                    })
                    if self.lives <= 0:
                        self.show_retry_prompt()
                        return

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
                ("Terry", "I dodged them all! The last of the mob finally gave up chasing!"),
                ("Terry", "My basket survived unscratched! Let's get out of here!"),
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

                # Golden glowing box with alpha oscillation
                pulse_alpha = int(170 + 80 * math.sin(time.time() * 7.0))
                slot_w = 54
                slot_h = 54
                arcade.draw_rect_filled(arcade.XYWH(rx, ry, slot_w, slot_h), (255, 220, 80, int(pulse_alpha * 0.25)))
                arcade.draw_rect_outline(arcade.XYWH(rx, ry, slot_w, slot_h), (255, 215, 60, pulse_alpha), border_width=3)

                # Pop-in scale animation (0.0 to 1.0)
                pop_scale = min(1.0, anim_t / 0.25)
                target_size = 46.0 * pop_scale
                if target_size > 1.0:
                    arcade.draw_texture_rect(tex, arcade.XYWH(rx, ry, target_size, target_size))

                # Mini Urgency Progress Bar above shelf slot
                bar_w = 46
                bar_h = 6
                bar_y = ry + 36
                arcade.draw_rect_filled(arcade.XYWH(rx, bar_y, bar_w, bar_h), (20, 16, 12, 230))
                arcade.draw_rect_outline(arcade.XYWH(rx, bar_y, bar_w, bar_h), (50, 42, 34), 1)

                pct = max(0.0, min(1.0, t_left / t_max))
                fill_w = max(2.0, (bar_w - 2) * pct)
                fill_x = (rx - (bar_w - 2) / 2) + fill_w / 2
                bar_col = (110, 240, 120) if pct > 0.5 else (255, 215, 60) if pct > 0.25 else (255, 75, 75)
                arcade.draw_rect_filled(arcade.XYWH(fill_x, bar_y, fill_w, bar_h - 2), bar_col)

                # Pulsing "[ENTER] GRAB" prompt when Terry is within 65px
                dist_to_player = math.hypot(self.player.center_x - rx, self.player.center_y - ry)
                if dist_to_player <= 65:
                    prompt_alpha = int(200 + 55 * math.sin(time.time() * 9.0))
                    prompt_x = rx + (58 if rx < 640 else -58)
                    prompt_y = ry
                    pill_w = 98
                    pill_h = 24
                    arcade.draw_rect_filled(arcade.XYWH(prompt_x, prompt_y, pill_w, pill_h), (25, 18, 12, 230))
                    arcade.draw_rect_outline(arcade.XYWH(prompt_x, prompt_y, pill_w, pill_h), (255, 220, 90, prompt_alpha), 2)
                    arcade.draw_text("[ENTER] GRAB", prompt_x, prompt_y - 4, (255, 240, 150, prompt_alpha), 10, bold=True, anchor_x="center")

            # Draw floor dropped items, shoppers, and player
            self.dropped_items.draw()
            self.snatchers_list.draw()
            for s in self.snatchers_list:
                s.draw_overlays()
            self.player_list.draw()

            # Visual shield aura while Terry is actively blocking
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

            # --- Bottom Key Hints ---
            if self.mode in ("veg", "meat"):
                block_status = "READY" if self.block_cooldown <= 0 else "RECHARGING"
                status_col = (130, 240, 160) if self.block_cooldown <= 0 else (240, 180, 100)
                arcade.draw_text(
                    f"WASD: Move   |   [ENTER]: Grab Shelf   |   SPACE: Block [{block_status}]   |   Hold Shift: Speed Boost",
                    WIDTH / 2 - 40, 25, status_col, 13, anchor_x="center", bold=True
                )
            elif self.mode == "defend":
                spin_status = "READY" if self.spin_cooldown <= 0 else "RECHARGING"
                status_col = (130, 240, 160) if self.spin_cooldown <= 0 else (240, 180, 100)
                arcade.draw_text(
                    f"WASD: Move   |   SPACE: Spin & Defend [{spin_status}]   |   Hold Shift: Speed Boost",
                    WIDTH / 2 - 40, 25, status_col, 13, anchor_x="center", bold=True
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

    def take_damage(self):
        if self.lives <= 0:
            return
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
