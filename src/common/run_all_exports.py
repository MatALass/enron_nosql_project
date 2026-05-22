"""
run_all_exports.py
------------------
Point d'entrée principal du projet : exécute l'ensemble du pipeline.

1. Lance le nettoyage + enrichissement (prepare_enron.py)
2. Génère les exports pour chacune des 5 bases NoSQL

Utilisation depuis la racine du projet :
    python src/common/run_all_exports.py

Pour ne lancer qu'une étape :
    python src/common/prepare_enron.py
    python src/mongo/export_mongo.py
    python src/elasticsearch/export_elasticsearch.py
    python src/neo4j/export_neo4j.py
    python src/cassandra/export_cassandra.py
    python src/redis/export_redis_data.py
"""

import sys
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable  # même interpréteur que celui qui exécute ce script


STEPS = [
    ("Nettoyage + enrichissement",  "src/common/prepare_enron.py"),
    ("Export MongoDB",              "src/mongo/export_mongo.py"),
    ("Export Elasticsearch",        "src/elasticsearch/export_elasticsearch.py"),
    ("Export Neo4j",                "src/neo4j/export_neo4j.py"),
    ("Export Cassandra",            "src/cassandra/export_cassandra.py"),
    ("Export Redis (preparation)",  "src/redis/export_redis_data.py"),
]


def run_step(label, script_relative_path):
    script = PROJECT_ROOT / script_relative_path
    print()
    print("#" * 70)
    print(f"#  {label}")
    print(f"#  -> {script_relative_path}")
    print("#" * 70)

    result = subprocess.run(
        [PYTHON, str(script)],
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode != 0:
        print(f"\n[ERREUR] L'etape '{label}' a echoue (code {result.returncode}).")
        sys.exit(result.returncode)


def main():
    print("=" * 70)
    print(" Pipeline NoSQL Enron - run_all_exports")
    print("=" * 70)
    print(f" Racine projet : {PROJECT_ROOT}")
    print(f" Python        : {PYTHON}")
    print(f" Etapes        : {len(STEPS)}")

    for label, path in STEPS:
        run_step(label, path)

    print()
    print("=" * 70)
    print(" Toutes les etapes ont termine avec succes.")
    print("=" * 70)
    print()
    print(" Fichiers generes dans data/ :")
    print("   data/enriched/enron_enriched.json")
    print("   data/mongo/enron_mongo.json")
    print("   data/elasticsearch/enron_es.ndjson")
    print("   data/neo4j/*.csv          (7 fichiers)")
    print("   data/cassandra/*.csv      (4 fichiers)")
    print("   data/redis/                (charge depuis enriched/ via load_redis.py)")
    print()


if __name__ == "__main__":
    main()
