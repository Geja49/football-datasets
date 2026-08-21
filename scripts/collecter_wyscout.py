"""
Jeu d'evenements Wyscout 2017-2018 (Pappalardo et al., Scientific Data).
Licence CC BY 4.0, telechargement Figshare officiel (pas de scrape).

Couverture : les 5 ligues, saison 2017-2018 complete uniquement.
Pas de xG, pas de pressions, pas de recoveries explicites.
Absent : toute autre saison, dont 2025-2026.
"""

import json
import sys
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from defense_commune import (
    COLONNES_COUVERTURE,
    COLONNES_DEFENSE,
    FICHIER_COUVERTURE,
    FICHIER_DEFENSE,
    ecrire_csv,
    lire_csv,
    ligne_defense,
    remplacer_source,
    stats_vides,
)

SOURCE = "wyscout"
SAISON = "2017-2018"
DOSSIER_CACHE = Path("donnees/cache_wyscout")
SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "StatsChampionnats/1.0 (projet local; Wyscout open dataset CC-BY)"
    }
)

# Figshare collection 4415000 / article fichiers documentes par le README communautaire.
URLS = {
    "joueurs.json": "https://ndownloader.figshare.com/files/15073721",
    "equipes.json": "https://ndownloader.figshare.com/files/15073697",
    "evenements.zip": "https://ndownloader.figshare.com/files/14464685",
}
FICHIERS_LIGUES = {
    "England": "Premier League",
    "Spain": "La Liga",
    "Germany": "Bundesliga",
    "Italy": "Serie A",
    "France": "Ligue 1",
}
TAG_GAGNE = 703
TAG_INTERCEPTION = 1401
TAG_BLOC = 2101
TAG_TACLE_GLISSE = 1703


def telecharger(nom_fichier, url):
    chemin = DOSSIER_CACHE / nom_fichier
    if chemin.exists() and chemin.stat().st_size > 1000:
        print(f"   cache {nom_fichier}")
        return chemin
    print(f"   telechargement {nom_fichier}...")
    DOSSIER_CACHE.mkdir(parents=True, exist_ok=True)
    with SESSION.get(url, timeout=180, stream=True) as reponse:
        reponse.raise_for_status()
        with open(chemin, "wb") as fichier:
            for morceau in reponse.iter_content(chunk_size=1024 * 256):
                if morceau:
                    fichier.write(morceau)
    print(f"      {chemin.stat().st_size} octets")
    return chemin


def extraire_zip(chemin_zip, sous_dossier):
    cible = DOSSIER_CACHE / sous_dossier
    if cible.exists() and any(cible.glob("*.json")):
        return cible
    cible.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(chemin_zip) as archive:
        archive.extractall(cible)
    return cible


def lire_json(chemin):
    with open(chemin, encoding="utf-8") as fichier:
        return json.load(fichier)


def nom_joueur(fiche):
    prenom = (fiche.get("firstName") or "").strip()
    nom = (fiche.get("lastName") or "").strip()
    complet = f"{prenom} {nom}".strip()
    return complet or (fiche.get("shortName") or "").strip()


def ids_tags(evenement):
    return {tag.get("id") for tag in (evenement.get("tags") or [])}


def trouver_json(dossier, motif):
    for chemin in Path(dossier).rglob("*.json"):
        if motif.lower() in chemin.name.lower():
            return chemin
    return None


def collecter():
    print("Wyscout 2017-2018 (Figshare, CC BY)...")
    joueurs_bruts = lire_json(telecharger("joueurs.json", URLS["joueurs.json"]))
    equipes_brutes = lire_json(telecharger("equipes.json", URLS["equipes.json"]))
    dossier_ev = extraire_zip(
        telecharger("evenements.zip", URLS["evenements.zip"]), "evenements"
    )

    noms_joueurs = {j.get("wyId"): nom_joueur(j) for j in joueurs_bruts}
    noms_equipes = {}
    for equipe in equipes_brutes:
        noms_equipes[equipe.get("wyId")] = (equipe.get("name") or "").strip()

    fusion = {}
    couverture = []
    for pays, championnat in FICHIERS_LIGUES.items():
        chemin_ev = trouver_json(dossier_ev, f"events_{pays}")
        if not chemin_ev:
            print(f"   {championnat}: fichier evenements absent")
            continue
        print(f"   {championnat}...")
        evenements = lire_json(chemin_ev)
        matchs_ids = set()
        for ev in evenements:
            match_id = ev.get("matchId")
            joueur_id = ev.get("playerId")
            equipe_id = ev.get("teamId")
            nom = noms_joueurs.get(joueur_id) or ""
            equipe = noms_equipes.get(equipe_id) or ""
            if not nom or not equipe:
                continue
            matchs_ids.add(match_id)
            cle = (championnat, equipe, nom)
            if cle not in fusion:
                fusion[cle] = stats_vides()
            stats = fusion[cle]
            stats["matchs_ids"].add(match_id)
            tags = ids_tags(ev)
            nom_ev = ev.get("eventName") or ""
            sous = ev.get("subEventName") or ""
            if nom_ev == "Duel":
                stats["duels"] += 1
                if TAG_GAGNE in tags:
                    stats["duels_gagnes"] += 1
                if sous == "Ground defending duel":
                    stats["tacles"] += 1
                    if TAG_GAGNE in tags:
                        stats["tacles_reussis"] += 1
            if TAG_TACLE_GLISSE in tags and sous != "Ground defending duel":
                stats["tacles"] += 1
            if TAG_INTERCEPTION in tags:
                stats["interceptions"] += 1
            if TAG_BLOC in tags:
                stats["blocs"] += 1
            if sous == "Clearance":
                stats["degagements"] += 1
            if nom_ev == "Save attempt":
                stats["arrets"] += 1
        couverture.append(
            {
                "championnat": championnat,
                "saison": SAISON,
                "source": SOURCE,
                "nb_matchs": len(matchs_ids),
                "complet": 1,
                "commentaire": (
                    "Saison 2017-2018 complete. Pas de xG, pressions ni recoveries "
                    "dans ce jeu."
                ),
            }
        )
        print(f"      {len(matchs_ids)} matchs, evenements lus")

    lignes = [
        ligne_defense(championnat, SAISON, equipe, joueur, stats, SOURCE)
        for (championnat, equipe, joueur), stats in fusion.items()
    ]
    remplacer_source(FICHIER_DEFENSE, SOURCE, lignes, COLONNES_DEFENSE)
    anciennes = [l for l in lire_csv(FICHIER_COUVERTURE) if l.get("source") != SOURCE]
    ecrire_csv(FICHIER_COUVERTURE, anciennes + couverture, COLONNES_COUVERTURE)
    print(f"   {len(lignes)} lignes joueurs defensifs Wyscout")
    return lignes, couverture


def main():
    collecter()
    print("Wyscout termine. Uniquement 2017-2018, pas les 5 ligues actuelles.")


if __name__ == "__main__":
    main()
