# Areyon Med — istruzioni per Codex

## Scopo
Sito italiano di validazione del mercato per un futuro servizio medico sulle terapie emergenti. Il brand è **Areyon Med** ("Emerging Medicine", payoff "Eccellenza, nel tempo."): il nome unisce *areté* (eccellenza) e *aion* (il tempo della vita) ed è un’interpretazione creativa, non una parola greca autentica: non presentarlo come tale. Il primo MVP include homepage, quattro consulenze come **servizi futuri senza prezzi**, directory di dieci peptidi, ricerca/filtri e raccolta di email attivabile via MailerLite.

## Vincoli importanti
- Il servizio è una rete di medici esperti: la persona racconta il suo obiettivo, le vengono proposti uno o più medici adatti, sceglie e prenota una videoconsulenza; il medico la segue nel tempo e, se lo ritiene appropriato, prescrive. Fase attuale: validazione dell'interesse. Finché il servizio non è prenotabile non presentarlo come già attivo.
- La prescrizione è sempre una decisione del medico e riguarda solo medicinali autorizzati. Non promettere prescrizioni, accesso a farmaci sperimentali o reperibilità di peptidi non autorizzati; non indicare fornitori.
- Sezione dosi delle schede (`dosing`): riportare solo dosi da foglietto/RCP approvato (UE o extra-UE) o da studi clinici pubblicati, sempre con la fonte (`basis`). Se non esiste una dose studiata nell'uomo (`basis: nessuna`) non riportare le quantità che circolano online. Mai protocolli, cicli o "stack" fai-da-te.
- Ogni nuova scheda medico-scientifica deve distinguere **studi in vitro, animali, osservazionali, RCT, e medicinali autorizzati**. Le schede e gli articoli esistenti sono revisionati dai medici di Areyon Med (`review.status: revisionata`, `review.reviewed`; per gli articoli `reviewed:` nel front-matter). Un contenuto nuovo o modificato in modo sostanziale resta `bozza` (senza `reviewed`) finché i medici non lo rivedono. Non indicare nomi dei medici revisori.
- Non associare indirizzi email a categorie di interesse per patologie o sostanze. Misurare click di interesse in aggregato, non per persona. Mai raccogliere anamnesi in un form marketing.
- Il questionario `/inizia/` è **anonimo**: mai aggiungere nome, email, telefono o altri identificativi, né salvare IP o user agent, né collegarlo all'iscrizione email. Un modulo identificato con dati sanitari richiede prima titolare del trattamento, informativa definitiva, consenso esplicito (art. 9 GDPR) e un archivio adatto: non usare MailerLite per questi dati.
- Preferire modifiche semplici e mantenere la struttura statica veloce, indicizzabile e accessibile.
- Indicizzazione attiva (`INDEXABLE = True` in `build.py`). `INDEXABLE = False` rimette noindex ovunque.
- Titolare indicato come "Areyon Med" (società non ancora costituita). `CONTACT_EMAIL` in `build.py` alimenta contatti, privacy e note legali.
- SEO: ogni pagina passa da `page()` con path canonico; non scrivere HTML a mano fuori da `build.py`. Titoli ≤ ~70 caratteri, meta description ≤ ~158 (il build avvisa).

## Files
- `data/articoli/<slug>.md` articoli (guide e news) in Markdown con front-matter, validati da `build.py`.
- `data/schede/<slug>.json` è la sorgente unica delle schede della Library (una per sostanza). Lo schema (stato regolatorio, griglia delle prove, fonti, revisione) è validato da `build.py`.
- `build.py` genera tutte le pagine HTML dai JSON. Modificare questo per pagine/struttura; dopo ogni modifica rilanciare `python3 build.py` e committare anche l'HTML generato (la CI lo verifica).
- Foto delle intestazioni: `img/schede/<slug>.*`, `img/aree/<area>.*`, `img/consulenze/<slug>.*`, `img/articoli/<slug>.*`, `img/pagine/<library|consulenze|metodo>.*` (elenco dei nomi in `img/LEGGIMI.md`, generato). `build.py` le converte in WebP in `media/` (serve Pillow) e le mette a tutta larghezza dietro il titolo. Usare solo immagini con licenza adatta.
- `.github/workflows/build.yml`: su `main` rigenera il sito e committa le pagine aggiornate (così le foto caricate da GitHub vengono pubblicate); sulle PR verifica che l'HTML sia aggiornato.
- `scripts/og-images.js` genera le immagini social in `og/` (Playwright): `node scripts/og-images.js && python3 build.py` dopo aver aggiunto pagine.
- `sitemap.xml`, `robots.txt` e `og/pages.json` sono generati da `build.py`.
- `fonts/` contiene i font del sito (Cinzel per il marchio, DM Sans e Manrope per i testi), ospitati in locale: niente Google Fonts (privacy e CSP).
- `styles.css` per estetica responsive.
- `app.js` ricerca / filtri / CTA / modulo.
- `SURVEY` in `build.py` definisce le domande del questionario e genera `inizia/index.html` e `api/_survey-schema.js` (non modificarlo a mano).
- `api/survey.js` salva le risposte su Redis (Upstash); `api/survey-export.js` le esporta in CSV con `SURVEY_ADMIN_KEY`.
- `api/event.js` conta in forma aggregata clic di interesse e questionari per area (nessun dato sulla persona); `api/stats.js` mostra i totali con `SURVEY_ADMIN_KEY`. Statistiche di visita: Vercel Web Analytics (senza cookie), da attivare nel pannello Vercel.
- `api/interest.js` iscrizione email: con `MAILERLITE_API_TOKEN` e `MAILERLITE_GROUP_ID` usa MailerLite, altrimenti salva nella lista d'attesa su Upstash (`waitlist:emails`, solo email e data del consenso), esportabile in CSV con `/api/waitlist-export?key=` (`SURVEY_ADMIN_KEY`). Honeypot e rate limit inclusi.
- La CSP vieta gli stili inline: niente attributi `style="…"` nell'HTML. Per il colore d'area usare le classi `cat-<slug>` di `styles.css` (da aggiornare se si aggiunge un'area a `CAT_COLORS`).
- `vercel.json` header di sicurezza, inclusa la CSP: aggiornarla se si aggiungono script o domini esterni (es. analytics).

## Prossime funzioni desiderate
- Sostituire build.py con template modulari o Astro se il catalogo cresce molto.
- Dominio definitivo: cambiare `SITE_URL` in `build.py`, rigenerare, aggiungere redirect 301 dal dominio vercel.app e reinviare la sitemap in Search Console.
- Definire revisore scientifico, bibliografia per scheda e date di verifica; aggiungere studi originali con grading standard.
- Attivare MailerLite (double opt-in) e importare la lista d'attesa.
