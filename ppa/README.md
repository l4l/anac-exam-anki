# PPA — Piloto Privado de Avión

Source material (ANAC,
<https://www.argentina.gob.ar/anac/personal-aeronautico/examenes/ppa-piloto-privado-de-avion>,
files dated 2021/05, content from 2013–2014):

- `preguntas-todos-los-capitulos-ppa.pdf`: 313 questions in 8 chapters
- `preguntas-segun-raac-61-105.pdf`: 385 items with the official answer marked `*` (the "key")
- `teor-a-y-analisis-de-respuestas-ppa.pdf`: theory and per-question analysis
- `anexo-figuras-para-las-preguntas-ppa.pdf`: figures annex

## What the deck contains

The union of both question lists, deduplicated: 444 cards in 9 subdecks (the
8 chapters plus *Factores humanos y seguridad operacional* for key items that
are not in the chapter list). Card ids: `kNNN` is key item NNN, and `cC-NN`
is a chapter question with no key equivalent.

Every answer was checked by an independent blind analysis against the key and
against the theory document. Disputed items were double-checked by two more
reviewers, one of whom argued for the official key.

| status | count | meaning |
|--------|------:|---------|
| `key_error` | 10 | the official key marks a wrong option; the card teaches the correct one and shows what the key says |
| `no_key` | 1 | the key marks no option (k327) |
| `ambiguous` | 5 | defective question; the card keeps the key's answer (k030, k093, k123, k136, k268) |
| `outdated` | 3 | correct in 2014, changed in RAAC 61 (2026) (k003, k223, k284) |

Smaller typos in the official questions (stem data that doesn't match any
option, duplicated options, misprints) are explained in a yellow **Nota** on
the card (`note:` in the YAML).

### Duplicated key items

The key repeats some questions under two item numbers (same question, options
and answer). Only one card is kept: the one matched to a chapter question. The
other item number has no card, and its id must not be reused.

| kept | dropped | question |
|------|---------|----------|
| k203 | k004 | Fig. 29, ilustr. 1: posición relativa del avión respecto a la estación VOR |
| k206 | k207 | Fig. 29, ilustr. 8: ¿sobre cuál radial? |
| k211 | k212 | Fig. 29, ilustr. 2: ¿sobre cuál radial? |
| k217 | k218 | Fig. 29, ilustr. 5: ¿sobre cuál radial? |
| k230 | k231 | Fig. 30, ilustr. 1: marcación magnética a la estación |
| k234 | k235 | Fig. 30, ilustr. 2: marcación magnética para volar hacia la estación |
| k238 | k239 | Fig. 30, ilustr. 2: rumbo para interceptar la marcación 180° hacia la estación |
| k240 | k241 | Fig. 30, ilustr. 3: marcación magnética desde la estación |
| k243 | k244 | Fig. 30: indicación en curso hacia la estación con viento cruzado de la derecha |
| k246 | k247 | Fig. 31, ilustr. 1: marcación relativa a la estación |
| k248 | k249 | Fig. 31, ilustr. 4: QDM con rumbo magnético 320° |
| k250 | k251 | Fig. 31, ilustr. 6: QDM con rumbo magnético 120° |

Questions that the bank asks twice with *different* options (k095/k354,
k342/k381, k036/k337, c2-16/k017) are kept as separate cards.

## Images

- `media/ppa-key-x*.jpg`: images embedded next to the question in the key PDF,
  copied byte for byte (no re-encoding).
- `media/ppa-figura-NN.*`: figures from the annex, rendered at the scan's
  native resolution (≥ 220 DPI, so nothing is downsampled). Stored as JPEG
  q92 (visually lossless, PSNR > 46 dB) unless PNG is smaller (vector tables).
  When a question cites "Figura N", the annex copy is used, because it is
  never lower resolution than the key's.

Not every annex figure is used. The weight-and-balance and landing charts
(Fig 33–66) have no questions in this bank.

## Editing

Edit `cards/*.yaml` directly, then `uv run build.py ppa --check`. The YAML is
the source of truth.
