"""
Verifie que les CSV (et la base si elle existe) contiennent
toutes les donnees attendues.

Usage (a la racine) :
    python scripts/verifier_donnees.py
"""

import csv
import sqlite3
import sys
import time
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parents[1]
DOSSIER_CSV = RACINE / "donnees" / "cinq_championnats"
FICHIER_BASE = RACINE / "donnees" / "football.db"
ANNEE_MIN = 2020
ANNEE_COURANTE = 2026
SAISON_COURANTE = f"{ANNEE_COURANTE}-{ANNEE_COURANTE + 1}"
LIGUES = (
    "Premier League",
    "La Liga",
    "Bundesliga",
    "Serie A",
    "Ligue 1",
)
LDC = "Ligue des champions"
UNDERSTAT = {
    "Premier League": "EPL",
    "La Liga": "La_liga",
    "Bundesliga": "Bundesliga",
    "Serie A": "Serie_A",
    "Ligue 1": "Ligue_1",
}


def libelle_saison(annee):
    return f"{annee}-{annee + 1}"


def matchs_attendus(championnat, saison):
    debut = int(saison[:4])
    if championnat == "Bundesliga":
        return 306
    if championnat == "Ligue 1":
        return 306 if debut >= 2023 else 380
    if championnat == LDC:
        return None
    return 380


def lire_csv(nom):
    chemin = DOSSIER_CSV / nom
    if not chemin.exists():
        return []
    with open(chemin, newline="", encoding="utf-8") as fichier:
        return list(csv.DictReader(fichier))


def compter(lignes, championnat, saison):
    return sum(
        1
        for ligne in lignes
        if ligne.get("championnat") == championnat and ligne.get("saison") == saison
    )


def session_understat():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )
    return session


def counts_understat(session, slug, annee):
    page = f"https://understat.com/league/{slug}/{annee}"
    session.get(page, timeout=30)
    reponse = session.get(
        f"https://understat.com/getLeagueData/{slug}/{annee}",
        headers={"X-Requested-With": "XMLHttpRequest"},
        timeout=30,
    )
    reponse.raise_for_status()
    data = reponse.json()
    dates = data.get("dates") or []
    joues = sum(1 for m in dates if m.get("isResult"))
    avenir = sum(1 for m in dates if not m.get("isResult"))
    joueurs = len(data.get("players") or [])
    return joues, avenir, joueurs


def verifier_base(matchs, matchs_xg, joueurs, calendrier):
    if not FICHIER_BASE.exists():
        print("\n=== Base SQLite ===")
        print("  football.db absente (normal sur GitHub).")
        return []
    connexion = sqlite3.connect(FICHIER_BASE)
    manques = []
    print("\n=== Base SQLite vs CSV ===")
    paires = (
        ("matchs", matchs),
        ("matchs_xg", matchs_xg),
        ("joueurs", joueurs),
        ("calendrier", calendrier),
    )
    for nom, lignes in paires:
        nb_base = connexion.execute(f"SELECT COUNT(*) FROM {nom}").fetchone()[0]
        nb_csv = len(lignes)
        etat = "OK" if nb_base == nb_csv else "MANQUE"
        print(f"  {nom:12}: base {nb_base:>6}  csv {nb_csv:>6}  {etat}")
        if nb_base != nb_csv:
            manques.append(f"SQLite {nom}: {nb_base} lignes, CSV {nb_csv}")
    connexion.close()
    return manques


def main():
    matchs = lire_csv("matchs.csv")
    matchs_xg = lire_csv("matchs_xg.csv")
    joueurs = lire_csv("joueurs.csv")
    calendrier = lire_csv("calendrier.csv")
    if not matchs:
        print("Aucun match dans donnees/cinq_championnats/matchs.csv")
        sys.exit(1)

    manques = []
    print("=== Saisons terminees (2020-2025) ===")
    for annee in range(ANNEE_MIN, ANNEE_COURANTE):
        saison = libelle_saison(annee)
        for ligue in LIGUES:
            nb_matchs = compter(matchs, ligue, saison)
            nb_xg = compter(matchs_xg, ligue, saison)
            nb_joueurs = compter(joueurs, ligue, saison)
            attendu = matchs_attendus(ligue, saison)
            etat = "OK" if nb_matchs == attendu else "MANQUE"
            if nb_matchs != attendu:
                manques.append(
                    f"{ligue} {saison}: {nb_matchs} matchs au lieu de {attendu}"
                )
            if nb_xg < nb_matchs:
                manques.append(
                    f"{ligue} {saison}: {nb_xg} xG pour {nb_matchs} matchs"
                )
            if nb_joueurs == 0:
                manques.append(f"{ligue} {saison}: aucun joueur")
            print(
                f"  {ligue:16} {saison}: matchs {nb_matchs:>4}/{attendu}"
                f"  xG {nb_xg:>4}  joueurs {nb_joueurs:>4}  {etat}"
            )

    print("\n=== Ligue des champions ===")
    for annee in range(2020, 2027):
        saison = libelle_saison(annee)
        nb_matchs = compter(matchs, LDC, saison)
        nb_cal = compter(calendrier, LDC, saison)
        print(f"  {saison}: {nb_matchs} joues, {nb_cal} a venir")
        if annee < ANNEE_COURANTE and nb_matchs == 0:
            manques.append(f"LDC {saison}: aucun match")
        if annee == ANNEE_COURANTE and nb_matchs == 0:
            print("  (2026-2027 pas encore publiee chez openfootball)")

    print(f"\n=== Saison en cours {SAISON_COURANTE} (sources live) ===")
    session = session_understat()
    for ligue in LIGUES:
        nos_matchs = compter(matchs, ligue, SAISON_COURANTE)
        nos_xg = compter(matchs_xg, ligue, SAISON_COURANTE)
        nos_cal = compter(calendrier, ligue, SAISON_COURANTE)
        nos_joueurs = compter(joueurs, ligue, SAISON_COURANTE)
        try:
            joues, avenir, nb_j = counts_understat(
                session, UNDERSTAT[ligue], ANNEE_COURANTE
            )
        except Exception as exc:
            print(f"  {ligue}: Understat inaccessible ({exc})")
            time.sleep(1)
            continue
        etat_m = "OK" if nos_matchs >= joues else "MANQUE"
        etat_c = "OK" if nos_cal >= avenir else "MANQUE"
        etat_j = "OK" if nos_joueurs >= nb_j else "MANQUE"
        if nos_matchs < joues:
            manques.append(
                f"{ligue} {SAISON_COURANTE}: {nos_matchs} matchs, Understat {joues}"
            )
        if nos_cal < avenir:
            manques.append(
                f"{ligue} {SAISON_COURANTE}: {nos_cal} a venir, Understat {avenir}"
            )
        if nos_joueurs < nb_j:
            manques.append(
                f"{ligue} {SAISON_COURANTE}: {nos_joueurs} joueurs, Understat {nb_j}"
            )
        print(
            f"  {ligue:16}: matchs {nos_matchs:>3}/{joues}"
            f"  xG {nos_xg:>3}  a venir {nos_cal:>3}/{avenir}"
            f"  joueurs {nos_joueurs:>3}/{nb_j}  {etat_m}/{etat_c}/{etat_j}"
        )
        time.sleep(1)

    manques.extend(verifier_base(matchs, matchs_xg, joueurs, calendrier))
    print("\n=== Bilan ===")
    if manques:
        print(f"{len(manques)} ecart(s) :")
        for ligne in manques:
            print(f"  - {ligne}")
        sys.exit(1)
    print("Toutes les donnees attendues sont presentes.")


if __name__ == "__main__":
    main()
