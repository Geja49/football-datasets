"""
StatsBomb Open Data (GitHub statsbomb/open-data, licence ouverte).

Perimetre reel (verifie sur competitions.json + listes de matchs, 2026) :
- Saisons quasi completes : PL / La Liga / Ligue 1 / Serie A 2015-2016.
- Saisons partielles : Bundesliga 2015-16 et 2023-24 (~34 matchs),
  La Liga 2004-2021 surtout un club, Ligue 1 2021-23, PL 2003-04.
- LDC : 1 match par saison (finale), pas le tournoi entier.
- Absent : 5 ligues 2024-25 et 2025-26.

Pas de scrape. Pause + cache. Les JSON d'evenements ne sont pas conserves.
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "site" / "api"))
from correspondances import nom_pour_calendrier
from defense_commune import (
    COLONNES_COUVERTURE,
    COLONNES_DEFENSE,
    DOSSIER_SORTIE,
    FICHIER_COUVERTURE,
    FICHIER_DEFENSE,
    ecrire_csv,
    lire_csv,
    ligne_defense,
    remplacer_source,
    saison_tirets,
    stats_vides,
)

URL_BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
DOSSIER_CACHE = Path("donnees/cache_statsbomb")
DOSSIER_AGREGATS = DOSSIER_CACHE / "agregats"
SOURCE = "statsbomb"
PAUSE = 0.08
NB_WORKERS = 4
TACLES_REUSSIS = {"Won", "Success In Play", "Success Out"}
ARRETS = {"Shot Saved", "Penalty Saved", "Saved To Post", "Save"}
NOMS_CIBLES = {
    "1. Bundesliga": "Bundesliga",
    "Premier League": "Premier League",
    "La Liga": "La Liga",
    "Ligue 1": "Ligue 1",
    "Serie A": "Serie A",
    "Champions League": "Ligue des champions",
}
SEUIL_COMPLET = 300
SESSION = requests.Session()
SESSION.headers.update(
    {"User-Agent": "StatsChampionnats/1.0 (projet local; StatsBomb open-data)"}
)


def telecharger_json(url, chemin, essais=3):
    if chemin.exists():
        return json.loads(chemin.read_text(encoding="utf-8"))
    dernier = None
    for essai in range(essais):
        try:
            reponse = SESSION.get(url, timeout=60)
        except requests.RequestException as exc:
            dernier = exc
            time.sleep(2 * (essai + 1))
            continue
        if reponse.status_code == 429:
            time.sleep(8 * (essai + 1))
            continue
        if reponse.status_code != 200:
            dernier = f"HTTP {reponse.status_code}"
            time.sleep(1)
            continue
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_bytes(reponse.content)
        time.sleep(PAUSE)
        return json.loads(reponse.content.decode("utf-8"))
    print(f"   echec {url} ({dernier})")
    return None


def competitions_cibles():
    chemin = DOSSIER_CACHE / "competitions.json"
    data = telecharger_json(f"{URL_BASE}/competitions.json", chemin)
    if not data:
        return []
    cibles = []
    for ligne in data:
        nom = ligne.get("competition_name")
        if nom not in NOMS_CIBLES:
            continue
        if ligne.get("competition_gender") != "male":
            continue
        cibles.append(ligne)
    return cibles


def nom_type(evenement):
    return ((evenement.get("type") or {}).get("name")) or ""


def nom_joueur(evenement):
    return ((evenement.get("player") or {}).get("name")) or ""


def nom_equipe(evenement):
    return ((evenement.get("team") or {}).get("name")) or ""


def id_equipe(evenement):
    return (evenement.get("team") or {}).get("id")


def extraire_agregat(evenements, contexte):
    """Compte les actions defensives d'un match. Gardien : arrets + xG des tirs subis."""
    par_joueur = {}
    gardiens = {}
    xg_domicile = 0.0
    xg_exterieur = 0.0
    home_id = contexte["home_id"]
    away_id = contexte["away_id"]
    match_id = contexte["match_id"]

    def bac(joueur, equipe):
        cle = (joueur, equipe)
        if cle not in par_joueur:
            par_joueur[cle] = stats_vides()
        return par_joueur[cle]

    for ev in evenements:
        type_nom = nom_type(ev)
        if type_nom == "Starting XI":
            equipe = nom_equipe(ev)
            tid = id_equipe(ev)
            for joueur_l in (ev.get("tactics") or {}).get("lineup") or []:
                poste = ((joueur_l.get("position") or {}).get("name")) or ""
                nom = ((joueur_l.get("player") or {}).get("name")) or ""
                if poste == "Goalkeeper" and nom:
                    gardiens[tid] = (nom, equipe)
            continue
        if type_nom == "Substitution":
            sortant = nom_joueur(ev)
            tid = id_equipe(ev)
            actuel = gardiens.get(tid)
            if actuel and actuel[0] == sortant:
                remplacant = ((ev.get("substitution") or {}).get("replacement") or {}).get(
                    "name"
                ) or ""
                if remplacant:
                    gardiens[tid] = (remplacant, nom_equipe(ev))
            continue

        joueur = nom_joueur(ev)
        equipe = nom_equipe(ev)
        if type_nom == "Shot":
            xg = float((ev.get("shot") or {}).get("statsbomb_xg") or 0)
            tid = id_equipe(ev)
            if tid == home_id:
                xg_domicile += xg
            else:
                xg_exterieur += xg
            autre = away_id if tid == home_id else home_id
            gardien = gardiens.get(autre)
            if gardien:
                stats = bac(gardien[0], gardien[1])
                stats["matchs_ids"].add(match_id)
                stats["xg_tirs_subis"] += xg
            continue

        if not joueur or not equipe:
            continue
        stats = bac(joueur, equipe)
        stats["matchs_ids"].add(match_id)
        if type_nom == "Duel":
            stats["duels"] += 1
            duel = ev.get("duel") or {}
            issue = ((duel.get("outcome") or {}).get("name")) or ""
            if issue in TACLES_REUSSIS or issue == "Won":
                stats["duels_gagnes"] += 1
            if ((duel.get("type") or {}).get("name")) == "Tackle":
                stats["tacles"] += 1
                if issue in TACLES_REUSSIS:
                    stats["tacles_reussis"] += 1
        elif type_nom == "Interception":
            stats["interceptions"] += 1
        elif type_nom == "Block":
            stats["blocs"] += 1
        elif type_nom == "Clearance":
            stats["degagements"] += 1
        elif type_nom == "Ball Recovery":
            stats["recoveries"] += 1
        elif type_nom == "Pressure":
            stats["pressions"] += 1
        elif type_nom == "Goal Keeper":
            sous = ((ev.get("goalkeeper") or {}).get("type") or {}).get("name") or ""
            if sous in ARRETS:
                stats["arrets"] += 1

    joueurs = []
    for (joueur, equipe), stats in par_joueur.items():
        joueurs.append(
            ligne_defense(
                contexte["championnat"],
                contexte["saison"],
                equipe,
                joueur,
                stats,
                SOURCE,
            )
        )
    return {
        "joueurs": joueurs,
        "xg_domicile": round(xg_domicile, 2),
        "xg_exterieur": round(xg_exterieur, 2),
        "date": contexte["date"],
        "domicile": contexte["domicile"],
        "exterieur": contexte["exterieur"],
        "championnat": contexte["championnat"],
        "saison": contexte["saison"],
    }


def chemin_agregat(match_id):
    return DOSSIER_AGREGATS / f"{match_id}.json"


def telecharger_evenements(match_id):
    url = f"{URL_BASE}/events/{match_id}.json"
    dernier = None
    for essai in range(3):
        try:
            reponse = requests.get(
                url,
                timeout=60,
                headers={
                    "User-Agent": "StatsChampionnats/1.0 (projet local; StatsBomb open-data)"
                },
            )
        except requests.RequestException as exc:
            dernier = exc
            time.sleep(2 * (essai + 1))
            continue
        if reponse.status_code == 429:
            time.sleep(8 * (essai + 1))
            continue
        if reponse.status_code != 200:
            dernier = f"HTTP {reponse.status_code}"
            time.sleep(1)
            continue
        time.sleep(PAUSE)
        return reponse.json()
    print(f"   evenements {match_id}: {dernier}")
    return None


def traiter_match(match, championnat, saison):
    match_id = match.get("match_id")
    cache = chemin_agregat(match_id)
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    evenements = telecharger_evenements(match_id)
    if evenements is None:
        return None
    contexte = {
        "match_id": match_id,
        "championnat": championnat,
        "saison": saison,
        "date": (match.get("match_date") or "")[:10],
        "domicile": ((match.get("home_team") or {}).get("home_team_name")) or "",
        "exterieur": ((match.get("away_team") or {}).get("away_team_name")) or "",
        "home_id": (match.get("home_team") or {}).get("home_team_id"),
        "away_id": (match.get("away_team") or {}).get("away_team_id"),
    }
    agregat = extraire_agregat(evenements, contexte)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(agregat), encoding="utf-8")
    return agregat


def noms_depuis_matchs(championnat, saison):
    noms = set()
    for ligne in lire_csv(DOSSIER_SORTIE / "matchs.csv"):
        if ligne.get("championnat") == championnat and ligne.get("saison") == saison:
            noms.add(ligne.get("domicile") or "")
            noms.add(ligne.get("exterieur") or "")
    noms.discard("")
    return noms


def fusionner_xg(agregats):
    existants = lire_csv(DOSSIER_SORTIE / "matchs_xg.csv")
    vus = {
        (l.get("championnat"), l.get("saison"), l.get("date"), l.get("domicile"), l.get("exterieur"))
        for l in existants
    }
    noms_par_cle = {}
    for ligne in lire_csv(DOSSIER_SORTIE / "matchs.csv"):
        cle_noms = (ligne.get("championnat"), ligne.get("saison"))
        noms_par_cle.setdefault(cle_noms, set()).update(
            [ligne.get("domicile") or "", ligne.get("exterieur") or ""]
        )
        noms_par_cle[cle_noms].discard("")
    ajouts = []
    for ag in agregats:
        if not ag or ag.get("xg_domicile") is None:
            continue
        cle_noms = (ag["championnat"], ag["saison"])
        if cle_noms not in noms_par_cle:
            noms_par_cle[cle_noms] = noms_depuis_matchs(ag["championnat"], ag["saison"])
        noms = noms_par_cle[cle_noms]
        domicile = nom_pour_calendrier(ag["domicile"], noms)
        exterieur = nom_pour_calendrier(ag["exterieur"], noms)
        cle = (ag["championnat"], ag["saison"], ag["date"], domicile, exterieur)
        if cle in vus:
            continue
        vus.add(cle)
        ajouts.append(
            {
                "championnat": ag["championnat"],
                "saison": ag["saison"],
                "date": ag["date"],
                "domicile": domicile,
                "exterieur": exterieur,
                "buts_domicile": "",
                "buts_exterieur": "",
                "xg_domicile": ag["xg_domicile"],
                "xg_exterieur": ag["xg_exterieur"],
                "resultat": "",
            }
        )
    if ajouts:
        ecrire_csv(DOSSIER_SORTIE / "matchs_xg.csv", existants + ajouts)
    return ajouts


def aggreguer_joueurs(agregats):
    fusion = {}
    for ag in agregats:
        if not ag:
            continue
        for ligne in ag.get("joueurs") or []:
            cle = (
                ligne["championnat"],
                ligne["saison"],
                ligne["equipe"],
                ligne["joueur"],
            )
            if cle not in fusion:
                fusion[cle] = dict(ligne)
                fusion[cle]["matchs"] = int(ligne.get("matchs") or 0)
                continue
            cible = fusion[cle]
            cible["matchs"] += int(ligne.get("matchs") or 0)
            for champ in (
                "tacles",
                "tacles_reussis",
                "interceptions",
                "blocs",
                "degagements",
                "duels",
                "duels_gagnes",
                "recoveries",
                "pressions",
                "arrets",
            ):
                cible[champ] = int(cible.get(champ) or 0) + int(ligne.get(champ) or 0)
            cible["xg_tirs_subis"] = round(
                float(cible.get("xg_tirs_subis") or 0) + float(ligne.get("xg_tirs_subis") or 0),
                2,
            )
    return list(fusion.values())


def commentaire_couverture(championnat, nb):
    if championnat == "Ligue des champions":
        return "Finale seulement (1 match), pas le tournoi entier."
    if nb >= SEUIL_COMPLET:
        return "Saison complete ou quasi complete dans l'open data."
    return "Saison partielle (souvent un seul club), pas les 38/34 journees."


def collecter():
    DOSSIER_AGREGATS.mkdir(parents=True, exist_ok=True)
    couverture = []
    tous_agregats = []
    print("StatsBomb Open Data (evenements defensifs)...")
    for comp in competitions_cibles():
        nom_source = comp["competition_name"]
        championnat = NOMS_CIBLES[nom_source]
        saison = saison_tirets(comp["season_name"])
        cid = comp["competition_id"]
        sid = comp["season_id"]
        matchs = telecharger_json(
            f"{URL_BASE}/matches/{cid}/{sid}.json",
            DOSSIER_CACHE / f"matchs_{cid}_{sid}.json",
        )
        if not matchs:
            continue
        if championnat != "Ligue des champions" and len(matchs) < 5:
            print(f"   {championnat} {saison}: {len(matchs)} matchs, ignore (curio)")
            continue
        print(f"   {championnat} {saison}: {len(matchs)} matchs...")
        faits = 0
        with ThreadPoolExecutor(max_workers=NB_WORKERS) as pool:
            futurs = [
                pool.submit(traiter_match, match, championnat, saison)
                for match in matchs
            ]
            for i, futur in enumerate(as_completed(futurs), 1):
                agregat = futur.result()
                if agregat:
                    tous_agregats.append(agregat)
                    faits += 1
                if i % 40 == 0 or i == len(matchs):
                    print(f"      {i}/{len(matchs)}")
        couverture.append(
            {
                "championnat": championnat,
                "saison": saison,
                "source": SOURCE,
                "nb_matchs": faits,
                "complet": 1 if faits >= SEUIL_COMPLET else 0,
                "commentaire": commentaire_couverture(championnat, faits),
            }
        )
    joueurs = aggreguer_joueurs(tous_agregats)
    remplacer_source(FICHIER_DEFENSE, SOURCE, joueurs, COLONNES_DEFENSE)
    anciennes_couv = [l for l in lire_csv(FICHIER_COUVERTURE) if l.get("source") != SOURCE]
    ecrire_csv(FICHIER_COUVERTURE, anciennes_couv + couverture, COLONNES_COUVERTURE)
    ajouts_xg = fusionner_xg(tous_agregats)
    print(f"   {len(joueurs)} lignes joueurs defensifs")
    print(f"   {len(ajouts_xg)} matchs xG ajoutes (absents d'Understat)")
    return joueurs, couverture


def main():
    collecter()
    print("StatsBomb termine. Les 5 ligues 2025-2026 ne sont pas dans ce dump.")


if __name__ == "__main__":
    main()
