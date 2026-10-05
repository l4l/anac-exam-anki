# anac-exam-anki

Anki decks for the Argentine ANAC pilot theory exams, kept as reviewable text
(YAML) plus images, and built into an `.apkg` with a script.

| Deck | Folder | Cards |
|------|--------|-------|
| Piloto Privado de Avión (PPA) | [`ppa/`](ppa/) | 456 |

## Build

Requires [uv](https://docs.astral.sh/uv/) (dependencies are declared inline in
the scripts, nothing to install).

```sh
uv run build.py ppa --check     # validate cards, options, answers, media
uv run build.py ppa             # -> dist/ppa.apkg
uv run build.py ppa --preview   # also dist/ppa-preview.html: every card, answer side, in one page
```

Import `dist/ppa.apkg` in Anki (File → Import). Works in Anki desktop,
AnkiDroid and AnkiMobile. Re-importing after edits updates the existing notes
in place (stable GUIDs derived from each card `id`) and keeps your review
history.

## Layout

```
build.py                 generic builder: <deck>/ -> dist/<deck>.apkg
ppa/
  deck.yaml              deck/subdeck/note-type ids, status labels and warnings
  model/                 Anki card templates: front.html, back.html, style.css
  cards/NN-*.yaml        one file per chapter (NN selects the subdeck)
  media/                 figures (annex + images embedded in the answer key)
```

## Card format

```yaml
- id: k099                     # stable id; never reuse or change (it is the note GUID)
  source:
    key_item: 99               # item number in preguntas-segun-raac-61-105.pdf
    chapter_question: '1.19'   # chapter.question in preguntas-todos-los-capitulos-ppa.pdf
  question: (Referirse a la Figura 2) Si un avion pesa 2200 kg, ...
  options: {a: 2200 kg., b: 3100 kg., c: 3300 kg.}
  answer: b                    # the answer the card teaches
  status: key_error            # optional: key_error | no_key | ambiguous | outdated
  official_key: c              # optional: what the official ANAC key marks
  images: [ppa-figura-02.jpg]  # optional, files in media/
  explanation: 'Factor de carga a 45° = 1,414<br>2200 kg × 1,414 ≈ 3111 kg → 3100 kg'
  note: ...                    # optional, yellow "Nota" box (errata, outdated rules)
  theory: ...                  # optional, excerpt from the official "Teoría y análisis"
```

Text fields are HTML (`<br>`, `<b>`). `build.py --check` rejects unknown
fields, duplicate ids, answers not among the options and missing images.

## Tags

`ppa::capNN`, `ppa::con_figura`, and one per status:
`ppa::clave_oficial_erronea`, `ppa::sin_clave_oficial`, `ppa::ambigua`,
`ppa::desactualizada`. Use them for filtered decks, e.g.
`tag:ppa::clave_oficial_erronea`.
