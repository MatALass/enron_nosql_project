"""
export_mongo.py
---------------
Export du dataset enrichi au format MongoDB.

Format de sortie :
  - JSON Lines (compatible mongoimport)
  - Le champ 'location' est converti en GeoJSON Point :
    { "type": "Point", "coordinates": [lon, lat] }
    pour permettre la creation d'un index 2dsphere et l'utilisation des
    operateurs geospatiaux ($geoWithin, $near, $geoIntersects).

Import dans MongoDB :
  mongoimport --db enron --collection emails \
              --file data/mongo/enron_mongo.json

Index recommandes apres import (dans mongosh) :
  db.emails.createIndex({ location: "2dsphere" })
  db.emails.createIndex({ sender: 1 })
  db.emails.createIndex({ date: 1 })
  db.emails.createIndex({ year_month: 1 })
  db.emails.createIndex({ "location.country": 1, "location.city": 1 })
"""

import sys
from pathlib import Path

# Import du module commun (chemin relatif depuis src/mongo/)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from io_utils import load_enriched, write_jsonl, project_root


def to_mongo(d):
    """Transforme un document enrichi en document MongoDB."""
    doc = dict(d)
    loc = d["location"]
    if loc["lat"] is not None and loc["lon"] is not None:
        # GeoJSON Point : ordre [longitude, latitude] (impose par la spec GeoJSON)
        doc["location"] = {
            "type":        "Point",
            "coordinates": [loc["lon"], loc["lat"]],
            "city":        loc["city"],
            "region":      loc["region"],
            "country":     loc["country"],
            "source":      loc["source"],
        }
    else:
        doc["location"] = None
    return doc


def main():
    print("Export MongoDB en cours...")

    docs = load_enriched()
    mongo_docs = [to_mongo(d) for d in docs]

    out_path = project_root() / "data" / "mongo" / "enron_mongo.json"
    write_jsonl(out_path, mongo_docs)

    print(f"  Documents exportes : {len(mongo_docs)}")
    print(f"  Fichier            : {out_path}")


if __name__ == "__main__":
    main()
