# AHEAD Medicine — istruzioni per Codex

## Scopo
Sito italiano di validazione del mercato per un futuro servizio medico sulle terapie emergenti. Il brand AHEAD è provvisorio. Il primo MVP include homepage, quattro consulenze come **servizi futuri senza prezzi**, directory di dieci peptidi, ricerca/filtri e raccolta di email attivabile via MailerLite.

## Vincoli importanti
- Il servizio è una rete di medici esperti: la persona racconta il suo obiettivo, le vengono proposti uno o più medici adatti, sceglie e prenota una videoconsulenza; il medico la segue nel tempo e, se lo ritiene appropriato, prescrive. Fase attuale: validazione dell'interesse. Finché il servizio non è prenotabile non presentarlo come già attivo.
- La prescrizione è sempre una decisione del medico e riguarda solo medicinali autorizzati. Non promettere prescrizioni, accesso a farmaci sperimentali o reperibilità di peptidi non autorizzati; non indicare fornitori.
- Sezione dosi delle schede (`dosing`): riportare solo dosi da foglietto/RCP approvato (UE o extra-UE) o da studi clinici pubblicati, sempre con la fonte (`basis`). Se non esiste una dose studiata nell'uomo (`basis: nessuna`) non riportare le quantità che circolano online. Mai protocolli, cicli o "stack" fai-da-te.
- Ogni nuova scheda medico-scientifica deve distinguere **studi in vitro, animali, osservazionali, RCT, e medicinali autorizzati**. Richiedere controllo medico indipendente prima della pubblicazione.
- Non associare indirizzi email a categorie di interesse per patologie o sostanze. Misurare click di interesse in aggregato, non per persona. Mai raccogliere anamnesi in un form marketing.
- Preferire modifiche semplici e mantenere la struttura statica veloce, indicizzabile e accessibile.
- Indicizzazione attiva (`INDEXABLE = True` in `build.py`) per decisione del titolare, prima della revisione medica: mantenere le schede in stato "bozza" visibile finché la revisione non è completata. `INDEXABLE = False` rimette noindex ovunque.
- SEO: ogni pagina passa da `page()` con path canonico; non scrivere HTML a mano fuori da `build.py`. Titoli ≤ ~70 caratteri, meta description ≤ ~158 (il build avvisa).

## Files
- `data/articoli/<slug>.md` articoli (guide e news) in Markdown con front-matter, validati da `build.py`.
- `data/schede/<slug>.json` è la sorgente unica delle schede della Library (una per sostanza). Lo schema (stato regolatorio, griglia delle prove, fonti, revisione) è validato da `build.py`.
- `build.py` genera tutte le pagine HTML dai JSON. Modificare questo per pagine/struttura; dopo ogni modifica rilanciare `python3 build.py` e committare anche l'HTML generato (la CI lo verifica).
- `scripts/og-images.js` genera le immagini social in `og/` (Playwright): `node scripts/og-images.js && python3 build.py` dopo aver aggiunto pagine.
- `sitemap.xml`, `robots.txt` e `og/pages.json` sono generati da `build.py`.
- `styles.css` per estetica responsive.
- `app.js` ricerca / filtri / CTA / modulo.
- `api/interest.js` endpoint Vercel da attivare via variabili d'ambiente (honeypot e rate limit di base inclusi).
- `vercel.json` header di sicurezza, inclusa la CSP: aggiornarla se si aggiungono script o domini esterni (es. analytics).

## Prossime funzioni desiderate
- Sostituire build.py con template modulari o Astro se il catalogo cresce molto.
- Dominio definitivo: cambiare `SITE_URL` in `build.py`, rigenerare, aggiungere redirect 301 dal dominio vercel.app e reinviare la sitemap in Search Console.
- Definire revisore scientifico, bibliografia per scheda e date di verifica; aggiungere studi originali con grading standard.
- Collegare privacy policy definitiva e MailerLite double opt-in.
- Installare analytics privacy-friendly con eventi aggregati per servizio, senza dati sensibili.
