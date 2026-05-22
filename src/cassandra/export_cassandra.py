"""
export_cassandra.py
-------------------
Export du dataset enrichi au format Cassandra (CSV multiples).

Principe : Cassandra impose une modelisation orientee requetes
(query-first design). On produit donc plusieurs tables denormalisees,
chacune optimisee pour un type de requete attendu.

Schemas (a creer AVANT l'import) :

  CREATE KEYSPACE enron WITH replication =
    {'class': 'SimpleStrategy', 'replication_factor': 1};

  USE enron;

  -- Q : emails envoyes par un sender (les plus recents d'abord)
  CREATE TABLE emails_by_sender (
    sender text,
    date timestamp,
    email_id text,
    subject text,
    nb_recipients int,
    city text,
    direction text,
    period text,
    PRIMARY KEY (sender, date, email_id)
  ) WITH CLUSTERING ORDER BY (date DESC, email_id ASC);

  -- Q : emails recus par un recipient
  CREATE TABLE emails_by_recipient (
    recipient text,
    date timestamp,
    email_id text,
    sender text,
    subject text,
    direction text,
    period text,
    PRIMARY KEY (recipient, date, email_id)
  ) WITH CLUSTERING ORDER BY (date DESC, email_id ASC);

  -- Q : emails sur un mois donne
  CREATE TABLE emails_by_month (
    year_month text,
    date timestamp,
    email_id text,
    sender text,
    subject text,
    nb_recipients int,
    city text,
    PRIMARY KEY (year_month, date, email_id)
  ) WITH CLUSTERING ORDER BY (date DESC, email_id ASC);

  -- Q : emails envoyes depuis une ville (geoloc)
  CREATE TABLE emails_by_city (
    city text,
    date timestamp,
    email_id text,
    country text,
    lat double,
    lon double,
    sender text,
    subject text,
    PRIMARY KEY (city, date, email_id)
  ) WITH CLUSTERING ORDER BY (date DESC, email_id ASC);

Import via cqlsh :
  COPY emails_by_sender (sender, date, email_id, subject, nb_recipients, city, direction, period)
       FROM 'data/cassandra/emails_by_sender.csv' WITH HEADER = TRUE;
  -- etc. pour les autres tables
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from io_utils import load_enriched, write_csv, clean_text_for_csv, project_root


def build_tables(docs):
    """Construit les 4 tables denormalisees depuis le dataset enrichi."""
    by_sender    = []
    by_recipient = []
    by_month     = []
    by_city      = []

    for d in docs:
        subj = clean_text_for_csv(d["subject"])
        city = d["location"]["city"] or ""

        # Table 1 : emails_by_sender
        by_sender.append({
            "sender":        d["sender"],
            "date":          d["date"],
            "email_id":      d["_id"],
            "subject":       subj,
            "nb_recipients": d["nb_recipients_total"],
            "city":          city,
            "direction":     d["direction"],
            "period":        d["period"] or "",
        })

        # Table 2 : emails_by_recipient (un row par destinataire = denormalisation)
        for r in d["all_recipients"]:
            by_recipient.append({
                "recipient": r,
                "date":      d["date"],
                "email_id":  d["_id"],
                "sender":    d["sender"],
                "subject":   subj,
                "direction": d["direction"],
                "period":    d["period"] or "",
            })

        # Table 3 : emails_by_month
        by_month.append({
            "year_month":    d["year_month"],
            "date":          d["date"],
            "email_id":      d["_id"],
            "sender":        d["sender"],
            "subject":       subj,
            "nb_recipients": d["nb_recipients_total"],
            "city":          city,
        })

        # Table 4 : emails_by_city (seulement les emails geolocalises)
        if d["location"]["city"]:
            by_city.append({
                "city":     d["location"]["city"],
                "country":  d["location"]["country"],
                "lat":      d["location"]["lat"],
                "lon":      d["location"]["lon"],
                "date":     d["date"],
                "email_id": d["_id"],
                "sender":   d["sender"],
                "subject":  subj,
            })

    return by_sender, by_recipient, by_month, by_city


def main():
    print("Export Cassandra en cours...")

    docs = load_enriched()
    by_sender, by_recipient, by_month, by_city = build_tables(docs)

    out_dir = project_root() / "data" / "cassandra"

    write_csv(out_dir / "emails_by_sender.csv", by_sender,
              ["sender", "date", "email_id", "subject", "nb_recipients",
               "city", "direction", "period"])

    write_csv(out_dir / "emails_by_recipient.csv", by_recipient,
              ["recipient", "date", "email_id", "sender", "subject",
               "direction", "period"])

    write_csv(out_dir / "emails_by_month.csv", by_month,
              ["year_month", "date", "email_id", "sender", "subject",
               "nb_recipients", "city"])

    write_csv(out_dir / "emails_by_city.csv", by_city,
              ["city", "country", "lat", "lon", "date", "email_id",
               "sender", "subject"])

    print(f"  emails_by_sender    : {len(by_sender)} rows")
    print(f"  emails_by_recipient : {len(by_recipient)} rows (denormalise)")
    print(f"  emails_by_month     : {len(by_month)} rows")
    print(f"  emails_by_city      : {len(by_city)} rows")
    print(f"  Dossier             : {out_dir}")


if __name__ == "__main__":
    main()
