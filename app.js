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
          && (selectedFilter === 'Tutti' || d.category === selectedFilter)
          && (!kind || d.kind === kind)
          && (!status || d.status === status);
        card.hidden = !show;
        if (show) count++;
      });
      document.querySelector('#results-count').textContent = count + (count === 1 ? ' risultato' : ' risultati');
      document.querySelector('#no-results').hidden = count > 0;
    };
    query.addEventListener('input', update);
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
      : 'Hai selezionato «Consulenza ' + service + '». Il servizio è in progettazione. Lascia la tua email per ricevere aggiornamenti generali sul progetto.';
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
