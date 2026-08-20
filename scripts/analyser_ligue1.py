import csv
from collections import defaultdict
from pathlib import Path

DOSSIER_LIGUE1 = Path("datasets/ligue-1")


def annee_debut(fichier):
    """season-2526.csv -> 2025, season-9900.csv -> 1999."""
    code = fichier.stem.replace("season-", "")[:2]
    annee = int(code)
    return 1900 + annee if annee >= 69 else 2000 + annee


def lire_matchs(chemin):
    matchs = []
    with open(chemin, newline="", encoding="utf-8", errors="replace") as fichier:
        for ligne in csv.DictReader(fichier):
            if not (ligne.get("Date") or "").strip():
                continue
            try:
                buts_domicile = int(ligne["FTHG"])
                buts_exterieur = int(ligne["FTAG"])
            except (ValueError, KeyError):
                continue
            matchs.append(
                {
                    "date": ligne["Date"],
                    "domicile": ligne["HomeTeam"],
                    "exterieur": ligne["AwayTeam"],
                    "buts_domicile": buts_domicile,
                    "buts_exterieur": buts_exterieur,
                    "resultat": (ligne.get("FTR") or "").strip(),
                }
            )
    return matchs


def afficher_saisons(fichiers):
    print("=== 5 dernieres saisons ===")
    print(
        f"{'Saison':<14} {'Matchs':>7} {'Buts':>7} {'Moy':>6} "
        f"{'Vic.dom':>8} {'Nuls':>6} {'Vic.ext':>8}"
    )
    for fichier in fichiers[-5:]:
        matchs = lire_matchs(fichier)
        buts = sum(m["buts_domicile"] + m["buts_exterieur"] for m in matchs)
        victoires_domicile = sum(1 for m in matchs if m["resultat"] == "H")
        nuls = sum(1 for m in matchs if m["resultat"] == "D")
        victoires_exterieur = sum(1 for m in matchs if m["resultat"] == "A")
        moyenne = buts / len(matchs) if matchs else 0
        print(
            f"{fichier.stem:<14} {len(matchs):>7} {buts:>7} {moyenne:>6.2f} "
            f"{victoires_domicile:>8} {nuls:>6} {victoires_exterieur:>8}"
        )


def classement(matchs):
    stats = defaultdict(
        lambda: {"j": 0, "v": 0, "n": 0, "d": 0, "bp": 0, "bc": 0, "pts": 0}
    )

    def ajouter(equipe, buts_pour, buts_contre, points, victoire, nul, defaite):
        ligne = stats[equipe]
        ligne["j"] += 1
        ligne["v"] += victoire
        ligne["n"] += nul
        ligne["d"] += defaite
        ligne["bp"] += buts_pour
        ligne["bc"] += buts_contre
        ligne["pts"] += points

    for match in matchs:
        if match["resultat"] == "H":
            ajouter(match["domicile"], match["buts_domicile"], match["buts_exterieur"], 3, 1, 0, 0)
            ajouter(match["exterieur"], match["buts_exterieur"], match["buts_domicile"], 0, 0, 0, 1)
        elif match["resultat"] == "A":
            ajouter(match["domicile"], match["buts_domicile"], match["buts_exterieur"], 0, 0, 0, 1)
            ajouter(match["exterieur"], match["buts_exterieur"], match["buts_domicile"], 3, 1, 0, 0)
        else:
            ajouter(match["domicile"], match["buts_domicile"], match["buts_exterieur"], 1, 0, 1, 0)
            ajouter(match["exterieur"], match["buts_exterieur"], match["buts_domicile"], 1, 0, 1, 0)

    return sorted(
        stats.items(),
        key=lambda item: (item[1]["pts"], item[1]["bp"] - item[1]["bc"], item[1]["bp"]),
        reverse=True,
    )


def main():
    fichiers = sorted(DOSSIER_LIGUE1.glob("season-*.csv"), key=annee_debut)
    print(f"Fichiers Ligue 1: {len(fichiers)}")
    print(f"Plus recent: {fichiers[-1].name}")
    print()
    afficher_saisons(fichiers)

    fichier_actuel = fichiers[-1]
    matchs = lire_matchs(fichier_actuel)
    lignes = classement(matchs)

    print()
    print(f"=== Classement {fichier_actuel.stem} ===")
    print(f"Premier match: {matchs[0]['date']}  |  Dernier match: {matchs[-1]['date']}")
    print(
        f"{'#':<3} {'Equipe':<18} {'Pts':>4} {'J':>3} {'V':>3} "
        f"{'N':>3} {'D':>3} {'BP':>4} {'BC':>4} {'Diff':>5}"
    )
    for rang, (equipe, stats) in enumerate(lignes, start=1):
        diff = stats["bp"] - stats["bc"]
        print(
            f"{rang:<3} {equipe:<18} {stats['pts']:>4} {stats['j']:>3} "
            f"{stats['v']:>3} {stats['n']:>3} {stats['d']:>3} "
            f"{stats['bp']:>4} {stats['bc']:>4} {diff:>5}"
        )

    print()
    print("=== 5 derniers matchs ===")
    for match in matchs[-5:]:
        print(
            f"{match['date']}  {match['domicile']} "
            f"{match['buts_domicile']}-{match['buts_exterieur']} {match['exterieur']}"
        )


if __name__ == "__main__":
    main()
