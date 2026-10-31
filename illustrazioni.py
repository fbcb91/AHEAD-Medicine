"""Illustrazioni evocative per le schede della Library (SVG 1200x400).

Un motivo per area, con variazioni deterministiche per sostanza (sfondo, posizione,
colori). Se esiste una foto in img/schede/<slug>.* o img/aree/<area>.*, build.py usa
quella al posto dell'illustrazione.
"""
import hashlib
import math

W, H = 1200, 400
S = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'


def _rng(seed):
    h = hashlib.sha256(seed.encode()).digest()
    return lambda i: h[i % 32] / 255


def _recupero(c, r):
    track = ''.join(f'<path d="M560 {420 + i * 34} Q 880 {170 + i * 30} 1220 {250 + i * 30}" stroke="#ffffff{"30" if i else "55"}" stroke-width="{3 if i else 4}" {S}/>' for i in range(4))
    x0 = 120 + r(3) * 80
    pulse = f'M{x0} 210 H{x0 + 330} l24 -70 l30 140 l26 -110 l18 40 H{x0 + 700}'
    return track + f'<path d="{pulse}" stroke="{c}" stroke-width="5" {S}/><circle cx="{x0 + 700}" cy="210" r="9" fill="{c}"/>'


def _ormoni(c, r):
    waves = ''
    for k in range(3):
        amp, ph = 34 + k * 12, r(k + 4) * 6
        pts = ' '.join(f'{x},{200 + k * 46 - 46 + amp * math.sin(x / (90 + k * 25) + ph):.0f}' for x in range(0, W + 1, 20))
        waves += f'<polyline points="{pts}" stroke="{c if k == 1 else "#ffffff40"}" stroke-width="{4 if k == 1 else 2.5}" {S}/>'
    cx = 820 + r(9) * 140
    gland = f'<circle cx="{cx}" cy="200" r="64" fill="{c}" fill-opacity=".18" stroke="{c}" stroke-width="3"/>'
    dots = ''.join(f'<circle cx="{cx + 110 * math.cos(a):.0f}" cy="{200 + 110 * math.sin(a):.0f}" r="{5 + (i % 3) * 2}" fill="#ffffff" fill-opacity=".6"/>' for i, a in enumerate(x * math.pi / 5 for x in range(10)))
    return waves + gland + dots


def _muscolo(c, r):
    x = 720 + r(2) * 120
    bell = (f'<rect x="{x}" y="186" width="300" height="28" rx="14" fill="#ffffff" fill-opacity=".75"/>'
            + ''.join(f'<rect x="{x + dx}" y="{200 - hh / 2}" width="34" height="{hh}" rx="10" fill="{c}"/>' for dx, hh in [(-50, 170), (-6, 130), (272, 130), (316, 170)]))
    fibers = ''.join(f'<path d="M{80 + i * 34} {330 - 40 * math.sin(i / 3)} C {150 + i * 34} 200 {80 + i * 34} 140 {170 + i * 34} 60" stroke="{c if i % 4 == 0 else "#ffffff26"}" stroke-width="{4 if i % 4 == 0 else 2}" {S}/>' for i in range(14))
    return fibers + bell


def _metabolismo(c, r):
    cx = 860 + r(5) * 120
    plate = (f'<circle cx="{cx}" cy="200" r="130" fill="#ffffff" fill-opacity=".08" stroke="#ffffff55" stroke-width="3"/>'
             f'<circle cx="{cx}" cy="200" r="88" stroke="{c}" stroke-width="4" {S}/>'
             f'<path d="M{cx - 190} 90 v230 M{cx - 205} 90 v60 q15 25 30 0 v-60" stroke="#ffffff99" stroke-width="4" {S}/>'
             f'<path d="M{cx + 190} 90 c26 20 26 90 0 110 v120" stroke="#ffffff99" stroke-width="4" {S}/>')
    pts = [(90 + i * 70, 110 + i * 22 + (r(i + 11) - .5) * 30) for i in range(8)]
    curve = f'<polyline points="{" ".join(f"{x:.0f},{y:.0f}" for x, y in pts)}" stroke="{c}" stroke-width="4" {S}/>' + ''.join(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="7" fill="{c}"/>' for x, y in pts)
    return curve + plate


def _longevita(c, r):
    cx = 300 + r(4) * 120
    rings = ''.join(f'<ellipse cx="{cx}" cy="200" rx="{30 + i * 26 + (r(i) - .5) * 10:.0f}" ry="{26 + i * 23 + (r(i + 3) - .5) * 10:.0f}" stroke="{c if i % 3 == 0 else "#ffffff30"}" stroke-width="{3.5 if i % 3 == 0 else 2}" {S}/>' for i in range(7))
    hx = 900 + r(8) * 80
    glass = (f'<path d="M{hx - 70} 60 h140 M{hx - 70} 340 h140 M{hx - 58} 60 c0 80 116 100 116 140 s-116 60 -116 140 M{hx + 58} 60 c0 80 -116 100 -116 140 s116 60 116 140" stroke="#ffffffaa" stroke-width="4" {S}/>'
             f'<path d="M{hx - 38} 300 q38 -46 76 0 z" fill="{c}"/><path d="M{hx - 30} 110 q30 34 60 0 z" fill="{c}" fill-opacity=".7"/>')
    return rings + glass


def _pelle(c, r):
    layers = ''
    for k in range(5):
        y = 150 + k * 40
        ph = r(k) * 3
        d = f'M0 {y} ' + ' '.join(f'Q {x + 75} {y + (24 if (x // 150 + k) % 2 else -24) * (1 + ph / 6):.0f} {x + 150} {y}' for x in range(0, W, 150))
        layers += f'<path d="{d}" stroke="{c if k == 1 else "#ffffff" + ("40" if k else "70")}" stroke-width="{4 if k == 1 else 2.5}" {S}/>'
    drops = ''.join(f'<path d="M{x} {y} c-14 22 -14 34 0 34 s14 -12 0 -34z" fill="{c}" fill-opacity="{.5 + .4 * r(i)}"/>' for i, (x, y) in enumerate([(820, 60), (900, 92), (980, 52), (1060, 84)]))
    return layers + drops


def _neuro(c, r):
    nodes = [(560 + 560 * r(i), 50 + 300 * r(i + 9)) for i in range(16)]
    edges = ''.join(f'<line x1="{a[0]:.0f}" y1="{a[1]:.0f}" x2="{b[0]:.0f}" y2="{b[1]:.0f}" stroke="#ffffff30" stroke-width="2"/>'
                    for i, a in enumerate(nodes) for b in nodes[i + 1:] if math.dist(a, b) < 170)
    dots = ''.join(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{6 + (i % 3) * 3}" fill="{c if i % 4 == 0 else "#ffffffaa"}"/>' for i, (x, y) in enumerate(nodes))
    pts = ' '.join(f'{x},{200 + (60 * math.exp(-((x - 300) / 140) ** 2)) * math.sin(x / 9):.0f}' for x in range(40, 560, 6))
    return edges + dots + f'<polyline points="{pts}" stroke="{c}" stroke-width="3.5" {S}/>'


def _immunita(c, r):
    sx = 860 + r(3) * 100
    shield = f'<path d="M{sx} 50 l120 40 v90 c0 90 -70 140 -120 160 c-50 -20 -120 -70 -120 -160 v-90z" fill="{c}" fill-opacity=".16" stroke="{c}" stroke-width="4" {S}/><path d="M{sx - 40} 200 l30 30 l60 -70" stroke="#ffffffcc" stroke-width="6" {S}/>'
    cells = ''
    for i in range(6):
        x, y, rad = 120 + i * 105 + r(i) * 30, 110 + r(i + 7) * 180, 22 + r(i + 13) * 18
        spikes = ''.join(f'<line x1="{x + rad * math.cos(a):.0f}" y1="{y + rad * math.sin(a):.0f}" x2="{x + (rad + 12) * math.cos(a):.0f}" y2="{y + (rad + 12) * math.sin(a):.0f}" stroke="#ffffff55" stroke-width="3" stroke-linecap="round"/>' for a in (k * math.pi / 4 for k in range(8)))
        cells += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rad:.0f}" fill="#ffffff" fill-opacity=".1" stroke="#ffffff66" stroke-width="2.5"/>' + spikes
    return cells + shield


def _sessualita(c, r):
    cx = 820 + r(2) * 100
    circles = (f'<circle cx="{cx - 70}" cy="200" r="120" fill="{c}" fill-opacity=".16" stroke="{c}" stroke-width="4"/>'
               f'<circle cx="{cx + 70}" cy="200" r="120" fill="#ffffff" fill-opacity=".06" stroke="#ffffffaa" stroke-width="3"/>')
    orbit = ''.join(f'<circle cx="{220 + 160 * math.cos(a) * 1.6:.0f}" cy="{200 + 110 * math.sin(a):.0f}" r="{5 + (i % 4) * 3}" fill="{c if i % 3 == 0 else "#ffffff99"}"/>' for i, a in enumerate(k * math.pi / 7 + r(5) for k in range(14)))
    return f'<ellipse cx="220" cy="200" rx="256" ry="110" stroke="#ffffff30" stroke-width="2" {S}/>' + orbit + circles


MOTIFS = {'Recupero': _recupero, 'Ormoni': _ormoni, 'Massa muscolare': _muscolo, 'Metabolismo': _metabolismo, 'Longevità': _longevita,
          'Pelle': _pelle, 'Neuro': _neuro, 'Immunità': _immunita, 'Sessualità e fertilità': _sessualita}


def cover_svg(seed, category, color, label):
    r = _rng(seed)
    gid = 'cv' + hashlib.sha256(seed.encode()).hexdigest()[:6]
    blobs = ''.join(f'<circle cx="{W * r(i + 20):.0f}" cy="{H * r(i + 24):.0f}" r="{140 + 160 * r(i + 28):.0f}" fill="{color if i % 2 == 0 else "#5f8794"}" fill-opacity="{.22 if i % 2 == 0 else .18}" filter="url(#{gid}b)"/>' for i in range(3))
    dots = f'<pattern id="{gid}d" width="28" height="28" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.4" fill="#ffffff" fill-opacity=".09"/></pattern>'
    return (f'<svg class="cover-art" viewBox="0 0 {W} {H}" role="img" aria-label="{label}" preserveAspectRatio="xMidYMid slice">'
            f'<defs><linearGradient id="{gid}g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#10191d"/><stop offset="1" stop-color="#1d3239"/></linearGradient>'
            f'<filter id="{gid}b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="60"/></filter>{dots}</defs>'
            f'<rect width="{W}" height="{H}" fill="url(#{gid}g)"/>{blobs}<rect width="{W}" height="{H}" fill="url(#{gid}d)"/>'
            f'{MOTIFS[category](color, r)}</svg>')
