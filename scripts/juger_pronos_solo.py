"""
Juge les pronos Solo figés une fois les scores en football.db.

Usage (à la racine du projet) :
    python scripts/juger_pronos_solo.py
    python scripts/juger_pronos_solo.py --weekend 2026-08-28

À lancer après le weekend (lundi/mardi) ou après mise à jour des résultats.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
DOSSIER_API = RACINE / "site" / "api"
FICHIER_FOOTBALL = RACINE / "donnees" / "football.db"
FICHIER_ANALYSES = RACINE / "donnees" / "analyses.db"

if str(DOSSIER_API) not in sys.path:
    sys.path.insert(0, str(DOSSIER_API))

from services.solo_fige import juger_pronos_weekend  # noqa: E402


def ouvrir_football() -> sqlite3.Connection:
    if not FICHIER_FOOTBALL.is_file():
        raise FileNotFoundError(f"Base introuvable : {FICHIER_FOOTBALL}")
    connexion = sqlite3.connect(str(FICHIER_FOOTBALL))
    connexion.row_factory = sqlite3.Row
    return connexion


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(
        description="Juge les pronos Solo figés (vrai/faux + motifs)",
    )
    parseur.add_argument(
        "--weekend",
        dest="weekend",
        default=None,
        help="Vendredi du weekend (YYYY-MM-DD). Défaut : tous les pronos sans verdict.",
    )
    args = parseur.parse_args(argv)

    connexion_foot = ouvrir_football()
    try:
        resume = juger_pronos_weekend(
            connexion_foot,
            date_debut=args.weekend,
            chemin_analyses=FICHIER_ANALYSES,
        )
    finally:
        connexion_foot.close()

    cible = resume["weekend_debut"] or "tous weekends"
    print(f"Jugement Solo — {cible}")
    print(
        f"{resume['nb_juges']} marché(s) jugé(s) "
        f"({resume['nb_vrais']} vrais / {resume['nb_faux']} faux)"
    )
    if resume["hit_rate"] is not None:
        print(f"Hit-rate : {resume['hit_rate']} %")
    if resume["nb_attente_score"]:
        print(f"En attente de score : {resume['nb_attente_score']}")
    if resume["nb_non_jugables"]:
        print(f"Non jugables (données manquantes) : {resume['nb_non_jugables']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
