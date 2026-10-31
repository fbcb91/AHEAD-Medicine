# Foto delle schede

Metti qui le foto evocative; `python3 build.py` le ritaglia in formato 1200×400 (3:1), le converte in WebP in `media/` e le usa al posto dell'illustrazione.

- `img/schede/<slug>.jpg` → foto di una singola scheda (es. `img/schede/semaglutide.jpg`)
- `img/aree/<area>.jpg` → foto per tutte le schede di un'area senza foto propria: `recupero`, `ormoni`, `massa-muscolare`, `metabolismo`, `longevita`, `pelle`, `neuro`, `immunita`, `sessualita-e-fertilita`

Formati: jpg, png o webp, orizzontali, almeno 1600 px di larghezza. Usa solo immagini con licenza adatta (proprie, Unsplash, Pexels, Adobe Stock…). Serve Pillow: `pip install pillow`.
