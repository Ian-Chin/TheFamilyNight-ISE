"""Full-screen post-processing: a scene drawn off-screen, then graded.

A view draws its world between `begin()` and `end(...)`. Instead of going
straight to the window, the world lands in an off-screen framebuffer; `end`
then draws that framebuffer to the window through one fragment shader that
can, per frame:

  - light it: a cool ambient multiplier with warm point lights added in
    (a light map worked out per pixel, no light texture needed),
  - drain the colour out of everything but a circle (selective colour),
  - tone it sepia and smear it sideways (a fast-forward look),
  - close it down to an iris around a point,
  - darken the corners (vignette), flush them red (a hit pulse),
  - jitter it (screen shake) and add film grain.

`blur_background()` is a second, smaller pass for depth of field: whatever
was drawn between `begin_background()` and it is copied into the scene
softened by a disc blur, so the sharp sprites drawn after sit in focus.

Everything here is skipped in performance mode, where `enabled` is False,
`begin` and `end` do nothing and the view draws straight to the window as
it always did; views keep their plain fades as the fallback.
"""

import array
import math

import arcade
from arcade.gl import geometry

from .settings import graphics

MAX_LIGHTS = 12

VERTEX = """
#version 330
in vec2 in_vert;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    v_uv = in_uv;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

GRADE = """
#version 330
uniform sampler2D scene;
uniform vec2 resolution;
uniform float time;

uniform int light_count;
uniform vec4 lights[%(max)d];        // x, y, radius (pixels), strength
uniform vec3 light_colors[%(max)d];
uniform vec3 ambient;                // 1, 1, 1 leaves the scene as drawn

uniform float desaturate;
uniform vec3 focus;                  // x, y, radius kept in colour
uniform float sepia;
uniform float smear;
uniform float darken;
uniform vec3 iris;                   // x, y, radius; radius < 0 is off
uniform float vignette;
uniform float pulse;
uniform vec2 shake;
uniform float grain;

in vec2 v_uv;
out vec4 frag;

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
    vec2 px = v_uv * resolution;
    vec2 uv = (px - shake) / resolution;

    vec3 color;
    if (smear > 0.0) {
        // Streaks along x, longer to the left, like frames rushing past.
        color = vec3(0.0);
        float total = 0.0;
        for (int i = 0; i < 9; i++) {
            float w = 1.0 - float(i) / 9.0;
            color += texture(scene, uv - vec2(float(i) * smear * 6.0 / resolution.x, 0.0)).rgb * w;
            total += w;
        }
        color /= total;
    } else {
        color = texture(scene, uv).rgb;
    }

    // Light map: the ambient multiplier, plus each light's falloff.
    vec3 light = ambient;
    for (int i = 0; i < light_count; i++) {
        float d = distance(px, lights[i].xy) / lights[i].z;
        float f = clamp(1.0 - d, 0.0, 1.0);
        light += light_colors[i] * (f * f) * lights[i].w;
    }
    color *= light;

    if (desaturate > 0.0) {
        float gray = dot(color, vec3(0.299, 0.587, 0.114));
        float keep = 1.0 - smoothstep(focus.z * 0.45, focus.z, distance(px, focus.xy));
        float amount = desaturate * (1.0 - keep);
        vec3 mono = vec3(clamp((gray - 0.5) * 1.25 + 0.5, 0.0, 1.0));
        color = mix(color, mono * vec3(0.92, 0.95, 1.05), amount);
    }

    if (sepia > 0.0) {
        vec3 toned = vec3(dot(color, vec3(0.393, 0.769, 0.189)),
                          dot(color, vec3(0.349, 0.686, 0.168)),
                          dot(color, vec3(0.272, 0.534, 0.131)));
        color = mix(color, toned, sepia);
    }
    color *= 1.0 - darken;

    float edge = smoothstep(0.35, 1.0, distance(v_uv, vec2(0.5)) * 1.414);
    color *= 1.0 - vignette * edge;
    color = mix(color, vec3(0.75, 0.04, 0.05), pulse * edge);

    color += (hash(px + fract(time) * 97.0) - 0.5) * grain;

    if (iris.z >= 0.0) {
        color *= 1.0 - smoothstep(iris.z, iris.z + 2.0, distance(px, iris.xy));
    }
    frag = vec4(color, 1.0);
}
""" % {"max": MAX_LIGHTS}

BLUR = """
#version 330
uniform sampler2D scene;
uniform vec2 resolution;
uniform float radius;     // pixels
uniform vec4 spot;        // x, y, sharp within, fully blurred past (pixels)
in vec2 v_uv;
out vec4 frag;

void main() {
    // Two rings of eight taps round the centre, weighted toward it: a
    // cheap disc blur, soft enough for an out-of-focus garden. The blur
    // grows with distance from the spot in focus, like a lens's depth of
    // field, so what is there stays sharp.
    float d = distance(v_uv * resolution, spot.xy);
    float blur = radius * smoothstep(spot.z, spot.w, d);
    vec4 sum = texture(scene, v_uv) * 2.0;
    float total = 2.0;
    for (int ring = 1; ring <= 2; ring++) {
        float r = blur * float(ring) / 2.0;
        float w = ring == 1 ? 1.0 : 0.6;
        for (int i = 0; i < 8; i++) {
            float a = float(i) * 0.7853982 + float(ring) * 0.3926991;
            sum += texture(scene, v_uv + vec2(cos(a), sin(a)) * r / resolution) * w;
            total += w;
        }
    }
    frag = sum / total;
}
"""

# The shader's defaults: no light map, no grade.
NEUTRAL = {
    "ambient": (1.0, 1.0, 1.0), "desaturate": 0.0, "focus": (0.0, 0.0, 1.0),
    "sepia": 0.0, "smear": 0.0, "darken": 0.0, "iris": (0.0, 0.0, -1.0),
    "vignette": 0.0, "pulse": 0.0, "shake": (0.0, 0.0), "grain": 0.0,
}


class PostFX:
    def __init__(self, window):
        self.window = window
        self.ctx = window.ctx
        self.grade = self.ctx.program(vertex_shader=VERTEX, fragment_shader=GRADE)
        self.blur = self.ctx.program(vertex_shader=VERTEX, fragment_shader=BLUR)
        self.quad = geometry.quad_2d_fs()
        self.size = None
        self.drawing = False

    @property
    def enabled(self):
        return graphics.animated

    def _fit(self):
        """(Re)build the framebuffers whenever the window changes size."""
        size = self.window.get_framebuffer_size()
        if size == self.size:
            return
        self.size = size
        self.scene = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture(size, components=4)])
        self.back = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture(size, components=4)])

    def begin_background(self):
        """Draw the background into its own buffer, to blur in a moment."""
        if not self.enabled:
            return
        self._fit()
        self.back.use()
        self.back.clear()

    def blur_background(self, radius, spot=(0.0, 0.0, 0.0, 0.0)):
        """The background, softened by up to `radius` pixels, under the scene.

        `spot` is (x, y, sharp within, fully blurred past) in window pixels;
        the default blurs everywhere.
        """
        if not self.enabled:
            return
        self.begin()
        self._full(self.scene)
        self.back.color_attachments[0].use(0)
        self.blur["resolution"] = self.size
        self.blur["radius"] = float(radius)
        self.blur["spot"] = spot
        self.quad.render(self.blur)

    def begin(self):
        """Start the world; it lands off-screen until `end`."""
        if not self.enabled or self.drawing:
            return
        self._fit()
        self.drawing = True
        self.scene.use()
        self.scene.clear()

    def end(self, time=0.0, lights=(), **settings):
        """Put the world on the window, graded by `settings` (see NEUTRAL).

        `time` is any running clock in seconds; it moves the film grain.
        `lights` are (x, y, radius, strength, (r, g, b)) in window pixels.
        """
        if not self.drawing:
            return
        self.drawing = False
        screen = self.ctx.screen
        screen.use()
        self._full(screen)
        program = self.grade
        program["resolution"] = self.size
        program["time"] = time
        lights = list(lights)[:MAX_LIGHTS]
        positions = array.array("f", [0.0] * 4 * MAX_LIGHTS)
        colors = array.array("f", [0.0] * 3 * MAX_LIGHTS)
        for i, (x, y, radius, strength, color) in enumerate(lights):
            positions[4 * i:4 * i + 4] = array.array("f", (x, y, max(radius, 1.0), strength))
            colors[3 * i:3 * i + 3] = array.array("f", color)
        program["light_count"] = len(lights)
        program["lights"] = tuple(positions)
        program["light_colors"] = tuple(colors)
        for name, value in {**NEUTRAL, **settings}.items():
            program[name] = value
        self.scene.color_attachments[0].use(0)
        self.quad.render(program)
        # Views go on to draw their interface with the window's own camera.
        self.window.default_camera.use()

    def _full(self, framebuffer):
        """Cover the whole buffer, whatever viewport a camera left on it."""
        framebuffer.viewport = (0, 0, *self.size)


def for_window(window):
    """The window's one PostFX, built the first time a view asks for it."""
    fx = getattr(window, "postfx", None)
    if fx is None:
        fx = window.postfx = PostFX(window)
    return fx


def flicker(clock, seed, amount):
    """A gentle uneven wobble around 1, for firelight."""
    wave = (math.sin(clock * 7.3 + seed) * 0.5 + math.sin(clock * 13.1 + seed * 2.7) * 0.3
            + math.sin(clock * 2.1 + seed * 0.6) * 0.2)
    return 1.0 + amount * wave
