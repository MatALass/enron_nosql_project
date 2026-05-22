"""
io_utils.py
-----------
Utilitaires partagés entre les scripts d'export par BDD.
"""

import csv
import json
from pathlib import Path


def project_root():
    """Racine du projet (deux niveaux au-dessus de src/common/)."""
    return Path(__file__).resolve().parents[2]


def load_enriched(enriched_path=None):
    """Charge le dataset enrichi en mémoire (liste de dicts)."""
    if enriched_path is None:
        enriched_path = project_root() / "data" / "enriched" / "enron_enriched.json"
    with open(enriched_path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, docs):
    """Écrit une liste de dicts au format JSON Lines."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")


def write_csv(path, rows, fieldnames):
    """Écrit une liste de dicts en CSV (toutes valeurs entre quotes pour Neo4j/Cassandra)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def clean_text_for_csv(text):
    """Supprime les retours à la ligne pour éviter de casser les CSV."""
    if not text:
        return ""
    return text.replace("\n", " ").replace("\r", " ")
