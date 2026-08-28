"""Tests unitaires de la couche IA (fallback template sans clé API)."""

from __future__ import annotations

from pathlib import Path

from ia_analyse import (
    enregistrer_analyse_ia_cachee,
    generer_analyse_ia,
    generer_faits_pour_ia,
    lire_analyse_ia_cachee,
)
from historique_analyses import assurer_schema, ouvrir_base


def test_generer_faits_contient_probas_et_xg():
    prediction = {
        "p_victoire_domicile": 45.0,
        "p_nul": 28.0,
        "p_victoire_exterieur": 27.0,
        "score_plus_probable": "2-1",
        "xg_prevu_domicile": 1.6,
        "xg_prevu_exterieur": 1.1,
        "xg_total": 2.7,
        "p_les_deux_marquent": 55.0,
        "p_plus_de_2_buts": 52.0,
        "cartons": {"jaunes_domicile": 1.5, "jaunes_exterieur": 2.0, "jaunes_match": 3.5},
    }
    faits = generer_faits_pour_ia(
        prediction,
        None,
        championnat="La Liga",
        saison="2026-2027",
        domicile="Barcelona",
        exterieur="Real Madrid",
    )
    assert faits["domicile"] == "Barcelona"
    assert faits["probas_1x2"]["victoire_domicile_pct"] == 45.0
    assert faits["xg_prevu"]["domicile"] == 1.6
    assert faits["score_plus_probable"] == "2-1"


def test_generer_faits_contient_h2h_si_confrontations():
    prediction = {"p_victoire_domicile": 40.0, "p_nul": 30.0, "p_victoire_exterieur": 30.0}
    confrontations = {
        "nb": 5,
        "victoires_domicile": 2,
        "nuls": 1,
        "victoires_exterieur": 2,
        "matchs": [
            {
                "date": "2025-10-01",
                "score": "2-1",
                "domicile": "Barcelona",
                "exterieur": "Real Madrid",
            }
        ],
    }
    faits = generer_faits_pour_ia(
        prediction,
        None,
        championnat="La Liga",
        saison="2026-2027",
        domicile="Barcelona",
        exterieur="Real Madrid",
        confrontations=confrontations,
    )
    assert faits["confrontations"]["nb"] == 5
    assert faits["confrontations"]["victoires_domicile"] == 2
    assert len(faits["confrontations"]["derniers_matchs"]) == 1


def test_analyse_template_mentionne_confrontations():
    faits = {
        "championnat": "La Liga",
        "saison": "2026-2027",
        "domicile": "Barcelona",
        "exterieur": "Real Madrid",
        "probas_1x2": {"victoire_domicile_pct": 40, "nul_pct": 30, "victoire_exterieur_pct": 30},
        "score_plus_probable": "2-1",
        "xg_prevu": {"domicile": 1.5, "exterieur": 1.2, "total": 2.7},
        "confrontations": {
            "nb": 3,
            "victoires_domicile": 1,
            "nuls": 1,
            "victoires_exterieur": 1,
            "derniers_matchs": [],
        },
        "scenarios": [],
    }
    from ia_analyse import _analyse_template

    texte = _analyse_template(faits)
    assert "Confrontations directes" in texte
    assert "La Liga" in texte


def test_desactiver_llm_force_template(monkeypatch):
    monkeypatch.setenv("CLE_LLM", "cle-test")
    monkeypatch.setenv("DESACTIVER_LLM", "1")
    faits = {
        "domicile": "Lyon",
        "exterieur": "Marseille",
        "probas_1x2": {"victoire_domicile_pct": 40, "nul_pct": 30, "victoire_exterieur_pct": 30},
        "score_plus_probable": "1-1",
        "scenarios": [],
    }
    resultat = generer_analyse_ia(faits, forcer_template=False)
    assert resultat["source"] == "template"


def test_generer_analyse_ia_fallback_template(monkeypatch):
    monkeypatch.delenv("CLE_LLM", raising=False)
    faits = {
        "championnat": "Ligue 1",
        "saison": "2026-2027",
        "domicile": "Lyon",
        "exterieur": "Marseille",
        "probas_1x2": {"victoire_domicile_pct": 40, "nul_pct": 30, "victoire_exterieur_pct": 30},
        "score_plus_probable": "1-1",
        "xg_prevu": {"domicile": 1.4, "exterieur": 1.2, "total": 2.6},
        "marche_buts": {"les_deux_marquent_pct": 50, "plus_de_2_buts_pct": 48},
        "scenarios": [],
    }
    resultat = generer_analyse_ia(faits, forcer_template=True)
    assert resultat["source"] == "template"
    assert "Lyon" in resultat["texte"]
    assert "1-1" in resultat["texte"]
    assert "40" in resultat["texte"]


def test_cache_analyse_ia(tmp_path: Path):
    chemin = tmp_path / "analyses_ia.db"
    connexion = ouvrir_base(chemin)
    try:
        assurer_schema(connexion)
        faits = {"domicile": "A", "exterieur": "B"}
        enregistrer_analyse_ia_cachee(
            connexion, "ligue 1|2026-2027|2026-08-01|a|b", "Texte test", "template", faits
        )
        lu = lire_analyse_ia_cachee(connexion, "ligue 1|2026-2027|2026-08-01|a|b")
        assert lu is not None
        assert lu["texte"] == "Texte test"
        assert lu["source"] == "template"
        assert lu["faits"]["domicile"] == "A"
    finally:
        connexion.close()
