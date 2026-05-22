# Projet NoSQL — Dataset Enron

Pipeline d'import du dataset **Enron** (corpus d'emails de Kenneth Lay, ~5900 mails) vers les **5 bases NoSQL** : MongoDB, Elasticsearch, Neo4j, Cassandra, Redis.

## Structure

```
enron_nosql_project/
├── README.md
├── pyproject.toml
├── .gitignore
├── data/
│   ├── raw/                  # Dataset original (versionné)
│   │   └── enron.json
│   ├── enriched/             # Fichier intermédiaire commun (généré)
│   │   └── enron_enriched.json
│   ├── mongo/                # Exports MongoDB (généré)
│   ├── elasticsearch/        # Exports Elasticsearch (généré)
│   ├── neo4j/                # Exports Neo4j en CSV (généré)
│   ├── cassandra/            # Exports Cassandra en CSV (généré)
│   └── redis/                # Redis charge directement depuis enriched/
└── src/
    ├── common/               # Code partagé entre toutes les BDD
    │   ├── referentiels.py       # Mapping bureaux/domaines/mots-clés
    │   ├── prepare_enron.py      # Nettoyage + enrichissement
    │   ├── io_utils.py           # Helpers I/O
    │   └── run_all_exports.py    # Equivalent au main.py (lancer ce fichier pour charger tous les datasets)
    ├── mongo/
    │   └── export_mongo.py
    ├── elasticsearch/
    │   └── export_elasticsearch.py
    ├── neo4j/
    │   └── export_neo4j.py
    ├── cassandra/
    │   └── export_cassandra.py
    └── redis/
        ├── export_redis_data.py  # Vérification + stats
        └── load_redis.py         # Chargement effectif dans Redis
```

## Installation

```powershell
# Cloner / décompresser le projet
cd enron_nosql_project

# Créer un venv (recommandé)
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
# ou : source .venv/bin/activate  (Linux/Mac)

# Installer les dépendances
pip install -e .
```

Pour installer les librairies Python requises  :

```powershell
pip install -e ".[all]"
```

## Utilisation

### Générer tous les exports d'un coup

```powershell
python src/common/run_all_exports.py
```

Cela exécute dans l'ordre :
1. `prepare_enron.py` → produit `data/enriched/enron_enriched.json`
2. `export_mongo.py` → `data/mongo/enron_mongo.json`
3. `export_elasticsearch.py` → `data/elasticsearch/enron_es.ndjson` + `mapping.json`
4. `export_neo4j.py` → 7 CSV dans `data/neo4j/`
5. `export_cassandra.py` → 4 CSV dans `data/cassandra/`
6. `export_redis_data.py` → vérification + stats

### Ou lancer chaque étape séparément

```powershell
python src/common/prepare_enron.py
python src/mongo/export_mongo.py
python src/elasticsearch/export_elasticsearch.py
python src/neo4j/export_neo4j.py
python src/cassandra/export_cassandra.py
python src/redis/export_redis_data.py
```

## Import dans chaque base

### MongoDB

```bash
mongoimport --db enron --collection emails --file data/mongo/enron_mongo.json
```

Puis dans `mongosh` :
```javascript
db.emails.createIndex({ location: "2dsphere" })
db.emails.createIndex({ sender: 1 })
db.emails.createIndex({ year_month: 1 })
```

### Elasticsearch

```bash
# 1. Créer l'index avec le mapping
curl -X PUT "localhost:9200/enron_emails" \
  -H "Content-Type: application/json" \
  -d @data/elasticsearch/mapping.json

# 2. Bulk import
curl -X POST "localhost:9200/_bulk" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @data/elasticsearch/enron_es.ndjson
```

### Neo4j

Voir le docstring de `src/neo4j/export_neo4j.py` pour les commandes Cypher complètes (`CREATE CONSTRAINT` + `LOAD CSV`).

### Cassandra

Voir le docstring de `src/cassandra/export_cassandra.py` pour les schémas CQL et les `COPY FROM`.

### Redis

```powershell
# 1. Démarrer Redis
docker run -d -p 6379:6379 redis:7-alpine

# 2. Charger
python src/redis/load_redis.py
```

## Modifications appliquées au dataset

**Nettoyage :**
- Normalisation des adresses email (lowercase, trim, déduplication)
- Application d'alias (`klay@enron.com` → `kenneth.lay@enron.com`)
- Filtrage des adresses techniques (`no.address@enron.com`)
- Parsing de la date string vers ISO 8601 + extraction year/month/day/hour/weekday
- Nettoyage du body (whitespaces excessifs)

**Enrichissement :**
- **Géolocalisation** par inférence depuis le sender (sigles de bureaux dans les bodies pour les `@enron.com`, mapping domaine→siège pour les externes). 71,5 % des emails géolocalisés ; les autres marqués `unknown` et exclus des requêtes géo.
- **Direction** du mail (`internal` / `outbound` / `inbound` / `mixed`)
- **Période narrative** (`pre_scandal` / `scandal` / `post_collapse`)
- **Mots-clés financiers** (24 termes liés au scandale Enron, avec word boundaries pour éviter les faux positifs)
- **Flags** : `is_reply`, `is_forward`, `is_mass_email`
- **Compteurs** : `nb_recipients_total`, `body_length`

**Bilan d'import :**

| Métrique | Valeur |
|---|---|
| Lignes JSON lues | 5929 |
| Adresses techniques filtrées | 47 |
| Documents écrits | 5882 |
| Géoloc résolue | 4206 (71,5 %) |
| Géoloc unknown | 1676 (28,5 %) |