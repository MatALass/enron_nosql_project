"""
export_redis_data.py
--------------------
Redis charge directement depuis data/enriched/enron_enriched.json
(pas de format intermediaire necessaire). Ce script verifie simplement
que le fichier enrichi est present et calcule quelques statistiques
qui seront utilisees par load_redis.py.

Pour charger reellement dans Redis :
  1. Demarrer Redis :     docker run -d -p 6379:6379 redis:7-alpine
  2. Installer le client : pip install redis
  3. Lancer le chargement : python src/redis/load_redis.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from io_utils import load_enriched, project_root


def main():
    print("Verification du dataset enrichi pour Redis...")

    enriched_path = project_root() / "data" / "enriched" / "enron_enriched.json"
    if not enriched_path.exists():
        print(f"  [ERREUR] {enriched_path} introuvable.")
        print("           Lance d'abord src/common/prepare_enron.py.")
        sys.exit(1)

    docs = load_enriched()

    nb_geoloc = sum(1 for d in docs if d["location"]["city"])
    nb_finance = sum(1 for d in docs if d["has_finance_keywords"])
    senders = {d["sender"] for d in docs}
    recipients = {r for d in docs for r in d["all_recipients"]}

    print(f"  Documents          : {len(docs)}")
    print(f"  Senders uniques    : {len(senders)}")
    print(f"  Recipients uniques : {len(recipients)}")
    print(f"  Geolocalises       : {nb_geoloc}")
    print(f"  Finance keywords   : {nb_finance}")
    print()
    print(f"  Source pour Redis  : {enriched_path}")
    print(f"  Pour charger       : python src/redis/load_redis.py")


if __name__ == "__main__":
    main()
