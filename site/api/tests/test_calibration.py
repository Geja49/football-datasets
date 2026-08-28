"""Tests unitaires des metriques de calibration (fonctions pures)."""

import math

from calibration import (
    agreger_metriques_saison,
    brier_score_1x2,
    calculer_metriques_match,
    issue_prevue_1x2,
    log_loss_1x2,
    mae_xg,
    score_exact_ok,
)


def test_brier_score_parfait_et_mauvais():
    # Victoire domicile reelle, prediction 100 % domicile.
    assert brier_score_1x2(100, 0, 0, "1") == 0.0
    # Prediction inverse.
    brier = brier_score_1x2(10, 20, 70, "1")
    assert brier > 0.5


def test_log_loss_1x2():
    loss = log_loss_1x2(80, 15, 5, "1")
    assert loss > 0
    assert loss < 1.0
    # Issue improbable => log-loss eleve.
    loss_mauvais = log_loss_1x2(5, 10, 85, "1")
    assert loss_mauvais > loss


def test_score_exact_ok():
    assert score_exact_ok("2-1", 2, 1) is True
    assert score_exact_ok("1-1", 2, 1) is False
    assert score_exact_ok(None, 0, 0) is False


def test_mae_xg():
    assert mae_xg(1.5, 1.0, 1.2, 0.8) == 0.25
    assert mae_xg(1.5, 1.0, None, 0.8) is None


def test_issue_prevue_1x2():
    assert issue_prevue_1x2(60, 25, 15) == "1"
    assert issue_prevue_1x2(20, 50, 30) == "N"
    assert issue_prevue_1x2(10, 20, 70) == "2"


def test_calculer_metriques_match():
    prevision = {
        "p_victoire_domicile": 55.0,
        "p_nul": 25.0,
        "p_victoire_exterieur": 20.0,
        "score_plus_probable": "2-1",
        "xg_prevu_domicile": 1.8,
        "xg_prevu_exterieur": 1.0,
        "p_les_deux_marquent": 60.0,
        "p_plus_de_2_buts": 55.0,
    }
    match = {
        "buts_domicile": 2,
        "buts_exterieur": 1,
        "xg_domicile": 1.6,
        "xg_exterieur": 0.9,
    }
    metriques = calculer_metriques_match(prevision, match)
    assert metriques["issue_reelle"] == "1"
    assert metriques["issue_1x2_ok"] is True
    assert metriques["score_exact_ok"] is True
    assert metriques["btts_ok"] is True
    assert metriques["o25_ok"] is True
    assert metriques["brier_score"] is not None
    assert abs(metriques["mae_xg"] - 0.15) < 0.001


def test_agreger_metriques_saison():
    resultats = [
        {
            "score_exact_ok": True,
            "issue_1x2_ok": True,
            "brier_score": 0.2,
            "log_loss": 0.5,
            "mae_xg": 0.3,
            "btts_ok": True,
            "o25_ok": False,
        },
        {
            "score_exact_ok": False,
            "issue_1x2_ok": False,
            "brier_score": 0.4,
            "log_loss": 0.8,
            "mae_xg": 0.5,
            "btts_ok": False,
            "o25_ok": True,
        },
    ]
    agg = agreger_metriques_saison(resultats)
    assert agg["nb_matchs"] == 2
    assert agg["pct_score_exact"] == 50.0
    assert agg["pct_issue_1x2"] == 50.0
    assert agg["brier_moyen"] == 0.3
    assert agg["mae_xg_moyen"] == 0.4
    assert agg["pct_btts"] == 50.0
    assert agg["pct_o25"] == 50.0


def test_agreger_metriques_vide():
    agg = agreger_metriques_saison([])
    assert agg["nb_matchs"] == 0
    assert agg["pct_score_exact"] is None
