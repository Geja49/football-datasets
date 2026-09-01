"""
Fige les marchés Solo (mêmes critères que la page live) dans analyses.db.

Critères : victoire 1/2 la plus probable, buts si potentiel > 2,
corners si total prévu > 8 — sans filtre d'exclusion 85 % / 75 %.
Le badge « haute confiance ≥ 85 % » reste informatif.

Usage (à la racine du projet) :
    python scripts/figer_pronos_solo.py
    python scripts/figer_pronos_solo.py --weekend 2026-08-28
    python scripts/figer_pronos_solo.py --weekend 2026-08-28 --forcer

Cron conseillé : vendredi avant le coup d'envoi (après mise à jour des données).
Peut aussi être enchaîné après `enregistrer_analyses.py` (voir note en fin de ce script).
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

from services.solo import vider_cache_solo  # noqa: E402
from services.solo_fige import figer_pronos_weekend  # noqa: E402


def ouvrir_football() -> sqlite3.Connection:
    if not FICHIER_FOOTBALL.is_file():
        raise FileNotFoundError(f"Base introuvable : {FICHIER_FOOTBALL}")
    connexion = sqlite3.connect(str(FICHIER_FOOTBALL))
    connexion.row_factory = sqlite3.Row
    return connexion


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(
        description="Fige les pronos Solo du weekend dans analyses.db",
    )
    parseur.add_argument(
        "--weekend",
        dest="weekend",
        default=None,
        help="Vendredi du weekend (YYYY-MM-DD). Défaut : weekend actif/prochain.",
    )
    parseur.add_argument(
        "--forcer",
        action="store_true",
        help="Remplace les marchés déjà figés (et efface leurs verdicts).",
    )
    parseur.add_argument(
        "--championnat",
        default=None,
        help="Filtrer une compétition (optionnel).",
    )
    args = parseur.parse_args(argv)

    vider_cache_solo()
    connexion_foot = ouvrir_football()
    try:
        resume = figer_pronos_weekend(
            connexion_foot,
            date_debut=args.weekend,
            championnat=args.championnat,
            forcer=args.forcer,
            chemin_analyses=FICHIER_ANALYSES,
        )
    finally:
        connexion_foot.close()

    print(
        f"Weekend {resume['weekend_debut']} — "
        f"{resume['nb_marches_figes']} marché(s) figé(s)"
        + (
            f", {resume['nb_marches_ignores']} déjà présent(s)"
            if resume["nb_marches_ignores"]
            else ""
        )
    )
    print(f"Matchs avec prono live : {resume['nb_matchs_avec_prono']}")
    print(f"Figé le : {resume['fige_le']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
