"""Generate ppa/cards/*.yaml from the answer analysis (tools/data/analysis.db).

One-time bootstrap: the YAML files are the source of truth afterwards and are
edited by hand. Re-running this OVERWRITES them.

    uv run ppa/tools/bootstrap_cards.py

Inputs (tools/data/):
  analysis.db                  parsed PDFs + independent answers + verification
  key_item_chapters.json       chapter for key items not present in the chapter PDF
  verified_explanations.json   English drafts for the disputed items (superseded by explicaciones_es)
  explicaciones_es.json        Spanish back-side explanation + theory excerpt per card id
  ../key_images.json           images embedded per key item (extract_figures.py)

Manual curation decided during review lives in the tables below (SKIP, IMAGES,
OPTIONS, STATUS, NOTES) so a re-run reproduces the committed YAML.
"""
# /// script
# dependencies = ["pyyaml"]
# ///
import json
import re
import sqlite3
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CARDS = HERE.parent / "cards"
MEDIA = HERE.parent / "media"

CHAPTERS = {
    1: "aerodinamica-basica", 2: "grupo-motopropulsor", 3: "instrumentos-de-vuelo",
    4: "regulaciones", 5: "generalidades", 6: "meteorologia", 7: "performance",
    8: "navegacion", 9: "factores-humanos",
}
LETTERS = "abc"
Q_PREFIX = re.compile(r"^(PPA(Mot)?:?\s*|\d{2}-\d{2}-\d{2}\s+|\d{1,3}\s*\.?-\s*\.?\s*)")
OPT_PREFIX = re.compile(r"^[a-cA-C]\s*[\).]\s*")
FIG_REF = re.compile(r"Figura (\d+)(?!-)", re.I)

# --- manual curation -------------------------------------------------------
SKIP = {
    "k385": "duplicate of k283 (same text); k283 keeps the correct VASI image",
}
IMAGES = {
    # the key prints the 4-panel Fig 48 next to k283, but its 'ilustración B' is the 3-panel one
    "k283": ["ppa-key-x319.jpg"],
}
OPTIONS = {
    # source PDF lost the 'c)' label and printed option c as a continuation of b
    "c4-24": {"b": "Una altitud de 500 pies sobre la superficie y no menos de 500 pies de cualquier "
                   "persona, nave, vehículo o estructuras.",
              "c": "300 m sobre la superficie terrestre."},
}
STATUS = {  # status for cards whose answer stays as the official key
    "k136": "ambiguous",
    "k003": "outdated", "k223": "outdated", "k284": "outdated",
}
NOTES = {
    "k003": "Bajo la RAAC 61 vigente (2026) ya no existe la readaptación a los 30 días; la experiencia reciente (61.140) exige 3 despegues y aterrizajes en los últimos 90 días.",
    "k223": "Bajo la RAAC 61 vigente (2026) ya no existe la readaptación a los 30 días; la experiencia reciente (61.140) exige 3 despegues y aterrizajes en los últimos 90 días.",
    "k284": "La RAAC 61 vigente (61.160) exige actualizar el domicilio en el legajo pero ya no fija el plazo de 30 días.",
    "k136": "Según OACI, al atravesar la capa de transición en ascenso la posición vertical se expresa en niveles de vuelo (en descenso, en altitudes). No hay opción «niveles de vuelo» y el enunciado está incompleto; la clave oficial marca «Altitudes».",
    "k091": "El enunciado parece tener un error: 1540 kg × 1,154 = 1777 kg, que no coincide con ninguna opción. La clave espera la más cercana (1848 kg).",
    "k182": "Dato inconsistente: 110 lb ÷ 6 lb/gal = 18,3 gal, que no está entre las opciones. La teoría ANAC resuelve el problema con 90 lb (= 15 gal).",
    "k348": "El cálculo exacto da ≈ 4,7 kt de componente cruzada; la opción marcada (3 kt) es la única plausible.",
    "k349": "El cálculo exacto da ≈ 7,6 kt de componente cruzada; la opción marcada (9 kt) es la única plausible.",
    "k168": "La respuesta usa la fórmula del banco ANAC (diferencia temperatura − punto de rocío ÷ 6,5 × 1000 m). El método estándar (≈ 125 m por °C) daría ≈ 560 m.",
    "k173": "La respuesta usa la fórmula del banco ANAC (diferencia temperatura − punto de rocío ÷ 6,5 × 1000 m). El método estándar (≈ 125 m por °C) daría ≈ 250 m.",
    "k301": "Las opciones a y c significan lo mismo; la clave oficial marca a.",
    "k064": "Las opciones a y c describen lo mismo (el arco blanco); la clave oficial marca c.",
    "k356": "El enunciado dice «cuadrado», pero la velocidad de pérdida aumenta con la raíz cuadrada del factor de carga.",
    "k358": "Errata en la opción b: «7°» debería ser «−7 °C».",
    "c2-29": "La opción b dice «consumo excesivo de combustible»; la fuente original se refiere a consumo excesivo de aceite.",
    "k376": "El enunciado clasifica mal algunos ejemplos (Hanta virus y Hepatitis B suelen ser grupo de riesgo 3).",
    "k293": "El término OACI correcto en descenso es «altitud»; la opción marcada es solo la más cercana.",
    "k177": "El requisito es 25 h como piloto al mando desde la obtención de la licencia; la redacción de la opción es imprecisa.",
    "c4-28": "La Figura 4-5 no está en el anexo de figuras; se responde con la regla semicircular de niveles de crucero VFR.",
    "c4-29": "La Figura 4-5 no está en el anexo de figuras; se responde con la regla semicircular de niveles de crucero VFR.",
}


def curate(c, spanish):
    """Apply Spanish texts and the manual curation tables to one card dict."""
    es = spanish[c["id"]]
    c["explanation"] = es["explicacion"].strip()
    if es.get("teoria"):
        c["theory"] = es["teoria"].strip()
    else:
        c.pop("theory", None)
    if c["id"] in IMAGES:
        c["images"] = IMAGES[c["id"]]
    if c["id"] in OPTIONS:
        c["options"].update(OPTIONS[c["id"]])
    if c["id"] in STATUS:
        c["status"], c["official_key"] = STATUS[c["id"]], c["answer"]
    if c["id"] in NOTES:
        c["note"] = NOTES[c["id"]]
    return c


def clean_q(s):
    return Q_PREFIX.sub("", s.strip()).strip()


def clean_opt(s):
    return OPT_PREFIX.sub("", (s or "").strip()).strip()


def figures_for(text):
    out = []
    for n in FIG_REF.findall(text):
        for f in MEDIA.glob(f"ppa-figura-{int(n):02d}.*"):
            if f.name not in out:
                out.append(f.name)
    return out


def card(id_, chapter, source, question, opts, answer, explanation,
         images, status="ok", official_key=None, theory=None):
    options = {LETTERS[i]: clean_opt(o) for i, o in enumerate(opts) if clean_opt(o)}
    c = {"id": id_, "source": source, "question": clean_q(question), "options": options,
         "answer": LETTERS[answer - 1]}
    if status != "ok":
        c["status"] = status
        c["official_key"] = LETTERS[official_key - 1] if official_key else None
    if images:
        c["images"] = images
    c["explanation"] = explanation.strip()
    if theory:
        c["theory"] = theory.strip()
    return chapter, c


def main():
    db = sqlite3.connect(DATA / "analysis.db")
    db.row_factory = sqlite3.Row
    key_chapter = {int(k): v for k, v in json.loads((DATA / "key_item_chapters.json").read_text()).items()}
    rewritten = {int(k): v for k, v in json.loads((DATA / "verified_explanations.json").read_text()).items()}
    key_images = {int(k): v for k, v in json.loads((HERE / "key_images.json").read_text()).items()}
    verdicts = {r["id"]: r["verdict"] for r in db.execute("select id, verdict from verifications where verifier='A'")}

    # chapter questions that correspond to a key item (same options, possibly reordered)
    chq_by_key = {}
    for r in db.execute("""select * from chapter_questions
                           where ref_id is not null and option_map is not null and option_map != ''
                           order by chapter, cast(qnum as int)"""):
        chq_by_key.setdefault(r["ref_id"], r)

    # chapter of any (even option-mismatched) chapter question pointing at a key item
    for r in db.execute("select ref_id, min(chapter) ch from chapter_questions where ref_id is not null group by ref_id"):
        key_chapter.setdefault(r["ref_id"], r["ch"])

    spanish = json.loads((DATA / "explicaciones_es.json").read_text())
    decks = {ch: [] for ch in CHAPTERS}
    order = {}

    for q in db.execute("select * from questions order by id"):
        chq = chq_by_key.get(q["id"])
        chapter = chq["chapter"] if chq else key_chapter[q["id"]]
        verdict = verdicts.get(q["id"])
        status = {"KEY_WRONG": "key_error", "NO_KEY": "no_key", "AMBIGUOUS": "ambiguous"}.get(verdict, "ok")
        answer = q["verified_answer"] if status in ("key_error", "no_key") else q["ref_answer"]
        opts = [q["opt_a"], q["opt_b"], q["opt_c"]]
        if not any(opts) and chq:  # key item printed without options: use the chapter version
            opts = [chq["opt_a"], chq["opt_b"], chq["opt_c"]]
        if not any(opts):  # key 307 = duplicate of key 100 printed without options
            continue
        source = {"key_item": q["id"]}
        if chq:
            source["chapter_question"] = f"{chq['chapter']}.{chq['qnum']}"
        theory = None
        if chq and chq["theory_answer"] and chq["option_map"]:
            # theory_answer uses chapter lettering; keep the note only if it agrees with the card
            if chq["option_map"][chq["theory_answer"] - 1] == LETTERS[answer - 1]:
                theory = chq["theory_note"]
        # the annex copy of a numbered figure is never lower resolution than the key's embedded one
        images = figures_for(q["question"]) or key_images.get(q["id"])
        ch, c = card(f"k{q['id']:03d}", chapter, source, q["question"], opts, answer,
                     rewritten.get(q["id"]) or q["my_explanation"], images, status, q["ref_answer"], theory)
        if c["id"] in SKIP:
            continue
        decks[ch].append(curate(c, spanish))
        order[c["id"]] = (int(chq["qnum"]) if chq else 1000 + q["id"])

    # chapter-PDF questions with no key equivalent; answer = independent analysis (agrees with theory doc)
    for r in db.execute("""select * from chapter_questions
                           where ref_id is null or option_map is null or option_map = ''
                           order by chapter, cast(qnum as int)"""):
        ch, c = card(f"c{r['chapter']}-{int(r['qnum']):02d}", r["chapter"],
                     {"chapter_question": f"{r['chapter']}.{r['qnum']}"},
                     r["question"], [r["opt_a"], r["opt_b"], r["opt_c"]], r["ch_my_answer"],
                     r["ch_explanation"], figures_for(r["question"]),
                     theory=r["theory_note"] if r["theory_answer"] == r["ch_my_answer"] else None)
        decks[ch].append(curate(c, spanish))
        order[c["id"]] = int(r["qnum"])

    yaml.add_representer(str, lambda d, s: d.represent_scalar(
        "tag:yaml.org,2002:str", s, style="|" if "\n" in s else None))
    CARDS.mkdir(exist_ok=True)
    for ch, cards in decks.items():
        cards.sort(key=lambda c: (order[c["id"]], c["id"]))
        path = CARDS / f"{ch:02d}-{CHAPTERS[ch]}.yaml"
        path.write_text(yaml.dump(cards, allow_unicode=True, sort_keys=False, width=100))
        print(path.name, len(cards))


if __name__ == "__main__":
    main()
