"""Build 5 French test texts of increasing length.

Each text embeds the SAME 5 structured fields (ground truth) inside prose,
so extraction reliability can be scored exactly against known values.
Output: corpus/text_1..5.txt  +  corpus/corpus_truth.json
"""
import json
import pathlib
import textwrap

HERE = pathlib.Path(__file__).parent
CORPUS = HERE / "corpus"
CORPUS.mkdir(exist_ok=True)

# Ground truth per text (5 keys). Distinct values so a model cannot "guess".
TRUTHS = [
    {"nom_client": "Boulangerie Lefevre",       "date_facture": "2024-03-14", "montant_total": "1 284,50 €", "reference_contrat": "CT-2024-0817", "date_echeance": "2024-04-13"},
    {"nom_client": "Garage Moreau & Fils",       "date_facture": "2023-11-02", "montant_total": "7 940,00 €", "reference_contrat": "CT-2023-1149", "date_echeance": "2023-12-02"},
    {"nom_client": "Cabinet d'architecture Rey",  "date_facture": "2024-06-27", "montant_total": "23 615,80 €","reference_contrat": "CT-2024-0342", "date_echeance": "2024-08-11"},
    {"nom_client": "Pharmacie du Vieux Port",     "date_facture": "2025-01-09", "montant_total": "512,30 €",   "reference_contrat": "CT-2025-0006", "date_echeance": "2025-02-08"},
    {"nom_client": "Transports Baptiste Girard",  "date_facture": "2024-09-30", "montant_total": "148 200,00 €","reference_contrat": "CT-2024-1802","date_echeance": "2024-11-14"},
]

# Neutral French filler sentences (no numbers that clash with the fields).
FILLER = [
    "La réunion de suivi a permis de clarifier les attentes de chaque partie prenante.",
    "Les équipes techniques ont confirmé la disponibilité des ressources nécessaires.",
    "Un compte rendu détaillé sera transmis aux responsables concernés dans les meilleurs délais.",
    "Les conditions générales de vente restent applicables pour l'ensemble des prestations.",
    "Nous vous remercions de la confiance renouvelée que vous accordez à nos services.",
    "Le calendrier prévisionnel tient compte des périodes de congés annoncées.",
    "Les livrables intermédiaires feront l'objet d'une validation formelle avant diffusion.",
    "Toute modification du périmètre devra être approuvée par écrit par les deux parties.",
    "Le service client reste joignable pour répondre à vos éventuelles interrogations.",
    "La qualité des matériaux employés respecte les normes en vigueur sur le marché.",
    "Un point d'avancement hebdomadaire est organisé afin de suivre le déroulement.",
    "Les procédures internes garantissent la traçabilité de chaque étape du dossier.",
]

# ~ target word counts
TARGETS = [100, 300, 600, 1200, 3000]


def build_text(truth, target_words):
    intro = (
        f"Note de synthèse commerciale rédigée à l'attention de notre client "
        f"{truth['nom_client']}. Le présent document récapitule les éléments "
        f"contractuels et financiers du dossier en cours."
    )
    embed = (
        f"La facture correspondante a été émise le {truth['date_facture']} pour "
        f"un montant total de {truth['montant_total']}, toutes taxes comprises. "
        f"Elle se rattache au contrat de référence {truth['reference_contrat']}, "
        f"signé antérieurement par les deux parties. Le règlement devra nous "
        f"parvenir au plus tard le {truth['date_echeance']}, date d'échéance "
        f"ferme au-delà de laquelle des pénalités de retard pourront s'appliquer."
    )
    parts = [intro, embed]
    i = 0
    while sum(len(p.split()) for p in parts) < target_words:
        parts.append(FILLER[i % len(FILLER)])
        i += 1
    return " ".join(parts)


def main():
    manifest = []
    for idx, (truth, target) in enumerate(zip(TRUTHS, TARGETS), start=1):
        text = build_text(truth, target)
        path = CORPUS / f"text_{idx}.txt"
        path.write_text(text, encoding="utf-8")
        wc = len(text.split())
        manifest.append({
            "id": idx,
            "file": path.name,
            "word_count": wc,
            "char_count": len(text),
            "truth": truth,
        })
        print(f"text_{idx}.txt  target={target:>4}  words={wc:>4}")
    (CORPUS / "corpus_truth.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("wrote corpus/corpus_truth.json")


if __name__ == "__main__":
    main()
