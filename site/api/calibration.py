"""
Metriques de calibration : previsions vs realite (Phase 2).

Fonctions pures, testables sans base de donnees.
"""

from __future__ import annotations

import math
from typing import Any


def _probas_normalisees(p1: float, pn: float, p2: float) -> tuple[float, float, float]:
    """Normalise les probabilites 1X2 (accepte des pourcentages 0-100 ou fractions 0-1)."""
    p1f, pnf, p2f = float(p1), float(pn), float(p2)
    if max(p1f, pnf, p2f) > 1.0:
        p1f, pnf, p2f = p1f / 100.0, pnf / 100.0, p2f / 100.0
    total = p1f + pnf + p2f
    if total <= 0:
        return 0.33, 0.34, 0.33
    return p1f / total, pnf / total, p2f / total


def issue_prevue_1x2(p1: float, pn: float, p2: float) -> str:
    """Issue 1X2 la plus probable selon les probabilites."""
    p1n, pnn, p2n = _probas_normalisees(p1, pn, p2)
    probs = {"1": p1n, "N": pnn, "2": p2n}
    return max(probs, key=probs.get)


def brier_score_1x2(p1: float, pn: float, p2: float, issue_reelle: str) -> float:
    """Score de Brier multiclasse pour 1X2 (issue_reelle : '1', 'N' ou '2')."""
    p1n, pnn, p2n = _probas_normalisees(p1, pn, p2)
    outcomes = {"1": (1.0, 0.0, 0.0), "N": (0.0, 1.0, 0.0), "2": (0.0, 0.0, 1.0)}
    o1, on, o2 = outcomes.get(issue_reelle, (0.0, 0.0, 0.0))
    return (p1n - o1) ** 2 + (pnn - on) ** 2 + (p2n - o2) ** 2


def log_loss_1x2(p1: float, pn: float, p2: float, issue_reelle: str) -> float:
    """Log-loss pour l'issue 1X2 reelle."""
    p1n, pnn, p2n = _probas_normalisees(p1, pn, p2)
    eps = 1e-15
    if issue_reelle == "1":
        p_reel = max(p1n, eps)
    elif issue_reelle == "N":
        p_reel = max(pnn, eps)
    else:
        p_reel = max(p2n, eps)
    return -math.log(p_reel)


def score_exact_ok(
    score_prevu: str | None,
    buts_dom: int,
    buts_ext: int,
) -> bool:
    """Le score modal prevu correspond au score reel."""
    if not score_prevu:
        return False
    attendu = f"{int(buts_dom)}-{int(buts_ext)}"
    return str(score_prevu).strip() == attendu


def mae_xg(
    xg_prevu_dom: float | None,
    xg_prevu_ext: float | None,
    xg_reel_dom: float | None,
    xg_reel_ext: float | None,
) -> float | None:
    """Erreur absolue moyenne sur les xG domicile / exterieur."""
    if xg_prevu_dom is None or xg_prevu_ext is None:
        return None
    if xg_reel_dom is None or xg_reel_ext is None:
        return None
    return (
        abs(float(xg_prevu_dom) - float(xg_reel_dom))
        + abs(float(xg_prevu_ext) - float(xg_reel_ext))
    ) / 2.0


def _btts_ok(p_les_deux: float | None, buts_dom: int, buts_ext: int) -> bool | None:
    if p_les_deux is None:
        return None
    prevu = float(p_les_deux) >= 50.0 if float(p_les_deux) > 1.0 else float(p_les_deux) >= 0.5
    reel = int(buts_dom) > 0 and int(buts_ext) > 0
    return prevu == reel


def _o25_ok(p_plus_2: float | None, buts_dom: int, buts_ext: int) -> bool | None:
    if p_plus_2 is None:
        return None
    prevu = float(p_plus_2) >= 50.0 if float(p_plus_2) > 1.0 else float(p_plus_2) >= 0.5
    reel = int(buts_dom) + int(buts_ext) >= 3
    return prevu == reel


def calculer_metriques_match(prevision: dict, match_joue: dict) -> dict[str, Any]:
    """
    Calcule les metriques de calibration pour un match joue.
    prevision : champs de previsions_match ou dict prediction figee.
    match_joue : buts, xG reels, etc.
    """
    buts_d = int(match_joue["buts_domicile"])
    buts_e = int(match_joue["buts_exterieur"])
    issue_reelle = match_joue.get("issue_reelle")
    if not issue_reelle:
        if buts_d > buts_e:
            issue_reelle = "1"
        elif buts_d < buts_e:
            issue_reelle = "2"
        else:
            issue_reelle = "N"

    p1 = prevision.get("p_victoire_domicile")
    pn = prevision.get("p_nul")
    p2 = prevision.get("p_victoire_exterieur")

    metriques: dict[str, Any] = {
        "issue_reelle": issue_reelle,
        "issue_prevue": issue_prevue_1x2(p1 or 0, pn or 0, p2 or 0) if p1 is not None else None,
        "score_exact_ok": score_exact_ok(
            prevision.get("score_plus_probable"), buts_d, buts_e
        ),
        "issue_1x2_ok": None,
        "brier_score": None,
        "log_loss": None,
        "mae_xg": mae_xg(
            prevision.get("xg_prevu_domicile"),
            prevision.get("xg_prevu_exterieur"),
            match_joue.get("xg_reel_domicile") or match_joue.get("xg_domicile"),
            match_joue.get("xg_reel_exterieur") or match_joue.get("xg_exterieur"),
        ),
        "btts_ok": _btts_ok(prevision.get("p_les_deux_marquent"), buts_d, buts_e),
        "o25_ok": _o25_ok(prevision.get("p_plus_de_2_buts"), buts_d, buts_e),
    }

    if p1 is not None and pn is not None and p2 is not None:
        metriques["brier_score"] = brier_score_1x2(p1, pn, p2, issue_reelle)
        metriques["log_loss"] = log_loss_1x2(p1, pn, p2, issue_reelle)
        metriques["issue_1x2_ok"] = metriques["issue_prevue"] == issue_reelle

    return metriques


def agreger_metriques_saison(resultats: list[dict]) -> dict[str, Any]:
    """
    Agrege une liste de resultats (avec metriques calculees).
    Chaque element doit contenir au moins les champs de metriques.
    """
    if not resultats:
        return {
            "nb_matchs": 0,
            "pct_score_exact": None,
            "pct_issue_1x2": None,
            "brier_moyen": None,
            "log_loss_moyen": None,
            "mae_xg_moyen": None,
            "pct_btts": None,
            "pct_o25": None,
        }

    nb = len(resultats)
    nb_score = sum(1 for r in resultats if r.get("score_exact_ok"))
    nb_1x2 = [r for r in resultats if r.get("issue_1x2_ok") is not None]
    briers = [r["brier_score"] for r in resultats if r.get("brier_score") is not None]
    log_losses = [r["log_loss"] for r in resultats if r.get("log_loss") is not None]
    maes = [r["mae_xg"] for r in resultats if r.get("mae_xg") is not None]
    btts = [r for r in resultats if r.get("btts_ok") is not None]
    o25s = [r for r in resultats if r.get("o25_ok") is not None]

    def pct_ok(items: list, cle: str) -> float | None:
        if not items:
            return None
        return round(100.0 * sum(1 for r in items if r.get(cle)) / len(items), 1)

    return {
        "nb_matchs": nb,
        "pct_score_exact": round(100.0 * nb_score / nb, 1),
        "pct_issue_1x2": pct_ok(nb_1x2, "issue_1x2_ok"),
        "brier_moyen": round(sum(briers) / len(briers), 4) if briers else None,
        "log_loss_moyen": round(sum(log_losses) / len(log_losses), 4) if log_losses else None,
        "mae_xg_moyen": round(sum(maes) / len(maes), 3) if maes else None,
        "pct_btts": pct_ok(btts, "btts_ok"),
        "pct_o25": pct_ok(o25s, "o25_ok"),
    }
