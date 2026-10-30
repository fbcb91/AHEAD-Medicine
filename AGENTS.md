# AHEAD Medicine — istruzioni per Codex

## Scopo
Sito italiano di validazione del mercato per un futuro servizio medico sulle terapie emergenti. Il brand AHEAD è provvisorio. Il primo MVP include homepage, quattro consulenze come **servizi futuri senza prezzi**, directory di dieci peptidi, ricerca/filtri e raccolta di email attivabile via MailerLite.

## Vincoli importanti
- Non rappresentare l'attività come una clinica operativa. Non affermare che esista un team medico finché non è stato effettivamente ingaggiato.
- Non promettere prescrizioni, accesso a farmaci sperimentali, protocolli di somministrazione, dosaggi o reperibilità di peptidi non autorizzati.
- Ogni nuova scheda medico-scientifica deve distinguere **studi in vitro, animali, osservazionali, RCT, e medicinali autorizzati**. Richiedere controllo medico indipendente prima della pubblicazione.
- Non associare indirizzi email a categorie di interesse per patologie o sostanze. Misurare click di interesse in aggregato, non per persona. Mai raccogliere anamnesi in un form marketing.
- Preferire modifiche semplici e mantenere la struttura statica veloce, indicizzabile e accessibile.
- Prima della pubblicazione rimuovere meta noindex **soltanto** dopo revisione scientifica e validazione privacy/legale.

## Files
- `data/schede/<slug>.json` è la sorgente unica delle schede della Library (una per sostanza). Lo schema (stato regolatorio, griglia delle prove, fonti, revisione) è validato da `build.py`.
- `build.py` genera tutte le pagine HTML dai JSON. Modificare questo per pagine/struttura; dopo ogni modifica rilanciare `python3 build.py` e committare anche l'HTML generato (la CI lo verifica).
- `styles.css` per estetica responsive.
- `app.js` ricerca / filtri / CTA / modulo.
- `api/interest.js` endpoint Vercel da attivare via variabili d'ambiente (honeypot e rate limit di base inclusi).
- `vercel.json` header di sicurezza, inclusa la CSP: aggiornarla se si aggiungono script o domini esterni (es. analytics).

## Prossime funzioni desiderate
- Sostituire build.py con template modulari o Astro se il catalogo cresce molto.
- Aggiungere schema.org e sitemap solo dopo dominio definitivo e revisione scientifica.
- Definire revisore scientifico, bibliografia per scheda e date di verifica; aggiungere studi originali con grading standard.
- Collegare privacy policy definitiva e MailerLite double opt-in.
- Installare analytics privacy-friendly con eventi aggregati per servizio, senza dati sensibili.
