"""Produce 2 basic charts from results.json.

  fig_reduction.png : token reduction % vs text length (per image preset)
  fig_tokens.png    : input_tokens vs text length (text vs each preset)
"""
import json
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).parent
rows = json.loads((HERE / "results.json").read_text(encoding="utf-8"))

by_id = {}
for r in rows:
    by_id.setdefault(r["text_id"], {})[r["mode"]] = r

ids = sorted(by_id)
words = [by_id[i]["text"]["word_count"] for i in ids]

# ---- Chart 1: reduction % vs length ----
fig, ax = plt.subplots(figsize=(7, 4.2))
for mode, label, c in [("img_dense", "dense", "#1f77b4"), ("img_comfort", "comfortable", "#ff7f0e")]:
    y = [by_id[i][mode]["reduction_vs_text_pct"] for i in ids]
    ax.plot(words, y, marker="o", label=f"image ({label})", color=c)
ax.axhline(0, color="#888", lw=1, ls="--")
ax.set_xlabel("Longueur du texte (mots)")
ax.set_ylabel("Réduction de tokens vs texte brut (%)")
ax.set_title("Réduction de tokens en entrée : image vs texte")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(HERE / "fig_reduction.png", dpi=120)

# ---- Chart 2: input_tokens vs length ----
fig, ax = plt.subplots(figsize=(7, 4.2))
for mode, label, c in [("text", "texte brut", "#2ca02c"),
                       ("img_dense", "image dense", "#1f77b4"),
                       ("img_comfort", "image comfortable", "#ff7f0e")]:
    y = [by_id[i][mode]["input_tokens"] for i in ids]
    ax.plot(words, y, marker="o", label=label, color=c)
ax.set_xlabel("Longueur du texte (mots)")
ax.set_ylabel("input_tokens réels (API)")
ax.set_title("Coût en tokens d'entrée selon la longueur")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(HERE / "fig_tokens.png", dpi=120)
print("wrote fig_reduction.png + fig_tokens.png")
