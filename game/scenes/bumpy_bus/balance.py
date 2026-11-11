"""Round 1: staying on your feet while the bus brakes, surges and bumps.

Terry's lean runs from -1 (falling toward the driver, on the left of the
screen) to +1 (falling toward the back). Standing is slightly unstable, the
road always rumbles a little, and every few seconds the driver does something
that shoves everyone one way. The player leans against it with A and D.

No window is needed here: given a seeded `random.Random` the whole ride is
deterministic, so it can be tested headless.
"""
import math
import random

RIDE_DURATION = 60.

TIP = 1.1            # leaning makes you lean more, per unit of lean
STEER = 4.2          # how hard the player can push back
DAMPING = 2.2
RECOVER_TIME = 1.4   # seconds on the floor after a stumble, safe from jolts
DANGER = .72         # |lean| past this is shown as about to fall

# kind -> (which way passengers are thrown, cue text). The driver sits on the
# left facing left, so braking throws everyone left and speeding up right.
JOLTS = {
    'brake': (-1, 'BRAKE!'),
    'surge': (1, 'SPEED UP!'),
    'bump': (0, 'BUMPY ROAD!'),   # direction is picked per pothole
}


def mix(a, b, value):
    return a + (b - a) * value


class BusBalance:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.reset()

    def reset(self):
        self.clock = 0.
        self.lean = self.velocity = 0.
        self.recover = 0.          # > 0 while Terry is picking himself up
        self.fell_toward = 0
        self.stumbles = 0
        self.brakes_held = 0       # hard brakes ridden out without falling
        self.jolt = None           # kind being warned about or happening
        self.jolt_time = 0.
        self.jolt_warn = self.jolt_length = 0.
        self.jolt_dir = 0
        self.jolt_peak = 0.
        self.jolt_clean = True
        self.kicks = []            # bump only: times left to kick at
        self.push = 0.             # the bus's force on Terry this frame
        self.bump_shake = 0.
        self.phases = (self.rng.uniform(0, math.tau), self.rng.uniform(0, math.tau))
        self.next_jolt = self.rng.uniform(3.2, 4.4)
        self.previous = None

    @property
    def difficulty(self):
        return min(1., self.clock / RIDE_DURATION)

    @property
    def warning(self):
        """True while a jolt is announced but has not hit yet."""
        return self.jolt is not None and self.jolt_time < self.jolt_warn

    @property
    def active(self):
        return self.jolt is not None and self.jolt_time >= self.jolt_warn

    @property
    def cue(self):
        """(text, direction thrown) for the jolt on the way, else None."""
        if self.jolt is None:
            return None
        return JOLTS[self.jolt][1], self.jolt_dir

    @property
    def danger(self):
        return self.recover <= 0 and abs(self.lean) >= DANGER

    def envelope(self):
        """0..1 strength of a brake or surge: a sharp start, a softer end."""
        if not self.active or self.jolt == 'bump':
            return 0.
        t = self.jolt_time - self.jolt_warn
        return max(0., min(1., t / .12, (self.jolt_length - t) / .3))

    def shake(self):
        """(dx, dy) to draw the bus interior at, in canvas pixels."""
        dx = self.jolt_dir * 11 * self.envelope()
        dy = math.sin(self.clock * 31) * .8
        if self.envelope():
            dx += math.sin(self.clock * 57) * 2.5
        if self.bump_shake > 0:
            dy += math.sin(self.clock * 46) * 9 * self.bump_shake
            dx += math.sin(self.clock * 39) * 3 * self.bump_shake
        return dx, dy

    def start_jolt(self):
        kinds = [kind for kind in JOLTS if kind != self.previous]
        # Brakes are what a bus does most.
        self.jolt = self.rng.choice(kinds + ['brake'] * ('brake' in kinds))
        self.previous = self.jolt
        d = self.difficulty
        self.jolt_time = 0.
        self.jolt_warn = mix(.85, .55, d)
        self.jolt_clean = True
        self.jolt_dir = JOLTS[self.jolt][0] or self.rng.choice((-1, 1))
        if self.jolt == 'bump':
            count = 2 + (d > .4) + (d > .8)
            self.kicks = [index * .42 for index in range(count)]
            self.jolt_length = count * .42 + .2
            self.jolt_peak = mix(.95, 1.3, d)
        else:
            self.jolt_length = self.rng.uniform(1., 1.3)
            self.jolt_peak = mix(2.7, 3.5, d)

    def end_jolt(self):
        if self.jolt == 'brake' and self.jolt_clean:
            self.brakes_held += 1
        self.jolt = None
        self.push = 0.
        d = self.difficulty
        self.next_jolt = self.clock + self.rng.uniform(mix(2.8, 1.7, d), mix(4.2, 2.8, d))

    def update(self, dt, steer):
        """Advance by `dt` with the player leaning -1, 0 or +1.

        Returns the names of what just happened: 'warn', 'brake', 'surge',
        'bump', 'stumble'.
        """
        events = []
        if dt <= 0:
            return events
        self.clock += dt
        self.bump_shake = max(0., self.bump_shake - dt * 2.4)
        if self.recover > 0:
            self.recover -= dt
            self.push = 0.
            if self.recover <= 0:
                self.next_jolt = max(self.next_jolt, self.clock + 1.2)
            return events

        if self.jolt is None and self.clock >= self.next_jolt and self.clock < RIDE_DURATION - 2.5:
            self.start_jolt()
            events.append('warn')
        self.push = 0.
        if self.jolt is not None:
            before = self.jolt_time
            self.jolt_time += dt
            if before < self.jolt_warn <= self.jolt_time and self.jolt != 'bump':
                events.append(self.jolt)
            if self.active:
                t = self.jolt_time - self.jolt_warn
                if self.jolt == 'bump':
                    while self.kicks and t >= self.kicks[0]:
                        self.kicks.pop(0)
                        self.velocity += self.jolt_dir * self.jolt_peak
                        self.jolt_dir = -self.jolt_dir   # potholes rock you back and forth
                        self.bump_shake = 1.
                        events.append('bump')
                else:
                    self.push = self.jolt_dir * self.jolt_peak * self.envelope()
                if t >= self.jolt_length:
                    self.end_jolt()

        rumble_strength = mix(.4, .65, self.difficulty)
        rumble = rumble_strength * (.6 * math.sin(self.clock * 1.7 + self.phases[0])
                                    + .4 * math.sin(self.clock * 2.9 + self.phases[1]))
        acceleration = (TIP * self.lean + self.push + rumble
                        + STEER * max(-1, min(1, steer)) - DAMPING * self.velocity)
        self.velocity += acceleration * dt
        self.lean += self.velocity * dt

        if abs(self.lean) >= 1.:
            self.fell_toward = 1 if self.lean > 0 else -1
            self.stumbles += 1
            self.lean = self.velocity = 0.
            self.recover = RECOVER_TIME
            self.jolt_clean = False
            if self.jolt is not None:
                self.end_jolt()
            events.append('stumble')
        return events
