"""
Collecte optionnelle API-Football (api-sports.io).

Sans CLE_API_FOOTBALL : ne fait rien.
Avec cle : une ligue, saison en cours, stats joueurs paginees, cache disque.
Le free tier est petit (~100 req/jour) : on s'arrete si le quota restant est bas.
Pas de cotes. Pas de telechargement massif.
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from defense_commune import (
    COLONNES_COUVERTURE,
    COLONNES_DEFENSE,
    FICHIER_COUVERTURE,
    FICHIER_DEFENSE,
    charger_env,
    ecrire_csv,
    lire_csv,
    remplacer_source,
    stats_vides,
    ligne_defense,
)

RACINE = Path(__file__).resolve().parents[1]
SOURCE = "api-football"
URL = "https://v3.football.api-sports.io/players"
DOSSIER_CACHE = Path("donnees/cache_api_football")
PAUSE = 1.2
QUOTA_MINIMUM = 15
ANNEE_SAISON = 2025
SAISON = "2025-2026"

# Une seule ligue par execution pour rester dans le free tier.
LIGUES = (
    {"id": 39, "nom": "Premier League"},
    {"id": 140, "nom": "La Liga"},
    {"id": 78, "nom": "Bundesliga"},
    {"id": 135, "nom": "Serie A"},
    {"id": 61, "nom": "Ligue 1"},
)


def quota_restant(reponse):
    try:
        return int(reponse.headers.get("x-ratelimit-requests-remaining") or 0)
    except ValueError:
        return 0


def lire_page_cache(ligue_id, page):
    chemin = DOSSIER_CACHE / f"joueurs_{ligue_id}_{ANNEE_SAISON}_{page}.json"
    if chemin.exists():
        return json.loads(chemin.read_text(encoding="utf-8"))
    return None


def sauver_page(ligue_id, page, data):
    DOSSIER_CACHE.mkdir(parents=True, exist_ok=True)
    chemin = DOSSIER_CACHE / f"joueurs_{ligue_id}_{ANNEE_SAISON}_{page}.json"
    chemin.write_text(json.dumps(data), encoding="utf-8")


def choisir_ligue():
    """Reprend la premiere ligue sans cache complet, sinon Premier League."""
    for ligue in LIGUES:
        marqueur = DOSSIER_CACHE / f"complet_{ligue['id']}_{ANNEE_SAISON}.txt"
        if not marqueur.exists():
            return ligue
    return LIGUES[0]


def collecter():
    charger_env(RACINE)
    cle = (os.environ.get("CLE_API_FOOTBALL") or "").strip()
    print("API-Football (optionnel)...")
    if not cle:
        print("   pas de CLE_API_FOOTBALL dans l'environnement / .env : ignore.")
        return [], []

    ligue = choisir_ligue()
    session = requests.Session()
    session.headers.update(
        {
            "x-apisports-key": cle,
            "User-Agent": "StatsChampionnats/1.0 (projet local; API-Football)",
        }
    )
    page = 1
    pages_total = 1
    fusion = {}
    while page <= pages_total:
        cache = lire_page_cache(ligue["id"], page)
        if cache is None:
            try:
                reponse = session.get(
                    URL,
                    params={"league": ligue["id"], "season": ANNEE_SAISON, "page": page},
                    timeout=30,
                )
            except requests.RequestException as exc:
                print(f"   requete impossible ({exc})")
                break
            if reponse.status_code == 429:
                print("   quota API epuise, on s'arrete.")
                break
            if reponse.status_code != 200:
                print(f"   HTTP {reponse.status_code}, ignore.")
                break
            restant = quota_restant(reponse)
            cache = reponse.json()
            sauver_page(ligue["id"], page, cache)
            if restant and restant < QUOTA_MINIMUM:
                print(f"   quota restant {restant}, on s'arrete apres cette page.")
                pages_total = page
            time.sleep(PAUSE)
        paging = (cache.get("paging") or {})
        pages_total = int(paging.get("total") or page)
        for item in cache.get("response") or []:
            fiche = item.get("player") or {}
            for bloc in item.get("statistics") or []:
                equipe = ((bloc.get("team") or {}).get("name")) or ""
                joueur = (fiche.get("name") or "").strip()
                if not joueur or not equipe:
                    continue
                tacles = bloc.get("tackles") or {}
                duels = bloc.get("duels") or {}
                gardien = bloc.get("goalkeeper") or {}
                jeux = bloc.get("games") or {}
                cle_j = (ligue["nom"], equipe, joueur)
                if cle_j not in fusion:
                    fusion[cle_j] = stats_vides()
                stats = fusion[cle_j]
                stats["matchs_ids"].add(page)
                stats["tacles"] += int(tacles.get("total") or 0)
                stats["interceptions"] += int(tacles.get("interceptions") or 0)
                stats["blocs"] += int(tacles.get("blocks") or 0)
                stats["duels"] += int(duels.get("total") or 0)
                stats["duels_gagnes"] += int(duels.get("won") or 0)
                stats["arrets"] += int(gardien.get("saves") or 0)
                apparitions = int(jeux.get("appearences") or jeux.get("appearances") or 0)
                if apparitions:
                    stats["matchs_ids"] = set(range(apparitions))
        print(f"   {ligue['nom']} page {page}/{pages_total}")
        page += 1

    if pages_total >= 1 and page > pages_total:
        marqueur = DOSSIER_CACHE / f"complet_{ligue['id']}_{ANNEE_SAISON}.txt"
        marqueur.write_text("ok", encoding="utf-8")

    lignes = [
        ligne_defense(championnat, SAISON, equipe, joueur, stats, SOURCE)
        for (championnat, equipe, joueur), stats in fusion.items()
    ]
    if not lignes:
        print("   aucune ligne (cle invalide, saison vide ou quota).")
        return [], []
    remplacer_source(FICHIER_DEFENSE, SOURCE, lignes, COLONNES_DEFENSE)
    couverture = [
        {
            "championnat": ligue["nom"],
            "saison": SAISON,
            "source": SOURCE,
            "nb_matchs": "",
            "complet": 0,
            "commentaire": "Stats joueurs API, une ligue a la fois, cachees.",
        }
    ]
    anciennes = [l for l in lire_csv(FICHIER_COUVERTURE) if l.get("source") != SOURCE]
    ecrire_csv(FICHIER_COUVERTURE, anciennes + couverture, COLONNES_COUVERTURE)
    print(f"   {len(lignes)} joueurs {ligue['nom']} {SAISON}")
    return lignes, couverture


def main():
    collecter()


if __name__ == "__main__":
    main()
