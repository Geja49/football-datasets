"""Inventaire des sources en base : ce qu'on a, ce qui manque."""

import sqlite3
from pathlib import Path

FICHIER_BASE = Path("donnees/football.db")


def main():
    if not FICHIER_BASE.exists():
        print("Base absente. Lancez python scripts/creer_base.py")
        return
    connexion = sqlite3.connect(FICHIER_BASE)
    print("=== Matchs ===")
    for row in connexion.execute(
        "SELECT championnat, MIN(saison), MAX(saison), COUNT(*) FROM matchs GROUP BY championnat"
    ):
        print(f"  {row[0]:22} {row[1]} -> {row[2]}  {row[3]} matchs")
    print("=== Joueurs (Understat, 5 ligues) ===")
    for row in connexion.execute(
        "SELECT championnat, MIN(saison), MAX(saison), COUNT(*) FROM joueurs GROUP BY championnat"
    ):
        print(f"  {row[0]:22} {row[1]} -> {row[2]}  {row[3]} lignes")
    ldc = connexion.execute(
        "SELECT COUNT(*) FROM joueurs WHERE championnat = 'Ligue des champions'"
    ).fetchone()[0]
    print(f"  LDC joueurs: {ldc} (0 = pas invente)")
    print("=== Defense ===")
    try:
        n = connexion.execute("SELECT COUNT(*) FROM actions_defensives").fetchone()[0]
        print(f"  {n} lignes actions_defensives")
        for row in connexion.execute(
            """
            SELECT championnat, saison, source, COUNT(*), SUM(tacles), SUM(interceptions)
            FROM actions_defensives
            GROUP BY championnat, saison, source
            ORDER BY saison, championnat
            """
        ):
            print(
                f"  {row[0]:22} {row[1]} {row[2]:12} "
                f"{row[3]} joueurs  tacles {row[4]}  interc. {row[5]}"
            )
    except sqlite3.OperationalError:
        print("  table actions_defensives absente")
    print("=== Couverture declaree ===")
    try:
        for row in connexion.execute(
            "SELECT championnat, saison, source, nb_matchs, complet, commentaire FROM couverture_sources"
        ):
            etat = "complet" if row[4] else "partiel"
            print(f"  {row[0]:22} {row[1]} {row[2]:12} {row[3]} matchs ({etat})")
            if row[5]:
                print(f"      {row[5]}")
    except sqlite3.OperationalError:
        print("  table couverture_sources absente")
    print("=== Toujours manquant (open data) ===")
    print("  5 ligues 2025-2026 : pas de tacles/interceptions/blocs/pressions/xG concédés joueur.")
    print("  LDC : scores openfootball ; pas de joueurs ni xG (sauf finales StatsBomb).")
    print("  PSxG gardien : absent (on a xG des tirs subis StatsBomb, pre-tir).")
    print("  Calendrier 38 journees : Understat ne le publie pas toujours en aout.")
    connexion.close()


if __name__ == "__main__":
    main()
