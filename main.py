# main.py (web)
import asyncio, math, random, sys
import pygame

WIDTH, HEIGHT = 960, 540
WHITE=(255,255,255); SKY_TOP=(110,175,255); SKY_BOTTOM=(200,230,255); HUD_COLOR=(240,250,255)

import io, wave, struct
SAMPLE_RATE=44100

def _to_wav_bytes(samples, sr=SAMPLE_RATE):
    buf=io.BytesIO();
    with wave.open(buf,'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(b''.join(struct.pack('<h', max(-32768,min(32767,int(s)))) for s in samples))
    buf.seek(0); return buf

NOTE={'A4':440.0,'C5':523.25,'D5':587.33,'E5':659.25,'F5':698.46,'G5':783.99,'A5':880.00}

def sq(freq,dur,vol=0.35):
    n=int(dur*SAMPLE_RATE)
    if freq<=0: return [0]*n
    period=SAMPLE_RATE/freq; amp=int(32767*vol); fade=min(120,n//20)
    out=[]
    for i in range(n):
        v=amp if (i%period)<(period/2) else -amp
        if i<fade: v=int(v*(i/fade))
        if i>n-fade: v=int(v*((n-i)/fade))
        out.append(v)
    return out

def noise(dur,vol=0.28):
    import random
    n=int(dur*SAMPLE_RATE); amp=int(32767*vol); fade=min(120,n//20)
    out=[]
    for i in range(n):
        v=random.randint(-amp,amp)
        if i<fade: v=int(v*(i/fade))
        if i>n-fade: v=int(v*((n-i)/fade))
        out.append(v)
    return out

def build_song():
    beat=60/132
    seq=[('A4',.5),('C5',.5),('E5',.5),('C5',.5),('A4',.5),('D5',.5),('F5',.5),('D5',.5)]*2
    melody=[]
    for n,d in seq: melody+=sq(NOTE[n],d,0.22)
    drums=[0]*len(melody); step=int(beat*SAMPLE_RATE); k=noise(beat*0.15,0.22)
    for i in range(0,len(drums),step):
        for j,v in enumerate(k):
            if i+j<len(drums): drums[i+j]+=v
    peak=max(1,max(abs(x+y) for x,y in zip(melody,drums)))
    mix=[int((x+y)*30000/peak) for x,y in zip(melody,drums)]
    return _to_wav_bytes(mix)

class Audio:
    def __init__(self):
        self.enabled=False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)
            self.enabled=True
        except Exception:
            self.enabled=False; return
        try:
            self.s_shoot=pygame.mixer.Sound(file=_to_wav_bytes(sq(880,0.06,0.35)))
            self.s_shoot2=pygame.mixer.Sound(file=_to_wav_bytes(sq(1320,0.05,0.30)))
            self.s_expl=pygame.mixer.Sound(file=_to_wav_bytes([x+y for x,y in zip(noise(0.22),sq(110,0.22,0.2))]))
            self.s_power=pygame.mixer.Sound(file=_to_wav_bytes([x+y for x,y in zip(sq(1200,0.08,0.25),sq(1600,0.06,0.20))]))
            self.s_hit=pygame.mixer.Sound(file=_to_wav_bytes(sq(220,0.12,0.30)))
            self.s_roar=pygame.mixer.Sound(file=_to_wav_bytes([x+y for x,y in zip(sq(90,0.5,0.22),noise(0.5,0.12))]))
            self.music=pygame.mixer.Sound(file=build_song())
        except TypeError:
            self.s_shoot=pygame.mixer.Sound(_to_wav_bytes(sq(880,0.06,0.35)))
            self.s_shoot2=pygame.mixer.Sound(_to_wav_bytes(sq(1320,0.05,0.30)))
            self.s_expl=pygame.mixer.Sound(_to_wav_bytes([x+y for x,y in zip(noise(0.22),sq(110,0.22,0.2))]))
            self.s_power=pygame.mixer.Sound(_to_wav_bytes([x+y for x,y in zip(sq(1200,0.08,0.25),sq(1600,0.06,0.20))]))
            self.s_hit=pygame.mixer.Sound(_to_wav_bytes(sq(220,0.12,0.30)))
            self.s_roar=pygame.mixer.Sound(_to_wav_bytes([x+y for x,y in zip(sq(90,0.5,0.22),noise(0.5,0.12))]))
            self.music=pygame.mixer.Sound(build_song())
        self.music_ch=None
    def play_music(self):
        if self.enabled and (not self.music_ch or not self.music_ch.get_busy()):
            self.music_ch=self.music.play(loops=-1)
    def pause_all(self):
        try: pygame.mixer.pause()
        except: pass
    def resume_all(self):
        try: pygame.mixer.unpause()
        except: pass
    def s(self,k):
        if not self.enabled: return
        mp={'shoot':self.s_shoot,'shoot2':self.s_shoot2,'expl':self.s_expl,'power':self.s_power,'hit':self.s_hit,'roar':self.s_roar}
        s=mp.get(k)
        if s: s.play()

# Arte utilitario

def draw_vertical_gradient(surf, top, bottom):
    h=surf.get_height(); w=surf.get_width()
    for y in range(h):
        t=y/max(1,h-1)
        r=int(top[0]+(bottom[0]-top[0])*t)
        g=int(top[1]+(bottom[1]-top[1])*t)
        b=int(top[2]+(bottom[2]-top[2])*t)
        pygame.draw.line(surf,(r,g,b),(0,y),(w,y))


def make_player_surface():
    w,h=60,50
    s=pygame.Surface((w,h),pygame.SRCALPHA)
    pygame.draw.ellipse(s,(0,0,0,60),(5,h-12,w-10,10))
    hull=[(w*.5,0),(w*.85,h*.55),(w*.65,h*.75),(w*.35,h*.75),(w*.15,h*.55)]
    pygame.draw.polygon(s,(70,200,255),hull)
    pygame.draw.polygon(s,(40,120,220),hull,3)
    pygame.draw.polygon(s,(50,160,240),[(w*.15,h*.55),(0,h*.65),(w*.35,h*.75)])
    pygame.draw.polygon(s,(50,160,240),[(w*.85,h*.55),(w,h*.65),(w*.65,h*.75)])
    pygame.draw.ellipse(s,(230,245,255),(w*.38,h*.18,w*.24,h*.28))
    pygame.draw.ellipse(s,(150,210,255),(w*.40,h*.20,w*.20,h*.24),2)
    return s


def make_enemy_surface(color=(255,120,120),frame=0):
    w,h=44,36
    s=pygame.Surface((w,h),pygame.SRCALPHA)
    bob=2 if frame%2==0 else 0
    pygame.draw.rect(s,color,pygame.Rect(4,6+bob,w-8,h-12),border_radius=10)
    eye_y=12+bob
    pygame.draw.circle(s,(255,255,255),(int(w*.35),eye_y),5)
    pygame.draw.circle(s,(255,255,255),(int(w*.65),eye_y),5)
    pygame.draw.circle(s,(30,30,30),(int(w*.35),eye_y),2)
    pygame.draw.circle(s,(30,30,30),(int(w*.65),eye_y),2)
    for i in range(4):
        x=int(8+i*(w-16)/3)
        pygame.draw.rect(s,(220,90,90),(x,h-10+bob,8,6),border_radius=3)
    return s


def make_boss_surface(frame=0):
    w,h=200,120
    s=pygame.Surface((w,h),pygame.SRCALPHA)
    bob=2 if frame%2==0 else 0
    pygame.draw.ellipse(s,(210,80,210),(10,20+bob,w-20,h-40))
    pygame.draw.ellipse(s,(120,40,160),(10,20+bob,w-20,h-40),4)
    for i in range(5):
        x=int(w*0.15+i*(w*0.14))
        pygame.draw.circle(s,(255,255,255),(x,int(h*0.35)+bob),10)
        pygame.draw.circle(s,(10,10,20),(x,int(h*0.35)+bob),5)
    for i in range(6):
        x=int(20+i*((w-40)/5))
        pygame.draw.polygon(s,(240,140,240),[(x,h-10),(x+18,h-28),(x+36,h-10)])
    return s

class Bullet(pygame.sprite.Sprite):
    def __init__(self,x,y,dy,color,owner='player'):
        super().__init__()
        self.image=pygame.Surface((4,12),pygame.SRCALPHA)
        pygame.draw.rect(self.image,color,(0,0,4,12),border_radius=2)
        self.rect=self.image.get_rect(center=(x,y))
        self.dy=dy; self.owner=owner
    def update(self,dt):
        self.rect.y+=int(self.dy*dt)
        if self.rect.bottom<0 or self.rect.top>HEIGHT: self.kill()

class Particle(pygame.sprite.Sprite):
    def __init__(self,pos,color,vel,lifetime=0.6):
        super().__init__()
        self.image=pygame.Surface((6,6),pygame.SRCALPHA)
        pygame.draw.circle(self.image,color,(3,3),3)
        self.rect=self.image.get_rect(center=pos)
        self.vx,self.vy=vel; self.lifetime=lifetime; self.age=0
    def update(self,dt):
        self.age+=dt; self.rect.x+=int(self.vx*dt); self.rect.y+=int(self.vy*dt)
        alpha=max(0,255-int(255*(self.age/self.lifetime))); self.image.set_alpha(alpha)
        if self.age>=self.lifetime: self.kill()

class PowerUp(pygame.sprite.Sprite):
    TYPES=("rapid","shield")
    COLORS={"rapid":(120,255,160),"shield":(160,220,255)}
    def __init__(self,pos,kind=None):
        super().__init__()
        self.kind=kind or random.choice(PowerUp.TYPES)
        self.image=pygame.Surface((22,22),pygame.SRCALPHA)
        color=PowerUp.COLORS[self.kind]
        pygame.draw.circle(self.image,color,(11,11),11)
        pygame.draw.circle(self.image,(255,255,255),(11,11),10,2)
        font=pygame.font.SysFont('arial',14,True)
        icon='R' if self.kind=='rapid' else 'S'
        t=font.render(icon,True,(20,40,60)); self.image.blit(t,t.get_rect(center=(11,11)))
        self.rect=self.image.get_rect(center=pos); self.vy=120
    def update(self,dt):
        self.rect.y+=int(self.vy*dt)
        if self.rect.top>HEIGHT: self.kill()

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image=make_player_surface(); self.rect=self.image.get_rect(midbottom=(WIDTH//2,HEIGHT-30))
        self.speed=360; self.cooldown=0.35; self.cool_timer=0
        self.alive=True; self.lives=3
        self.rapid_timer=0; self.shield_timer=0; self.shield_radius=40
    def update(self,dt,move_dir):
        if not self.alive: return
        self.rect.x+=int(move_dir*self.speed*dt)
        self.rect.left=max(self.rect.left,10); self.rect.right=min(self.rect.right,WIDTH-10)
        self.cool_timer=max(0,self.cool_timer-dt)
        if self.rapid_timer>0: self.rapid_timer-=dt
        if self.shield_timer>0: self.shield_timer-=dt
    def can_shoot(self):
        rate=0.13 if self.rapid_timer>0 else self.cooldown
        return self.cool_timer<=0, rate
    def shoot(self,grp,audio=None):
        ok,rate=self.can_shoot()
        if ok and self.alive:
            grp.add(Bullet(self.rect.centerx,self.rect.top-8,-620,(255,250,180),'player'))
            self.cool_timer=rate
            if audio: audio.s('shoot' if self.rapid_timer<=0 else 'shoot2')
    def draw_extras(self,surf,t):
        flame_len=10+6*math.sin(t*12)
        fl=pygame.Surface((12,int(18+flame_len)),pygame.SRCALPHA)
        pygame.draw.polygon(fl,(255,200,60,210),[(6,0),(0,fl.get_height()),(12,fl.get_height())])
        surf.blit(fl,(self.rect.centerx-6,self.rect.bottom-6))
        if self.shield_timer>0:
            alpha=80+int(40*math.sin(t*6))
            pygame.draw.circle(surf,(150,210,255,alpha),self.rect.center,self.shield_radius,3)

class Enemy(pygame.sprite.Sprite):
    def __init__(self,pos,color,frame=0):
        super().__init__(); self.frame=frame; self.color=color
        self.image=make_enemy_surface(color,frame); self.rect=self.image.get_rect(topleft=pos)
    def animate(self,frame): self.frame=frame; self.image=make_enemy_surface(self.color,frame)

class Boss(pygame.sprite.Sprite):
    def __init__(self,pos,level):
        super().__init__(); self.frame=0; self.image=make_boss_surface(0); self.rect=self.image.get_rect(center=pos)
        self.max_hp=150+60*(max(1,level//3)-1); self.hp=self.max_hp
        self.speed_x=120+10*(max(1,level//3)-1); self.dir=1
        self.fire_timer=0; self.fire_cool=max(0.7,1.2-0.05*(max(1,level//3)-1))
        self.anim_timer=0; self.phase_timer=0; self.phase=1
    def update(self,dt):
        self.rect.x+=int(self.speed_x*self.dir*dt)
        if self.rect.right>=WIDTH-10: self.dir=-1; self.rect.right=WIDTH-10
        elif self.rect.left<=10: self.dir=1; self.rect.left=10
        self.anim_timer+=dt
        if self.anim_timer>=0.3:
            self.anim_timer=0; self.frame=1-self.frame; self.image=make_boss_surface(self.frame)
        self.phase_timer+=dt
        if self.phase_timer>=6: self.phase=2 if self.phase==1 else 1; self.phase_timer=0

class Sky:
    def __init__(self):
        self.bg=pygame.Surface((WIDTH,HEIGHT)); draw_vertical_gradient(self.bg,SKY_TOP,SKY_BOTTOM)
        self.layers=[]; rnd=random.Random(42)
        for speed,opacity,srng,count in [(20,140,(180,260),4),(35,170,(160,220),5),(60,200,(120,180),6)]:
            clouds=[]
            for _ in range(count):
                w=rnd.randint(srng[0],srng[1]); h=rnd.randint(int(w*.45),int(w*.65))
                s=pygame.Surface((w,h),pygame.SRCALPHA)
                base=pygame.Surface((w,h),pygame.SRCALPHA)
                for __ in range(6):
                    import random as rr
                    rw=rr.randint(int(w*.35),int(w*.65)); rh=rr.randint(int(h*.40),int(h*.70))
                    rx=rr.randint(0,w-rw); ry=rr.randint(0,h-rh)
                    pygame.draw.ellipse(base,(255,255,255,opacity),(rx,ry,rw,rh))
                s.blit(base,(0,0))
                x=rnd.randint(0,WIDTH); y=rnd.randint(20,HEIGHT//2)
                clouds.append({'surf':s,'x':x,'y':y})
            self.layers.append({'speed':speed,'clouds':clouds})
    def update(self,dt):
        for layer in self.layers:
            sp=layer['speed']
            for c in layer['clouds']:
                c['x']-=sp*dt
                if c['x']+c['surf'].get_width()<0:
                    c['x']=WIDTH+random.randint(20,200); c['y']=random.randint(20,HEIGHT//2)
    def draw(self,surf):
        surf.blit(self.bg,(0,0))
        for layer in self.layers:
            for c in layer['clouds']:
                surf.blit(c['surf'],(int(c['x']),int(c['y'])))

class Game:
    def __init__(self,screen):
        self.screen=screen; self.clock=pygame.time.Clock()
        self.font=pygame.font.SysFont('arial',22); self.bigfont=pygame.font.SysFont('arial',40,True)
        self.sky=Sky(); self.player=Player();
        self.player_group=pygame.sprite.GroupSingle(self.player)
        self.enemy_group=pygame.sprite.Group(); self.boss_group=pygame.sprite.GroupSingle()
        self.bullets=pygame.sprite.Group(); self.enemy_bullets=pygame.sprite.Group(); self.particles=pygame.sprite.Group(); self.powerups=pygame.sprite.Group()
        self.state='menu'; self.score=0; self.level=1; self.world_time=0; self.shake_timer=0
        self.enemy_dir=1; self.enemy_speed=40; self.enemy_descend=18; self.enemy_fire_cool=1.4; self.enemy_fire_timer=0; self.anim_frame=0; self.anim_timer=0
        self.audio=Audio(); self.brand='JPortas Desing Vintage'
        self.logo=None
        try:
            self.logo=pygame.image.load('assets/icon.png').convert_alpha()
        except Exception: self.logo=None
        self.spawn_wave(self.level)

    def spawn_wave(self,level):
        self.enemy_group.empty(); self.boss_group.empty()
        if level%3==0:
            boss=Boss((WIDTH//2,140),level); self.boss_group.add(boss); self.enemy_speed=0; self.enemy_fire_cool=1.0; self.enemy_fire_timer=0
            if self.audio.enabled: self.audio.s('roar')
            return
        rows=min(6,3+level); cols=10; mx=70; my=70; sx=60; sy=70
        palette=[(255,120,120),(255,180,120),(255,230,120),(160,230,140),(150,200,255),(210,160,255)]
        for r in range(rows):
            for c in range(cols):
                x=sx+c*mx; y=sy+r*my
                self.enemy_group.add(Enemy((x,y),palette[r%len(palette)],frame=random.randint(0,1)))
        self.enemy_dir=1; self.enemy_speed=40+12*(level-1); self.enemy_descend=18+2*(level-1); self.enemy_fire_cool=max(0.6,1.4-0.08*(level-1)); self.enemy_fire_timer=0

    def add_explosion(self,pos,col):
        for _ in range(16):
            a=random.uniform(0,2*math.pi); s=random.uniform(120,320)
            vx=math.cos(a)*s; vy=math.sin(a)*s
            c=(min(255,int(col[0]+random.randint(-20,20))),min(255,int(col[1]+random.randint(-20,20))),min(255,int(col[2]+random.randint(-20,20))))
            self.particles.add(Particle(pos,c,(vx,vy),lifetime=random.uniform(0.35,0.8)))
        self.shake_timer=0.15
        if self.audio.enabled: self.audio.s('expl')

    def enemy_fire(self):
        columns={}
        for e in self.enemy_group:
            col=round(e.rect.x/70)
            if col not in columns or e.rect.y>columns[col].rect.y: columns[col]=e
        shooters=list(columns.values())
        if shooters:
            e=random.choice(shooters)
            self.enemy_bullets.add(Bullet(e.rect.centerx,e.rect.bottom+6,260,(255,140,140),'enemy'))

    def boss_fire(self,boss):
        if boss.phase==1:
            for ang in range(-45,46,15):
                a=math.radians(90+ang); vx=220*math.cos(a); vy=220*math.sin(a)
                b=Bullet(boss.rect.centerx,boss.rect.bottom-10,0,(255,120,180),'enemy'); b.vx=vx; b.vy=vy
                def upd(selfb,dt):
                    selfb.rect.x+=int(selfb.vx*dt); selfb.rect.y+=int(selfb.vy*dt)
                    if selfb.rect.bottom<0 or selfb.rect.top>HEIGHT or selfb.rect.right<0 or selfb.rect.left>WIDTH: selfb.kill()
                b.update=upd.__get__(b,Bullet); self.enemy_bullets.add(b)
        else:
            if self.player.alive:
                px,py=self.player.rect.center
                for i in range(3):
                    dx=px-boss.rect.centerx; dy=py-boss.rect.centery
                    ang=math.atan2(dy,dx); sp=300+i*40
                    vx=math.cos(ang)*sp; vy=math.sin(ang)*sp
                    b=Bullet(boss.rect.centerx,boss.rect.centery+20,0,(255,180,120),'enemy'); b.vx,b.vy=vx,vy
                    def upd(selfb,dt):
                        selfb.rect.x+=int(selfb.vx*dt); selfb.rect.y+=int(selfb.vy*dt)
                        if selfb.rect.bottom<0 or selfb.rect.top>HEIGHT or selfb.rect.right<0 or selfb.rect.left>WIDTH: selfb.kill()
                    b.update=upd.__get__(b,Bullet); self.enemy_bullets.add(b)

    def handle_collisions(self):
        hits=pygame.sprite.groupcollide(self.enemy_group,self.bullets,False,True)
        for enemy,bullets in hits.items():
            self.add_explosion(enemy.rect.center,enemy.color); enemy.kill(); self.score+=10
            if random.random()<0.12: self.powerups.add(PowerUp(enemy.rect.center))
        if self.boss_group:
            boss=self.boss_group.sprite
            if boss:
                collisions=pygame.sprite.spritecollide(boss,self.bullets,True)
                for _ in collisions:
                    boss.hp-=5; self.add_explosion((boss.rect.centerx+random.randint(-20,20),boss.rect.centery+random.randint(-20,20)),(250,160,250)); self.score+=2
                if boss and boss.hp<=0:
                    self.add_explosion(boss.rect.center,(250,160,250)); self.score+=300; boss.kill()
                    if random.random()<0.8: self.powerups.add(PowerUp((WIDTH//2,260),kind=random.choice(['rapid','shield'])))
        if self.player.alive:
            phit=pygame.sprite.spritecollide(self.player,self.enemy_bullets,True)
            if phit:
                if self.player.shield_timer>0:
                    self.add_explosion((self.player.rect.centerx,self.player.rect.top),(150,210,255))
                else:
                    self.player.lives-=1; self.add_explosion(self.player.rect.center,(255,200,160))
                    if self.audio.enabled: self.audio.s('hit')
                    if self.player.lives<=0: self.player.alive=False; self.state='gameover'
        for e in list(self.enemy_group):
            if e.rect.bottom>=self.player.rect.top-10:
                self.player.lives=0; self.player.alive=False; self.state='gameover'; break
        if self.player.alive:
            got=pygame.sprite.spritecollide(self.player,self.powerups,True)
            for p in got:
                if p.kind=='rapid': self.player.rapid_timer=8.0
                elif p.kind=='shield': self.player.shield_timer=6.0
                if self.audio.enabled: self.audio.s('power')

    def draw_hud(self):
        s1=self.font.render(f"Vidas: {self.player.lives}",True,HUD_COLOR)
        s2=self.font.render(f"Puntos: {self.score}",True,HUD_COLOR)
        s3=self.font.render(f"Oleada: {self.level}",True,HUD_COLOR)
        self.screen.blit(s1,(16,8)); self.screen.blit(s2,(16,32)); self.screen.blit(s3,(16,56))
        if self.player.rapid_timer>0:
            t=self.font.render(f"Ráfaga: {self.player.rapid_timer:0.1f}s",True,(160,255,190)); self.screen.blit(t,(WIDTH-210,8))
        if self.player.shield_timer>0:
            t=self.font.render(f"Escudo: {self.player.shield_timer:0.1f}s",True,(180,220,255)); self.screen.blit(t,(WIDTH-210,32))
        brand=self.font.render('JPortas Desing Vintage',True,(224,186,94))
        self.screen.blit(brand,(WIDTH-brand.get_width()-12,HEIGHT-24))
        if self.boss_group:
            boss=self.boss_group.sprite
            if boss:
                bar_w=WIDTH-200; bar_h=16; x=100; y=12
                pygame.draw.rect(self.screen,(60,30,80),(x,y,bar_w,bar_h),border_radius=6)
                pct=max(0.0,min(1.0,boss.hp/boss.max_hp))
                pygame.draw.rect(self.screen,(220,120,240),(x,y,int(bar_w*pct),bar_h),border_radius=6)

    def draw_center_text(self,lines,small=False):
        y=HEIGHT//2 - sum((self.bigfont if not small else self.font).size(t)[1]+(10 if not small else 6) for t,_ in lines)//2
        for txt,col in lines:
            f=self.bigfont if not small else self.font
            s=f.render(txt,True,col)
            self.screen.blit(s,s.get_rect(center=(WIDTH//2,y+s.get_height()//2)))
            y+=s.get_height()+(10 if not small else 6)

    def frame(self,dt):
        self.world_time+=dt
        move_dir=0
        keys=pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: move_dir-=1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: move_dir+=1

        for ev in pygame.event.get():
            if ev.type==pygame.QUIT:
                pygame.quit(); sys.exit()
            if self.state=='menu' and (ev.type==pygame.KEYDOWN or ev.type==pygame.MOUSEBUTTONDOWN):
                self.reset(); self.state='playing'
            elif self.state=='playing' and ev.type==pygame.KEYDOWN and ev.key==pygame.K_p:
                self.state='paused'; self.audio.pause_all()
            elif self.state=='playing' and ev.type==pygame.MOUSEBUTTONDOWN:
                self.player.shoot(self.bullets,self.audio)
            elif self.state=='gameover' and (ev.type==pygame.KEYDOWN or ev.type==pygame.MOUSEBUTTONDOWN):
                self.reset(); self.state='playing'

        self.sky.update(dt)

        if self.state=='playing':
            self.audio.play_music()
            self.player.update(dt,move_dir)
            if (keys[pygame.K_SPACE] or keys[pygame.K_UP]) and self.player.rapid_timer>0:
                self.player.shoot(self.bullets,self.audio)
            self.bullets.update(dt); self.enemy_bullets.update(dt); self.powerups.update(dt); self.particles.update(dt)
            if self.boss_group:
                boss=self.boss_group.sprite
                if boss:
                    boss.update(dt); boss.fire_timer-=dt
                    if boss.fire_timer<=0:
                        self.boss_fire(boss); boss.fire_timer=boss.fire_cool
                if not self.boss_group and not self.enemy_group:
                    self.level+=1; self.spawn_wave(self.level)
            else:
                if not self.enemy_group: self.level+=1; self.spawn_wave(self.level)
                else:
                    move_x=self.enemy_speed*dt; shift=False
                    min_x=min(e.rect.left for e in self.enemy_group); max_x=max(e.rect.right for e in self.enemy_group)
                    if max_x+move_x>=WIDTH-20: self.enemy_dir=-1; shift=True
                    elif min_x-move_x<=20: self.enemy_dir=1; shift=True
                    for e in self.enemy_group:
                        e.rect.x+=int(self.enemy_speed*self.enemy_dir*dt)
                        if shift: e.rect.y+=self.enemy_descend
                    self.anim_timer+=dt
                    if self.anim_timer>=0.35:
                        self.anim_timer=0; self.anim_frame=1-self.anim_frame
                        for e in self.enemy_group: e.animate(self.anim_frame)
                    self.enemy_fire_timer-=dt
                    if self.enemy_fire_timer<=0:
                        self.enemy_fire(); self.enemy_fire_timer=self.enemy_fire_cool
            self.handle_collisions()

        ox=oy=0
        if hasattr(self,'shake_timer') and self.shake_timer>0:
            self.shake_timer-=dt; import random as rr
            amp=4; ox=int((rr.random()-0.5)*2*amp); oy=int((rr.random()-0.5)*2*amp)

        self.sky.draw(self.screen)
        for g in (self.powerups, self.enemy_group, self.boss_group, self.bullets, self.enemy_bullets, self.player_group, self.particles):
            for spr in g: self.screen.blit(spr.image, spr.rect.move(ox,oy))
        self.player.draw_extras(self.screen,getattr(self,'world_time',0))
        self.draw_hud()
        if self.state=='menu':
            self.draw_center_text([("SPACE BLUE SKY +",WHITE),(self.brand,(224,186,94)),("Haz clic/toca para empezar",(255,255,180))])
            if self.logo:
                lg=pygame.transform.smoothscale(self.logo,(140,140)); self.screen.blit(lg,(960-160,20))
        elif self.state=='paused':
            self.draw_center_text([("PAUSA",WHITE),("Pulsa P para reanudar",(255,255,180))])
        elif self.state=='gameover':
            self.draw_center_text([("GAME OVER",(255,180,180)),(f"Puntuación: {self.score}",WHITE),(f"Oleada: {self.level}",WHITE),("Clic/tocar para reiniciar",(255,255,180))])
        pygame.display.flip()

    def reset(self):
        self.__init__(self.screen)

async def main():
    pygame.init()
    screen=pygame.display.set_mode((WIDTH,HEIGHT))
    pygame.display.set_caption('Space Blue Sky + — JPortas Desing Vintage (Web)')
    g=Game(screen)
    last=pygame.time.get_ticks()
    while True:
        now=pygame.time.get_ticks(); dt=(now-last)/1000.0; last=now
        g.frame(dt)
        await asyncio.sleep(0)

asyncio.run(main())
