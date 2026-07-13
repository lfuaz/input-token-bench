"""Measurement harness — text vs image input token cost + extraction reliability.

For every corpus text we run 3 input modes through the SAME model with the
SAME fixed instruction, asking for the SAME 5 keys:
  - text        : raw text in the input
  - img_dense   : dense-preset PNG in the input
  - img_comfort : comfortable-preset PNG in the input

For each call we record the REAL usage.input_tokens returned by the API
(never an estimate) and score the extracted values against known ground truth.

Output: results.csv  +  results.json
"""
import base64
import csv
import io
import json
import os
import pathlib
import re
import sys

import anthropic
from PIL import Image

MAX_IMG_PX = 8000  # hard API limit on either image dimension

HERE = pathlib.Path(__file__).parent
CORPUS = HERE / "corpus"
IMG = CORPUS / "img"

MODEL = "claude-sonnet-5"
MAX_TOKENS = 400

KEYS = ["nom_client", "date_facture", "montant_total", "reference_contrat", "date_echeance"]

INSTRUCTION = (
    "Tu reçois un document en français. Extrais EXACTEMENT ces 5 champs et "
    "réponds UNIQUEMENT par un objet JSON valide, sans texte autour, avec ces "
    "clés : nom_client, date_facture, montant_total, reference_contrat, "
    "date_echeance. Recopie les valeurs telles qu'elles apparaissent dans le "
    "document. Si un champ est absent, mets une chaîne vide."
)

# ---- value normalisation: measures if the model READ the right value, not format ----

def norm_amount(s):
    digits = re.sub(r"[^\d]", "", s)
    return digits

def norm_date(s):
    nums = re.findall(r"\d+", s)
    if len(nums) == 3:
        # canonicalise to a sorted signature so 14/03/2024 == 2024-03-14
        year = max(nums, key=len)
        rest = sorted(n for n in nums if n is not year)
        return (year, tuple(sorted(rest)))
    return re.sub(r"\s+", "", s.lower())

def norm_plain(s):
    return re.sub(r"\s+", " ", s.strip().lower())

NORMALIZERS = {
    "nom_client": norm_plain,
    "date_facture": norm_date,
    "montant_total": norm_amount,
    "reference_contrat": lambda s: re.sub(r"[\s-]", "", s.upper()),
    "date_echeance": norm_date,
}


def score(extracted, truth):
    correct, errors = 0, {}
    for k in KEYS:
        got = extracted.get(k, "") if isinstance(extracted, dict) else ""
        exp = truth[k]
        n = NORMALIZERS[k]
        if n(str(got)) == n(exp):
            correct += 1
        else:
            errors[k] = {"expected": exp, "got": got}
    return correct, errors


def parse_json(raw):
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def call_text(client, text):
    resp = client.messages.create(
        model=MODEL, max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": INSTRUCTION},
            {"type": "text", "text": text},
        ]}],
    )
    return resp, False


def load_image_bytes(png_path):
    """Return (png_bytes, downscaled_bool). Downscale if a dim exceeds MAX_IMG_PX."""
    raw = png_path.read_bytes()
    im = Image.open(io.BytesIO(raw))
    w, h = im.size
    if max(w, h) <= MAX_IMG_PX:
        return raw, False
    scale = MAX_IMG_PX / max(w, h)
    im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue(), True


def call_image(client, png_path):
    data, downscaled = load_image_bytes(png_path)
    b64 = base64.standard_b64encode(data).decode()
    resp = client.messages.create(
        model=MODEL, max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": INSTRUCTION},
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
        ]}],
    )
    return resp, downscaled


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic()

    corpus = json.loads((CORPUS / "corpus_truth.json").read_text(encoding="utf-8"))
    render_meta = {(m["id"], m["preset"]): m
                   for m in json.loads((CORPUS / "render_meta.json").read_text(encoding="utf-8"))}

    rows = []
    for item in corpus:
        text = (CORPUS / item["file"]).read_text(encoding="utf-8")
        truth = item["truth"]
        modes = [
            ("text", lambda: call_text(client, text), None),
            ("img_dense", lambda: call_image(client, IMG / f"text_{item['id']}_dense.png"), "dense"),
            ("img_comfort", lambda: call_image(client, IMG / f"text_{item['id']}_comfortable.png"), "comfortable"),
        ]
        text_tokens = None
        for mode, fn, preset in modes:
            resp, downscaled = fn()
            in_tok = resp.usage.input_tokens
            raw = "".join(b.text for b in resp.content if b.type == "text")
            extracted = parse_json(raw)
            correct, errors = score(extracted or {}, truth)
            rmeta = render_meta.get((item["id"], preset), {}) if preset else {}
            if mode == "text":
                text_tokens = in_tok
            reduction = None if mode == "text" or not text_tokens else round(
                (text_tokens - in_tok) / text_tokens * 100, 1)
            row = {
                "text_id": item["id"],
                "word_count": item["word_count"],
                "char_count": item["char_count"],
                "mode": mode,
                "img_width_px": rmeta.get("width_px", ""),
                "img_height_px": rmeta.get("height_px", ""),
                "img_megapixels": rmeta.get("megapixels", ""),
                "img_downscaled": downscaled,
                "input_tokens": in_tok,
                "reduction_vs_text_pct": reduction if reduction is not None else "",
                "fields_correct": correct,
                "fields_total": len(KEYS),
                "extraction_ok": correct == len(KEYS),
                "errors": errors,
            }
            rows.append(row)
            print(f"text {item['id']:>1} {mode:<11} tokens={in_tok:>6} "
                  f"red={row['reduction_vs_text_pct'] or '   -':>5} "
                  f"score={correct}/{len(KEYS)}")

    (HERE / "results.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    cols = ["text_id", "word_count", "char_count", "mode", "img_width_px",
            "img_height_px", "img_megapixels", "img_downscaled", "input_tokens",
            "reduction_vs_text_pct", "fields_correct", "fields_total", "extraction_ok"]
    with (HERE / "results.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote results.json + results.csv ({len(rows)} rows)")


if __name__ == "__main__":
    main()
