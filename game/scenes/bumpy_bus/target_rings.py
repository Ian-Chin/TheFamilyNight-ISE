"""Deterministic movement and hit testing for the bus's two tracking rings.

Coordinates use the bus canvas's top-left origin. This module needs no window.
"""
from dataclasses import dataclass
import math
import random


PIRATE_WINDUP = .35
PIRATE_DURATION = 1.55
WARP_DURATION = 1.16
WARP_UNTRACKABLE = (.31, .87)
RIDE_DURATION = 90.
RING_SCALE = 1 / 1.5
SWITCH_DURATION = .7
BOUNDS = (250., 1030., 395., 535.)


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def smooth(value):
    value = clamp(value, 0., 1.)
    return value * value * (3 - 2 * value)


def mix(a, b, value):
    return a + (b - a) * value


def rotate(x, y, angle):
    """Clockwise rotation in the top-left coordinate system."""
    c, s = math.cos(angle), math.sin(angle)
    return x * c - y * s, x * s + y * c


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    age: float = 0.


@dataclass(frozen=True)
class RingPose:
    x: float
    y: float
    sx: float = 1.
    sy: float = 1.
    opacity: float = 1.


class TrackingRing:
    """Cannon recoil, Tesla warp, light transitions, and mouse containment."""

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.reset()

    def reset(self):
        self.clock = 0.
        self.x, self.y = 640., 505.
        self.kind = 'pirate'
        self.previous_kind = None
        self.previous_angle = 0.
        self.swap_time = 1.
        self.angle = 0.
        self.action = None
        self.action_time = 0.
        self.start = self.goal = (self.x, self.y)
        self.start_angle = self.spin = 0.
        self.aim_from = 0.
        self.fired = False
        self.shot_age = 99.
        self.projectiles = []
        self.events = []
        self.ghost = None
        self.ghost_age = 99.
        self.next_action = self.rng.uniform(2., 2.7)
        self.next_switch = self.rng.uniform(10.5, 12.5)
        self.shots_fired = self.warps_completed = self.switches = 0

    @property
    def radius(self):
        return (92 - 14 * min(self.clock / RIDE_DURATION, 1.)) * RING_SCALE

    @property
    def tracking_active(self):
        return not (self.action == 'teleport' and
                    WARP_UNTRACKABLE[0] <= self.action_time < WARP_UNTRACKABLE[1])

    def guidance(self, pointer):
        """A steady green signal inside; a breathing red signal outside."""
        if not self.tracking_active:
            return False, 0.
        inside = self.contains(pointer)
        pulse = 1. if inside else .5 + .5 * math.sin(self.clock * math.tau / 1.6)
        return inside, pulse

    def pose(self):
        if self.action != 'teleport':
            return RingPose(self.x, self.y)
        t = self.action_time
        if t < .26:
            p = smooth(t / .26)
            return RingPose(self.x, self.y, 1 + .12 * p, 1 - .10 * p)
        if t < .4:
            p = smooth((t - .26) / .14)
            return RingPose(self.x, self.y, mix(1.12, .025, p), mix(.9, 1.6, p), 1 - p * .9)
        if t < .52:
            return RingPose(self.x, self.y, .025, 1.6, 0.)
        if t < .87:
            p = (t - .52) / .35
            if p < .45:
                q = smooth(p / .45)
                sx, sy = mix(.08, 1.16, q), mix(1.6, .86, q)
            else:
                q = smooth((p - .45) / .55)
                sx, sy = mix(1.16, 1., q), mix(.86, 1., q)
            return RingPose(self.x, self.y, sx, sy)
        return RingPose(self.x, self.y)

    def contains(self, pointer):
        p = self.pose()
        return (((pointer[0] - p.x) / (self.radius * p.sx)) ** 2 +
                ((pointer[1] - p.y) / (self.radius * p.sy)) ** 2 <= 1.)

    def _bounded(self, x, y):
        return clamp(x, BOUNDS[0], BOUNDS[1]), clamp(y, BOUNDS[2], BOUNDS[3])

    def switch(self):
        self.previous_kind, self.previous_angle = self.kind, self.angle
        self.kind = 'tesla' if self.kind == 'pirate' else 'pirate'
        self.angle = 0.
        self.swap_time = 0.
        self.switches += 1
        self.next_switch = self.clock + self.rng.uniform(10.5, 13.)
        self.next_action = self.clock + 1.25
        self.events.append('ring-charge')

    def start_cannon(self):
        self.action, self.action_time = 'cannon', 0.
        self.start = (self.x, self.y)
        self.aim_from = self.angle
        distance = self.rng.uniform(260, 340)
        dx, dy = rotate(-distance, 0, self.angle)
        self.goal = self._bounded(self.x + dx, self.y + dy + self.rng.uniform(-24, 24))
        if math.dist(self.start, self.goal) < 240:
            self.goal = self._bounded(self.x + (distance if self.x < 640 else -distance),
                                      self.y + self.rng.uniform(-55, 55))
        # Aim during the warning so even a shot near an edge can recoil far
        # enough while its direction still agrees with the cannonball.
        self.start_angle = math.atan2(self.start[1] - self.goal[1], self.start[0] - self.goal[0])
        self.spin = self.rng.choice((-1, 1)) * self.rng.uniform(math.pi * .8, math.pi * 1.3)
        self.fired = False

    def start_teleport(self):
        self.action, self.action_time = 'teleport', 0.
        self.start = (self.x, self.y)
        candidates = [(self.rng.uniform(BOUNDS[0], BOUNDS[1]), self.rng.uniform(BOUNDS[2], BOUNDS[3]))
                      for _ in range(12)]
        suitable = [p for p in candidates if 180 <= math.dist(p, self.start) <= 340]
        self.goal = self.rng.choice(suitable) if suitable else max(candidates, key=lambda p: math.dist(p, self.start))
        self.events.append('ring-charge')

    def muzzle(self):
        # Matches the pivot and bore of the cleaned 640px pirate source sprite.
        dx, dy = rotate(248 / 137 * self.radius, -62 / 137 * self.radius, self.angle)
        return self.x + dx, self.y + dy

    def _shoot(self):
        self.fired = True
        self.angle = self.start_angle
        x, y = self.muzzle()
        vx, vy = rotate(460., 0., self.start_angle)
        self.projectiles.append(Projectile(x, y, vx, vy))
        self.shot_age = 0.
        self.shots_fired += 1
        self.events.append('ring-cannon')

    def update(self, dt):
        if dt <= 0:
            return []
        self.events = []
        self.clock += dt
        self.swap_time += dt
        self.shot_age += dt
        self.ghost_age += dt
        for ball in self.projectiles:
            ball.age += dt
            ball.x += ball.vx * dt
            ball.y += ball.vy * dt
            ball.vy += 36 * dt
        self.projectiles = [ball for ball in self.projectiles
                            if ball.age < 2 and -50 < ball.x < 1330 and -50 < ball.y < 770]
        if self.ghost_age >= 1.4:
            self.ghost = None
        if self.action is None:
            self.x, self.y = self._bounded(self.x + math.cos(self.clock * .72) * dt * 21,
                                          self.y + math.sin(self.clock * .9) * dt * 9)
            if self.clock >= self.next_switch:
                self.switch()
            elif self.clock >= self.next_action:
                self.start_cannon() if self.kind == 'pirate' else self.start_teleport()
            return self.events
        previous = self.action_time
        self.action_time += dt
        t = self.action_time
        if self.action == 'cannon':
            if not self.fired and t >= PIRATE_WINDUP:
                self._shoot()
            if t < PIRATE_WINDUP:
                delta = (self.start_angle - self.aim_from + math.pi) % math.tau - math.pi
                self.angle = self.aim_from + delta * smooth(t / PIRATE_WINDUP)
            else:
                p = clamp((t - PIRATE_WINDUP) / (PIRATE_DURATION - PIRATE_WINDUP), 0., 1.)
                travel = 1 - (1 - p) ** 2
                self.x = mix(self.start[0], self.goal[0], travel)
                self.y = mix(self.start[1], self.goal[1], travel)
                self.angle = self.start_angle + self.spin * smooth(p)
            if t >= PIRATE_DURATION:
                self.action = None
                self.angle %= math.tau
                self.next_action = self.clock + self.rng.uniform(2.2, 3.5)
        else:
            if previous < .52 <= t:
                self.x, self.y = self.goal
                self.ghost, self.ghost_age = self.start, 0.
                self.warps_completed += 1
                self.events.append('ring-warp')
            if t >= WARP_DURATION:
                self.action = None
                self.next_action = self.clock + self.rng.uniform(2.7, 4.)
        return self.events
