"""
load_redis.py
-------------
Charge le dataset enrichi dans une instance Redis locale en utilisant
exclusivement les primitives natives (HSET, SADD, ZINCRBY, GEOADD).

Strategie : Redis n'est pas un moteur de requetes. Pour pouvoir
"interroger" les donnees, on PRE-CALCULE les agregats au moment du
chargement (leaderboards, sets, compteurs, index geo).

Prerequis :
  docker run -d -p 6379:6379 redis:7-alpine
  pip install redis

Lancement (depuis la racine du projet) :
  python src/redis/load_redis.py

Structures creees :

  HASHES
    email:{id}                    -> tous les champs principaux du mail

  SORTED SETS (leaderboards)
    sender:count                  -> ZRANGEBYSCORE pour top senders
    recipient:count               -> top recipients
    pair:count                    -> top paires (sender|recipient)
    month:count                   -> distribution mensuelle
    city:count                    -> distribution par ville
    finance:count                 -> top senders d'emails finance

  SETS
    sender_emails:{addr}          -> ids des mails envoyes par cette adresse
    recipient_emails:{addr}       -> ids des mails recus
    domain_senders:{domain}       -> senders distincts par domaine

  GEO
    offices                       -> coordonnees lat/lon des villes
                                     (GEOSEARCH, GEORADIUS)
"""

import json
import sys
from pathlib import Path

try:
    import redis
except ImportError:
    print("Le module 'redis' n'est pas installe. Faites : pip install redis")
    sys.exit(1)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENRICHED = PROJECT_ROOT / "data" / "enriched" / "enron_enriched.json"


def main():
    if not ENRICHED.exists():
        print(f"[ERREUR] {ENRICHED} introuvable.")
        print("         Lance d'abord src/common/prepare_enron.py.")
        sys.exit(1)

    # Connexion
    print("Connexion a Redis (localhost:6379) ...")
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    try:
        r.ping()
    except redis.exceptions.ConnectionError:
        print("[ERREUR] Impossible de se connecter a Redis sur localhost:6379.")
        print("         Demarre Redis : docker run -d -p 6379:6379 redis:7-alpine")
        sys.exit(1)

    # Repart propre
    print("Flushdb...")
    r.flushdb()

    # Chargement
    print(f"Lecture de {ENRICHED} ...")
    with open(ENRICHED, encoding="utf-8") as f:
        docs = [json.loads(line) for line in f if line.strip()]
    print(f"  {len(docs)} documents")

    print("Chargement dans Redis (via pipeline) ...")
    pipe = r.pipeline()
    offices_added = set()

    for d in docs:
        eid = d["_id"]

        # 1. Hash de l'email (subject tronque pour limiter la taille)
        pipe.hset(f"email:{eid}", mapping={
            "sender":       d["sender"],
            "subject":      (d["subject"] or "")[:200],
            "date":         d["date"],
            "year_month":   d["year_month"],
            "direction":    d["direction"],
            "period":       d["period"] or "",
            "nb_recipients": d["nb_recipients_total"],
            "body_length":  d["body_length"],
            "city":         d["location"]["city"] or "",
            "has_finance":  "1" if d["has_finance_keywords"] else "0",
        })

        # 2. Leaderboards (sorted sets)
        pipe.zincrby("sender:count", 1, d["sender"])
        pipe.zincrby("month:count",  1, d["year_month"])
        if d["location"]["city"]:
            pipe.zincrby("city:count", 1, d["location"]["city"])
        if d["has_finance_keywords"]:
            pipe.zincrby("finance:count", 1, d["sender"])

        # 3. Sets : qui envoie / qui recoit
        pipe.sadd(f"sender_emails:{d['sender']}", eid)
        for rec in d["all_recipients"]:
            pipe.zincrby("recipient:count", 1, rec)
            pipe.sadd(f"recipient_emails:{rec}", eid)
            pipe.zincrby("pair:count", 1, f"{d['sender']}|{rec}")

        # 4. Domaines
        if d["sender_domain"]:
            pipe.sadd(f"domain_senders:{d['sender_domain']}", d["sender"])

        # 5. Index geo (une seule fois par ville)
        loc = d["location"]
        if loc["city"] and loc["city"] not in offices_added:
            pipe.geoadd("offices", (loc["lon"], loc["lat"], loc["city"]))
            offices_added.add(loc["city"])

    pipe.execute()

    # Resume
    print()
    print(f"OK - {len(docs)} emails charges.")
    print(f"     {len(offices_added)} villes geolocalisees (GEO 'offices').")
    print(f"     Cles totales dans Redis : {r.dbsize()}")


if __name__ == "__main__":
    main()
