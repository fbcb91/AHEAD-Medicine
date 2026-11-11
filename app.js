(() => {
  'use strict';
  // Contatore aggregato (api/event.js): invia solo il nome dell'evento e l'area, nessun dato sulla persona.
  function count(e, v) {
    try { navigator.sendBeacon('/api/event', new Blob([JSON.stringify({ e, v })], { type: 'application/json' })); } catch (_) {}
  }
  const menuButton = document.querySelector('.mobile-menu');
  const nav = document.querySelector('.nav-links');
  if (menuButton && nav) {
    menuButton.addEventListener('click', () => {
      const expanded = menuButton.getAttribute('aria-expanded') === 'true';
      menuButton.setAttribute('aria-expanded', String(!expanded));
      nav.classList.toggle('is-open', !expanded);
    });
    nav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
      nav.classList.remove('is-open'); menuButton.setAttribute('aria-expanded','false');
    }));
  }

  // Search happens in the browser. No search terms are sent to a server.
  const query = document.querySelector('#peptide-search');
  if (query) {
    const cards = [...document.querySelectorAll('.library-results .peptide-card')];
    const filters = [...document.querySelectorAll('.filter')];
    const kindFilter = document.querySelector('#kind-filter');
    const statusFilter = document.querySelector('#status-filter');
    let selectedFilter = 'Tutti';
    const update = () => {
      let count = 0;
      const search = query.value.trim().toLocaleLowerCase('it');
      const kind = kindFilter?.value || '';
      const status = statusFilter?.value || '';
      cards.forEach(card => {
        const d = card.dataset;
        const show = (d.search || '').includes(search)
          && (selectedFilter === 'Tutti' || (d.categories || '').split('|').includes(selectedFilter))
          && (!kind || d.kind === kind)
          && (!status || d.status === status);
        card.hidden = !show;
        if (show) count++;
      });
      document.querySelector('#results-count').textContent = count + (count === 1 ? ' risultato' : ' risultati');
      document.querySelector('#no-results').hidden = count > 0;
    };
    query.addEventListener('input', update);
    // Supporta link del tipo /library/?q=bpc
    const initial = new URLSearchParams(location.search).get('q');
    if (initial) { query.value = initial; update(); }
    kindFilter?.addEventListener('change', update);
    statusFilter?.addEventListener('change', update);
    filters.forEach(f => f.addEventListener('click', () => {
      selectedFilter = f.dataset.filter;
      filters.forEach(el => {
        el.classList.toggle('active', el === f);
        el.setAttribute('aria-pressed', String(el === f));
      });
      update();
    }));
  }

  // Article list: filter by type (Guida / News).
  const typeFilters = [...document.querySelectorAll('.article-filters .filter')];
  typeFilters.forEach(f => f.addEventListener('click', () => {
    typeFilters.forEach(el => {
      el.classList.toggle('active', el === f);
      el.setAttribute('aria-pressed', String(el === f));
    });
    document.querySelectorAll('.article-list .article-card').forEach(card => {
      card.hidden = f.dataset.type !== 'Tutti' && card.dataset.type !== f.dataset.type;
    });
  }));

  // Questionario anonimo (/inizia/): un passo alla volta, invio a /api/survey.
  const survey = document.querySelector('#survey-form');
  if (survey) {
    const steps = [...survey.querySelectorAll('.survey-step')];
    const back = document.querySelector('#survey-back');
    const next = document.querySelector('#survey-next');
    const send = document.querySelector('#survey-submit');
    const error = document.querySelector('#survey-error');
    const bar = document.querySelector('#survey-bar');
    let current = 0;

    // Precompila l'area se si arriva da una consulenza: /inizia/?area=trt
    const area = new URLSearchParams(location.search).get('area');
    const preset = area && survey.querySelector(`input[name="aree"][data-slug="${CSS.escape(area)}"]`);
    if (preset) preset.checked = true;

    const show = (i, initial = false) => {
      steps.forEach((s, n) => { s.hidden = n !== i; });
      current = i;
      back.hidden = i === 0;
      next.hidden = i === steps.length - 1;
      send.hidden = i !== steps.length - 1;
      bar.style.width = ((i + 1) / steps.length * 100) + '%';
      error.textContent = '';
      if (initial) return;
      steps[i].querySelector('h2').focus({ preventScroll: true });
      survey.scrollIntoView({ block: 'start', behavior: 'smooth' });
    };
    const checkStep = i => {
      for (const block of steps[i].querySelectorAll('fieldset[data-q]')) {
        const chosen = block.querySelectorAll('input:checked').length;
        const max = Number(block.dataset.max || 0);
        if (block.dataset.required === 'true' && !chosen) {
          block.scrollIntoView({ block: 'center', behavior: 'smooth' });
          return 'Seleziona almeno una risposta per continuare: «' + block.querySelector('legend').firstChild.textContent.trim() + '».';
        }
        if (max && chosen > max) return 'Puoi scegliere al massimo ' + max + ' opzioni.';
      }
      return '';
    };
    // Limite di scelte: disattiva le altre opzioni quando si raggiunge il massimo.
    survey.querySelectorAll('fieldset[data-max]').forEach(block => block.addEventListener('change', () => {
      const max = Number(block.dataset.max);
      const boxes = [...block.querySelectorAll('input')];
      const full = boxes.filter(b => b.checked).length >= max;
      boxes.forEach(b => { if (!b.checked) b.disabled = full; });
    }));
    survey.addEventListener('change', () => { error.textContent = ''; });
    next.addEventListener('click', () => {
      const problem = checkStep(current);
      if (problem) { error.textContent = problem; return; }
      show(current + 1);
    });
    back.addEventListener('click', () => show(current - 1));
    survey.addEventListener('submit', async event => {
      event.preventDefault();
      const problem = checkStep(current);
      if (problem) { error.textContent = problem; return; }
      const data = {};
      new FormData(survey).forEach((value, key) => {
        const multi = survey.querySelector(`input[type="checkbox"][name="${key}"]`);
        if (multi) (data[key] = data[key] || []).push(value);
        else data[key] = value;
      });
      send.disabled = true;
      error.textContent = '';
      try {
        const res = await fetch('/api/survey', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        let body = {};
        try { body = await res.json(); } catch (_) {}
        if (!res.ok) throw new Error(body.error || 'Impossibile inviare le risposte, riprova più tardi.');
        (data.aree || []).forEach(a => count('questionario', a));
        survey.hidden = true;
        document.querySelector('.survey-progress').hidden = true;
        const done = document.querySelector('#survey-done');
        done.hidden = false;
        done.focus();
      } catch (err) {
        error.textContent = err.message;
      } finally {
        send.disabled = false;
      }
    });
    show(0, true);
  }

  // Click sui pulsanti che portano al questionario: conteggio aggregato per area.
  document.querySelectorAll('.start-link').forEach(link => link.addEventListener('click', () => {
    count('interesse', link.dataset.service || 'generale');
  }));

  const modal = document.querySelector('#interest-modal');
  const form = document.querySelector('#interest-form');
  const message = document.querySelector('#form-message');
  const submit = document.querySelector('#form-submit');
  let previousFocus = null;
  // Event analytics are anonymous by design: only category, no email or medical history.
  function trackInterest(service) {
    count('interesse', service);
  }
  function openModal(service) {
    previousFocus = document.activeElement;
    message.textContent = '';
    message.className = 'form-message';
    form.hidden = false;
    document.querySelector('#form-success').hidden = true;
    document.querySelector('#modal-description').textContent = service === 'generale'
      ? 'Lascia la tua email per ricevere aggiornamenti sul progetto.'
      : 'Hai selezionato «Consulenza ' + service + '». Le videoconsulenze sono in fase di avvio. Lascia la tua email per ricevere aggiornamenti generali sul lancio.';
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
    modal.querySelector('#interest-email').focus();
    trackInterest(service);
  }
  function closeModal() {
    modal.hidden = true;
    document.body.style.overflow = '';
    if (previousFocus) previousFocus.focus();
  }
  document.querySelectorAll('.interest-trigger').forEach(button => button.addEventListener('click', () => openModal(button.dataset.service || 'generale')));
  modal?.querySelector('[data-close-modal]')?.addEventListener('click', closeModal);
  modal?.addEventListener('click', event => { if (event.target === modal) closeModal(); });
  document.addEventListener('keydown', event => {
    if (!modal || modal.hidden) return;
    if (event.key === 'Escape') { closeModal(); return; }
    // Keep keyboard focus inside the dialog while it is open.
    if (event.key === 'Tab') {
      const focusable = [...modal.querySelectorAll('a[href], button:not([disabled]), input:not([tabindex="-1"])')].filter(el => el.offsetParent !== null);
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  // Non fingere un'iscrizione riuscita: il messaggio dipende dalla risposta del server.
  form?.addEventListener('submit', async event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    submit.disabled = true;
    submit.textContent = 'Invio in corso…';
    message.textContent = '';
    message.className = 'form-message';
    try {
      const res = await fetch('/api/interest', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
          email: document.querySelector('#interest-email').value.trim(),
          consent: document.querySelector('#interest-consent').checked,
          website: document.querySelector('#interest-website')?.value || ''
        })
      });
      let data = {};
      try { data = await res.json(); } catch (_) {}
      if (!res.ok) throw new Error(data.error || 'Impossibile inviare la richiesta, riprova più tardi.');
      const success = document.querySelector('#form-success');
      success.querySelector('p').textContent = data.mode === 'mailerlite'
        ? 'Ti abbiamo inviato un’email: clicca sul link per confermare l’iscrizione. Se non la trovi, controlla nello spam.'
        : 'Ti scriveremo quando apriremo le prenotazioni delle videoconsulenze. Puoi cancellarti in qualsiasi momento.';
      form.reset();
      form.hidden = true;
      success.hidden = false;
      success.focus();
    } catch (error) {
      message.textContent = error.message || 'Impossibile inviare la richiesta, riprova più tardi.';
      message.className = 'form-message is-error';
    } finally {
      submit.disabled = false;
      submit.innerHTML = 'Ricevi aggiornamenti <span>↗</span>';
    }
  });
})();

// Effetti visivi: solo decorazione, nessun dato inviato. Rispettano prefers-reduced-motion.
(() => {
  'use strict';
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  // Header compatto e barra di avanzamento
  const header = document.querySelector('.site-header');
  const bar = document.querySelector('.scroll-progress');
  let ticking = false;
  const onScroll = () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      const y = window.scrollY;
      header?.classList.toggle('is-scrolled', y > 40);
      const max = document.documentElement.scrollHeight - innerHeight;
      bar?.style.setProperty('--progress', max > 0 ? Math.min(1, y / max).toFixed(4) : '0');
      ticking = false;
    });
  };
  addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // Comparsa allo scroll, con ritardo a cascata dentro le griglie
  if (!reduce && 'IntersectionObserver' in window) {
    const sel = ['main section:not(.hero):not(.inner-hero):not(.marquee) .section-label', 'main section:not(.hero):not(.inner-hero) h2',
      '.section-subtitle', '.service-card', '.peptide-card', '.article-card', '.principles-grid > div', '.library-bottom',
      '.signup-panel', '.area-tile', '.services-foot', '.signup-grid > div > p', '.fact-box', '.aside-cta'].join(',');
    const els = [...document.querySelectorAll(sel)].filter(el => el.getBoundingClientRect().top > innerHeight * 0.9);
    const io = new IntersectionObserver(entries => entries.forEach(en => {
      if (!en.isIntersecting) return;
      en.target.classList.add('is-in');
      io.unobserve(en.target);
    }), { rootMargin: '0px 0px -8% 0px' });
    els.forEach(el => {
      const parent = el.parentElement;
      const siblings = parent ? [...parent.children].filter(c => els.includes(c)) : [];
      const i = Math.max(0, siblings.indexOf(el));
      el.style.setProperty('--d', (Math.min(i, 7) * 0.08) + 's');
      el.classList.add('reveal');
      io.observe(el);
    });
    document.querySelectorAll('.steps-grid').forEach(g => {
      [...g.children].forEach((c, i) => c.style.setProperty('--d', (i * 0.25) + 's'));
      io.observe(g);
    });
  } else {
    document.documentElement.classList.add('no-reveal');
  }

  // Numeri che contano fino al valore finale (il testo nell'HTML resta quello vero)
  if (!reduce) {
    document.querySelectorAll('.hero-stats-row strong').forEach((el, k) => {
      const m = el.textContent.trim().match(/^(\d+)(.*)$/);
      if (!m) return;
      const end = +m[1], rest = m[2], t0 = performance.now() + 300 + k * 120, dur = 1400;
      const step = now => {
        const p = Math.min(1, Math.max(0, (now - t0) / dur));
        el.textContent = Math.round(end * (1 - Math.pow(1 - p, 4))) + rest;
        if (p < 1) requestAnimationFrame(step);
      };
      el.textContent = '0' + rest;
      requestAnimationFrame(step);
    });
  }

  // Luce che segue il cursore sulle card
  if (finePointer) {
    document.addEventListener('pointermove', e => {
      const card = e.target.closest?.('.service-card, .peptide-card, .article-card, .area-tile');
      if (!card) return;
      const r = card.getBoundingClientRect();
      card.style.setProperty('--mx', (e.clientX - r.left) + 'px');
      card.style.setProperty('--my', (e.clientY - r.top) + 'px');
    }, { passive: true });
  }

  // Campo molecolare animato nelle intestazioni scure
  const heroes = [...document.querySelectorAll('.hero, .inner-hero:not(.has-photo)')];
  if (reduce || !heroes.length || !window.HTMLCanvasElement) return;
  heroes.forEach(hero => {
    const canvas = document.createElement('canvas');
    canvas.className = 'hero-canvas';
    canvas.setAttribute('aria-hidden', 'true');
    const spot = document.createElement('div');
    spot.className = 'hero-spot';
    spot.setAttribute('aria-hidden', 'true');
    hero.prepend(canvas, spot);
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const isHome = hero.classList.contains('hero');
    const colors = ['137,185,209', '190,215,237', '224,232,167'];
    let w = 0, h = 0, dpr = 1, nodes = [], visible = true, raf = 0;
    const mouse = { x: -9999, y: -9999 };

    const resize = () => {
      const r = hero.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = r.width; h = r.height;
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const target = Math.round(Math.min(isHome ? 95 : 55, (w * h) / (isHome ? 14000 : 20000)));
      nodes = Array.from({ length: target }, () => ({
        x: Math.random() * w, y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.25, vy: (Math.random() - 0.5) * 0.25,
        r: Math.random() * 1.6 + 0.6, c: colors[Math.random() < 0.15 ? 2 : Math.random() < 0.5 ? 1 : 0],
        p: Math.random() * Math.PI * 2,
      }));
    };

    const LINK = 130;
    const draw = t => {
      ctx.clearRect(0, 0, w, h);
      for (const n of nodes) {
        const dx = mouse.x - n.x, dy = mouse.y - n.y, d2 = dx * dx + dy * dy;
        if (d2 < 40000) { n.vx += dx * 0.000025; n.vy += dy * 0.000025; }
        n.vx *= 0.995; n.vy *= 0.995;
        n.vx += (Math.random() - 0.5) * 0.008; n.vy += (Math.random() - 0.5) * 0.008;
        n.x += n.vx; n.y += n.vy;
        if (n.x < -20) n.x = w + 20; else if (n.x > w + 20) n.x = -20;
        if (n.y < -20) n.y = h + 20; else if (n.y > h + 20) n.y = -20;
      }
      ctx.lineWidth = 0.7;
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j], dx = a.x - b.x, dy = a.y - b.y, d = Math.hypot(dx, dy);
          if (d < LINK) {
            ctx.strokeStyle = `rgba(${a.c},${(1 - d / LINK) * 0.22})`;
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
          }
        }
        const md = Math.hypot(mouse.x - a.x, mouse.y - a.y);
        if (md < 170) {
          ctx.strokeStyle = `rgba(224,232,167,${(1 - md / 170) * 0.35})`;
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(mouse.x, mouse.y); ctx.stroke();
        }
      }
      for (const n of nodes) {
        const tw = 0.55 + 0.45 * Math.sin(t / 900 + n.p);
        ctx.fillStyle = `rgba(${n.c},${0.35 + tw * 0.5})`;
        ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2); ctx.fill();
        if (n.r > 1.8) {
          ctx.fillStyle = `rgba(${n.c},${0.06 * tw})`;
          ctx.beginPath(); ctx.arc(n.x, n.y, n.r * 6, 0, Math.PI * 2); ctx.fill();
        }
      }
    };
    const loop = t => { draw(t); raf = visible && !document.hidden ? requestAnimationFrame(loop) : 0; };
    const start = () => { if (!raf && visible && !document.hidden) raf = requestAnimationFrame(loop); };

    resize();
    let rt;
    addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(resize, 150); }, { passive: true });
    new IntersectionObserver(([en]) => { visible = en.isIntersecting; start(); }).observe(hero);
    document.addEventListener('visibilitychange', start);
    requestAnimationFrame(() => canvas.classList.add('is-ready'));
    start();

    if (finePointer) {
      const layers = isHome ? [...hero.querySelectorAll('.molecule-core, .core-halo, .orbit, .visual-code')] : [];
      layers.forEach(l => l.classList.add('parallax'));
      hero.addEventListener('pointermove', e => {
        const r = hero.getBoundingClientRect();
        mouse.x = e.clientX - r.left; mouse.y = e.clientY - r.top;
        spot.style.setProperty('--sx', mouse.x + 'px');
        spot.style.setProperty('--sy', mouse.y + 'px');
        const px = (mouse.x / r.width - 0.5), py = (mouse.y / r.height - 0.5);
        layers.forEach((l, i) => {
          const depth = l.classList.contains('molecule-core') ? 28 : l.classList.contains('visual-code') ? -14 : 10 + i * 4;
          l.style.translate = `${(px * depth).toFixed(1)}px ${(py * depth).toFixed(1)}px`;
        });
      }, { passive: true });
      hero.addEventListener('pointerleave', () => { mouse.x = mouse.y = -9999; layers.forEach(l => { l.style.translate = ''; }); });
    }
  });
})();
