"""
Met a jour les 5 championnats et la Ligue des champions, puis recree SQLite.

Usage (a la racine du projet) :
    python scripts/mettre_a_jour.py

Ne lancez pas ce script si une collecte est deja en cours.
"""

import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def lancer(nom_script):
    print(f"\n=== {nom_script} ===")
    resultat = subprocess.run(
        [sys.executable, str(RACINE / "scripts" / nom_script)],
        cwd=RACINE,
    )
    if resultat.returncode != 0:
        sys.exit(resultat.returncode)


def main():
    lancer("collecter_cinq_championnats.py")
    lancer("collecter_ligue_champions.py")
    lancer("creer_base.py")
    print("\nTermine. Rechargez la page du site (localhost:5173).")
    print(
        "Pour rester a jour ensuite : python scripts/surveiller_sources.py"
    )
    print(
        "Si un match du jour manque encore : football-data.co.uk "
        "publie souvent avec 1 a 2 jours de retard."
    )
    print(
        "Le calendrier a venir des 5 ligues vient d'Understat "
        "(pas toujours les 38 journees en aout) et de fixtures.csv pour la semaine."
    )
    print(
        "La Ligue des champions vient d'openfootball (GitHub), depuis 2020-2021. "
        "Pas de xG. La saison 2026-2027 apparait quand le fichier est publie."
    )


if __name__ == "__main__":
    main()
