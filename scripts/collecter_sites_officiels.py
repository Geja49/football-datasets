"""
Recupere logos et sites officiels des clubs via TheSportsDB (API publique).
Usage : python scripts/collecter_sites_officiels.py
"""

import csv
import sqlite3
import sys
import time
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "site" / "api"))

from sites_officiels import RECHERCHE_SITES, normaliser_url

FICHIER_BASE = RACINE / "donnees" / "football.db"
FICHIER_CSV = RACINE / "donnees" / "cinq_championnats" / "sites_equipes.csv"
URL_RECHERCHE = "https://www.thesportsdb.com/api/v1/json/3/searchteams.php"
PAUSE = 0.8


def nom_recherche(nom_matchs):
    return RECHERCHE_SITES.get(nom_matchs, nom_matchs)


def choisir_equipe(candidats, nom_matchs):
    foot = [c for c in candidats if (c.get("strSport") or "") == "Soccer"]
    if not foot:
        return None
    cible = nom_recherche(nom_matchs).lower()
    for equipe in foot:
        nom = (equipe.get("strTeam") or "").lower()
        if cible in nom or nom in cible:
            return equipe
    return foot[0]


def chercher(session, nom_matchs):
    requete = nom_recherche(nom_matchs)
    reponse = session.get(URL_RECHERCHE, params={"t": requete}, timeout=20)
    reponse.raise_for_status()
    data = reponse.json() or {}
    equipes = data.get("teams") or []
    choisi = choisir_equipe(equipes, nom_matchs)
    if not choisi:
        return {
            "equipe": nom_matchs,
            "nom_officiel": "",
            "url_site": "",
            "url_logo": "",
            "stade": "",
        }
    return {
        "equipe": nom_matchs,
        "nom_officiel": choisi.get("strTeam") or "",
        "url_site": normaliser_url(choisi.get("strWebsite")),
        "url_logo": normaliser_url(choisi.get("strBadge")),
        "stade": choisi.get("strStadium") or "",
    }


def equipes_uniques(connexion):
    lignes = connexion.execute(
        """
        SELECT DISTINCT domicile AS equipe FROM matchs
        UNION
        SELECT DISTINCT exterieur FROM matchs
        ORDER BY 1
        """
    )
    return [row[0] for row in lignes]


def ecrire_base(connexion, lignes):
    connexion.execute("DROP TABLE IF EXISTS sites_equipes")
    connexion.execute(
        """
        CREATE TABLE sites_equipes (
            equipe TEXT PRIMARY KEY,
            nom_officiel TEXT,
            url_site TEXT,
            url_logo TEXT,
            stade TEXT
        )
        """
    )
    connexion.executemany(
        """
        INSERT INTO sites_equipes (equipe, nom_officiel, url_site, url_logo, stade)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (l["equipe"], l["nom_officiel"], l["url_site"], l["url_logo"], l["stade"])
            for l in lignes
        ],
    )
    connexion.commit()


def main():
    session = requests.Session()
    session.headers.update({"User-Agent": "StatsChampionnats/1.0 (recherche sites officiels)"})
    connexion = sqlite3.connect(FICHIER_BASE)
    noms = equipes_uniques(connexion)
    print(f"{len(noms)} equipes a rechercher")
    resultats = []
    for i, nom in enumerate(noms, start=1):
        try:
            fiche = chercher(session, nom)
        except Exception as exc:
            print(f"  erreur {nom}: {exc}")
            fiche = {
                "equipe": nom,
                "nom_officiel": "",
                "url_site": "",
                "url_logo": "",
                "stade": "",
            }
        resultats.append(fiche)
        if i % 10 == 0 or fiche["url_site"]:
            print(f"  {i}/{len(noms)} {nom} -> {fiche['url_site'] or 'pas de site'}")
        time.sleep(PAUSE)

    FICHIER_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(FICHIER_CSV, "w", newline="", encoding="utf-8") as fichier:
        writer = csv.DictWriter(
            fichier,
            fieldnames=["equipe", "nom_officiel", "url_site", "url_logo", "stade"],
        )
        writer.writeheader()
        writer.writerows(resultats)
    ecrire_base(connexion, resultats)
    connexion.close()
    avec_site = sum(1 for l in resultats if l["url_site"])
    print(f"Termine : {avec_site}/{len(resultats)} sites officiels")
    print(f"CSV : {FICHIER_CSV}")


if __name__ == "__main__":
    main()
