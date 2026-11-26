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
 "focus_glp1": {
  "type": "single",
  "required": false,
  "options": [
   "Se un farmaco GLP-1 è adatto a me",
   "Come gestire un trattamento che sto già facendo",
   "Come mantenere il peso dopo la terapia",
   "Alternative ai farmaci"
  ]
 },
 "focus_trt": {
  "type": "single",
  "required": false,
  "options": [
   "Se ho il testosterone basso",
   "Se una terapia è adatta a me",
   "Come seguire meglio una terapia in corso",
   "Testosterone e fertilità"
  ]
 },
 "focus_capelli": {
  "type": "multi",
  "required": false,
  "options": [
   "Minoxidil",
   "Finasteride o dutasteride",
   "Integratori",
   "Trattamenti in clinica (PRP, laser…)",
   "Niente finora"
  ]
 },
 "focus_menopausa": {
  "type": "single",
  "required": false,
  "options": [
   "Benefici e rischi della terapia ormonale",
   "Alternative non ormonali",
   "Prevenzione per ossa, cuore e metabolismo",
   "Come gestire sintomi specifici"
  ]
 },
 "focus_peptidi": {
  "type": "single",
  "required": false,
  "options": [
   "Un parere su sostanze che sto già usando",
   "Capire prove e rischi prima di decidere",
   "Sapere se esistono alternative autorizzate"
  ]
 },
 "focus_recupero": {
  "type": "single",
  "required": false,
  "options": [
   "Infortunio recente",
   "Dolore che dura da mesi",
   "Recupero dopo un intervento",
   "Voglio migliorare la preparazione"
  ]
 },
 "focus_longevity": {
  "type": "multi",
  "required": false,
  "options": [
   "Check-up ed esami mirati",
   "Un piano di prevenzione",
   "Farmaci e sostanze per la longevità",
   "Performance fisica e mentale"
  ],
  "max": 2
 },
 "focus_sessuale": {
  "type": "single",
  "required": false,
  "options": [
   "Desiderio",
   "Erezione",
   "Fertilità",
   "Altro"
  ]
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
 "questionario_medico": {
  "type": "single",
  "required": true,
  "options": [
   "Sì, così la visita è più utile",
   "Forse",
   "No, preferisco raccontare tutto in visita"
  ]
 },
 "esami_prima": {
  "type": "single",
  "required": true,
  "options": [
   "Sì",
   "Sì, se il costo è contenuto",
   "Preferisco parlarne prima con il medico"
  ]
 },
 "chat": {
  "type": "single",
  "required": true,
  "options": [
   "Sì, molto",
   "Forse",
   "No, mi bastano le videoconsulenze"
  ]
 },
 "fiducia": {
  "type": "multi",
  "required": true,
  "options": [
   "Profili dei medici con esperienza e titoli",
   "Recensioni di altri pazienti",
   "Prezzi chiari fin dall’inizio",
   "Poter cambiare medico",
   "Indipendenza da chi vende prodotti"
  ],
  "max": 2
 },
 "note": {
  "type": "text",
  "required": false,
  "max": 500
 }
};
