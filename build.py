"""Build an Anki package (.apkg) from a deck folder.

    uv run build.py ppa            # -> dist/ppa.apkg
    uv run build.py ppa --check    # validate only
    uv run build.py ppa --preview  # also write dist/<deck>-preview.html (all cards, answer side)

A deck folder contains:
  deck.yaml        deck/subdeck/model ids and labels
  model/           front.html, back.html, style.css (Anki card templates)
  cards/NN-*.yaml  one file per chapter; NN selects the subdeck from deck.yaml
  media/           images referenced by cards
"""
# /// script
# dependencies = ["genanki", "pyyaml"]
# ///
import argparse
import html
import re
import sys
from pathlib import Path

import genanki
import yaml

ROOT = Path(__file__).resolve().parent
FIELDS = ["ID", "Pregunta", "OpcionA", "OpcionB", "OpcionC", "Respuesta", "RespuestaTexto",
          "Imagenes", "Explicacion", "Teoria", "Aviso", "Nota", "Fuente"]
REQUIRED = {"id", "question", "options", "answer", "explanation"}
OPTIONAL = {"source", "status", "official_key", "images", "theory", "note"}


def load_cards(deck_dir, cfg):
    errors, cards, seen = [], [], set()
    media = deck_dir / "media"
    for path in sorted((deck_dir / "cards").glob("*.yaml")):
        chapter = path.name[:2]
        if chapter not in cfg["chapters"]:
            errors.append(f"{path.name}: prefix {chapter} not in deck.yaml chapters")
            continue
        for c in yaml.safe_load(path.read_text()) or []:
            where = f"{path.name}:{c.get('id', '?')}"
            if missing := REQUIRED - c.keys():
                errors.append(f"{where}: missing {sorted(missing)}")
                continue
            if extra := c.keys() - REQUIRED - OPTIONAL:
                errors.append(f"{where}: unknown fields {sorted(extra)}")
            if c["id"] in seen:
                errors.append(f"{where}: duplicate id")
            seen.add(c["id"])
            if c["answer"] not in c["options"]:
                errors.append(f"{where}: answer {c['answer']!r} not among options")
            if (status := c.get("status")) and status not in cfg["status"]:
                errors.append(f"{where}: unknown status {status!r}")
            if (status == "key_error") != ("official_key" in c):
                errors.append(f"{where}: official_key is required for key_error and only allowed there")
            for img in c.get("images") or []:
                if not (media / img).is_file():
                    errors.append(f"{where}: missing media/{img}")
            cards.append((chapter, c))
    return cards, errors


def fields_for(c, cfg):
    opts = c["options"]
    src = c.get("source") or {}
    fuente = " · ".join(filter(None, [
        f"Clave oficial ítem {src['key_item']}" if "key_item" in src else None,
        f"Cap. {src['chapter_question']}" if "chapter_question" in src else None,
        c["id"],
    ]))
    aviso = ""
    if status := c.get("status"):
        aviso = cfg["status"][status]["warning"].format(official_key=c.get("official_key"), answer=c["answer"])
    imgs = "".join(f'<img src="{html.escape(i)}">' for i in c.get("images") or [])
    return [
        c["id"], c["question"], opts.get("a", ""), opts.get("b", ""), opts.get("c", ""),
        c["answer"], opts[c["answer"]], imgs, c["explanation"], c.get("theory") or "", aviso, c.get("note") or "", fuente,
    ]


def render(template, fields):
    """Minimal Anki template rendering: {{#F}}..{{/F}} sections and {{F}} fields."""
    template = re.sub(r"{{#(\w+)}}(.*?){{/\1}}",
                      lambda m: m.group(2) if fields.get(m.group(1)) else "", template, flags=re.S)
    return re.sub(r"{{(\w+)}}", lambda m: fields.get(m.group(1), ""), template)


def write_preview(deck_dir, cfg, cards, out):
    tpl = deck_dir / "model"
    front, back = (tpl / "front.html").read_text(), (tpl / "back.html").read_text()
    body = []
    for ch, c in cards:
        f = dict(zip(FIELDS, fields_for(c, cfg)))
        f["Imagenes"] = f["Imagenes"].replace('src="', f'src="../{deck_dir.name}/media/')
        f["FrontSide"] = render(front, f)
        # the template's highlight script is page-global, so mark the answer statically here
        card_html = re.sub(r"<script>.*?</script>", "", render(back, f), flags=re.S).replace(
            f'<li data-letra="{c["answer"]}"', f'<li class="correcta" data-letra="{c["answer"]}"')
        body.append(f'<section class="card" id="{c["id"]}"><h3 class="fuente">{cfg["chapters"][ch]["title"]}'
                    f'</h3>{card_html}</section>')
    out.write_text(f'<!doctype html><meta charset="utf-8"><title>{cfg["name"]} preview</title>'
                   f'<style>{(tpl / "style.css").read_text()} section.card {{ border-bottom: 3px solid #999;'
                   f' padding-bottom: 24px; margin-bottom: 24px; }}</style>{"".join(body)}')
    print(f"wrote {out.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck", help="deck folder, e.g. ppa")
    ap.add_argument("--check", action="store_true", help="validate only, don't write the .apkg")
    ap.add_argument("--preview", action="store_true", help="also write an HTML preview of all cards")
    ap.add_argument("-o", "--output", help="output path (default dist/<deck>.apkg)")
    args = ap.parse_args()

    deck_dir = ROOT / args.deck
    cfg = yaml.safe_load((deck_dir / "deck.yaml").read_text())
    cards, errors = load_cards(deck_dir, cfg)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(f"{len(errors)} error(s)")
    print(f"{len(cards)} cards OK")
    if args.check:
        return

    tpl = deck_dir / "model"
    model = genanki.Model(
        cfg["model_id"], cfg["model_name"],
        fields=[{"name": f} for f in FIELDS],
        templates=[{"name": "Pregunta",
                    "qfmt": (tpl / "front.html").read_text(),
                    "afmt": (tpl / "back.html").read_text()}],
        css=(tpl / "style.css").read_text(),
        sort_field_index=FIELDS.index("Pregunta"),
    )
    decks = {ch: genanki.Deck(v["id"], f"{cfg['name']}::{v['title']}") for ch, v in cfg["chapters"].items()}
    media = set()
    for ch, c in cards:
        tags = [f"{cfg['tag_prefix']}::cap{ch}"]
        if status := c.get("status"):
            tags.append(f"{cfg['tag_prefix']}::{cfg['status'][status]['tag']}")
        if c.get("images"):
            tags.append(f"{cfg['tag_prefix']}::con_figura")
        decks[ch].add_note(genanki.Note(
            model=model, fields=fields_for(c, cfg), tags=tags,
            guid=genanki.guid_for(cfg["slug"], c["id"]),
        ))
        media.update(c.get("images") or [])

    out = Path(args.output) if args.output else ROOT / "dist" / f"{args.deck}.apkg"
    out.parent.mkdir(parents=True, exist_ok=True)
    genanki.Package(list(decks.values()), media_files=[str(deck_dir / "media" / m) for m in sorted(media)]).write_to_file(out)
    print(f"wrote {out.relative_to(ROOT)} ({len(media)} media files)")
    if args.preview:
        write_preview(deck_dir, cfg, cards, out.with_name(f"{args.deck}-preview.html"))


if __name__ == "__main__":
    main()
