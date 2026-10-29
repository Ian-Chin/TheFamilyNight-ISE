"""Behavior checks for movement, teleport fairness, and restart state."""
import math
import random
import unittest

from game.scenes.bumpy_bus.target_rings import (
    BOUNDS, PIRATE_WINDUP, RIDE_DURATION, RING_SCALE, TrackingRing,
)


def advance(ring, seconds, step=1 / 120):
    remaining = seconds
    while remaining > 1e-9:
        dt = min(step, remaining)
        ring.update(dt)
        remaining -= dt


class RingBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.ring = TrackingRing(random.Random(27))
        self.ring.next_action = self.ring.next_switch = 999

    def test_cannon_fires_before_spin_and_recoil(self):
        ring = self.ring
        start = ring.x, ring.y
        ring.start_cannon()
        advance(ring, PIRATE_WINDUP - .02)
        self.assertEqual(ring.shots_fired, 0)
        self.assertEqual((ring.x, ring.y), start)
        advance(ring, .04)
        self.assertEqual(ring.shots_fired, 1)
        self.assertEqual(len(ring.projectiles), 1)
        self.assertLess(ring.x, start[0])
        advance(ring, 1.3)
        self.assertIsNone(ring.action)
        self.assertGreaterEqual(math.dist(start, (ring.x, ring.y)), 240)
        self.assertGreater(abs(ring.angle), .5)

    def test_teleport_has_invisible_grace_and_real_destination(self):
        ring = self.ring
        ring.kind = 'tesla'
        ring.start_teleport()
        start, goal = ring.start, ring.goal
        self.assertGreaterEqual(math.dist(start, goal), 180)
        advance(ring, .44)
        self.assertEqual(ring.pose().opacity, 0)
        self.assertFalse(ring.tracking_active)
        self.assertEqual((ring.x, ring.y), start)
        advance(ring, .13)
        self.assertEqual((ring.x, ring.y), goal)
        self.assertEqual(ring.ghost, start)
        self.assertEqual(ring.warps_completed, 1)
        self.assertFalse(ring.tracking_active)
        advance(ring, .34)
        self.assertTrue(ring.tracking_active)
        self.assertTrue(ring.contains(goal))
        self.assertFalse(ring.contains(start))

    def test_hit_area_matches_stretched_ellipse(self):
        ring = self.ring
        ring.kind = 'tesla'
        ring.start_teleport()
        advance(ring, .29)
        pose = ring.pose()
        self.assertTrue(ring.contains((pose.x, pose.y)))
        self.assertFalse(ring.contains((pose.x + ring.radius * pose.sx * 1.01, pose.y)))
        self.assertTrue(ring.contains((pose.x, pose.y + ring.radius * pose.sy * .99)))

    def test_guidance_breathes_outside_and_is_steady_green_inside(self):
        ring = self.ring
        outside = (-999, -999)
        first = ring.guidance(outside)
        self.assertFalse(first[0])
        advance(ring, .4)
        self.assertNotAlmostEqual(first[1], ring.guidance(outside)[1])
        self.assertEqual(ring.guidance((ring.x, ring.y)), (True, 1.))
        advance(ring, .7)
        self.assertEqual(ring.guidance((ring.x, ring.y)), (True, 1.))
        ring.kind = 'tesla'
        ring.start_teleport()
        advance(ring, .44)
        self.assertEqual(ring.guidance(outside), (False, 0.))

    def test_both_styles_have_the_requested_smaller_hit_area(self):
        for kind in ('pirate', 'tesla'):
            self.ring.kind = kind
            self.ring.clock = 0
            self.assertAlmostEqual(self.ring.radius, 92 / 1.5)
            self.ring.clock = RIDE_DURATION
            self.assertAlmostEqual(self.ring.radius, 78 * RING_SCALE)

    def test_far_recoil_is_preserved_near_edges_and_for_vertical_shots(self):
        ring = self.ring
        for x in (BOUNDS[0], 640, BOUNDS[1]):
            for angle in (0, math.pi / 2, math.pi, math.pi * 1.5):
                ring.x, ring.y, ring.angle = x, 470, angle
                ring.start_cannon()
                self.assertGreaterEqual(math.dist(ring.start, ring.goal), 240)
                delta = (ring.goal[0] - ring.x, ring.goal[1] - ring.y)
                recoil = (-math.cos(ring.start_angle), -math.sin(ring.start_angle))
                self.assertGreater(delta[0] * recoil[0] + delta[1] * recoil[1], 0)

    def test_projectiles_and_ghosts_expire(self):
        ring = self.ring
        ring.start_cannon()
        advance(ring, .4)
        self.assertTrue(ring.projectiles)
        advance(ring, 2.2)
        self.assertFalse(ring.projectiles)
        ring.kind = 'tesla'
        ring.start_teleport()
        advance(ring, .6)
        self.assertIsNotNone(ring.ghost)
        advance(ring, 1.5)
        self.assertIsNone(ring.ghost)

    def test_full_ride_uses_both_styles_and_light_switches_on_canvas(self):
        ring = TrackingRing(random.Random(39))
        seen, events = set(), set()
        for _ in range(int(RIDE_DURATION * 60)):
            events.update(ring.update(1 / 60))
            seen.add(ring.kind)
            self.assertTrue(BOUNDS[0] <= ring.x <= BOUNDS[1])
            self.assertTrue(BOUNDS[2] <= ring.y <= BOUNDS[3])
        self.assertEqual(seen, {'pirate', 'tesla'})
        self.assertNotIn('ring-burn', events)
        self.assertIn('ring-charge', events)
        self.assertGreater(ring.shots_fired, 1)
        self.assertGreater(ring.warps_completed, 1)
        self.assertGreaterEqual(ring.switches, 3)

    def test_restart_clears_previous_effects_and_timers(self):
        ring = self.ring
        ring.kind = 'tesla'
        ring.start_teleport()
        advance(ring, .65)
        ring.reset()
        self.assertEqual(ring.kind, 'pirate')
        self.assertEqual(ring.clock, 0)
        self.assertEqual(ring.angle, 0)
        self.assertIsNone(ring.action)
        self.assertIsNone(ring.ghost)
        self.assertFalse(ring.projectiles)

    def test_zero_update_keeps_the_animation_still(self):
        before = self.ring.pose(), self.ring.clock, self.ring.swap_time
        self.ring.update(0)
        self.assertEqual(before, (self.ring.pose(), self.ring.clock, self.ring.swap_time))


if __name__ == '__main__':
    unittest.main()
