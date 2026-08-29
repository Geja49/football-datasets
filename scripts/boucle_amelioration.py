"""
Boucle d'amélioration continue Solo : figer -> juger -> calibrer.

Usage (à la racine du projet) :
    python scripts/boucle_amelioration.py
    python scripts/boucle_amelioration.py --forcer-figer
    python scripts/boucle_amelioration.py --forcer-juger
    python scripts/boucle_amelioration.py --skip-calibrateur

Horloge : heure locale du système (Windows Task Scheduler = heure PC).
- Figer : jeudi >= 18h ou vendredi (si le weekend n'est pas déjà figé)
- Juger : à chaque passage (idempotent - matchs joués sans verdict)
- Calibrer : après juger, si assez de données (seuil calibrateur)

Idempotent : relancer 10×/jour est sans danger.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

RACINE = Path(__file__).resolve().parents[1]
DOSSIER_API = RACINE / "site" / "api"
FICHIER_FOOTBALL = RACINE / "donnees" / "football.db"
FICHIER_ANALYSES = RACINE / "donnees" / "analyses.db"
DOSSIER_MODELES = RACINE / "donnees" / "modeles"
FICHIER_BILAN_SOLO = DOSSIER_MODELES / "bilan_solo.json"

# Jeudi = 3, vendredi = 4 (datetime.weekday)
HEURE_FIGER_JEUDI = 18
SEUIL_VERDICTS_SUIVI = 20
HIT_RATE_FAIBLE = 55.0

if str(DOSSIER_API) not in sys.path:
    sys.path.insert(0, str(DOSSIER_API))


def doit_figer_aujourdhui(
    maintenant: datetime | None = None,
    *,
    forcer: bool = False,
) -> bool:
    """True le vendredi, ou le jeudi à partir de 18h (heure locale)."""
    if forcer:
        return True
    ref = maintenant or datetime.now().astimezone()
    if ref.tzinfo is None:
        ref = ref.astimezone()
    jour = ref.weekday()
    if jour == 4:
        return True
    if jour == 3 and ref.hour >= HEURE_FIGER_JEUDI:
        return True
    return False


def doit_juger_aujourdhui(
    maintenant: datetime | None = None,
    *,
    forcer: bool = False,
) -> bool:
    """
    Toujours True : le jugement est idempotent et utile dès que les scores
    arrivent (souvent lundi-mardi, parfois plus tard).
    """
    _ = maintenant  # réservé doc / tests futurs
    _ = forcer
    return True


def suggestion_seuils(
    hit_rate: float | None,
    nb_verdicts: int,
    *,
    seuil_verdicts: int = SEUIL_VERDICTS_SUIVI,
    hit_rate_faible: float = HIT_RATE_FAIBLE,
) -> str | None:
    """Suggestion textuelle si hit-rate faible - ne modifie aucun seuil."""
    if hit_rate is None or nb_verdicts < seuil_verdicts:
        return None
    if hit_rate >= hit_rate_faible:
        return None
    return (
        f"Hit-rate Solo faible ({hit_rate} % sur {nb_verdicts} verdicts). "
        "Envisager de relever SEUIL_PROBABILITE (85) / SEUIL_CORNERS (75) "
        "après revue - aucun changement automatique."
    )


def _ouvrir_football() -> sqlite3.Connection:
    if not FICHIER_FOOTBALL.is_file():
        raise FileNotFoundError(f"Base introuvable : {FICHIER_FOOTBALL}")
    connexion = sqlite3.connect(str(FICHIER_FOOTBALL))
    connexion.row_factory = sqlite3.Row
    return connexion


def etape_figer(*, forcer: bool = False) -> dict[str, Any]:
    """Fige les marchés Solo du weekend actif si besoin."""
    from services.solo import vendredi_weekend
    from services.solo_fige import figer_pronos_weekend, weekend_est_fige

    weekend = vendredi_weekend().isoformat()
    deja = weekend_est_fige(weekend, chemin_analyses=FICHIER_ANALYSES)
    if deja and not forcer:
        return {
            "action": "figer",
            "statut": "skip",
            "weekend_debut": weekend,
            "nb_figes": 0,
            "message": f"Weekend {weekend} déjà figé - skip",
        }

    connexion = _ouvrir_football()
    try:
        from services.solo import vider_cache_solo

        vider_cache_solo()
        resume = figer_pronos_weekend(
            connexion,
            date_debut=weekend,
            forcer=forcer,
            chemin_analyses=FICHIER_ANALYSES,
        )
    finally:
        connexion.close()

    return {
        "action": "figer",
        "statut": "ok",
        "weekend_debut": resume["weekend_debut"],
        "nb_figes": resume["nb_marches_figes"],
        "nb_ignores": resume.get("nb_marches_ignores", 0),
        "message": (
            f"Weekend {resume['weekend_debut']} - "
            f"{resume['nb_marches_figes']} marché(s) figé(s)"
        ),
    }


def etape_juger() -> dict[str, Any]:
    """Juge les pronos Solo figés dont le score est disponible."""
    from services.solo_fige import juger_pronos_weekend

    connexion = _ouvrir_football()
    try:
        resume = juger_pronos_weekend(
            connexion,
            date_debut=None,
            chemin_analyses=FICHIER_ANALYSES,
        )
    finally:
        connexion.close()

    return {
        "action": "juger",
        "statut": "ok",
        "weekend_debut": resume.get("weekend_debut"),
        "nb_juges": resume["nb_juges"],
        "nb_vrais": resume["nb_vrais"],
        "nb_faux": resume["nb_faux"],
        "nb_attente_score": resume.get("nb_attente_score", 0),
        "hit_rate": resume.get("hit_rate"),
        "message": (
            f"{resume['nb_juges']} marché(s) jugé(s) "
            f"({resume['nb_vrais']} vrais / {resume['nb_faux']} faux)"
        ),
    }


def etape_calibrateur() -> dict[str, Any]:
    """Réentraîne le calibrateur 1X2 si assez de résultats honnêtes."""
    from calibrateur import SEUIL_MIN_MATCHS, entrainer_calibrateur
    from historique_analyses import ouvrir_base

    connexion = ouvrir_base(FICHIER_ANALYSES)
    try:
        resume = entrainer_calibrateur(connexion, saison=None)
    finally:
        connexion.close()

    if resume.get("succes"):
        statut = "ok"
    elif resume.get("nb_matchs", 0) < SEUIL_MIN_MATCHS:
        statut = "skip"
    else:
        statut = "echec"

    return {
        "action": "calibrateur",
        "statut": statut,
        "nb_matchs": resume.get("nb_matchs", 0),
        "seuil_min": resume.get("seuil_min", SEUIL_MIN_MATCHS),
        "message": resume.get("message", ""),
        "brier_avant": resume.get("brier_avant"),
        "brier_apres": resume.get("brier_apres"),
    }


def _stats_verdicts_globaux(chemin_analyses: Path | None = None) -> dict[str, Any]:
    """Agrège les verdicts Solo déjà jugés (tous weekends)."""
    from historique_analyses import ouvrir_base

    chemin = chemin_analyses or FICHIER_ANALYSES
    connexion = ouvrir_base(chemin)
    try:
        try:
            lignes = connexion.execute(
                """
                SELECT p.weekend_debut,
                       COUNT(*) AS nb_juges,
                       SUM(CASE WHEN v.vrai = 1 THEN 1 ELSE 0 END) AS nb_vrais,
                       SUM(CASE WHEN v.vrai = 0 THEN 1 ELSE 0 END) AS nb_faux
                FROM verdicts_solo v
                JOIN pronos_solo p ON p.id = v.prono_solo_id
                GROUP BY p.weekend_debut
                ORDER BY p.weekend_debut
                """
            ).fetchall()
        except sqlite3.OperationalError:
            return {
                "weekends": {},
                "global": {
                    "nb_juges": 0,
                    "nb_vrais": 0,
                    "nb_faux": 0,
                    "hit_rate": None,
                },
            }
    finally:
        connexion.close()

    weekends: dict[str, Any] = {}
    total_j = 0
    total_v = 0
    total_f = 0
    for ligne in lignes:
        nb_j = int(ligne["nb_juges"] or 0)
        nb_v = int(ligne["nb_vrais"] or 0)
        nb_f = int(ligne["nb_faux"] or 0)
        total_j += nb_j
        total_v += nb_v
        total_f += nb_f
        weekends[str(ligne["weekend_debut"])] = {
            "nb_juges": nb_j,
            "nb_vrais": nb_v,
            "nb_faux": nb_f,
            "hit_rate": round(100.0 * nb_v / nb_j, 1) if nb_j else None,
        }

    return {
        "weekends": weekends,
        "global": {
            "nb_juges": total_j,
            "nb_vrais": total_v,
            "nb_faux": total_f,
            "hit_rate": round(100.0 * total_v / total_j, 1) if total_j else None,
        },
    }


def enregistrer_bilan_solo(chemin: Path | None = None) -> dict[str, Any]:
    """Écrit donnees/modeles/bilan_solo.json pour suivi hit-rate."""
    cible = chemin or FICHIER_BILAN_SOLO
    stats = _stats_verdicts_globaux()
    glob = stats["global"]
    suggestion = suggestion_seuils(glob.get("hit_rate"), int(glob.get("nb_juges") or 0))
    bilan = {
        "mis_a_jour_le": datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "weekends": stats["weekends"],
        "global": glob,
        "suggestion": suggestion,
        "garde_fous": {
            "seuil_verdicts": SEUIL_VERDICTS_SUIVI,
            "hit_rate_faible": HIT_RATE_FAIBLE,
            "seuils_auto": False,
        },
    }
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(json.dumps(bilan, ensure_ascii=False, indent=2), encoding="utf-8")
    return bilan


def executer_boucle(
    *,
    forcer_figer: bool = False,
    forcer_juger: bool = False,
    skip_calibrateur: bool = False,
    maintenant: datetime | None = None,
) -> dict[str, Any]:
    """Exécute figer / juger / calibrer selon le jour. Retourne un résumé."""
    ref = maintenant or datetime.now().astimezone()
    resume: dict[str, Any] = {
        "horloge": "locale",
        "maintenant": ref.isoformat(),
        "etapes": [],
    }

    print("=== Boucle amélioration Solo ===")
    print(f"Horloge locale : {ref.strftime('%Y-%m-%d %H:%M (%A)')}")

    # --- Figer ---
    if doit_figer_aujourdhui(ref, forcer=forcer_figer):
        try:
            etape = etape_figer(forcer=forcer_figer)
        except Exception as erreur:  # noqa: BLE001
            etape = {
                "action": "figer",
                "statut": "echec",
                "nb_figes": 0,
                "message": f"Échec figer : {erreur}",
            }
        resume["etapes"].append(etape)
        print(f"[figer] {etape['statut']} - {etape['message']}")
    else:
        etape = {
            "action": "figer",
            "statut": "skip",
            "nb_figes": 0,
            "message": "Hors fenetre figer (jeudi >= 18h / vendredi) - skip",
        }
        resume["etapes"].append(etape)
        print(f"[figer] skip - {etape['message']}")

    # --- Juger ---
    if doit_juger_aujourdhui(ref, forcer=forcer_juger) or forcer_juger:
        try:
            etape = etape_juger()
        except Exception as erreur:  # noqa: BLE001
            etape = {
                "action": "juger",
                "statut": "echec",
                "nb_juges": 0,
                "message": f"Échec juger : {erreur}",
            }
        resume["etapes"].append(etape)
        print(f"[juger] {etape['statut']} - {etape['message']}")
        if etape.get("hit_rate") is not None:
            print(f"         hit-rate passage : {etape['hit_rate']} %")
    else:
        etape = {
            "action": "juger",
            "statut": "skip",
            "nb_juges": 0,
            "message": "Juger non planifié - skip",
        }
        resume["etapes"].append(etape)
        print(f"[juger] skip - {etape['message']}")

    # --- Bilan hit-rate (suivi, sans toucher aux seuils) ---
    try:
        bilan = enregistrer_bilan_solo()
        resume["bilan"] = bilan["global"]
        if bilan.get("suggestion"):
            print(f"[bilan] {bilan['suggestion']}")
        else:
            g = bilan["global"]
            print(
                f"[bilan] global {g.get('hit_rate')} % "
                f"({g.get('nb_vrais')}/{g.get('nb_juges')} verdicts) "
                f"-> {FICHIER_BILAN_SOLO.name}"
            )
    except Exception as erreur:  # noqa: BLE001
        print(f"[bilan] ignore : {erreur}")

    # --- Calibrateur ---
    if skip_calibrateur:
        etape = {
            "action": "calibrateur",
            "statut": "skip",
            "message": "Skip demandé (--skip-calibrateur)",
        }
        resume["etapes"].append(etape)
        print(f"[calibrateur] skip - {etape['message']}")
    else:
        try:
            etape = etape_calibrateur()
        except Exception as erreur:  # noqa: BLE001
            etape = {
                "action": "calibrateur",
                "statut": "echec",
                "message": f"Échec calibrateur : {erreur}",
            }
        resume["etapes"].append(etape)
        libelle = "OK" if etape["statut"] == "ok" else etape["statut"]
        print(f"[calibrateur] {libelle} - {etape['message']}")

    resume["ok"] = all(e.get("statut") != "echec" for e in resume["etapes"])
    print("=== Fin boucle amélioration ===")
    return resume


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(
        description=(
            "Boucle Solo : figer (jeudi soir/vendredi), juger, calibrer. "
            "Horloge locale."
        ),
    )
    parseur.add_argument(
        "--forcer-figer",
        action="store_true",
        help="Figer meme hors jeudi soir / vendredi (remplace si deja fige).",
    )
    parseur.add_argument(
        "--forcer-juger",
        action="store_true",
        help="Forcer le jugement (deja tente a chaque passage).",
    )
    parseur.add_argument(
        "--skip-calibrateur",
        action="store_true",
        help="Ne pas reentrainer le calibrateur.",
    )
    args = parseur.parse_args(argv)

    resume = executer_boucle(
        forcer_figer=args.forcer_figer,
        forcer_juger=args.forcer_juger,
        skip_calibrateur=args.skip_calibrateur,
    )
    return 0 if resume.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
