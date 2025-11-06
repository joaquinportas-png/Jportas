# space_bluesky_plus.py
# Juego estilo Space Invaders con cielo azul, nubes parallax, SFX y música chiptune generados por código,
# power-ups y JEFES cada 3 oleadas.
# Autor: M365 Copilot para Joaquín Portas Alés

import math
import random
import sys
import time
import io
import wave
import struct
import pygame

# ------------------------------
# Configuración general
# ------------------------------
WIDTH, HEIGHT = 920, 700
FPS = 60

# Colores
WHITE = (255, 255, 255)
BLACK = (10, 10, 15)
SKY_TOP = (110, 175, 255)     # azul cielo arriba
SKY_BOTTOM = (200, 230, 255)  # azul cielo abajo
HUD_COLOR = (240, 250, 255)

# ------------------------------
# Utilidades de audio chiptune (sin dependencias externas)
# ------------------------------
SAMPLE_RATE = 44100
BITS = 16
CHANNELS = 1

NOTE_FREQS = {
    'C4':261.63,'Cs4':277.18,'Db4':277.18,'D4':293.66,'Ds4':311.13,'Eb4':311.13,'E4':329.63,'F4':349.23,'Fs4':369.99,
    'Gb4':369.99,'G4':392.00,'Gs4':415.30,'Ab4':415.30,'A4':440.00,'As4':466.16,'Bb4':466.16,'B4':493.88,
    'C5':523.25,'Cs5':554.37,'D5':587.33,'Ds5':622.25,'E5':659.25,'F5':698.46,'Fs5':739.99,'G5':783.99,'Gs5':830.61,'A5':880.00,
}

def _to_wav_bytes(samples, sample_rate=SAMPLE_RATE):
    """Convierte una lista/iterable de enteros 16-bit a un WAV en memoria (mono)."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = b''.join(struct.pack('<h', max(-32768, min(32767, int(s)))) for s in samples)
        wf.writeframes(data)
    buf.seek(0)
    return buf


def synth_square(freq, duration, volume=0.4, sample_rate=SAMPLE_RATE):
    n = int(duration * sample_rate)
    if freq <= 0:
        return [0]*n
    period = sample_rate / freq
    samples = []
    amp = int(32767 * volume)
    # Fade corto para evitar clicks
    fade = min(120, n//20)
    for i in range(n):
        t = (i % period) < (period/2)
        val = amp if t else -amp
        if i < fade:
            val = int(val * (i/fade))
        if i > n-fade:
            val = int(val * ((n-i)/fade))
        samples.append(val)
    return samples


def synth_noise(duration, volume=0.35, sample_rate=SAMPLE_RATE):
    n = int(duration * sample_rate)
    amp = int(32767 * volume)
    rnd = random.Random(123)
    samples = []
    fade = min(120, n//20)
    for i in range(n):
        val = rnd.randint(-amp, amp)
        if i < fade:
            val = int(val * (i/fade))
        if i > n-fade:
            val = int(val * ((n-i)/fade))
        samples.append(val)
    return samples


def mix_tracks(*tracks):
    """Suma listas de samples alineadas (mono) normalizando si hace falta."""
    if not tracks:
        return []
    L = max(len(t) for t in tracks)
    out = [0]*L
    for t in tracks:
        for i, s in enumerate(t):
            out[i] += s
    # normalización suave
    peak = max(1, max(abs(x) for x in out))
    if peak > 30000:
        scale = 30000/peak
        out = [int(x*scale) for x in out]
    return out


def build_melody(bpm=120):
    beat = 60.0/bpm
    # Patrón simple chiptune (A-minor feel)
    seq = [
        ('A4', beat*0.5), ('C5', beat*0.5), ('E5', beat*0.5), ('C5', beat*0.5),
        ('A4', beat*0.5), ('D5', beat*0.5), ('F5', beat*0.5), ('D5', beat*0.5),
        ('A4', beat*0.5), ('C5', beat*0.5), ('E5', beat*0.5), ('G5', beat*0.5),
        ('F5', beat*0.5), ('E5', beat*0.5), ('D5', beat*0.5), ('C5', beat*0.5),
    ]
    samples = []
    for note, dur in seq:
        f = NOTE_FREQS.get(note, 0)
        samples.extend(synth_square(f, dur, volume=0.22))
    # Batería 8-bit: bombo (ruido corto grave) en cada negra
    bar = int(4*beat*SAMPLE_RATE)
    drums = [0]*(len(samples))
    step = int(beat*SAMPLE_RATE)
    kick = synth_noise(beat*0.15, volume=0.25)
    for i in range(0, len(drums), step):
        for j, v in enumerate(kick):
            if i+j < len(drums):
                drums[i+j] += v
    return mix_tracks(samples, drums)


class Audio:
    def __init__(self):
        self.enabled = False
        self.channels = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)
            self.enabled = True
        except Exception:
            self.enabled = False
            return
        # Prepara SFX
        self.sfx = {}
        self.sfx['shoot'] = self._make_sound(synth_square(880, 0.06, 0.35))
        self.sfx['shoot_alt'] = self._make_sound(synth_square(1320, 0.05, 0.30))
        self.sfx['explosion'] = self._make_sound(mix_tracks(synth_noise(0.22, 0.35), synth_square(110, 0.22, 0.2)))
        self.sfx['power'] = self._make_sound(mix_tracks(synth_square(1200, 0.08, 0.25), synth_square(1600, 0.06, 0.20)))
        self.sfx['hit'] = self._make_sound(synth_square(220, 0.12, 0.30))
        self.sfx['boss_roar'] = self._make_sound(mix_tracks(synth_square(90, 0.5, 0.22), synth_noise(0.5, 0.12)))
        # Música (loop)
        music_samples = build_melody(bpm=132)
        self.music = self._make_sound(music_samples)
        self.music_channel = None

    def _make_sound(self, samples):
        if not self.enabled:
            return None
        bio = _to_wav_bytes(samples)
        try:
            snd = pygame.mixer.Sound(file=bio)
        except TypeError:
            # Compatibilidad: versiones que usan keyword 'file' o no
            snd = pygame.mixer.Sound(bio)
        return snd

    def play_music(self):
        if not self.enabled or self.music is None:
            return
        if self.music_channel is None or not self.music_channel.get_busy():
            self.music_channel = self.music.play(loops=-1)

    def stop_music(self):
        if self.music_channel:
            self.music_channel.stop()

    def pause_all(self):
        try:
            pygame.mixer.pause()
        except Exception:
            pass

    def resume_all(self):
        try:
            pygame.mixer.unpause()
        except Exception:
            pass

    def sfx_play(self, key):
        if not self.enabled:
            return
        s = self.sfx.get(key)
        if s:
            s.play()

# ------------------------------
# Utilidades de arte
# ------------------------------
def draw_vertical_gradient(surf, top_color, bottom_color):
    h = surf.get_height()
    w = surf.get_width()
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (w, y))


def make_player_surface(scale=1.0):
    w, h = int(60*scale), int(50*scale)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 60), (5, h-12, w-10, 10))
    hull = [
        (w*0.5, 0),
        (w*0.85, h*0.55),
        (w*0.65, h*0.75),
        (w*0.35, h*0.75),
        (w*0.15, h*0.55),
    ]
    pygame.draw.polygon(s, (70, 200, 255), hull)
    pygame.draw.polygon(s, (40, 120, 220), hull, width=3)
    pygame.draw.polygon(s, (50, 160, 240), [(w*0.15, h*0.55), (0, h*0.65), (w*0.35, h*0.75)])
    pygame.draw.polygon(s, (50, 160, 240), [(w*0.85, h*0.55), (w, h*0.65), (w*0.65, h*0.75)])
    pygame.draw.ellipse(s, (230, 245, 255), (w*0.38, h*0.18, w*0.24, h*0.28))
    pygame.draw.ellipse(s, (150, 210, 255), (w*0.40, h*0.20, w*0.20, h*0.24), width=2)
    return s


def make_enemy_surface(color=(255, 120, 120), scale=1.0, frame=0):
    w, h = int(44*scale), int(36*scale)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    bob = 2 if frame % 2 == 0 else 0
    body_rect = pygame.Rect(4, 6+bob, w-8, h-12)
    pygame.draw.rect(s, color, body_rect, border_radius=10)
    eye_y = 12 + bob
    pygame.draw.circle(s, (255, 255, 255), (int(w*0.35), eye_y), 5)
    pygame.draw.circle(s, (255, 255, 255), (int(w*0.65), eye_y), 5)
    pygame.draw.circle(s, (30, 30, 30), (int(w*0.35), eye_y), 2)
    pygame.draw.circle(s, (30, 30, 30), (int(w*0.65), eye_y), 2)
    for i in range(4):
        x = int(8 + i*(w-16)/3)
        pygame.draw.rect(s, (220, 90, 90), (x, h-10+bob, 8, 6), border_radius=3)
    return s


def make_boss_surface(scale=1.0, frame=0):
    w, h = int(200*scale), int(120*scale)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    bob = 2 if frame % 2 == 0 else 0
    pygame.draw.ellipse(s, (210, 80, 210), (10, 20+bob, w-20, h-40))
    pygame.draw.ellipse(s, (120, 40, 160), (10, 20+bob, w-20, h-40), width=4)
    # ojos múltiples
    for i in range(5):
        x = int(w*0.15 + i*(w*0.14))
        pygame.draw.circle(s, (255,255,255), (x, int(h*0.35)+bob), 10)
        pygame.draw.circle(s, (10,10,20), (x, int(h*0.35)+bob), 5)
    # pinchos
    for i in range(6):
        x = int(20 + i*((w-40)/5))
        pygame.draw.polygon(s, (240, 140, 240), [(x, h-10), (x+18, h-28), (x+36, h-10)])
    return s


def make_cloud_surface(size=(200, 100), opacity=180, seed=None):
    rnd = random.Random(seed) if seed is not None else random
    w, h = size
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    base = pygame.Surface((w, h), pygame.SRCALPHA)
    for _ in range(6):
        rw = rnd.randint(int(w*0.35), int(w*0.65))
        rh = rnd.randint(int(h*0.40), int(h*0.70))
        rx = rnd.randint(0, w-rw)
        ry = rnd.randint(0, h-rh)
        pygame.draw.ellipse(base, (255, 255, 255, opacity), (rx, ry, rw, rh))
    s.blit(base, (0, 0))
    return s

# ------------------------------
# Entidades
# ------------------------------
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, dy, color=(255, 250, 120), w=4, h=12, owner="player"):
        super().__init__()
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(self.image, color, (0, 0, w, h), border_radius=2)
        self.rect = self.image.get_rect(center=(x, y))
        self.dy = dy
        self.owner = owner
    def update(self, dt):
        self.rect.y += int(self.dy * dt)
        if self.rect.bottom < 0 or self.rect.top > HEIGHT:
            self.kill()


class Particle(pygame.sprite.Sprite):
    def __init__(self, pos, color, vel, lifetime=0.6):
        super().__init__()
        self.image = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (3, 3), 3)
        self.rect = self.image.get_rect(center=pos)
        self.vx, self.vy = vel
        self.lifetime = lifetime
        self.age = 0.0
    def update(self, dt):
        self.age += dt
        self.rect.x += int(self.vx * dt)
        self.rect.y += int(self.vy * dt)
        alpha = max(0, 255 - int(255 * (self.age / self.lifetime)))
        self.image.set_alpha(alpha)
        if self.age >= self.lifetime:
            self.kill()


class PowerUp(pygame.sprite.Sprite):
    TYPES = ("rapid", "shield")
    COLORS = {"rapid": (120, 255, 160), "shield": (160, 220, 255)}
    def __init__(self, pos, kind=None):
        super().__init__()
        if kind is None:
            kind = random.choice(PowerUp.TYPES)
        self.kind = kind
        self.image = pygame.Surface((22, 22), pygame.SRCALPHA)
        color = PowerUp.COLORS[self.kind]
        pygame.draw.circle(self.image, color, (11, 11), 11)
        pygame.draw.circle(self.image, (255, 255, 255), (11, 11), 10, width=2)
        icon = "R" if self.kind == "rapid" else "S"
        font = pygame.font.SysFont("arial", 14, bold=True)
        txt = font.render(icon, True, (20, 40, 60))
        self.image.blit(txt, txt.get_rect(center=(11, 11)))
        self.rect = self.image.get_rect(center=pos)
        self.vy = 120
    def update(self, dt):
        self.rect.y += int(self.vy * dt)
        if self.rect.top > HEIGHT:
            self.kill()


class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.base_image = make_player_surface(1.0)
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(midbottom=(WIDTH//2, HEIGHT-30))
        self.speed = 360
        self.cooldown = 0.35
        self.cool_timer = 0.0
        self.alive = True
        self.lives = 3
        self.rapid_timer = 0.0
        self.shield_timer = 0.0
        self.shield_radius = 40
    def update(self, dt, keys):
        if not self.alive:
            return
        dx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= self.speed * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += self.speed * dt
        self.rect.x += int(dx)
        self.rect.left = max(self.rect.left, 10)
        self.rect.right = min(self.rect.right, WIDTH-10)
        self.cool_timer = max(0.0, self.cool_timer - dt)
        if self.rapid_timer > 0:
            self.rapid_timer -= dt
        if self.shield_timer > 0:
            self.shield_timer -= dt
    def can_shoot(self):
        rate = 0.13 if self.rapid_timer > 0 else self.cooldown
        return self.cool_timer <= 0.0, rate
    def shoot(self, bullets_group, audio=None):
        ok, rate = self.can_shoot()
        if ok and self.alive:
            bullet = Bullet(self.rect.centerx, self.rect.top-8, dy=-620, color=(255, 250, 180), owner="player")
            bullets_group.add(bullet)
            self.cool_timer = rate
            if audio:
                audio.sfx_play('shoot' if self.rapid_timer<=0 else 'shoot_alt')
    def draw_extras(self, surf, t):
        if self.alive:
            flame_len = 10 + 6*math.sin(t*12)
            flame = pygame.Surface((12, int(18+flame_len)), pygame.SRCALPHA)
            pygame.draw.polygon(flame, (255, 200, 60, 210), [(6,0),(0,flame.get_height()),(12,flame.get_height())])
            surf.blit(flame, (self.rect.centerx-6, self.rect.bottom-6))
        if self.shield_timer > 0 and self.alive:
            alpha = 80 + int(40*math.sin(t*6))
            pygame.draw.circle(surf, (150, 210, 255, alpha), self.rect.center, self.shield_radius, width=3)


class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos, color, frame=0):
        super().__init__()
        self.frame = frame
        self.color = color
        self.image = make_enemy_surface(color, 1.0, frame)
        self.rect = self.image.get_rect(topleft=pos)
        self.alive = True
    def animate(self, frame):
        self.frame = frame
        self.image = make_enemy_surface(self.color, 1.0, self.frame)


class Boss(pygame.sprite.Sprite):
    def __init__(self, pos, level):
        super().__init__()
        self.frame = 0
        self.image = make_boss_surface(1.0, self.frame)
        self.rect = self.image.get_rect(center=pos)
        self.max_hp = 150 + 60*(max(1, level//3)-1)
        self.hp = self.max_hp
        self.speed_x = 120 + 10*(max(1, level//3)-1)
        self.dir = 1
        self.fire_timer = 0.0
        self.fire_cool = max(0.7, 1.2 - 0.05*(max(1, level//3)-1))
        self.anim_timer = 0.0
        self.phase_timer = 0.0
        self.phase = 1
    def update(self, dt):
        self.rect.x += int(self.speed_x * self.dir * dt)
        if self.rect.right >= WIDTH-10:
            self.dir = -1
            self.rect.right = WIDTH-10
        elif self.rect.left <= 10:
            self.dir = 1
            self.rect.left = 10
        self.anim_timer += dt
        if self.anim_timer >= 0.3:
            self.anim_timer = 0.0
            self.frame = 1 - self.frame
            self.image = make_boss_surface(1.0, self.frame)
        self.phase_timer += dt
        if self.phase_timer >= 6.0:
            self.phase_timer = 0.0
            self.phase = 2 if self.phase == 1 else 1

# ------------------------------
# Fondo con nubes parallax
# ------------------------------
class Sky:
    def __init__(self):
        self.bg = pygame.Surface((WIDTH, HEIGHT))
        draw_vertical_gradient(self.bg, SKY_TOP, SKY_BOTTOM)
        self.layers = []
        rnd = random.Random(42)
        for i, (speed, opacity, size_range, count) in enumerate([
            (20, 140, (180, 260), 5),
            (35, 170, (160, 220), 6),
            (60, 200, (120, 180), 7),
        ]):
            clouds = []
            for c in range(count):
                w = rnd.randint(size_range[0], size_range[1])
                h = rnd.randint(int(w*0.45), int(w*0.65))
                cloud = make_cloud_surface((w, h), opacity=opacity, seed=rnd.randint(0,99999))
                x = rnd.randint(0, WIDTH)
                y = rnd.randint(20, HEIGHT//2)
                clouds.append({"surf": cloud, "x": x, "y": y})
            self.layers.append({"speed": speed, "clouds": clouds})
    def update(self, dt):
        for layer in self.layers:
            spd = layer["speed"]
            for c in layer["clouds"]:
                c["x"] -= spd * dt
                if c["x"] + c["surf"].get_width() < 0:
                    c["x"] = WIDTH + random.randint(20, 200)
                    c["y"] = random.randint(20, HEIGHT//2)
    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        for layer in self.layers:
            for c in layer["clouds"]:
                surf.blit(c["surf"], (int(c["x"]), int(c["y"])) )

# ------------------------------
# Juego principal
# ------------------------------
class Game:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22)
        self.bigfont = pygame.font.SysFont("arial", 44, bold=True)

        self.sky = Sky()

        self.player = Player()
        self.player_group = pygame.sprite.GroupSingle(self.player)
        self.enemy_group = pygame.sprite.Group()
        self.boss_group = pygame.sprite.GroupSingle()
        self.bullets = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()
        self.particles = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()

        self.state = "menu"   # menu, playing, paused, gameover
        self.score = 0
        self.level = 1
        self.world_time = 0.0
        self.shake_timer = 0.0

        self.enemy_dir = 1
        self.enemy_speed = 40
        self.enemy_descend = 18
        self.enemy_fire_cool = 1.4
        self.enemy_fire_timer = 0.0
        self.anim_frame = 0
        self.anim_timer = 0.0

        self.audio = Audio()

        self.spawn_wave(self.level)

    def spawn_wave(self, level):
        self.enemy_group.empty()
        self.boss_group.empty()
        if level % 3 == 0:
            # Jefe
            boss = Boss((WIDTH//2, 140), level)
            self.boss_group.add(boss)
            if self.audio.enabled:
                self.audio.sfx_play('boss_roar')
            # Ajustar enemigos normales: ninguno en esta oleada
            self.enemy_speed = 0
            self.enemy_fire_cool = 1.0
            self.enemy_fire_timer = 0.0
            return
        rows = min(6, 3 + level)
        cols = 10
        margin_x = 70
        margin_y = 80
        start_x = 70
        start_y = 80
        palette = [
            (255, 120, 120), (255, 180, 120), (255, 230, 120),
            (160, 230, 140), (150, 200, 255), (210, 160, 255),
        ]
        for r in range(rows):
            for c in range(cols):
                x = start_x + c * margin_x
                y = start_y + r * margin_y
                color = palette[r % len(palette)]
                enemy = Enemy((x, y), color, frame=random.randint(0,1))
                self.enemy_group.add(enemy)
        self.enemy_dir = 1
        self.enemy_speed = 40 + 12 * (level-1)
        self.enemy_descend = 18 + 2 * (level-1)
        self.enemy_fire_cool = max(0.6, 1.4 - 0.08 * (level-1))
        self.enemy_fire_timer = 0.0

    def add_explosion(self, pos, base_color):
        for _ in range(16):
            angle = random.uniform(0, 2*math.pi)
            speed = random.uniform(120, 320)
            vx = math.cos(angle)*speed
            vy = math.sin(angle)*speed
            color = (
                min(255, int(base_color[0] + random.randint(-20, 20))),
                min(255, int(base_color[1] + random.randint(-20, 20))),
                min(255, int(base_color[2] + random.randint(-20, 20))),
            )
            self.particles.add(Particle(pos, color, (vx, vy), lifetime=random.uniform(0.35, 0.8)))
        self.shake_timer = 0.15
        if self.audio.enabled:
            self.audio.sfx_play('explosion')

    def enemy_fire(self):
        # enemigo aleatorio de la fila más baja por columna
        columns = {}
        for e in self.enemy_group:
            col = round(e.rect.x / 70)
            if col not in columns or e.rect.y > columns[col].rect.y:
                columns[col] = e
        shooters = list(columns.values())
        if shooters:
            e = random.choice(shooters)
            bullet = Bullet(e.rect.centerx, e.rect.bottom+6, dy=260, color=(255, 140, 140), owner="enemy")
            self.enemy_bullets.add(bullet)

    def boss_fire(self, boss):
        # Dos patrones: abanico y ráfaga dirigida
        if boss.phase == 1:
            # abanico
            for ang in range(-45, 46, 15):
                a = math.radians(90 + ang)
                vx = 220 * math.cos(a)
                vy = 220 * math.sin(a)
                b = Bullet(boss.rect.centerx, boss.rect.bottom-10, dy=0, color=(255, 120, 180), owner="enemy")
                # reutilizamos Bullet, pero le damos velocidad con vx via rect update manual
                b.vx = vx
                b.vy = vy
                def upd(selfb, dt, _orig=Bullet.update):
                    selfb.rect.x += int(selfb.vx * dt)
                    selfb.rect.y += int(selfb.vy * dt)
                    if selfb.rect.bottom < 0 or selfb.rect.top > HEIGHT or selfb.rect.right < 0 or selfb.rect.left > WIDTH:
                        selfb.kill()
                b.update = upd.__get__(b, Bullet)
                self.enemy_bullets.add(b)
        else:
            # ráfagas dirigidas al jugador
            if self.player.alive:
                px, py = self.player.rect.center
                for i in range(3):
                    dx = px - boss.rect.centerx
                    dy = py - boss.rect.centery
                    ang = math.atan2(dy, dx)
                    speed = 300 + i*40
                    vx = math.cos(ang)*speed
                    vy = math.sin(ang)*speed
                    b = Bullet(boss.rect.centerx, boss.rect.centery+20, dy=0, color=(255, 180, 120), owner="enemy")
                    b.vx, b.vy = vx, vy
                    def upd(selfb, dt, _orig=Bullet.update):
                        selfb.rect.x += int(selfb.vx * dt)
                        selfb.rect.y += int(selfb.vy * dt)
                        if selfb.rect.bottom < 0 or selfb.rect.top > HEIGHT or selfb.rect.right < 0 or selfb.rect.left > WIDTH:
                            selfb.kill()
                    b.update = upd.__get__(b, Bullet)
                    self.enemy_bullets.add(b)

    def handle_collisions(self, dt):
        # Balas del jugador contra enemigos
        hits = pygame.sprite.groupcollide(self.enemy_group, self.bullets, dokilla=False, dokillb=True)
        for enemy, bullets in hits.items():
            self.add_explosion(enemy.rect.center, enemy.color)
            enemy.kill()
            self.score += 10
            if random.random() < 0.12:
                self.powerups.add(PowerUp(enemy.rect.center))

        # Balas jugador contra BOSS
        if self.boss_group:
            boss = self.boss_group.sprite
            if boss:
                collisions = pygame.sprite.spritecollide(boss, self.bullets, dokill=True)
                for _ in collisions:
                    boss.hp -= 5
                    self.add_explosion((boss.rect.centerx + random.randint(-20,20), boss.rect.centery+random.randint(-20,20)), (250, 160, 250))
                    self.score += 2
                if boss and boss.hp <= 0:
                    self.add_explosion(boss.rect.center, (250, 160, 250))
                    self.score += 300
                    boss.kill()
                    if random.random() < 0.8:
                        self.powerups.add(PowerUp((WIDTH//2, 260), kind=random.choice(['rapid','shield'])))

        # Balas enemigas contra jugador
        if self.player.alive:
            phit = pygame.sprite.spritecollide(self.player, self.enemy_bullets, dokill=True)
            if phit:
                if self.player.shield_timer > 0:
                    self.add_explosion((self.player.rect.centerx, self.player.rect.top), (150, 210, 255))
                else:
                    self.player.lives -= 1
                    if self.audio.enabled:
                        self.audio.sfx_play('hit')
                    self.add_explosion(self.player.rect.center, (255, 200, 160))
                    if self.player.lives <= 0:
                        self.player.alive = False
                        self.state = "gameover"

        # Enemigos que llegan al suelo
        for e in list(self.enemy_group):
            if e.rect.bottom >= self.player.rect.top - 10:
                self.player.lives = 0
                self.player.alive = False
                self.state = "gameover"
                break

        # Player con powerups
        if self.player.alive:
            got = pygame.sprite.spritecollide(self.player, self.powerups, dokill=True)
            for p in got:
                if p.kind == "rapid":
                    self.player.rapid_timer = 8.0
                elif p.kind == "shield":
                    self.player.shield_timer = 6.0
                if self.audio.enabled:
                    self.audio.sfx_play('power')

    def update_enemies(self, dt):
        # Si hay boss, actualiza boss y su fuego
        if self.boss_group:
            boss = self.boss_group.sprite
            if boss:
                boss.update(dt)
                boss.fire_timer -= dt
                if boss.fire_timer <= 0:
                    self.boss_fire(boss)
                    boss.fire_timer = boss.fire_cool
            # avanzar oleada cuando no haya boss vivo
            if not self.boss_group and not self.enemy_group:
                self.level += 1
                self.spawn_wave(self.level)
            return

        # Oleada normal
        if not self.enemy_group:
            self.level += 1
            self.spawn_wave(self.level)
            return

        move_x = self.enemy_speed * self.enemy_dir * dt
        shift_down = False
        min_x = min(e.rect.left for e in self.enemy_group)
        max_x = max(e.rect.right for e in self.enemy_group)

        if max_x + move_x >= WIDTH - 20:
            self.enemy_dir = -1
            shift_down = True
        elif min_x + move_x <= 20:
            self.enemy_dir = 1
            shift_down = True

        for e in self.enemy_group:
            e.rect.x += int(self.enemy_speed * self.enemy_dir * dt)
            if shift_down:
                e.rect.y += self.enemy_descend

        self.anim_timer += dt
        if self.anim_timer >= 0.35:
            self.anim_timer = 0.0
            self.anim_frame = 1 - self.anim_frame
            for e in self.enemy_group:
                e.animate(self.anim_frame)

        self.enemy_fire_timer -= dt
        if self.enemy_fire_timer <= 0:
            self.enemy_fire()
            self.enemy_fire_timer = self.enemy_fire_cool

    def draw_hud(self, surf):
        lives_surf = self.font.render(f"Vidas: {self.player.lives}", True, HUD_COLOR)
        score_surf = self.font.render(f"Puntos: {self.score}", True, HUD_COLOR)
        lvl_surf = self.font.render(f"Oleada: {self.level}", True, HUD_COLOR)
        surf.blit(lives_surf, (16, 10))
        surf.blit(score_surf, (16, 36))
        surf.blit(lvl_surf, (16, 62))
        if self.player.rapid_timer > 0:
            t = self.font.render(f"Ráfaga: {self.player.rapid_timer:0.1f}s", True, (160, 255, 190))
            surf.blit(t, (WIDTH-200, 10))
        if self.player.shield_timer > 0:
            t = self.font.render(f"Escudo: {self.player.shield_timer:0.1f}s", True, (180, 220, 255))
            surf.blit(t, (WIDTH-200, 36))
        # barra de vida del boss
        if self.boss_group:
            boss = self.boss_group.sprite
            if boss:
                bar_w = WIDTH - 200
                bar_h = 18
                x = 100
                y = 18
                pygame.draw.rect(surf, (60, 30, 80), (x, y, bar_w, bar_h), border_radius=6)
                pct = max(0.0, min(1.0, boss.hp / boss.max_hp))
                pygame.draw.rect(surf, (220, 120, 240), (x, y, int(bar_w*pct), bar_h), border_radius=6)
                lbl = self.font.render("Jefe", True, (255, 230, 255))
                surf.blit(lbl, (x+4, y-4))

    def draw_center_text(self, lines, small=False):
        total_h = 0
        rendered = []
        for i, (txt, color) in enumerate(lines):
            f = self.font if small else self.bigfont
            s = f.render(txt, True, color)
            rendered.append(s)
            total_h += s.get_height() + (10 if not small else 6)
        y = HEIGHT//2 - total_h//2
        for s in rendered:
            self.screen.blit(s, s.get_rect(center=(WIDTH//2, y + s.get_height()//2)))
            y += s.get_height() + (10 if not small else 6)

    def run(self):
        while True:
            dt_ms = self.clock.tick(FPS)
            dt = dt_ms / 1000.0
            self.world_time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if self.state == "menu":
                    if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.reset()
                        self.state = "playing"
                elif self.state == "playing":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                        self.state = "paused"
                        if self.audio.enabled:
                            self.audio.pause_all()
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                        self.player.shoot(self.bullets, audio=self.audio)
                elif self.state == "paused":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                        self.state = "playing"
                        if self.audio.enabled:
                            self.audio.resume_all()
                elif self.state == "gameover":
                    if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.reset()
                        self.state = "playing"

            keys = pygame.key.get_pressed()

            # Update
            self.sky.update(dt)

            if self.state == "playing":
                if self.audio.enabled:
                    self.audio.play_music()
                self.player.update(dt, keys)
                if (keys[pygame.K_SPACE] or keys[pygame.K_UP]) and self.player.rapid_timer > 0:
                    self.player.shoot(self.bullets, audio=self.audio)
                self.bullets.update(dt)
                self.enemy_bullets.update(dt)
                self.powerups.update(dt)
                self.particles.update(dt)
                self.update_enemies(dt)
                self.handle_collisions(dt)
            else:
                self.particles.update(dt*0.6)
                self.powerups.update(dt*0.6)

            # Screen shake
            ox = oy = 0
            if self.shake_timer > 0:
                self.shake_timer -= dt
                amp = 4
                ox = int((random.random()-0.5) * 2 * amp)
                oy = int((random.random()-0.5) * 2 * amp)

            # Draw
            self.sky.draw(self.screen)
            for g in (self.powerups, self.enemy_group, self.boss_group, self.bullets, self.enemy_bullets, self.player_group, self.particles):
                for spr in g:
                    self.screen.blit(spr.image, spr.rect.move(ox, oy))
            self.player.draw_extras(self.screen, self.world_time)

            self.draw_hud(self.screen)

            if self.state == "menu":
                self.draw_center_text([
                    ("SPACE BLUE SKY +", (255, 255, 255)),
                    ("", WHITE),
                    ("Flechas/A-D mover, Espacio disparar", (235, 245, 255)),
                    ("P pausar", (235, 245, 255)),
                    ("ENTER/ESPACIO para empezar", (255, 255, 180)),
                ])
            elif self.state == "paused":
                self.draw_center_text([
                    ("PAUSA", (255, 255, 255)),
                    ("Pulsa P para reanudar", (255, 255, 180)),
                ])
            elif self.state == "gameover":
                self.draw_center_text([
                    ("GAME OVER", (255, 180, 180)),
                    (f"Puntuación: {self.score}", (235, 245, 255)),
                    (f"Oleada alcanzada: {self.level}", (235, 245, 255)),
                    ("ENTER/ESPACIO para reiniciar", (255, 255, 180)),
                ])

            pygame.display.flip()

    def reset(self):
        self.player = Player()
        self.player_group = pygame.sprite.GroupSingle(self.player)
        self.enemy_group.empty()
        self.boss_group.empty()
        self.bullets.empty()
        self.enemy_bullets.empty()
        self.particles.empty()
        self.powerups.empty()
        self.score = 0
        self.level = 1
        self.spawn_wave(self.level)
        self.state = "playing"
        if self.audio.enabled:
            self.audio.play_music()


def main():
    pygame.init()
    pygame.display.set_caption("Space Blue Sky + - Invaders")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    game = Game(screen)
    game.run()


if __name__ == "__main__":
    main()
