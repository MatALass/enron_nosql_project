"""
export_elasticsearch.py
-----------------------
Export du dataset enrichi au format Elasticsearch.

Format de sortie :
  - NDJSON (newline-delimited JSON) compatible avec l'API Bulk d'Elasticsearch.
  - Alternance de lignes action/document.
  - Le champ 'location' est converti en geo_point natif ES :
    { "lat": <float>, "lon": <float>, ... }

Import dans Elasticsearch :
  # 1. Creer l'index avec le bon mapping (necessaire pour geo_point et text)
  curl -X PUT "localhost:9200/enron_emails" -H "Content-Type: application/json" \
       -d @data/elasticsearch/mapping.json

  # 2. Bulk import
  curl -X POST "localhost:9200/_bulk" -H "Content-Type: application/x-ndjson" \
       --data-binary @data/elasticsearch/enron_es.ndjson
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from io_utils import load_enriched, project_root


INDEX_NAME = "enron_emails"


# Mapping recommande pour ES (a creer AVANT l'import du NDJSON)
ES_MAPPING = {
    "mappings": {
        "properties": {
            "sender":           {"type": "keyword"},
            "sender_domain":    {"type": "keyword"},
            "recipients":       {"type": "keyword"},
            "cc":               {"type": "keyword"},
            "bcc":              {"type": "keyword"},
            "all_recipients":   {"type": "keyword"},
            "subject":          {"type": "text"},
            "body":             {"type": "text"},
            "body_length":      {"type": "integer"},
            "date":             {"type": "date"},
            "year":             {"type": "integer"},
            "month":            {"type": "integer"},
            "day":              {"type": "integer"},
            "hour":             {"type": "integer"},
            "weekday":          {"type": "integer"},
            "year_month":       {"type": "keyword"},
            "folder":           {"type": "keyword"},
            "nb_recipients":        {"type": "integer"},
            "nb_cc":                {"type": "integer"},
            "nb_bcc":               {"type": "integer"},
            "nb_recipients_total":  {"type": "integer"},
            "is_mass_email":        {"type": "boolean"},
            "direction":            {"type": "keyword"},
            "period":               {"type": "keyword"},
            "is_reply":             {"type": "boolean"},
            "is_forward":           {"type": "boolean"},
            "has_finance_keywords": {"type": "boolean"},
            "finance_keywords":     {"type": "keyword"},
            "location": {
                "properties": {
                    # geo_point pour les requetes geospatiales
                    "coord":   {"type": "geo_point"},
                    "city":    {"type": "keyword"},
                    "region":  {"type": "keyword"},
                    "country": {"type": "keyword"},
                    "source":  {"type": "keyword"},
                }
            }
        }
    }
}


def to_es(d):
    """Transforme un document enrichi en document ES."""
    doc = dict(d)
    loc = d["location"]
    if loc["lat"] is not None and loc["lon"] is not None:
        doc["location"] = {
            "coord":   {"lat": loc["lat"], "lon": loc["lon"]},
            "city":    loc["city"],
            "region":  loc["region"],
            "country": loc["country"],
            "source":  loc["source"],
        }
    else:
        doc["location"] = None
    return doc


def write_bulk(path, docs):
    """Ecrit le fichier NDJSON au format bulk API."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for d in docs:
            # Ligne 1 : action
            action = {"index": {"_index": INDEX_NAME, "_id": d["_id"]}}
            f.write(json.dumps(action) + "\n")
            # Ligne 2 : document
            f.write(json.dumps(d, ensure_ascii=False) + "\n")


def write_mapping(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ES_MAPPING, f, indent=2)


def main():
    print("Export Elasticsearch en cours...")

    docs = load_enriched()
    es_docs = [to_es(d) for d in docs]

    out_dir = project_root() / "data" / "elasticsearch"
    bulk_path    = out_dir / "enron_es.ndjson"
    mapping_path = out_dir / "mapping.json"

    write_bulk(bulk_path, es_docs)
    write_mapping(mapping_path)

    print(f"  Documents exportes : {len(es_docs)}")
    print(f"  Fichier bulk       : {bulk_path}")
    print(f"  Mapping            : {mapping_path}")


if __name__ == "__main__":
    main()
