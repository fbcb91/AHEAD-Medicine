(() => {
  'use strict';
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
        if (typeof window.plausible === 'function') {
          (data.aree || []).forEach(a => window.plausible('Questionario completato', { props: { area: a } }));
        }
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
    if (typeof window.plausible === 'function') {
      window.plausible('Consulenza: interesse', { props: { servizio: link.dataset.service || 'generale' } });
    }
  }));

  const modal = document.querySelector('#interest-modal');
  const form = document.querySelector('#interest-form');
  const message = document.querySelector('#form-message');
  const submit = document.querySelector('#form-submit');
  let previousFocus = null;
  // Event analytics are anonymous by design: only category, no email or medical history.
  function trackInterest(service) {
    if (typeof window.plausible === 'function') {
      window.plausible('Consulenza: interesse', { props: { servizio: service } });
    }
  }
  function openModal(service) {
    previousFocus = document.activeElement;
    message.textContent = '';
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
  // Do not silently pretend signups worked. The API returns 503 until MailerLite is configured.
  form?.addEventListener('submit', async event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    submit.disabled = true;
    submit.textContent = 'Invio in corso…';
    message.textContent = '';
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
      if (!res.ok) throw new Error(data.error || 'Modulo non ancora attivo.');
      message.textContent = 'Richiesta ricevuta. Controlla la posta per eventuali passaggi di conferma.';
      form.reset();
    } catch (error) {
      message.textContent = error.message || 'Impossibile inviare la richiesta, riprova più tardi.';
    } finally {
      submit.disabled = false;
      submit.innerHTML = 'Ricevi aggiornamenti <span>↗</span>';
    }
  });
})();
