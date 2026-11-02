"""Genera le pagine statiche del sito a partire da data/schede/*.json.

Uso: python3 build.py
Ogni file JSON in data/schede/ è una scheda. Il build si interrompe se una
scheda non rispetta lo schema (vedi validate()).
"""
from pathlib import Path
from html import escape
from urllib.parse import quote
import json
import unicodedata
import hashlib
import math
import re
import sys

ROOT = Path(__file__).parent

# --- SEO ---------------------------------------------------------------
# Indirizzo pubblico del sito: usato per canonical, Open Graph, sitemap e dati
# strutturati. Quando ci sarà il dominio definitivo basta cambiare questa riga
# (e aggiungere un redirect 301 dal vecchio dominio su Vercel).
SITE_URL = 'https://aheadmedicine.vercel.app'
SITE_NAME = 'AHEAD Medicine'
# False rimette "noindex" su tutte le pagine.
INDEXABLE = True
# Codice di verifica di Google Search Console (meta tag), se si sceglie quel metodo.
GSC_VERIFICATION = ''
DATA_DIR = ROOT / 'data' / 'schede'

# Etichette dello stato regolatorio. La classe CSS colora il pallino del badge.
STATUS = {
    'ue': ('Autorizzato in UE', 'approved'),
    'extra_ue': ('Autorizzato solo fuori UE', 'partial'),
    'trial': ('In sperimentazione clinica', 'pending'),
    'ritirato': ('Ex medicinale, ritirato', 'pending'),
    'sperimentale': ('Sperimentale', 'pending'),
    'integratore': ('Integratore / cosmetico', 'pending'),
}
EVIDENCE_ROWS = [
    ('in_vitro', 'In vitro'),
    ('animale', 'Modelli animali'),
    ('osservazionale', 'Studi osservazionali sull’uomo'),
    ('rct', 'Studi clinici randomizzati (RCT)'),
    ('autorizzato', 'Medicinale autorizzato'),
]
LEVELS = {'si': 'Presenti', 'limitato': 'Limitate', 'no': 'Assenti'}
AUTH_LEVELS = {'si': 'Sì', 'limitato': 'Parziale', 'no': 'No'}
CATEGORIES = ['Recupero', 'Ormoni', 'Massa muscolare', 'Metabolismo', 'Longevità', 'Pelle', 'Neuro', 'Immunità', 'Sessualità e fertilità']
SERVICES = ['Peptidi', 'TRT', 'GLP-1', 'Longevity & Performance', 'Capelli', 'Salute sessuale', 'Menopausa', 'Recupero e sport']
KINDS = {'peptide': ('Peptide', 'peptidi'), 'sostanza': ('Altra sostanza', 'sostanze')}
# Da dove provengono le dosi riportate nella sezione "Come si assume".
DOSING_BASIS = {
    'rcp': 'Fonte: foglietto illustrativo / RCP approvato in UE',
    'extra_ue': 'Fonte: foglietto approvato fuori UE',
    'studi': 'Fonte: studi clinici pubblicati — nessuna dose approvata',
    'nessuna': 'Nessuna dose validata nell’uomo',
}
SOURCE_TYPES = {'regolatorio': 'Autorità', 'studio': 'Studi', 'revisione': 'Revisione', 'azienda': 'Azienda', 'notizia': 'Notizia'}
REQUIRED = ['name', 'slug', 'kind', 'category', 'status', 'service', 'focus', 'tagline', 'evidence_summary',
            'what', 'unknown', 'risk', 'reg', 'evidence', 'dosing', 'sources', 'review']
FEATURED = ['bpc-157', 'semaglutide', 'retatrutide', 'testosterone', 'rapamicina', 'mots-c']
MONTHS = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']


def validate(p, fname):
    errors = [f'manca il campo "{k}"' for k in REQUIRED if k not in p]
    if errors:
        return errors
    if p['slug'] != fname:
        errors.append(f'slug "{p["slug"]}" diverso dal nome del file')
    if not re.fullmatch(r'[a-z0-9-]+', p['slug']):
        errors.append('slug non valido')
    if p['kind'] not in KINDS:
        errors.append(f'kind "{p["kind"]}" non valido')
    if p['status'] not in STATUS:
        errors.append(f'status "{p["status"]}" non valido')
    if p['category'] not in CATEGORIES:
        errors.append(f'categoria "{p["category"]}" non valida')
    if p['service'] is not None and p['service'] not in SERVICES:
        errors.append(f'servizio "{p["service"]}" non valido')
    for c in p.get('extra_categories', []):
        if c not in CATEGORIES or c == p['category']:
            errors.append(f'categoria aggiuntiva "{c}" non valida')
    for key, _ in EVIDENCE_ROWS:
        row = p['evidence'].get(key)
        if not row or row.get('level') not in LEVELS or not row.get('note'):
            errors.append(f'evidenza "{key}" mancante o non valida')
    dosing = p['dosing']
    if dosing.get('basis') not in DOSING_BASIS or not dosing.get('route') or not dosing.get('text'):
        errors.append('dosing deve avere basis valido, route e text')
    if p['status'] in ('sperimentale', 'integratore', 'trial', 'ritirato') and dosing.get('basis') == 'rcp':
        errors.append('dosing.basis "rcp" ammesso solo per medicinali autorizzati')
    if not all(isinstance(x, str) and x for x in p.get('key_points', [])):
        errors.append('key_points deve essere una lista di frasi')
    for k in ('faq', 'timeline'):
        if not all(isinstance(x, list) and len(x) == 2 and all(x) for x in p.get(k, [])):
            errors.append(f'{k} deve essere una lista di coppie [a, b]')
    if 'mechanism' in p and not p['mechanism']:
        errors.append('mechanism vuoto')
    if not p['sources']:
        errors.append('serve almeno una fonte specifica')
    for s in p['sources']:
        if s.get('type') not in SOURCE_TYPES or not s.get('url', '').startswith('https://'):
            errors.append(f'fonte non valida: {s}')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', p['review'].get('checked') or ''):
        errors.append('review.checked deve essere una data AAAA-MM-GG')
    return errors


def load():
    data, problems = [], []
    for f in sorted(DATA_DIR.glob('*.json')):
        p = json.loads(f.read_text(encoding='utf-8'))
        problems += [f'{f.name}: {e}' for e in validate(p, f.stem)]
        data.append(p)
    if problems:
        sys.exit('Schede non valide:\n  ' + '\n  '.join(problems))
    data.sort(key=lambda p: (CATEGORIES.index(p['category']), p['name'].lower()))
    for i, p in enumerate(data, 1):
        p['num'] = f'{i:02d}'
        p['url'] = f'/{KINDS[p["kind"]][1]}/{p["slug"]}/'
        term = quote(p.get('search_term', p['name']))
        p['pubmed'] = 'https://pubmed.ncbi.nlm.nih.gov/?term=' + term
        p['trials'] = 'https://clinicaltrials.gov/search?term=' + term
    return data


def it_date(iso):
    y, m, d = iso.split('-')
    return f'{int(d)} {MONTHS[int(m) - 1]} {y}'


DATA = load()
N = len(DATA)


ART_DIR = ROOT / 'data' / 'articoli'


def inline_md(text):
    text = escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    def link(m):
        label, url = m.group(1), m.group(2)
        ext = '' if url.startswith('/') else ' target="_blank" rel="noopener noreferrer"'
        return f'<a href="{url}"{ext}>{label}</a>'
    return re.sub(r'\[(.+?)\]\((\S+?)\)', link, text)


def render_md(md):
    """Markdown minimo: ## / ### titoli, elenchi con "- ", paragrafi, **grassetto**, [link](url)."""
    html, para, items = [], [], []
    def flush():
        if para:
            html.append(f'<p>{inline_md(" ".join(para))}</p>'); para.clear()
        if items:
            html.append('<ul>' + ''.join(f'<li>{inline_md(i)}</li>' for i in items) + '</ul>'); items.clear()
    for line in md.splitlines():
        line = line.rstrip()
        if not line:
            flush()
        elif line.startswith('### '):
            flush(); html.append(f'<h3>{inline_md(line[4:])}</h3>')
        elif line.startswith('## '):
            flush(); html.append(f'<h2 id="{slugify(line[3:])}">{inline_md(line[3:])}</h2>')
        elif line.startswith('- '):
            if para:
                flush()
            items.append(line[2:])
        else:
            para.append(line)
    flush()
    return ''.join(html)


def load_articles():
    arts, problems = [], []
    slugs = {p['slug'] for p in DATA}
    for f in sorted(ART_DIR.glob('*.md')):
        raw = f.read_text(encoding='utf-8')
        m = re.match(r'---\n(.*?)\n---\n(.*)', raw, re.S)
        if not m:
            problems.append(f'{f.name}: manca il front-matter'); continue
        meta = dict(line.split(': ', 1) for line in m.group(1).splitlines() if ': ' in line)
        a = {'slug': f.stem, 'body': m.group(2), **meta}
        for k in ('title', 'type', 'date', 'description'):
            if not a.get(k):
                problems.append(f'{f.name}: manca "{k}"')
        if a.get('type') not in ('Guida', 'News'):
            problems.append(f'{f.name}: type deve essere Guida o News')
        a['related'] = [x.strip() for x in a.get('related', '').split(',') if x.strip()]
        problems += [f'{f.name}: scheda correlata "{x}" inesistente' for x in a['related'] if x not in slugs]
        a['service'] = a.get('service') or None
        if a['service'] and a['service'] not in SERVICES:
            problems.append(f'{f.name}: servizio "{a["service"]}" non valido')
        arts.append(a)
    if problems:
        sys.exit('Articoli non validi:\n  ' + '\n  '.join(problems))
    return sorted(arts, key=lambda a: (a['date'], a['title']), reverse=True)


ARTICLES = load_articles()


def article_card(a):
    return f'<a class="article-card" href="/articoli/{a["slug"]}/"><span class="article-meta">{escape(a["type"].upper())} · {it_date(a["date"])}</span><h3>{escape(a["title"])}</h3><p>{escape(a["description"])}</p><span class="article-more">Leggi ↗</span></a>'

NAV = '''<a class="logo" href="/" aria-label="AHEAD — home"><span class="logo-mark">A<span class="logo-spark">✳</span></span><span class="logo-word">AHEAD<span class="logo-dot">.</span><small>MEDICINE / PROJECT</small></span></a><nav class="nav-links" aria-label="Navigazione principale"><a href="/library/">Library</a><a href="/consulenze/">Consulenze</a><a href="/articoli/">Articoli</a><a href="/metodo/">Metodo</a></nav><a href="/inizia/" class="nav-cta start-link">Trova il tuo medico <span>↗</span></a><button class="mobile-menu" type="button" aria-label="Apri menu" aria-expanded="false">☰</button>'''
FOOTER = '''<footer class="footer"><div class="wrap footer-main"><div><a class="footer-logo" href="/">AHEAD<span>.</span></a><p>Medicina emergente, senza scorciatoie.</p><p class="muted">Nome e identità visiva provvisori.</p></div><div class="footer-links"><a href="/library/">Library</a><a href="/peptidi/">Peptidi</a><a href="/sostanze/">Farmaci e sostanze</a><a href="/consulenze/">Consulenze</a><a href="/articoli/">Articoli</a><a href="/metodo/">Metodo editoriale</a><a href="/privacy/">Privacy</a></div></div><div class="wrap footer-bottom"><span>© 2026 AHEAD · Progetto in fase di esplorazione</span><span>Contenuti informativi. Nessun servizio sanitario attualmente erogato.</span></div></footer>'''
MODAL = '''<div class="modal-backdrop" id="interest-modal" hidden><div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" aria-describedby="modal-description"><button type="button" class="modal-close" data-close-modal aria-label="Chiudi">×</button><div class="eyebrow dark-ink">MANIFESTAZIONE DI INTERESSE</div><h2 id="modal-title">Restiamo in contatto.</h2><p id="modal-description">Stiamo valutando questo servizio. Lascia la tua email per ricevere aggiornamenti sul progetto.</p><form id="interest-form"><label for="interest-email">La tua email</label><input type="email" id="interest-email" name="email" placeholder="nome@email.it" autocomplete="email" required maxlength="254"><div class="hp-field" aria-hidden="true"><label for="interest-website">Lascia vuoto questo campo</label><input type="text" id="interest-website" name="website" tabindex="-1" autocomplete="off"></div><label class="checkline"><input id="interest-consent" type="checkbox" required><span>Acconsento a ricevere comunicazioni email relative al progetto. Ho letto l'<a href="/privacy/" target="_blank">informativa privacy</a>.</span></label><button class="btn btn-dark full" type="submit" id="form-submit">Ricevi aggiornamenti <span>↗</span></button><p class="form-message" id="form-message" role="status" aria-live="polite"></p></form><p class="note">Non chiediamo informazioni sulla tua salute. Iscrizione gratuita, cancellazione possibile in ogni momento.</p></div></div>'''
def asset_version(name):
    # Cambia a ogni modifica del file: i browser scaricano subito la versione nuova.
    import hashlib
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()[:10]


CSS_V, JS_V = asset_version('styles.css'), asset_version('app.js')
HEAD_META = f'''<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#10171b"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap"><link rel="stylesheet" href="/styles.css?v={CSS_V}"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/og/apple-touch-icon.png"><script defer src="/app.js?v={JS_V}"></script>'''


SITEMAP = []   # (path, lastmod)
OG_JOBS = []   # immagini Open Graph da generare: vedi scripts/og-images.mjs
BUILD_DATE = '2026-10-30'


def slugify(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')


def abs_url(path):
    return SITE_URL + path


def clip(text, n=158):
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= n:
        return text
    return text[:n].rsplit(' ', 1)[0].rstrip(',;:') + '…'


def crumbs_ld(crumbs):
    return {'@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i, 'name': name, 'item': abs_url(path)} for i, (name, path) in enumerate(crumbs, 1)]}


def og_image(key, title, kicker):
    """Registra un'immagine social per la pagina e restituisce il suo percorso (o quella generica)."""
    OG_JOBS.append({'file': f'og/{key}.jpg', 'title': title, 'kicker': kicker})
    return f'/og/{key}.jpg' if (ROOT / 'og' / f'{key}.jpg').exists() else '/og/default.jpg'


def page(title, desc, body, path, *, schema=(), crumbs=None, image='/og/default.jpg', og_type='website', indexable=True, lastmod=BUILD_DATE):
    full_title = title if SITE_NAME in title or 'AHEAD' in title else f'{title} | AHEAD'
    indexable = indexable and INDEXABLE
    robots = '<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">' if indexable else '<meta name="robots" content="noindex,nofollow">'
    graph = list(schema) + ([crumbs_ld(crumbs)] if crumbs else [])
    ld = ''
    if graph:
        data = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
        ld = f'<script type="application/ld+json">{data}</script>'
    verify = f'<meta name="google-site-verification" content="{GSC_VERIFICATION}">' if GSC_VERIFICATION else ''
    url = abs_url(path)
    meta = (f'<title>{escape(full_title)}</title><meta name="description" content="{escape(desc, quote=True)}">{robots}'
            f'<link rel="canonical" href="{url}">'
            f'<meta property="og:type" content="{og_type}"><meta property="og:site_name" content="{SITE_NAME}"><meta property="og:locale" content="it_IT">'
            f'<meta property="og:title" content="{escape(title, quote=True)}"><meta property="og:description" content="{escape(desc, quote=True)}">'
            f'<meta property="og:url" content="{url}"><meta property="og:image" content="{abs_url(image)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
            f'<meta name="twitter:card" content="summary_large_image">{verify}{ld}')
    if indexable:
        SITEMAP.append((path, lastmod))
    return f'''<!doctype html><html lang="it"><head>{HEAD_META}{meta}</head><body><a class="skip-link" href="#main">Vai al contenuto</a><div class="topbar">PROGETTO IN FASE DI SVILUPPO <span class="topbar-sep">/</span> SERVIZI NON ANCORA DISPONIBILI</div><header class="site-header"><div class="wrap header-inner">{NAV}</div></header><main id="main">{body}</main>{FOOTER}{MODAL}</body></html>'''


ORG_LD = {'@type': 'Organization', '@id': SITE_URL + '/#org', 'name': SITE_NAME, 'url': SITE_URL + '/', 'logo': SITE_URL + '/og/logo.png',
          'description': 'Informazione scientifica su peptidi, GLP-1, ormoni e longevità e una rete di medici esperti in videoconsulenza (servizio in avvio).'}
WEBSITE_LD = {'@type': 'WebSite', '@id': SITE_URL + '/#website', 'name': SITE_NAME, 'url': SITE_URL + '/', 'inLanguage': 'it-IT', 'publisher': {'@id': SITE_URL + '/#org'}}


def webpage_ld(kind, path, name, desc, **extra):
    return {'@type': kind, '@id': abs_url(path) + '#page', 'url': abs_url(path), 'name': name, 'description': desc, 'inLanguage': 'it-IT',
            'isPartOf': {'@id': SITE_URL + '/#website'}, **extra}


def itemlist_ld(items):
    return {'@type': 'ItemList', 'itemListElement': [{'@type': 'ListItem', 'position': i, 'url': abs_url(u), 'name': n} for i, (n, u) in enumerate(items, 1)]}


def faq_ld(pairs):
    return {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in pairs]}


def write(rel, html):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding='utf-8')


def status_badge(p):
    label, cls = STATUS[p['status']]
    return f'<span class="status {cls}"><i></i>{escape(label)}</span>'


CAT_COLORS = {'Recupero': '#6fb39b', 'Ormoni': '#d9a066', 'Massa muscolare': '#d9826b', 'Metabolismo': '#7fb4d3', 'Longevità': '#a99be0',
              'Pelle': '#e3a9bf', 'Neuro': '#8ea6e8', 'Immunità': '#93c98c', 'Sessualità e fertilità': '#de94ad'}


def molecule_svg(seed, color, dark=False, cls='mol-art'):
    """Illustrazione molecolare astratta e deterministica: stessa sostanza, stesso disegno."""
    h = hashlib.sha256(seed.encode()).digest()
    r = lambda i: h[i % 32] / 255
    n = 6 + h[0] % 4
    pts, ang = [(0.0, 0.0)], r(1) * 360
    for i in range(1, n):
        ang += (60 if h[i] % 2 else -60) + (r(i + 7) - .5) * 24
        d = 50 + r(i + 11) * 14
        pts.append((pts[-1][0] + d * math.cos(math.radians(ang)), pts[-1][1] + d * math.sin(math.radians(ang))))
    bonds = [(i - 1, i) for i in range(1, n)]
    for k in range(2 + h[3] % 2):                       # ramificazioni
        base = 1 + h[k + 20] % (n - 1)
        a = r(k + 24) * 360
        pts.append((pts[base][0] + 46 * math.cos(math.radians(a)), pts[base][1] + 46 * math.sin(math.radians(a))))
        bonds.append((base, len(pts) - 1))
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    scale = min(300 / max(max(xs) - min(xs), 1), 300 / max(max(ys) - min(ys), 1), 1.6)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    pts = [(200 + (x - cx) * scale, 200 + (y - cy) * scale) for x, y in pts]
    line = '#ffffff40' if dark else '#9fb3b6'
    gid = 'g' + h[:4].hex()
    out = [f'<svg class="{cls}" viewBox="0 0 400 400" aria-hidden="true" focusable="false"><defs><radialGradient id="{gid}" cx="35%" cy="35%"><stop offset="0" stop-color="#ffffff" stop-opacity=".9"/><stop offset=".45" stop-color="{color}"/><stop offset="1" stop-color="{color}" stop-opacity=".75"/></radialGradient></defs>']
    out += [f'<line x1="{pts[a][0]:.1f}" y1="{pts[a][1]:.1f}" x2="{pts[b][0]:.1f}" y2="{pts[b][1]:.1f}" stroke="{line}" stroke-width="3" stroke-linecap="round"/>' for a, b in bonds]
    core = h[5] % len(pts)
    for i, (x, y) in enumerate(pts):
        rad = 26 if i == core else 9 + h[(i + 13) % 32] % 9
        if i == core or h[(i + 2) % 32] % 3:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad}" fill="url(#{gid})"/>')
        else:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad}" fill="none" stroke="{color}" stroke-width="3"/>')
    return ''.join(out) + '</svg>'


_ICON = {
    'Peptidi': '<circle cx="10" cy="34" r="5"/><circle cx="24" cy="24" r="5"/><circle cx="38" cy="14" r="5"/><path d="M14 31l6-4M28 21l6-4"/>',
    'TRT': '<circle cx="20" cy="28" r="11"/><path d="M28 20l11-11M30 9h9v9"/>',
    'GLP-1': '<path d="M24 6c7 9 12 15 12 22a12 12 0 0 1-24 0c0-7 5-13 12-22z"/><path d="M18 30c2 3 5 4 8 3"/>',
    'Longevity & Performance': '<path d="M6 24c0-5 4-8 8-8 7 0 13 16 20 16 4 0 8-3 8-8s-4-8-8-8c-7 0-13 16-20 16-4 0-8-3-8-8z"/>',
    'Capelli': '<path d="M14 40c-4-10 4-14 0-26M24 40c-4-10 4-14 0-26M34 40c-4-10 4-14 0-26"/>',
    'Salute sessuale': '<path d="M24 40S8 30 8 19a8 8 0 0 1 16-3 8 8 0 0 1 16 3c0 11-16 21-16 21z"/>',
    'Menopausa': '<path d="M30 8a16 16 0 1 0 10 26A13 13 0 0 1 30 8z"/>',
    'Recupero e sport': '<path d="M27 5L11 27h12l-3 16 17-23H25z"/>',
}


def area_icon(name, cls='area-icon'):
    return f'<svg class="{cls}" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{_ICON[name]}</svg>' if name in _ICON else ''


PHOTO_EXT = ('.jpg', '.jpeg', '.png', '.webp')


def find_photo(folder, name):
    """Cerca img/<folder>/<name>.<ext> senza badare a maiuscole o spazi nel nome del file."""
    base = ROOT / 'img' / folder
    if base.is_dir():
        for f in sorted(base.iterdir()):
            if f.suffix.lower() in PHOTO_EXT and slugify(f.stem) == name:
                return f
    return None


def hero_photo(*candidates):
    """Foto a tutta larghezza per l'intestazione: la prima trovata tra (cartella, nome).
    Viene ridimensionata in WebP (1200 e 2400 px) in media/; il nome contiene l'hash
    della foto, quindi Pillow serve solo quando se ne aggiunge o cambia una."""
    for folder, name in candidates:
        src = find_photo(folder, name)
        if not src:
            continue
        digest = hashlib.sha256(src.read_bytes()).hexdigest()[:8]
        outs = {w: ROOT / 'media' / folder / f'{name}-{digest}-{w}.webp' for w in (1200, 2400)}
        if not all(o.exists() for o in outs.values()):
            from PIL import Image, ImageOps
            outs[1200].parent.mkdir(parents=True, exist_ok=True)
            for old in outs[1200].parent.glob(f'{name}-*.webp'):
                old.unlink()
            img = ImageOps.exif_transpose(Image.open(src)).convert('RGB')
            for w, out in outs.items():
                copy = img.copy()
                copy.thumbnail((w, w * 2))
                copy.save(out, 'WEBP', quality=78)
        srcset = ', '.join(f'/media/{folder}/{o.name} {w}w' for w, o in outs.items())
        return f'<img class="hero-photo" src="/media/{folder}/{outs[1200].name}" srcset="{srcset}" sizes="100vw" alt="" fetchpriority="high" decoding="async">'
    return ''


def evidence_pyramid():
    tiers = [('Medicinale autorizzato', '#10191d', '#fff'), ('Studi clinici randomizzati', '#2c4a55', '#fff'), ('Studi osservazionali', '#5f8794', '#fff'),
             ('Modelli animali', '#a9c3c8', '#10191d'), ('In vitro', '#dbe6e5', '#10191d')]
    out = ['<svg class="pyramid" viewBox="0 0 700 360" role="img" aria-label="Piramide delle prove: dal basso in vitro, modelli animali, studi osservazionali, studi clinici randomizzati, medicinale autorizzato">']
    for i, (label, fill, ink) in enumerate(tiers):
        y0, y1 = 10 + i * 68, 72 + i * 68
        w0, w1 = 230 + i * 92, 230 + i * 92 + 84
        out.append(f'<polygon points="{350 - w0 / 2},{y0} {350 + w0 / 2},{y0} {350 + w1 / 2},{y1} {350 - w1 / 2},{y1}" fill="{fill}"/>'
                   f'<text x="350" y="{(y0 + y1) / 2 + 6}" text-anchor="middle" fill="{ink}" font-size="17" font-weight="700" font-family="DM Sans, sans-serif">{label}</text>')
    return ''.join(out) + '</svg>'


def card(p, small=False):
    cls = 'peptide-card small' if small else 'peptide-card'
    cats = [p['category'], *p.get('extra_categories', [])]
    search = ' '.join([p['name'], p['focus'], *cats, *p['aliases']]).lower()
    return (f'''<a class="{cls}" href="{p['url']}" data-categories="{escape('|'.join(cats), quote=True)}" data-kind="{p['kind']}" data-status="{p['status']}" data-search="{escape(search, quote=True)}">'''
            f'''<div class="pc-head"><span class="pc-tag">{escape(p['category'])}</span><span class="pc-arrow">↗</span></div>{molecule_svg(p['slug'], CAT_COLORS[p['category']], cls='pc-art')}'''
            f'''<div class="pc-main"><div class="pc-molecule">{p['num']} / {escape(KINDS[p['kind']][0].upper())}</div><h3>{escape(p['name'])}</h3><p>{escape(p['focus'])}</p></div>'''
            f'''<div class="pc-bottom">{status_badge(p)}</div></a>''')


def evidence_grid(p):
    rows = ''
    for key, label in EVIDENCE_ROWS:
        row = p['evidence'][key]
        text = (AUTH_LEVELS if key == 'autorizzato' else LEVELS)[row['level']]
        rows += (f'<li class="ev-row"><span class="ev-name">{escape(label)}</span>'
                 f'<span class="ev-level ev-{row["level"]}"><i></i><i></i><i></i>{escape(text)}</span>'
                 f'<p class="ev-note">{escape(row["note"])}</p></li>')
    return f'<ul class="evidence-grid" aria-label="Livelli di evidenza">{rows}</ul>'


def related(p):
    same = [q for q in DATA if q is not p and (q['category'] == p['category'] or p['category'] in q.get('extra_categories', []))]
    other = [q for q in DATA if q is not p and q['category'] != p['category']]
    return (same + other)[:3]


# ------------------------------------------------------------------ homepage
STEPS = '''<div class="principles-grid steps-grid"><div><span>01</span><h3>Racconta il tuo obiettivo</h3><p>Rispondi a poche domande su cosa vuoi ottenere e sulla tua situazione.</p></div><div><span>02</span><h3>Scegli il tuo medico</h3><p>Ti proponiamo uno o più medici della nostra rete, esperti proprio nella tua area. Scegli tu con chi parlare.</p></div><div><span>03</span><h3>Videoconsulenza</h3><p>Il medico valuta la tua storia e, se serve, ti chiede esami mirati. Se lo ritiene appropriato, prescrive i trattamenti indicati per il tuo caso.</p></div><div><span>04</span><h3>Ti segue nel tempo</h3><p>Controlli periodici per valutare risultati, effetti indesiderati ed eventuali aggiustamenti.</p></div></div>'''
services = [
    ('Peptidi', 'BPC-157, MOTS-c e altri peptidi: un medico valuta con te prove, rischi e alternative autorizzate.'),
    ('TRT', 'Salute ormonale maschile: diagnosi con esami, terapia sostitutiva quando indicata e monitoraggio nel tempo.'),
    ('GLP-1', 'Salute metabolica e gestione del peso: valutazione clinica, trattamenti autorizzati se appropriati e follow-up.'),
    ('Longevity & Performance', 'Prevenzione, esami mirati e un piano personalizzato per la salute nel tempo, basato sulle prove.'),
    ('Capelli', 'Diradamento e caduta: diagnosi della causa, terapie con prove di efficacia e controlli fotografici nel tempo.'),
    ('Salute sessuale', 'Desiderio, erezione, cambiamenti con l’età: una valutazione riservata delle cause e delle soluzioni.'),
    ('Menopausa', 'Sintomi, terapia ormonale e alternative: scegliere con consapevolezza, con un piano di prevenzione.'),
    ('Recupero e sport', 'Infortuni, dolori ricorrenti e recupero lento: un percorso basato sulle prove, senza scorciatoie.'),
]
SERVICE_SLUGS = {'Peptidi': 'peptidi', 'TRT': 'trt', 'GLP-1': 'glp-1', 'Longevity & Performance': 'longevity-performance', 'Capelli': 'capelli', 'Salute sessuale': 'salute-sessuale', 'Menopausa': 'menopausa', 'Recupero e sport': 'recupero-sport'}
service_html = ''.join(f'''<article class="service-card">{area_icon(name)}<span class="service-number">{i:02d} / CONSULENZA</span><h3><a href="/consulenze/{SERVICE_SLUGS[name]}/">{escape(name)}</a></h3><p>{escape(desc)}</p><div class="service-actions"><a class="text-cta" href="/consulenze/{SERVICE_SLUGS[name]}/">Scopri la consulenza <span>→</span></a><a class="text-cta start-link" href="/inizia/?area={SERVICE_SLUGS[name]}" data-service="{escape(name, quote=True)}">Trova il tuo medico <span>↗</span></a></div></article>''' for i, (name, desc) in enumerate(services, 1))
featured = [p for s in FEATURED for p in DATA if p['slug'] == s]

home = f'''<section class="hero"><div class="wrap hero-grid"><div class="hero-content"><div class="eyebrow"><span class="pulse-dot"></span> MEDICINA EMERGENTE, SENZA HYPE.</div><h1>La medicina<br>di <em>domani.</em><br>Le risposte di oggi.</h1><p class="hero-lede">Peptidi, terapie innovative, longevità e performance. Un nuovo servizio per chi vuole capire davvero cosa sta cambiando nella medicina — e farsi seguire, in videoconsulenza, da medici esperti di terapie emergenti.</p><div class="hero-actions"><a class="btn btn-light start-link" href="/inizia/">Trova il tuo medico <span>↗</span></a><a class="link-light" href="/library/">Esplora la Library <span>→</span></a></div><p class="hero-footnote">Servizio in fase di avvio. Le consulenze non sono ancora prenotabili.</p></div><div class="hero-visual" aria-hidden="true"><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="orbit orbit-three"></div><div class="molecule-core"><span class="core-a"></span><span class="core-b"></span><span class="core-c"></span></div><span class="visual-code visual-code-top">EMERGING<br>MEDICINE<br>— 2026</span><span class="visual-code visual-code-bottom">RESEARCH /<br>EVIDENCE /<br>CLARITY</span></div></div><div class="wrap hero-stats"><span>01 / LIBRARY: {N} SCHEDE</span><span>02 / VIDEOCONSULENZE CON MEDICI ESPERTI</span><span>03 / RICERCA & INNOVAZIONE</span></div></section>
<section class="intro-section section-pad" id="approccio"><div class="wrap intro-grid"><div><div class="section-label">01 / IL PROGETTO</div><h2>Le innovazioni corrono.<br><span class="muted-heading">Le informazioni spesso no.</span></h2></div><div class="intro-copy"><p>Internet parla di BPC-157, GLP-1, rapamicina e terapie emergenti. Ma tra entusiasmi, studi preliminari e pubblicità è difficile capire cosa sia realmente dimostrato.</p><p>Vogliamo creare uno spazio in cui la curiosità incontra il rigore scientifico: informazioni affidabili e, a breve, videoconsulenze con i medici della nostra rete.</p><a class="underlined-link" href="/metodo/">Come valutiamo le prove ↗</a></div></div></section>
<section class="library-section section-pad" id="library"><div class="wrap"><div class="section-label">02 / KNOWLEDGE FIRST</div><div class="section-row"><div><h2>La <em>Library.</em></h2><p class="section-subtitle">Peptidi, farmaci e molecole emergenti. Per ognuno: cosa è dimostrato, cosa no.</p></div><a class="outlined-link" href="/library/">Tutte le {N} schede ↗</a></div><div class="card-grid">{''.join(card(p) for p in featured)}</div><div class="library-bottom"><div class="big-asterisk">✳</div><p>Come funziona. Cosa è stato studiato, dal laboratorio agli studi clinici. Quali rischi conosciamo. Cosa è autorizzato e cosa è ancora sperimentale.</p><a href="/library/" class="btn btn-dark">Entra nella Library <span>↗</span></a></div></div></section>
<section class="section-pad articles-home"><div class="wrap"><div class="section-label">ARTICOLI / GUIDE E NEWS</div><div class="section-row"><div><h2>Capire, <em>prima di scegliere.</em></h2><p class="section-subtitle">Guide e notizie su peptidi, farmaci e longevità.</p></div><a class="outlined-link" href="/articoli/">Tutti gli articoli ↗</a></div><div class="article-grid">{''.join(article_card(a) for a in ARTICLES[:3])}</div></div></section>
<section class="services-section section-pad" id="consulenze"><div class="wrap"><div class="section-label light-text">03 / IL SERVIZIO</div><div class="section-row"><div><h2>Non un altro<br><em>programma wellness.</em></h2><p class="section-subtitle">Una rete di medici esperti di terapie emergenti. Ci racconti il tuo obiettivo, ti abbiniamo ai medici più adatti e scegli tu con chi iniziare. Stiamo organizzando l’avvio del servizio.</p></div><span class="launch-chip">COMING SOON <i></i></span></div><div class="services-grid">{service_html}</div><div class="services-foot"><span>Le consulenze non sono ancora prenotabili. La prescrizione non è garantita: il medico la valuta caso per caso, solo per medicinali autorizzati e quando è appropriata.</span><span>Serve una valutazione medica, non una scorciatoia.</span></div></div></section>
<section class="principles how-section section-pad" id="come-funziona"><div class="wrap"><div class="section-label">04 / COME FUNZIONA</div><h2>Un medico al tuo fianco,<br><em>passo dopo passo.</em></h2>{STEPS}</div></section>
<section class="principles section-pad"><div class="wrap"><div class="section-label">05 / OUR STANDARD</div><h2>Curiosità radicale.<br><em>Rigore assoluto.</em></h2><div class="principles-grid"><div><span>01</span><h3>Prove, non promesse</h3><p>Per ogni sostanza distinguiamo studi in vitro, su animali, osservazionali, clinici randomizzati e medicinali autorizzati.</p></div><div><span>02</span><h3>Domande intelligenti</h3><p>Non celebriamo né demonizziamo una molecola: valutiamo cosa dicono i dati disponibili.</p></div><div><span>03</span><h3>Medicina responsabile</h3><p>Le dosi nelle schede sono quelle dei foglietti approvati o degli studi, mai consigli fai-da-te. Le decisioni cliniche spettano ai medici, nel rispetto di indicazioni, autorizzazioni e sicurezza.</p></div></div></div></section>
<section class="signup-section section-pad" id="interesse"><div class="wrap signup-grid"><div><div class="section-label">06 / STAY AHEAD</div><h2>La prossima<br>frontiera? <em>Seguici.</em></h2><p>Stiamo organizzando l’avvio delle videoconsulenze e ampliando la Library. Lasciaci la tua email per sapere quando partiamo.</p></div><div class="signup-panel"><div class="panel-icon">↗</div><h3>Entra nella lista di aggiornamento.</h3><p>Le consulenze non sono ancora prenotabili. Ti scriveremo solo per aggiornarti sul lancio.</p><button type="button" class="btn btn-dark full interest-trigger" data-service="generale">Ricevi aggiornamenti <span>↗</span></button><span class="note">Non raccogliamo dati sanitari. Puoi cancellarti quando vuoi.</span></div></div></section>'''
HOME_DESC = 'Peptidi, GLP-1, testosterone e longevità: cosa dicono davvero gli studi, rischi e dosi in oltre 40 schede. E una rete di medici esperti in videoconsulenza.'
write('index.html', page('AHEAD Medicine — Peptidi, GLP-1, TRT e longevità, senza hype', HOME_DESC, home, '/',
      schema=[ORG_LD, WEBSITE_LD, webpage_ld('WebPage', '/', SITE_NAME, HOME_DESC)], image=og_image('home', 'La medicina di domani. Le risposte di oggi.', 'AHEAD MEDICINE')))

# ------------------------------------------------------------------ library
used_categories = [c for c in CATEGORIES if any(c == p['category'] or c in p.get('extra_categories', []) for p in DATA)]
used_status = [s for s in STATUS if any(p['status'] == s for p in DATA)]
chips = ''.join(f'<button type="button" class="filter{" active" if c == "Tutti" else ""}" data-filter="{escape(c, quote=True)}" aria-pressed="{"true" if c == "Tutti" else "false"}">{escape(c)}</button>' for c in ['Tutti'] + used_categories)
kind_opts = '<option value="">Tutti i tipi</option>' + ''.join(f'<option value="{k}">{escape(v[0])}</option>' for k, v in KINDS.items())
status_opts = '<option value="">Tutti gli stati</option>' + ''.join(f'<option value="{s}">{escape(STATUS[s][0])}</option>' for s in used_status)
library = f'''<section class="inner-hero"><div class="wrap"><div class="section-label light-text">RESEARCH / LIBRARY</div><h1>La <em>Library.</em></h1><p>{N} schede su peptidi, farmaci e molecole emergenti. Per ognuna: livelli di evidenza, rischi e stato autorizzativo. Senza confondere ricerca e terapia.</p><div class="mini-notice">Le schede sono bozze editoriali in attesa di revisione medico-scientifica indipendente e non rappresentano consigli terapeutici. <a href="/metodo/">Come lavoriamo ↗</a></div></div></section><section class="section-pad library-page"><div class="wrap"><div class="library-controls"><label class="search-label"><span aria-hidden="true">⌕</span><input id="peptide-search" type="search" placeholder="Cerca per nome, area o sinonimo…" aria-label="Cerca nella Library"></label><div class="selects"><label class="select-label"><span class="visually-hidden">Tipo</span><select id="kind-filter" aria-label="Filtra per tipo">{kind_opts}</select></label><label class="select-label"><span class="visually-hidden">Stato regolatorio</span><select id="status-filter" aria-label="Filtra per stato regolatorio">{status_opts}</select></label></div></div><div class="filters" role="group" aria-label="Filtra per area">{chips}</div><nav class="area-nav" aria-label="Pagine per area"><span class="mini-label">PAGINE PER AREA</span>{''.join(f'<a href="/library/{slugify(c)}/">{escape(c)}</a>' for c in used_categories)}<a href="/peptidi/">Tutti i peptidi</a><a href="/sostanze/">Farmaci e sostanze</a></nav><p class="results-count" id="results-count" aria-live="polite">{N} risultati</p><div class="card-grid library-results">{''.join(card(p, True) for p in DATA)}</div><p id="no-results" class="empty-results" hidden>Nessuna scheda corrisponde alla ricerca.</p></div></section>'''
LIB_DESC = f'{N} schede su peptidi, GLP-1, ormoni e sostanze per la longevità: cosa dicono gli studi, effetti collaterali, dosi e stato legale in Italia.'
write('library/index.html', page('Library: peptidi, GLP-1, ormoni e longevità — schede scientifiche', LIB_DESC, library, '/library/',
      schema=[webpage_ld('CollectionPage', '/library/', 'Library', LIB_DESC), itemlist_ld([(p['name'], p['url']) for p in DATA])],
      crumbs=[('Home', '/'), ('Library', '/library/')], image=og_image('library', f'{N} schede su peptidi e terapie emergenti', 'LIBRARY')))

CAT_INTRO = {
    'Recupero': ('Peptidi per il recupero e gli infortuni', 'BPC-157, TB-500, KPV e le altre sostanze proposte per tendini, muscoli e infiammazione. Per ognuna: cosa dicono davvero gli studi, quali rischi comporta e se è autorizzata in Italia.'),
    'Ormoni': ('Ormoni e secretagoghi del GH', 'Testosterone, ormone della crescita, hCG e i peptidi che stimolano il rilascio di GH: indicazioni autorizzate, prove scientifiche e rischi di un uso fuori controllo.'),
    'Massa muscolare': ('Peptidi e sostanze per la massa muscolare', 'Dai farmaci autorizzati come testosterone e somatropina ai peptidi venduti online come follistatina, IGF-1 LR3 e GHRP-6: cosa è dimostrato, cosa no e quali rischi comportano, anche per chi fa sport.'),
    'Metabolismo': ('GLP-1, peptidi e farmaci per peso e metabolismo', 'Semaglutide, tirzepatide, retatrutide e le nuove molecole per obesità e diabete, insieme alle sostanze proposte online per dimagrire: stato autorizzativo, prove e sicurezza.'),
    'Longevità': ('Longevità: peptidi, farmaci e integratori anti-aging', 'Rapamicina, metformina, NAD+, MOTS-c, epitalon e senolitici: cosa sappiamo davvero sulle strategie per vivere più a lungo, dagli studi sugli animali a quelli sull’uomo.'),
    'Pelle': ('Peptidi per pelle e capelli', 'GHK-Cu, AHK-Cu, melanotan e gli altri peptidi usati in cosmetica o venduti per pelle, capelli e abbronzatura: differenze tra uso cosmetico e iniettabile, prove e rischi.'),
    'Neuro': ('Peptidi per cervello, sonno e ansia', 'Semax, Selank e DSIP: peptidi registrati in Russia o studiati per cognizione, ansia e sonno. Cosa dicono gli studi e perché in Europa non sono medicinali.'),
    'Immunità': ('Peptidi per il sistema immunitario', 'Timosina alfa-1, timalina e LL-37: immunomodulanti e peptidi antimicrobici tra uso clinico extra-UE e ricerca. Prove, limiti e stato regolatorio.'),
    'Sessualità e fertilità': ('Peptidi e ormoni per sessualità e fertilità', 'Bremelanotide (PT-141), kisspeptina e hCG: cosa è autorizzato, per quali indicazioni, e cosa invece resta sperimentale.'),
}
CAT_URL = {c: f'/library/{slugify(c)}/' for c in CATEGORIES}


def listing_page(path, label, h1, intro, items, crumbs, og_key):
    desc = clip(intro)
    links = ''.join(f'<a class="filter" href="{CAT_URL[c]}"{" aria-current=\"page\"" if CAT_URL[c] == path else ""}>{escape(c)}</a>' for c in used_categories)
    body = f'''<section class="inner-hero"><div class="wrap"><div class="breadcrumbs">{' / '.join(f'<a href="{u}">{escape(n)}</a>' for n, u in crumbs[:-1])} / {escape(crumbs[-1][0])}</div><div class="section-label light-text">{escape(label)}</div><h1>{escape(h1)}</h1><p>{escape(intro)}</p></div></section><section class="section-pad"><div class="wrap"><nav class="filters area-links" aria-label="Aree della Library">{links}</nav><p class="results-count">{len(items)} schede</p><div class="card-grid">{''.join(card(q, True) for q in items)}</div></div></section>'''
    write(path.strip('/') + '/index.html', page(h1, desc, body, path, schema=[webpage_ld('CollectionPage', path, h1, desc), itemlist_ld([(q['name'], q['url']) for q in items])],
                                                 crumbs=crumbs, image=og_image(og_key, h1, label)))


for c in used_categories:
    h1, intro = CAT_INTRO[c]
    items = [q for q in DATA if q['category'] == c or c in q.get('extra_categories', [])]
    listing_page(CAT_URL[c], f'LIBRARY / {c.upper()}', h1, intro, items, [('Home', '/'), ('Library', '/library/'), (c, CAT_URL[c])], 'cat-' + slugify(c))

listing_page('/peptidi/', 'LIBRARY / PEPTIDI', 'Peptidi: elenco completo e schede scientifiche', 'Tutti i peptidi della Library, dai medicinali autorizzati come semaglutide e tirzepatide ai peptidi “da ricerca” come BPC-157, TB-500 e MOTS-c. Per ognuno: prove, effetti collaterali, dosi e stato legale in Italia.',
             [q for q in DATA if q['kind'] == 'peptide'], [('Home', '/'), ('Peptidi', '/peptidi/')], 'peptidi')
listing_page('/sostanze/', 'LIBRARY / FARMACI E SOSTANZE', 'Farmaci, ormoni e altre sostanze', 'Testosterone, ormone della crescita, rapamicina, metformina, orforglipron, NAD+ e le altre molecole non peptidiche della Library: indicazioni autorizzate, prove scientifiche, rischi e dosi.',
             [q for q in DATA if q['kind'] == 'sostanza'], [('Home', '/'), ('Farmaci e sostanze', '/sostanze/')], 'sostanze')

# ------------------------------------------------------------------ schede
for p in DATA:
    review = p['review']
    checked = it_date(review['checked'])
    reviewer = review.get('medical_reviewer') or 'Non ancora effettuata'
    refs = [(s['label'], s['url'], SOURCE_TYPES[s['type']]) for s in p['sources']]
    refs += [('Tutti gli studi su PubMed', p['pubmed'], 'Ricerca'), ('Trial registrati su ClinicalTrials.gov', p['trials'], 'Ricerca')]
    refs_html = ''.join(f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer"><span><small class="src-type">{escape(t)}</small>{escape(label)}</span> <span aria-hidden="true">↗</span></a>' for label, url, t in refs)
    aliases = f'<p class="aliases">Noto anche come: {escape(", ".join(p["aliases"]))}</p>' if p['aliases'] else ''
    kind_label = KINDS[p['kind']][0]
    p_arts = [a for a in ARTICLES if p['slug'] in a['related']]
    arts_block = f'<section class="section-pad articles-related"><div class="wrap"><div class="section-row"><h2>Articoli su {escape(p["name"])}.</h2><a class="underlined-link" href="/articoli/">Tutti gli articoli ↗</a></div><div class="article-grid">{"".join(article_card(a) for a in p_arts[:3])}</div></div></section>' if p_arts else ''
    name = p['name']
    color = CAT_COLORS[p['category']]
    dosing_html = (f'<div class="dosing-box"><span class="dosing-basis">{escape(DOSING_BASIS[p["dosing"]["basis"]])}</span><p class="dosing-route"><strong>Via di somministrazione:</strong> {escape(p["dosing"]["route"])}</p><p>{escape(p["dosing"]["text"])}</p></div>'
                   '<div class="dosing-warning" role="note"><strong>Informazione, non indicazione.</strong> Le dosi riportate descrivono come la sostanza è usata nei medicinali approvati o negli studi clinici. Non sono consigli da seguire: ogni trattamento richiede una visita e l’approvazione di un medico, che valuta indicazione, controindicazioni ed esami. Non usare prodotti acquistati fuori dai canali autorizzati.</div>')
    secs = [('in-breve', 'IN BREVE', f'Che cos’è {name}?', aliases + f'<p>{escape(p["what"])}</p>')]
    if p.get('mechanism'):
        secs.append(('come-funziona', 'COME FUNZIONA', f'Come funziona {name}', f'<p>{escape(p["mechanism"])}</p>'))
    secs += [('prove', 'LE PROVE', f'A cosa serve {name}? Cosa dicono gli studi', evidence_grid(p) + f'<h3 class="sub-heading">Cosa non sappiamo ancora</h3><p>{escape(p["unknown"])}</p>'),
             ('dosi', 'COME SI ASSUME', f'Come si assume {name} e a quali dosi', dosing_html),
             ('rischi', 'RISCHI', f'Effetti collaterali e rischi di {name}', f'<p>{escape(p["risk"])}</p>'),
             ('legale', 'REGOLAMENTAZIONE', f'{name} è legale in Italia? Lo stato in Europa', f'<p>{escape(p["reg"])}</p>')]
    if p.get('timeline'):
        secs.append(('storia', 'LA STORIA', 'Le tappe principali', '<ol class="timeline">' + ''.join(f'<li><span class="tl-year">{escape(y)}</span><p>{escape(t)}</p></li>' for y, t in p['timeline']) + '</ol>'))
    if p.get('faq'):
        secs.append(('faq', 'DOMANDE FREQUENTI', f'Domande frequenti su {name}', '<div class="faq">' + ''.join(f'<details class="faq-item"><summary>{escape(q)}</summary><p>{escape(a)}</p></details>' for q, a in p['faq']) + '</div>'))
    secs.append(('fonti', 'LE FONTI', 'Approfondisci la ricerca.', f'<div class="source-links">{refs_html}</div><p class="citation-note">Link a fonti ufficiali e studi per orientarsi. La bibliografia completa con grading delle prove sarà aggiunta con la revisione medico-scientifica. <a href="/metodo/">Il nostro metodo ↗</a></p>'))
    sections_html = ''.join(f'<section class="profile-section-block" id="{sid}" aria-labelledby="h-{sid}"><div class="section-label">{n:02d} / {label}</div><h2 id="h-{sid}">{escape(h2)}</h2>{html}</section>' for n, (sid, label, h2, html) in enumerate(secs, 1))
    key_points = f'<div class="key-points" style="--accent:{color}"><span class="mini-label">IN SINTESI</span><ul>{"".join(f"<li>{escape(k)}</li>" for k in p["key_points"])}</ul></div>' if p.get('key_points') else ''
    toc = '<nav class="toc" aria-label="In questa pagina"><span class="mini-label">IN QUESTA PAGINA</span>' + ''.join(f'<a href="#{sid}">{escape(label.capitalize())}</a>' for sid, label, _, _ in secs) + '</nav>'
    photo = hero_photo(('schede', p['slug']), ('aree', slugify(p['category'])))
    body = f'''<section class="inner-hero peptide-hero{' has-photo' if photo else ''}" style="--accent:{color}">{photo}<div class="wrap hero-split"><div><div class="breadcrumbs"><a href="/">Home</a> / <a href="/library/">Library</a> / <a href="/library/{slugify(p['category'])}/">{escape(p['category'])}</a> / {escape(name)}</div><div class="section-label light-text">{escape(kind_label.upper())} / {escape(p['category'].upper())}</div><h1>{escape(name)}<span class="little-star">✳</span></h1><p>{escape(p['tagline'])}</p>{status_badge(p)}</div>{'' if photo else molecule_svg(p['slug'], color, dark=True, cls='hero-art')}</div></section><section class="section-pad profile-section"><div class="wrap profile-grid"><article class="profile-main"><div class="review-notice"><strong>Bozza informativa — revisione medica indipendente non ancora effettuata.</strong><br>Ultima verifica editoriale delle fonti: {checked}. Questa pagina non sostituisce il parere di un medico.</div>{key_points}{sections_html}</article><aside class="profile-aside"><div class="fact-box"><span class="mini-label">AREA DI RICERCA / APPLICAZIONE</span><strong>{escape(p['focus'])}</strong><hr><span class="mini-label">TIPO</span><strong>{escape(kind_label)}</strong><hr><span class="mini-label">QUALITÀ DELLE PROVE</span><strong>{escape(p['evidence_summary'])}</strong><hr><span class="mini-label">STATO REGOLATORIO</span><strong>{escape(STATUS[p['status']][0])}</strong><hr><span class="mini-label">REVISIONE MEDICA</span><strong>{escape(reviewer)}</strong><hr><span class="mini-label">ULTIMA VERIFICA FONTI</span><strong>{checked}</strong></div>{toc}<div class="aside-cta"><span>THE HUMAN SIDE OF RESEARCH</span><h3>Vuoi parlarne con un medico?</h3><p>Rispondi a un breve questionario anonimo: ci aiuta ad abbinarti ai medici più adatti della nostra rete.</p><a class="btn btn-dark full start-link" href="/inizia/{'?area=' + SERVICE_SLUGS[p['service']] if p['service'] else ''}" data-service="{escape(p['service'] or 'generale', quote=True)}">Trova il tuo medico ↗</a><small>Servizio in avvio. La prescrizione è decisa dal medico e solo se appropriata.</small></div></aside></div></section>{arts_block}<section class="related-section"><div class="wrap"><div class="section-row"><h2>Continua a esplorare.</h2><a class="underlined-link" href="/library/">Tutte le schede ↗</a></div><div class="card-grid related-grid">{''.join(card(q, True) for q in related(p))}</div></div></section>'''
    title = (f'{name}: cos’è, a cosa serve, effetti collaterali e dosi' if len(name) <= 14
             else f'{name}: cos’è, effetti e dosi' if len(name) > 26 else f'{name}: cos’è, studi, rischi e dosi')
    alias = f" ({', '.join(p['aliases'][:2])})" if p['aliases'] else ''
    desc = clip(f"{name}{alias}: {p['what'].split('. ')[0].rstrip('.')}. Studi, effetti collaterali, dosi e stato legale in Italia.")
    drug_like = p['status'] in ('ue', 'extra_ue', 'trial', 'ritirato')
    about = {'@type': 'Drug' if drug_like else 'Substance', 'name': name}
    if p['aliases']:
        about['alternateName'] = p['aliases']
    faq_pairs = [(f'Che cos’è {name}?', p['what']), (f'A cosa serve {name}? Cosa dicono gli studi', p['unknown']),
                 (f'Come si assume {name} e a quali dosi', p['dosing']['route'] + ' ' + p['dosing']['text']),
                 (f'Effetti collaterali e rischi di {name}', p['risk']), (f'{name} è legale in Italia?', p['reg'])] + [tuple(x) for x in p.get('faq', [])]
    schema = [webpage_ld('MedicalWebPage', p['url'], title, desc, about=about, lastReviewed=review['checked'], dateModified=review['checked'], publisher={'@id': SITE_URL + '/#org'}),
              faq_ld(faq_pairs)]
    crumbs = [('Home', '/'), ('Library', '/library/'), (p['category'], f"/library/{slugify(p['category'])}/"), (name, p['url'])]
    write(p['url'].strip('/') + '/index.html', page(title, desc, body, p['url'], schema=schema, crumbs=crumbs, lastmod=review['checked'],
                                                    image=og_image('scheda-' + p['slug'], name, f"{KINDS[p['kind']][0].upper()} / {p['category'].upper()}")))

# ------------------------------------------------------------------ consulenze
CONSULENZE = [
    dict(name='Peptidi', title='Peptidi, <em>con un medico.</em>',
         lede='BPC-157, TB-500, MOTS-c, GHK-Cu: se ne parla ovunque. In videoconsulenza un medico della nostra rete valuta con te cosa dicono davvero gli studi, quali rischi corri e quali alternative autorizzate esistono per il tuo obiettivo.',
         for_whom=['Stai pensando di usare peptidi acquistati online, o li usi già, e vuoi un parere medico indipendente.',
                   'Hai un problema di recupero, dolore articolare, pelle o metabolismo e ti sono stati proposti dei peptidi.',
                   'Vuoi capire la differenza tra peptidi sperimentali e medicinali peptidici autorizzati, come i GLP-1.'],
         doctor=['Ricostruisce con te obiettivo, storia clinica e farmaci in uso.',
                 'Ti spiega il livello delle prove per le sostanze che ti interessano.',
                 'Valuta rischi, interazioni e segnali da non trascurare.',
                 'Propone un percorso e, se appropriato, prescrive medicinali autorizzati.'],
         exams='Gli esami vengono richiesti solo se utili al tuo caso, per esempio emocromo e funzionalità renale ed epatica se stai già usando delle sostanze.',
         limits='I peptidi non autorizzati, come BPC-157, TB-500 o MOTS-c, non possono essere prescritti: non sono medicinali e non esistono canali di acquisto controllati. Il medico non indica fornitori né dosaggi per queste sostanze. Se le stai già usando, ti aiuta a valutarne i rischi, senza giudicarti.',
         faq=[('Il medico può prescrivermi BPC-157 o altri peptidi “da ricerca”?', 'No. Queste sostanze non sono medicinali autorizzati e la legge non ne consente la prescrizione. Il medico può però valutare con te il problema di fondo e le alternative autorizzate.'),
              ('Ho già comprato dei peptidi online. Posso parlarne?', 'Sì, ed è importante farlo. Il medico ti aiuta a capire i rischi legati alla sostanza e alla qualità del prodotto e a riconoscere eventuali effetti indesiderati.'),
              ('Esistono peptidi che sono medicinali veri e propri?', 'Sì: per esempio semaglutide, tirzepatide e liraglutide sono peptidi autorizzati per diabete e gestione del peso. Li trovi nella Library con il loro stato regolatorio.'),
              ('Quanto costa la consulenza?', 'Le tariffe saranno comunicate al lancio del servizio.')]),
    dict(name='TRT', title='Testosterone, <em>senza scorciatoie.</em>',
         lede='Stanchezza, calo del desiderio, perdita di massa muscolare: possono dipendere da un testosterone basso, ma anche da molto altro. Un medico della rete ti accompagna dalla diagnosi al monitoraggio e prescrive la terapia sostitutiva solo quando è indicata.',
         for_whom=['Uomini con sintomi compatibili con un testosterone basso.',
                   'Chi ha già esami alterati e vuole un inquadramento completo.',
                   'Chi è già in terapia e vuole un monitoraggio strutturato.',
                   'Chi desidera figli e vuole capire come proteggere la fertilità.'],
         doctor=['Valuta sintomi, storia clinica, farmaci e stile di vita.',
                 'Conferma la diagnosi con misurazioni mattutine ripetute del testosterone e gli esami ormonali correlati.',
                 'Cerca le cause e le condizioni da trattare per prime.',
                 'Se la terapia è indicata, sceglie con te la formulazione e pianifica i controlli.'],
         exams='Testosterone totale al mattino (ripetuto), LH e FSH, emocromo con ematocrito, PSA in base all’età e altri esami secondo il caso.',
         limits='La terapia con testosterone non è indicata per chi ha livelli normali, né per aumentare la massa muscolare o le prestazioni. Può ridurre la fertilità: se desideri figli, il medico ne parla con te prima di iniziare.',
         faq=[('Devo avere gli esami prima della videoconsulenza?', 'Se li hai, portali. Altrimenti il medico ti indica quali fare e quando, perché il testosterone va misurato al mattino e ripetuto.'),
              ('Il medico mi prescriverà sicuramente il testosterone?', 'Solo se la diagnosi di ipogonadismo è confermata e i benefici attesi superano i rischi. In molti casi esistono cause da trattare prima.'),
              ('La terapia è per sempre?', 'Spesso è un trattamento di lungo periodo, che viene rivalutato nel tempo. Un’eventuale sospensione va pianificata con il medico.'),
              ('Posso avere figli durante la terapia?', 'Il testosterone può ridurre la produzione di spermatozoi. Se il tema ti riguarda, il medico valuta con te le strategie possibili prima di iniziare.')]),
    dict(name='GLP-1', title='Peso e metabolismo, <em>con metodo.</em>',
         lede='I farmaci GLP-1 hanno cambiato la cura dell’obesità e del diabete, ma non sono per tutti e funzionano meglio dentro un percorso. Il medico valuta se sono indicati per te e ti segue nel tempo.',
         for_whom=['Persone con obesità, o sovrappeso con almeno una condizione legata al peso, come previsto dalle indicazioni dei farmaci.',
                   'Persone con diabete di tipo 2 che vogliono rivalutare la terapia.',
                   'Chi usa già un GLP-1 e vuole un monitoraggio strutturato.',
                   'Chi vuole capire le differenze tra semaglutide, tirzepatide e le nuove molecole.'],
         doctor=['Valuta storia del peso, alimentazione, attività fisica e altre condizioni.',
                 'Verifica indicazioni e controindicazioni.',
                 'Se appropriato, prescrive un medicinale autorizzato e ti spiega l’aumento graduale della dose.',
                 'Programma controlli su risultati, effetti indesiderati e mantenimento nel tempo.'],
         exams='Glicemia ed emoglobina glicata, profilo lipidico, funzionalità renale ed epatica e altri esami secondo il caso.',
         limits='Non prescriviamo GLP-1 fuori dalle indicazioni autorizzate, per esempio per dimagrire a fini estetici. Non prescriviamo molecole non ancora autorizzate, come retatrutide, né prodotti venduti online fuori dai canali farmaceutici.',
         faq=[('Cosa succede quando si smette?', 'Gli studi mostrano che il peso tende a risalire. Per questo il percorso comprende alimentazione, attività fisica e un piano per il lungo periodo.'),
              ('Quali effetti indesiderati sono comuni?', 'Soprattutto nausea, diarrea o stitichezza, in genere nelle prime settimane e durante gli aumenti di dose. Il medico ti spiega come gestirli e quando contattarlo.'),
              ('Il farmaco è rimborsato dal Servizio sanitario?', 'Dipende dal farmaco e dall’indicazione. Il medico ti spiega se e quando è previsto un rimborso.'),
              ('Posso avere retatrutide?', 'No: alla data di verifica non è autorizzato in nessun Paese. I prodotti venduti online con questo nome non provengono da canali controllati.')]),
    dict(name='Longevity & Performance', title='Longevità, <em>basata sulle prove.</em>',
         lede='Vivere più a lungo e meglio dipende soprattutto da fattori misurabili e modificabili. Il medico parte dai tuoi dati per costruire un piano di prevenzione personalizzato e ti aiuta a distinguere le promesse dalle prove.',
         for_whom=['Chi vuole un check-up strutturato e un piano di prevenzione.',
                   'Sportivi e persone attive che vogliono migliorare salute e prestazioni senza rischi.',
                   'Chi è incuriosito da rapamicina, metformina, NAD+ e altre strategie anti-aging e vuole un parere medico.'],
         doctor=['Valuta rischio cardiovascolare, metabolico e oncologico in base a storia ed esami.',
                 'Imposta priorità concrete: attività fisica, forza muscolare, sonno, alimentazione.',
                 'Discute con te le prove sulle strategie “longevity” che ti interessano.',
                 'Se c’è un’indicazione clinica, prescrive trattamenti autorizzati e pianifica i controlli.'],
         exams='Profilo lipidico (incluse ApoB e lipoproteina(a) quando utili), glicemia ed emoglobina glicata, funzionalità renale ed epatica, pressione arteriosa e altri esami secondo età e storia.',
         limits='Non prescriviamo farmaci “anti-aging” fuori indicazione senza prove adeguate, né ormoni o altre sostanze per migliorare le prestazioni in persone sane. Le sostanze vietate nello sport non vengono prescritte a questo scopo.',
         faq=[('Fate test dell’età biologica?', 'I test che stimano l’età biologica sono ancora strumenti di ricerca. Il medico ti spiega cosa possono dire e cosa no, e su quali esami vale davvero la pena basarsi.'),
              ('Posso avere una prescrizione di rapamicina o metformina per la longevità?', 'Oggi non ci sono prove sufficienti per usarle nelle persone sane a questo scopo. Il medico ne discute con te le prove; la prescrizione avviene solo se esiste un’indicazione clinica.'),
              ('Seguite anche gli sportivi?', 'Sì, per salute, prevenzione e gestione dei carichi. Non prescriviamo sostanze dopanti né ormoni per aumentare le prestazioni.'),
              ('Quanto costa la consulenza?', 'Le tariffe saranno comunicate al lancio del servizio.')]),
    dict(name='Capelli', title='Capelli, <em>prima che sia tardi.</em>', related=['ghk-cu'],
         lede='Diradamento, stempiatura, caduta improvvisa: le cause sono diverse e le terapie che funzionano esistono, se si parte presto. Un medico della rete esperto di tricologia valuta il tuo caso e costruisce con te un piano.',
         for_whom=['Uomini con stempiatura o diradamento sul vertice.',
                   'Donne con diradamento diffuso o caduta aumentata.',
                   'Chi ha notato una caduta improvvisa dopo stress, malattia, gravidanza o un forte dimagrimento.',
                   'Chi usa già prodotti o farmaci e vuole capire se stanno funzionando.'],
         doctor=['Ricostruisce storia, familiarità, farmaci e possibili fattori scatenanti.',
                 'Valuta le foto del cuoio capelluto e, se serve, ti indirizza a una tricoscopia.',
                 'Richiede esami mirati per escludere cause trattabili.',
                 'Se appropriato, prescrive i trattamenti indicati e pianifica controlli fotografici nel tempo.'],
         exams='Emocromo e ferritina, funzionalità tiroidea, vitamina D e, nella donna, esami ormonali quando indicati.',
         limits='Non promettiamo ricrescita garantita: i risultati richiedono mesi e dipendono dalla causa e da quanto è avanzato il diradamento. Peptidi cosmetici e integratori vengono valutati per quello che dicono le prove, senza sostituirli ai trattamenti efficaci.',
         faq=[('Quali trattamenti funzionano davvero?', 'Per la calvizie androgenetica le prove più solide riguardano minoxidil e, negli uomini, finasteride. Il medico valuta con te benefici, effetti indesiderati e alternative, incluse le opzioni fuori indicazione con prove crescenti.'),
              ('Ho perso molti capelli dopo una dieta o un farmaco per dimagrire. È normale?', 'Una caduta diffusa qualche mese dopo un forte dimagrimento, una malattia o uno stress intenso è frequente e spesso temporanea. Va comunque valutata per escludere carenze o altre cause.'),
              ('I peptidi al rame fanno ricrescere i capelli?', 'Le prove su GHK-Cu e AHK-Cu sono di laboratorio o cosmetiche, senza studi clinici solidi sulla caduta. Trovi i dettagli nelle schede della Library.'),
              ('Fate trapianti?', 'No: la consulenza serve per la diagnosi e la terapia medica. Se il trapianto è un’opzione sensata, il medico te lo dice.')]),
    dict(name='Salute sessuale', title='Salute sessuale, <em>senza imbarazzo.</em>', related=['testosterone', 'hcg', 'kisspeptina'],
         lede='Calo del desiderio, difficoltà di erezione, cambiamenti con l’età: sono temi frequenti e spesso trattabili. In videoconsulenza, in modo riservato, un medico della rete cerca le cause e propone le soluzioni adatte a te.',
         for_whom=['Uomini con difficoltà di erezione o calo del desiderio.',
                   'Donne con calo del desiderio o disturbi della sfera sessuale.',
                   'Chi vuole capire se un problema sessuale nasconde una causa ormonale, cardiovascolare o metabolica.',
                   'Chi usa già farmaci o integratori e vuole un parere.'],
         doctor=['Ascolta la tua storia in un contesto riservato.',
                 'Valuta fattori ormonali, cardiovascolari, metabolici, farmacologici e psicologici.',
                 'Richiede gli esami utili.',
                 'Se appropriato, prescrive i trattamenti indicati e ti segue nel tempo.'],
         exams='Glicemia, profilo lipidico, testosterone negli uomini, esami ormonali secondo il caso e una valutazione del rischio cardiovascolare.',
         limits='Non prescriviamo farmaci “da prestazione” senza una valutazione, né sostanze non autorizzate come il melanotan. Alcuni sintomi, come la disfunzione erettile, possono essere un primo segnale cardiovascolare: per questo non li trattiamo come un problema solo “tecnico”.',
         faq=[('La consulenza è riservata?', 'Sì: la videochiamata avviene solo tra te e il medico, che è tenuto al segreto professionale.'),
              ('Esistono farmaci per il desiderio femminile?', 'Negli Stati Uniti sono approvati due farmaci per il disturbo del desiderio sessuale ipoattivo, tra cui bremelanotide; in UE non sono autorizzati. Il medico ti spiega le opzioni disponibili per il tuo caso.'),
              ('Il testosterone aumenta la libido?', 'Solo se è davvero basso. Con livelli normali non ci sono prove di benefici.'),
              ('Quanto costa la consulenza?', 'Le tariffe saranno comunicate al lancio del servizio.')]),
    dict(name='Menopausa', title='Menopausa, <em>da protagonista.</em>',
         lede='Vampate, sonno disturbato, umore, salute di ossa e cuore: la menopausa cambia molte cose, e le terapie oggi sono più personalizzabili di quanto si pensi. Un medico della rete esperto di salute femminile ti aiuta a scegliere con consapevolezza.',
         for_whom=['Donne in perimenopausa o menopausa con sintomi che pesano sulla qualità della vita.',
                   'Chi vuole capire benefici e rischi della terapia ormonale sostitutiva.',
                   'Chi non può o non vuole usare ormoni e cerca alternative.',
                   'Chi vuole un piano di prevenzione per ossa, cuore e metabolismo.'],
         doctor=['Valuta sintomi, storia personale e familiare e fattori di rischio.',
                 'Spiega in modo chiaro benefici e rischi delle diverse opzioni.',
                 'Richiede gli esami utili, inclusi gli screening previsti.',
                 'Se appropriato, prescrive la terapia e programma i controlli.'],
         exams='Esami del sangue di base, profilo lipidico e glicemia, pressione arteriosa, screening oncologici previsti per età e, quando indicato, densitometria ossea.',
         limits='La terapia ormonale non è adatta a tutte: alcune condizioni la sconsigliano. Non prescriviamo preparati “bioidentici” galenici non standardizzati al posto dei medicinali autorizzati.',
         faq=[('La terapia ormonale fa venire il tumore al seno?', 'Il rischio dipende dal tipo di terapia, dalla durata e dalla persona. Per molte donne con sintomi, iniziata vicino alla menopausa, i benefici superano i rischi: il medico valuta il tuo caso.'),
              ('Esistono alternative agli ormoni?', 'Sì: esistono farmaci non ormonali autorizzati per le vampate e interventi sullo stile di vita. Il medico ti spiega quale opzione ha più senso per te.'),
              ('Per quanto tempo si può fare la terapia?', 'Non esiste una scadenza uguale per tutte: la terapia viene rivalutata periodicamente con il medico.'),
              ('Quanto costa la consulenza?', 'Le tariffe saranno comunicate al lancio del servizio.')]),
    dict(name='Recupero e sport', title='Recupero e sport, <em>con criterio.</em>', related=['bpc-157', 'tb-500', 'ara-290', 'kpv'],
         lede='Infortuni che non passano, dolori articolari, recupero lento: prima di cercare scorciatoie serve capire cosa sta succedendo. Un medico della rete esperto di medicina dello sport valuta il problema e imposta il recupero.',
         for_whom=['Sportivi amatoriali e agonisti con infortuni o dolori ricorrenti.',
                   'Chi ha un recupero lento dopo un infortunio o un intervento.',
                   'Chi sta valutando peptidi o altre sostanze per il recupero e vuole un parere medico.',
                   'Chi vuole migliorare la preparazione in sicurezza.'],
         doctor=['Ricostruisce l’infortunio, i carichi di allenamento e le terapie già fatte.',
                 'Indica gli esami di imaging utili, se servono.',
                 'Imposta il percorso con fisioterapia, gestione dei carichi e terapie con prove di efficacia.',
                 'Valuta con te prove e rischi delle sostanze di cui hai sentito parlare.'],
         exams='Ecografia o risonanza solo se utili, ed esami del sangue in caso di stanchezza, infortuni ripetuti o sospette carenze.',
         limits='Non prescriviamo peptidi non autorizzati come BPC-157 o TB-500, né sostanze vietate dalle norme antidoping. Gli atleti tesserati devono sempre verificare la compatibilità di ogni trattamento con le regole antidoping.',
         faq=[('BPC-157 e TB-500 servono davvero per gli infortuni?', 'Le prove nell’uomo sono quasi assenti: i dati vengono soprattutto da studi su animali. Trovi i dettagli nelle schede della Library.'),
              ('Fate infiltrazioni o terapie in presenza?', 'No: la consulenza è online. Se serve una procedura, il medico ti indica a chi rivolgerti.'),
              ('Sono un atleta tesserato: posso fare la consulenza?', 'Sì. Il medico tiene conto delle regole antidoping in ogni proposta.'),
              ('Quanto costa la consulenza?', 'Le tariffe saranno comunicate al lancio del servizio.')]),
]


def li(items):
    return ''.join(f'<li>{escape(x)}</li>' for x in items)


for c in CONSULENZE:
    slug = SERVICE_SLUGS[c['name']]
    rel = [p for p in DATA if p['service'] == c['name'] or p['slug'] in c.get('related', [])]
    faq = ''.join(f'<details class="faq-item"><summary>{escape(q)}</summary><p>{escape(a)}</p></details>' for q, a in c['faq'])
    library_block = f'''<div class="section-row"><h2>Approfondisci nella Library.</h2><a class="underlined-link" href="/library/">Tutte le schede ↗</a></div><div class="card-grid related-grid">{''.join(card(p, True) for p in rel[:6])}</div>''' if rel else ''
    arts = [a for a in ARTICLES if a['service'] == c['name']]
    articles_block = f'''<div class="section-row space-top"><h2>Articoli.</h2><a class="underlined-link" href="/articoli/">Tutti gli articoli ↗</a></div><div class="article-grid">{''.join(article_card(a) for a in arts[:3])}</div>''' if arts else ''
    others = ''.join(f'<a class="other-service" href="/consulenze/{SERVICE_SLUGS[o["name"]]}/">Consulenza {escape(o["name"])} <span>→</span></a>' for o in CONSULENZE if o is not c)
    photo = hero_photo(('consulenze', slug))
    body = f'''<section class="inner-hero{' has-photo' if photo else ''}">{photo}<div class="wrap">{'' if photo else area_icon(c['name'], 'consult-art')}<div class="breadcrumbs"><a href="/">Home</a> / <a href="/consulenze/">Consulenze</a> / {escape(c['name'])}</div><div class="section-label light-text">{area_icon(c['name'], 'hero-icon')}CONSULENZA / {escape(c['name'].upper())}</div><h1>{c['title']}</h1><p>{escape(c['lede'])}</p><div class="hero-actions"><a class="btn btn-light start-link" href="/inizia/?area={slug}" data-service="{escape(c['name'], quote=True)}">Trova il tuo medico <span>↗</span></a><a class="link-light" href="#come-funziona">Come funziona <span>↓</span></a></div><div class="mini-notice">Servizio in fase di avvio: le videoconsulenze non sono ancora prenotabili. La prescrizione è decisa dal medico, solo per medicinali autorizzati e quando è appropriata.</div></div></section>
<section class="section-pad"><div class="wrap service-grid"><div><div class="section-label">01 / PER CHI È</div><h2>È pensata per te se…</h2><ul class="check-list">{li(c['for_whom'])}</ul></div><div><div class="section-label">02 / COSA FA IL MEDICO</div><h2>In videoconsulenza.</h2><ol class="numbered-list">{li(c['doctor'])}</ol><div class="fact-box exams-box"><span class="mini-label">ESAMI</span><p>{escape(c['exams'])}</p></div></div></div></section>
<section class="section-pad first-visit"><div class="wrap"><div class="section-label">LA PRIMA VIDEOCONSULENZA</div><h2>Come sarà, <em>passo per passo.</em></h2><div class="visit-grid"><div><span class="mini-label">PRIMA</span><h3>Prepara le tue domande</h3><p>Dopo il questionario scegli il medico. Tieni a portata di mano gli esami recenti e l’elenco di farmaci e integratori che usi.</p></div><div><span class="mini-label">DURANTE · 30–45 MINUTI</span><h3>Una conversazione vera</h3><p>Il medico ascolta la tua storia, chiarisce obiettivi e dubbi e valuta cosa serve per avere un quadro completo.</p></div><div><span class="mini-label">DOPO</span><h3>Un piano chiaro</h3><p>Ricevi le indicazioni, gli eventuali esami da fare e, se il medico lo ritiene appropriato, la prescrizione. Poi fissate insieme il prossimo controllo.</p></div></div></div></section>
<section class="principles how-section section-pad" id="come-funziona"><div class="wrap"><div class="section-label">03 / COME FUNZIONA</div><h2>Un medico al tuo fianco,<br><em>passo dopo passo.</em></h2>{STEPS}</div></section>
<section class="section-pad"><div class="wrap service-grid"><div><div class="section-label">04 / COSA NON FACCIAMO</div><h2>I limiti, <em>chiari.</em></h2><p class="limits-text">{escape(c['limits'])}</p></div><div><div class="section-label">05 / DOMANDE FREQUENTI</div><h2>FAQ.</h2><div class="faq">{faq}</div></div></div></section>
<section class="related-section"><div class="wrap">{library_block}{articles_block}<div class="other-services"><span class="mini-label">ALTRE CONSULENZE</span>{others}</div></div></section>'''
    path = f'/consulenze/{slug}/'
    title = f"Consulenza {c['name']} online con medici esperti" if len(c['name']) < 16 else f"Consulenza {c['name']} online"
    desc = clip(c['lede'])
    write(f'consulenze/{slug}/index.html', page(title, desc, body, path,
          schema=[webpage_ld('MedicalWebPage', path, title, desc, publisher={'@id': SITE_URL + '/#org'}), faq_ld(c['faq'])],
          crumbs=[('Home', '/'), ('Consulenze', '/consulenze/'), (c['name'], path)], image=og_image('consulenza-' + slug, f"Consulenza {c['name']}", 'VIDEOCONSULENZA')))

CONS_DESC = 'Videoconsulenze con medici esperti di peptidi, GLP-1, TRT, longevità, capelli, salute sessuale, menopausa e sport. Racconti il tuo obiettivo, scegli il tuo medico.'
consulenze_hub = f'''<section class="inner-hero"><div class="wrap"><div class="breadcrumbs"><a href="/">Home</a> / Consulenze</div><div class="section-label light-text">CONSULENZE / RETE DI MEDICI</div><h1>Consulenze online <em>con medici esperti.</em></h1><p>Una rete di medici esperti di terapie emergenti. Ci racconti il tuo obiettivo, ti proponiamo i medici più adatti e scegli tu con chi iniziare, in videochiamata.</p><div class="mini-notice">Servizio in fase di avvio: le videoconsulenze non sono ancora prenotabili. Lascia la tua email per sapere quando partiamo.</div></div></section><section class="services-section section-pad"><div class="wrap"><div class="services-grid">{service_html}</div></div></section><section class="principles how-section section-pad"><div class="wrap"><div class="section-label">COME FUNZIONA</div><h2>Un medico al tuo fianco,<br><em>passo dopo passo.</em></h2>{STEPS}</div></section>'''
write('consulenze/index.html', page('Consulenze mediche online: peptidi, GLP-1, TRT e longevità', CONS_DESC, consulenze_hub, '/consulenze/',
      schema=[webpage_ld('CollectionPage', '/consulenze/', 'Consulenze', CONS_DESC), itemlist_ld([(f"Consulenza {c['name']}", f"/consulenze/{SERVICE_SLUGS[c['name']]}/") for c in CONSULENZE])],
      crumbs=[('Home', '/'), ('Consulenze', '/consulenze/')], image=og_image('consulenze', 'Consulenze online con medici esperti', 'CONSULENZE')))

# ------------------------------------------------------------------ articoli
type_chips = ''.join(f'<button type="button" class="filter{" active" if t == "Tutti" else ""}" data-type="{t}" aria-pressed="{"true" if t == "Tutti" else "false"}">{t}</button>' for t in ['Tutti', 'Guida', 'News'])
article_items = ''.join(article_card(a).replace('<a class="article-card"', '<a class="article-card" data-type="' + a['type'] + '"', 1) for a in ARTICLES)
articoli = f'''<section class="inner-hero"><div class="wrap"><div class="section-label light-text">ARTICOLI / GUIDE E NEWS</div><h1>Articoli <em>e news.</em></h1><p>Guide per orientarsi e notizie dal mondo delle terapie emergenti, spiegate senza hype.</p></div></section><section class="section-pad"><div class="wrap"><div class="filters article-filters" role="group" aria-label="Filtra per tipo">{type_chips}</div><div class="article-grid article-list">{article_items}</div></div></section>'''
ART_DESC = 'Guide e notizie su peptidi, farmaci GLP-1, testosterone e longevità: cosa dicono gli studi e cosa cambia per chi vive in Italia.'
write('articoli/index.html', page('Articoli e news su peptidi, GLP-1, TRT e longevità', ART_DESC, articoli, '/articoli/',
      schema=[webpage_ld('CollectionPage', '/articoli/', 'Articoli', ART_DESC), itemlist_ld([(a['title'], f"/articoli/{a['slug']}/") for a in ARTICLES])],
      crumbs=[('Home', '/'), ('Articoli', '/articoli/')], image=og_image('articoli', 'Articoli e news', 'GUIDE E NEWS')))

for a in ARTICLES:
    rel = [p for s in a['related'] for p in DATA if p['slug'] == s]
    more = [b for b in ARTICLES if b is not a][:3]
    svc = a['service']
    minutes = max(1, round(len(re.findall(r'\w+', a['body'])) / 200))
    heads = [h[3:] for h in a['body'].splitlines() if h.startswith('## ')]
    art_toc = ('<nav class="toc" aria-label="In questo articolo"><span class="mini-label">IN QUESTO ARTICOLO</span>' + ''.join(f'<a href="#{slugify(h)}">{escape(h)}</a>' for h in heads) + '</nav>') if heads else ''
    art_color = CAT_COLORS[rel[0]['category']] if rel else '#7fb4d3'
    cta = f'''<div class="aside-cta"><span>LA CONSULENZA</span><h3>Vuoi parlarne con un medico?</h3><p>La nostra rete di medici sta per avviare le videoconsulenze.</p><a class="btn btn-dark full" href="/consulenze/{SERVICE_SLUGS[svc]}/">Consulenza {escape(svc)} ↗</a></div>''' if svc else ''
    body = f'''<section class="inner-hero"><div class="wrap"><div class="breadcrumbs"><a href="/">Home</a> / <a href="/articoli/">Articoli</a> / {escape(a['title'])}</div><div class="section-label light-text">{escape(a['type'].upper())} · {it_date(a['date'])} · {minutes} MIN DI LETTURA</div><h1 class="article-title">{escape(a['title'])}</h1><p>{escape(a['description'])}</p>{molecule_svg(a['slug'], art_color, dark=True, cls='hero-art article-art')}</div></section><section class="section-pad"><div class="wrap profile-grid"><article class="article-body">{render_md(a['body'])}<div class="dosing-warning" role="note"><strong>Contenuto informativo.</strong> Questo articolo non sostituisce il parere di un medico. Bozza editoriale in attesa di revisione medico-scientifica.</div></article><aside class="profile-aside">{art_toc}{cta}<div class="fact-box"><span class="mini-label">REDAZIONE</span><strong>AHEAD</strong><hr><span class="mini-label">PUBBLICATO</span><strong>{it_date(a['date'])}</strong></div></aside></div></section>'''
    if rel:
        body += f'''<section class="related-section"><div class="wrap"><div class="section-row"><h2>Le schede citate.</h2><a class="underlined-link" href="/library/">Tutta la Library ↗</a></div><div class="card-grid related-grid">{''.join(card(p, True) for p in rel[:6])}</div></div></section>'''
    if more:
        body += f'''<section class="section-pad"><div class="wrap"><div class="section-row"><h2>Leggi anche.</h2><a class="underlined-link" href="/articoli/">Tutti gli articoli ↗</a></div><div class="article-grid">{''.join(article_card(b) for b in more)}</div></div></section>'''
    path = f"/articoli/{a['slug']}/"
    img = og_image('articolo-' + a['slug'], a['title'], a['type'].upper())
    art_ld = {'@type': 'NewsArticle' if a['type'] == 'News' else 'Article', 'headline': a['title'], 'description': clip(a['description']),
              'datePublished': a['date'], 'dateModified': a.get('updated', a['date']), 'inLanguage': 'it-IT', 'image': abs_url(img),
              'author': {'@id': SITE_URL + '/#org'}, 'publisher': {'@id': SITE_URL + '/#org'}, 'mainEntityOfPage': abs_url(path)}
    if rel:
        art_ld['about'] = [{'@type': 'Thing', 'name': q['name'], 'url': abs_url(q['url'])} for q in rel]
    write(f'articoli/{a["slug"]}/index.html', page(a.get('seo_title', a['title']), clip(a['description']), body, path, schema=[ORG_LD, art_ld],
          crumbs=[('Home', '/'), ('Articoli', '/articoli/'), (a['title'], path)], og_type='article', image=img, lastmod=a.get('updated', a['date'])))

# ------------------------------------------------------------------ questionario (anonimo)
# Le domande sono definite solo qui: build.py genera sia la pagina /inizia/ sia lo
# schema usato da api/survey.js per validare le risposte. Il questionario è anonimo:
# non aggiungere mai nome, email, telefono o altri dati identificativi.
SURVEY_SUBSTANCES = ['Semaglutide', 'Tirzepatide', 'Retatrutide', 'Testosterone', 'Ormone della crescita (somatropina)', 'BPC-157', 'TB-500', 'MOTS-c',
                     'Rapamicina (sirolimus)', 'Metformina', 'Precursori del NAD+ (NMN e NR)', 'GHK-Cu', 'Melanotan II', 'Bremelanotide (PT-141)', 'CJC-1295', 'Ipamorelin']
assert all(any(p['name'] == n for p in DATA) for n in SURVEY_SUBSTANCES), 'SURVEY_SUBSTANCES: nome non presente nella Library'
SURVEY = [
    ('La tua area', 'Di cosa vorresti parlare con un medico?', [
        dict(id='aree', type='multi', required=True, label='Scegli una o più aree', options=SERVICES + ['Non lo so ancora'])]),
    ('I tuoi obiettivi', 'Cosa vorresti ottenere?', [
        dict(id='obiettivi', type='multi', required=True, max=3, label='Scegli fino a 3 obiettivi', options=[
            'Perdere peso', 'Più energia e meno stanchezza', 'Aumentare massa muscolare e forza', 'Recuperare da un infortunio o un dolore',
            'Migliorare la salute ormonale', 'Fermare la caduta dei capelli', 'Migliorare la vita sessuale', 'Gestire i sintomi della menopausa',
            'Prevenzione e longevità', 'Capire se una sostanza fa per me'])]),
    ('La tua situazione', 'Da dove parti?', [
        dict(id='gia_usato', type='multi', required=True, label='Per questi obiettivi hai già usato…', options=[
            'Farmaci prescritti da un medico', 'Peptidi o sostanze acquistati online', 'Integratori', 'Niente di tutto questo']),
        dict(id='seguito', type='single', required=True, label='Sei seguito da un medico per questo?', options=['Sì', 'No', 'In passato']),
        dict(id='esami', type='single', required=True, label='Hai esami del sangue recenti (ultimi 6 mesi)?', options=['Sì', 'No', 'Non ricordo'])]),
    ('Le sostanze', 'Ce n’è qualcuna su cui vorresti un parere?', [
        dict(id='sostanze', type='multi', required=False, label='Facoltativo: scegli quelle che ti interessano', options=SURVEY_SUBSTANCES + ['Altre', 'Nessuna in particolare'])]),
    ('Su di te', 'Qualche informazione generale', [
        dict(id='eta', type='single', required=True, label='Fascia d’età', options=['18–29', '30–39', '40–49', '50–59', '60 o più']),
        dict(id='sesso', type='single', required=True, label='Sesso', options=['Uomo', 'Donna', 'Preferisco non dirlo']),
        dict(id='zona', type='single', required=False, label='Dove vivi', options=['Nord Italia', 'Centro Italia', 'Sud Italia e isole', 'Fuori dall’Italia'])]),
    ('Il servizio', 'Come lo immagini', [
        dict(id='urgenza', type='single', required=True, label='Quando vorresti iniziare?', options=['Il prima possibile', 'Entro 3 mesi', 'Sto solo esplorando']),
        dict(id='budget', type='single', required=True, label='Quanto spenderesti per una prima videoconsulenza di 30–45 minuti?', options=['Meno di 50 €', '50–100 €', '100–150 €', 'Più di 150 €']),
        dict(id='percorso', type='single', required=True, label='Ti interesserebbe un percorso con controlli periodici (abbonamento mensile)?', options=['Sì', 'Forse', 'No']),
        dict(id='lingua', type='single', required=False, label='Il medico deve parlare italiano?', options=['Sì, necessariamente', 'Va bene anche in inglese']),
        dict(id='fonte', type='single', required=False, label='Come ci hai conosciuto?', options=['Google', 'Instagram o TikTok', 'YouTube o podcast', 'Passaparola', 'Altro'])]),
    ('In due parole', 'C’è altro che vorresti dirci?', [
        dict(id='note', type='text', required=False, max=500, label='Facoltativo: cosa vorresti chiedere al medico?')]),
]
SURVEY_FIELDS = [q for _, _, qs in SURVEY for q in qs]
write('api/_survey-schema.js', '// Generato da build.py: non modificare a mano.\nexport default ' + json.dumps(
    {q['id']: {k: q[k] for k in ('type', 'required', 'options', 'max') if k in q} for q in SURVEY_FIELDS}, ensure_ascii=False, indent=1) + ';\n')


def survey_question(q):
    hint = f'<span class="q-hint">Massimo {q["max"]}</span>' if q['type'] == 'multi' and q.get('max') else ''
    req = '' if q['required'] else '<span class="q-optional">facoltativo</span>'
    if q['type'] == 'text':
        return (f'<div class="q-block"><label class="q-label" for="q-{q["id"]}">{escape(q["label"])}</label>'
                f'<textarea id="q-{q["id"]}" name="{q["id"]}" maxlength="{q["max"]}" rows="4" placeholder="Per esempio: vorrei capire se la terapia che sto facendo è adatta a me."></textarea>'
                f'<p class="q-warning">Non scrivere il tuo nome, la tua email o altri dati che possano identificarti.</p></div>')
    kind = 'checkbox' if q['type'] == 'multi' else 'radio'
    opts = ''.join(f'<label class="choice"><input type="{kind}" name="{q["id"]}" value="{escape(o, quote=True)}"'
                   f'{f" data-slug={chr(34)}{SERVICE_SLUGS[o]}{chr(34)}" if q["id"] == "aree" and o in SERVICE_SLUGS else ""}><span>{escape(o)}</span></label>' for o in q['options'])
    attrs = f' data-required="{str(q["required"]).lower()}"' + (f' data-max="{q["max"]}"' if q.get('max') else '')
    return f'<fieldset class="q-block" data-q="{q["id"]}"{attrs}><legend class="q-label">{escape(q["label"])} {req}{hint}</legend><div class="choices">{opts}</div></fieldset>'


steps_html = ''.join(
    f'<section class="survey-step" data-step="{i}"{"" if i == 1 else " hidden"} aria-labelledby="step-title-{i}"><span class="step-kicker">{i} / {len(SURVEY)} · {escape(kicker.upper())}</span>'
    f'<h2 id="step-title-{i}" tabindex="-1">{escape(title)}</h2>{"".join(survey_question(q) for q in qs)}</section>'
    for i, (kicker, title, qs) in enumerate(SURVEY, 1))
survey = f'''<section class="inner-hero survey-hero"><div class="wrap"><div class="breadcrumbs"><a href="/">Home</a> / Trova il tuo medico</div><div class="section-label light-text">QUESTIONARIO / 2 MINUTI</div><h1>Trova il medico <em>giusto per te.</em></h1><p>Raccontaci cosa vorresti ottenere: useremo le risposte per costruire il servizio e abbinarti ai medici più adatti della nostra rete.</p><div class="mini-notice">Il questionario è <strong>anonimo</strong>: non chiediamo nome, email o telefono. Le videoconsulenze non sono ancora prenotabili.</div></div></section>
<section class="section-pad"><div class="wrap survey-wrap"><div class="survey-progress" aria-hidden="true"><span id="survey-bar"></span></div>
<form id="survey-form" class="survey-form" novalidate><div class="hp-field" aria-hidden="true"><label for="survey-website">Lascia vuoto questo campo</label><input type="text" id="survey-website" name="website" tabindex="-1" autocomplete="off"></div>{steps_html}
<p class="survey-error" id="survey-error" role="alert"></p><div class="survey-nav"><button type="button" class="btn btn-ghost" id="survey-back" hidden>← Indietro</button><button type="button" class="btn btn-dark" id="survey-next">Avanti <span>→</span></button><button type="submit" class="btn btn-dark" id="survey-submit" hidden>Invia le risposte <span>↗</span></button></div></form>
<div class="survey-done" id="survey-done" hidden tabindex="-1"><span class="step-kicker">GRAZIE</span><h2>Risposte ricevute.</h2><p>Ci aiutano a capire di cosa hanno bisogno le persone e quali medici coinvolgere per primi.</p><p>Vuoi sapere quando apriamo le prenotazioni? Lascia la tua email: l’iscrizione è separata dal questionario e non viene collegata alle tue risposte.</p><button type="button" class="btn btn-dark interest-trigger" data-service="generale">Avvisami al lancio <span>↗</span></button><p><a class="underlined-link" href="/library/">Intanto esplora la Library ↗</a></p></div>
<noscript><p class="survey-error">Per compilare il questionario serve JavaScript attivo.</p></noscript></div></section>'''
SURVEY_DESC = 'Un questionario anonimo di 2 minuti: raccontaci obiettivi e interessi e ti abbiniamo ai medici esperti più adatti della nostra rete.'
write('inizia/index.html', page('Trova il medico giusto per te — questionario', SURVEY_DESC, survey, '/inizia/',
      crumbs=[('Home', '/'), ('Trova il tuo medico', '/inizia/')], image=og_image('inizia', 'Trova il medico giusto per te', 'QUESTIONARIO')))

# ------------------------------------------------------------------ metodo
grid_legend = ''.join(f'<li><strong>{escape(label)}</strong></li>' for _, label in EVIDENCE_ROWS)
status_legend = ''.join(f'<li><span class="status {cls}"><i></i>{escape(label)}</span></li>' for label, cls in STATUS.values())
metodo = f'''<section class="inner-hero"><div class="wrap"><div class="section-label light-text">DOCUMENTAZIONE / METODO</div><h1>Il nostro <em>metodo.</em></h1><p>Come scegliamo le fonti, come classifichiamo le prove e cosa non troverai mai nelle nostre schede.</p></div></section><section class="section-pad"><div class="wrap privacy-content"><div class="review-notice"><strong>Stato attuale:</strong> le schede sono bozze editoriali. La revisione medico-scientifica indipendente non è ancora stata effettuata: il nome del revisore e la data di revisione compariranno su ogni scheda quando sarà completata.</div>
<h2>Da dove vengono le prove</h2><p>Ogni scheda indica per cinque livelli se esistono prove e di che qualità. I livelli non sono equivalenti: un risultato su cellule o su topi non dimostra un beneficio nelle persone. Più si sale nella piramide, più le prove sono affidabili per decidere su una terapia.</p><figure class="pyramid-figure">{evidence_pyramid()}<figcaption>La piramide delle prove: alla base gli studi di laboratorio, al vertice i medicinali che hanno superato studi clinici e valutazione delle autorità.</figcaption></figure><ol class="method-list">{grid_legend}</ol><p>Per ogni livello usiamo tre gradi: <strong>Presenti</strong> (più studi coerenti), <strong>Limitate</strong> (pochi studi, piccoli, non replicati o con limiti importanti), <strong>Assenti</strong>. Per l’autorizzazione: <strong>Sì</strong> (medicinale autorizzato in UE), <strong>Parziale</strong> (autorizzato solo fuori UE o per un’altra indicazione), <strong>No</strong>.</p>
<h2>Stato regolatorio</h2><ul class="method-status">{status_legend}</ul><p>Lo stato si riferisce all’Unione europea, salvo diversa indicazione. Le decisioni di autorità extra-UE (per esempio FDA) sono riportate nel testo, ma non rendono un prodotto autorizzato in Italia.</p>
<h2>Gerarchia delle fonti</h2><p>Diamo priorità a: documenti delle autorità regolatorie (EMA, AIFA, FDA), studi clinici randomizzati pubblicati, revisioni sistematiche, studi osservazionali, studi su animali e in vitro. Comunicati aziendali e notizie sono indicati come tali e usati solo per aggiornamenti recenti non ancora pubblicati altrove.</p>
<h2>Revisione e aggiornamento</h2><p>Ogni scheda riporta la data dell’ultima verifica delle fonti. Le schede vengono ricontrollate almeno ogni sei mesi e ogni volta che cambia lo stato regolatorio. Prima della pubblicazione definitiva ogni scheda dovrà essere approvata da un medico revisore indipendente.</p>
<h2>Dosi e modalità d’uso</h2><p>Ogni scheda indica come la sostanza viene assunta e da dove provengono le dosi riportate: il foglietto illustrativo approvato in UE, un foglietto approvato fuori UE, gli studi clinici pubblicati, oppure nessuna fonte affidabile. Quando non esiste una dose studiata nell’uomo non riportiamo le quantità che circolano online. Le dosi sono informazioni, non indicazioni: ogni trattamento richiede una visita e l’approvazione di un medico.</p>
<h2>Cosa non facciamo</h2><p>Non indichiamo fornitori né prodotti “per uso di ricerca”. Non promettiamo prescrizioni: il medico prescrive solo medicinali autorizzati, quando li ritiene appropriati. Le schede non contengono link di affiliazione né contenuti sponsorizzati.</p>
<h2>Segnalare un errore</h2><p>Un indirizzo dedicato alle segnalazioni sarà pubblicato al lancio. Ogni correzione sostanziale sarà indicata nella scheda.</p></div></section>'''
write('metodo/index.html', page('Metodo editoriale: come valutiamo le prove scientifiche', 'Come AHEAD seleziona le fonti, classifica le prove scientifiche (in vitro, animali, osservazionali, RCT) e aggiorna le schede della Library.', metodo, '/metodo/',
      crumbs=[('Home', '/'), ('Metodo', '/metodo/')]))

# ------------------------------------------------------------------ privacy
privacy = '''<section class="inner-hero"><div class="wrap"><div class="section-label light-text">DOCUMENTAZIONE</div><h1>Privacy <em>e trasparenza.</em></h1><p>Informativa provvisoria. Da completare prima di attivare la raccolta di indirizzi email.</p></div></section><section class="section-pad"><div class="wrap privacy-content"><div class="review-notice"><strong>Prima della pubblicazione:</strong> inserire titolare effettivo del trattamento, contatti, base giuridica, tempi di conservazione, fornitori, trasferimenti, diritti e istruzioni aggiornate. Non attivare il modulo in produzione senza l’informativa definitiva.</div><h2>Perché raccogliere email?</h2><p>L’unico scopo previsto è inviare aggiornamenti sul progetto a chi ne fa richiesta con consenso esplicito. Non chiediamo informazioni su diagnosi, terapie o condizioni di salute.</p><h2>Quali strumenti useremo?</h2><p>MailerLite per l’invio di email e, previo assetto privacy adeguato, uno strumento di analytics per contare gli interessi in forma aggregata. Le integrazioni non sono ancora attive nella demo.</p><h2>Questionario “Trova il tuo medico”</h2><p>Il questionario è anonimo: non chiede nome, email, telefono o altri dati identificativi, e non registriamo indirizzo IP né informazioni sul dispositivo. Salviamo solo le risposte scelte e la data, per capire in forma aggregata quali servizi e quali medici sono più richiesti. Ti chiediamo di non inserire dati che possano identificarti nel campo di testo libero. L’eventuale iscrizione via email è separata e non viene collegata alle risposte.</p><h2>Ricerca nella Library</h2><p>La ricerca e i filtri funzionano interamente nel tuo browser: i termini cercati non vengono inviati a nessun server.</p><h2>Servizi sanitari</h2><p>Il progetto non è una struttura sanitaria operativa e non offre visite, prescrizioni o terapie.</p></div></section>'''
write('privacy/index.html', page('Privacy — informativa provvisoria', 'Informazioni sulla gestione dei dati per il progetto AHEAD.', privacy, '/privacy/'))

# ------------------------------------------------------------------ 404
not_found = '''<section class="inner-hero"><div class="wrap"><div class="section-label light-text">ERRORE 404</div><h1>Pagina <em>non trovata.</em></h1><p>La pagina che cerchi non esiste o è stata spostata.</p><div class="hero-actions"><a class="btn btn-light" href="/library/">Vai alla Library <span>↗</span></a><a class="link-light" href="/">Torna alla home</a></div></div></section>'''
write('404.html', page('Pagina non trovata', 'Pagina non trovata.', not_found, '/404', indexable=False))

write('favicon.svg', '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="15" fill="#111a1d"/><path d="M14 47 29 16h7l15 31h-9l-4-9H26l-4 9zm15-16h7l-4-10z" fill="#b8d9f5"/><circle cx="53" cy="13" r="5" fill="#e8e89a"/></svg>''')
# ------------------------------------------------------------------ elenco nomi per le foto
photo_list = '\n'.join(f'| `{q["slug"]}` | {q["name"]} |' for q in sorted(DATA, key=lambda q: q['slug']))
area_list = '\n'.join(f'| `{slugify(c)}` | {c} |' for c in used_categories)
cons_list = '\n'.join(f'| `{SERVICE_SLUGS[c["name"]]}` | {c["name"]} |' for c in CONSULENZE)
write('img/LEGGIMI.md', f"""# Foto delle intestazioni

Le foto vanno a tutta larghezza come sfondo dell'intestazione, dietro titolo e testo.
Carica il file nella cartella giusta con il **nome indicato qui sotto** (maiuscole e spazi non contano: `Semaglutide.JPG` va bene).
Su GitHub: apri la cartella → **Add file → Upload files** → **Commit changes** su `main`.
Entro un paio di minuti GitHub rigenera il sito e Vercel lo pubblica.

- `img/schede/<nome>.jpg` → foto di una scheda
- `img/aree/<nome>.jpg` → foto usata da tutte le schede di un'area che non hanno una foto propria
- `img/consulenze/<nome>.jpg` → foto dell'intestazione di una consulenza

Consigli: foto orizzontali, almeno 2400 px di larghezza, soggetto sulla destra (a sinistra c'è il testo). Formati jpg, png o webp.
Usa solo immagini con licenza adatta (tue, Unsplash, Pexels, Adobe Stock…).
Per sostituire una foto basta caricarne un'altra con lo stesso nome; per toglierla, eliminarla.

## Schede (`img/schede/`)
| Nome file | Scheda |
|---|---|
{photo_list}

## Aree (`img/aree/`)
| Nome file | Area |
|---|---|
{area_list}

## Consulenze (`img/consulenze/`)
| Nome file | Consulenza |
|---|---|
{cons_list}
""")

# ------------------------------------------------------------------ sitemap / robots
urls = ''.join(f'<url><loc>{abs_url(path)}</loc><lastmod>{mod}</lastmod></url>' for path, mod in SITEMAP)
write('sitemap.xml', f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
write('robots.txt', (f'User-agent: *\nAllow: /\nDisallow: /api/\n\nSitemap: {SITE_URL}/sitemap.xml\n' if INDEXABLE else 'User-agent: *\nDisallow: /\n'))
write('og/pages.json', json.dumps(OG_JOBS, ensure_ascii=False, indent=1) + '\n')
missing = [j['file'] for j in OG_JOBS if not (ROOT / j['file']).exists()]
if missing:
    print(f'Attenzione: {len(missing)} immagini social mancanti. Lancia: node scripts/og-images.js && python3 build.py')
long_titles = [t for t in re.findall(r'<title>(.*?)</title>', ''.join((ROOT / (path.strip('/') + '/index.html' if path != '/' else 'index.html')).read_text() for path, _ in SITEMAP)) if len(t.replace('&amp;', '&')) > 75]
if long_titles:
    print('Titoli lunghi (>75 caratteri):', *long_titles, sep='\n  ')
print(f'Generate {N} schede + {len(ARTICLES)} articoli + {len(CONSULENZE)} consulenze + homepage + library + metodo + privacy + 404')
