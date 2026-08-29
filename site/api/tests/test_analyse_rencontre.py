"""Tests unitaires des fonctions pures d'analyse_rencontre."""

from analyse_rencontre import (
    _bilan_match,
    _commentaire_score,
    _lambda_cartons_equipe,
    _lambda_corners_equipe,
    _lambda_fautes_equipe,
    _phrases,
    _poisson,
    _recit_scenario,
    _scenario_cartons,
    _scenario_corners,
    _scenario_fautes,
    _scenario_poisson,
    _scenarios_detailles,
    classer_style_de_jeu,
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


def test_lambda_corners_equipe_preferer_forme():
    forme = {
        "nb_avec_corners": 4,
        "corners_par_match": 6.2,
    }
    lam, source = _lambda_corners_equipe(forme, 4.5, 5.0)
    assert lam == 6.2
    assert source == "5 derniers matchs"


def test_scenario_corners_structure():
    corners = _scenario_corners(5.5, 4.8, 9.5, ["saison", "saison"])
    assert corners["corners_match"] == 10.3
    assert corners["p_corners_total_over"] is not None
    assert "corners" in corners["texte"].lower()


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
    pred["fautes"] = _scenario_fautes(11.0, 12.0, 23.0, ["saison", "saison"])
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
            "fautes_domicile": 10,
            "fautes_exterieur": 14,
        },
    )
    libelles = [ligne["statistique"] for ligne in comparaison["lignes"]]
    assert libelles == [
        "Buts",
        "Occasions (xG)",
        "Cartons jaunes",
        "Cartons rouges",
        "Fautes",
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
        "fautes_domicile": 11.0,
    }
    profil = {
        "xg_marques": 2.0,
        "xg_encaisses": 0.8,
        "tirs_cadres": 6.0,
        "jaunes": 1.2,
        "rouges": 0.05,
        "fautes": 14.0,
    }
    phrases = _phrases(profil, moyennes, True, False)
    texte = " ".join(phrases["forces"] + phrases["faiblesses"]).lower()
    assert "occasions attendues" in texte
    assert "attaque" in texte or "défense" in texte or "tirs cadrés" in texte
    assert "fautes" in texte


def test_recit_scenario_style_film():
    pred = _scenario_poisson(2.0, 1.0)
    cartons = _scenario_cartons(1.5, 1.8, 0.05, 0.05, 3.5, ["saison", "saison"])
    fautes = _scenario_fautes(10.0, 11.0, 23.0, ["saison", "saison"])
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
        "style_de_jeu": {
            "code": "offensif",
            "libelle": "Offensif",
            "explication": "Beaucoup d'occasions.",
            "proxy_possession": False,
        },
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
        "style_de_jeu": {
            "code": "defensif",
            "libelle": "Défensif",
            "explication": "Peu d'occasions concédées.",
            "proxy_possession": False,
        },
    }
    recit = _recit_scenario(
        "Paris", "Lyon", domicile, exterieur, pred, cartons, fautes
    )
    assert 3 <= len(recit) <= 6
    texte = " ".join(recit).lower()
    assert "affiche" in texte
    assert "dénouement" in texte
    assert "paris" in texte and "lyon" in texte
    assert "offensif" in texte or "défensif" in texte
    # Pas une liste sèche de stats collées
    assert "xG marqués par match" not in texte


def test_lambda_et_scenario_fautes():
    forme = {"nb_avec_fautes": 4, "fautes_par_match": 13.5}
    lam, source = _lambda_fautes_equipe(forme, 11.0, 12.0)
    assert lam == 13.5
    assert source == "5 derniers matchs"
    scenario = _scenario_fautes(13.0, 14.0, 23.0, ["saison", "saison"])
    assert scenario["fautes_match"] == 27.0
    assert scenario["rythme"] == "physique"
    assert "fautes" in scenario["texte"].lower()
    assert "football-data" in scenario["texte"].lower()


def test_classer_style_de_jeu_offensif_et_defensif():
    moyennes = {
        "xg_domicile": 1.4,
        "xg_encaisses_domicile": 1.2,
        "tirs_domicile": 12.0,
        "corners_domicile": 5.0,
    }
    offensif = classer_style_de_jeu(2.0, 1.1, 16.0, 5.0, moyennes, True)
    assert offensif["code"] == "offensif"
    defensif = classer_style_de_jeu(1.3, 0.8, 11.0, 5.0, moyennes, True)
    assert defensif["code"] == "defensif"


def test_classer_style_de_jeu_direct_possession_proxy():
    moyennes = {
        "xg_domicile": 1.4,
        "xg_encaisses_domicile": 1.2,
        "tirs_domicile": 12.0,
        "corners_domicile": 5.0,
    }
    direct = classer_style_de_jeu(1.4, 1.2, 16.0, 3.5, moyennes, True)
    assert direct["code"] == "direct"
    possession = classer_style_de_jeu(1.5, 1.1, 11.0, 7.0, moyennes, True)
    assert possession["code"] == "possession"
    assert possession["proxy_possession"] is True
    equilibre = classer_style_de_jeu(1.4, 1.2, 12.0, 5.0, moyennes, True)
    assert equilibre["code"] == "equilibre"