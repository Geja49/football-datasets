"""
Associe chaque club a un blason (depot luukhopman/football-logos via jsDelivr).
Usage : python scripts/collecter_logos.py
"""

import csv
import sqlite3
import sys
import unicodedata
import urllib.parse
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "site" / "api"))

FICHIER_BASE = RACINE / "donnees" / "football.db"
FICHIER_CSV = RACINE / "donnees" / "cinq_championnats" / "sites_equipes.csv"
CDN = "https://cdn.jsdelivr.net/gh/luukhopman/football-logos@master/"
API = "https://api.github.com/repos/luukhopman/football-logos/contents/"
SAISONS = [
    "logos",
    "history/2025-26",
    "history/2024-25",
    "history/2023-24",
    "history/2022-23",
    "history/2021-22",
]
LIGUES = [
    "England - Premier League",
    "France - Ligue 1",
    "Germany - Bundesliga",
    "Italy - Serie A",
    "Spain - LaLiga",
]

# Nom dans nos CSV -> fragment du fichier blason
ALIAS = {
    "Alaves": "alaves",
    "Almeria": "almeria",
    "Angers": "angers",
    "Ath Bilbao": "athletic",
    "Ath Madrid": "atletico",
    "Barcelona": "barcelona",
    "Benevento": "benevento",
    "Betis": "betis",
    "Bournemouth": "bournemouth",
    "Brest": "brestois",
    "Brighton": "brighton",
    "Cadiz": "cadiz",
    "Celta": "celta",
    "Como": "como",
    "Crotone": "crotone",
    "Dep. A Coruna": "coruna",
    "Dijon": "dijon",
    "Eibar": "eibar",
    "Ein Frankfurt": "eintracht",
    "Espanol": "espanyol",
    "FC Koln": "koln",
    "Greuther Furth": "furth",
    "Huesca": "huesca",
    "Inter": "inter milan",
    "Leeds": "leeds",
    "Leganes": "leganes",
    "Lens": "lens",
    "Leverkusen": "leverkusen",
    "Lille": "lille",
    "Lyon": "lyon",
    "M'gladbach": "gladbach",
    "Mainz": "mainz",
    "Man City": "manchester city",
    "Man United": "manchester united",
    "Marseille": "marseille",
    "Milan": "ac milan",
    "Newcastle": "newcastle",
    "Nice": "nice",
    "Nimes": "nimes",
    "Nott'm Forest": "nottingham",
    "Paris SG": "paris saint",
    "Parma": "parma",
    "Pisa": "pisa",
    "Reims": "reims",
    "Rennes": "rennais",
    "Roma": "as roma",
    "Santander": "santander",
    "Sociedad": "sociedad",
    "St Etienne": "etienne",
    "St Pauli": "st. pauli",
    "Strasbourg": "strasbourg",
    "Union Berlin": "union berlin",
    "Vallecano": "vallecano",
    "Verona": "hellas",
    "Villarreal": "villarreal",
    "Werder Bremen": "werder",
    "West Brom": "west brom",
    "West Ham": "west ham",
    "Wolves": "wolverhampton",
    "Dortmund": "dortmund",
}


def sans_accents(texte):
    decompose = unicodedata.normalize("NFD", texte or "")
    return "".join(c for c in decompose if unicodedata.category(c) != "Mn")


def normaliser(nom):
    texte = sans_accents(nom).lower()
    return "".join(c for c in texte if c.isalnum())


PAGES_WIKI = {
    "Benevento": "Benevento_Calcio",
    "Crotone": "FC_Crotone",
    "Dijon": "Dijon_FCO",
    "Eibar": "SD_Eibar",
    "Huesca": "SD_Huesca",
    "Nimes": "Nîmes_Olympique",
    "West Brom": "West_Bromwich_Albion_F.C.",
}


def url_cdn(chemin):
    return CDN + urllib.parse.quote(chemin, safe="/")


def logo_wikipedia(session, article):
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(article)}"
    reponse = session.get(url, timeout=20)
    if reponse.status_code != 200:
        return ""
    visuel = (reponse.json().get("thumbnail") or {}).get("source") or ""
    return visuel.replace("http://", "https://")


def charger_fichiers(session):
    fichiers = []
    for i, saison in enumerate(SAISONS):
        recence = 90 - i * 10
        for ligue in LIGUES:
            chemin_api = f"{saison}/{ligue}"
            url = API + urllib.parse.quote(chemin_api)
            reponse = session.get(url, timeout=30)
            if reponse.status_code != 200:
                continue
            for item in reponse.json():
                if item.get("type") != "file" or not item["name"].endswith(".png"):
                    continue
                nom = item["name"][:-4]
                chemin = item["path"]
                fichiers.append((normaliser(nom), chemin, recence))
    return fichiers


def trouver_logo(nom_club, fichiers):
    cible = normaliser(ALIAS.get(nom_club, nom_club))
    if len(cible) < 4:
        return None
    meilleur = None
    meilleur_score = 0
    for nom_norm, chemin, recence in fichiers:
        if nom_norm == cible:
            score = 1000 + recence
        elif cible in nom_norm:
            score = 500 + int(300 * len(cible) / len(nom_norm)) + recence
        elif nom_norm in cible and len(nom_norm) >= 6:
            score = 300 + recence
        else:
            continue
        if score > meilleur_score:
            meilleur_score = score
            meilleur = chemin
    return meilleur if meilleur_score >= 300 else None


def main():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "StatsChampionnats/1.0 (projet local; logos clubs europeens)"
        }
    )
    print("Lecture des dossiers de blasons...")
    fichiers = charger_fichiers(session)
    print(f"{len(fichiers)} fichiers")

    connexion = sqlite3.connect(FICHIER_BASE)
    connexion.row_factory = sqlite3.Row
    clubs = [
        row["equipe"]
        for row in connexion.execute("SELECT equipe FROM sites_equipes ORDER BY equipe")
    ]
    manques = []
    for club in clubs:
        chemin = trouver_logo(club, fichiers)
        if chemin:
            connexion.execute(
                "UPDATE sites_equipes SET url_logo = ? WHERE equipe = ?",
                (url_cdn(chemin), club),
            )
            print(f"  {club} -> {Path(chemin).name}")
            continue
        article = PAGES_WIKI.get(club)
        if article:
            visuel = logo_wikipedia(session, article)
            if visuel:
                connexion.execute(
                    "UPDATE sites_equipes SET url_logo = ? WHERE equipe = ?",
                    (visuel, club),
                )
                print(f"  {club} -> wikipedia")
                continue
        manques.append(club)
    connexion.commit()

    lignes = [
        dict(row)
        for row in connexion.execute(
            "SELECT equipe, nom_officiel, url_site, url_logo, stade FROM sites_equipes ORDER BY equipe"
        )
    ]
    with open(FICHIER_CSV, "w", newline="", encoding="utf-8") as fichier:
        writer = csv.DictWriter(
            fichier,
            fieldnames=["equipe", "nom_officiel", "url_site", "url_logo", "stade"],
        )
        writer.writeheader()
        writer.writerows(lignes)
    connexion.close()
    avec = sum(1 for l in lignes if l["url_logo"])
    print(f"Logos : {avec}/{len(lignes)}")
    if manques:
        print("Sans logo :", ", ".join(manques))


if __name__ == "__main__":
    main()
