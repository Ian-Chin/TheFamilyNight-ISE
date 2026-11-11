"""Round 2 without the pictures: the bus, the traffic and what hits what.

The bus drives down a three-lane road and gains on everything ahead of it.
The player only steers. Positions are on the road, not on screen: `x` runs
from -1 to +1 across it and `z` is the distance ahead of the camera, as
described in config.py. highway.py draws whatever this says is there.

Needs no window, and a seeded `random.Random` makes a run repeatable.
"""

import random

from .config import (
    AIM_AT_BUS, BUS_REACH, BUS_SPEED, BUS_WIDTH, BUS_Z, CAR_PAINTS, CLEAR_TIME,
    CLOSING_SPEED, FAR_Z, HALF_LENGTH, HIGHWAY_DURATION, HIT_FORGIVE, HIT_GRACE,
    LANE_CHANGE, LANE_X, NEAR_GAP, SAFE_MARGIN, SPAWN_GAP, STEER_SPEED,
    TRUCK_PAINTS, VAN_PAINTS, VEHICLE_KINDS,
)

PAINTS = {"car": CAR_PAINTS, "van": VAN_PAINTS, "truck": TRUCK_PAINTS}
GONE_Z = BUS_Z - HALF_LENGTH - 0.3    # overtaken and out of sight


def mix(a, b, share):
    return a + (b - a) * share


class Vehicle:
    def __init__(self, kind, paint, lane, x, closing):
        self.kind = kind
        self.paint = paint
        self.lane = lane
        self.x = x
        self.z = FAR_Z
        self.closing = closing     # road units per second the bus gains on it
        self.width = VEHICLE_KINDS[kind][0]
        self.hit = False
        self.grazed = False
        self.counted = False       # already behind the bus
        self.drift = 0.0           # knocked sideways, across the road per second
        self.spin = 0.0            # degrees
        self.fade = 1.0
        self.sprite = None         # highway.py hangs its sprite here


class Traffic:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.reset()

    def reset(self):
        self.clock = 0.0
        self.distance = 0.0        # road units driven, for the scrolling ground
        self.x = LANE_X[1]
        self.vx = 0.0
        self.vehicles = []
        self.grace = 0.0
        self.shake = 0.0
        self.slowed = 0.0          # 1 right after a crash, easing back to 0
        self.safe = False          # set once the round is won: nothing can hit
        self.crashes = self.near_misses = self.overtakes = 0
        self.next_spawn = 1.0

    @property
    def difficulty(self):
        return min(1.0, self.clock / HIGHWAY_DURATION)

    @property
    def pace(self):
        """How much of its speed the bus has, knocked back by a crash."""
        return 1.0 - 0.5 * self.slowed

    @property
    def speed(self):
        return mix(*BUS_SPEED, self.difficulty) * self.pace

    @property
    def done(self):
        return self.clock >= HIGHWAY_DURATION

    def bus_lane(self):
        return min(range(len(LANE_X)), key=lambda lane: abs(LANE_X[lane] - self.x))

    # --- Traffic ------------------------------------------------------------

    def window(self, vehicle):
        """(from, to) in seconds from now that `vehicle` is level with the bus."""
        return ((vehicle.z - BUS_Z - HALF_LENGTH) / vehicle.closing,
                (vehicle.z - BUS_Z + HALF_LENGTH) / vehicle.closing)

    def escape_exists(self, extra):
        """With `extra` added, can the bus still thread through everything?

        Time is cut into steps of one lane change. Each step the bus may stay
        put or move one lane over, and a lane counts as shut while a vehicle
        is level with the bus (give or take SAFE_MARGIN). If some lane can be
        reached at every step, starting from where the bus is, there is a way.
        """
        windows = [(v.lane, *self.window(v)) for v in self.vehicles if not v.hit]
        windows.append((extra.lane, *self.window(extra)))
        horizon = max(end for _, _, end in windows) + SAFE_MARGIN

        def free(lane, start):
            return not any(
                other == lane and a - SAFE_MARGIN < start + LANE_CHANGE
                and b + SAFE_MARGIN > start for other, a, b in windows
            )

        reach = {self.bus_lane()}
        clock = 0.0
        while clock < horizon:
            clock += LANE_CHANGE
            open_lanes = {lane for lane in range(len(LANE_X)) if free(lane, clock)}
            # Sliding over needs both lanes clear for that step.
            reach = {
                lane for lane in open_lanes
                if lane in reach or (open_lanes & reach & {lane - 1, lane + 1})
            }
            if not reach:
                return False
        return True

    def make_vehicle(self, lane):
        roll, kind = self.rng.random(), "car"
        for name, (_, share) in VEHICLE_KINDS.items():
            if roll < share:
                kind = name
                break
            roll -= share
        closing = self.rng.uniform(*CLOSING_SPEED) * (1 + 0.35 * self.difficulty)
        # Never gaining faster than the one nearer in the same lane, so the
        # two cannot run into each other.
        nearer = [v.closing for v in self.vehicles if v.lane == lane and not v.hit]
        if nearer:
            closing = min(closing, min(nearer))
        return Vehicle(
            kind, self.rng.randrange(len(PAINTS[kind])), lane,
            LANE_X[lane] + self.rng.uniform(-0.04, 0.04), closing,
        )

    def spawn(self):
        """Add one vehicle, but only where it leaves the bus a way through."""
        lanes = list(range(len(LANE_X)))
        self.rng.shuffle(lanes)
        if self.rng.random() < AIM_AT_BUS:
            # Usually straight ahead of the bus, so sitting still is never safe.
            here = self.bus_lane()
            lanes.remove(here)
            lanes.insert(0, here)
        for lane in lanes:
            vehicle = self.make_vehicle(lane)
            # Room behind the last one in this lane.
            if any(v.lane == lane and v.z > FAR_Z - 4 * HALF_LENGTH for v in self.vehicles):
                continue
            if not self.escape_exists(vehicle):
                continue
            self.vehicles.append(vehicle)
            return True
        return False

    # --- Frame --------------------------------------------------------------

    def update(self, delta_time, steer, traffic=True):
        """Advance by `delta_time` with the player steering -1, 0 or +1.

        Returns what just happened: "crash", "near", "overtake".
        """
        events = []
        if delta_time <= 0:
            return events
        self.clock += delta_time
        self.distance += self.speed * delta_time
        self.grace = max(0.0, self.grace - delta_time)
        self.shake = max(0.0, self.shake - delta_time * 2.2)
        self.slowed = max(0.0, self.slowed - delta_time / 1.5)

        self.vx += (steer * STEER_SPEED - self.vx) * min(1.0, delta_time * 11)
        self.x = max(-BUS_REACH, min(BUS_REACH, self.x + self.vx * delta_time))
        if abs(self.x) == BUS_REACH:
            self.vx = 0.0

        if (traffic and self.clock >= self.next_spawn
                and self.clock < HIGHWAY_DURATION - CLEAR_TIME):
            if self.spawn():
                gap = mix(*SPAWN_GAP, self.difficulty)
                self.next_spawn = self.clock + gap * self.rng.uniform(0.8, 1.2)
            else:
                self.next_spawn = self.clock + 0.2

        for vehicle in self.vehicles:
            vehicle.z -= vehicle.closing * self.pace * delta_time
            if vehicle.hit:
                vehicle.x += vehicle.drift * delta_time
                vehicle.spin += 420 * delta_time * (1 if vehicle.drift > 0 else -1)
                vehicle.fade = max(0.0, vehicle.fade - delta_time * 1.6)
                continue
            if vehicle.z < BUS_Z - HALF_LENGTH:
                # Dropping behind: it slips out of view rather than swelling
                # up over the bottom of the screen.
                vehicle.fade = max(0.0, (vehicle.z - GONE_Z) / (BUS_Z - HALF_LENGTH - GONE_Z))
                if not vehicle.counted:
                    vehicle.counted = True
                    self.overtakes += 1
                    events.append("overtake")
                    if vehicle.grazed:
                        self.near_misses += 1
                        events.append("near")
                continue
            if abs(vehicle.z - BUS_Z) >= HALF_LENGTH or self.grace > 0 or self.safe:
                continue
            gap = abs(vehicle.x - self.x) - (vehicle.width + BUS_WIDTH) / 2
            if gap < -HIT_FORGIVE:
                vehicle.hit = True
                vehicle.drift = 2.4 if vehicle.x >= self.x else -2.4
                self.crashes += 1
                self.grace = HIT_GRACE
                self.shake = self.slowed = 1.0
                events.append("crash")
            elif gap < NEAR_GAP:
                vehicle.grazed = True

        self.vehicles = [v for v in self.vehicles if v.fade > 0 and v.z > GONE_Z]
        return events
