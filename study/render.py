"""Render each corpus text to PNG, headless, with 2 layout presets.

Same source text, two presets that differ only in font size / line height /
margins (police, interligne, marge) — NOT in wording.
  - dense       : small font, tight leading, narrow page
  - comfortable : larger font, airy leading, wide page

Output: corpus/img/text_{id}_{preset}.png  +  corpus/render_meta.json
"""
import json
import pathlib
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
CORPUS = HERE / "corpus"
IMG = CORPUS / "img"
IMG.mkdir(exist_ok=True)

PRESETS = {
    "dense":       {"font_px": 13, "line_height": 1.25, "pad_px": 16, "width_px": 640},
    "comfortable": {"font_px": 18, "line_height": 1.8,  "pad_px": 40, "width_px": 820},
}

HTML = """<!doctype html><html><head><meta charset="utf-8">
<style>
  html,body{{margin:0;padding:0;background:#ffffff;}}
  #page{{
    width:{width}px; padding:{pad}px; box-sizing:border-box;
    font-family:'DejaVu Sans', Arial, sans-serif;
    font-size:{font}px; line-height:{lh}; color:#111111;
    text-align:justify;
  }}
</style></head><body><div id="page">{body}</div></body></html>"""


def main():
    manifest = json.loads((CORPUS / "corpus_truth.json").read_text(encoding="utf-8"))
    meta = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(device_scale_factor=1)
        for item in manifest:
            text = (CORPUS / item["file"]).read_text(encoding="utf-8")
            body = text.replace("&", "&amp;").replace("<", "&lt;")
            for preset, cfg in PRESETS.items():
                page.set_viewport_size({"width": cfg["width_px"], "height": 800})
                page.set_content(HTML.format(
                    width=cfg["width_px"], pad=cfg["pad_px"],
                    font=cfg["font_px"], lh=cfg["line_height"], body=body,
                ))
                out = IMG / f"text_{item['id']}_{preset}.png"
                page.screenshot(path=str(out), full_page=True)
                box = page.eval_on_selector("#page", "el => ({w: el.scrollWidth, h: el.scrollHeight})")
                meta.append({
                    "id": item["id"], "preset": preset, "file": out.name,
                    "width_px": box["w"], "height_px": box["h"],
                    "megapixels": round(box["w"] * box["h"] / 1_000_000, 3),
                })
                print(f"text_{item['id']}_{preset}.png  {box['w']}x{box['h']}px  {meta[-1]['megapixels']} MP")
        browser.close()
    (CORPUS / "render_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote corpus/render_meta.json")


if __name__ == "__main__":
    main()
