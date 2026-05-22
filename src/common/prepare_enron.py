"""
prepare_enron.py
----------------
Pipeline de préparation du dataset Enron pour import dans les 5 bases NoSQL
(MongoDB, Elasticsearch, Neo4j, Cassandra, Redis).

Entrée  : data/raw/enron.json           (JSON Lines, 5929 docs bruts)
Sortie  : data/enriched/enron_enriched.json (JSON Lines, docs enrichis)

Transformations appliquées (chacune justifiée dans le rapport) :

  [NETTOYAGE]
  1. Normalisation des adresses email (lowercase, trim, déduplication)
  2. Application des alias connus (klay@enron.com -> kenneth.lay@enron.com)
  3. Filtrage des adresses techniques (no.address@enron.com, ...)
  4. Parsing de la date string vers ISO 8601 + extraction des composantes
  5. Nettoyage du body (whitespaces excessifs)

  [ENRICHISSEMENT]
  6. Géolocalisation par inférence depuis le sender (referentiels.py)
  7. Extraction du domaine du sender
  8. Calcul de la direction (internal / inbound / outbound / mixed)
  9. Détection des mass emails (>10 destinataires)
 10. Détection des mots-clés financiers (avec word boundaries)
 11. Détection des forward/reply
 12. Tagging par période narrative (pre_scandal / scandal / post_collapse)
 13. Compteurs utiles (nb_recipients_total, body_length, etc.)
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from referentiels import (
    ENRON_OFFICES, ENRON_DEFAULT_OFFICE, EXTERNAL_DOMAINS,
    FINANCE_KEYWORDS, EMAIL_ALIASES, JUNK_ADDRESSES, PERIODS,
)

# Pré-compilation des regex
RE_OFFICE_TAG      = re.compile(r"/(HOU|LON|NYC|NY|OSL|CAL|PDX)/", re.IGNORECASE)
RE_REPLY_SUBJECT   = re.compile(r"^\s*(re|réf|réponse)\s*:", re.IGNORECASE)
RE_FORWARD_SUBJECT = re.compile(r"^\s*(fw|fwd|tr)\s*:", re.IGNORECASE)
RE_FORWARD_BODY    = re.compile(r"-+\s*original message\s*-+", re.IGNORECASE)
RE_WHITESPACE      = re.compile(r"[ \t]+")
RE_NEWLINES        = re.compile(r"\n{3,}")


# =============================================================================
# 1. Nettoyage des adresses email
# =============================================================================
def normalize_email(addr):
    """Lowercase + trim + alias + filtrage des junk addresses."""
    if not addr:
        return None
    addr = addr.strip().lower()
    if addr in JUNK_ADDRESSES:
        return None
    return EMAIL_ALIASES.get(addr, addr)


def normalize_list(lst):
    """Normalise une liste d'emails (déduplication, suppression des None)."""
    if not lst:
        return []
    out, seen = [], set()
    for a in lst:
        n = normalize_email(a)
        if n and n not in seen:
            out.append(n)
            seen.add(n)
    return out


def get_domain(email):
    """Extrait le domaine d'une adresse email."""
    if not email or "@" not in email:
        return None
    return email.split("@", 1)[1]


# =============================================================================
# 2. Parsing de date
# =============================================================================
def parse_date(date_str):
    """
    Format dataset : '2000-01-12 08:24:00-08:00'
    Retourne (iso, year, month, day, hour, weekday) ou (None,)*6.
    weekday : 0=lundi, 6=dimanche.
    """
    if not date_str:
        return None, None, None, None, None, None
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.isoformat(), dt.year, dt.month, dt.day, dt.hour, dt.weekday()
    except (ValueError, TypeError):
        return None, None, None, None, None, None


def get_period(date_iso):
    """Retourne le label de période en fonction de la date."""
    if not date_iso:
        return None
    for label, start, end in PERIODS:
        if start <= date_iso[:10] < end:
            return label
    return None


# =============================================================================
# 3. Nettoyage du body
# =============================================================================
def clean_body(text):
    """Supprime les whitespaces excessifs."""
    if not text:
        return ""
    text = RE_NEWLINES.sub("\n\n", text)
    text = RE_WHITESPACE.sub(" ", text)
    return text.strip()


# =============================================================================
# 4. Inférence de la géolocalisation
# =============================================================================
def infer_location(sender, body):
    """
    Stratégie :
      - sender @enron.com : chercher un sigle de bureau (HOU/LON/...) dans le
        body. Sinon, retomber sur le siège de Houston.
      - sender domaine connu : utiliser EXTERNAL_DOMAINS.
      - sinon : 'unknown' (exclu des requêtes géo).
    """
    domain = get_domain(sender)
    if not domain:
        return _unknown_location()

    if domain == "enron.com":
        match = RE_OFFICE_TAG.search(body or "")
        if match:
            code = match.group(1).upper()
            if code in ENRON_OFFICES:
                return _enrich_location(ENRON_OFFICES[code], "body_office_tag")
        return _enrich_location(ENRON_OFFICES[ENRON_DEFAULT_OFFICE], "enron_default")

    if domain in EXTERNAL_DOMAINS:
        return _enrich_location(EXTERNAL_DOMAINS[domain], "external_domain")

    return _unknown_location()


def _enrich_location(loc, source):
    return {
        "city": loc["city"], "region": loc["region"], "country": loc["country"],
        "lat":  loc["lat"],  "lon":    loc["lon"],
        "source": source,
    }


def _unknown_location():
    return {
        "city": None, "region": None, "country": None,
        "lat": None, "lon": None, "source": "unknown",
    }


# =============================================================================
# 5. Détection des mots-clés financiers
# =============================================================================
def detect_finance_keywords(subject, body):
    """
    Détection avec word boundaries pour éviter les faux positifs
    (ex : 'sec' qui matcherait 'second', 'sector', 'secure').
    """
    text = ((subject or "") + " " + (body or "")).lower()
    found = []
    for kw in FINANCE_KEYWORDS:
        if " " in kw:
            # Mots-clés multi-tokens : recherche directe
            if kw in text:
                found.append(kw)
        else:
            # Mots simples : word boundary
            if re.search(r"\b" + re.escape(kw) + r"\b", text):
                found.append(kw)
    return sorted(found)


# =============================================================================
# 6. Direction du mail
# =============================================================================
def compute_direction(sender, all_recipients):
    """
    internal : tout @enron.com des deux côtés
    outbound : sender @enron.com, au moins un destinataire externe
    inbound  : sender externe, au moins un destinataire @enron.com
    mixed    : sender externe et tous destinataires externes
    """
    sender_is_enron = (get_domain(sender) == "enron.com")
    recs_enron      = [r for r in all_recipients if get_domain(r) == "enron.com"]
    recs_external   = [r for r in all_recipients if get_domain(r) != "enron.com"]

    if sender_is_enron and not recs_external:
        return "internal"
    if sender_is_enron and recs_external:
        return "outbound"
    if not sender_is_enron and recs_enron:
        return "inbound"
    return "mixed"


# =============================================================================
# 7. Pipeline principal
# =============================================================================
def process(input_path, output_path):
    """Lit input_path (JSON Lines brut) et écrit output_path (JSON Lines enrichi)."""
    stats = {
        "lignes_lues": 0,
        "ignorees_json_invalide": 0,
        "ignorees_sender_absent": 0,
        "ignorees_sender_junk": 0,
        "ignorees_date_invalide": 0,
        "ecrites": 0,
        "geoloc_resolue": 0,
        "geoloc_unknown": 0,
    }

    # Crée le dossier parent si nécessaire
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:

        for line in fin:
            line = line.strip()
            if not line:
                continue
            stats["lignes_lues"] += 1

            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                stats["ignorees_json_invalide"] += 1
                continue

            # --- Nettoyage adresses ---
            raw_sender = doc.get("sender")
            sender = normalize_email(raw_sender)
            if not sender:
                if raw_sender and raw_sender.strip().lower() in JUNK_ADDRESSES:
                    stats["ignorees_sender_junk"] += 1
                else:
                    stats["ignorees_sender_absent"] += 1
                continue

            recipients = normalize_list(doc.get("recipients", []))
            cc         = normalize_list(doc.get("cc", []))
            bcc        = normalize_list(doc.get("bcc", []))
            all_recs   = recipients + cc + bcc

            # --- Date ---
            date_iso, year, month, day, hour, weekday = parse_date(doc.get("date"))
            if not date_iso:
                stats["ignorees_date_invalide"] += 1
                continue

            # --- Subject + body ---
            subject = (doc.get("subject") or "").strip()
            body    = clean_body(doc.get("text", ""))

            # --- Géoloc ---
            location = infer_location(sender, body)
            if location["source"] == "unknown":
                stats["geoloc_unknown"] += 1
            else:
                stats["geoloc_resolue"] += 1

            # --- Champs calculés ---
            direction  = compute_direction(sender, all_recs)
            period     = get_period(date_iso)
            finance_kw = detect_finance_keywords(subject, body)
            is_reply   = bool(RE_REPLY_SUBJECT.search(subject))
            is_forward = bool(RE_FORWARD_SUBJECT.search(subject) or RE_FORWARD_BODY.search(body))

            raw_id = doc.get("_id")
            email_id = raw_id.get("$oid") if isinstance(raw_id, dict) else str(raw_id)

            # --- Document enrichi ---
            enriched = {
                "_id":            email_id,
                "sender":         sender,
                "sender_domain":  get_domain(sender),
                "recipients":     recipients,
                "cc":             cc,
                "bcc":            bcc,
                "all_recipients": all_recs,
                "subject":        subject,
                "body":           body,
                "body_length":    len(body),
                "date":           date_iso,
                "year":           year,
                "month":          month,
                "day":            day,
                "hour":           hour,
                "weekday":        weekday,
                "year_month":     f"{year:04d}-{month:02d}",
                "folder":         doc.get("folder", ""),
                "nb_recipients":  len(recipients),
                "nb_cc":          len(cc),
                "nb_bcc":         len(bcc),
                "nb_recipients_total":  len(all_recs),
                "is_mass_email":        len(all_recs) > 10,
                "direction":            direction,
                "period":               period,
                "is_reply":             is_reply,
                "is_forward":           is_forward,
                "has_finance_keywords": bool(finance_kw),
                "finance_keywords":     finance_kw,
                "location":             location,
            }
            fout.write(json.dumps(enriched, ensure_ascii=False) + "\n")
            stats["ecrites"] += 1

    return stats


# =============================================================================
# Entrée
# =============================================================================
def main():
    # Chemins par défaut (relatifs à la racine du projet)
    project_root = Path(__file__).resolve().parents[2]
    default_in   = project_root / "data" / "raw"      / "enron.json"
    default_out  = project_root / "data" / "enriched" / "enron_enriched.json"

    input_path  = Path(sys.argv[1]) if len(sys.argv) > 1 else default_in
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else default_out

    print("=" * 60)
    print("Pipeline de preparation du dataset Enron")
    print("=" * 60)
    print(f"  Entree : {input_path}")
    print(f"  Sortie : {output_path}")
    print()

    stats = process(input_path, output_path)

    print("Statistiques :")
    for k, v in stats.items():
        print(f"  {k:30s} : {v}")
    print()
    print(f"OK - {stats['ecrites']} documents enrichis ecrits.")


if __name__ == "__main__":
    main()
