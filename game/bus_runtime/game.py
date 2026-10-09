"""Bus Balance — run with Python 3.12 and pygame-ce. All art is local."""
import math
import os
import json
from pathlib import Path
import sys
from statistics import median

ROOT = Path(os.environ.get('IMAGING_GAME_ASSET_ROOT', Path(__file__).resolve().parents[2] / 'assets'))
PREVIEW_ROOT = Path(os.environ.get('IMAGING_GAME_PREVIEW_DIR', ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent / '.packages'))
if '--smoke-test' in sys.argv:
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame as pg
from game_audio import GameAudio
from comic_ui import bitmap, draw_menu, menu_click, journey_bar, honey_frame, centered

W, H = 1280, 720
BOARD_WALK = 2.0
BOARD_ENTER = 0.55
DEPART_DRIVE = 2.8
DEPART_EMPTY_HOLD = 0.15
TRANSITION_FADE = 0.4
STATION_CUT = 0.7
INK = (18, 28, 43)
WHITE = (241, 246, 238)
GOLD = (255, 208, 86)
MINT = (107, 230, 177)
RED = (255, 113, 113)
EVENTS = [
    ('面具小孩', '', 'J', 'scare'),
    ('奶奶的拐杖', '', 'K', 'spill'),
    ('上班族偷吃', '', 'L', 'eat'),
    ('臭气来袭', '', 'I', 'gas'),
]


class Art:
    def __init__(self):
        self.cache = {}
        self.anchors = {}

    def load(self, pattern):
        path = next(ROOT.glob(pattern))
        return pg.image.load(str(path)).convert_alpha()

    def sheet(self, name, pattern, cols, rows, height):
        source = self.load(pattern)
        cells, anchors, body_sizes = [], [], []
        cw, ch = source.get_width() // cols, source.get_height() // rows
        for y in range(rows):
            for x in range(cols):
                frame = source.subsurface((x*cw, y*ch, cw, ch)).copy()
                bounds = frame.get_bounding_rect(min_alpha=100)
                if name in ('idle', 'spill', 'gas', 'eat'):
                    # Shoes are the stable body anchor. Bags, flying vegetables,
                    # exclamation marks and MUNCH text must not affect scale.
                    shoes = []
                    for yy in range(int(ch*.80), ch):
                        for xx in range(cw):
                            r, g, b, a = frame.get_at((xx, yy))
                            if a > 180 and 12 < min(r,g,b) and max(r,g,b) < 65 and max(r,g,b)-min(r,g,b) < 10:
                                shoes.append((xx, yy))
                    left = min(p[0] for p in shoes)
                    right = max(p[0] for p in shoes)
                    bottom = max(p[1] for p in shoes)+1
                    anchors.append(((left+right)/2, bottom))
                    body_sizes.append(right-left+1)
                else:
                    # Use the body's lower half, rather than moving hands/canes,
                    # to keep the character planted at a consistent location.
                    foot = frame.subsurface((0, int(ch*.78), cw, ch-int(ch*.78))).get_bounding_rect(min_alpha=100)
                    anchors.append((foot.centerx if foot.width else bounds.centerx,
                                    int(ch*.78)+foot.bottom if foot.width else bounds.bottom))
                    body_sizes.append(bounds.height)
                cells.append(frame)
        # One scale per sheet; never resize each frame to its individual bounds.
        if name in ('idle','spill','gas','eat','walk'):
            # Frame zero has the clean cap/body in each reaction sheet.
            # Calibrate all four sheets to the same cap-to-shoe body height.
            cap_y = min(yy for yy in range(ch) for xx in range(cw)
                        if cells[0].get_at((xx,yy)).a > 180
                        and cells[0].get_at((xx,yy)).r > 180
                        and cells[0].get_at((xx,yy)).g < 120)
            scale = height/(anchors[0][1]-cap_y)
        else:
            scale = height/median(body_sizes)
        if name == 'walk':
            body_height = anchors[0][1]-cap_y
            for i,cell in enumerate(cells):
                red = [(xx,yy) for yy in range(ch) for xx in range(cw)
                       if cell.get_at((xx,yy)).a>180 and cell.get_at((xx,yy)).r>180 and cell.get_at((xx,yy)).g<120]
                anchors[i] = ((min(x for x,y in red)+max(x for x,y in red))/2, min(y for x,y in red)+body_height)
        size = (round(cw*scale), round(ch*scale))
        frames = [pg.transform.scale(frame, size) for frame in cells]
        self.cache[name] = frames
        self.anchors[name] = [(round(x*scale), round(y*scale)) for x,y in anchors]


class Game:
    def __init__(self):
        pg.init()
        if not pg.mixer.get_init():pg.mixer.init()
        pg.mixer.set_num_channels(16)
        self.music_enabled = True
        self.volume=.55
        self.menu_open=False
        self.menu_page="main"
        self.paused_before_menu=False
        self.bgm = None
        music_path = ROOT / 'audio/bus-scene/bgm/arcade-rush-bgm.wav'
        if music_path.exists():
            if not pg.mixer.get_init(): pg.mixer.init()
            self.bgm = pg.mixer.Sound(str(music_path))
            self.bgm.set_volume(.55)
            pg.mixer.Channel(0).play(self.bgm,loops=-1)
        self.audio = GameAudio(ROOT,lambda:self.volume)
        destination=ROOT/'backgrounds/bus-scene/destination/bbq-background.png'
        self.destination_background=None
        self.screen = pg.display.set_mode((W, H), pg.RESIZABLE)
        pg.display.set_caption('巴士上的食材保卫战 | Bus Balance')
        self.canvas = pg.Surface((W, H))
        if destination.exists():self.destination_background=pg.image.load(str(destination)).convert()
        self.clock = pg.time.Clock()
        font = pg.font.match_font('microsoftyahei,simhei,notosanscjk,arial')
        self.fonts = {n: pg.font.Font(font, n) for n in (16, 20, 24, 32, 40, 48, 66)}
        self.art = Art()
        self.scene_frames = {}
        self.scene_meta = {}
        scene_root = Path(os.environ.get('IMAGING_GAME_SCENE_ROOT', ROOT / 'backgrounds/bus-scene/animations'))
        manifest = scene_root / 'manifest.json'
        if manifest.exists():
            meta = json.loads(manifest.read_text(encoding='utf-8-sig'))
            fw, fh = meta['frameWidth'], meta['frameHeight']
            viewport = meta.get('viewport', {'x':0,'y':122,'width':W,'height':round(W*fh/fw)})
            self.scene_position = (viewport['x'], viewport['y'])
            scene_size = (viewport['width'], viewport['height'])
            for scene in meta['scenes']:
                sheet = pg.image.load(str(scene_root / scene['sheet'])).convert_alpha()
                assert sheet.get_size() == (fw*meta['columns'], fh*meta['rows'])
                self.scene_frames[scene['id']] = [pg.transform.scale(
                    sheet.subsurface((i % meta['columns']*fw, i // meta['columns']*fh, fw, fh)),
                    scene_size) for i in range(meta['frameCount'])]
                self.scene_meta[scene['id']] = scene
        clean_station = Path(os.environ.get('IMAGING_GAME_CLEAN_STATION', ROOT / 'backgrounds/bus-scene/waiting_bus/start-scene-clean.png'))
        station = pg.image.load(str(clean_station)).convert_alpha() if clean_station.exists() else self.art.load('backgrounds/bus-scene/waiting_bus/start scene.png')
        self.stop = pg.transform.smoothscale(station, (W, H))
        original_bus = pg.transform.smoothscale(self.art.load('backgrounds/bus-scene/in_bus/bus background/bus background.png'), (W, 640))
        # Add floor depth before the foreground seats, keeping the upper cabin
        # and driver's position at their existing coordinates.
        split, extra = 376, 50
        self.bus = pg.Surface((W, 640 + extra), pg.SRCALPHA)
        self.bus.blit(original_bus, (0, 0), (0, 0, W, split))
        floor_band = original_bus.subsurface((0, split, W, 10))
        self.bus.blit(pg.transform.scale(floor_band, (W, extra)), (0, split))
        self.bus.blit(original_bus, (0, split + extra), (0, split, W, 640 - split))
        # The generated heading sits outside the vehicle, on black padding.
        self.bus.fill((0, 0, 0, 255), (0, 0, W, 103))
        self.floor_y = 464
        self.riders = {'kid': 400, 'granny': 590, 'idle': 735, 'worker': 900, 'fat': 1090}
        for name, pattern, cols, rows, size in [
            ('idle', 'characters/bus-scene/main character/*08_18*.png', 4, 4, 78),
            ('spill', 'characters/bus-scene/main character/*08_08*.png', 4, 4, 78),
            ('gas', 'characters/bus-scene/main character/*08_27*.png', 4, 4, 78),
            ('eat', 'characters/bus-scene/main character/*09_01*.png', 4, 4, 78),
            ('driver', 'characters/bus-scene/driver/*.png', 4, 2, 84),
            ('kid', 'characters/bus-scene/zombie/*07_00*.png', 4, 2, 100),
            ('mask', 'characters/bus-scene/zombie/*06_42*.png', 4, 2, 100),
            ('granny', 'characters/bus-scene/old women/*07_28*.png', 4, 2, 105),
            ('cane', 'characters/bus-scene/old women/*08_15*.png', 4, 2, 105),
            ('worker', 'characters/bus-scene/office worker/the*.png', 8, 1, 105),
            ('fat', 'characters/bus-scene/fat guy/*10_21*.png', 4, 4, 108),
            ('fart', 'characters/bus-scene/fat guy/*10_22*.png', 4, 4, 108),
            ('monster', 'sprites/bus-scene/effects/monster*.png', 8, 1, 300),
        ]:
            self.art.sheet(name, pattern, cols, rows, size)
        self.art.sheet('start-arrow', 'sprites/bus-scene/effects/start-arrow-reference.png', 4, 4, 85)
        self.art.sheet('walk', 'characters/bus-scene/main character/hero-walk-16frames.png', 4, 4, 78)
        arrow_source = self.art.load('backgrounds/bus-scene/waiting_bus/start-arrow-down.png')
        arrow_source = arrow_source.subsurface(arrow_source.get_bounding_rect(min_alpha=100)).copy()
        self.down_arrow = pg.transform.scale(arrow_source,(round(arrow_source.get_width()*126/arrow_source.get_height()),126))
        bus_source = self.art.load('sprites/bus-scene/transitions/bus-top-down-right.png')
        bus_source = bus_source.subsurface(bus_source.get_bounding_rect(min_alpha=100)).copy()
        self.top_bus = pg.transform.smoothscale(bus_source,(300,round(bus_source.get_height()*300/bus_source.get_width())))
        self.wipe_bus = pg.transform.smoothscale(bus_source,(round(bus_source.get_width()*1000/bus_source.get_height()),1000))
        health_source = self.art.load('sprites/bus-scene/effects/sandwich-health.png')
        health_source = health_source.subsurface(health_source.get_bounding_rect(min_alpha=100)).copy()
        self.health_bread = pg.transform.smoothscale(health_source,(340,round(health_source.get_height()*340/health_source.get_width())))
        self.pixel_ui = {p.stem: pg.image.load(str(p)).convert_alpha() for p in (ROOT/'ui/bus-scene/pixel-v3').glob('*.png')}
        self.health_bread=pg.transform.scale(self.pixel_ui['bread-base-full'],(340,45))
        self.bread_edges=json.loads((ROOT/'ui/bus-scene/pixel-v3/manifest.json').read_text())['breadSegmentEdges']
        self.bread_states=[]
        for active in range(11):
            bar=self.health_bread.copy()
            for i in range(active,10):
                left=max(5,self.bread_edges[i]);right=min(335,self.bread_edges[i+1])
                bar.fill((52,58,65),(left,5,right-left,35),special_flags=pg.BLEND_RGB_MULT)
            self.bread_states.append(bar)
        self.pixel_font = pg.font.SysFont('couriernew', 10, bold=True)
        title = self.pixel_ui['failed']
        self.failed_title=pg.transform.scale(title,(680,round(title.get_height()*680/title.get_width())))
        overlay_path = Path(os.environ.get('IMAGING_GAME_OVERLAY', ROOT / 'sprites/bus-scene/effects/screen-overlay-ingredients-failed-16frames.png'))
        source = pg.image.load(str(overlay_path)).convert_alpha() if overlay_path.exists() else pg.Surface((1280*16,720),pg.SRCALPHA)
        self.art.cache['broken'] = [source.subsurface((i*1280, 0, 1280, 720)).copy() for i in range(16)]
        self.arrow_rect = pg.Rect(260,140,150,135)
        self.departure_bg = self.stop.copy()
        # Extract the actual yellow bus from the supplied station picture.
        self.exterior = pg.Surface((430, 212), pg.SRCALPHA)
        self.exterior.blit(self.stop, (0, -277))
        mask = pg.Surface(self.exterior.get_size(), pg.SRCALPHA)
        pg.draw.polygon(mask, (255,255,255,255), [(0,10),(260,4),(279,0),(410,4),(419,20),(419,201),(0,201)])
        self.exterior.blit(mask,(0,0),special_flags=pg.BLEND_RGBA_MULT)
        trees = pg.transform.smoothscale(self.stop.subsurface((1000,277,280,203)),(430,203))
        self.departure_bg.blit(trees,(0,277))
        # Road reflections scroll with the bus, not with the station.
        water = pg.transform.smoothscale(self.stop.subsurface((1040,518,240,128)),(430,128))
        self.departure_bg.blit(water,(0,518))
        self.exterior_start_x = 0
        intro_root = Path(os.environ.get('IMAGING_GAME_INTRO_ROOT', ROOT / 'backgrounds/bus-scene/waiting_bus'))
        exterior_path = intro_root / 'start-scene-bus-layer-v2.png'
        empty_path = intro_root / 'start-scene-empty-background.png'
        if exterior_path.exists() and empty_path.exists():
            original_exterior = pg.image.load(str(exterior_path)).convert_alpha()
            # The full bus continues off the left edge while parked; its rear
            # becomes visible naturally when it accelerates to the right.
            self.exterior = pg.transform.scale(original_exterior, (round(988*W/1671), round(267*H/941)))
            self.exterior.fill((19, 30, 32, 255), (round(809*W/1671), round(21*H/941), round(171*W/1671), round(31*H/941)))
            self.exterior_start_x = round(-448*W/1671)
            empty = pg.image.load(str(empty_path)).convert_alpha()
            self.departure_bg = pg.transform.scale(empty, (W,H))
            # Keep the wordless station signs and their reflection from the
            # previously cleaned station art, without copying its parked bus.
            self.departure_bg.blit(self.stop, (430,0), (430,0,W-430,H))
        self.exterior_reflection = pg.transform.scale(pg.transform.flip(self.exterior,False,True),
                                                     (self.exterior.get_width(),128))
        self.exterior_reflection.set_alpha(90)
        colorful=ROOT/'backgrounds/bus-scene/waiting_bus/station-colorful-billboard.png'
        if colorful.exists(): self.departure_bg=pg.transform.scale(pg.image.load(str(colorful)).convert_alpha(),(W,H))
        # Recompose the parked frame with the same layers used for departure.
        self.stop = self.departure_bg.copy()
        self.stop.blit(self.exterior, (self.exterior_start_x,277))
        self.stop.blit(self.exterior_reflection,(self.exterior_start_x,518))
        self.station_layout={'heroStartX':690,'heroFeetY':485,'heroMinX':210,
                             'boardZone':[210,245],'arrowX':335,'arrowY':207}
        pasar_layout=ROOT/'backgrounds/bus-scene/waiting_bus/pasar-layout.json'
        if pasar_layout.exists():
            self.station_layout.update(json.loads(pasar_layout.read_text(encoding='utf-8')))
            self.stop=pg.transform.scale(pg.image.load(str(ROOT/'backgrounds/bus-scene/waiting_bus/pasar-station.png')).convert(),(W,H))
        self.queue = pg.Surface((W,H), pg.SRCALPHA)
        self.mode = 'stop'
        self.running = True
        self.paused = False
        self.held = set()
        self.anim = 0
        self.reset()

    def reset(self):
        self.audio.stop()
        self.jump_y=0.0
        self.jump_v=0.0
        self.step_time=0.0
        self.step_side=0
        self.outside_elapsed=0.0
        self.outside_active=False
        self.arrival_time=0.0
        self.arrival_done=False
        self.focus_suspended=False
        self.focus_was_paused=False
        self.menu_open=False
        self.menu_page="main"
        self.damaged_food = set()
        self.station_x = float(self.station_layout['heroStartX'])
        self.station_moving = False
        self.elapsed = 0.0
        self.departure_time = 0.0
        self.boarding_time = 0.0
        self.ride_entry_time = 0.0
        self.scene_reaction = None
        self.scene_reaction_time = 0.0
        self.balance = 100.0
        self.food = 100
        self.event_index = 0
        self.event = None
        self.next_event = 7.0
        self.event_left = 0
        self.presses = 0
        self.required = 0
        self.notice = ''
        self.notice_left = 0
        self.reaction = 'idle'
        self.reaction_left = 0
        self.end_time = 0
        self.reason = ''
        self.solved = 0
        self.paused = False
        self.held.clear()

    def target(self):
        difficulty=min(self.elapsed/60,1)
        return 640+math.sin(self.elapsed*.95)*95,550+math.cos(self.elapsed*.8)*15,92-14*difficulty

    def mouse(self):
        sw, sh = self.screen.get_size()
        scale = min(sw/W, sh/H)
        ox, oy = (sw-W*scale)/2, (sh-H*scale)/2
        x, y = pg.mouse.get_pos()
        return (x-ox)/scale, (y-oy)/scale

    def text(self, value, pos, size=24, color=WHITE, center=False):
        image = self.fonts[size].render(value, True, color)
        rect = image.get_rect(center=pos) if center else image.get_rect(topleft=pos)
        self.canvas.blit(image, rect)

    def panel(self, rect, color=INK, alpha=235):
        layer = pg.Surface((rect[2], rect[3]), pg.SRCALPHA)
        pg.draw.rect(layer, (*color, alpha), layer.get_rect(), border_radius=18)
        self.canvas.blit(layer, rect[:2])

    def draw_health(self):
        active=math.ceil(max(0,min(100,self.balance))/10)
        self.canvas.blit(self.bread_states[active],(32,14))

    def food_icon(self,index,cx,cy):
        if index==0:
            pg.draw.rect(self.canvas,(109,155,50),(cx-4,cy+5,8,13))
            for dx,dy,col in ((-9,1,(54,126,62)),(8,1,(89,160,65)),(0,-8,(105,176,76))): pg.draw.circle(self.canvas,col,(cx+dx,cy+dy),10)
        elif index==1:
            pg.draw.polygon(self.canvas,(239,149,43),[(cx-9,cy-6),(cx+10,cy-3),(cx-3,cy+20)])
            for dx in (-6,0,6): pg.draw.line(self.canvas,(77,142,63),(cx,cy-6),(cx+dx,cy-17),4)
        elif index==2:
            pg.draw.circle(self.canvas,(215,70,59),(cx,cy+3),15);pg.draw.circle(self.canvas,(244,116,79),(cx-5,cy-3),5)
            pg.draw.polygon(self.canvas,(61,128,62),[(cx,cy-16),(cx+4,cy-8),(cx+12,cy-10),(cx+4,cy-3),(cx-8,cy-8)])
        elif index==3:
            pg.draw.ellipse(self.canvas,(239,226,181),(cx-12,cy-18,24,36));pg.draw.ellipse(self.canvas,(255,246,213),(cx-8,cy-14,12,24))
        else:
            pg.draw.polygon(self.canvas,(246,191,63),[(cx-16,cy-13),(cx+15,cy-2),(cx+15,cy+15),(cx-16,cy+15)])
            for dx,dy in ((-7,6),(7,9),(4,-2)): pg.draw.circle(self.canvas,(201,139,44),(cx+dx,cy+dy),3)

    def draw_pixel_target(self,x,y,radius,inside):
        layer=pg.Surface((W//6,H//6),pg.SRCALPHA)
        center=(round(x/6),round(y/6));r=round(radius/6)
        color=MINT if inside else RED
        pg.draw.circle(layer,(*color,35),center,r)
        pg.draw.circle(layer,(*color,255),center,r,1)
        pg.draw.rect(layer,WHITE,(center[0],center[1],1,1))
        self.canvas.blit(pg.transform.scale(layer,(W,H)),(0,0))

    def pixel_text(self,value,pos,color=(255,239,191)):
        self.canvas.blit(bitmap(pg,value,3),pos)

    def ui_sprite(self,name,x,y,w,h,clip=1):
        im=pg.transform.scale(self.pixel_ui[name],(w,h))
        if clip<1: im=im.subsurface((0,0,max(0,round(w*clip)),h))
        self.canvas.blit(im,(x,y))

    def draw_hud(self):
        self.draw_health()
        warnings=('kid','cane','worker','fart')
        for i,key in enumerate(warnings):
            x=42+i*74
            self.ui_sprite('warning-'+key,x,68,42,36)
            centered(self,pg,EVENTS[i][2],x+21,113,2)
            if self.event==i:pg.draw.rect(self.canvas,GOLD,(x-3,65,48,42),2)
        stage=0 if self.mode=='stop' else 2 if self.mode in ('success','arrival','home') else 1
        progress=.06 if stage==0 else 1 if stage==2 else .5+.5*min(1,self.elapsed/60)
        journey_bar(self,pg,stage,progress)
        for i,key in enumerate(('stage-stop','stage-bus','stage-arrival')):
            self.ui_sprite(key,410+i*192,4,40,35)
        card_names=('carrot','broccoli','tomato','cheese','egg','lettuce')
        slot_to_card={0:1,1:0,2:2,3:4,4:3}
        for i,name in enumerate(card_names):
            x=416+i*68
            self.ui_sprite('card-'+name,x,42,56,73)
            if i in [slot_to_card[k] for k in self.damaged_food if k in slot_to_card]:
                pg.draw.line(self.canvas,RED,(x+10,57),(x+47,103),4)
                pg.draw.line(self.canvas,RED,(x+47,57),(x+10,103),4)
        for i,key in enumerate(('music','menu'),start=1):
            self.ui_sprite('icon-'+key,1143+i*33,8,26,26)

    def sprite(self, name, x, bottom, frame=None, alpha=255):
        frames = self.art.cache[name]
        index = int(self.anim*6 if frame is None else frame) % len(frames)
        image = frames[index]
        if alpha != 255:
            image = image.copy()
            image.set_alpha(alpha)
        ax, ay = self.art.anchors[name][index]
        self.canvas.blit(image, (round(x-ax), round(bottom-ay)))

    def start_arrow(self):
        layout=self.station_layout
        self.canvas.blit(self.down_arrow,self.down_arrow.get_rect(center=(layout['arrowX'],layout['arrowY']+round(math.sin(self.anim*3)*4))))
        x=layout['arrowX'];y=layout['arrowY']-89
        pg.draw.rect(self.canvas,INK,(x-72,y-22,144,44),border_radius=6)
        pg.draw.rect(self.canvas,GOLD if self.can_board() else (92,115,128),(x-72,y-22,144,44),2,border_radius=6)
        centered(self,pg,'ENTER',x,y,3)

    def can_board(self):
        zone=self.station_layout['boardZone']
        return self.mode=='stop' and not self.paused and zone[0]<=self.station_x<=zone[1] and self.jump_y==0

    def begin_boarding(self):
        if self.mode != 'stop':
            return False
        self.mode = 'departure'
        self.departure_time = 0
        self.jump_y=0.0;self.jump_v=0.0
        self.audio.play('bus-drive')
        self.held.clear()
        return True

    def boarding_pose(self):
        p = min(1, self.boarding_time / BOARD_WALK)
        x = 690 + (224-690)*p
        entering = max(0, min(1, (self.boarding_time-BOARD_WALK)/BOARD_ENTER))
        bottom = 485 + (round(math.sin(p*math.pi*16)*2) if p<1 else 0) - round(entering*17)
        return x, bottom, round(255*(1-entering))

    def departure_x(self):
        p = max(0, min(1, self.departure_time/DEPART_DRIVE))
        width = self.wipe_bus.get_width()
        return -width + round((W+width)*p)

    def blit_exterior(self, x, bob):
        self.canvas.blit(self.departure_bg,(0,0))
        if hasattr(self, 'exterior_reflection'):
            self.canvas.blit(self.exterior_reflection,(x,518-bob))
        self.canvas.blit(self.exterior,(x,277+bob))

    def draw_scene(self):
        if not self.scene_frames:
            return False
        kind, elapsed, loop = 'idle', self.anim, True
        if self.scene_reaction and self.reaction_left > 0:
            kind, elapsed, loop = self.scene_reaction, self.scene_reaction_time, False
        elif self.event is not None:
            kind = ('boy-scares','cane-hit','worker-steals','fart-poison')[self.event]
            # Preparation remains reversible during the player's response window.
            image = self.scene_frames['idle'][0]
            self.canvas.blit(image,self.scene_position)
            return True
        durations = self.scene_meta[kind]['durationsMs']
        milliseconds = elapsed*1000
        if loop:
            milliseconds %= sum(durations)
        frame = len(durations)-1
        for i, duration in enumerate(durations):
            if milliseconds < duration:
                frame = i
                break
            milliseconds -= duration
        self.canvas.blit(self.scene_frames[kind][frame], self.scene_position)
        return True

    def foot_shadow(self, x, bottom, width):
        layer = pg.Surface((width+8, 14), pg.SRCALPHA)
        pg.draw.ellipse(layer, (0, 0, 0, 75), (4, 4, width, 7))
        self.canvas.blit(layer, (round(x-width/2-4), round(bottom-7)))

    def finish(self, success, reason=''):
        self.audio.stop()
        self.audio.play('bus-horn' if success else 'fail')
        self.mode = ('arrival' if self.destination_background is not None else 'success') if success else 'failed'
        self.arrival_time=0.0
        self.outside_elapsed=0;self.outside_active=False
        self.reaction_left=0;self.event=None
        self.end_time = 0
        self.reason = reason

    def open_menu(self):
        self.paused_before_menu=self.paused
        self.menu_open=True;self.menu_page='main';self.paused=True;self.held.clear()
        pg.mixer.pause()

    def close_menu(self):
        self.menu_open=False;self.paused=self.paused_before_menu;self.held.clear()
        if not self.paused:pg.mixer.unpause()

    def key(self, key):
        if key==pg.K_ESCAPE:
            self.close_menu() if self.menu_open else self.open_menu()
            return
        if self.menu_open:return
        if key == pg.K_ESCAPE:
            self.running = False
        elif key == pg.K_r:
            self.reset()
            self.mode = 'stop'
            if self.music_enabled: pg.mixer.unpause()
        elif key == pg.K_b:
            self.music_enabled = not self.music_enabled
            if self.bgm: self.bgm.set_volume(self.volume if self.music_enabled else 0)
        elif key in (pg.K_RETURN,pg.K_KP_ENTER) and self.can_board():
            self.begin_boarding()
        elif key==pg.K_SPACE and self.mode=='stop' and not self.paused:
            if self.jump_y==0 and self.jump_v==0:
                self.jump_v=420.0;self.step_time=0;self.audio.play('jump')
        elif key in (pg.K_SPACE, pg.K_p) and self.mode in ('ride','boarding','departure'):
            self.paused = not self.paused
            if self.paused: pg.mixer.pause()
            else: pg.mixer.unpause()
        elif self.mode == 'ride' and not self.paused and self.event is not None:
            if key == pg.key.key_code(EVENTS[self.event][2].lower()):
                self.presses += 1
                if self.presses >= self.required:
                    self.audio.play('protect')
                    self.solved += 1
                    self.notice = '✓ PROBLEM SOLVED · 危机解除！'
                    self.notice_left = 2.3
                    self.event = None

    def update(self, dt, mouse):
        if not self.paused:
            self.anim += dt
        if self.mode == 'stop':
            if not self.paused:
                direction = int(pg.K_d in self.held)-int(pg.K_a in self.held)
                old_x=self.station_x
                self.station_x = max(self.station_layout['heroMinX'],min(W-55,self.station_x+direction*180*dt))
                self.station_moving=self.station_x!=old_x
                if self.jump_y>0 or self.jump_v!=0:
                    self.jump_y+=self.jump_v*dt-490*dt*dt;self.jump_v-=980*dt
                    if self.jump_y<=0:
                        self.jump_y=0.0;self.jump_v=0.0;self.audio.play('land')
                if self.station_moving and self.jump_y==0:
                    self.step_time-=dt
                    if self.step_time<=0:
                        self.audio.play('step-right' if self.step_side%2 else 'step-left')
                        self.step_side+=1;self.step_time=.24
                else:self.step_time=0
            return
        if self.mode == 'boarding':
            if not self.paused:
                self.boarding_time += dt
                if self.boarding_time + 1e-9 >= STATION_CUT:
                    self.mode = 'departure'
                    self.departure_time = 0
            return
        if self.mode == 'departure':
            if not self.paused:
                self.departure_time += dt
                if self.departure_time + 1e-9 >= DEPART_DRIVE:
                    self.mode = 'ride'
                    self.ride_entry_time = TRANSITION_FADE
            return
        if self.mode=='arrival':
            if not self.paused:
                self.arrival_time+=dt
                if self.arrival_time+1e-9>=4:
                    self.mode='home';self.arrival_done=True
            return
        if self.mode in ('failed', 'success'):
            self.end_time += dt
        if self.mode != 'ride' or self.paused:
            return
        self.elapsed += dt
        self.ride_entry_time += dt
        self.scene_reaction_time += dt
        if self.scene_reaction and self.reaction_left>0:
            total=sum(self.scene_meta[self.scene_reaction]['durationsMs'])/1000
            self.audio.update(self.scene_reaction_time,total)
        self.notice_left -= dt
        self.reaction_left -= dt
        if self.reaction_left <= 0:
            self.reaction = 'idle'
        x, y, radius = self.target()
        inside = math.hypot(mouse[0]-x, mouse[1]-y) <= radius
        self.outside_active=not inside
        if inside:self.outside_elapsed=0.0
        else:
            self.outside_elapsed+=dt
            while self.outside_elapsed+1e-9>=5:
                self.balance=max(0,self.balance-10);self.outside_elapsed=max(0,self.outside_elapsed-5)
                self.audio.play('warning',.65)
        if self.balance <= 0:
            self.finish(False, '生命值耗尽，食材掉落了。')
            return
        if self.event is None and self.event_index < 4 and self.elapsed >= self.next_event:
            self.audio.play('warning')
            self.event = self.event_index
            self.event_index += 1
            self.event_left = 7.0
            self.required = (4,4,5,5)[self.event]
            self.presses = 0
            self.next_event += 13
        if self.event is not None:
            self.event_left -= dt
            if self.event_left <= 0:
                self.reaction = EVENTS[self.event][3]
                if self.reaction == 'scare':
                    self.reaction = 'idle'
                    # The circle grace timer is the sole source of life loss.
                self.reaction_left = 3
                if self.scene_frames:
                    self.scene_reaction = ('boy-scares','cane-hit','worker-steals','fart-poison')[self.event]
                    self.scene_reaction_time = 0
                    self.audio.begin(self.scene_reaction)
                    self.reaction_left = sum(self.scene_meta[self.scene_reaction]['durationsMs'])/1000
                self.damaged_food.add((3,2,4,0)[self.event])
                self.food = max(0, self.food-15)
                self.notice = '食材受损 -15 · 继续稳住！'
                self.notice_left = 3
                self.event = None
                if self.food == 0:
                    self.finish(False, '食材损失过多，没能送达。')
        if self.mode == 'ride' and self.elapsed >= 60:
            self.finish(True)

    def draw(self):
        self.canvas.fill((9, 16, 26))
        if self.mode in ('arrival','home'):
            self.draw_scene()
            if self.mode=='home':self.canvas.blit(self.destination_background,(0,0))
            elif self.arrival_time>=1.2:
                w=self.wipe_bus.get_width();p=min(1,(self.arrival_time-1.2)/2.8);x=-w+round((W+w)*p)
                clip=self.canvas.get_clip();self.canvas.set_clip((0,0,max(0,min(W,x+64)),H))
                self.canvas.blit(self.destination_background,(0,0));self.canvas.set_clip(clip)
                self.canvas.blit(self.wipe_bus,(x,(H-self.wipe_bus.get_height())//2))
        elif self.mode == 'stop':
            self.canvas.blit(self.stop, (0, 0))
            self.canvas.blit(self.queue,(0,0))
            grounded_walk=self.station_moving and self.jump_y==0
            feet=self.station_layout['heroFeetY']
            if self.jump_y>0:self.foot_shadow(self.station_x,feet,max(18,round(42-self.jump_y*.18)))
            self.sprite('walk' if grounded_walk else 'idle', self.station_x, feet-round(self.jump_y),
                        frame=self.anim*(16 if grounded_walk else 4))
            self.start_arrow()
        elif self.mode == 'boarding':
            self.canvas.blit(self.stop,(0,0))
            self.canvas.blit(self.queue,(0,0))
            self.sprite('idle',690,485,frame=self.anim*4)
            fade = pg.Surface((W,H))
            fade.set_alpha(round(255*min(1,self.boarding_time/.55)))
            self.canvas.blit(fade,(0,0))
        elif self.mode == 'departure':
            t = self.departure_time
            bus_x = self.departure_x()
            self.canvas.blit(self.stop,(0,0))
            self.canvas.blit(self.queue,(0,0))
            self.sprite('idle',self.station_x,self.station_layout['heroFeetY'],frame=self.anim*4)
            reveal = max(0,min(W,bus_x+64))
            if reveal:
                station_canvas = self.canvas
                self.canvas = pg.Surface((W,H));self.canvas.fill((0,0,0))
                self.draw_scene()
                inside = self.canvas;self.canvas = station_canvas
                self.canvas.blit(inside,(0,0),(0,0,reveal,H))
            self.canvas.blit(self.wipe_bus,(bus_x,(H-self.wipe_bus.get_height())//2))
        else:
            shake = round(math.sin(self.elapsed*13)*1.5)
            full_scene = self.draw_scene()
            if not full_scene:
                self.canvas.blit(self.bus, (0, 26+shake))
            # Passing trees/buildings are clipped to the glass. The whole bus
            # and its occupants share the same suspension offset.
            for left, width in (() if full_scene else ((560,166),(744,148),(908,181),(320,208))):
                glass = pg.Surface((width,85),pg.SRCALPHA)
                for i in range(-1,5):
                    xx = int(i*83-self.elapsed*65)% (width+100)-50
                    pg.draw.rect(glass,(152,205,163,22),(xx,25,34,60))
                    pg.draw.circle(glass,(48,107,77,40),(xx+15,28),24)
                self.canvas.blit(glass,(left,213+shake))
            if not full_scene: self.sprite('driver', 148, 389+shake)
            floor = self.floor_y + shake
            for name, width in (() if full_scene else (('kid',28),('granny',35),('worker',36),('fat',58),('idle',52))):
                self.foot_shadow(self.riders[name], floor, width)
            if not full_scene:
                self.sprite('mask' if self.event == 0 else 'kid', self.riders['kid'], floor, frame=self.anim*5 if self.event==0 else 0)
                self.sprite('cane' if self.event == 1 else 'granny', self.riders['granny'], floor, frame=self.anim*5 if self.event==1 else 0)
                self.sprite('worker', self.riders['worker'], floor, self.anim*5 if self.event == 2 else 0)
                self.sprite('fart' if self.event == 3 else 'fat', self.riders['fat'], floor, frame=self.anim*5 if self.event==3 else 0)
                self.sprite(self.reaction, self.riders['idle'], floor, frame=self.anim*6 if self.reaction!='idle' else 0)
            if self.mode == 'ride':
                x, y, radius = self.target()
                inside = math.dist(self.mouse(), (x,y)) <= radius
                self.draw_pixel_target(x,y,radius,inside)
                if self.outside_active:
                    honey_frame(pg,self.canvas,(410,614,460,70))
                    pg.draw.rect(self.canvas,INK,(762,622,98,54),border_radius=12)
                    self.text('PLEASE MOVE BACK',(580,649),24,INK,True)
                    self.text(f'{max(1,math.ceil(5-self.outside_elapsed))}s',(811,648),40,WHITE,True)
                if self.event is not None:
                    title, desc, key, kind = EVENTS[self.event]
                    if kind == 'scare' and not full_scene:
                        self.sprite('monster', 640, 480, min(7, int((5.5-self.event_left)/5.5*8)), 135)
                if self.reaction_left>0 and self.reaction=='gas' and not full_scene:
                    gas=pg.Surface((W,H),pg.SRCALPHA)
                    for i in range(7):
                        pg.draw.circle(gas,(132,171,66,35),(520+i*55,400+int(math.sin(self.anim*3+i)*40)),65)
                    self.canvas.blit(gas,(0,0))
            if self.mode in ('failed','success'):
                if self.mode=='failed':
                    shade=pg.Surface((W,H),pg.SRCALPHA);shade.fill((4,12,20,160));self.canvas.blit(shade,(0,0))
                    self.canvas.blit(self.failed_title,self.failed_title.get_rect(center=(640,310)))
                else:
                    self.panel((340,220,600,270),alpha=235)
                    self.text('SUCCESS',(640,275),66,MINT,True)
        if self.mode!='home':self.draw_hud()
        if self.mode == 'ride' and self.ride_entry_time < TRANSITION_FADE:
            fade = pg.Surface((W,H))
            fade.set_alpha(round(255*(1-self.ride_entry_time/TRANSITION_FADE)))
            self.canvas.blit(fade,(0,0))
        if self.paused and self.mode == 'ride':
            self.panel((390,265,500,165))
            self.text('已暂停', (640,310),48,GOLD,True)
            self.text('按空格继续旅程', (640,386),24,WHITE,True)
        elif self.paused and self.mode in ('boarding','departure'):
            self.panel((570,290,140,140), alpha=170)
            pg.draw.rect(self.canvas, GOLD, (607,326,20,68), border_radius=4)
            pg.draw.rect(self.canvas, GOLD, (653,326,20,68), border_radius=4)
        if self.menu_open:draw_menu(self,pg)
        sw, sh = self.screen.get_size()
        scale = min(sw/W, sh/H)
        scaled = pg.transform.smoothscale(self.canvas, (max(1,int(W*scale)),max(1,int(H*scale))))
        self.screen.fill((9,16,26))
        self.screen.blit(scaled, scaled.get_rect(center=(sw//2,sh//2)))
        pg.display.flip()

    def run(self):
        while self.running:
            dt = min(.05, self.clock.tick(60)/1000)
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.running = False
                elif event.type == pg.WINDOWFOCUSLOST:
                    self.held.clear()
                    pg.mixer.pause()
                    if not self.focus_suspended:
                        self.focus_was_paused=self.paused;self.focus_suspended=True
                    self.paused=True
                elif event.type == pg.WINDOWFOCUSGAINED:
                    if self.focus_suspended:
                        self.paused=self.focus_was_paused;self.focus_suspended=False
                    if not self.paused: pg.mixer.unpause()
                elif event.type == pg.MOUSEBUTTONDOWN and event.button==1:
                    x,y=self.mouse();menu_click(self,pg,x,y)
                elif event.type == pg.KEYDOWN and event.key not in self.held:
                    self.held.add(event.key)
                    self.key(event.key)
                elif event.type == pg.KEYUP:
                    self.held.discard(event.key)
            self.update(dt, self.mouse())
            self.draw()
        pg.quit()


def smoke_test(game):
    game.draw()
    pg.image.save(game.canvas, str(PREVIEW_ROOT/'preview_station.png'))
    for name in ('idle','spill','gas','eat','kid','mask','granny','cane','fat','fart'):
        assert len({image.get_size() for image in game.art.cache[name]}) == 1
        for index in range(len(game.art.cache[name])):
            game.sprite(name, 640, 438, frame=index)
    game.mode = 'departure'
    game.update(1, (0,0))
    assert game.mode == 'departure' and game.elapsed == 0
    game.departure_time = 2.5
    game.draw()
    pg.image.save(game.canvas,str(PREVIEW_ROOT/'preview_departure.png'))
    game.update(DEPART_DRIVE + DEPART_EMPTY_HOLD + TRANSITION_FADE - 2.5,(0,0))
    assert game.mode == 'ride' and game.elapsed == 0
    game.event = None
    game.draw()
    pg.image.save(game.canvas,str(PREVIEW_ROOT/'preview_bus_layout.png'))
    game.mode = 'ride'
    for index in range(4):
        game.elapsed = 7+index*13
        game.update(.01, game.target()[:2])
        assert game.event == index
        game.draw()
        if index == 0: pg.image.save(game.canvas,str(PREVIEW_ROOT/'preview_bus.png'))
        for _ in range(game.required): game.key(pg.key.key_code(EVENTS[index][2].lower()))
        assert game.event is None
    assert game.solved == 4
    game.elapsed = 60
    game.update(.01, game.target()[:2])
    assert game.mode == 'success'
    game.draw()
    game.reset()
    game.mode = 'ride'
    for index in range(3):
        game.elapsed = 7+index*13
        game.update(.01,game.target()[:2])
        game.event_left = 0
        game.update(.01,game.target()[:2])
    assert game.mode == 'failed' and game.food == 0
    game.end_time = 1.7
    game.draw()
    pg.image.save(game.canvas,str(PREVIEW_ROOT/'preview_failed.png'))
    game.reset()
    game.mode = 'ride'
    game.elapsed = 3
    game.balance = .1
    game.update(.05,(-100,-100))
    assert game.mode == 'failed'
    game.reset()
    game.mode='ride'
    game.paused=True
    game.update(1,(0,0))
    assert game.elapsed==0 and game.balance==100
    print('PASS: fixed sprite canvases, departure transition, assets, four events, success, food loss, balance loss, pause, rendering')
    pg.quit()


if __name__ == '__main__':
    game = Game()
    smoke_test(game) if '--smoke-test' in sys.argv else game.run()

