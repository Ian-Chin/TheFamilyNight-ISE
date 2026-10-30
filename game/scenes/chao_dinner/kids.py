"""The kids-at-the-table mini game in the Chao dinner.

Jess and Tom keep hopping off their stools to run about the garden. The
player clicks a runaway and drags them back: the kid throws a tantrum the
whole way, every so often yanking the cursor aside, while an escape bar over
their head fills. Dropped on the glowing box over their stool, they sit back
down; dropped anywhere else, or carried until the bar is full, they wriggle
free and run off again. After a little while seated they get up and run.

The game lasts a fixed time and is scored on how much of it the kids spent
in their seats.

Positions are canvas units throughout, feet first: a runner's `x, y` is the
point between their shoes.
"""

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
    KIDS_GAME_TIME, KIDS_HINT, KIDS_HUD_H, KIDS_HUD_NOTE_SIZE, KIDS_HUD_TOP,
    KIDS_HUD_W, KIDS_TIMER_SIZE, KID_BAR_DANGER, KID_BAR_GAP, KID_BAR_H, KID_BAR_SAFE,
    KID_BAR_W, KID_BOUNDS, KID_CAUGHT_FRAME, KID_CLEARANCE, KID_ESCAPE_COOLDOWN,
    KID_ESCAPE_TIME, KID_GRID, KID_HEIGHT, KID_HIT_PAD, KID_RUN_AREA, KID_RUN_FRAME,
    KID_RUN_SPEED, KID_SEATED_MAX, KID_SEATED_MIN, KID_SEAT_BOX, KID_SEAT_BOX_RISE,
    KID_SEAT_COLOR, KID_SEAT_READY, KID_SHAKE, KID_TUG, KID_TUG_EVERY, KID_TUG_TIME,
    KID_LIFT, KID_SPARKLES, KID_TRAIL, KID_TRAIL_EVERY,
)
from ...core.effects import WalkDust

def _inside(x, y, box, pad=0):
    left, right, bottom, top = box
    return left - pad <= x <= right + pad and bottom - pad <= y <= top + pad


def _mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _spring(clock, amount):
    """A wobble that starts at `amount` and rings down to 0, for squash
    and stretch."""
    return amount * math.exp(-clock * 7) * math.cos(clock * 24)


# --- finding a way round the scenery ----------------------------------------
# The garden is laid over a grid of KID_GRID cells; a cell is open if a kid's
# feet could stand at its middle, clear of every obstacle by KID_CLEARANCE.

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
    """The closest open cell, for a kid let go on top of the scenery."""
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
    """True if a kid can run straight from a to b without touching scenery."""
    steps = max(1, int(math.dist(a, b) / (KID_GRID / 2)))
    return all(
        not blocked(a[0] + (b[0] - a[0]) * i / steps,
                    a[1] + (b[1] - a[1]) * i / steps)
        for i in range(1, steps + 1)
    )


def _grid_route(first, last):
    """Cells from first to last by A*, or None if there is no way through."""
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
                # No cutting across the corner of something solid.
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
    """Waypoints from start to goal round the scenery, start left out.

    A* on the grid finds the way; it is then cut down to the corners that
    matter, so the kid runs in straight lines rather than cell to cell.
    """
    cells = _grid_route(_nearest_open(_cell(*start)), _nearest_open(_cell(*goal)))
    if cells is None:
        return [goal]
    points = [_middle(cell) for cell in cells]
    if not blocked(*goal):
        points[-1] = goal
    path = []
    if blocked(*start):
        # Dropped on the scenery: hop off it to the nearest open ground first.
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
    """Somewhere open in the garden for a runaway to head for."""
    left, right, bottom, top = KID_RUN_AREA
    for _ in range(40):
        x, y = random.uniform(left, right), random.uniform(bottom, top)
        if not blocked(x, y):
            return x, y
    return (left + right) / 2, (bottom + top) / 2


class Runner:
    """One of the kids: sat at the table, loose in the garden, or carried.

    States: "seated" (drawn by their Diner), "running" and "carried".
    """

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
        self.heading = (0.0, 0.0)   # last direction run in, for the dust
        self.state = "seated"
        self.path = []
        self.facing = 1
        self.frame_clock = 0.0
        self.seated_for = 0.0
        self.escape = 0.0      # seconds carried; they get free at KID_ESCAPE_TIME
        self.cooldown = 0.0    # seconds until they can be grabbed again
        # Squash and stretch: seconds since the last jolt, and how big it was
        # (+ stretches tall, - squashes flat).
        self.jolt_clock = 9.0
        self.jolt = 0.0
        # Afterimages left behind while carried: (x, y, texture, facing).
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
        """Out of their seat, running about or being carried."""
        return self.state != "seated"

    @property
    def over_seat(self):
        """Carried over the drop box on their stool."""
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
        """Back on their feet: a squash, for the jolt of landing."""
        self.jolt, self.jolt_clock = -0.25, 0.0

    def break_free(self):
        """Wriggled out of the player's grip, or dropped short of the seat."""
        self.state = "running"
        self.cooldown = KID_ESCAPE_COOLDOWN
        self.path = find_path((self.x, self.y), random_spot())
        self.land()

    def contains(self, x, y):
        half_w = abs(self.sprite.width) / 2 + KID_HIT_PAD
        return (abs(x - self.x) <= half_w
                and self.y - KID_HIT_PAD <= y <= self.y + KID_HEIGHT + KID_HIT_PAD)

    def walk(self, delta_time, speed):
        """Step along the path; True once it has run out."""
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
                # The art runs to the right, so it is mirrored to run left.
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
        elif self.state == "running":
            if self.walk(delta_time, KID_RUN_SPEED):
                self.path = find_path((self.x, self.y), random_spot())
        elif self.state == "carried":
            self.escape += delta_time
        self.jolt_clock += delta_time
        # While carried, drop an afterimage every so often; once let go the
        # trail runs out one image at a time.
        self.trail_clock += delta_time
        if self.trail_clock >= KID_TRAIL_EVERY:
            self.trail_clock = 0.0
            if self.state == "carried":
                self.trail.append((self.x, self.y, self.sprite.texture, self.facing))
            elif self.trail:
                self.trail.popleft()
        # Dust kicked up behind their feet while they run, as with Terry.
        running = self.state == "running"
        self.dust.update(delta_time, running, self.x, self.y, *self.heading)

    def draw(self):
        # Dust still in the air settles even once they are sat back down.
        self.dust.draw()
        if self.state == "seated":
            return
        if self.state == "running":
            frames, frame_time = self.run_frames, KID_RUN_FRAME
        else:
            frames, frame_time = self.caught_frames, KID_CAUGHT_FRAME
        self.draw_shadow()
        self.draw_trail()
        sprite = self.sprite
        sprite.texture = frames[int(self.frame_clock / frame_time) % len(frames)]
        # Stretched tall when grabbed, squashed flat on landing; the area
        # stays about the same, and the feet stay put.
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

    def draw_shadow(self):
        """A soft oval on the ground: under the feet while running, and
        smaller, fainter and further down while held up off it."""
        carried = self.state == "carried"
        lift = KID_LIFT + 4 * math.sin(self.frame_clock * 9) if carried else 0
        width = KID_HEIGHT * (0.42 if carried else 0.55)
        alpha = 60 if carried else 95
        arcade.draw_ellipse_filled(self.x, self.y - lift, width, width * 0.32,
                                   (0, 0, 0, alpha))

    def draw_trail(self):
        """Fading, blue-tinted copies along the path the kid was dragged."""
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
        """How close the kid is to wriggling free, over their head."""
        share = min(self.escape / KID_ESCAPE_TIME, 1.0)
        left = self.x - KID_BAR_W / 2
        bottom = self.y + KID_HEIGHT + KID_BAR_GAP
        arcade.draw_lbwh_rectangle_filled(
            left - 2, bottom - 2, KID_BAR_W + 4, KID_BAR_H + 4, (12, 10, 16, 220),
        )
        color = _mix(KID_BAR_SAFE, KID_BAR_DANGER, share)
        # Close to breaking free, the bar flashes.
        if share > 0.75 and int(self.frame_clock * 10) % 2:
            color = (255, 240, 220)
        if share > 0:
            arcade.draw_lbwh_rectangle_filled(
                left, bottom, KID_BAR_W * share, KID_BAR_H, color,
            )

    def draw_seat_box(self, clock):
        """The glowing drop box over the stool, while they are carried."""
        left, right, bottom, top = self.seat_box
        ready = self.over_seat
        color = KID_SEAT_READY if ready else KID_SEAT_COLOR
        pulse = 0.5 + 0.5 * math.sin(clock * 6)
        fill = (90 if ready else 40 + 30 * pulse)
        arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, (*color, round(fill)))
        arcade.draw_lrbt_rectangle_outline(
            left, right, bottom, top, (*color, round(170 + 85 * pulse)), 3,
        )
        # Corner ticks, so it reads as a target rather than a plain frame.
        tick = 12
        for x, sx in ((left, 1), (right, -1)):
            for y, sy in ((bottom, 1), (top, -1)):
                arcade.draw_line(x, y, x + sx * tick, y, color, 5)
                arcade.draw_line(x, y, x, y + sy * tick, color, 5)


class KidsGame:
    """Runs the mini game: the clock, the runaways, the carrying and the score.

    `pointer` is where the player's cursor is in canvas units while carrying.
    A tug moves it; the view reads `pointer_moved` each frame and puts the
    real mouse cursor there to match.
    """

    def __init__(self, diners):
        """`diners` maps "Tom" and "Jess" to their Diner at the table."""
        self.runners = [Runner(name, diners[name]) for name in ("Jess", "Tom")]
        self.clock = 0.0
        self.sparkles = []   # [x, y, vx, vy, age, life, color, size]
        self.events = []     # "escape" and "seated", for the view to react to
        self.reset()

    def reset(self):
        self.time_left = KIDS_GAME_TIME
        self.elapsed = 0.0
        self.seated_time = 0.0
        self.active = False
        self.carried = None
        self.grip = (0.0, 0.0)      # cursor to the kid's feet when picked up
        self.pointer = (0.0, 0.0)
        self.pointer_moved = False
        self.tug_in = 0.0
        self.tug = None             # (dx, dy, seconds left) of a tug under way
        self.escapes = 0            # wriggled free this round, for Wriggle Room
        for runner in self.runners:
            runner.sit(0.0)

    def start(self):
        """Both kids are off and running; the clock starts."""
        self.reset()
        self.active = True
        for runner in self.runners:
            runner.run_off()

    @property
    def seated(self):
        return sum(not runner.loose for runner in self.runners)

    @property
    def share(self):
        """Share of the time so far that the kids were in their seats."""
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
            self.time_left -= step
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
        """A fountain of gold and white bits off the stool, and a ring."""
        y += KID_HEIGHT * 0.6
        for _ in range(KID_SPARKLES):
            angle = random.uniform(0.15, math.pi - 0.15)
            speed = random.uniform(140, 320)
            color = random.choice(((255, 222, 120), (255, 246, 214), (255, 190, 90)))
            self.sparkles.append([x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                                  0.0, random.uniform(0.45, 0.8), color,
                                  random.choice((3, 4, 5))])
        self.sparkles.append([x, y, 0.0, 0.0, 0.0, 0.45, None, 0])   # the ring

    def draw_effects(self):
        """The sparkles from a kid put back in their seat."""
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
        """The carried kid yanks the cursor about and may get free."""
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
        """Put the cursor at canvas (x, y), and the carried kid under it."""
        left, right, bottom, top = KID_BOUNDS
        x = min(max(x, left), right)
        y = min(max(y, bottom), top)
        self.pointer = (x, y)
        if self.carried is not None:
            self.carried.x = x - self.grip[0]
            self.carried.y = y - self.grip[1]

    def stop(self):
        """Time is up: everyone back in their seat and staying there."""
        self.active = False
        self.carried = None
        self.tug = None
        for runner in self.runners:
            runner.sit(0.0)

    def press(self, x, y):
        """Pick up the runaway under the cursor, if there is one."""
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
                audio.play("ui_click")
                return True
        return False

    def drag(self, x, y):
        if self.carried is not None:
            self.move_pointer(x, y)

    def release(self):
        """Drop the carried kid: into their seat if over it, else they run."""
        kid, self.carried = self.carried, None
        self.tug = None
        if kid is None:
            return
        if kid.over_seat:
            kid.sit(random.uniform(KID_SEATED_MIN, KID_SEATED_MAX))
            audio.play("ingredient_get")
            self.events.append("seated")
            self.sparkle(*kid.seat)
        else:
            kid.break_free()

    def draw_targets(self):
        """The drop box for the kid being carried, under everyone."""
        if self.carried is not None:
            self.carried.draw_seat_box(self.clock)


class KidsHud:
    """The mini game's clock and seat count, on a plank at the top middle,
    with the how-to line along the bottom of the screen."""

    def __init__(self):
        self.stage = None
        self.shown = None   # (seconds, seated, total) last written to the text

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
        hurry = seconds <= 10
        arcade.draw_texture_rect(
            self.plank_hurry if hurry else self.plank,
            stage.rect(WIDTH / 2 - KIDS_HUD_W / 2 - PLANK_PAD,
                       KIDS_HUD_TOP - KIDS_HUD_H - PLANK_PAD,
                       KIDS_HUD_W + 2 * PLANK_PAD, KIDS_HUD_H + 2 * PLANK_PAD),
        )
        self.timer[1].color = TEXT_HOVER if hurry else TEXT_BRIGHT
        for text in (*self.timer, self.note, *self.hint):
            text.draw()
