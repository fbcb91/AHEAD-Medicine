# AHEAD Medicine — sito demo deploy-ready

> **AHEAD è un nome provvisorio. Il sito è un prototipo**, non una clinica e non offre servizi sanitari. Le schede sono bozze da sottoporre a revisione clinico-scientifica prima della messa online definitiva.

## Cosa contiene
- Homepage premium e responsive
- Peptide Library: `/library/` con ricerca e filtri
- 10 schede SEO separate: `/peptidi/bpc-157/`, ecc.
- 4 consulenze future **senza prezzi**: Peptidi, TRT, GLP-1 e Longevity & Performance
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

## Misura interesse
Le CTA lanciano un evento aggregato `Consulenza: interesse` con proprietà `servizio`, **senza l'email**. L'evento viene registrato solo se è stato collegato uno strumento compatibile con la funzione `window.plausible` e solo nel rispetto delle regole privacy e cookie. Collega la piattaforma analytics configurandone la libreria di tracciamento: non è inclusa nella demo.

La mail del visitatore non viene associata alla consulenza selezionata. Questo evita inferenze su informazioni sanitarie nella lista marketing.

## Aggiornare o aggiungere schede
Al momento i dati sono nel blocco `DATA` di `build.py`: modificane i campi e lancia `python3 build.py`. Quando si superano 10–20 schede, conviene separare dati e template, mantenendo URLs indicizzabili.

## Prima di rendere pubblico
- Nome e brand definitivi, dominio e logo
- Revisione medico-scientifica delle 10 schede, bibliografia originale, grading delle prove, aggiornamenti e identità del revisore
- Verifica legale/autorizzativa di servizi sanitari e comunicazione pubblicitaria in Italia
- Informativa privacy definitiva, cookie e contratti con fornitori
- Form attivo e testato, anti-spam e rate limit, double opt-in (da implementare/configurare)
- Analytics e tracciamento per consulenza
- Test su smartphone, accessibilità e metadati finali

**Non rimuovere `noindex` fino a revisione e approvazione.**
