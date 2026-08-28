"""
Surveille football-data, Understat et openfootball.
Des qu'une source change, relance la collecte et recree football.db.

Usage (a la racine du projet) :
    python scripts/surveiller_sources.py
    python scripts/surveiller_sources.py --une-fois
    python scripts/surveiller_sources.py --forcer
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parents[1]
FICHIER_ETAT = RACINE / "donnees" / "etat_sources.json"
FICHIER_VERROU = RACINE / "donnees" / "collecte.lock"
ANNEE = 2026
CODE_SAISON = f"{str(ANNEE)[-2:]}{str(ANNEE + 1)[-2:]}"
PAUSE_SECONDES = 20 * 60

LIGUES_FOOTBALL_DATA = (
    ("E0", "Premier League"),
    ("SP1", "La Liga"),
    ("D1", "Bundesliga"),
    ("I1", "Serie A"),
    ("F1", "Ligue 1"),
)
LIGUES_UNDERSTAT = (
    ("EPL", "Premier League"),
    ("La_liga", "La Liga"),
    ("Bundesliga", "Bundesliga"),
    ("Serie_A", "Serie A"),
    ("Ligue_1", "Ligue 1"),
)
URL_FIXTURES = "https://www.football-data.co.uk/fixtures.csv"
URL_LDC = (
    "https://raw.githubusercontent.com/openfootball/champions-league/"
    "master/{dossier}/cl.txt"
)

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "StatsChampionnats/1.0 (projet local; surveillance sources)"
    }
)


def empreinte(texte):
    return hashlib.sha256(texte.encode("utf-8", errors="replace")).hexdigest()


def lire_url(url, en_tetes=None):
    try:
        reponse = SESSION.get(url, timeout=30, headers=en_tetes)
    except requests.RequestException as exc:
        print(f"  indisponible {url}: {exc}")
        return None
    if reponse.status_code != 200:
        print(f"  HTTP {reponse.status_code} {url}")
        return None
    reponse.encoding = reponse.apparent_encoding or "utf-8"
    return reponse.text


def collecter_empreintes():
    etat = {}
    for code, nom in LIGUES_FOOTBALL_DATA:
        url = f"https://www.football-data.co.uk/mmz4281/{CODE_SAISON}/{code}.csv"
        texte = lire_url(url)
        if texte is not None:
            etat[f"football-data:{nom}"] = empreinte(texte)

    texte = lire_url(URL_FIXTURES)
    if texte is not None:
        etat["football-data:fixtures"] = empreinte(texte)

    for slug, nom in LIGUES_UNDERSTAT:
        page = f"https://understat.com/league/{slug}/{ANNEE}"
        SESSION.get(page, timeout=30)
        texte = lire_url(
            f"https://understat.com/getLeagueData/{slug}/{ANNEE}",
            en_tetes={"X-Requested-With": "XMLHttpRequest"},
        )
        if texte is not None:
            etat[f"understat:{nom}"] = empreinte(texte)
        time.sleep(1)

    for dossier in ("2025-26", "2026-27"):
        texte = lire_url(URL_LDC.format(dossier=dossier))
        if texte is not None:
            etat[f"openfootball:{dossier}"] = empreinte(texte)
    return etat


def charger_etat():
    if not FICHIER_ETAT.exists():
        return {}
    try:
        return json.loads(FICHIER_ETAT.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def sauver_etat(etat):
    FICHIER_ETAT.parent.mkdir(parents=True, exist_ok=True)
    FICHIER_ETAT.write_text(
        json.dumps(etat, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def sources_changees(ancien, nouveau):
    changements = []
    for nom, valeur in nouveau.items():
        if ancien.get(nom) != valeur:
            changements.append(nom)
    return changements


def collecte_en_cours():
    if not FICHIER_VERROU.exists():
        return False
    age = time.time() - FICHIER_VERROU.stat().st_mtime
    return age < 45 * 60


def poser_verrou():
    FICHIER_VERROU.parent.mkdir(parents=True, exist_ok=True)
    FICHIER_VERROU.write_text(str(time.time()), encoding="utf-8")


def oter_verrou():
    if FICHIER_VERROU.exists():
        FICHIER_VERROU.unlink()


def mettre_a_jour():
    if collecte_en_cours():
        print("Une collecte est deja en cours, on attend le prochain tour.")
        return False
    poser_verrou()
    try:
        print("Sources changees : collecte et recreation de la base...")
        resultat = subprocess.run(
            [sys.executable, str(RACINE / "scripts" / "mettre_a_jour.py")],
            cwd=RACINE,
        )
        return resultat.returncode == 0
    finally:
        oter_verrou()


def verifier(forcer=False):
    print("Verification des sources...")
    nouveau = collecter_empreintes()
    ancien = charger_etat()
    if forcer:
        changements = list(nouveau.keys()) or ["force"]
    else:
        changements = sources_changees(ancien, nouveau)
    if not changements:
        print("Rien de nouveau sur les sites sources.")
        sauver_etat(nouveau)
        return
    print("Changements :")
    for nom in changements:
        print(f"  - {nom}")
    if mettre_a_jour():
        # L'historique analyses est deja lance en fin de mettre_a_jour.py.
        sauver_etat(nouveau)
        print("Base a jour.")
    else:
        print("La mise a jour a echoue, nouvel essai au prochain tour.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--une-fois", action="store_true")
    parser.add_argument("--forcer", action="store_true")
    args = parser.parse_args()
    verifier(forcer=args.forcer)
    if args.une_fois:
        return
    print(f"Surveillance toutes les {PAUSE_SECONDES // 60} minutes.")
    while True:
        time.sleep(PAUSE_SECONDES)
        verifier()


if __name__ == "__main__":
    main()
