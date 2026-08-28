"""
Entraine le calibrateur 1X2 sur l'historique analyses.db.

Usage (a la racine du projet) :
    python scripts/entrainer_calibrateur.py
    python scripts/entrainer_calibrateur.py --saison 2026-2027
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
DOSSIER_API = RACINE / "site" / "api"
SAISON_DEFAUT = "2026-2027"

if str(DOSSIER_API) not in sys.path:
    sys.path.insert(0, str(DOSSIER_API))

from calibrateur import SEUIL_MIN_MATCHS, entrainer_calibrateur  # noqa: E402
from historique_analyses import ouvrir_base  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Entraine le calibrateur automatique sur analyses.db."
    )
    parser.add_argument(
        "--saison",
        default=None,
        help=f"Filtrer une saison (defaut : toutes les saisons, min {SEUIL_MIN_MATCHS} matchs)",
    )
    parser.add_argument(
        "--fichier-analyses",
        default=None,
        help="Chemin alternatif pour analyses.db",
    )
    args = parser.parse_args()

    chemin = Path(args.fichier_analyses) if args.fichier_analyses else None
    connexion = ouvrir_base(chemin)
    try:
        resume = entrainer_calibrateur(connexion, saison=args.saison)
    finally:
        connexion.close()

    print("=== Calibrateur automatique ===")
    print(f"Matchs honnetes (retroactif=0) : {resume['nb_matchs']}")
    print(f"Seuil minimum                  : {resume['seuil_min']}")
    if args.saison:
        print(f"Saison filtree                 : {args.saison}")

    if resume["succes"]:
        print(f"Brier avant calibration        : {resume['brier_avant']}")
        print(f"Brier apres calibration        : {resume['brier_apres']}")
        print(f"Methode                        : {resume.get('methode', '?')}")
        print(resume["message"])
    else:
        print(resume["message"])

    return 0 if resume["succes"] or resume["nb_matchs"] < SEUIL_MIN_MATCHS else 1


if __name__ == "__main__":
    sys.exit(main())
