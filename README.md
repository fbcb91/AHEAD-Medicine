# AHEAD Medicine — sito demo deploy-ready

> **AHEAD è un nome provvisorio. Il sito è un prototipo**, non una clinica e non offre servizi sanitari. Le schede sono bozze da sottoporre a revisione clinico-scientifica prima della messa online definitiva.

## Cosa contiene
- Homepage premium e responsive
- Library: `/library/` con ricerca (nome, area, sinonimi) e filtri per area, tipo e stato regolatorio
- 46 schede separate: peptidi in `/peptidi/<slug>/`, altre sostanze (testosterone, rapamicina, metformina…) in `/sostanze/<slug>/`
- Per ogni scheda: griglia delle prove (in vitro, animali, osservazionali, RCT, autorizzazione), stato regolatorio, fonti tipizzate, data di verifica e stato della revisione medica
- Sezione "Come si assume": via di somministrazione e dosi con la loro fonte (RCP UE, foglietto extra-UE, studi clinici, oppure nessuna dose validata)
- Sezione Articoli `/articoli/` (guide e news) generata da `data/articoli/*.md`
- Pagina `/metodo/` con il metodo editoriale e pagina 404
- 8 consulenze **senza prezzi** (Peptidi, TRT, GLP-1, Longevity & Performance, Capelli, Salute sessuale, Menopausa, Recupero e sport), ognuna con la sua pagina in `/consulenze/<slug>/` (per chi è, cosa fa il medico, esami, limiti, FAQ, schede correlate)
- Modale raccolta email via funzione Vercel + MailerLite; disattivata finché non configurata
- Privacy provvisoria da sostituire prima di raccogliere dati

## Anteprima locale
Per vedere il sito:
```bash
python3 -m http.server 8000
```
Apri `http://localhost:8000/` nel browser.

> Il modulo non funziona con `http.server`: per questo serve Vercel e un account MailerLite configurato.

## Pubblicazione su GitHub + Vercel
1. Crea un repository privato GitHub (es. `ahead-medicine`) e carica questi file.
2. Su Vercel crea un progetto importando il repository GitHub.
3. Framework: **Other**; Build command: **vuoto**; Output directory: **vuoto** (serve root); deploy.
4. Imposta prima dominio e privacy definitiva. Nella demo tutte le pagine HTML includono meta `noindex,nofollow`, perché i contenuti clinici non sono ancora revisionati.
5. Quando vuoi attivare la raccolta email crea una lista/gruppo dedicato in MailerLite e configura su Vercel **Environment Variables**:
   - `MAILERLITE_API_TOKEN` = token API segreto, **mai nel browser**.
   - `MAILERLITE_GROUP_ID` = ID gruppo MailerLite per contatti generici.
   - `SITE_FORMS_ENABLED` = `true` **solo dopo** privacy definitiva, verifica GDPR, consenso e conferma iscrizione.
6. Verifica con test end-to-end, preferendo il **double opt-in** configurato con MailerLite.

API MailerLite: https://developers.mailerlite.com/api/subscribers

## Questionario "Trova il tuo medico" (`/inizia/`)
Questionario anonimo in 7 passi: aree, obiettivi, situazione di partenza, sostanze di interesse, fascia d'età e sesso, aspettative sul servizio (tempi, budget, abbonamento, lingua, canale) e una nota libera facoltativa. Tutti i pulsanti "Trova il tuo medico" del sito portano qui, con l'area già selezionata (`/inizia/?area=trt`).

Non raccoglie nome, email o telefono e non salva IP: le risposte servono a capire la domanda in forma aggregata. L'iscrizione email resta separata e non è collegata alle risposte.

Per attivarlo su Vercel:
1. **Storage → Marketplace → Upstash for Redis** (piano gratuito) e collegalo al progetto: Vercel aggiunge da solo le variabili di connessione (`KV_REST_API_URL` e `KV_REST_API_TOKEN`, anche con un prefisso personalizzato).
2. Aggiungi la variabile `SURVEY_ADMIN_KEY` con una chiave lunga e casuale (almeno 16 caratteri).
3. Rifai il deploy.

Per scaricare le risposte in CSV (si apre con Excel o Google Sheets): `https://<sito>/api/survey-export?key=<SURVEY_ADMIN_KEY>`.
Finché lo storage non è configurato il questionario risponde "non ancora attivo".

Le domande si modificano nella lista `SURVEY` in `build.py`; il build rigenera la pagina e lo schema di validazione del server.

## SEO
Tutto è generato da `build.py`:
- `<title>`, meta description, canonical, Open Graph e Twitter card su ogni pagina; `robots` index/follow (`INDEXABLE` in `build.py`)
- Dati strutturati JSON-LD: Organization e WebSite (home), MedicalWebPage + FAQPage (schede e consulenze), Article/NewsArticle (articoli), CollectionPage + ItemList (Library, aree, elenchi), BreadcrumbList ovunque
- `sitemap.xml` e `robots.txt`
- Pagine di atterraggio per area (`/library/<area>/`), per tipo (`/peptidi/`, `/sostanze/`) e per consulenze (`/consulenze/`)
- Titoli H2 delle schede formulati sulle ricerche reali ("a cosa serve", "effetti collaterali", "dosi", "è legale in Italia")
- Immagini social 1200×630 per ogni pagina in `og/`: dopo aver aggiunto schede, articoli o consulenze lancia `node scripts/og-images.js && python3 build.py`

Per cambiare dominio modifica `SITE_URL` in `build.py`. Dopo la pubblicazione: verifica il sito in Google Search Console (metodo "prefisso URL"; se scegli il meta tag inserisci il codice in `GSC_VERIFICATION`) e invia `sitemap.xml`.

## Misura interesse
Le CTA lanciano un evento aggregato `Consulenza: interesse` con proprietà `servizio`, **senza l'email**. L'evento viene registrato solo se è stato collegato uno strumento compatibile con la funzione `window.plausible` e solo nel rispetto delle regole privacy e cookie. Collega la piattaforma analytics configurandone la libreria di tracciamento: non è inclusa nella demo.

La mail del visitatore non viene associata alla consulenza selezionata. Questo evita inferenze su informazioni sanitarie nella lista marketing.

## Aggiungere articoli
Ogni articolo è un file Markdown in `data/articoli/<slug>.md` con un front-matter:

```
---
title: Titolo dell'articolo
type: Guida            # oppure News
date: 2026-10-30
description: Una o due frasi, usate anche come meta description.
related: bpc-157, tb-500   # slug di schede della Library (facoltativo)
service: Peptidi           # consulenza collegata (facoltativo)
---
```

Il corpo supporta titoli `##` e `###`, elenchi con `- `, **grassetto** e [link](/library/). Poi lancia `python3 build.py`.

## Aggiornare o aggiungere schede
Ogni scheda è un file in `data/schede/<slug>.json`. Per aggiungerne una copia un file esistente, modifica i campi e lancia `python3 build.py`: il build si ferma con un errore se mancano campi, se lo stato o i livelli di evidenza non sono validi o se non c'è almeno una fonte specifica.

Campi principali:
- `kind`: `peptide` o `sostanza` (determina l'URL)
- `category` e, facoltativo, `extra_categories` (la scheda compare anche in questi filtri, per esempio "Massa muscolare")
- `service`: consulenza collegata (`Peptidi`, `TRT`, `GLP-1`, `Longevity & Performance`) oppure `null`
- `status`: `ue`, `extra_ue`, `trial`, `ritirato`, `sperimentale`, `integratore`
- `dosing`: `basis` (`rcp`, `extra_ue`, `studi`, `nessuna`), `route` e `text`. `rcp` è ammesso solo per medicinali autorizzati
- `evidence`: per `in_vitro`, `animale`, `osservazionale`, `rct`, `autorizzato` un `level` (`si`, `limitato`, `no`) e una `note`
- `sources`: elenco di `{label, url, type}` con `type` tra `regolatorio`, `studio`, `revisione`, `azienda`, `notizia`
- `review`: `checked` (data ultima verifica fonti), `next_check`, `medical_reviewer` (resta `null` finché la revisione medica non è fatta)

Una GitHub Action rilancia il build a ogni push e fallisce se l'HTML committato non corrisponde ai dati.

## Prima di rendere pubblico
- Nome e brand definitivi, dominio e logo
- Revisione medico-scientifica delle 10 schede, bibliografia originale, grading delle prove, aggiornamenti e identità del revisore
- Verifica legale/autorizzativa di servizi sanitari e comunicazione pubblicitaria in Italia
- Informativa privacy definitiva, cookie e contratti con fornitori
- Form attivo e testato, anti-spam e rate limit, double opt-in (da implementare/configurare)
- Analytics e tracciamento per consulenza
- Test su smartphone, accessibilità e metadati finali

**Non rimuovere `noindex` fino a revisione e approvazione.**
