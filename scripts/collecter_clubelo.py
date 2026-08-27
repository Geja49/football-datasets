"""
Classements Elo clubs via l'API publique ClubElo (api.clubelo.com).

Source gratuite, hors sites interdits du projet. Pas de dependance
soccerdata (qui embarque aussi FBref / Sofascore / WhoScored).

Usage : python scripts/collecter_clubelo.py
"""

import csv
import time
from datetime import date, timedelta
from pathlib import Path

import requests

DOSSIER_SORTIE = Path("donnees/cinq_championnats")
FICHIER = DOSSIER_SORTIE / "classements_elo.csv"
URL_JOUR = "https://api.clubelo.com/{date}"
TIMEOUT = 60
# Codes pays ClubElo pour les 5 ligues + LDC europeenne (Level 1).
PAYS_CIBLES = {"ENG", "ESP", "GER", "ITA", "FRA", "TUR"}
COLONNES = [
    "date",
    "rang",
    "club",
    "pays",
    "niveau",
    "elo",
    "source",
]

SESSION_WEB = requests.Session()
SESSION_WEB.headers.update(
    {
        "User-Agent": "StatsChampionnats/1.0 (projet local; ClubElo API)"
    }
)


def telecharger_jour(jour):
    url = URL_JOUR.format(date=jour.isoformat())
    try:
        reponse = SESSION_WEB.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        print(f"   {jour}: impossible ({exc})")
        return None
    if reponse.status_code != 200:
        print(f"   {jour}: HTTP {reponse.status_code}")
        return None
    if "Elo" not in reponse.text[:200] and "Club" not in reponse.text[:200]:
        print(f"   {jour}: reponse inattendue")
        return None
    return reponse.text


def parser(texte, jour):
    lignes = []
    lecteur = csv.DictReader(texte.splitlines())
    for row in lecteur:
        pays = (row.get("Country") or "").strip().upper()
        if pays not in PAYS_CIBLES:
            continue
        try:
            elo = float(row.get("Elo") or 0)
        except ValueError:
            continue
        lignes.append(
            {
                "date": jour.isoformat(),
                "rang": (row.get("Rank") or "").strip(),
                "club": (row.get("Club") or "").strip(),
                "pays": pays,
                "niveau": (row.get("Level") or "").strip(),
                "elo": round(elo, 1),
                "source": "clubelo",
            }
        )
    return lignes


def ecrire_csv(chemin, lignes):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLONNES)
        writer.writeheader()
        writer.writerows(lignes)


def main():
    print("ClubElo (api.clubelo.com)...")
    texte = None
    jour_ok = None
    # Essayer aujourd'hui puis quelques jours en arriere (API parfois en retard).
    for decalage in range(0, 8):
        jour = date.today() - timedelta(days=decalage)
        print(f"  tentative {jour}...")
        texte = telecharger_jour(jour)
        if texte:
            jour_ok = jour
            break
        time.sleep(0.5)
    if not texte or not jour_ok:
        print(
            "   ClubElo inaccessible pour le moment "
            "(timeout / reseau). On conserve l'ancien fichier s'il existe."
        )
        return
    lignes = parser(texte, jour_ok)
    if not lignes:
        print("   Aucune ligne pour ENG/ESP/GER/ITA/FRA")
        return
    ecrire_csv(FICHIER, lignes)
    print(f"   {len(lignes)} clubs -> {FICHIER} (date {jour_ok})")


if __name__ == "__main__":
    main()
