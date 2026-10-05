# PPA — Piloto Privado de Avión

Source material (ANAC,
<https://www.argentina.gob.ar/anac/personal-aeronautico/examenes/ppa-piloto-privado-de-avion>,
files dated 2021/05, content from 2013–2014):

- `preguntas-todos-los-capitulos-ppa.pdf`: 313 questions in 8 chapters
- `preguntas-segun-raac-61-105.pdf`: 385 items with the official answer marked `*` (the "key")
- `teor-a-y-analisis-de-respuestas-ppa.pdf`: theory and per-question analysis
- `anexo-figuras-para-las-preguntas-ppa.pdf`: figures annex

## What the deck contains

The union of both question lists, deduplicated: 456 cards in 9 subdecks (the
8 chapters plus *Factores humanos y seguridad operacional* for key items that
are not in the chapter list). Card ids: `kNNN` is key item NNN, and `cC-NN`
is a chapter question with no key equivalent.

Every answer was checked by an independent blind analysis against the key and
against the theory document. Disputed items were double-checked by two more
reviewers, one of whom argued for the official key.

| status | count | meaning |
|--------|------:|---------|
| `key_error` | 17 | the official key marks a wrong option; the card teaches the correct one and shows what the key says |
| `no_key` | 1 | the key marks no option (k327) |
| `ambiguous` | 2 | defective question; the card keeps the key's answer (k256, k136) |
| `outdated` | 3 | correct in 2014, changed in RAAC 61 (2026) (k003, k223, k284) |

Smaller typos in the official questions (stem data that doesn't match any
option, duplicated options, misprints) are explained in a yellow **Nota** on
the card. The list is in `NOTES` in `tools/bootstrap_cards.py`.

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

`tools/` holds the one-time bootstrap that produced the YAML. It is kept for
provenance:

- `extract_figures.py --annex <annex.pdf> --key <key.pdf>` regenerates
  `media/` and `tools/key_images.json`.
- `bootstrap_cards.py` regenerates `cards/*.yaml` from `tools/data/`. **This
  overwrites manual edits.** Data files:
  - `analysis.db`: parsed PDFs, independent answers, verifications
  - `explicaciones_es.json`: Spanish explanations
  - curation tables at the top of the script

`analysis.db` tables: `questions` (key items, `ref_answer` = official key,
`my_answer`, `verified_answer`), `chapter_questions` (chapter PDF, mapping
to key, theory-implied answer), `verifications` (per-reviewer verdicts), and
the view `key_errors`.
