import random
import arcade
from ...config import HEIGHT
from .common import PLAY_LEFT, PLAY_RIGHT


def get_separated_x(existing_sprites, min_gap=110, attempts=12):
    """Generates an X coordinate spaced away from existing entities."""
    top_sprites = [s for s in existing_sprites if s.top > HEIGHT - 180]
    for gap in (min_gap, min_gap * 0.75, min_gap * 0.5):
        for _ in range(attempts // 3):
            candidate_x = random.randint(PLAY_LEFT + 40, PLAY_RIGHT - 40)
            if all(abs(candidate_x - s.center_x) >= gap for s in top_sprites):
                return candidate_x
    return random.randint(PLAY_LEFT + 40, PLAY_RIGHT - 40)


class SnatcherSprite(arcade.Sprite):
    """Falling hazard that loops drop frames, chases Terry in wave 3, and gets knocked out."""

    def __init__(self, fall_textures, grab_textures, initial_x=None):
        super().__init__(fall_textures[0], scale=0.42)
        self.fall_textures = fall_textures
        self.grab_textures = grab_textures
        self.frame_timer = 0.0
        self.cur_frame = 0
        self.is_grabbing = False
        self.knocked_out = False
        self.spin_vel = 0.0
        self.reset_pos(custom_x=initial_x)

    def reset_pos(self, custom_x=None, existing_list=None):
        self.knocked_out = False
        self.angle = 0
        if custom_x is not None:
            self.center_x = custom_x
        elif existing_list is not None:
            self.center_x = get_separated_x(existing_list)
        else:
            self.center_x = random.randint(PLAY_LEFT + 40, PLAY_RIGHT - 40)

        self.center_y = HEIGHT + random.randint(30, 240)
        self.change_x = 0.0
        self.change_y = -random.uniform(4.5, 6.5)
        self.is_grabbing = False
        self.cur_frame = 0

    def trigger_knockout(self, player_x):
        self.knocked_out = True
        # Fling outward away from player
        self.change_x = 9.0 if self.center_x >= player_x else -9.0
        self.change_y = random.uniform(6.0, 10.0)
        self.spin_vel = 38.0 if self.change_x > 0 else -38.0

    def update_behavior(self, delta_time, player_y, player_x, is_wave_3):
        if self.knocked_out:
            # Gravity and rapid spin
            self.angle += self.spin_vel
            self.change_y -= 18.0 * delta_time
            self.center_x += self.change_x
            self.center_y += self.change_y
            return

        # Wave 3 tracking behavior: home horizontally towards Terry
        if is_wave_3:
            dx = player_x - self.center_x
            if abs(dx) > 15:
                self.change_x = 2.8 if dx > 0 else -2.8
            else:
                self.change_x = 0
        else:
            self.change_x = 0

        self.center_x += self.change_x
        self.center_y += self.change_y

        # Proximity for grab pose
        self.frame_timer += delta_time
        dist_y = self.center_y - player_y
        dist_x = abs(self.center_x - player_x)
        self.is_grabbing = (0 < dist_y < 140) and (dist_x < 90)

        active_list = self.grab_textures if self.is_grabbing else self.fall_textures
        if self.frame_timer >= 0.10:
            self.frame_timer = 0.0
            self.cur_frame = (self.cur_frame + 1) % len(active_list)
            self.texture = active_list[self.cur_frame]


class IngredientDrop(arcade.Sprite):
    """Collectible food items dropped on the field."""

    def __init__(self, item_name, texture, initial_x=None):
        target_size = 90.0
        calc_scale = target_size / max(texture.width, texture.height)
        super().__init__(texture, scale=calc_scale)
        self.item_name = item_name
        self.reset_pos(custom_x=initial_x)

    def reset_pos(self, custom_x=None, existing_list=None):
        if custom_x is not None:
            self.center_x = custom_x
        elif existing_list is not None:
            self.center_x = get_separated_x(existing_list)
        else:
            self.center_x = random.randint(PLAY_LEFT + 30, PLAY_RIGHT - 30)

        self.center_y = HEIGHT + random.randint(30, 180)
        # Reduced drop speed
        self.change_y = -random.uniform(2.8, 4.2)