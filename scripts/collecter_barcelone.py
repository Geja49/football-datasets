"""
Collecte simple pour le FC Barcelone :
- matchs Liga : fichiers locaux datasets/la-liga
- stats joueurs : Understat (buts, passes, xG)
"""

import csv
from pathlib import Path

import requests

CLUB = "Barcelona"
DOSSIER_LIGA = Path("datasets/la-liga")
DOSSIER_SORTIE = Path("donnees/barcelone")
SAISON_UNDERSTAT = "2025"
URL_PAGE = f"https://understat.com/team/Barcelona/{SAISON_UNDERSTAT}"
URL_JOUEURS = f"https://understat.com/getTeamData/Barcelona/{SAISON_UNDERSTAT}"


def annee_debut(fichier):
    code = fichier.stem.replace("season-", "")[:2]
    annee = int(code)
    return 1900 + annee if annee >= 69 else 2000 + annee


def collecter_matchs():
    matchs = []
    fichiers = sorted(DOSSIER_LIGA.glob("season-*.csv"), key=annee_debut)
    for fichier in fichiers:
        saison = fichier.stem.replace("season-", "")
        with open(fichier, newline="", encoding="utf-8", errors="replace") as f:
            for ligne in csv.DictReader(f):
                domicile = (ligne.get("HomeTeam") or "").strip()
                exterieur = (ligne.get("AwayTeam") or "").strip()
                if CLUB not in (domicile, exterieur):
                    continue
                a_domicile = domicile == CLUB
                buts_barca = ligne.get("FTHG") if a_domicile else ligne.get("FTAG")
                buts_adversaire = ligne.get("FTAG") if a_domicile else ligne.get("FTHG")
                resultat_ligne = (ligne.get("FTR") or "").strip()
                if resultat_ligne == "D":
                    resultat = "N"
                elif (resultat_ligne == "H" and a_domicile) or (
                    resultat_ligne == "A" and not a_domicile
                ):
                    resultat = "V"
                else:
                    resultat = "D"
                matchs.append(
                    {
                        "saison": saison,
                        "date": ligne.get("Date", ""),
                        "lieu": "domicile" if a_domicile else "exterieur",
                        "adversaire": exterieur if a_domicile else domicile,
                        "buts_barca": buts_barca,
                        "buts_adversaire": buts_adversaire,
                        "resultat": resultat,
                        "tirs_barca": ligne.get("HS") if a_domicile else ligne.get("AS"),
                        "tirs_adversaire": ligne.get("AS") if a_domicile else ligne.get("HS"),
                        "tirs_cadres_barca": ligne.get("HST") if a_domicile else ligne.get("AST"),
                        "corners_barca": ligne.get("HC") if a_domicile else ligne.get("AC"),
                        "jaunes_barca": ligne.get("HY") if a_domicile else ligne.get("AY"),
                        "rouges_barca": ligne.get("HR") if a_domicile else ligne.get("AR"),
                        "arbitre": ligne.get("Referee", ""),
                    }
                )
    return matchs


def arrondi(valeur, decimales=2):
    try:
        return round(float(valeur), decimales)
    except (TypeError, ValueError):
        return 0


def collecter_joueurs():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )
    session.get(URL_PAGE, timeout=30)
    reponse = session.get(
        URL_JOUEURS,
        headers={"X-Requested-With": "XMLHttpRequest"},
        timeout=30,
    )
    reponse.raise_for_status()
    donnees = reponse.json().get("players") or []
    if not donnees:
        raise ValueError("Aucun joueur renvoye par Understat.")

    joueurs = []
    for j in donnees:
        joueurs.append(
            {
                "joueur": j.get("player_name", ""),
                "poste": j.get("position", ""),
                "matchs": j.get("games", ""),
                "minutes": j.get("time", ""),
                "buts": j.get("goals", ""),
                "passes_decisives": j.get("assists", ""),
                "tirs": j.get("shots", ""),
                "passes_cles": j.get("key_passes", ""),
                "xg": arrondi(j.get("xG")),
                "xa": arrondi(j.get("xA")),
                "buts_hors_penalty": j.get("npg", ""),
                "carton_jaune": j.get("yellow_cards", ""),
                "carton_rouge": j.get("red_cards", ""),
            }
        )
    joueurs.sort(key=lambda x: int(x["buts"] or 0), reverse=True)
    return joueurs


def ecrire_csv(chemin, lignes):
    if not lignes:
        return
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        writer.writeheader()
        writer.writerows(lignes)


def resume_matchs(matchs):
    saison = matchs[-1]["saison"] if matchs else ""
    actuels = [m for m in matchs if m["saison"] == saison]
    victoires = sum(1 for m in actuels if m["resultat"] == "V")
    nuls = sum(1 for m in actuels if m["resultat"] == "N")
    defaites = sum(1 for m in actuels if m["resultat"] == "D")
    buts = sum(int(m["buts_barca"] or 0) for m in actuels)
    return saison, actuels, victoires, nuls, defaites, buts


def main():
    matchs = collecter_matchs()
    ecrire_csv(DOSSIER_SORTIE / "matchs_liga.csv", matchs)
    saison, actuels, victoires, nuls, defaites, buts = resume_matchs(matchs)
    print(f"Matchs Liga collectes : {len(matchs)}")
    print(f"Saison {saison} : {len(actuels)} matchs  {victoires}V-{nuls}N-{defaites}D  {buts} buts")
    print(f"Fichier : {DOSSIER_SORTIE / 'matchs_liga.csv'}")
    print()

    joueurs = collecter_joueurs()
    ecrire_csv(DOSSIER_SORTIE / "joueurs_2025_2026.csv", joueurs)
    print(f"Joueurs Understat {SAISON_UNDERSTAT}-{int(SAISON_UNDERSTAT)+1} : {len(joueurs)}")
    print(f"Fichier : {DOSSIER_SORTIE / 'joueurs_2025_2026.csv'}")
    print()
    print(f"{'Joueur':<22} {'Poste':<6} {'M':>3} {'Buts':>5} {'PD':>4} {'xG':>6}")
    for j in joueurs[:12]:
        print(
            f"{j['joueur']:<22} {j['poste']:<6} {j['matchs']:>3} "
            f"{j['buts']:>5} {j['passes_decisives']:>4} {float(j['xg'] or 0):>6.1f}"
        )


if __name__ == "__main__":
    main()
