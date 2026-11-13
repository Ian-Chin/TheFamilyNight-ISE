import collections
import functools
import heapq
import math
import random

import arcade

from ...core import achievements, audio, textures
from ...config import (
    CHAO_OBSTACLES, CHAO_STONE_AREAS, PLANK_PAD, TEXT_BRIGHT, TEXT_DIM, TEXT_HOVER,
    TEXT_SHADOW, WIDTH,
)
from .config import (
    KIDS_GAME_TIME, KIDS_HINT, KIDS_HURRY, KIDS_HUD_H, KIDS_HUD_NOTE_SIZE, KIDS_HUD_TOP,
    KIDS_HUD_W, KIDS_TIMER_SIZE, KID_BAR_DANGER, KID_BAR_GAP, KID_BAR_H, KID_BAR_SAFE,
    KID_BAR_W, KID_BOUNDS, KID_CAUGHT_FRAME, KID_CLEARANCE, KID_ESCAPE_COOLDOWN,
    KID_ESCAPE_TIME, KID_GRID, KID_HEIGHT, KID_HIT_PAD, KID_RUN_AREA, KID_RUN_FRAME,
    KID_RUN_SPEED, KID_SEATED_MAX, KID_SEATED_MIN, KID_SEAT_BOX, KID_SEAT_BOX_RISE,
    KID_SEAT_COLOR, KID_SEAT_READY, KID_SHAKE, KID_TUG, KID_TUG_EVERY, KID_TUG_TIME,
    KID_SPARKLES, KID_TRAIL, KID_TRAIL_EVERY,
)
from ...core.effects import WalkDust

def _inside(x, y, box, pad=0):
    left, right, bottom, top = box
    return left - pad <= x <= right + pad and bottom - pad <= y <= top + pad


def _mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _spring(clock, amount):
    return amount * math.exp(-clock * 7) * math.cos(clock * 24)


def blocked(x, y):
    left, right, bottom, top = KID_BOUNDS
    if not (left <= x <= right and bottom <= y <= top):
        return True
    return any(_inside(x, y, box, KID_CLEARANCE) for box in CHAO_OBSTACLES)


def _cell(x, y):
    return int(x // KID_GRID), int(y // KID_GRID)


def _middle(cell):
    return (cell[0] + 0.5) * KID_GRID, (cell[1] + 0.5) * KID_GRID


@functools.lru_cache(maxsize=None)
def _open(cell):
    return not blocked(*_middle(cell))


def _nearest_open(cell):
    if _open(cell):
        return cell
    for radius in range(1, 40):
        ring = [(cell[0] + dx, cell[1] + dy)
                for dx in range(-radius, radius + 1)
                for dy in range(-radius, radius + 1)
                if max(abs(dx), abs(dy)) == radius]
        free = [c for c in ring if _open(c)]
        if free:
            return min(free, key=lambda c: math.dist(c, cell))
    return cell


def clear_line(a, b):
    steps = max(1, int(math.dist(a, b) / (KID_GRID / 2)))
    return all(
        not blocked(a[0] + (b[0] - a[0]) * i / steps,
                    a[1] + (b[1] - a[1]) * i / steps)
        for i in range(1, steps + 1)
    )


def _grid_route(first, last):
    came = {first: None}
    cost = {first: 0.0}
    queue = [(0.0, first)]
    while queue:
        _, cell = heapq.heappop(queue)
        if cell == last:
            break
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                step = (cell[0] + dx, cell[1] + dy)
                if not (dx or dy) or not _open(step):
                    continue
                if dx and dy and not (_open((cell[0] + dx, cell[1]))
                                      and _open((cell[0], cell[1] + dy))):
                    continue
                new = cost[cell] + math.hypot(dx, dy)
                if new < cost.get(step, math.inf):
                    cost[step] = new
                    came[step] = cell
                    heapq.heappush(queue, (new + math.dist(step, last), step))
    if last not in came:
        return None
    cells = []
    while last is not None:
        cells.append(last)
        last = came[last]
    return cells[::-1]


def find_path(start, goal):
    cells = _grid_route(_nearest_open(_cell(*start)), _nearest_open(_cell(*goal)))
    if cells is None:
        return [goal]
    points = [_middle(cell) for cell in cells]
    if not blocked(*goal):
        points[-1] = goal
    path = []
    if blocked(*start):
        here = points[0]
        path.append(here)
    else:
        here = start
    index = 0
    while index < len(points) - 1:
        reach = len(points) - 1
        while reach > index + 1 and not clear_line(here, points[reach]):
            reach -= 1
        here = points[reach]
        path.append(here)
        index = reach
    return path or [points[-1]]


def random_spot():
    left, right, bottom, top = KID_RUN_AREA
    for _ in range(40):
        x, y = random.uniform(left, right), random.uniform(bottom, top)
        if not blocked(x, y):
            return x, y
    return (left + right) / 2, (bottom + top) / 2


class Runner:
    def __init__(self, name, diner):
        self.name = name
        self.diner = diner
        self.run_frames, self.caught_frames = textures.kid_frames(name)
        texture = self.run_frames[0]
        self.scale = KID_HEIGHT / texture.height
        self.sprite = arcade.Sprite(texture, scale=self.scale)
        self.sprites = arcade.SpriteList()
        self.sprites.append(self.sprite)

        stool_x, stool_y = diner.stool
        self.seat = (stool_x, stool_y - 6)
        width, height = KID_SEAT_BOX
        middle_y = stool_y + KID_SEAT_BOX_RISE
        self.seat_box = (stool_x - width / 2, stool_x + width / 2,
                         middle_y - height / 2, middle_y + height / 2)
        self.x, self.y = self.seat
        self.dust = WalkDust(CHAO_STONE_AREAS)
        self.heading = (0.0, 0.0)
        self.state = "seated"
        self.path = []
        self.facing = 1
        self.frame_clock = 0.0
        self.seated_for = 0.0
        self.escape = 0.0
        self.cooldown = 0.0
        self.jolt_clock = 9.0
        self.jolt = 0.0
        self.trail = collections.deque(maxlen=KID_TRAIL)
        self.trail_clock = 0.0
        self.ghosts = arcade.SpriteList()
        for _ in range(KID_TRAIL):
            ghost = arcade.Sprite(texture, scale=self.scale)
            ghost.color = (150, 190, 255)
            self.ghosts.append(ghost)

    @property
    def ground_y(self):
        return self.y

    @property
    def loose(self):
        return self.state != "seated"

    @property
    def over_seat(self):
        return _inside(self.x, self.y + KID_HEIGHT / 3, self.seat_box)

    @property
    def grabbable(self):
        return self.state == "running" and self.cooldown <= 0

    def sit(self, wait):
        self.state = "seated"
        self.x, self.y = self.seat
        self.path = []
        self.seated_for = wait
        self.diner.visible = True

    def run_off(self):
        self.state = "running"
        self.x, self.y = self.seat
        self.path = find_path(self.seat, random_spot())
        self.diner.visible = False

    def pick_up(self):
        self.state = "carried"
        self.escape = 0.0
        self.jolt, self.jolt_clock = 0.22, 0.0

    def land(self):
        self.jolt, self.jolt_clock = -0.25, 0.0

    def break_free(self):
        self.state = "running"
        self.cooldown = KID_ESCAPE_COOLDOWN
        self.path = find_path((self.x, self.y), random_spot())
        self.land()

    def contains(self, x, y):
        half_w = abs(self.sprite.width) / 2 + KID_HIT_PAD
        return (abs(x - self.x) <= half_w
                and self.y - KID_HIT_PAD <= y <= self.y + KID_HEIGHT + KID_HIT_PAD)

    def walk(self, delta_time, speed):
        step = speed * delta_time
        while self.path and step > 0:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            distance = math.hypot(dx, dy)
            if distance <= step:
                self.x, self.y = tx, ty
                self.path.pop(0)
                step -= distance
                continue
            self.x += dx / distance * step
            self.y += dy / distance * step
            self.heading = (dx / distance, dy / distance)
            if abs(dx) > 1:
                self.facing = 1 if dx > 0 else -1
            step = 0
        return not self.path

    def update(self, delta_time, active):
        self.frame_clock += delta_time
        self.cooldown = max(0.0, self.cooldown - delta_time)
        if self.state == "seated":
            if active:
                self.seated_for -= delta_time
                if self.seated_for <= 0:
                    self.run_off()
                    audio.play(random.choice(("chao_laugh", "chao_laugh_b")),
                               speed=random.uniform(0.95, 1.1))
        elif self.state == "running":
            if self.walk(delta_time, KID_RUN_SPEED):
                self.path = find_path((self.x, self.y), random_spot())
        elif self.state == "carried":
            self.escape += delta_time
        self.jolt_clock += delta_time
        self.trail_clock += delta_time
        if self.trail_clock >= KID_TRAIL_EVERY:
            self.trail_clock = 0.0
            if self.state == "carried":
                self.trail.append((self.x, self.y, self.sprite.texture, self.facing))
            elif self.trail:
                self.trail.popleft()
        running = self.state == "running"
        self.dust.update(delta_time, running, self.x, self.y, *self.heading)

    def draw(self):
        self.dust.draw()
        if self.state == "seated":
            return
        if self.state == "running":
            frames, frame_time = self.run_frames, KID_RUN_FRAME
        else:
            frames, frame_time = self.caught_frames, KID_CAUGHT_FRAME
        self.draw_trail()
        sprite = self.sprite
        sprite.texture = frames[int(self.frame_clock / frame_time) % len(frames)]
        stretch = _spring(self.jolt_clock, self.jolt)
        sprite.scale_x = self.scale * self.facing * (1 - stretch * 0.6)
        sprite.scale_y = self.scale * (1 + stretch)
        shake = 0.0
        if self.state == "carried":
            shake = KID_SHAKE * math.sin(self.frame_clock * 60)
        sprite.center_x = self.x + shake
        sprite.center_y = self.y + KID_HEIGHT * (1 + stretch) / 2
        self.sprites.draw(pixelated=True)
        if self.state == "carried":
            self.draw_bar()

    def draw_trail(self):
        count = len(self.trail)
        for index, ghost in enumerate(self.ghosts):
            if index >= count:
                ghost.visible = False
                continue
            x, y, texture, facing = self.trail[index]
            ghost.visible = True
            ghost.texture = texture
            ghost.scale_x = self.scale * facing
            ghost.scale_y = self.scale
            ghost.center_x, ghost.center_y = x, y + KID_HEIGHT / 2
            ghost.alpha = round(110 * (index + 1) / (count + 1))
        self.ghosts.draw(pixelated=True)

    def draw_bar(self):
        share = min(self.escape / KID_ESCAPE_TIME, 1.0)
        left = self.x - KID_BAR_W / 2
        bottom = self.y + KID_HEIGHT + KID_BAR_GAP
        arcade.draw_lbwh_rectangle_filled(
            left - 2, bottom - 2, KID_BAR_W + 4, KID_BAR_H + 4, (12, 10, 16, 220),
        )
        color = _mix(KID_BAR_SAFE, KID_BAR_DANGER, share)
        if share > 0.75 and int(self.frame_clock * 10) % 2:
            color = (255, 240, 220)
        if share > 0:
            arcade.draw_lbwh_rectangle_filled(
                left, bottom, KID_BAR_W * share, KID_BAR_H, color,
            )

    def draw_seat_box(self, clock):
        left, right, bottom, top = self.seat_box
        ready = self.over_seat
        color = KID_SEAT_READY if ready else KID_SEAT_COLOR
        pulse = 0.5 + 0.5 * math.sin(clock * 6)
        fill = (90 if ready else 40 + 30 * pulse)
        arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, (*color, round(fill)))
        arcade.draw_lrbt_rectangle_outline(
            left, right, bottom, top, (*color, round(170 + 85 * pulse)), 3,
        )
        tick = 12
        for x, sx in ((left, 1), (right, -1)):
            for y, sy in ((bottom, 1), (top, -1)):
                arcade.draw_line(x, y, x + sx * tick, y, color, 5)
                arcade.draw_line(x, y, x, y + sy * tick, color, 5)


class KidsGame:
    def __init__(self, diners):
        self.runners = [Runner(name, diners[name]) for name in ("Jess", "Tom")]
        self.clock = 0.0
        self.sparkles = []
        self.events = []
        self.reset()

    def reset(self):
        self.time_left = KIDS_GAME_TIME
        self.elapsed = 0.0
        self.seated_time = 0.0
        self.active = False
        self.carried = None
        self.grip = (0.0, 0.0)
        self.pointer = (0.0, 0.0)
        self.pointer_moved = False
        self.tug_in = 0.0
        self.tug = None
        self.escapes = 0
        for runner in self.runners:
            runner.sit(0.0)

    def start(self):
        self.reset()
        self.active = True
        for runner in self.runners:
            runner.run_off()

    @property
    def seated(self):
        return sum(not runner.loose for runner in self.runners)

    @property
    def share(self):
        if self.elapsed <= 0:
            return 1.0
        return self.seated_time / self.elapsed

    @property
    def finished(self):
        return self.active and self.time_left <= 0

    def update(self, delta_time):
        self.clock += delta_time
        self.pointer_moved = False
        if self.active:
            step = min(delta_time, self.time_left)
            shown = math.ceil(self.time_left)
            self.time_left -= step
            if 0 < math.ceil(self.time_left) < shown <= KIDS_HURRY + 1:
                audio.play("chao_tick", speed=1.0 if shown % 2 else 0.8)
            self.elapsed += step
            self.seated_time += step * self.seated / len(self.runners)
        for runner in self.runners:
            runner.update(delta_time, self.active)
        if self.carried is not None:
            self.struggle(delta_time)
        for bit in self.sparkles:
            bit[0] += bit[2] * delta_time
            bit[1] += bit[3] * delta_time
            bit[3] -= 520 * delta_time
            bit[4] += delta_time
        self.sparkles = [bit for bit in self.sparkles if bit[4] < bit[5]]

    def take_events(self):
        events, self.events = self.events, []
        return events

    def sparkle(self, x, y):
        y += KID_HEIGHT * 0.6
        for _ in range(KID_SPARKLES):
            angle = random.uniform(0.15, math.pi - 0.15)
            speed = random.uniform(140, 320)
            color = random.choice(((255, 222, 120), (255, 246, 214), (255, 190, 90)))
            self.sparkles.append([x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                                  0.0, random.uniform(0.45, 0.8), color,
                                  random.choice((3, 4, 5))])
        self.sparkles.append([x, y, 0.0, 0.0, 0.0, 0.45, None, 0])

    def draw_effects(self):
        for x, y, _, _, age, life, color, size in self.sparkles:
            t = age / life
            if color is None:
                arcade.draw_circle_outline(
                    x, y, 10 + 70 * t, (255, 230, 150, round(220 * (1 - t))),
                    max(1, 5 * (1 - t)))
                continue
            half = size * (1 - 0.5 * t) / 2
            arcade.draw_lrbt_rectangle_filled(
                x - half, x + half, y - half, y + half,
                (*color, round(255 * (1 - t * t))))

    def struggle(self, delta_time):
        kid = self.carried
        if kid.escape >= KID_ESCAPE_TIME:
            self.carried = None
            kid.break_free()
            audio.play("get_snatched")
            self.escapes += 1
            self.events.append("escape")
            if self.escapes >= 3:
                achievements.unlock("egg_escape")
            return
        self.tug_in -= delta_time
        if self.tug is None and self.tug_in <= 0:
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(*KID_TUG)
            self.tug = (math.cos(angle) * distance, math.sin(angle) * distance,
                        KID_TUG_TIME)
            self.tug_in = random.uniform(*KID_TUG_EVERY)
        if self.tug is not None:
            dx, dy, left = self.tug
            step = min(delta_time, left) / KID_TUG_TIME
            self.move_pointer(self.pointer[0] + dx * step,
                              self.pointer[1] + dy * step)
            self.pointer_moved = True
            left -= delta_time
            self.tug = (dx, dy, left) if left > 0 else None

    def move_pointer(self, x, y):
        left, right, bottom, top = KID_BOUNDS
        x = min(max(x, left), right)
        y = min(max(y, bottom), top)
        self.pointer = (x, y)
        if self.carried is not None:
            self.carried.x = x - self.grip[0]
            self.carried.y = y - self.grip[1]

    def stop(self):
        self.active = False
        self.carried = None
        self.tug = None
        for runner in self.runners:
            runner.sit(0.0)

    def press(self, x, y):
        if not self.active or self.carried is not None:
            return False
        for runner in sorted(self.runners, key=lambda r: r.y):
            if runner.grabbable and runner.contains(x, y):
                runner.pick_up()
                self.carried = runner
                self.grip = (x - runner.x, y - runner.y)
                self.pointer = (x, y)
                self.tug = None
                self.tug_in = random.uniform(*KID_TUG_EVERY)
                audio.play("chao_grab")
                return True
        return False

    def drag(self, x, y):
        if self.carried is not None:
            self.move_pointer(x, y)

    def release(self):
        kid, self.carried = self.carried, None
        self.tug = None
        if kid is None:
            return
        if kid.over_seat:
            kid.sit(random.uniform(KID_SEATED_MIN, KID_SEATED_MAX))
            audio.play("chao_seated")
            self.events.append("seated")
            self.sparkle(*kid.seat)
        else:
            kid.break_free()
            audio.play("chao_whoops")

    def draw_targets(self):
        if self.carried is not None:
            self.carried.draw_seat_box(self.clock)


class KidsHud:
    def __init__(self):
        self.stage = None
        self.shown = None

    def layout(self, stage):
        self.stage = stage
        self.shown = None
        pad = stage.px(PLANK_PAD)
        self.plank = textures.plank(
            stage.px(KIDS_HUD_W), stage.px(KIDS_HUD_H), pad, False,
        )
        self.plank_hurry = textures.plank(
            stage.px(KIDS_HUD_W), stage.px(KIDS_HUD_H), pad, True,
        )
        middle = WIDTH / 2
        center = dict(anchor_x="center", anchor_y="center")
        top = KIDS_HUD_TOP
        self.timer = [
            stage.text("", middle + offset, top - 28 - offset, shade,
                       KIDS_TIMER_SIZE, bold=True, **center)
            for offset, shade in ((2, TEXT_SHADOW), (0, TEXT_BRIGHT))
        ]
        self.note = stage.text("", middle, top - 58, TEXT_DIM,
                               KIDS_HUD_NOTE_SIZE, **center)
        self.hint = [
            stage.text(KIDS_HINT, middle + offset, 26 - offset, shade, 14,
                       bold=True, **center)
            for offset, shade in ((1.5, TEXT_SHADOW), (0, TEXT_HOVER))
        ]

    def draw(self, time_left, seated, total):
        stage = self.stage
        seconds = math.ceil(time_left)
        if self.shown != (seconds, seated, total):
            self.shown = (seconds, seated, total)
            clock = f"{seconds // 60}:{seconds % 60:02d}"
            for text in self.timer:
                text.text = clock
            self.note.text = f"Kids in their seats: {seated}/{total}"
        hurry = seconds <= KIDS_HURRY
        arcade.draw_texture_rect(
            self.plank_hurry if hurry else self.plank,
            stage.rect(WIDTH / 2 - KIDS_HUD_W / 2 - PLANK_PAD,
                       KIDS_HUD_TOP - KIDS_HUD_H - PLANK_PAD,
                       KIDS_HUD_W + 2 * PLANK_PAD, KIDS_HUD_H + 2 * PLANK_PAD),
        )
        self.timer[1].color = TEXT_HOVER if hurry else TEXT_BRIGHT
        for text in (*self.timer, self.note, *self.hint):
            text.draw()
