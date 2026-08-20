"""
Presaison 2026-27 du FC Barcelone.
Les amicaux ne sont pas dans football-data.co.uk ni Understat.
Sources : site officiel, Wikipedia, comptes rendus de match.
"""

import csv
from collections import defaultdict
from pathlib import Path

DOSSIER_SORTIE = Path("donnees/barcelone")

MATCHS = [
    {
        "date": "2026-07-24",
        "competition": "Amiable",
        "lieu": "domicile",
        "adversaire": "CE Europa",
        "buts_barca": 4,
        "buts_adversaire": 1,
        "resultat": "V",
        "duree_minutes": 90,
        "stade": "Ciutat Esportiva Joan Gamper",
        "ville": "Sant Joan Despí",
        "buteurs_barca": "Ibrahim Diarra; Héctor Fort; Ebrima Tunkara; Álex González",
        "note": "Huis clos, beaucoup de jeunes",
    },
    {
        "date": "2026-07-31",
        "competition": "Amiable",
        "lieu": "exterieur",
        "adversaire": "Birmingham City",
        "buts_barca": 2,
        "buts_adversaire": 2,
        "resultat": "N",
        "duree_minutes": 90,
        "stade": "St Andrew's",
        "ville": "Birmingham",
        "buteurs_barca": "Hamza Abdelkarim (pen); Hamza Abdelkarim",
        "note": "Perdu 3-2 aux tirs au but",
    },
    {
        "date": "2026-08-08",
        "competition": "Friuli Venezia Giulia Cup",
        "lieu": "neutre",
        "adversaire": "Nottingham Forest",
        "buts_barca": 1,
        "buts_adversaire": 0,
        "resultat": "V",
        "duree_minutes": 45,
        "stade": "Stadio Friuli",
        "ville": "Udine",
        "buteurs_barca": "Raphinha (pen)",
        "note": "Match de 45 minutes, tournoi a 3",
    },
    {
        "date": "2026-08-08",
        "competition": "Friuli Venezia Giulia Cup",
        "lieu": "neutre",
        "adversaire": "Udinese",
        "buts_barca": 0,
        "buts_adversaire": 1,
        "resultat": "D",
        "duree_minutes": 45,
        "stade": "Stadio Friuli",
        "ville": "Udine",
        "buteurs_barca": "",
        "note": "Match de 45 minutes, 1ere defaite de presaison",
    },
    {
        "date": "2026-08-16",
        "competition": "Amiable",
        "lieu": "exterieur",
        "adversaire": "FC Basel",
        "buts_barca": 5,
        "buts_adversaire": 2,
        "resultat": "V",
        "duree_minutes": 90,
        "stade": "St. Jakob-Park",
        "ville": "Bâle",
        "buteurs_barca": "Karim Adeyemi; Hamza Abdelkarim; Lamine Yamal (pen); Jesse Bisiwu; Jesse Bisiwu",
        "note": "1er match d'Anthony Gordon",
    },
    {
        "date": "2026-08-19",
        "competition": "Trophee Joan Gamper",
        "lieu": "domicile",
        "adversaire": "Al Ahly",
        "buts_barca": 2,
        "buts_adversaire": 1,
        "resultat": "V",
        "duree_minutes": 90,
        "stade": "Spotify Camp Nou",
        "ville": "Barcelone",
        "buteurs_barca": "Hamza Abdelkarim; Raphinha (pen)",
        "note": "Fin de presaison, 54224 spectateurs. Gordon rate un penalty",
    },
]


def extraire_nom(buteur):
    return buteur.replace(" (pen)", "").strip()


def stats_buteurs(matchs):
    compteur = defaultdict(lambda: {"buts": 0, "penalties": 0})
    for match in matchs:
        if not match["buteurs_barca"]:
            continue
        for buteur in match["buteurs_barca"].split(";"):
            buteur = buteur.strip()
            if not buteur:
                continue
            nom = extraire_nom(buteur)
            compteur[nom]["buts"] += 1
            if "(pen)" in buteur:
                compteur[nom]["penalties"] += 1
    lignes = [
        {"joueur": nom, "buts": stats["buts"], "penalties": stats["penalties"]}
        for nom, stats in compteur.items()
    ]
    return sorted(lignes, key=lambda x: (-x["buts"], x["joueur"]))


def ecrire_csv(chemin, lignes):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", newline="", encoding="utf-8") as fichier:
        writer = csv.DictWriter(fichier, fieldnames=list(lignes[0].keys()))
        writer.writeheader()
        writer.writerows(lignes)


def main():
    buteurs = stats_buteurs(MATCHS)
    ecrire_csv(DOSSIER_SORTIE / "matchs_presaison.csv", MATCHS)
    ecrire_csv(DOSSIER_SORTIE / "buteurs_presaison.csv", buteurs)

    victoires = sum(1 for m in MATCHS if m["resultat"] == "V")
    nuls = sum(1 for m in MATCHS if m["resultat"] == "N")
    defaites = sum(1 for m in MATCHS if m["resultat"] == "D")
    buts = sum(m["buts_barca"] for m in MATCHS)
    buts_contre = sum(m["buts_adversaire"] for m in MATCHS)

    print("Presaison 2026-27 du Barca")
    print(f"Matchs : {len(MATCHS)}  {victoires}V-{nuls}N-{defaites}D")
    print(f"Buts : {buts} pour, {buts_contre} contre")
    print(f"Fichier : {DOSSIER_SORTIE / 'matchs_presaison.csv'}")
    print()
    print(f"{'Date':<12} {'Adv.':<20} {'Score':<7} {'Comp.'}")
    for m in MATCHS:
        score = f"{m['buts_barca']}-{m['buts_adversaire']}"
        print(f"{m['date']:<12} {m['adversaire']:<20} {score:<7} {m['competition']}")
    print()
    print("Buteurs Barca")
    for b in buteurs:
        print(f"  {b['joueur']:<22} {b['buts']} buts")
    print()
    print("Limite : pas de xG / tirs / minutes par joueur sur les amicaux publics.")


if __name__ == "__main__":
    main()
