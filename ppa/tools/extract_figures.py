"""Extract figures from the ANAC PPA source PDFs into ppa/media/.

One-time bootstrap step; the images are committed, so you only need this to
regenerate them.

    uv run ppa/tools/extract_figures.py --annex anexo-figuras-para-las-preguntas-ppa.pdf \
        --key preguntas-segun-raac-61-105.pdf

Writes:
  media/ppa-figura-NN.{jpg,png}   one per figure of the annex (Figura 33 spans 3 pages)
  media/ppa-key-xNNN.{jpg,png}    images embedded in the answer-key PDF, by PDF xref

Answer-key images are copied byte for byte from the PDF (no re-encoding).
Annex figures carry vector overlays, so they are rendered at the embedded
scan's native resolution (min 220 DPI, so nothing is downsampled) and stored
as JPEG q92 (visually lossless, PSNR > 46 dB) unless PNG is smaller, which
happens for vector-drawn tables.
  tools/key_images.json     {key item id: [media file, ...]}
"""
# /// script
# dependencies = ["pymupdf", "pillow"]
# ///
import argparse
import collections
import io
import json
import re
from pathlib import Path

import pymupdf
from PIL import Image

HERE = Path(__file__).resolve().parent
MEDIA = HERE.parent / "media"
DPI = 220
KEY_LOGO_XREF = 224  # page-header logo repeated on every page of the key PDF

# Annex layout: page -> figures top to bottom, with an optional explicit clip
# (in PDF points) when the figure is vector-drawn rather than an embedded image.
CONTENT = (40, 125, 572, 765)
ANNEX = {
    1: ["1", "2"], 2: ["3", "4"], 3: ["5", "6"], 4: ["7"], 5: ["8"],
    6: ["9", "29"], 7: ["30", "31"],
    8: ["33"], 9: ["33"], 10: ["33"],
    11: ["34"], 12: ["35"], 13: ["36"], 14: ["37"],
    15: ["38", "39"], 16: ["41"], 17: ["48"], 18: ["49"], 19: ["50"],
    20: ["59", "61"], 21: ["62", "63"], 22: ["65"], 23: ["66"], 24: ["67"],
}
CLIPS = {
    ("33", 8): CONTENT, ("33", 9): CONTENT, ("33", 10): (40, 125, 572, 420),
    ("36", 13): (60, 215, 590, 500),
    ("38", 15): (60, 140, 580, 520), ("39", 15): (60, 520, 580, 700),
    ("41", 16): (40, 125, 590, 625),
}


def native_dpi(page, rect):
    """Highest resolution of the embedded images inside rect, never below DPI."""
    rect, best = pymupdf.Rect(rect), DPI
    for i in page.get_image_info():
        bbox = pymupdf.Rect(i["bbox"])
        if bbox.intersects(rect) and bbox.width > 0:
            best = max(best, i["width"] / bbox.width * 72)
    return min(round(best), 400)


def render(page, rect):
    pix = page.get_pixmap(dpi=native_dpi(page, rect), clip=pymupdf.Rect(rect))
    return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")


def save(im, stem):
    """Write the smaller of PNG / JPEG q92 and return the file name."""
    png, jpg = io.BytesIO(), io.BytesIO()
    im.save(png, "PNG", optimize=True)
    im.save(jpg, "JPEG", quality=92, optimize=True)
    ext, buf = ("png", png) if png.tell() <= jpg.tell() else ("jpg", jpg)
    for old in MEDIA.glob(f"{stem}.*"):
        old.unlink()
    (MEDIA / f"{stem}.{ext}").write_bytes(buf.getvalue())
    return f"{stem}.{ext}"


def save_embedded(doc, xref, stem):
    """Copy an embedded image as-is when it is a plain RGB/gray JPEG or PNG."""
    img = doc.extract_image(xref)
    if not img.get("smask") and img["ext"] in ("jpeg", "jpg", "png") and img["colorspace"] in (1, 3):
        ext = "png" if img["ext"] == "png" else "jpg"
        for old in MEDIA.glob(f"{stem}.*"):
            old.unlink()
        (MEDIA / f"{stem}.{ext}").write_bytes(img["image"])
        return f"{stem}.{ext}"
    pix = pymupdf.Pixmap(doc, xref)
    if pix.alpha or img.get("smask"):
        pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.Pixmap(pix, 0) if pix.alpha else pix)
    im = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    return save(im, stem)


def annex(pdf):
    doc = pymupdf.open(pdf)
    parts = collections.defaultdict(list)
    for pno, figs in ANNEX.items():
        page = doc[pno - 1]
        imgs = sorted((i["bbox"] for i in page.get_image_info()), key=lambda b: b[1])
        for idx, fig in enumerate(figs):
            clip = CLIPS.get((fig, pno))
            if clip is None:
                x0, y0, x1, y1 = imgs[idx] if len(imgs) == len(figs) else CONTENT
                clip = (x0 - 4, y0 - 4, x1 + 4, y1 + 4)
            parts[fig].append(render(page, clip))
    for fig, ims in parts.items():
        w = max(i.width for i in ims)
        out = Image.new("RGB", (w, sum(i.height for i in ims)), "white")
        y = 0
        for im in ims:
            out.paste(im, (0, y))
            y += im.height
        print("figura", fig, out.size, save(out, f"ppa-figura-{int(fig):02d}"))


def key_images(pdf):
    """Assign each embedded image to the question whose 'N S 1' header precedes it."""
    doc = pymupdf.open(pdf)
    events = []
    for page in doc:
        lines = collections.defaultdict(list)
        for w in page.get_text("words"):
            lines[round(w[1])].append(w)
        for y, ws in lines.items():
            ws.sort(key=lambda w: w[0])
            m = re.fullmatch(r"(\d+) S 1", " ".join(w[4] for w in ws))
            if m:
                events.append((page.number, y, "q", int(m.group(1))))
        for info in page.get_image_info(xrefs=True):
            if info["xref"] != KEY_LOGO_XREF:
                events.append((page.number, info["bbox"][1], "img", info))
    events.sort(key=lambda e: (e[0], e[1]))
    assigned, current, saved = collections.defaultdict(list), None, {}
    for pno, _, kind, val in events:
        if kind == "q":
            current = val
            continue
        xref = val["xref"]
        if xref not in saved:
            saved[xref] = save_embedded(doc, xref, f"ppa-key-x{xref}")
        name = saved[xref]
        if name not in assigned[current]:
            assigned[current].append(name)
    (HERE / "key_images.json").write_text(json.dumps(assigned, indent=1, sort_keys=True))
    print(len(assigned), "key items with images")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--annex", required=True)
    ap.add_argument("--key", required=True)
    a = ap.parse_args()
    MEDIA.mkdir(exist_ok=True)
    annex(a.annex)
    key_images(a.key)
