"""Deterministic bitmap alphabet matching the yellow/red reference."""
GLYPHS = dict(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!?-:/ .',[
'01110/11011/11011/11111/11011/11011/11011','11110/11011/11011/11110/11011/11011/11110','01111/11000/11000/11000/11000/11000/01111','11110/11011/11011/11011/11011/11011/11110','11111/11000/11000/11110/11000/11000/11111','11111/11000/11000/11110/11000/11000/11000','01111/11000/11000/11011/11011/11011/01111','11011/11011/11011/11111/11011/11011/11011','11111/00110/00110/00110/00110/00110/11111','00111/00011/00011/00011/11011/11011/01110','11011/11011/11110/11100/11110/11011/11011','11000/11000/11000/11000/11000/11000/11111','11011/11111/11111/11011/11011/11011/11011','11011/11111/11111/11111/11011/11011/11011','01110/11011/11011/11011/11011/11011/01110','11110/11011/11011/11110/11000/11000/11000','01110/11011/11011/11011/11111/01110/00011','11110/11011/11011/11110/11110/11011/11011','01111/11000/11000/01110/00011/00011/11110','11111/00110/00110/00110/00110/00110/00110','11011/11011/11011/11011/11011/11011/01110','11011/11011/11011/11011/11011/01110/00100','11011/11011/11011/11011/11111/11111/11011','11011/11011/01110/00100/01110/11011/11011','11011/11011/01110/00110/00110/00110/00110','11111/00011/00110/01100/11000/11000/11111',
'01110/11011/11111/11011/11011/11011/01110','00110/01110/00110/00110/00110/00110/11111','01110/11011/00011/00110/01100/11000/11111','11110/00011/00011/01110/00011/00011/11110','11011/11011/11011/11111/00011/00011/00011','11111/11000/11000/11110/00011/00011/11110','01110/11000/11000/11110/11011/11011/01110','11111/00011/00011/00110/00110/01100/01100','01110/11011/11011/01110/11011/11011/01110','01110/11011/11011/01111/00011/00011/01110',
'00110/00110/00110/00110/00110/00000/00110','01110/11011/00011/00110/00110/00000/00110','00000/00000/00000/11111/00000/00000/00000','00000/00110/00110/00000/00110/00110/00000','00001/00011/00110/01100/11000/10000/00000','00000/00000/00000/00000/00000/00000/00000','00000/00000/00000/00000/00000/00110/00110']))

def bitmap(pg,text,scale=3):
    text=text.upper();im=pg.Surface((max(1,len(text)*6+3)*scale,11*scale),pg.SRCALPHA)
    pixels=[(3+n*6+x,1+y) for n,c in enumerate(text) for y,row in enumerate(GLYPHS.get(c,GLYPHS['?']).split('/')) for x,b in enumerate(row) if b=='1']
    for dx,dy,col in [(1,2,(22,20,36)),(-1,0,(22,20,36)),(1,0,(22,20,36)),(0,-1,(22,20,36)),(0,1,(22,20,36))]:
        for x,y in pixels:pg.draw.rect(im,col,((x+dx)*scale,(y+dy)*scale,scale,scale))
    for x,y in pixels:pg.draw.rect(im,(242,193,50) if y<5 else (212,49,27),(x*scale,y*scale,scale,scale))
    return im

PANELS=[('PLAY',[(352,224),(653,241),(653,530),(337,548)],(223,42,76)),('SETTING',[(680,246),(899,259),(899,384),(680,399)],(42,168,215)),('EXIT',[(680,424),(899,408),(885,541),(680,555)],(91,97,111))]

def centered(g,pg,text,cx,cy,scale=3):
    im=bitmap(pg,text,scale);bounds=im.get_bounding_rect();g.canvas.blit(im,(round(cx-bounds.centerx),round(cy-bounds.centery)))

def gradient_box(pg,canvas,rect,r,top,bottom,border=None):
    x,y,w,h=rect;im=pg.Surface((w,h),pg.SRCALPHA)
    for j in range(h):
        t=j/max(1,h-1);col=tuple(round(a+(b-a)*t)for a,b in zip(top,bottom))
        pg.draw.line(im,col,(0,j),(w,j))
    mask=pg.Surface((w,h),pg.SRCALPHA);pg.draw.rect(mask,(255,255,255),(0,0,w,h),border_radius=r)
    im.blit(mask,(0,0),special_flags=pg.BLEND_RGBA_MULT);canvas.blit(im,(x,y))
    if border:pg.draw.rect(canvas,border,rect,3,border_radius=r)

def draw_menu(g,pg):
    shade=pg.Surface((1280,720),pg.SRCALPHA);shade.fill((4,10,24,204));g.canvas.blit(shade,(0,0))
    pg.draw.rect(g.canvas,(7,20,31),(311,158,635,450),border_radius=34)
    gradient_box(pg,g.canvas,(305,148,635,450),34,(121,239,242),(23,103,152),(158,250,255))
    pg.draw.rect(g.canvas,(86,199,219),(313,156,619,434),2,border_radius=28)
    if g.menu_page=='main':
        for name,pts,col in PANELS:
            pg.draw.polygon(g.canvas,(16,19,30),[(x+8,y+10)for x,y in pts])
            pg.draw.polygon(g.canvas,(255,245,213),pts)
            cx=sum(x for x,y in pts)/4;cy=sum(y for x,y in pts)/4
            for factor,color in ((.94,(20,22,34)),(.9,col)):
                pg.draw.polygon(g.canvas,color,[(cx+(x-cx)*factor,cy+(y-cy)*factor)for x,y in pts])
            centered(g,pg,name,cx,cy,6 if name=='PLAY' else 4)
        honey_frame(pg,g.canvas,(489,165,266,43));centered(g,pg,'PAUSED',622,187,3);return
    pg.draw.rect(g.canvas,(20,36,49),(350,210,580,310),border_radius=24)
    pg.draw.rect(g.canvas,(94,175,199),(350,210,580,310),3,border_radius=24)
    honey_frame(pg,g.canvas,(420,225,440,56));centered(g,pg,'SETTING',640,253,4)
    centered(g,pg,'MUSIC: '+('ON'if g.music_enabled else 'OFF'),640,340,3)
    centered(g,pg,'SFX: '+('ON' if g.audio.enabled else 'OFF'),640,372,2)
    centered(g,pg,'VOLUME',640,399,2)
    pg.draw.rect(g.canvas,(68,70,89),(460,424,360,18),border_radius=9)
    if g.volume:pg.draw.rect(g.canvas,(255,218,73),(460,424,round(360*g.volume),18),border_radius=9)
    centered(g,pg,str(round(g.volume*100))+'%',640,478,2)
    centered(g,pg,'BACK',640,550,4)

def journey_bar(g,pg,stage,progress):
    x,y,w,h=418,16,408,20
    pg.draw.rect(g.canvas,(18,36,47),(x-4,y-4,w+8,h+8),border_radius=14)
    pg.draw.rect(g.canvas,(97,127,133),(x-4,y-4,w+8,h+8),3,border_radius=14)
    bar=pg.Surface((w,h),pg.SRCALPHA);pg.draw.rect(bar,(41,58,67),(0,0,w,h),border_radius=10)
    fill=pg.Surface((w,h),pg.SRCALPHA);gradient_box(pg,fill,(0,0,w,h),10,(255,242,138),(209,139,40))
    fill.fill((0,0,0,0),(round(w*progress),0,w-round(w*progress),h))
    mask=pg.mask.from_surface(fill).to_surface(setcolor=(255,255,255,255),unsetcolor=(0,0,0,0))
    shine=pg.Surface((w,h),pg.SRCALPHA);sx=(g.anim*88)%(w+100)-50
    pg.draw.rect(shine,(255,255,225,100),(5,3,max(0,round(w*progress)-10),3))
    pg.draw.polygon(shine,(255,255,240,115),[(sx,0),(sx+15,0),(sx-3,h),(sx-18,h)])
    shine.blit(mask,(0,0),special_flags=pg.BLEND_RGBA_MULT);fill.blit(shine,(0,0));bar.blit(fill,(0,0));g.canvas.blit(bar,(x,y))
    honey_frame(pg,g.canvas,(848,5,237,36));centered(g,pg,('WAITING BUS','ON THE BUS','ARRIVED')[stage],966,23,2)

def menu_click(g,pg,x,y):
    if not g.menu_open:
        if 1202<=x<=1238 and y<42:g.open_menu();return True
        if 1170<=x<1202 and y<42:
            g.music_enabled=not g.music_enabled
            if g.bgm:g.bgm.set_volume(g.volume if g.music_enabled else 0)
            return True
        return False
    if g.menu_page!='main':
        if 430<x<850 and 510<=y<=565:g.menu_page='main'
        if g.menu_page=='settings' and 310<y<365:
            g.music_enabled=not g.music_enabled
            if g.bgm:g.bgm.set_volume(g.volume if g.music_enabled else 0)
        if g.menu_page=='settings' and 365<=y<385:
            g.audio.enabled=not g.audio.enabled
            if not g.audio.enabled:g.audio.stop(clear=False)
        if g.menu_page=='settings' and 395<y<465:
            g.volume=max(0,min(1,(x-460)/360))
            if g.bgm:g.bgm.set_volume(g.volume if g.music_enabled else 0)
        return True
    for name,pts,col in PANELS:
        inside=False
        for i,a in enumerate(pts):
            b=pts[i-1]
            if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
        if inside:
            if name=='PLAY':g.close_menu()
            elif name=='EXIT':g.close_menu();g.reset();g.mode='stop'
            else:g.menu_page='settings'
            break
    return True


def honey_frame(pg,canvas,rect):
    x,y,w,h=rect
    def points(inset):
        a,b=x+inset,y+inset;c,d=x+w-inset,y+h-inset;r=7
        return [(a+r,b),(c-r,b),(c-r,b+3),(c-3,b+3),(c-3,b+r),(c,b+r),(c,d-r),(c-3,d-r),(c-3,d-3),(c-r,d-3),(c-r,d),(a+r,d),(a+r,d-3),(a+3,d-3),(a+3,d-r),(a,d-r),(a,b+r),(a+3,b+r),(a+3,b+3),(a+r,b+3)]
    for inset,col in [(0,(113,54,31)),(3,(255,240,170)),(6,(255,179,50))]:pg.draw.polygon(canvas,col,points(inset))
    pg.draw.rect(canvas,(255,220,115),(x+12,y+7,w-24,3))
    for dx in (14,w-14):pg.draw.polygon(canvas,(217,124,39),[(x+dx,y+h/2-5),(x+dx+5,y+h/2),(x+dx,y+h/2+5),(x+dx-5,y+h/2)])
