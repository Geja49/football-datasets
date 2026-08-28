"""Tests du calibrateur automatique 1X2."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from calibrateur import (
    FICHIER_CALIBRATEUR,
    FICHIER_META,
    SEUIL_MIN_MATCHS,
    appliquer_calibrateur,
    charger_calibrateur,
    entrainer_calibrateur,
    lire_donnees_entrainement,
)
from historique_analyses import (
    enregistrer_prevision,
    enregistrer_resultat,
    obtenir_ou_creer_version_modele,
    ouvrir_base,
)


def _prediction_test(p1: float, pn: float, p2: float, xg_d: float = 1.5, xg_e: float = 1.0):
    return {
        "xg_prevu_domicile": xg_d,
        "xg_prevu_exterieur": xg_e,
        "p_victoire_domicile": p1,
        "p_nul": pn,
        "p_victoire_exterieur": p2,
        "probas_1x2_brutes": {
            "p_victoire_domicile": p1,
            "p_nul": pn,
            "p_victoire_exterieur": p2,
        },
        "score_plus_probable": "1-1",
        "p_les_deux_marquent": 55.0,
        "p_plus_de_2_buts": 50.0,
        "cartons": {"jaunes_domicile": 2.0, "jaunes_exterieur": 2.0},
    }


def _remplir_fixture_entrainement(connexion, nb_matchs: int = 25):
    """Cree nb_matchs resultats honnetes avec issues variees."""
    version_id = obtenir_ou_creer_version_modele(connexion, hash_code="calibtest")
    issues = ("1", "N", "2")
    buts_par_issue = {"1": (2, 1), "N": (1, 1), "2": (0, 2)}
    for i in range(nb_matchs):
        issue = issues[i % 3]
        bd, be = buts_par_issue[issue]
        p1, pn, p2 = (60.0, 25.0, 15.0) if issue == "1" else (20.0, 55.0, 25.0) if issue == "N" else (15.0, 25.0, 60.0)
        date_m = f"2026-09-{i + 1:02d}"
        pred = _prediction_test(p1, pn, p2)
        pid = enregistrer_prevision(
            connexion,
            "La Liga",
            "2026-2027",
            date_m,
            f"EquipeA{i}",
            f"EquipeB{i}",
            pred,
            version_modele_id=version_id,
            retroactif=False,
        )
        assert pid is not None
        enregistrer_resultat(
            connexion,
            pid,
            {
                "date": date_m,
                "buts_domicile": bd,
                "buts_exterieur": be,
            },
            {"points": []},
        )


def test_appliquer_sans_calibrateur_normalise():
    p1, pn, p2 = appliquer_calibrateur(50.0, 30.0, 20.0)
    assert abs(p1 + pn + p2 - 100.0) < 0.2


def test_entrainement_insuffisant(tmp_path: Path, monkeypatch):
    chemin_db = tmp_path / "analyses.db"
    chemin_pkl = tmp_path / "calibrateur.pkl"
    chemin_json = tmp_path / "calibrateur.json"
    monkeypatch.setattr("calibrateur.FICHIER_CALIBRATEUR", chemin_pkl)
    monkeypatch.setattr("calibrateur.FICHIER_META", chemin_json)

    connexion = ouvrir_base(chemin_db)
    try:
        _remplir_fixture_entrainement(connexion, nb_matchs=SEUIL_MIN_MATCHS - 1)
        resume = entrainer_calibrateur(
            connexion, chemin_modele=chemin_pkl, chemin_meta=chemin_json
        )
        assert resume["succes"] is False
        assert not chemin_pkl.is_file()
    finally:
        connexion.close()


def test_entrainement_et_application_normalise(tmp_path: Path, monkeypatch):
    chemin_db = tmp_path / "analyses.db"
    chemin_pkl = tmp_path / "calibrateur.pkl"
    chemin_json = tmp_path / "calibrateur.json"
    monkeypatch.setattr("calibrateur.FICHIER_CALIBRATEUR", chemin_pkl)
    monkeypatch.setattr("calibrateur.FICHIER_META", chemin_json)

    connexion = ouvrir_base(chemin_db)
    try:
        _remplir_fixture_entrainement(connexion, nb_matchs=SEUIL_MIN_MATCHS + 5)
        donnees = lire_donnees_entrainement(connexion)
        assert len(donnees) >= SEUIL_MIN_MATCHS

        resume = entrainer_calibrateur(
            connexion, chemin_modele=chemin_pkl, chemin_meta=chemin_json
        )
        assert resume["succes"] is True
        assert chemin_pkl.is_file()
        assert chemin_json.is_file()
        meta = json.loads(chemin_json.read_text(encoding="utf-8"))
        assert meta["nb_matchs"] >= SEUIL_MIN_MATCHS
        assert resume["brier_apres"] is not None

        cal = charger_calibrateur(chemin_pkl, forcer_rechargement=True)
        assert cal is not None

        p1, pn, p2 = appliquer_calibrateur(55.0, 25.0, 20.0, features={"championnat": "La Liga"})
        assert abs(p1 + pn + p2 - 100.0) < 0.2
        assert all(v >= 0 for v in (p1, pn, p2))
    finally:
        connexion.close()
