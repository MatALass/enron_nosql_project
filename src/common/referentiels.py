"""
referentiels.py
---------------
Référentiels de mapping utilisés pour enrichir le dataset Enron.

Sources :
  - Bureaux Enron : sigles confirmés par les bodies des emails du dataset
    (HOU=1763 occurrences, LON=176, NYC/NY=15, OSL=3, etc.)
    Coordonnées : centres géographiques des villes (Wikipedia).
  - Domaines email externes : sièges sociaux des entreprises/organisations
    présentes dans les top domaines du dataset.
  - Mots-clés financiers : vocabulaire lié au scandale Enron 2001
    (audit, SEC, restatement, Arthur Andersen, etc.).
"""

# =============================================================================
# 1. Bureaux Enron (sigles identifiés dans les bodies des emails)
# =============================================================================
ENRON_OFFICES = {
    "HOU": {"city": "Houston",  "region": "Texas",      "country": "USA",    "lat": 29.7604, "lon": -95.3698},
    "LON": {"city": "London",   "region": "England",    "country": "UK",     "lat": 51.5074, "lon": -0.1278},
    "NYC": {"city": "New York", "region": "New York",   "country": "USA",    "lat": 40.7128, "lon": -74.0060},
    "NY":  {"city": "New York", "region": "New York",   "country": "USA",    "lat": 40.7128, "lon": -74.0060},
    "OSL": {"city": "Oslo",     "region": "Oslo",       "country": "Norway", "lat": 59.9139, "lon": 10.7522},
    "CAL": {"city": "Calgary",  "region": "Alberta",    "country": "Canada", "lat": 51.0447, "lon": -114.0719},
    "PDX": {"city": "Portland", "region": "Oregon",     "country": "USA",    "lat": 45.5152, "lon": -122.6784},
}

# Bureau par défaut quand le sigle n'est pas détectable dans le body
ENRON_DEFAULT_OFFICE = "HOU"

# =============================================================================
# 2. Domaines email externes (mappés vers le siège social)
# =============================================================================
EXTERNAL_DOMAINS = {
    # ---- Entreprises identifiées dans le dataset ----
    "lilly.com":      {"city": "Indianapolis", "region": "Indiana",      "country": "USA", "lat": 39.7684, "lon": -86.1581},
    "compaq.com":     {"city": "Houston",      "region": "Texas",        "country": "USA", "lat": 29.7604, "lon": -95.3698},
    "i2.com":         {"city": "Dallas",       "region": "Texas",        "country": "USA", "lat": 32.7767, "lon": -96.7970},
    "williams.com":   {"city": "Tulsa",        "region": "Oklahoma",     "country": "USA", "lat": 36.1540, "lon": -95.9928},
    "cera.com":       {"city": "Cambridge",    "region": "Massachusetts","country": "USA", "lat": 42.3736, "lon": -71.1097},
    "kudlow.com":     {"city": "New York",     "region": "New York",     "country": "USA", "lat": 40.7128, "lon": -74.0060},
    "velaw.com":      {"city": "Houston",      "region": "Texas",        "country": "USA", "lat": 29.7604, "lon": -95.3698},  # Vinson & Elkins (cabinet d'avocats Enron)

    # ---- FAI et webmails grand public (mappés au siège du provider) ----
    "aol.com":          {"city": "Dulles",       "region": "Virginia",     "country": "USA", "lat": 38.9543, "lon": -77.4488},
    "yahoo.com":        {"city": "Sunnyvale",    "region": "California",   "country": "USA", "lat": 37.3688, "lon": -122.0363},
    "hotmail.com":      {"city": "Redmond",      "region": "Washington",   "country": "USA", "lat": 47.6740, "lon": -122.1215},
    "msn.com":          {"city": "Redmond",      "region": "Washington",   "country": "USA", "lat": 47.6740, "lon": -122.1215},
    "email.msn.com":    {"city": "Redmond",      "region": "Washington",   "country": "USA", "lat": 47.6740, "lon": -122.1215},
    "earthlink.net":    {"city": "Atlanta",      "region": "Georgia",      "country": "USA", "lat": 33.7490, "lon": -84.3880},
    "mindspring.com":   {"city": "Atlanta",      "region": "Georgia",      "country": "USA", "lat": 33.7490, "lon": -84.3880},
    "worldnet.att.net": {"city": "Dallas",       "region": "Texas",        "country": "USA", "lat": 32.7767, "lon": -96.7970},
    "swbell.net":       {"city": "San Antonio",  "region": "Texas",        "country": "USA", "lat": 29.4241, "lon": -98.4936},
    "pacbell.net":      {"city": "San Francisco","region": "California",   "country": "USA", "lat": 37.7749, "lon": -122.4194},
    "mediaone.net":     {"city": "Englewood",    "region": "Colorado",     "country": "USA", "lat": 39.6478, "lon": -104.9876},
    "verizon.net":      {"city": "New York",     "region": "New York",     "country": "USA", "lat": 40.7128, "lon": -74.0060},
    "prodigy.net":      {"city": "White Plains", "region": "New York",     "country": "USA", "lat": 41.0339, "lon": -73.7629},
    "attglobal.net":    {"city": "Dallas",       "region": "Texas",        "country": "USA", "lat": 32.7767, "lon": -96.7970},

    # ---- Universités ----
    "uh.edu":          {"city": "Houston",     "region": "Texas",                    "country": "USA", "lat": 29.7604, "lon": -95.3698},
    "uth.tmc.edu":     {"city": "Houston",     "region": "Texas",                    "country": "USA", "lat": 29.7604, "lon": -95.3698},
    "howard.edu":      {"city": "Washington",  "region": "District of Columbia",     "country": "USA", "lat": 38.9072, "lon": -77.0369},
    "yale.edu":        {"city": "New Haven",   "region": "Connecticut",              "country": "USA", "lat": 41.3083, "lon": -72.9279},
    "missouri.edu":    {"city": "Columbia",    "region": "Missouri",                 "country": "USA", "lat": 38.9517, "lon": -92.3341},

    # ---- Think tanks / ONG / lobbies ----
    "aei.org":           {"city": "Washington", "region": "District of Columbia", "country": "USA",         "lat": 38.9072, "lon": -77.0369},
    "as-coa.org":        {"city": "New York",   "region": "New York",             "country": "USA",         "lat": 40.7128, "lon": -74.0060},
    "uschamber.com":     {"city": "Washington", "region": "District of Columbia", "country": "USA",         "lat": 38.9072, "lon": -77.0369},
    "weforum.org":       {"city": "Geneva",     "region": "Geneva",               "country": "Switzerland", "lat": 46.2044, "lon": 6.1432},
    "csis.org":          {"city": "Washington", "region": "District of Columbia", "country": "USA",         "lat": 38.9072, "lon": -77.0369},
    "rff.org":           {"city": "Washington", "region": "District of Columbia", "country": "USA",         "lat": 38.9072, "lon": -77.0369},
    "independent.org":   {"city": "Oakland",    "region": "California",           "country": "USA",         "lat": 37.8044, "lon": -122.2712},
    "usmcoc.org":        {"city": "Washington", "region": "District of Columbia", "country": "USA",         "lat": 38.9072, "lon": -77.0369},
    "mail.house.gov":    {"city": "Washington", "region": "District of Columbia", "country": "USA",         "lat": 38.9072, "lon": -77.0369},
    "ci.portland.or.us": {"city": "Portland",   "region": "Oregon",               "country": "USA",         "lat": 45.5152, "lon": -122.6784},

    # ---- Domaines géolocalisables explicitement ----
    "houston.org":       {"city": "Houston", "region": "Texas", "country": "USA", "lat": 29.7604, "lon": -95.3698},
    "houston.rr.com":    {"city": "Houston", "region": "Texas", "country": "USA", "lat": 29.7604, "lon": -95.3698},
    "layfam.com":        {"city": "Houston", "region": "Texas", "country": "USA", "lat": 29.7604, "lon": -95.3698},  # famille Lay
    "lplpi.com":         {"city": "Houston", "region": "Texas", "country": "USA", "lat": 29.7604, "lon": -95.3698},  # Linda Lay (épouse)
    "madisonenergy.com": {"city": "Houston", "region": "Texas", "country": "USA", "lat": 29.7604, "lon": -95.3698},
}

# =============================================================================
# 3. Mots-clés financiers / scandale Enron
# =============================================================================
FINANCE_KEYWORDS = {
    "stock", "stocks", "share", "shares", "shareholder", "shareholders",
    "earnings", "revenue", "profit", "loss", "losses", "audit", "auditor",
    "sec", "10-k", "10-q", "restatement", "restated", "merger", "acquisition",
    "ipo", "off-balance", "off balance", "special purpose", "spv",
    "andersen", "arthur andersen", "subpoena", "litigation", "lawsuit",
    "investigation", "whistleblower", "watkins",
}

# =============================================================================
# 4. Alias d'adresses (même personne sous plusieurs adresses)
# =============================================================================
EMAIL_ALIASES = {
    "klay@enron.com": "kenneth.lay@enron.com",
}

# Adresses techniques sans personne réelle derrière
JUNK_ADDRESSES = {
    "no.address@enron.com",
    "outlook.team@enron.com",
}

# =============================================================================
# 5. Périodes du scandale Enron (axe temporel narratif)
# =============================================================================
PERIODS = [
    # (label, date_start_inclusive, date_end_exclusive)
    ("pre_scandal",   "1998-01-01", "2001-08-01"),  # avant la démission de Skilling (14 août 2001)
    ("scandal",       "2001-08-01", "2002-01-01"),  # démission Skilling -> faillite (décembre 2001)
    ("post_collapse", "2002-01-01", "2010-01-01"),  # après faillite (mise en examen de Lay, procès)
]
