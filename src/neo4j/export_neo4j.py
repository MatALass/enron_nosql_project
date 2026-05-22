"""
export_neo4j.py
---------------
Export du dataset enrichi au format Neo4j (CSV multiples).

Modele de graphe :

  (:Person {email, domain})
       -[:SENT]->          (:Email {id, subject, date, ...})
                              -[:TO]->        (:Person)
                              -[:CC]->        (:Person)
                              -[:LOCATED_AT]->(:Office {city, region, country, lat, lon})

Fichiers produits (CSV avec entetes, valeurs entre quotes) :
  - nodes_persons.csv     : noeuds Person (email, domain)
  - nodes_emails.csv      : noeuds Email (sans body, pour ne pas surcharger)
  - nodes_offices.csv     : noeuds Office (= villes uniques)
  - edges_sent.csv        : Person -[SENT]-> Email
  - edges_to.csv          : Email -[TO]-> Person
  - edges_cc.csv          : Email -[CC]-> Person
  - edges_located_at.csv  : Email -[LOCATED_AT]-> Office

Import dans Neo4j (commandes Cypher) :

  // 1. Contraintes d'unicite (a creer AVANT les LOAD CSV)
  CREATE CONSTRAINT person_email IF NOT EXISTS
    FOR (p:Person) REQUIRE p.email IS UNIQUE;
  CREATE CONSTRAINT email_id IF NOT EXISTS
    FOR (e:Email)  REQUIRE e.id IS UNIQUE;
  CREATE CONSTRAINT office_city IF NOT EXISTS
    FOR (o:Office) REQUIRE o.city IS UNIQUE;

  // 2. Noeuds
  LOAD CSV WITH HEADERS FROM 'file:///nodes_persons.csv' AS row
  CREATE (:Person {email: row.email, domain: row.domain});

  LOAD CSV WITH HEADERS FROM 'file:///nodes_offices.csv' AS row
  CREATE (:Office {
    city: row.city, region: row.region, country: row.country,
    lat: toFloat(row.lat), lon: toFloat(row.lon)
  });

  LOAD CSV WITH HEADERS FROM 'file:///nodes_emails.csv' AS row
  CREATE (:Email {
    id: row.id, subject: row.subject, date: datetime(row.date),
    year: toInteger(row.year), month: toInteger(row.month),
    body_length: toInteger(row.body_length),
    direction: row.direction, period: row.period,
    is_reply: row.is_reply = 'True',
    is_forward: row.is_forward = 'True',
    has_finance_keywords: row.has_finance_keywords = 'True',
    nb_recipients_total: toInteger(row.nb_recipients_total)
  });

  // 3. Relations
  LOAD CSV WITH HEADERS FROM 'file:///edges_sent.csv' AS row
  MATCH (p:Person {email: row.sender}), (e:Email {id: row.email_id})
  CREATE (p)-[:SENT]->(e);

  LOAD CSV WITH HEADERS FROM 'file:///edges_to.csv' AS row
  MATCH (e:Email {id: row.email_id}), (p:Person {email: row.recipient})
  CREATE (e)-[:TO]->(p);

  LOAD CSV WITH HEADERS FROM 'file:///edges_cc.csv' AS row
  MATCH (e:Email {id: row.email_id}), (p:Person {email: row.recipient})
  CREATE (e)-[:CC]->(p);

  LOAD CSV WITH HEADERS FROM 'file:///edges_located_at.csv' AS row
  MATCH (e:Email {id: row.email_id}), (o:Office {city: row.city})
  CREATE (e)-[:LOCATED_AT]->(o);
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from io_utils import load_enriched, write_csv, clean_text_for_csv, project_root


def build_entities(docs):
    """
    Collecte les entites uniques et les arcs a partir des documents enrichis.
    Retourne un tuple (persons, emails, offices, edges_sent, edges_to,
                       edges_cc, edges_located).
    """
    persons       = {}   # email -> {email, domain}
    emails        = {}   # id    -> dict
    offices       = {}   # city  -> dict
    edges_sent    = []
    edges_to      = []
    edges_cc      = []
    edges_located = []

    for d in docs:
        # Noeuds Person (sender + tous les destinataires)
        for e in [d["sender"]] + d["all_recipients"]:
            if e and e not in persons:
                persons[e] = {
                    "email":  e,
                    "domain": e.split("@", 1)[1] if "@" in e else "",
                }

        # Noeud Email (sans body complet pour limiter la taille)
        emails[d["_id"]] = {
            "id":                   d["_id"],
            "subject":              clean_text_for_csv(d["subject"]),
            "date":                 d["date"],
            "year":                 d["year"],
            "month":                d["month"],
            "body_length":          d["body_length"],
            "direction":            d["direction"],
            "period":               d["period"] or "",
            "is_reply":             d["is_reply"],
            "is_forward":           d["is_forward"],
            "has_finance_keywords": d["has_finance_keywords"],
            "nb_recipients_total":  d["nb_recipients_total"],
        }

        # Noeud Office (=ville, dedupliquee)
        loc = d["location"]
        if loc["city"]:
            offices[loc["city"]] = {
                "city":    loc["city"],
                "region":  loc["region"],
                "country": loc["country"],
                "lat":     loc["lat"],
                "lon":     loc["lon"],
            }
            edges_located.append({"email_id": d["_id"], "city": loc["city"]})

        # Relations
        edges_sent.append({"sender": d["sender"], "email_id": d["_id"]})
        for r in d["recipients"]:
            edges_to.append({"email_id": d["_id"], "recipient": r})
        for r in d["cc"]:
            edges_cc.append({"email_id": d["_id"], "recipient": r})

    return (persons, emails, offices,
            edges_sent, edges_to, edges_cc, edges_located)


def main():
    print("Export Neo4j en cours...")

    docs = load_enriched()
    persons, emails, offices, e_sent, e_to, e_cc, e_loc = build_entities(docs)

    out_dir = project_root() / "data" / "neo4j"

    write_csv(out_dir / "nodes_persons.csv",
              persons.values(),
              ["email", "domain"])

    write_csv(out_dir / "nodes_emails.csv",
              emails.values(),
              ["id", "subject", "date", "year", "month", "body_length",
               "direction", "period", "is_reply", "is_forward",
               "has_finance_keywords", "nb_recipients_total"])

    write_csv(out_dir / "nodes_offices.csv",
              offices.values(),
              ["city", "region", "country", "lat", "lon"])

    write_csv(out_dir / "edges_sent.csv",       e_sent, ["sender", "email_id"])
    write_csv(out_dir / "edges_to.csv",         e_to,   ["email_id", "recipient"])
    write_csv(out_dir / "edges_cc.csv",         e_cc,   ["email_id", "recipient"])
    write_csv(out_dir / "edges_located_at.csv", e_loc,  ["email_id", "city"])

    print(f"  Persons    : {len(persons)}")
    print(f"  Emails     : {len(emails)}")
    print(f"  Offices    : {len(offices)}")
    print(f"  SENT       : {len(e_sent)}")
    print(f"  TO         : {len(e_to)}")
    print(f"  CC         : {len(e_cc)}")
    print(f"  LOCATED_AT : {len(e_loc)}")
    print(f"  Dossier    : {out_dir}")


if __name__ == "__main__":
    main()
