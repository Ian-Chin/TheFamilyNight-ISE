import math
import random
import time
import arcade

from ...config import HEIGHT, WIDTH
from .common import (
    PLAY_LEFT, PLAY_RIGHT,
    AISLE_MIN_X, AISLE_MAX_X, AISLE_MIN_Y, AISLE_MAX_Y
)

STATE_WANDERING = "WANDERING"
STATE_RUSHING_SHELF = "RUSHING_SHELF"
STATE_FLEEING_WITH_ITEM = "FLEEING_WITH_ITEM"
STATE_STUNNED = "STUNNED"


def get_separated_x(existing_sprites, min_gap=110, attempts=12):
    """Generates an X coordinate spaced away from existing entities."""
    for gap in (min_gap, min_gap * 0.75, min_gap * 0.5):
        for _ in range(attempts // 3):
            candidate_x = random.randint(AISLE_MIN_X + 40, AISLE_MAX_X - 40)
            if all(abs(candidate_x - s.center_x) >= gap for s in existing_sprites):
                return candidate_x
    return random.randint(AISLE_MIN_X + 40, AISLE_MAX_X - 40)


class DroppedIngredient(arcade.Sprite):
    """Temporary floor pickup dropped when a fleeing shopper is stunned or food is spilled."""

    def __init__(self, item_name, texture, x, y, persists_indefinitely=False):
        target_size = 46.0
        calc_scale = target_size / max(texture.width, texture.height)
        super().__init__(texture, scale=calc_scale)
        self.item_name = item_name
        self.center_x = x
        self.center_y = y
        self.timer = 5.0
        self.max_timer = 5.0
        self.expired = False
        self.persists_indefinitely = persists_indefinitely

    def update_timer(self, delta_time):
        if self.persists_indefinitely:
            self.alpha = 255
            return False
        self.timer -= delta_time
        if self.timer <= 0:
            self.expired = True
            return True
        # Blinking effect when < 1.8 seconds remaining
        if self.timer < 1.8:
            blink = int((self.timer * 9) % 2)
            self.alpha = 255 if blink == 0 else 70
        else:
            self.alpha = 255
        return False


# Compatibility alias
IngredientDrop = DroppedIngredient


class SnatcherSprite(arcade.Sprite):
    """2D floor NPC with 4 AI states: WANDERING, RUSHING_SHELF, FLEEING_WITH_ITEM, STUNNED."""

    def __init__(self, fall_textures, grab_textures, initial_x=None, initial_y=None, rush_speed=5.2, player_pos=None, min_dist=200):
        self.base_scale = 0.38
        super().__init__(fall_textures[0], scale=self.base_scale)
        self.fall_textures = fall_textures
        self.grab_textures = grab_textures
        self.frame_timer = 0.0
        self.cur_frame = 0

        self.state = STATE_WANDERING
        self.rush_speed = rush_speed
        self.wander_speed = random.uniform(1.6, 2.4)
        self.chase_speed = random.uniform(2.5, 3.4)
        self.wander_timer = 0.0
        self.target_x = 0
        self.target_y = 0

        self.carried_item = None
        self.carried_texture = None
        self.has_fled_with_item = False

        self.stun_timer = 0.0
        self.ram_cooldown = 0.0
        self.knockback_vx = 0.0
        self.knockback_vy = 0.0

        self.reset_pos(custom_x=initial_x, custom_y=initial_y, rush_speed=rush_speed, player_pos=player_pos, min_dist=min_dist)

    def reset_pos(self, custom_x=None, custom_y=None, rush_speed=None, existing_list=None, player_pos=None, min_dist=200):
        self.state = STATE_WANDERING
        self.carried_item = None
        self.carried_texture = None
        self.target_floor_item = None
        self.has_fled_with_item = False
        self.stun_timer = 0.0
        self.ram_cooldown = 0.0
        self.knockback_vx = 0.0
        self.knockback_vy = 0.0
        self.angle = 0
        self.alpha = 255
        if rush_speed is not None:
            self.rush_speed = rush_speed
        self.wander_speed = random.uniform(1.5, 2.7)
        self.chase_speed = random.uniform(2.5, 3.4)

        if custom_x is not None and custom_y is not None:
            self.center_x = custom_x
            self.center_y = custom_y
        else:
            # Pick a spawn location with comfortable clearance away from player
            chosen = False
            for _ in range(35):
                cand_x = random.randint(AISLE_MIN_X + 60, AISLE_MAX_X - 60)
                cand_y = random.randint(AISLE_MIN_Y + 50, AISLE_MAX_Y - 50)
                if player_pos is not None:
                    dist = math.hypot(cand_x - player_pos[0], cand_y - player_pos[1])
                    if dist < min_dist:
                        continue
                self.center_x = cand_x
                self.center_y = cand_y
                chosen = True
                break

            if not chosen:
                self.center_x = random.choice([AISLE_MIN_X + 60, AISLE_MAX_X - 60])
                self.center_y = random.choice([AISLE_MIN_Y + 50, AISLE_MAX_Y - 50])

        self.pick_new_wander_target()

    def pick_new_wander_target(self):
        self.target_x = random.randint(AISLE_MIN_X + 40, AISLE_MAX_X - 40)
        self.target_y = random.randint(AISLE_MIN_Y + 40, AISLE_MAX_Y - 40)
        self.wander_timer = random.uniform(1.5, 3.5)

    def trigger_rush(self, shelf_x, shelf_y, item_name, item_texture):
        if self.state == STATE_WANDERING:
            self.state = STATE_RUSHING_SHELF
            self.target_x = shelf_x
            self.target_y = shelf_y
            self.carried_item = None
            self.carried_texture = None
            self.target_floor_item = None

    def cancel_rush(self):
        if self.state == STATE_RUSHING_SHELF:
            self.state = STATE_WANDERING
            self.target_floor_item = None
            self.pick_new_wander_target()

    def claim_item(self, item_name, item_texture):
        self.state = STATE_FLEEING_WITH_ITEM
        self.carried_item = item_name
        self.carried_texture = item_texture
        self.target_floor_item = None
        # Sprint toward nearest top/bottom exit of the screen
        if self.center_y >= HEIGHT / 2:
            self.target_y = HEIGHT + 120
        else:
            self.target_y = -120
        self.target_x = self.center_x

    def trigger_stun(self, from_x, from_y, is_defending=False):
        was_fleeing = (self.state == STATE_FLEEING_WITH_ITEM and self.carried_item is not None)
        dropped = (self.carried_item, self.carried_texture) if was_fleeing else None

        self.carried_item = None
        self.carried_texture = None
        self.target_floor_item = None
        self.state = STATE_STUNNED
        self.stun_timer = 1.8
        self.ram_cooldown = 1.8

        dx = self.center_x - from_x
        dy = self.center_y - from_y
        dist = max(1.0, math.hypot(dx, dy))
        speed = 9.5 if is_defending else 7.5
        self.knockback_vx = (dx / dist) * speed
        self.knockback_vy = (dy / dist) * speed

        return dropped

    def update_animation(self, delta_time, move_dx, is_action=False, fast=False):
        anim_speed = 0.08 if fast else 0.12
        self.frame_timer += delta_time
        if self.frame_timer >= anim_speed:
            self.frame_timer = 0.0
            active_list = self.grab_textures if is_action else self.fall_textures
            self.cur_frame = (self.cur_frame + 1) % len(active_list)
            self.texture = active_list[self.cur_frame]

        if move_dx < -0.1:
            self.scale_x = -abs(self.base_scale)
        elif move_dx > 0.1:
            self.scale_x = abs(self.base_scale)

    def update_behavior(self, delta_time, player_y, player_x, dropped_items=None):
        step = delta_time * 60.0
        if self.ram_cooldown > 0:
            self.ram_cooldown = max(0.0, self.ram_cooldown - delta_time)

        # STUNNED STATE
        if self.state == STATE_STUNNED:
            self.stun_timer -= delta_time
            self.center_x += self.knockback_vx * step
            self.center_y += self.knockback_vy * step
            self.knockback_vx *= 0.88
            self.knockback_vy *= 0.88

            # Confine within floor area
            self.center_x = max(AISLE_MIN_X - 10, min(AISLE_MAX_X + 10, self.center_x))
            self.center_y = max(AISLE_MIN_Y - 10, min(AISLE_MAX_Y + 10, self.center_y))

            # Dizzy frame
            self.texture = self.grab_textures[0]
            if self.stun_timer <= 0:
                self.state = STATE_WANDERING
                self.pick_new_wander_target()
            return

        # 1. WANDERING (with Opportunistic Stealing of dropped items within 260px)
        if self.state == STATE_WANDERING:
            if dropped_items:
                nearest_item = None
                nearest_dist = 260.0
                for item in dropped_items:
                    d = math.hypot(item.center_x - self.center_x, item.center_y - self.center_y)
                    if d < nearest_dist:
                        nearest_dist = d
                        nearest_item = item

                if nearest_item:
                    self.state = STATE_RUSHING_SHELF
                    self.target_x = nearest_item.center_x
                    self.target_y = nearest_item.center_y
                    self.target_floor_item = nearest_item

            if self.state == STATE_WANDERING:
                self.wander_timer -= delta_time
                dx = self.target_x - self.center_x
                dy = self.target_y - self.center_y
                dist = math.hypot(dx, dy)
                if dist < 20 or self.wander_timer <= 0:
                    self.pick_new_wander_target()
                else:
                    move_dist = min(dist, self.wander_speed * step)
                    self.center_x += (dx / dist) * move_dist
                    self.center_y += (dy / dist) * move_dist
                    self.update_animation(delta_time, dx, is_action=False, fast=False)

        # 2. RUSHING_SHELF (or rushing dropped floor item)
        elif self.state == STATE_RUSHING_SHELF:
            # If tracking a dropped item that was picked up, revert to wandering
            if getattr(self, "target_floor_item", None):
                if dropped_items is not None and self.target_floor_item not in dropped_items:
                    self.target_floor_item = None
                    self.state = STATE_WANDERING
                    self.pick_new_wander_target()
                    return

            dx = self.target_x - self.center_x
            dy = self.target_y - self.center_y
            dist = math.hypot(dx, dy)
            move_dist = min(dist, self.rush_speed * step)
            if dist > 0.1:
                self.center_x += (dx / dist) * move_dist
                self.center_y += (dy / dist) * move_dist
            self.update_animation(delta_time, dx, is_action=True, fast=True)

            # Check if reached target floor item to claim it
            if getattr(self, "target_floor_item", None):
                if dist < 35:
                    item = self.target_floor_item
                    self.claim_item(item.item_name, item.texture)
                    self.target_floor_item = None
                    item.remove_from_sprite_lists()

        # 3. FLEEING_WITH_ITEM
        elif self.state == STATE_FLEEING_WITH_ITEM:
            dy = self.target_y - self.center_y
            flee_speed = 5.8
            step_y = (1.0 if dy > 0 else -1.0) * flee_speed * step
            self.center_y += step_y
            self.update_animation(delta_time, 0, is_action=True, fast=True)

            # Exit boundaries check
            if self.center_y > HEIGHT + 60 or self.center_y < -60:
                self.has_fled_with_item = True
                self.has_fled_with_item = True

    def draw_overlays(self):
        """Draws carried items or stun indicators above shopper."""
        if self.state == STATE_FLEEING_WITH_ITEM and self.carried_texture:
            bob = math.sin(time.time() * 8) * 3
            icon_x = self.center_x
            icon_y = self.top + 18 + bob
            # Floating halo
            arcade.draw_circle_filled(icon_x, icon_y, 18, (255, 245, 210, 220))
            arcade.draw_circle_outline(icon_x, icon_y, 18, (230, 160, 40, 240), 2)
            arcade.draw_texture_rect(self.carried_texture, arcade.XYWH(icon_x, icon_y, 28, 28))

        elif self.state == STATE_STUNNED:
            bob = math.sin(time.time() * 9) * 3
            arcade.draw_text(
                "★ STUNNED ★",
                self.center_x,
                self.top + 14 + bob,
                (255, 230, 80),
                10,
                bold=True,
                anchor_x="center",
                anchor_y="center"
            )
