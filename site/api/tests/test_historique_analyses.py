"""Tests unitaires de l'historique systematique des analyses."""

from pathlib import Path

from historique_analyses import (
    assurer_schema,
    cle_match,
    enregistrer_prevision,
    enregistrer_resultat,
    hash_code_modele,
    issue_depuis_buts,
    lire_prevision_figee,
    lire_resultat,
    lister_resultats_avec_previsions,
    obtenir_ou_creer_version_modele,
    ouvrir_base,
    pred_depuis_prevision_figee,
)
from calibration import score_exact_ok


def test_cle_match_stable_et_normalisee():
    a = cle_match("La Liga", "2026-2027", "2026-08-28", "Barcelona", "Real Madrid")
    b = cle_match("la liga", "2026-2027", "2026-08-28T21:00:00", " barcelona ", "REAL MADRID")
    assert a == b
    assert a.startswith("la liga|2026-2027|2026-08-28|")


def test_issue_et_score_exact():
    assert issue_depuis_buts(2, 1) == "1"
    assert issue_depuis_buts(1, 1) == "N"
    assert issue_depuis_buts(0, 3) == "2"
    assert score_exact_ok("2-1", 2, 1) is True
    assert score_exact_ok("1-1", 2, 1) is False


def test_schema_et_enregistrement_lecture(tmp_path: Path):
    chemin = tmp_path / "analyses_test.db"
    connexion = ouvrir_base(chemin)
    try:
        assurer_schema(connexion)
        version_id = obtenir_ou_creer_version_modele(connexion, hash_code="abc123test")
        assert version_id >= 1
        # Meme hash => meme version.
        assert obtenir_ou_creer_version_modele(connexion, hash_code="abc123test") == version_id

        prediction = {
            "xg_prevu_domicile": 1.8,
            "xg_prevu_exterieur": 1.1,
            "p_victoire_domicile": 55.0,
            "p_nul": 25.0,
            "p_victoire_exterieur": 20.0,
            "score_plus_probable": "2-1",
            "p_les_deux_marquent": 60.0,
            "p_plus_de_2_buts": 58.0,
            "cartons": {"jaunes_domicile": 1.5, "jaunes_exterieur": 2.0},
            "texte": "Scenario de test",
        }
        prevision_id = enregistrer_prevision(
            connexion,
            "La Liga",
            "2026-2027",
            "2026-08-28",
            "Barcelona",
            "Real Madrid",
            prediction,
            version_modele_id=version_id,
        )
        assert prevision_id is not None

        # Idempotent : pas de doublon.
        meme = enregistrer_prevision(
            connexion,
            "La Liga",
            "2026-2027",
            "2026-08-28",
            "Barcelona",
            "Real Madrid",
            prediction,
            version_modele_id=version_id,
        )
        assert meme == prevision_id

        lue = lire_prevision_figee(
            connexion,
            "La Liga",
            "2026-2027",
            "2026-08-28",
            "Barcelona",
            "Real Madrid",
        )
        assert lue is not None
        assert lue["score_plus_probable"] == "2-1"
        assert lue["version_modele"]["hash_code"] == "abc123test"
        assert lue["prediction"]["texte"] == "Scenario de test"

        match_joue = {
            "date": "2026-08-28",
            "buts_domicile": 2,
            "buts_exterieur": 1,
            "xg_domicile": 1.7,
            "xg_exterieur": 0.9,
            "jaunes_domicile": 2,
            "jaunes_exterieur": 3,
        }
        bilan = {"points": ["Score exact."], "comparaison": {"lignes": []}}
        resultat_id = enregistrer_resultat(connexion, prevision_id, match_joue, bilan)
        assert resultat_id is not None
        assert enregistrer_resultat(connexion, prevision_id, match_joue, bilan) == resultat_id

        resultat = lire_resultat(connexion, prevision_id)
        assert resultat is not None
        assert resultat["issue_reelle"] == "1"
        assert resultat["score_exact_ok"] is True
        assert resultat["brier_score"] is not None
        assert resultat["issue_1x2_ok"] is True
        assert resultat["bilan"]["points"] == ["Score exact."]

        pred = pred_depuis_prevision_figee(lue)
        assert pred["score_plus_probable"] == "2-1"
        assert pred["cartons"]["jaunes_domicile"] == 1.5
    finally:
        connexion.close()


def test_hash_code_modele_non_vide():
    empreinte = hash_code_modele()
    assert isinstance(empreinte, str)
    assert len(empreinte) >= 8


def _prediction_test():
    return {
        "xg_prevu_domicile": 1.5,
        "xg_prevu_exterieur": 1.0,
        "p_victoire_domicile": 50.0,
        "p_nul": 25.0,
        "p_victoire_exterieur": 25.0,
        "score_plus_probable": "1-1",
        "p_les_deux_marquent": 55.0,
        "p_plus_de_2_buts": 50.0,
        "cartons": {"jaunes_domicile": 1.0, "jaunes_exterieur": 1.0},
    }


def test_lister_resultats_exclut_retroactif_par_defaut(tmp_path: Path):
    chemin = tmp_path / "analyses_retro.db"
    connexion = ouvrir_base(chemin)
    try:
        version_id = obtenir_ou_creer_version_modele(connexion, hash_code="retrotest")
        prediction = _prediction_test()

        id_figee = enregistrer_prevision(
            connexion,
            "La Liga",
            "2026-2027",
            "2026-08-28",
            "Barcelona",
            "Real Madrid",
            prediction,
            version_modele_id=version_id,
            retroactif=False,
        )
        id_retro = enregistrer_prevision(
            connexion,
            "La Liga",
            "2026-2027",
            "2026-08-29",
            "Sevilla",
            "Betis",
            prediction,
            version_modele_id=version_id,
            retroactif=True,
        )
        assert id_figee and id_retro

        match = {
            "date": "2026-08-28",
            "buts_domicile": 1,
            "buts_exterieur": 1,
            "xg_domicile": 1.2,
            "xg_exterieur": 1.0,
        }
        enregistrer_resultat(connexion, id_figee, match, {"points": []})
        enregistrer_resultat(
            connexion,
            id_retro,
            {**match, "date": "2026-08-29"},
            {"points": []},
        )

        sans_retro = lister_resultats_avec_previsions(connexion, "2026-2027")
        assert len(sans_retro) == 1
        assert sans_retro[0]["domicile"] == "Barcelona"

        avec_retro = lister_resultats_avec_previsions(
            connexion, "2026-2027", inclure_retroactif=True
        )
        assert len(avec_retro) == 2
    finally:
        connexion.close()


def test_retroactif_exclus_dans_analyses_prod():
    """Verifie que les 70 backfills retroactif sont exclus par defaut en prod."""
    chemin = Path(__file__).resolve().parents[3] / "donnees" / "analyses.db"
    if not chemin.is_file():
        return
    connexion = ouvrir_base(chemin)
    try:
        nb_retro = connexion.execute(
            """
            SELECT COUNT(1) FROM resultats_analyse r
            JOIN previsions_match p ON p.id = r.prevision_id
            WHERE p.retroactif = 1
            """
        ).fetchone()[0]
        if nb_retro == 0:
            return
        resultats = lister_resultats_avec_previsions(connexion, "2026-2027")
        assert len(resultats) == 0
        resultats_retro = lister_resultats_avec_previsions(
            connexion, "2026-2027", inclure_retroactif=True
        )
        assert len(resultats_retro) == nb_retro
    finally:
        connexion.close()
