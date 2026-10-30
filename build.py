"""Genera le pagine statiche del sito a partire da data/schede/*.json.

Uso: python3 build.py
Ogni file JSON in data/schede/ è una scheda. Il build si interrompe se una
scheda non rispetta lo schema (vedi validate()).
"""
from pathlib import Path
from html import escape
from urllib.parse import quote
import json
import re
import sys

ROOT = Path(__file__).parent
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
            flush(); html.append(f'<h2>{inline_md(line[3:])}</h2>')
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

NAV = '''<a class="logo" href="/" aria-label="AHEAD — home"><span class="logo-mark">A<span class="logo-spark">✳</span></span><span class="logo-word">AHEAD<span class="logo-dot">.</span><small>MEDICINE / PROJECT</small></span></a><nav class="nav-links" aria-label="Navigazione principale"><a href="/library/">Library</a><a href="/#consulenze">Consulenze</a><a href="/articoli/">Articoli</a><a href="/metodo/">Metodo</a></nav><a href="/#interesse" class="nav-cta">Ricevi aggiornamenti <span>↗</span></a><button class="mobile-menu" type="button" aria-label="Apri menu" aria-expanded="false">☰</button>'''
FOOTER = '''<footer class="footer"><div class="wrap footer-main"><div><a class="footer-logo" href="/">AHEAD<span>.</span></a><p>Medicina emergente, senza scorciatoie.</p><p class="muted">Nome e identità visiva provvisori.</p></div><div class="footer-links"><a href="/library/">Library</a><a href="/#consulenze">Consulenze</a><a href="/articoli/">Articoli</a><a href="/metodo/">Metodo editoriale</a><a href="/privacy/">Privacy</a></div></div><div class="wrap footer-bottom"><span>© 2026 AHEAD · Progetto in fase di esplorazione</span><span>Contenuti informativi. Nessun servizio sanitario attualmente erogato.</span></div></footer>'''
MODAL = '''<div class="modal-backdrop" id="interest-modal" hidden><div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" aria-describedby="modal-description"><button type="button" class="modal-close" data-close-modal aria-label="Chiudi">×</button><div class="eyebrow dark-ink">MANIFESTAZIONE DI INTERESSE</div><h2 id="modal-title">Restiamo in contatto.</h2><p id="modal-description">Stiamo valutando questo servizio. Lascia la tua email per ricevere aggiornamenti sul progetto.</p><form id="interest-form"><label for="interest-email">La tua email</label><input type="email" id="interest-email" name="email" placeholder="nome@email.it" autocomplete="email" required maxlength="254"><div class="hp-field" aria-hidden="true"><label for="interest-website">Lascia vuoto questo campo</label><input type="text" id="interest-website" name="website" tabindex="-1" autocomplete="off"></div><label class="checkline"><input id="interest-consent" type="checkbox" required><span>Acconsento a ricevere comunicazioni email relative al progetto. Ho letto l'<a href="/privacy/" target="_blank">informativa privacy</a>.</span></label><button class="btn btn-dark full" type="submit" id="form-submit">Ricevi aggiornamenti <span>↗</span></button><p class="form-message" id="form-message" role="status" aria-live="polite"></p></form><p class="note">Non chiediamo informazioni sulla tua salute. Iscrizione gratuita, cancellazione possibile in ogni momento.</p></div></div>'''
HEAD_META = '''<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#10171b"><link rel="stylesheet" href="/styles.css"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><script defer src="/app.js"></script>'''


def page(title, desc, body, indexable=False):
    robots = '' if indexable else '<meta name="robots" content="noindex,nofollow">'
    return f'''<!doctype html><html lang="it"><head>{HEAD_META}<title>{escape(title)} | AHEAD Medicine</title><meta name="description" content="{escape(desc, quote=True)}">{robots}</head><body><div class="topbar">PROGETTO IN FASE DI SVILUPPO <span class="topbar-sep">/</span> SERVIZI NON ANCORA DISPONIBILI</div><header class="site-header"><div class="wrap header-inner">{NAV}</div></header><main>{body}</main>{FOOTER}{MODAL}</body></html>'''


def write(rel, html):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding='utf-8')


def status_badge(p):
    label, cls = STATUS[p['status']]
    return f'<span class="status {cls}"><i></i>{escape(label)}</span>'


def card(p, small=False):
    cls = 'peptide-card small' if small else 'peptide-card'
    cats = [p['category'], *p.get('extra_categories', [])]
    search = ' '.join([p['name'], p['focus'], *cats, *p['aliases']]).lower()
    return (f'''<a class="{cls}" href="{p['url']}" data-categories="{escape('|'.join(cats), quote=True)}" data-kind="{p['kind']}" data-status="{p['status']}" data-search="{escape(search, quote=True)}">'''
            f'''<div class="pc-head"><span class="pc-tag">{escape(p['category'])}</span><span class="pc-arrow">↗</span></div>'''
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
service_html = ''.join(f'''<article class="service-card"><span class="service-number">{i:02d} / CONSULENZA</span><h3><a href="/consulenze/{SERVICE_SLUGS[name]}/">{escape(name)}</a></h3><p>{escape(desc)}</p><div class="service-actions"><a class="text-cta" href="/consulenze/{SERVICE_SLUGS[name]}/">Scopri la consulenza <span>→</span></a><button class="text-cta interest-trigger" type="button" data-service="{escape(name, quote=True)}">Sono interessato <span>↗</span></button></div></article>''' for i, (name, desc) in enumerate(services, 1))
featured = [p for s in FEATURED for p in DATA if p['slug'] == s]

home = f'''<section class="hero"><div class="wrap hero-grid"><div class="hero-content"><div class="eyebrow"><span class="pulse-dot"></span> MEDICINA EMERGENTE, SENZA HYPE.</div><h1>La medicina<br>di <em>domani.</em><br>Le risposte di oggi.</h1><p class="hero-lede">Peptidi, terapie innovative, longevità e performance. Un nuovo servizio per chi vuole capire davvero cosa sta cambiando nella medicina — e farsi seguire, in videoconsulenza, da medici esperti di terapie emergenti.</p><div class="hero-actions"><a class="btn btn-light" href="/library/">Esplora la Library <span>↗</span></a><a class="link-light" href="#consulenze">Scopri le consulenze <span>↓</span></a></div><p class="hero-footnote">Servizio in fase di avvio. Le consulenze non sono ancora prenotabili.</p></div><div class="hero-visual" aria-hidden="true"><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="orbit orbit-three"></div><div class="molecule-core"><span class="core-a"></span><span class="core-b"></span><span class="core-c"></span></div><span class="visual-code visual-code-top">EMERGING<br>MEDICINE<br>— 2026</span><span class="visual-code visual-code-bottom">RESEARCH /<br>EVIDENCE /<br>CLARITY</span></div></div><div class="wrap hero-stats"><span>01 / LIBRARY: {N} SCHEDE</span><span>02 / VIDEOCONSULENZE CON MEDICI ESPERTI</span><span>03 / RICERCA & INNOVAZIONE</span></div></section>
<section class="intro-section section-pad" id="approccio"><div class="wrap intro-grid"><div><div class="section-label">01 / IL PROGETTO</div><h2>Le innovazioni corrono.<br><span class="muted-heading">Le informazioni spesso no.</span></h2></div><div class="intro-copy"><p>Internet parla di BPC-157, GLP-1, rapamicina e terapie emergenti. Ma tra entusiasmi, studi preliminari e pubblicità è difficile capire cosa sia realmente dimostrato.</p><p>Vogliamo creare uno spazio in cui la curiosità incontra il rigore scientifico: informazioni affidabili e, a breve, videoconsulenze con i medici della nostra rete.</p><a class="underlined-link" href="/metodo/">Come valutiamo le prove ↗</a></div></div></section>
<section class="library-section section-pad" id="library"><div class="wrap"><div class="section-label">02 / KNOWLEDGE FIRST</div><div class="section-row"><div><h2>La <em>Library.</em></h2><p class="section-subtitle">Peptidi, farmaci e molecole emergenti. Per ognuno: cosa è dimostrato, cosa no.</p></div><a class="outlined-link" href="/library/">Tutte le {N} schede ↗</a></div><div class="card-grid">{''.join(card(p) for p in featured)}</div><div class="library-bottom"><div class="big-asterisk">✳</div><p>Come funziona. Cosa è stato studiato, dal laboratorio agli studi clinici. Quali rischi conosciamo. Cosa è autorizzato e cosa è ancora sperimentale.</p><a href="/library/" class="btn btn-dark">Entra nella Library <span>↗</span></a></div></div></section>
<section class="section-pad articles-home"><div class="wrap"><div class="section-label">ARTICOLI / GUIDE E NEWS</div><div class="section-row"><div><h2>Capire, <em>prima di scegliere.</em></h2><p class="section-subtitle">Guide e notizie su peptidi, farmaci e longevità.</p></div><a class="outlined-link" href="/articoli/">Tutti gli articoli ↗</a></div><div class="article-grid">{''.join(article_card(a) for a in ARTICLES[:3])}</div></div></section>
<section class="services-section section-pad" id="consulenze"><div class="wrap"><div class="section-label light-text">03 / IL SERVIZIO</div><div class="section-row"><div><h2>Non un altro<br><em>programma wellness.</em></h2><p class="section-subtitle">Una rete di medici esperti di terapie emergenti. Ci racconti il tuo obiettivo, ti abbiniamo ai medici più adatti e scegli tu con chi iniziare. Stiamo organizzando l’avvio del servizio.</p></div><span class="launch-chip">COMING SOON <i></i></span></div><div class="services-grid">{service_html}</div><div class="services-foot"><span>Le consulenze non sono ancora prenotabili. La prescrizione non è garantita: il medico la valuta caso per caso, solo per medicinali autorizzati e quando è appropriata.</span><span>Serve una valutazione medica, non una scorciatoia.</span></div></div></section>
<section class="principles how-section section-pad" id="come-funziona"><div class="wrap"><div class="section-label">04 / COME FUNZIONA</div><h2>Un medico al tuo fianco,<br><em>passo dopo passo.</em></h2>{STEPS}</div></section>
<section class="principles section-pad"><div class="wrap"><div class="section-label">05 / OUR STANDARD</div><h2>Curiosità radicale.<br><em>Rigore assoluto.</em></h2><div class="principles-grid"><div><span>01</span><h3>Prove, non promesse</h3><p>Per ogni sostanza distinguiamo studi in vitro, su animali, osservazionali, clinici randomizzati e medicinali autorizzati.</p></div><div><span>02</span><h3>Domande intelligenti</h3><p>Non celebriamo né demonizziamo una molecola: valutiamo cosa dicono i dati disponibili.</p></div><div><span>03</span><h3>Medicina responsabile</h3><p>Le dosi nelle schede sono quelle dei foglietti approvati o degli studi, mai consigli fai-da-te. Le decisioni cliniche spettano ai medici, nel rispetto di indicazioni, autorizzazioni e sicurezza.</p></div></div></div></section>
<section class="signup-section section-pad" id="interesse"><div class="wrap signup-grid"><div><div class="section-label">06 / STAY AHEAD</div><h2>La prossima<br>frontiera? <em>Seguici.</em></h2><p>Stiamo organizzando l’avvio delle videoconsulenze e ampliando la Library. Lasciaci la tua email per sapere quando partiamo.</p></div><div class="signup-panel"><div class="panel-icon">↗</div><h3>Entra nella lista di aggiornamento.</h3><p>Le consulenze non sono ancora prenotabili. Ti scriveremo solo per aggiornarti sul lancio.</p><button type="button" class="btn btn-dark full interest-trigger" data-service="generale">Ricevi aggiornamenti <span>↗</span></button><span class="note">Non raccogliamo dati sanitari. Puoi cancellarti quando vuoi.</span></div></div></section>'''
write('index.html', page('Peptidi, longevità e medicina emergente', 'Library su peptidi e terapie emergenti e futuro progetto di consulenza medica su longevità, metabolismo e performance.', home))

# ------------------------------------------------------------------ library
used_categories = [c for c in CATEGORIES if any(c == p['category'] or c in p.get('extra_categories', []) for p in DATA)]
used_status = [s for s in STATUS if any(p['status'] == s for p in DATA)]
chips = ''.join(f'<button type="button" class="filter{" active" if c == "Tutti" else ""}" data-filter="{escape(c, quote=True)}" aria-pressed="{"true" if c == "Tutti" else "false"}">{escape(c)}</button>' for c in ['Tutti'] + used_categories)
kind_opts = '<option value="">Tutti i tipi</option>' + ''.join(f'<option value="{k}">{escape(v[0])}</option>' for k, v in KINDS.items())
status_opts = '<option value="">Tutti gli stati</option>' + ''.join(f'<option value="{s}">{escape(STATUS[s][0])}</option>' for s in used_status)
library = f'''<section class="inner-hero"><div class="wrap"><div class="section-label light-text">RESEARCH / LIBRARY</div><h1>La <em>Library.</em></h1><p>{N} schede su peptidi, farmaci e molecole emergenti. Per ognuna: livelli di evidenza, rischi e stato autorizzativo. Senza confondere ricerca e terapia.</p><div class="mini-notice">Le schede sono bozze editoriali in attesa di revisione medico-scientifica indipendente e non rappresentano consigli terapeutici. <a href="/metodo/">Come lavoriamo ↗</a></div></div></section><section class="section-pad library-page"><div class="wrap"><div class="library-controls"><label class="search-label"><span aria-hidden="true">⌕</span><input id="peptide-search" type="search" placeholder="Cerca per nome, area o sinonimo…" aria-label="Cerca nella Library"></label><div class="selects"><label class="select-label"><span class="visually-hidden">Tipo</span><select id="kind-filter" aria-label="Filtra per tipo">{kind_opts}</select></label><label class="select-label"><span class="visually-hidden">Stato regolatorio</span><select id="status-filter" aria-label="Filtra per stato regolatorio">{status_opts}</select></label></div></div><div class="filters" role="group" aria-label="Filtra per area">{chips}</div><p class="results-count" id="results-count" aria-live="polite">{N} risultati</p><div class="card-grid library-results">{''.join(card(p, True) for p in DATA)}</div><p id="no-results" class="empty-results" hidden>Nessuna scheda corrisponde alla ricerca.</p></div></section>'''
write('library/index.html', page('Library — peptidi e terapie emergenti', f'{N} schede su peptidi, GLP-1, ormoni e molecole per la longevità: livelli di evidenza, rischi e stato autorizzativo in Europa.', library))

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
    body = f'''<section class="inner-hero peptide-hero"><div class="wrap"><div class="breadcrumbs"><a href="/">Home</a> / <a href="/library/">Library</a> / {escape(p['name'])}</div><div class="section-label light-text">{escape(kind_label.upper())} / {escape(p['category'].upper())}</div><h1>{escape(p['name'])}<span class="little-star">✳</span></h1><p>{escape(p['tagline'])}</p>{status_badge(p)}</div></section><section class="section-pad profile-section"><div class="wrap profile-grid"><article class="profile-main"><div class="review-notice"><strong>Bozza informativa — revisione medica indipendente non ancora effettuata.</strong><br>Ultima verifica editoriale delle fonti: {checked}. Questa pagina non sostituisce il parere di un medico.</div><div class="section-label">01 / IN BREVE</div><h2>Che cos'è {escape(p['name'])}?</h2>{aliases}<p>{escape(p['what'])}</p><div class="section-label space-top">02 / LE PROVE</div><h2>Da dove vengono le prove.</h2>{evidence_grid(p)}<h3 class="sub-heading">Cosa non sappiamo ancora</h3><p>{escape(p['unknown'])}</p><div class="section-label space-top">03 / COME SI ASSUME</div><h2>Modalità d’uso e dosi.</h2><div class="dosing-box"><span class="dosing-basis">{escape(DOSING_BASIS[p['dosing']['basis']])}</span><p class="dosing-route"><strong>Via di somministrazione:</strong> {escape(p['dosing']['route'])}</p><p>{escape(p['dosing']['text'])}</p></div><div class="dosing-warning" role="note"><strong>Informazione, non indicazione.</strong> Le dosi riportate descrivono come la sostanza è usata nei medicinali approvati o negli studi clinici. Non sono consigli da seguire: ogni trattamento richiede una visita e l’approvazione di un medico, che valuta indicazione, controindicazioni ed esami. Non usare prodotti acquistati fuori dai canali autorizzati.</div><div class="section-label space-top">04 / RISCHI</div><h2>Sicurezza e limiti.</h2><p>{escape(p['risk'])}</p><div class="section-label space-top">05 / REGOLAMENTAZIONE</div><h2>È autorizzato in Europa?</h2><p>{escape(p['reg'])}</p><div class="section-label space-top">06 / LE FONTI</div><h2>Approfondisci la ricerca.</h2><div class="source-links">{refs_html}</div><p class="citation-note">Link a fonti ufficiali e studi per orientarsi. La bibliografia completa con grading delle prove sarà aggiunta con la revisione medico-scientifica. <a href="/metodo/">Il nostro metodo ↗</a></p></article><aside class="profile-aside"><div class="fact-box"><span class="mini-label">AREA DI RICERCA / APPLICAZIONE</span><strong>{escape(p['focus'])}</strong><hr><span class="mini-label">TIPO</span><strong>{escape(kind_label)}</strong><hr><span class="mini-label">QUALITÀ DELLE PROVE</span><strong>{escape(p['evidence_summary'])}</strong><hr><span class="mini-label">STATO REGOLATORIO</span><strong>{escape(STATUS[p['status']][0])}</strong><hr><span class="mini-label">REVISIONE MEDICA</span><strong>{escape(reviewer)}</strong><hr><span class="mini-label">ULTIMA VERIFICA FONTI</span><strong>{checked}</strong></div><div class="aside-cta"><span>THE HUMAN SIDE OF RESEARCH</span><h3>Vuoi parlarne con un medico?</h3><p>La nostra rete di medici sta per avviare le videoconsulenze. Lascia la tua email per sapere quando partiamo.</p><button type="button" class="btn btn-dark full interest-trigger" data-service="{escape(p['service'] or 'generale', quote=True)}">Sono interessato ↗</button><small>Servizio in avvio. La prescrizione è decisa dal medico e solo se appropriata.</small></div></aside></div></section><section class="related-section"><div class="wrap"><div class="section-row"><h2>Continua a esplorare.</h2><a class="underlined-link" href="/library/">Tutte le schede ↗</a></div><div class="card-grid related-grid">{''.join(card(q, True) for q in related(p))}</div></div></section>'''
    write(p['url'].strip('/') + '/index.html', page(f'{p["name"]}: evidenze, rischi e stato in Europa', f'{p["name"]}: cosa dice la ricerca, dal laboratorio agli studi clinici, quali sono i rischi e qual è lo stato autorizzativo europeo.', body))

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
    body = f'''<section class="inner-hero"><div class="wrap"><div class="breadcrumbs"><a href="/">Home</a> / <a href="/#consulenze">Consulenze</a> / {escape(c['name'])}</div><div class="section-label light-text">CONSULENZA / {escape(c['name'].upper())}</div><h1>{c['title']}</h1><p>{escape(c['lede'])}</p><div class="hero-actions"><button type="button" class="btn btn-light interest-trigger" data-service="{escape(c['name'], quote=True)}">Sono interessato <span>↗</span></button><a class="link-light" href="#come-funziona">Come funziona <span>↓</span></a></div><div class="mini-notice">Servizio in fase di avvio: le videoconsulenze non sono ancora prenotabili. La prescrizione è decisa dal medico, solo per medicinali autorizzati e quando è appropriata.</div></div></section>
<section class="section-pad"><div class="wrap service-grid"><div><div class="section-label">01 / PER CHI È</div><h2>È pensata per te se…</h2><ul class="check-list">{li(c['for_whom'])}</ul></div><div><div class="section-label">02 / COSA FA IL MEDICO</div><h2>In videoconsulenza.</h2><ol class="numbered-list">{li(c['doctor'])}</ol><div class="fact-box exams-box"><span class="mini-label">ESAMI</span><p>{escape(c['exams'])}</p></div></div></div></section>
<section class="principles how-section section-pad" id="come-funziona"><div class="wrap"><div class="section-label">03 / COME FUNZIONA</div><h2>Un medico al tuo fianco,<br><em>passo dopo passo.</em></h2>{STEPS}</div></section>
<section class="section-pad"><div class="wrap service-grid"><div><div class="section-label">04 / COSA NON FACCIAMO</div><h2>I limiti, <em>chiari.</em></h2><p class="limits-text">{escape(c['limits'])}</p></div><div><div class="section-label">05 / DOMANDE FREQUENTI</div><h2>FAQ.</h2><div class="faq">{faq}</div></div></div></section>
<section class="related-section"><div class="wrap">{library_block}{articles_block}<div class="other-services"><span class="mini-label">ALTRE CONSULENZE</span>{others}</div></div></section>'''
    write(f'consulenze/{slug}/index.html', page(f'Consulenza {c["name"]}', re.sub('<[^>]+>', '', c['lede'])[:155], body))

# ------------------------------------------------------------------ articoli
type_chips = ''.join(f'<button type="button" class="filter{" active" if t == "Tutti" else ""}" data-type="{t}" aria-pressed="{"true" if t == "Tutti" else "false"}">{t}</button>' for t in ['Tutti', 'Guida', 'News'])
article_items = ''.join(article_card(a).replace('<a class="article-card"', '<a class="article-card" data-type="' + a['type'] + '"', 1) for a in ARTICLES)
articoli = f'''<section class="inner-hero"><div class="wrap"><div class="section-label light-text">ARTICOLI / GUIDE E NEWS</div><h1>Articoli <em>e news.</em></h1><p>Guide per orientarsi e notizie dal mondo delle terapie emergenti, spiegate senza hype.</p></div></section><section class="section-pad"><div class="wrap"><div class="filters article-filters" role="group" aria-label="Filtra per tipo">{type_chips}</div><div class="article-grid article-list">{article_items}</div></div></section>'''
write('articoli/index.html', page('Articoli e news su peptidi, GLP-1 e longevità', 'Guide e notizie su peptidi, farmaci GLP-1, ormoni e longevità: cosa dicono gli studi e cosa cambia per chi vive in Italia.', articoli))

for a in ARTICLES:
    rel = [p for s in a['related'] for p in DATA if p['slug'] == s]
    more = [b for b in ARTICLES if b is not a][:3]
    svc = a['service']
    cta = f'''<div class="aside-cta"><span>LA CONSULENZA</span><h3>Vuoi parlarne con un medico?</h3><p>La nostra rete di medici sta per avviare le videoconsulenze.</p><a class="btn btn-dark full" href="/consulenze/{SERVICE_SLUGS[svc]}/">Consulenza {escape(svc)} ↗</a></div>''' if svc else ''
    body = f'''<section class="inner-hero"><div class="wrap"><div class="breadcrumbs"><a href="/">Home</a> / <a href="/articoli/">Articoli</a></div><div class="section-label light-text">{escape(a['type'].upper())} · {it_date(a['date'])}</div><h1 class="article-title">{escape(a['title'])}</h1><p>{escape(a['description'])}</p></div></section><section class="section-pad"><div class="wrap profile-grid"><article class="article-body">{render_md(a['body'])}<div class="dosing-warning" role="note"><strong>Contenuto informativo.</strong> Questo articolo non sostituisce il parere di un medico. Bozza editoriale in attesa di revisione medico-scientifica.</div></article><aside class="profile-aside">{cta}<div class="fact-box"><span class="mini-label">REDAZIONE</span><strong>AHEAD</strong><hr><span class="mini-label">PUBBLICATO</span><strong>{it_date(a['date'])}</strong></div></aside></div></section>'''
    if rel:
        body += f'''<section class="related-section"><div class="wrap"><div class="section-row"><h2>Le schede citate.</h2><a class="underlined-link" href="/library/">Tutta la Library ↗</a></div><div class="card-grid related-grid">{''.join(card(p, True) for p in rel[:6])}</div></div></section>'''
    if more:
        body += f'''<section class="section-pad"><div class="wrap"><div class="section-row"><h2>Leggi anche.</h2><a class="underlined-link" href="/articoli/">Tutti gli articoli ↗</a></div><div class="article-grid">{''.join(article_card(b) for b in more)}</div></div></section>'''
    write(f'articoli/{a["slug"]}/index.html', page(a['title'], a['description'], body))

# ------------------------------------------------------------------ metodo
grid_legend = ''.join(f'<li><strong>{escape(label)}</strong></li>' for _, label in EVIDENCE_ROWS)
status_legend = ''.join(f'<li><span class="status {cls}"><i></i>{escape(label)}</span></li>' for label, cls in STATUS.values())
metodo = f'''<section class="inner-hero"><div class="wrap"><div class="section-label light-text">DOCUMENTAZIONE / METODO</div><h1>Il nostro <em>metodo.</em></h1><p>Come scegliamo le fonti, come classifichiamo le prove e cosa non troverai mai nelle nostre schede.</p></div></section><section class="section-pad"><div class="wrap privacy-content"><div class="review-notice"><strong>Stato attuale:</strong> le schede sono bozze editoriali. La revisione medico-scientifica indipendente non è ancora stata effettuata: il nome del revisore e la data di revisione compariranno su ogni scheda quando sarà completata.</div>
<h2>Da dove vengono le prove</h2><p>Ogni scheda indica per cinque livelli se esistono prove e di che qualità. I livelli non sono equivalenti: un risultato su cellule o su topi non dimostra un beneficio nelle persone.</p><ol class="method-list">{grid_legend}</ol><p>Per ogni livello usiamo tre gradi: <strong>Presenti</strong> (più studi coerenti), <strong>Limitate</strong> (pochi studi, piccoli, non replicati o con limiti importanti), <strong>Assenti</strong>. Per l’autorizzazione: <strong>Sì</strong> (medicinale autorizzato in UE), <strong>Parziale</strong> (autorizzato solo fuori UE o per un’altra indicazione), <strong>No</strong>.</p>
<h2>Stato regolatorio</h2><ul class="method-status">{status_legend}</ul><p>Lo stato si riferisce all’Unione europea, salvo diversa indicazione. Le decisioni di autorità extra-UE (per esempio FDA) sono riportate nel testo, ma non rendono un prodotto autorizzato in Italia.</p>
<h2>Gerarchia delle fonti</h2><p>Diamo priorità a: documenti delle autorità regolatorie (EMA, AIFA, FDA), studi clinici randomizzati pubblicati, revisioni sistematiche, studi osservazionali, studi su animali e in vitro. Comunicati aziendali e notizie sono indicati come tali e usati solo per aggiornamenti recenti non ancora pubblicati altrove.</p>
<h2>Revisione e aggiornamento</h2><p>Ogni scheda riporta la data dell’ultima verifica delle fonti. Le schede vengono ricontrollate almeno ogni sei mesi e ogni volta che cambia lo stato regolatorio. Prima della pubblicazione definitiva ogni scheda dovrà essere approvata da un medico revisore indipendente.</p>
<h2>Dosi e modalità d’uso</h2><p>Ogni scheda indica come la sostanza viene assunta e da dove provengono le dosi riportate: il foglietto illustrativo approvato in UE, un foglietto approvato fuori UE, gli studi clinici pubblicati, oppure nessuna fonte affidabile. Quando non esiste una dose studiata nell’uomo non riportiamo le quantità che circolano online. Le dosi sono informazioni, non indicazioni: ogni trattamento richiede una visita e l’approvazione di un medico.</p>
<h2>Cosa non facciamo</h2><p>Non indichiamo fornitori né prodotti “per uso di ricerca”. Non promettiamo prescrizioni: il medico prescrive solo medicinali autorizzati, quando li ritiene appropriati. Le schede non contengono link di affiliazione né contenuti sponsorizzati.</p>
<h2>Segnalare un errore</h2><p>Un indirizzo dedicato alle segnalazioni sarà pubblicato al lancio. Ogni correzione sostanziale sarà indicata nella scheda.</p></div></section>'''
write('metodo/index.html', page('Metodo editoriale', 'Come AHEAD seleziona le fonti, classifica le prove scientifiche e aggiorna le schede della Library.', metodo))

# ------------------------------------------------------------------ privacy
privacy = '''<section class="inner-hero"><div class="wrap"><div class="section-label light-text">DOCUMENTAZIONE</div><h1>Privacy <em>e trasparenza.</em></h1><p>Informativa provvisoria. Da completare prima di attivare la raccolta di indirizzi email.</p></div></section><section class="section-pad"><div class="wrap privacy-content"><div class="review-notice"><strong>Prima della pubblicazione:</strong> inserire titolare effettivo del trattamento, contatti, base giuridica, tempi di conservazione, fornitori, trasferimenti, diritti e istruzioni aggiornate. Non attivare il modulo in produzione senza l’informativa definitiva.</div><h2>Perché raccogliere email?</h2><p>L’unico scopo previsto è inviare aggiornamenti sul progetto a chi ne fa richiesta con consenso esplicito. Non chiediamo informazioni su diagnosi, terapie o condizioni di salute.</p><h2>Quali strumenti useremo?</h2><p>MailerLite per l’invio di email e, previo assetto privacy adeguato, uno strumento di analytics per contare gli interessi in forma aggregata. Le integrazioni non sono ancora attive nella demo.</p><h2>Ricerca nella Library</h2><p>La ricerca e i filtri funzionano interamente nel tuo browser: i termini cercati non vengono inviati a nessun server.</p><h2>Servizi sanitari</h2><p>Il progetto non è una struttura sanitaria operativa e non offre visite, prescrizioni o terapie.</p></div></section>'''
write('privacy/index.html', page('Privacy — informativa provvisoria', 'Informazioni sulla gestione dei dati per il progetto AHEAD.', privacy))

# ------------------------------------------------------------------ 404
not_found = '''<section class="inner-hero"><div class="wrap"><div class="section-label light-text">ERRORE 404</div><h1>Pagina <em>non trovata.</em></h1><p>La pagina che cerchi non esiste o è stata spostata.</p><div class="hero-actions"><a class="btn btn-light" href="/library/">Vai alla Library <span>↗</span></a><a class="link-light" href="/">Torna alla home</a></div></div></section>'''
write('404.html', page('Pagina non trovata', 'Pagina non trovata.', not_found))

write('favicon.svg', '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="15" fill="#111a1d"/><path d="M14 47 29 16h7l15 31h-9l-4-9H26l-4 9zm15-16h7l-4-10z" fill="#b8d9f5"/><circle cx="53" cy="13" r="5" fill="#e8e89a"/></svg>''')
print(f'Generate {N} schede + {len(ARTICLES)} articoli + {len(CONSULENZE)} consulenze + homepage + library + metodo + privacy + 404')
