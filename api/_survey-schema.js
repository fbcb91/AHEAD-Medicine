// Generato da build.py: non modificare a mano.
export default {
 "aree": {
  "type": "multi",
  "required": true,
  "options": [
   "Peptidi",
   "TRT",
   "GLP-1",
   "Longevity & Performance",
   "Capelli",
   "Salute sessuale",
   "Menopausa",
   "Recupero e sport",
   "Non lo so ancora"
  ]
 },
 "obiettivi": {
  "type": "multi",
  "required": true,
  "options": [
   "Perdere peso",
   "Più energia e meno stanchezza",
   "Aumentare massa muscolare e forza",
   "Recuperare da un infortunio o un dolore",
   "Migliorare la salute ormonale",
   "Fermare la caduta dei capelli",
   "Migliorare la vita sessuale",
   "Gestire i sintomi della menopausa",
   "Prevenzione e longevità",
   "Capire se una sostanza fa per me"
  ],
  "max": 3
 },
 "gia_usato": {
  "type": "multi",
  "required": true,
  "options": [
   "Farmaci prescritti da un medico",
   "Peptidi o sostanze acquistati online",
   "Integratori",
   "Niente di tutto questo"
  ]
 },
 "seguito": {
  "type": "single",
  "required": true,
  "options": [
   "Sì",
   "No",
   "In passato"
  ]
 },
 "esami": {
  "type": "single",
  "required": true,
  "options": [
   "Sì",
   "No",
   "Non ricordo"
  ]
 },
 "sostanze": {
  "type": "multi",
  "required": false,
  "options": [
   "Semaglutide",
   "Tirzepatide",
   "Retatrutide",
   "Testosterone",
   "Ormone della crescita (somatropina)",
   "BPC-157",
   "TB-500",
   "MOTS-c",
   "Rapamicina (sirolimus)",
   "Metformina",
   "Precursori del NAD+ (NMN e NR)",
   "GHK-Cu",
   "Melanotan II",
   "Bremelanotide (PT-141)",
   "CJC-1295",
   "Ipamorelin",
   "Altre",
   "Nessuna in particolare"
  ]
 },
 "eta": {
  "type": "single",
  "required": true,
  "options": [
   "18–29",
   "30–39",
   "40–49",
   "50–59",
   "60 o più"
  ]
 },
 "sesso": {
  "type": "single",
  "required": true,
  "options": [
   "Uomo",
   "Donna",
   "Preferisco non dirlo"
  ]
 },
 "zona": {
  "type": "single",
  "required": false,
  "options": [
   "Nord Italia",
   "Centro Italia",
   "Sud Italia e isole",
   "Fuori dall’Italia"
  ]
 },
 "urgenza": {
  "type": "single",
  "required": true,
  "options": [
   "Il prima possibile",
   "Entro 3 mesi",
   "Sto solo esplorando"
  ]
 },
 "budget": {
  "type": "single",
  "required": true,
  "options": [
   "Meno di 50 €",
   "50–100 €",
   "100–150 €",
   "Più di 150 €"
  ]
 },
 "percorso": {
  "type": "single",
  "required": true,
  "options": [
   "Sì",
   "Forse",
   "No"
  ]
 },
 "lingua": {
  "type": "single",
  "required": false,
  "options": [
   "Sì, necessariamente",
   "Va bene anche in inglese"
  ]
 },
 "fonte": {
  "type": "single",
  "required": false,
  "options": [
   "Google",
   "Instagram o TikTok",
   "YouTube o podcast",
   "Passaparola",
   "Altro"
  ]
 },
 "note": {
  "type": "text",
  "required": false,
  "max": 500
 }
};
