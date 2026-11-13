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
            candidate_x = random.randint(AISLE_MIN_X + 20, AISLE_MAX_X - 20)
            if all(abs(candidate_x - s.center_x) >= gap for s in existing_sprites):
                return candidate_x
    return random.randint(AISLE_MIN_X + 20, AISLE_MAX_X - 20)


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
        if self.timer < 1.8:
            blink = int((self.timer * 9) % 2)
            self.alpha = 255 if blink == 0 else 70
        else:
            self.alpha = 255
        return False



IngredientDrop = DroppedIngredient


class SnatcherSprite(arcade.Sprite):
    """2D floor NPC with 4 AI states: WANDERING, RUSHING_SHELF, FLEEING_WITH_ITEM, STUNNED."""

    def __init__(self, anim_data_or_falls, grab_textures=None, initial_x=None, initial_y=None, rush_speed=5.2, player_pos=None, min_dist=200):
        self.base_scale = 0.38

       
        if isinstance(anim_data_or_falls, dict):
            self.animations = anim_data_or_falls
            self.walk_textures = self.animations.get("walk", [])
            self.walk_right_textures = self.animations.get("walk_right", self.walk_textures)
            self.rush_textures = self.animations.get("rush", self.walk_textures)
            self.rush_right_textures = self.animations.get("rush_right", self.rush_textures)
            self.grab_textures = self.animations.get("grab", self.walk_textures)
        else:
            self.walk_textures = list(anim_data_or_falls)
            self.walk_right_textures = self.walk_textures
            self.grab_textures = list(grab_textures) if grab_textures is not None else self.walk_textures
            self.rush_textures = self.grab_textures
            self.rush_right_textures = self.grab_textures
            self.animations = {
                "walk": self.walk_textures,
                "walk_right": self.walk_right_textures,
                "rush": self.rush_textures,
                "rush_right": self.rush_right_textures,
                "grab": self.grab_textures,
            }

        self.fall_textures = self.walk_textures
        first_tex = self.walk_textures[0] if self.walk_textures else (
            self.grab_textures[0] if self.grab_textures else arcade.make_circle_texture(32, (200, 40, 40))
        )
        super().__init__(first_tex, scale=self.base_scale)
        self.frame_timer = 0.0
        self.cur_frame = 0

        self.state = STATE_WANDERING
        self.rush_speed = rush_speed
        self.flee_speed = 3.6 
        self.rush_reaction_timer = 0.0
        self.wander_speed = random.uniform(2.0, 3.2)
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
        self.rush_reaction_timer = 0.0
        self.flee_speed = 3.6 
        self.stun_timer = 0.0
        self.ram_cooldown = 0.0
        self.knockback_vx = 0.0
        self.knockback_vy = 0.0
        self.angle = 0
        self.alpha = 255
        if rush_speed is not None:
            self.rush_speed = rush_speed
        self.wander_speed = random.uniform(2.0, 3.2) 
        self.chase_speed = random.uniform(2.5, 3.4)

        if custom_x is not None and custom_y is not None:
            self.center_x = custom_x
            self.center_y = custom_y
        else:
            chosen = False
            for _ in range(35):
                cand_x = random.randint(AISLE_MIN_X + 25, AISLE_MAX_X - 25)
                cand_y = random.randint(AISLE_MIN_Y + 25, AISLE_MAX_Y - 25)
                if player_pos is not None:
                    dist = math.hypot(cand_x - player_pos[0], cand_y - player_pos[1])
                    if dist < min_dist:
                        continue
                self.center_x = cand_x
                self.center_y = cand_y
                chosen = True
                break

            if not chosen:
                self.center_x = random.choice([AISLE_MIN_X + 35, AISLE_MAX_X - 35])
                self.center_y = random.choice([AISLE_MIN_Y + 35, AISLE_MAX_Y - 35])

        self.pick_new_wander_target()

    def pick_new_wander_target(self):
        min_x = AISLE_MIN_X + 15
        max_x = AISLE_MAX_X - 15
        min_y = AISLE_MIN_Y + 15
        max_y = AISLE_MAX_Y - 15

     
        roll = random.random()
        if roll < 0.15:
            self.target_x = random.randint(min_x, min_x + 180)
            self.target_y = random.randint(min_y, max_y)
        elif roll < 0.30:
            self.target_x = random.randint(max_x - 180, max_x)
            self.target_y = random.randint(min_y, max_y)
        elif roll < 0.45:
            self.target_x = random.randint(min_x, max_x)
            self.target_y = random.randint(max_y - 150, max_y)
        elif roll < 0.60:
            self.target_x = random.randint(min_x, max_x)
            self.target_y = random.randint(min_y, min_y + 150)
        else:
            self.target_x = random.randint(min_x, max_x)
            self.target_y = random.randint(min_y, max_y)

   
        dx = self.target_x - self.center_x
        dy = self.target_y - self.center_y
        dist = math.hypot(dx, dy)
        travel_time = dist / max(1.0, self.wander_speed * 60.0)
        self.wander_timer = travel_time + random.uniform(1.2, 2.8)

    def trigger_rush(self, shelf_x, shelf_y, item_name, item_texture, delay=None):
        if self.state == STATE_WANDERING:
            self.state = STATE_RUSHING_SHELF
            self.target_x = shelf_x
            self.target_y = shelf_y
            self.carried_item = None
            self.carried_texture = None
            self.target_floor_item = None
            self.rush_reaction_timer = delay if delay is not None else random.uniform(0.5, 0.8) # reaction delay before rushing to shelf

    def cancel_rush(self):
        if self.state == STATE_RUSHING_SHELF:
            self.state = STATE_WANDERING
            self.target_floor_item = None
            self.rush_reaction_timer = 0.0
            self.pick_new_wander_target()

    def claim_item(self, item_name, item_texture):
        self.state = STATE_FLEEING_WITH_ITEM
        self.carried_item = item_name
        self.carried_texture = item_texture
        self.target_floor_item = None
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
        self.angle = 0
        self.stun_timer = 1.8
        self.ram_cooldown = 1.8

        dx = self.center_x - from_x
        dy = self.center_y - from_y
        dist = max(1.0, math.hypot(dx, dy))
        speed = 9.5 if is_defending else 7.5
        self.knockback_vx = (dx / dist) * speed
        self.knockback_vy = (dy / dist) * speed

        return dropped

    def update_animation(self, delta_time, move_dx, is_action=False, fast=False, anim_type=None):
        anim_speed = 0.05 if fast else 0.07
        self.frame_timer += delta_time

        if anim_type is None:
            anim_type = "grab" if (is_action and self.state == STATE_FLEEING_WITH_ITEM) else ("rush" if is_action else "walk")

        is_moving_right = move_dx > 0.1
        is_moving_left = move_dx < -0.1

        if anim_type == "rush":
            if is_moving_right:
                active_list = self.rush_right_textures
                self.scale_x = abs(self.base_scale)
            elif is_moving_left:
                active_list = self.rush_right_textures
                self.scale_x = -abs(self.base_scale)
            else:
                active_list = self.rush_textures
        elif anim_type == "grab":
            active_list = self.grab_textures
            if is_moving_left:
                self.scale_x = -abs(self.base_scale)
            elif is_moving_right:
                self.scale_x = abs(self.base_scale)
        else:
            if is_moving_right:
                active_list = self.walk_right_textures
                self.scale_x = abs(self.base_scale)
            elif is_moving_left:
                active_list = self.walk_right_textures
                self.scale_x = -abs(self.base_scale)
            else:
                active_list = self.walk_textures

        if not active_list:
            return

        if self.frame_timer >= anim_speed:
            self.frame_timer = 0.0
            self.cur_frame = (self.cur_frame + 1) % len(active_list)
            self.texture = active_list[self.cur_frame]

    def update_behavior(self, delta_time, player_y, player_x, dropped_items=None, is_wave_3=False, **kwargs):
        step = delta_time * 60.0
        if self.ram_cooldown > 0:
            self.ram_cooldown = max(0.0, self.ram_cooldown - delta_time)

    
        if self.state == STATE_STUNNED:
            self.stun_timer -= delta_time
            self.center_x += self.knockback_vx * step
            self.center_y += self.knockback_vy * step
            self.knockback_vx *= 0.88
            self.knockback_vy *= 0.88

          
            self.center_x = max(AISLE_MIN_X + 5, min(AISLE_MAX_X - 5, self.center_x))
            self.center_y = max(AISLE_MIN_Y + 5, min(AISLE_MAX_Y - 5, self.center_y))

          
            self.texture = self.grab_textures[0]
            if self.stun_timer <= 0:
                self.state = STATE_WANDERING
                self.pick_new_wander_target()
            return

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
                if dist < 25 or self.wander_timer <= 0:
                    self.pick_new_wander_target()
                else:
                    move_dist = min(dist, self.wander_speed * step)
                    self.center_x += (dx / dist) * move_dist
                    self.center_y += (dy / dist) * move_dist
                    self.update_animation(delta_time, dx, is_action=False, fast=False, anim_type="walk")

              
                self.center_x = max(AISLE_MIN_X + 10, min(AISLE_MAX_X - 10, self.center_x))
                self.center_y = max(AISLE_MIN_Y + 10, min(AISLE_MAX_Y - 10, self.center_y))

        elif self.state == STATE_RUSHING_SHELF:
            if getattr(self, "target_floor_item", None):
                if dropped_items is not None and self.target_floor_item not in dropped_items:
                    self.target_floor_item = None
                    self.rush_reaction_timer = 0.0
                    self.state = STATE_WANDERING
                    self.pick_new_wander_target()
                    return

     
            if getattr(self, "rush_reaction_timer", 0) > 0:
                self.rush_reaction_timer -= delta_time
                dx = self.target_x - self.center_x
                self.update_animation(delta_time, dx, is_action=False, fast=False, anim_type="walk")
                return

            dx = self.target_x - self.center_x
            dy = self.target_y - self.center_y
            dist = math.hypot(dx, dy)
            move_dist = min(dist, self.rush_speed * step)
            if dist > 0.1:
                self.center_x += (dx / dist) * move_dist
                self.center_y += (dy / dist) * move_dist
            self.update_animation(delta_time, dx, is_action=True, fast=True, anim_type="rush")

           
            if getattr(self, "target_floor_item", None):
                if dist < 35:
                    item = self.target_floor_item
                    self.claim_item(item.item_name, item.texture)
                    self.target_floor_item = None
                    item.remove_from_sprite_lists()

       
        elif self.state == STATE_FLEEING_WITH_ITEM:
            dy = self.target_y - self.center_y
            flee_speed = getattr(self, "flee_speed", 3.6) 
            fleeing_up = dy > 0
            step_y = (1.0 if fleeing_up else -1.0) * flee_speed * step
            self.center_y += step_y

           
            if fleeing_up:
                self.angle = 180
            else:
                self.angle = 0

           
            self.update_animation(delta_time, 0, is_action=False, fast=True, anim_type="walk")

           
            if self.center_y > HEIGHT + 60 or self.center_y < -60:
                self.has_fled_with_item = True

    def draw_shadow(self):
        """Draws a soft ground contact shadow beneath the shopper's feet."""
        feet_y = (self.bottom + 6) if self.angle == 180 else (self.center_y - (abs(self.height) / 2) + (10 * abs(self.scale_y)))
        shadow_w = 46.0 * (abs(self.scale_x) / self.base_scale)
        shadow_h = 16.0 * (abs(self.scale_y) / self.base_scale)
        arcade.draw_ellipse_filled(self.center_x, feet_y, shadow_w, shadow_h, (15, 15, 25, 75))

    def draw_overlays(self):
        """Draws carried items, reaction alert bubbles, or stun indicators above shopper."""
        if self.state == STATE_FLEEING_WITH_ITEM and self.carried_texture:
            bob = math.sin(time.time() * 8) * 3
            icon_x = self.center_x
            icon_y = self.top + 18 + bob
            arcade.draw_circle_filled(icon_x, icon_y, 18, (255, 245, 210, 220))
            arcade.draw_circle_outline(icon_x, icon_y, 18, (230, 160, 40, 240), 2)
            arcade.draw_texture_rect(self.carried_texture, arcade.XYWH(icon_x, icon_y, 28, 28))

        elif self.state == STATE_RUSHING_SHELF and getattr(self, "rush_reaction_timer", 0) > 0:
            bob = math.sin(time.time() * 10) * 2
            bx = self.center_x
            by = self.top + 16 + bob
            arcade.draw_circle_filled(bx, by, 14, (255, 235, 60, 240))
            arcade.draw_circle_outline(bx, by, 14, (210, 140, 20, 255), 2)
            arcade.draw_text("!", bx, by - 8, (200, 40, 20), 16, bold=True, anchor_x="center")

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
