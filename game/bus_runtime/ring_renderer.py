"""Draw prepared ring sprites and their runtime effects through the bus painter."""
import json
import math

import arcade
from PIL import Image, ImageDraw, ImageFilter

from .target_rings import PIRATE_WINDUP, SWITCH_DURATION, mix, rotate, smooth


class RingRenderer:
    def __init__(self, assets):
        folder = assets / 'ui/bus-scene/target-rings'
        self.meta = json.loads((folder / 'manifest.json').read_text())
        self.textures = {}
        for kind in ('pirate', 'tesla'):
            with Image.open(folder / self.meta[kind]['file']) as image:
                self.textures[kind] = arcade.Texture(image.convert('RGBA'))
        self.guide_textures = {name: self.make_glow(color) for name, color in (
            ('inside', (62, 255, 151)), ('outside', (255, 81, 88)), ('switch', (149, 217, 255)))}

    @staticmethod
    def make_glow(color):
        mask = Image.new('L', (256, 256))
        ImageDraw.Draw(mask).ellipse((28, 28, 228, 228), outline=230, width=6)
        halo = mask.filter(ImageFilter.GaussianBlur(8))
        image = Image.new('RGBA', mask.size, (*color, 0))
        image.putalpha(halo)
        return arcade.Texture(image)

    def sprite(self, p, kind, x, y, radius, angle=0., sx=1., sy=1., alpha=255):
        size = self.meta['canvas'] * radius / self.meta[kind]['inner_radius']
        p.image(self.textures[kind], x - size * sx / 2, y - size * sy / 2,
                size * sx, size * sy, alpha=max(0, min(255, round(alpha))),
                angle=-math.degrees(angle))

    def outline(self, p, center, rx, ry, color, width=1, dashed=False):
        segments = 64
        points = [(center[0] + math.cos(i * math.tau / segments) * rx,
                   center[1] + math.sin(i * math.tau / segments) * ry) for i in range(segments + 1)]
        for i in range(segments):
            if not dashed or i % 4 < 2:
                p.line(points[i], points[i + 1], color, width)

    def electricity(self, p, ring, x, y, strength, sx=1., sy=1.):
        radius = ring.radius * 1.49
        phase = math.floor(ring.clock * 18)
        for arc in range(4):
            start = arc * math.pi / 2 + ring.clock * .7
            points = []
            for k in range(9):
                angle = start + k * .057
                jitter = math.sin(k * 9.2 + arc * 5 + phase * 2.3) * 5 * strength
                points.append((x + math.cos(angle) * (radius + jitter) * sx,
                               y + math.sin(angle) * (radius + jitter) * sy))
            for a, b in zip(points, points[1:]):
                p.line(a, b, (80, 53, 255, round(65 * strength)), 7)
                p.line(a, b, (110, 153, 255, round(175 * strength)), 3)
                p.line(a, b, (224, 246, 255, round(235 * strength)), 1)

    def warp_effect(self, p, ring):
        t = ring.action_time
        start, goal = ring.start, ring.goal
        if t < .4:
            self.outline(p, goal, ring.radius, ring.radius, (110, 185, 255, 110), 1.4, True)
            for i in range(10):
                angle = i * math.tau / 10 + t
                r = ring.radius * (2.0 - min(1, t / .4) * .8)
                a = (start[0] + math.cos(angle) * r, start[1] + math.sin(angle) * r)
                b = (start[0] + math.cos(angle) * (r - 10), start[1] + math.sin(angle) * (r - 10))
                p.line(a, b, (170, 219, 255, 180), 1.6)
        if .36 <= t < .83:
            progress = smooth((t - .4) / .12)
            alpha = round(225 * min(1, (.83 - t) / .25))
            for n in range(3):
                points = []
                for i in range(30):
                    u = progress * i / 29
                    points.append((mix(start[0], goal[0], u),
                                   mix(start[1], goal[1], u) - math.sin(u * math.pi) * 18 +
                                   math.sin(i * .7 + n) * 2 + (n - 1) * 4))
                for a, b in zip(points, points[1:]):
                    p.line(a, b, (83 + n * 40, 138 + n * 35, 255, alpha), 1.6)
            tip = (mix(start[0], goal[0], progress), mix(start[1], goal[1], progress))
            p.circle(*tip, 4, (227, 250, 255, alpha))
        if .52 <= t < 1.16:
            q = (t - .52) / .64
            alpha = round(195 * (1 - q))
            radius = ring.radius * (.3 + 1.8 * q)
            self.outline(p, (goal[0], goal[1] + ring.radius * .9), radius, radius * .22,
                         (130, 192, 255, alpha), 2.5)
            if q < .35:
                a = round(200 * (1 - q / .35))
                p.line((goal[0] - 28, goal[1]), (goal[0] + 28, goal[1]), (222, 250, 255, a), 3)
                p.line((goal[0], goal[1] - 48), (goal[0], goal[1] + 48), (183, 218, 255, a), 2)

    def cannon_effect(self, p, ring):
        if ring.shot_age < .23:
            age = ring.shot_age
            strength = max(0, 1 - age / .23)
            x, y = ring.muzzle()
            length = (26 + 45 * math.sin(strength * math.pi / 2)) * ring.radius / 92
            shape = [(0, -6), (length * .35, -15), (length * .48, -7),
                     (length, -3), (length * .65, 3), (length * .8, 12),
                     (length * .3, 7), (0, 5)]
            points = [rotate(a, b, ring.angle) for a, b in shape]
            p.polygon([(x + a, y + b) for a, b in points], (255, 120, 30, round(245 * strength)))
            p.polygon([(x + a * .7, y + b * .62) for a, b in points], (255, 237, 133, round(255 * strength)))
        elif ring.shot_age < .65:
            q = (ring.shot_age - .23) / .42
            x, y = ring.muzzle()
            for n in range(3):
                dx, dy = rotate(10 + 20 * q + n * 8, -q * 15 - n * 3, ring.angle)
                p.circle(x + dx, y + dy, 5 + q * 8, (133, 143, 153, round(65 * (1 - q))))
        for ball in ring.projectiles:
            speed = math.hypot(ball.vx, ball.vy)
            tail = (ball.x - ball.vx / speed * 20, ball.y - ball.vy / speed * 20)
            p.line(tail, (ball.x, ball.y), (255, 173, 59, 110), 4)
            p.circle(ball.x, ball.y, 7, (21, 30, 40))
            p.circle(ball.x - 2, ball.y - 2, 2, (136, 149, 165))

    def guidance(self, p, ring, pointer):
        if not ring.tracking_active:
            return
        pose = ring.pose()
        inside, pulse = ring.guidance(pointer)
        texture = self.guide_textures['inside' if inside else 'outside']
        alpha = 230 if inside else round(100 + 155 * pulse)
        spread = 1. if inside else 1 + .035 * pulse
        width = ring.radius * 2.56 * pose.sx * spread
        height = ring.radius * 2.56 * pose.sy * spread
        p.image(texture, pose.x - width / 2, pose.y - height / 2, width, height, alpha=alpha)
        color = (71, 255, 158, 235) if inside else (255, 91, 98, round(130 + 110 * pulse))
        self.outline(p, (pose.x, pose.y), ring.radius * pose.sx, ring.radius * pose.sy,
                     color, 2.2 if inside else 1.8 + 1.1 * pulse)
        if not inside:
            p.text('KEEP MOUSE INSIDE', pose.x, pose.y - ring.radius * 2.05, 2,
                   (255, 189, 188))

    def transition(self, p, ring):
        q = min(1., ring.swap_time / SWITCH_DURATION)
        if not ring.previous_kind or q >= 1:
            return q
        self.sprite(p, ring.previous_kind, ring.x, ring.y, ring.radius,
                    ring.previous_angle, alpha=235 * (1 - smooth(q)))
        radius = ring.radius * (1.1 + .9 * q)
        size = radius * 2.56
        p.image(self.guide_textures['switch'], ring.x - size / 2, ring.y - size / 2,
                size, size, alpha=round(255 * math.sin(q * math.pi)))
        self.outline(p, (ring.x, ring.y), radius, radius,
                     (183, 230, 255, round(195 * (1 - q))), 2)
        return smooth(q)

    def draw(self, p, ring, pointer):
        pose = ring.pose()
        if ring.ghost is not None:
            alpha = round(65 * (1 - min(1, ring.ghost_age / 1.4)))
            self.sprite(p, 'tesla', *ring.ghost, ring.radius, alpha=alpha)
        transition_alpha = self.transition(p, ring)
        self.sprite(p, ring.kind, pose.x, pose.y, ring.radius, ring.angle,
                    pose.sx, pose.sy, 235 * pose.opacity * transition_alpha)
        if ring.kind == 'tesla' and pose.opacity > .15:
            strength = .48
            if ring.action == 'teleport':
                strength = min(1, .55 + ring.action_time * 2)
            self.electricity(p, ring, pose.x, pose.y, strength * pose.opacity, pose.sx, pose.sy)
        if ring.action == 'teleport':
            self.warp_effect(p, ring)
        self.cannon_effect(p, ring)
        self.guidance(p, ring, pointer)
        cue = None
        if ring.action == 'cannon' and ring.action_time < PIRATE_WINDUP:
            cue = 'CANNON!'
        elif ring.action == 'teleport' and ring.action_time < .4:
            cue = 'WARP!'
        if cue:
            p.text(cue, ring.x, ring.y - ring.radius * 1.85, 2, (255, 231, 163))
