"""
Rapport texte ou CSV des metriques de calibration du modele.

Usage (racine du projet) :
    python scripts/rapport_calibration.py
    python scripts/rapport_calibration.py --saison 2026-2027
    python scripts/rapport_calibration.py --saison 2026-2027 --csv rapport.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
DOSSIER_API = RACINE / "site" / "api"
SAISON_DEFAUT = "2026-2027"

if str(DOSSIER_API) not in sys.path:
    sys.path.insert(0, str(DOSSIER_API))

from calibration import agreger_metriques_saison  # noqa: E402
from historique_analyses import (  # noqa: E402
    lister_resultats_avec_previsions,
    ouvrir_base,
)


def _fmt_pct(val: float | None) -> str:
    if val is None:
        return "—"
    return f"{val:.1f} %"


def _fmt_float(val: float | None, decimales: int = 3) -> str:
    if val is None:
        return "—"
    return f"{val:.{decimales}f}"


def afficher_tableau(saison: str, par_championnat: dict[str, dict]) -> None:
    print(f"\nCalibration modele — saison {saison}")
    print("=" * 72)
    if not par_championnat:
        print("Aucun resultat enregistre pour cette saison.")
        return
    entetes = (
        "Championnat",
        "Matchs",
        "1X2",
        "Score exact",
        "Brier",
        "MAE xG",
        "BTTS",
        "O2.5",
    )
    lignes = []
    for champ, metriques in sorted(par_championnat.items()):
        lignes.append(
            [
                champ,
                str(metriques.get("nb_matchs") or 0),
                _fmt_pct(metriques.get("pct_issue_1x2")),
                _fmt_pct(metriques.get("pct_score_exact")),
                _fmt_float(metriques.get("brier_moyen"), 4),
                _fmt_float(metriques.get("mae_xg_moyen"), 2),
                _fmt_pct(metriques.get("pct_btts")),
                _fmt_pct(metriques.get("pct_o25")),
            ]
        )
    # Largeurs colonnes
    largeurs = [max(len(h), max(len(l[i]) for l in lignes)) for i, h in enumerate(entetes)]
    fmt = "  ".join(f"{{:<{w}}}" for w in largeurs)
    print(fmt.format(*entetes))
    print("-" * 72)
    for ligne in lignes:
        print(fmt.format(*ligne))


def exporter_csv(chemin: Path, saison: str, par_championnat: dict[str, dict]) -> None:
    with chemin.open("w", newline="", encoding="utf-8") as fichier:
        writer = csv.writer(fichier, delimiter=";")
        writer.writerow(
            [
                "saison",
                "championnat",
                "nb_matchs",
                "pct_issue_1x2",
                "pct_score_exact",
                "brier_moyen",
                "log_loss_moyen",
                "mae_xg_moyen",
                "pct_btts",
                "pct_o25",
            ]
        )
        for champ, metriques in sorted(par_championnat.items()):
            writer.writerow(
                [
                    saison,
                    champ,
                    metriques.get("nb_matchs"),
                    metriques.get("pct_issue_1x2"),
                    metriques.get("pct_score_exact"),
                    metriques.get("brier_moyen"),
                    metriques.get("log_loss_moyen"),
                    metriques.get("mae_xg_moyen"),
                    metriques.get("pct_btts"),
                    metriques.get("pct_o25"),
                ]
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Rapport calibration du modele.")
    parser.add_argument("--saison", default=SAISON_DEFAUT, help="Saison (ex. 2026-2027)")
    parser.add_argument(
        "--championnat",
        default=None,
        help="Filtrer un championnat (optionnel)",
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="Exporter en CSV (chemin fichier)",
    )
    parser.add_argument(
        "--fichier-analyses",
        default=None,
        help="Chemin alternatif analyses.db",
    )
    parser.add_argument(
        "--inclure-retroactif",
        action="store_true",
        help="Inclure les previsions backfill (retroactif=1)",
    )
    args = parser.parse_args()

    chemin = Path(args.fichier_analyses) if args.fichier_analyses else None
    connexion = ouvrir_base(chemin)
    try:
        resultats = lister_resultats_avec_previsions(
            connexion,
            args.saison,
            args.championnat,
            inclure_retroactif=args.inclure_retroactif,
        )
        groupes: dict[str, list] = {}
        for ligne in resultats:
            groupes.setdefault(ligne["championnat"], []).append(ligne)
        par_championnat = {
            champ: agreger_metriques_saison(lignes)
            for champ, lignes in groupes.items()
        }
        global_stats = agreger_metriques_saison(resultats)
        if args.championnat:
            par_championnat = {args.championnat: global_stats}
    finally:
        connexion.close()

    afficher_tableau(args.saison, par_championnat)
    if global_stats["nb_matchs"]:
        print(
            f"\nTotal : {global_stats['nb_matchs']} match(s) | "
            f"Brier { _fmt_float(global_stats.get('brier_moyen'), 4)} | "
            f"1X2 {_fmt_pct(global_stats.get('pct_issue_1x2'))} | "
            f"Score exact {_fmt_pct(global_stats.get('pct_score_exact'))}"
        )

    if args.csv:
        exporter_csv(Path(args.csv), args.saison, par_championnat)
        print(f"\nExport CSV : {args.csv}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
