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
    let selectedFilter = 'Tutti';
    const update = () => {
      let count = 0;
      const search = query.value.trim().toLocaleLowerCase('it');
      cards.forEach(card => {
        const title = card.querySelector('h3')?.textContent?.toLocaleLowerCase('it') || '';
        const category = card.querySelector('.pc-tag')?.textContent?.trim() || '';
        const show = title.includes(search) && (selectedFilter === 'Tutti' || category === selectedFilter);
        card.hidden = !show;
        if (show) count++;
      });
      document.querySelector('#results-count').textContent = count + (count === 1 ? ' risultato' : ' risultati');
      document.querySelector('#no-results').hidden = count > 0;
    };
    query.addEventListener('input', update);
    filters.forEach(f => f.addEventListener('click', () => {
      selectedFilter = f.dataset.filter;
      filters.forEach(el => el.classList.toggle('active', el === f));
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
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && modal && !modal.hidden) closeModal(); });
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
        body: JSON.stringify({ email: document.querySelector('#interest-email').value.trim(), consent: document.querySelector('#interest-consent').checked })
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
