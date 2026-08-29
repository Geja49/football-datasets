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


def lancer(nom_script, obligatoire=True):
    print(f"\n=== {nom_script} ===")
    resultat = subprocess.run(
        [sys.executable, str(RACINE / "scripts" / nom_script)],
        cwd=RACINE,
    )
    if resultat.returncode != 0 and obligatoire:
        sys.exit(resultat.returncode)
    if resultat.returncode != 0:
        print(f"{nom_script} a echoue, on continue avec les fichiers deja presents.")


def main():
    lancer("collecter_cinq_championnats.py")
    # Completer les 38 journees (Understat souvent partiel en aout).
    lancer("collecter_calendrier_openfootball.py", obligatoire=False)
    lancer("collecter_ligue_champions.py")
    # Joueurs / defense LDC historiques (OpenML 43510, CC0, 2013-2020).
    lancer("collecter_joueurs_ldc_openml.py", obligatoire=False)
    lancer("collecter_wyscout.py", obligatoire=False)
    lancer("collecter_statsbomb.py", obligatoire=False)
    lancer("collecter_api_football.py", obligatoire=False)
    # Elo clubs (api.clubelo.com) — ignore si timeout reseau.
    lancer("collecter_clubelo.py", obligatoire=False)
    # Valeurs de marche : re-telecharge le dump publie (pas de scrape Transfermarkt).
    lancer("collecter_valeurs_marche.py", obligatoire=False)
    lancer("creer_base.py")
    # Historique analyses (base separee) : ne doit pas faire echouer la MAJ.
    try:
        lancer("enregistrer_analyses.py", obligatoire=False)
    except Exception as erreur:  # noqa: BLE001
        print(f"enregistrer_analyses.py ignore ({erreur}), on continue.")
    # Solo : figer / juger / calibrer selon le jour (idempotent, non bloquant).
    try:
        lancer("boucle_amelioration.py", obligatoire=False)
    except Exception as erreur:  # noqa: BLE001
        print(f"boucle_amelioration.py ignore ({erreur}), on continue.")
    print("\nTermine. Rechargez la page du site (localhost:5173).")
    print(
        "Pour rester a jour ensuite : python scripts/surveiller_sources.py"
    )
    print(
        "Si un match du jour manque encore : football-data.co.uk "
        "publie souvent avec 1 a 2 jours de retard."
    )
    print(
        "Le calendrier a venir : Understat + fixtures.csv + openfootball "
        "(38 journees si publiees). Super Lig : fixtures.csv uniquement "
        "(pas de source Understat/openfootball)."
    )
    print(
        "La Ligue des champions vient d'openfootball (GitHub), depuis 2011-2012. "
        "Joueurs/defense LDC 2013-2020 : OpenML 43510 (CC0), sans xG. "
        "Pas de xG recente sauf finales StatsBomb. "
        "La saison 2026-2027 apparait quand openfootball la publie."
    )
    print(
        "Defense : Wyscout 2017-2018 (5 ligues) et StatsBomb open-data "
        "(surtout 2015-2016 + saisons partielles). "
        "Les 5 ligues 2025-2026 n'ont pas de tacles/interceptions en open data."
    )
    print(
        "ClubElo : classements_elo.csv si l'API repond "
        "(pas de FBref / Sofascore / WhoScored)."
    )
    print(
        "Valeurs de marche : dump CC0 transfermarkt-datasets "
        "(snapshot figé, matching noms Understat best-effort)."
    )
    print(
        "API-Football : si CLE_API_FOOTBALL est dans .env — fixtures/scores "
        "(rotation 1–2 ligues/jour + LDC si quota) puis stats joueurs ; "
        "sinon ignoree proprement. Free ~100 req/jour, cache disque."
    )


if __name__ == "__main__":
    main()
