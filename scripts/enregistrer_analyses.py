"""
Enregistre automatiquement les previsions (avant match) et resultats (apres).

Usage (a la racine du projet) :
    python scripts/enregistrer_analyses.py
    python scripts/enregistrer_analyses.py --saison 2026-2027
    python scripts/enregistrer_analyses.py --limite 20
    python scripts/enregistrer_analyses.py --backfill-joues --saison 2026-2027

Base : donnees/analyses.db (separee de football.db).

Note backfill : sans date_limite parfaite sur toutes les agregats saison,
les previsions retroactives restent approximatives pour la calibration historique.
Le flag retroactif=1 les identifie en base.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
DOSSIER_API = RACINE / "site" / "api"
FICHIER_FOOTBALL = RACINE / "donnees" / "football.db"
SAISON_DEFAUT = "2026-2027"

if str(DOSSIER_API) not in sys.path:
    sys.path.insert(0, str(DOSSIER_API))

from alias_equipes import normaliser_nom_calendrier  # noqa: E402
from analyse_rencontre import (  # noqa: E402
    analyser_rencontre,
    comparaison_previsions_reel,
    lire_match_joue,
    _bilan_match,
)
from historique_analyses import (  # noqa: E402
    cle_match,
    enregistrer_prevision,
    enregistrer_resultat,
    obtenir_ou_creer_version_modele,
    ouvrir_base as ouvrir_analyses,
    pred_depuis_prevision_figee,
    prevision_existe,
    resultat_existe_pour_prevision,
)


def ouvrir_football() -> sqlite3.Connection:
    if not FICHIER_FOOTBALL.is_file():
        raise FileNotFoundError(f"Base introuvable : {FICHIER_FOOTBALL}")
    connexion = sqlite3.connect(str(FICHIER_FOOTBALL))
    connexion.row_factory = sqlite3.Row
    return connexion


def lister_matchs_a_venir(connexion_foot: sqlite3.Connection, saison: str, aujourdhui: str):
    """Matchs du calendrier a venir (date >= aujourd'hui) pour la saison."""
    return connexion_foot.execute(
        """
        SELECT date, championnat, saison, domicile, exterieur
        FROM calendrier
        WHERE saison = ?
          AND date IS NOT NULL
          AND date >= ?
          AND domicile IS NOT NULL
          AND exterieur IS NOT NULL
          AND domicile != exterieur
        ORDER BY date, championnat, domicile
        """,
        (saison, aujourdhui),
    ).fetchall()


def lister_previsions_sans_resultat(connexion_analyses: sqlite3.Connection, saison: str):
    return connexion_analyses.execute(
        """
        SELECT p.id, p.cle_match, p.championnat, p.saison, p.date_match,
               p.domicile, p.exterieur, p.payload_json,
               p.xg_prevu_domicile, p.xg_prevu_exterieur,
               p.p_victoire_domicile, p.p_nul, p.p_victoire_exterieur,
               p.score_plus_probable, p.p_les_deux_marquent, p.p_plus_de_2_buts,
               p.jaunes_domicile, p.jaunes_exterieur
        FROM previsions_match p
        LEFT JOIN resultats_analyse r ON r.prevision_id = p.id
        WHERE p.saison = ?
          AND r.id IS NULL
        ORDER BY p.date_match, p.id
        """,
        (saison,),
    ).fetchall()


def creer_previsions(
    connexion_foot: sqlite3.Connection,
    connexion_analyses: sqlite3.Connection,
    saison: str,
    limite: int | None = None,
) -> tuple[int, int]:
    """
    PRE-MATCH : analyser et figer les matchs a venir sans prevision.
    Retourne (crees, ignores_erreur).
    """
    aujourdhui = date.today().isoformat()
    matchs = lister_matchs_a_venir(connexion_foot, saison, aujourdhui)
    version_id = obtenir_ou_creer_version_modele(connexion_analyses)
    crees = 0
    erreurs = 0

    for ligne in matchs:
        if limite is not None and crees >= limite:
            break
        date_m = (ligne["date"] or "")[:10]
        champ = ligne["championnat"]
        dom = normaliser_nom_calendrier(ligne["domicile"])
        ext = normaliser_nom_calendrier(ligne["exterieur"])
        cle = cle_match(champ, saison, date_m, dom, ext)
        if prevision_existe(connexion_analyses, cle):
            continue
        # Ne pas figer si le match est deja joue (score en base).
        deja = lire_match_joue(connexion_foot, champ, saison, dom, ext)
        if deja.get("joue"):
            continue
        try:
            analyse = analyser_rencontre(connexion_foot, champ, saison, dom, ext)
        except ValueError as erreur:
            print(f"  ignore {champ} {dom}-{ext} ({date_m}) : {erreur}")
            erreurs += 1
            continue
        except Exception as erreur:  # noqa: BLE001 — batch robuste
            print(f"  erreur {champ} {dom}-{ext} ({date_m}) : {erreur}")
            erreurs += 1
            continue

        prediction = analyse.get("prediction") or {}
        # Stocker la prediction seule (pas domicile/exterieur profils) pour rester leger.
        nouvel_id = enregistrer_prevision(
            connexion_analyses,
            champ,
            saison,
            date_m,
            dom,
            ext,
            prediction,
            version_modele_id=version_id,
            payload_complet=prediction,
        )
        if nouvel_id:
            crees += 1
            print(f"  prevision : {champ} {dom} - {ext} ({date_m})")

    return crees, erreurs


def pred_figee_depuis_ligne(ligne: sqlite3.Row) -> dict:
    """Reconstruit la prediction figee depuis une ligne previsions_match."""
    try:
        payload = json.loads(ligne["payload_json"] or "{}")
    except json.JSONDecodeError:
        payload = {}
    return pred_depuis_prevision_figee(
        {
            "prediction": payload,
            "xg_prevu_domicile": ligne["xg_prevu_domicile"],
            "xg_prevu_exterieur": ligne["xg_prevu_exterieur"],
            "p_victoire_domicile": ligne["p_victoire_domicile"],
            "p_nul": ligne["p_nul"],
            "p_victoire_exterieur": ligne["p_victoire_exterieur"],
            "score_plus_probable": ligne["score_plus_probable"],
            "p_les_deux_marquent": ligne["p_les_deux_marquent"],
            "p_plus_de_2_buts": ligne["p_plus_de_2_buts"],
            "jaunes_domicile": ligne["jaunes_domicile"],
            "jaunes_exterieur": ligne["jaunes_exterieur"],
        }
    )


def completer_resultats(
    connexion_foot: sqlite3.Connection,
    connexion_analyses: sqlite3.Connection,
    saison: str,
) -> tuple[int, int]:
    """
    POST-MATCH : pour chaque prevision sans resultat, si score en base,
    comparer avec la prevision FIGEE (pas de recalcul live).
    """
    lignes = lister_previsions_sans_resultat(connexion_analyses, saison)
    completes = 0
    ignores = 0

    for ligne in lignes:
        prevision_id = int(ligne["id"])
        if resultat_existe_pour_prevision(connexion_analyses, prevision_id):
            continue
        champ = ligne["championnat"]
        dom = ligne["domicile"]
        ext = ligne["exterieur"]
        match_joue = lire_match_joue(connexion_foot, champ, saison, dom, ext)
        if not match_joue.get("joue"):
            ignores += 1
            continue

        pred_figee = pred_figee_depuis_ligne(ligne)
        bilan = _bilan_match(pred_figee, match_joue)
        comparaison = comparaison_previsions_reel(pred_figee, match_joue)
        bilan_complet = {
            "points": bilan.get("points") or [],
            "comparaison": comparaison,
            "score_exact_ok": (
                str(pred_figee.get("score_plus_probable") or "").strip()
                == f"{match_joue['buts_domicile']}-{match_joue['buts_exterieur']}"
            ),
        }
        enregistrer_resultat(connexion_analyses, prevision_id, match_joue, bilan_complet)
        completes += 1
        print(
            f"  resultat : {champ} {dom} - {ext} "
            f"({match_joue.get('date')}) "
            f"{match_joue['buts_domicile']}-{match_joue['buts_exterieur']}"
        )

    return completes, ignores


def lister_matchs_joues_sans_prevision(
    connexion_foot: sqlite3.Connection,
    connexion_analyses: sqlite3.Connection,
    saison: str,
):
    """Matchs deja joues (score en base) sans prevision enregistree."""
    lignes = connexion_foot.execute(
        """
        SELECT championnat, date, domicile, exterieur
        FROM matchs
        WHERE saison = ?
          AND buts_domicile IS NOT NULL
          AND buts_exterieur IS NOT NULL
          AND domicile IS NOT NULL
          AND exterieur IS NOT NULL
          AND domicile != exterieur
        ORDER BY date, championnat, domicile
        """,
        (saison,),
    ).fetchall()
    resultat = []
    for ligne in lignes:
        date_m = (ligne["date"] or "")[:10]
        cle = cle_match(
            ligne["championnat"], saison, date_m, ligne["domicile"], ligne["exterieur"]
        )
        if not prevision_existe(connexion_analyses, cle):
            resultat.append(ligne)
    return resultat


def backfill_matchs_joues(
    connexion_foot: sqlite3.Connection,
    connexion_analyses: sqlite3.Connection,
    saison: str,
    limite: int | None = None,
) -> tuple[int, int]:
    """
    Genere des previsions retroactives pour matchs joues sans prevision,
    puis complete les resultats_analyse.
    """
    matchs = lister_matchs_joues_sans_prevision(
        connexion_foot, connexion_analyses, saison
    )
    version_id = obtenir_ou_creer_version_modele(connexion_analyses)
    crees = 0
    erreurs = 0

    for ligne in matchs:
        if limite is not None and crees >= limite:
            break
        date_m = (ligne["date"] or "")[:10]
        champ = ligne["championnat"]
        dom = ligne["domicile"]
        ext = ligne["exterieur"]
        try:
            analyse = analyser_rencontre(
                connexion_foot, champ, saison, dom, ext, date_limite=date_m
            )
        except ValueError as erreur:
            print(f"  ignore backfill {champ} {dom}-{ext} ({date_m}) : {erreur}")
            erreurs += 1
            continue
        except Exception as erreur:  # noqa: BLE001
            print(f"  erreur backfill {champ} {dom}-{ext} ({date_m}) : {erreur}")
            erreurs += 1
            continue

        prediction = dict(analyse.get("prediction") or {})
        prediction.pop("bilan", None)
        prediction.pop("comparaison", None)
        nouvel_id = enregistrer_prevision(
            connexion_analyses,
            champ,
            saison,
            date_m,
            dom,
            ext,
            prediction,
            version_modele_id=version_id,
            payload_complet=prediction,
            retroactif=True,
        )
        if nouvel_id:
            crees += 1
            print(f"  backfill prevision : {champ} {dom} - {ext} ({date_m})")

    completes, _ = completer_resultats(connexion_foot, connexion_analyses, saison)
    return crees, completes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enregistre previsions et resultats d'analyses de match."
    )
    parser.add_argument(
        "--saison",
        default=SAISON_DEFAUT,
        help=f"Saison cible (defaut {SAISON_DEFAUT})",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        help="Nombre max de nouvelles previsions (smoke / debug)",
    )
    parser.add_argument(
        "--backfill-joues",
        action="store_true",
        help="Backfill retroactif : previsions + resultats pour matchs deja joues",
    )
    parser.add_argument(
        "--fichier-analyses",
        default=None,
        help="Chemin alternatif pour analyses.db",
    )
    args = parser.parse_args()

    print(f"Historique analyses - saison {args.saison}")
    connexion_foot = ouvrir_football()
    chemin_analyses = Path(args.fichier_analyses) if args.fichier_analyses else None
    connexion_analyses = ouvrir_analyses(chemin_analyses)

    try:
        if args.backfill_joues:
            print("\n=== Backfill matchs joues (retroactif) ===")
            print(
                "Attention : calibration historique approximative "
                "(stats saison partiellement post-match)."
            )
            nb_prev, nb_res = backfill_matchs_joues(
                connexion_foot,
                connexion_analyses,
                args.saison,
                limite=args.limite,
            )
            print(f"{nb_prev} prevision(s) retroactive(s) creee(s)")
            print(f"{nb_res} resultat(s) complete(s)")
        else:
            print("\n=== Previsions (avant match) ===")
            nb_prev, nb_err = creer_previsions(
                connexion_foot, connexion_analyses, args.saison, limite=args.limite
            )
            print(
                f"{nb_prev} prevision(s) creee(s)"
                + (f", {nb_err} ignoree(s)" if nb_err else "")
            )

            print("\n=== Resultats (apres match) ===")
            nb_res, nb_att = completer_resultats(
                connexion_foot, connexion_analyses, args.saison
            )
            print(
                f"{nb_res} resultat(s) complete(s)"
                + (
                    f", {nb_att} prevision(s) encore en attente de score"
                    if nb_att
                    else ""
                )
            )
    finally:
        connexion_foot.close()
        connexion_analyses.close()

    if not args.backfill_joues:
        try:
            from calibrateur import entrainer_calibrateur

            print("\n=== Calibrateur automatique ===")
            connexion_cal = ouvrir_analyses(chemin_analyses)
            try:
                resume_cal = entrainer_calibrateur(connexion_cal, saison=args.saison)
            finally:
                connexion_cal.close()
            print(resume_cal.get("message", ""))
            if resume_cal.get("brier_avant") is not None:
                print(
                    f"Brier : {resume_cal['brier_avant']} -> "
                    f"{resume_cal.get('brier_apres')}"
                )
        except Exception as erreur:  # noqa: BLE001 — non bloquant
            print(f"Calibrateur ignore : {erreur}")

    print("\nTermine.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
