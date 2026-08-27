"""Tests unitaires des fonctions pures d'analyse_rencontre."""

from analyse_rencontre import (
    _bilan_match,
    _commentaire_score,
    _lambda_cartons_equipe,
    _phrases,
    _poisson,
    _recit_scenario,
    _scenario_cartons,
    _scenario_poisson,
    _scenarios_detailles,
    comparaison_previsions_reel,
    saison_precedente,
    serie_forme_matchs,
)


def test_saison_precedente():
    assert saison_precedente("2026-2027") == "2025-2026"
    assert saison_precedente("2025-2026") == "2024-2025"


def test_poisson_somme_proche_de_un():
    total = sum(_poisson(k, 1.5) for k in range(0, 20))
    assert abs(total - 1.0) < 1e-6


def test_poisson_lambda_nulle():
    assert _poisson(0, 0) == 1.0
    assert _poisson(1, 0) == 0.0


def test_commentaire_score():
    assert _commentaire_score(0, 0) == "match nul et blanc"
    assert _commentaire_score(1, 1) == "match nul 1-1"
    assert "domicile" in _commentaire_score(1, 0)
    assert "extérieur" in _commentaire_score(0, 1)
    assert "large" in _commentaire_score(4, 0)


def test_scenario_poisson_structure_et_probabilites():
    pred = _scenario_poisson(1.6, 1.1)
    assert "-" in pred["score_plus_probable"]
    assert len(pred["scores_frequents"]) == 6
    total_1n2 = (
        pred["p_victoire_domicile"]
        + pred["p_nul"]
        + pred["p_victoire_exterieur"]
    )
    assert abs(total_1n2 - 100.0) < 1.5
    assert pred["xg_prevu_domicile"] == 1.6
    assert pred["commentaire_score"]


def test_scenario_poisson_favorise_domicile_fort():
    fort = _scenario_poisson(2.5, 0.6)
    faible = _scenario_poisson(0.6, 2.5)
    assert fort["p_victoire_domicile"] > fort["p_victoire_exterieur"]
    assert faible["p_victoire_exterieur"] > faible["p_victoire_domicile"]


def test_serie_forme_matchs():
    matchs = [
        {
            "date": "2026-01-03",
            "domicile": "A",
            "exterieur": "B",
            "buts_domicile": 2,
            "buts_exterieur": 0,
        },
        {
            "date": "2026-01-02",
            "domicile": "C",
            "exterieur": "A",
            "buts_domicile": 1,
            "buts_exterieur": 1,
        },
        {
            "date": "2026-01-01",
            "domicile": "A",
            "exterieur": "D",
            "buts_domicile": 0,
            "buts_exterieur": 1,
        },
    ]
    assert serie_forme_matchs(matchs, "A") == ["V", "N", "D"]


def test_lambda_cartons_equipe_preferer_forme():
    forme = {
        "nb_avec_cartons": 4,
        "jaunes_par_match": 2.5,
        "rouges_par_match": 0.1,
    }
    j, r, source = _lambda_cartons_equipe(forme, 1.0, 0.0, 2.0, 0.1)
    assert j == 2.5
    assert r == 0.1
    assert source == "5 derniers matchs"


def test_scenario_cartons_et_scenarios_detailles():
    cartons = _scenario_cartons(
        2.0, 2.5, 0.05, 0.05, 4.0, ["saison", "saison"]
    )
    assert cartons["jaunes_match"] == 4.5
    assert cartons["titre"]
    assert "jaunes" in cartons["texte"].lower()

    pred = _scenario_poisson(1.8, 1.2)
    scenarios = _scenarios_detailles(pred, cartons, 2.5)
    cles = [s["cle"] for s in scenarios]
    assert cles == ["rythme", "deux_equipes", "buts", "cartons"]
    assert "occasions attendues" in scenarios[0]["texte"].lower()


def test_bilan_match_score_exact():
    pred = _scenario_poisson(1.5, 1.0)
    pred["score_plus_probable"] = "2-1"
    pred["cartons"] = {"jaunes_match": 4.0}
    bilan = _bilan_match(
        pred,
        {
            "buts_domicile": 2,
            "buts_exterieur": 1,
            "jaunes_domicile": 2,
            "jaunes_exterieur": 2,
            "rouges_domicile": 0,
            "rouges_exterieur": 0,
        },
    )
    assert bilan["points"]
    assert any("exactement" in p for p in bilan["points"])


def test_comparaison_previsions_reel_lignes_chiffrees():
    pred = _scenario_poisson(1.5, 1.0)
    pred["score_plus_probable"] = "2-1"
    pred["cartons"] = _scenario_cartons(
        2.0, 1.8, 0.05, 0.02, 3.8, ["saison", "saison"]
    )
    comparaison = comparaison_previsions_reel(
        pred,
        {
            "buts_domicile": 2,
            "buts_exterieur": 1,
            "xg_domicile": 1.6,
            "xg_exterieur": 0.9,
            "jaunes_domicile": 3,
            "jaunes_exterieur": 2,
            "rouges_domicile": 0,
            "rouges_exterieur": 1,
        },
    )
    libelles = [ligne["statistique"] for ligne in comparaison["lignes"]]
    assert libelles == [
        "Buts",
        "Occasions (xG)",
        "Cartons jaunes",
        "Cartons rouges",
    ]
    buts = comparaison["lignes"][0]
    assert buts["prevu_domicile"] == 2
    assert buts["reel_exterieur"] == 1


def test_comparaison_previsions_reel_sans_xg_reel():
    pred = _scenario_poisson(1.2, 1.0)
    pred["cartons"] = {"jaunes_domicile": 2.0, "jaunes_exterieur": 1.5}
    comparaison = comparaison_previsions_reel(
        pred,
        {
            "buts_domicile": 1,
            "buts_exterieur": 0,
            "xg_domicile": None,
            "xg_exterieur": None,
            "jaunes_domicile": 2,
            "jaunes_exterieur": 1,
        },
    )
    libelles = [ligne["statistique"] for ligne in comparaison["lignes"]]
    assert "Occasions (xG)" not in libelles
    assert "Buts" in libelles
    assert "Cartons jaunes" in libelles


def test_phrases_simples_expliquent_xg():
    moyennes = {
        "xg_domicile": 1.4,
        "xg_encaisses_domicile": 1.1,
        "tirs_cadres_domicile": 4.5,
        "jaunes_domicile": 2.0,
        "rouges_domicile": 0.1,
    }
    profil = {
        "xg_marques": 2.0,
        "xg_encaisses": 0.8,
        "tirs_cadres": 6.0,
        "jaunes": 1.2,
        "rouges": 0.05,
    }
    phrases = _phrases(profil, moyennes, True, False)
    texte = " ".join(phrases["forces"]).lower()
    assert "occasions attendues" in texte
    assert "attaque" in texte or "défense" in texte or "tirs cadrés" in texte


def test_recit_scenario_style_film():
    pred = _scenario_poisson(2.0, 1.0)
    cartons = _scenario_cartons(1.5, 1.8, 0.05, 0.05, 3.5, ["saison", "saison"])
    pred["scenarios"] = _scenarios_detailles(pred, cartons, 2.5)
    domicile = {
        "forces": [
            "Bonne attaque à domicile : environ 2.00 occasions attendues (xG) "
            "par match, au-dessus de la moyenne (1.40)."
        ],
        "faiblesses": [
            "Pas de faiblesse marquée à domicile face à la moyenne du championnat."
        ],
        "donnees_limitees": False,
    }
    exterieur = {
        "forces": [
            "Profil à l'extérieur proche de la moyenne du championnat : "
            "ni très fort, ni très faible en attaque et en défense."
        ],
        "faiblesses": [
            "Défense à l'extérieur fragile : elle concède beaucoup d'occasions "
            "(1.80 xG encaissés, moyenne 1.20)."
        ],
        "donnees_limitees": False,
    }
    recit = _recit_scenario("Paris", "Lyon", domicile, exterieur, pred, cartons)
    assert 3 <= len(recit) <= 6
    texte = " ".join(recit).lower()
    assert "affiche" in texte
    assert "dénouement" in texte
    assert "paris" in texte and "lyon" in texte
    # Pas une liste sèche de stats collées
    assert "xG marqués par match" not in texte
