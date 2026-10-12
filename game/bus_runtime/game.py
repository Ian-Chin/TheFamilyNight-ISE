"""Native Arcade bus gameplay, rendering, input and sound. Fixed 1280x720 layout."""
import json
import math
import random
from pathlib import Path

import arcade
from PIL import Image, ImageDraw
from .game_audio import GameAudio
from .pixel_text import GLYPHS
from ..sprites import Terry

W, H = 1280, 720
INK = (18, 28, 43)
WHITE = (241, 246, 238)
GOLD = (255, 208, 86)
RED = (255, 113, 113)
EVENT_SCENES = ('boy-scares', 'cane-hit', 'worker-steals', 'fart-poison')
EVENT_NAMES = ('MASK KID SCARE', 'GRANNY CANE', 'WORKER STEALS FOOD', 'FART ATTACK')
INGREDIENTS = ('eggs', 'meat', 'cabbage', 'eggplant')
MENU_PANELS = [('PLAY',[(352,224),(653,241),(653,530),(337,548)],(223,42,76)),
               ('SETTING',[(680,246),(899,259),(899,384),(680,399)],(42,168,215)),
               ('EXIT',[(680,424),(899,408),(885,541),(680,555)],(91,97,111))]
# Event spacing is sampled again after every event; animations never overlap.
FIRST_EVENT_DELAY = (2.5, 5.0)
SOLVED_EVENT_DELAY = (2.0, 4.0)
REACTION_EVENT_DELAY = (1.5, 3.0)
KEY_POOL = (arcade.key.F, arcade.key.G, arcade.key.H, arcade.key.I, arcade.key.J,
            arcade.key.K, arcade.key.L, arcade.key.O, arcade.key.U, arcade.key.Y, arcade.key.T)


class Painter:
    """Map fixed top-left art coordinates onto the Arcade stage."""
    def __init__(self, stage):
        self.stage = stage
        self.text_cache = {}

    def image(self, texture, x, y, width, height, alpha=255):
        arcade.draw_texture_rect(texture, self.stage.rect(x, H-y-height, width, height),
                                 pixelated=True, alpha=alpha)

    def fitted(self, texture, x, y, width, height, alpha=255):
        factor = min(width/texture.width,height/texture.height)
        draw_w,draw_h = texture.width*factor,texture.height*factor
        self.image(texture,x+(width-draw_w)/2,y+(height-draw_h)/2,draw_w,draw_h,alpha)

    def ellipse(self, x, y, width, height, color):
        x,y = self.stage.to_screen(x,H-y)
        arcade.draw_ellipse_filled(x,y,width*self.stage.scale,height*self.stage.scale,color)

    def rect(self, x, y, width, height, color):
        if width > 0 and height > 0:
            arcade.draw_rect_filled(self.stage.rect(x, H-y-height, width, height), color)

    def circle(self, x, y, radius, color):
        x, y = self.stage.to_screen(x, H-y)
        arcade.draw_circle_filled(x, y, radius*self.stage.scale, color, num_segments=32)

    def line(self, a, b, color, width=1):
        ax, ay = self.stage.to_screen(a[0], H-a[1])
        bx, by = self.stage.to_screen(b[0], H-b[1])
        arcade.draw_line(ax, ay, bx, by, color, width*self.stage.scale)

    def polygon(self, points, color):
        arcade.draw_polygon_filled([self.stage.to_screen(x, H-y) for x, y in points], color)

    def rounded(self, x, y, width, height, color, radius=12):
        radius = min(radius, width/2, height/2)
        self.rect(x+radius, y, width-2*radius, height, color)
        self.rect(x, y+radius, width, height-2*radius, color)
        for cx in (x+radius, x+width-radius):
            for cy in (y+radius, y+height-radius):
                self.circle(cx, cy, radius, color)

    def text(self, text, cx, cy, scale=2, color=GOLD):
        text = text.upper()
        cache_key = (text, color)
        if cache_key not in self.text_cache:
            image = Image.new('RGBA', (max(1,len(text)*6+1),9))
            draw = ImageDraw.Draw(image)
            pixels = [(1+n*6+x, 1+y) for n,char in enumerate(text)
                      for y,row in enumerate(GLYPHS.get(char,GLYPHS['?']).split('/'))
                      for x,value in enumerate(row) if value == '1']
            for x,y in pixels:
                draw.rectangle((x-1,y-1,x+1,y+1), fill=INK)
            for x,y in pixels:
                draw.point((x,y), fill=color)
            self.text_cache[cache_key] = arcade.Texture(image)
        texture = self.text_cache[cache_key]
        self.image(texture,cx-texture.width*scale/2,cy-texture.height*scale/2,
                   texture.width*scale,texture.height*scale)

    def plaque(self, x, y, width, height):
        self.rounded(x, y, width, height, INK, 10)
        self.rounded(x+3, y+3, width-6, height-6, GOLD, 8)
        self.rounded(x+6, y+6, width-12, height-12, (246, 164, 41), 6)


class Game:
    def __init__(self, assets, stage, rng=None):
        self.root, self.paint = Path(assets), Painter(stage)
        self.rng = rng or random.Random()
        self.held = set()
        self.volume = .55
        self.music_enabled = True
        self.audio = GameAudio(self.root, lambda: self.volume)
        self.bgm = arcade.Sound(str(self.root/'audio/bus-scene/bgm/arcade-rush-bgm.wav'))
        self.music_player = self.bgm.play(volume=self.volume, loop=True)
        self.station_layout = json.loads((self.root/'backgrounds/bus-scene/waiting_bus/pasar-layout.json').read_text())
        self.station = self.load('backgrounds/bus-scene/waiting_bus/pasar-station.png')
        self.arrow = self.load('backgrounds/bus-scene/waiting_bus/start-arrow-down.png', trim=True)
        self.wipe = self.load('sprites/bus-scene/transitions/bus-top-down-right.png', trim=True)
        self.destination = self.load('backgrounds/bus-scene/destination/bbq-background.png')
        ui = self.root/'ui/bus-scene/pixel-v3'
        ui_names = ('warning-kid', 'warning-cane', 'warning-worker', 'warning-fart', 'stage-stop', 'stage-bus', 'stage-arrival', 'icon-music', 'icon-menu', 'failed')
        self.ui = {name: self.load(ui/(name+'.png')) for name in ui_names}
        fresh = self.root/'ui/bus-scene/ingredients-v4'
        self.cards = {name: self.load(fresh/f'card-{name}.png', trim=True) for name in INGREDIENTS}
        self.bread = self.load(fresh/'bread-three-segments.png', trim=True)
        self.bread_states = self.make_bread_states()
        self.station_hero = Terry(0,0)
        self.mirrored_heroes = {}
        self.target_textures = {name: self.load('ui/bus-scene/pixel-circle-'+name+'.png',trim=True)
                                for name in ('green','red')}
        scene_root = self.root/'backgrounds/bus-scene/animations'
        self.manifest = json.loads((scene_root/'manifest.json').read_text())
        self.scenes = {s['id']: s for s in self.manifest['scenes']}
        self.sheets = {s['id']: Image.open(scene_root/s['sheet']).convert('RGBA')
                       for s in self.manifest['scenes']}
        self.frame_id = None
        self.scene_texture = arcade.Texture(self.frame_image('idle', 0))
        self.anim = 0
        self.reset()

    def load(self, path, trim=False):
        path = Path(path)
        if not path.is_absolute():
            path = self.root/path
        with Image.open(path) as image:
            image = image.convert('RGBA')
            bounds = image.getchannel('A').point(lambda value: 255 if value >= 100 else 0).getbbox()
            if trim and bounds:
                image = image.crop(bounds)
            return arcade.Texture(image)

    def make_bread_states(self):
        states = []
        image = self.bread.image
        for active in range(4):
            result = image.copy()
            for index in range(active, 3):
                box = (round(image.width*index/3), 0, round(image.width*(index+1)/3), image.height)
                portion = result.crop(box)
                from PIL import ImageEnhance
                portion = ImageEnhance.Color(portion).enhance(.15)
                portion = ImageEnhance.Brightness(portion).enhance(.25)
                result.paste(portion, box)
            states.append(arcade.Texture(result))
        return states

    def frame_image(self, kind, index):
        fw, fh, cols = self.manifest['frameWidth'], self.manifest['frameHeight'], self.manifest['columns']
        x, y = index%cols*fw, index//cols*fh
        return self.sheets[kind].crop((x,y,x+fw,y+fh))

    def reset(self):
        self.audio.stop()
        self.mode = 'stop'
        self.paused = self.menu_open = False
        self.menu_page = 'main'
        self.held.clear()
        self.elapsed = self.departure_time = self.arrival_time = self.end_time = 0.
        self.arrival_done = False
        self.balance = 3
        self.food = 100
        self.damaged_food = set()
        self.event = None
        self.previous_event = None
        self.event_key = None
        self.event_left = self.presses = 0
        self.required = 4
        self.next_event = self.rng.uniform(*FIRST_EVENT_DELAY)
        self.scene_reaction = None
        self.scene_reaction_time = 0.
        self.station_x = float(self.station_layout['heroStartX'])
        self.station_moving = False
        self.jump_y = self.step_time = 0.
        self.station_hero.jump_timer = None
        self.station_hero.center_y = self.station_hero.ground_y = 0
        self.station_hero.animate(0,False)
        self.facing_left = False
        self.step_side = 0
        self.outside_elapsed = 0.
        self.outside_active = False
        self.set_paused(False)

    def set_paused(self, value):
        self.paused = value
        if value:
            self.audio.pause()
            self.music_player.pause()
        else:
            self.audio.resume()
            self.music_player.play()

    def open_menu(self):
        self.paused_before_menu = self.paused
        self.menu_open = True
        self.menu_page = 'main'
        self.held.clear()
        self.set_paused(True)

    def close_menu(self):
        self.menu_open = False
        self.held.clear()
        self.set_paused(self.paused_before_menu)

    def can_board(self):
        left, right = self.station_layout['boardZone']
        return self.mode == 'stop' and not self.paused and left <= self.station_x <= right and self.jump_y == 0

    def begin_boarding(self):
        if not self.can_board():
            return False
        self.mode = 'departure'
        self.departure_time = 0
        self.held.clear()
        self.audio.play('bus-drive')
        return True

    def key(self, key):
        if key == arcade.key.ESCAPE:
            self.close_menu() if self.menu_open else self.open_menu()
            return
        if self.menu_open:
            return
        if key == arcade.key.R:
            self.reset()
        elif key == arcade.key.B:
            self.music_enabled = not self.music_enabled
            self.music_player.volume = self.volume if self.music_enabled else 0
        elif key in (arcade.key.ENTER, arcade.key.NUM_ENTER) and self.can_board():
            self.begin_boarding()
        elif key == arcade.key.SPACE and self.mode == 'stop' and not self.paused:
            if self.jump_y == 0:
                self.station_hero.start_jump()
                self.audio.play('jump')
        elif key in (arcade.key.SPACE, arcade.key.P) and self.mode in ('ride', 'departure'):
            self.set_paused(not self.paused)
        elif self.mode == 'ride' and not self.paused and self.event is not None and key == self.event_key:
            self.presses += 1
            if self.presses >= self.required:
                self.audio.play('protect')
                self.event = None
                self.next_event = self.elapsed+self.rng.uniform(*SOLVED_EVENT_DELAY)

    def target(self):
        return 640+math.sin(self.elapsed*.95)*95, 550+math.cos(self.elapsed*.8)*15, 92-14*min(self.elapsed/60,1)

    def damaged_food_name(self, index):
        return INGREDIENTS[index]

    def finish(self, success):
        self.audio.stop()
        self.audio.play('bus-horn' if success else 'fail')
        self.mode = 'arrival' if success else 'failed'
        self.arrival_time = self.end_time = 0.
        self.outside_elapsed = 0.
        self.outside_active = False
        self.event = None
        self.scene_reaction = None

    def start_event(self):
        choices = [index for index in range(4) if index != self.previous_event]
        self.event = self.rng.choice(choices)
        self.previous_event = self.event
        previous_key = self.event_key
        self.event_key = self.rng.choice([key for key in KEY_POOL if key != previous_key])
        self.event_left = 7.
        self.presses = 0
        self.required = (4,4,5,5)[self.event]
        self.audio.play('warning')

    def update(self, dt, pointer):
        if self.paused:
            return
        self.anim += dt
        if self.mode == 'stop':
            direction = int(arcade.key.D in self.held)-int(arcade.key.A in self.held)
            old_x = self.station_x
            self.station_x = max(self.station_layout['heroMinX'], min(W-55, old_x+direction*180*dt))
            self.station_moving = self.station_x != old_x
            if direction:
                self.facing_left = direction < 0
            jumping = self.station_hero.jumping
            self.station_hero.animate(dt,self.station_moving)
            self.jump_y = self.station_hero.center_y-self.station_hero.ground_y
            if jumping and not self.station_hero.jumping:
                self.audio.play('land')
            if self.station_moving and self.jump_y == 0:
                self.step_time -= dt
                if self.step_time <= 0:
                    self.audio.play('step-right' if self.step_side%2 else 'step-left')
                    self.step_side += 1
                    self.step_time = .24
            else:
                self.step_time = 0
            return
        if self.mode == 'departure':
            self.departure_time += dt
            if self.departure_time+1e-9 >= 2.8:
                self.mode = 'ride'
            return
        if self.mode == 'arrival':
            self.arrival_time += dt
            if self.arrival_time+1e-9 >= 4:
                self.mode = 'home'
                self.arrival_done = True
            return
        if self.mode == 'failed':
            self.end_time += dt
            if self.end_time+1e-9 >= 2.5:
                self.reset()
            return
        if self.mode != 'ride':
            return
        self.elapsed += dt
        x, y, radius = self.target()
        self.outside_active = math.hypot(pointer[0]-x, pointer[1]-y) > radius
        self.outside_elapsed = self.outside_elapsed+dt if self.outside_active else 0.
        while self.outside_elapsed+1e-9 >= 5:
            self.outside_elapsed = max(0., self.outside_elapsed-5)
            self.balance = max(0, self.balance-1)
            self.audio.play('warning', .65)
        if self.balance == 0:
            self.finish(False)
            return
        if self.scene_reaction:
            self.scene_reaction_time += dt
            duration = sum(self.scenes[self.scene_reaction]['durationsMs'])/1000
            self.audio.update(self.scene_reaction_time, duration)
            if self.scene_reaction_time >= duration:
                self.scene_reaction = None
                self.next_event = self.elapsed+self.rng.uniform(*REACTION_EVENT_DELAY)
        if self.event is None and self.scene_reaction is None and self.elapsed >= self.next_event and self.elapsed < 54:
            self.start_event()
        if self.event is not None:
            self.event_left -= dt
            if self.event_left <= 0:
                self.scene_reaction = EVENT_SCENES[self.event]
                self.scene_reaction_time = 0.
                self.audio.begin(self.scene_reaction)
                self.damaged_food.add(self.rng.randrange(4))
                self.food = max(0, self.food-25)
                self.event = None
                if self.food == 0:
                    self.finish(False)
                    return
        if self.elapsed >= 60:
            self.finish(True)

    def scene_frame(self):
        kind = self.scene_reaction or 'idle'
        time_ms = (self.scene_reaction_time if self.scene_reaction else self.anim)*1000
        durations = self.scenes[kind]['durationsMs']
        if kind == 'idle':
            time_ms %= sum(durations)
        index = len(durations)-1
        for i, duration in enumerate(durations):
            if time_ms < duration:
                index = i
                break
            time_ms -= duration
        return kind, index

    def draw_scene(self):
        frame_id = self.scene_frame()
        if frame_id != self.frame_id:
            self.scene_texture.image = self.frame_image(*frame_id)
            atlas = arcade.get_window().ctx.default_atlas
            if self.frame_id is None:
                atlas.add(self.scene_texture)
            atlas.update_texture_image(self.scene_texture)
            self.frame_id = frame_id
        viewport = self.manifest['viewport']
        self.paint.image(self.scene_texture, viewport['x'], viewport['y'], viewport['width'], viewport['height'])

    def draw_stop(self, arrow=True):
        p = self.paint
        p.image(self.station, 0, 0, W, H)
        texture = self.station_hero.texture
        if self.facing_left:
            if texture not in self.mirrored_heroes:
                self.mirrored_heroes[texture] = texture.flip_left_right()
            texture = self.mirrored_heroes[texture]
        height = 118
        width = texture.width*height/texture.height
        feet = self.station_layout['heroFeetY']
        shrink = 1-.4*min(self.jump_y/70,1)
        p.ellipse(self.station_x,feet-4,width*.58*shrink,width*.58*.34*shrink,(18,14,10,round(150*shrink)))
        p.image(texture,self.station_x-width/2,feet-self.jump_y-height,width,height)
        if arrow:
            ax, ay = self.station_layout['arrowX'], self.station_layout['arrowY']+math.sin(self.anim*4)*6
            width = self.arrow.width*126/self.arrow.height
            p.image(self.arrow, ax-width/2, ay-63, width, 126)
            p.plaque(ax-72, ay-110, 144, 38)
            p.text('ENTER', ax, ay-91, 3, WHITE if self.can_board() else GOLD)

    def draw_wipe(self, progress, arriving=False):
        p = self.paint
        width = self.wipe.width*1000/self.wipe.height
        x = -width+(W+width)*progress
        reveal = max(0, min(W, x+64))
        context = arcade.get_window().ctx
        previous = context.scissor
        stage = p.stage
        try:
            context.scissor = (round(stage.left), round(stage.bottom), round(reveal*stage.scale), round(stage.height))
            p.rect(0, 0, W, H, (9,16,26))
            p.image(self.destination, 0, 0, W, H) if arriving else self.draw_scene()
        finally:
            context.scissor = previous
        p.image(self.wipe, x, (H-1000)/2, width, 1000)

    def draw_hud(self):
        p = self.paint
        p.fitted(self.bread_states[self.balance],32,12,276,52)
        for i, name in enumerate(('kid', 'cane', 'worker', 'fart')):
            p.fitted(self.ui['warning-'+name],42+i*56,76,44,36)
            if self.event == i:
                p.rounded(40+i*56,73,48,4,GOLD,2)
        stage = 0 if self.mode == 'stop' else 2 if self.mode in ('arrival','home') else 1
        progress = .06 if stage == 0 else 1 if stage == 2 else .5+.5*min(1,self.elapsed/60)
        p.rounded(414, 12, 416, 28, INK, 14)
        p.rounded(418, 16, 408, 20, (68,93,100), 10)
        p.rounded(418, 16, max(20, 408*progress), 20, GOLD, 10)
        p.rounded(425, 19, max(2, 392*progress), 4, (255,246,173), 2)
        shine = 418+(self.anim*88)%408
        if shine < 418+408*progress-8:
            p.line((shine,17),(shine-6,34),WHITE,3)
        p.plaque(848, 5, 237, 36)
        p.text(('WAITING BUS','ON THE BUS','ARRIVED')[stage], 966, 23, 2)
        for i, key in enumerate(('stage-stop','stage-bus','stage-arrival')):
            p.image(self.ui[key], 410+i*192, 4, 40, 35)
        for i, name in enumerate(INGREDIENTS):
            x = 500+i*72
            p.fitted(self.cards[name],x,45,64,78)
            p.text(name,x+32,131,1,WHITE)
            if i in self.damaged_food:
                p.line((x+6,55),(x+58,115),RED,4)
                p.line((x+58,55),(x+6,115),RED,4)
        p.image(self.ui['icon-music'],1176,8,26,26)
        p.image(self.ui['icon-menu'],1209,8,26,26)

    def draw_menu(self):
        p = self.paint
        p.rect(0,0,W,H,(4,10,24,204))
        p.rounded(305,148,635,450,(8,25,42),34)
        p.rounded(310,153,625,440,(42,147,184),30)
        for row in range(80):
            t = row/79
            color = tuple(round(a+(b-a)*t) for a,b in zip((98,224,233),(24,106,155)))
            p.rect(340,170+row*5,565,5,color)
        if self.menu_page == 'main':
            for text,points,color in MENU_PANELS:
                p.polygon([(x+8,y+10) for x,y in points],INK)
                p.polygon(points,WHITE)
                cx = sum(x for x,y in points)/4
                cy = sum(y for x,y in points)/4
                for factor,fill in ((.94,INK),(.9,color)):
                    p.polygon([(cx+(x-cx)*factor,cy+(y-cy)*factor) for x,y in points],fill)
                p.text(text,cx,cy,6 if text == 'PLAY' else 4,WHITE)
            p.plaque(489,165,266,43)
            p.text('PAUSED',622,187,3)
        else:
            p.rounded(350,210,580,310,INK,24)
            p.plaque(420,225,440,56)
            p.text('SETTING',640,253,4)
            p.text('MUSIC: '+('ON' if self.music_enabled else 'OFF'),640,340,3)
            p.text('SFX: '+('ON' if self.audio.enabled else 'OFF'),640,375,2)
            p.text('VOLUME',640,400,2)
            p.rounded(460,424,360,18,(68,70,89),9)
            if self.volume:
                p.rounded(460,424,360*self.volume,18,GOLD,9)
            p.text(str(round(self.volume*100)),640,478,2)
            p.text('BACK',640,550,4)

    def click(self, x, y):
        if not self.menu_open:
            if 1202 <= x <= 1238 and y < 42:
                self.open_menu()
            elif 1170 <= x < 1202 and y < 42:
                self.key(arcade.key.B)
            return
        if self.menu_page == 'settings':
            if 430 < x < 850 and 510 <= y <= 565:
                self.menu_page = 'main'
            elif 430 < x < 850 and 310 < y < 365:
                self.music_enabled = not self.music_enabled
            elif 430 < x < 850 and 365 <= y < 390:
                self.audio.enabled = not self.audio.enabled
                if not self.audio.enabled:
                    self.audio.stop(clear=False)
            elif 395 < y < 465:
                self.volume = max(0,min(1,(x-460)/360))
            self.music_player.volume = self.volume if self.music_enabled else 0
        else:
            for name,points,color in MENU_PANELS:
                inside = False
                for index,a in enumerate(points):
                    b = points[index-1]
                    if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
                        inside = not inside
                if inside:
                    if name == 'PLAY':
                        self.close_menu()
                    elif name == 'SETTING':
                        self.menu_page = 'settings'
                    else:
                        self.reset()
                    break

    def draw(self, pointer):
        p = self.paint
        if self.mode == 'stop':
            self.draw_stop()
        elif self.mode == 'departure':
            self.draw_stop(arrow=False)
            self.draw_wipe(min(1,self.departure_time/2.8))
        elif self.mode in ('arrival','home'):
            self.draw_scene()
            if self.mode == 'home':
                p.image(self.destination,0,0,W,H)
            elif self.arrival_time >= 1.2:
                self.draw_wipe(min(1,(self.arrival_time-1.2)/2.8), arriving=True)
        else:
            self.draw_scene()
            if self.mode == 'ride':
                x,y,radius = self.target()
                inside = math.dist(pointer,(x,y)) <= radius
                p.fitted(self.target_textures['green' if inside else 'red'],
                         x-radius,y-radius,radius*2,radius*2,alpha=100)
                if self.outside_active:
                    p.plaque(410,614,460,70)
                    p.text('PLEASE MOVE BACK',580,649,2,WHITE)
                    p.rounded(762,622,98,54,INK,12)
                    p.text(str(max(1,math.ceil(5-self.outside_elapsed)))+'S',811,649,5,WHITE)
            elif self.mode == 'failed':
                p.rect(0,0,W,H,(4,12,20,160))
                failed = self.ui['failed']
                height = failed.height*680/failed.width
                p.image(failed,300,310-height/2,680,height)
        if self.mode != 'home':
            self.draw_hud()
        if self.mode == 'ride' and self.event is not None:
            p.plaque(354,176,572,124)
            p.text('ALERT',640,196,3,WHITE)
            p.text(EVENT_NAMES[self.event],640,228,2,WHITE)
            message = f'PRESS {chr(self.event_key).upper()} - {self.presses}/{self.required} - {max(1,math.ceil(self.event_left))}S'
            p.text(message,640,269,2,WHITE)
        if self.paused and not self.menu_open:
            p.plaque(420,300,440,110)
            p.text('PAUSED',640,330,5,WHITE)
            p.text('PRESS SPACE TO RESUME',640,385,2,WHITE)
        if self.menu_open:
            self.draw_menu()

    def dispose(self):
        self.audio.stop()
        self.music_player.delete()
        for sheet in self.sheets.values():
            sheet.close()
