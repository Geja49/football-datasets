"""Tests — figer / juger les pronos Solo (Phase 1)."""

from pathlib import Path

import sqlite3

from historique_analyses import assurer_schema, ouvrir_base
from requetes.solo import inserer_prono_solo, lister_pronos_solo_weekend
from services.solo_fige import (
    bilan_weekend_solo,
    construire_pronos_depuis_figes,
    evaluer_verdict_marche,
    juger_pronos_weekend,
)


WEEKEND = "2026-08-28"
DATE_MATCH = "2026-08-29"


def _base_analyses(tmp_path: Path):
    chemin = tmp_path / "analyses_solo.db"
    connexion = ouvrir_base(chemin)
    assurer_schema(connexion)
    return chemin, connexion


def _base_football(tmp_path: Path) -> Path:
    chemin = tmp_path / "football_solo.db"
    connexion = sqlite3.connect(str(chemin))
    connexion.row_factory = sqlite3.Row
    connexion.executescript(
        """
        CREATE TABLE matchs (
            championnat TEXT,
            saison TEXT,
            date TEXT,
            domicile TEXT,
            exterieur TEXT,
            buts_domicile INTEGER,
            buts_exterieur INTEGER,
            jaunes_domicile INTEGER,
            jaunes_exterieur INTEGER,
            corners_domicile INTEGER,
            corners_exterieur INTEGER
        );
        """
    )
    connexion.commit()
    connexion.close()
    return chemin


def _inserer_prono(connexion, type_marche, libelle, proba=90.0, detail_json=None):
    assert inserer_prono_solo(
        connexion,
        cle_match="la liga|2026-2027|2026-08-29|barcelona|sevilla",
        weekend_debut=WEEKEND,
        championnat="La Liga",
        saison="2026-2027",
        date_match=DATE_MATCH,
        domicile="Barcelona",
        exterieur="Sevilla",
        type_marche=type_marche,
        libelle_marche=libelle,
        probabilite=proba,
        detail_json=detail_json,
        fige_le="2026-08-28T12:00:00Z",
    )


def test_schema_pronos_verdicts_solo(tmp_path: Path):
    chemin, connexion = _base_analyses(tmp_path)
    try:
        tables = {
            row[0]
            for row in connexion.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "pronos_solo" in tables
        assert "verdicts_solo" in tables
        _inserer_prono(connexion, "victoire_1", "Victoire Barcelona")
        connexion.commit()
        lignes = lister_pronos_solo_weekend(connexion, WEEKEND)
        assert len(lignes) == 1
        assert lignes[0]["type_marche"] == "victoire_1"
    finally:
        connexion.close()


def test_evaluer_verdict_marches_principaux():
    score = {
        "buts_domicile": 3,
        "buts_exterieur": 1,
        "jaunes_domicile": 3,
        "jaunes_exterieur": 2,
        "corners_domicile": 7,
        "corners_exterieur": 4,
    }
    vrai, code, _ = evaluer_verdict_marche("victoire_1", score)
    assert vrai is True and code == "victoire_domicile"

    vrai, code, _ = evaluer_verdict_marche("victoire_2", score)
    assert vrai is False and code == "issue_inversee"

    vrai, code, _ = evaluer_verdict_marche("btts", score)
    assert vrai is True and code == "btts_ok"

    vrai, code, _ = evaluer_verdict_marche("over_25", score)
    assert vrai is True and code == "over_25_ok"

    vrai, code, _ = evaluer_verdict_marche(
        "cartons", score, '{"seuil_jaunes": 4}'
    )
    assert vrai is True and code == "cartons_eleves"

    vrai, code, _ = evaluer_verdict_marche("corners_over_95", score)
    assert vrai is True and code == "corners_over_ok"


def test_evaluer_verdict_faux_et_under():
    score = {
        "buts_domicile": 0,
        "buts_exterieur": 1,
        "jaunes_domicile": 1,
        "jaunes_exterieur": 1,
        "corners_domicile": 3,
        "corners_exterieur": 2,
    }
    vrai, code, _ = evaluer_verdict_marche("victoire_1", score)
    assert vrai is False and code == "issue_inversee"

    vrai, code, _ = evaluer_verdict_marche("btts", score)
    assert vrai is False and code == "btts_rate"

    vrai, code, _ = evaluer_verdict_marche("over_25", score)
    assert vrai is False and code == "under_expected"

    vrai, code, _ = evaluer_verdict_marche(
        "cartons", score, '{"seuil_jaunes": 4}'
    )
    assert vrai is False and code == "cartons_sous_seuil"

    vrai, code, _ = evaluer_verdict_marche("corners_over_95", score)
    assert vrai is False and code == "corners_under"


def test_juger_prono_avec_score(tmp_path: Path):
    chemin_analyses, connexion_analyses = _base_analyses(tmp_path)
    _inserer_prono(connexion_analyses, "victoire_1", "Victoire Barcelona", 92.0)
    _inserer_prono(connexion_analyses, "over_25", "Plus de 2,5 buts", 88.0)
    connexion_analyses.commit()
    connexion_analyses.close()

    chemin_foot = _base_football(tmp_path)
    foot = sqlite3.connect(str(chemin_foot))
    foot.row_factory = sqlite3.Row
    foot.execute(
        """
        INSERT INTO matchs (
            championnat, saison, date, domicile, exterieur,
            buts_domicile, buts_exterieur,
            jaunes_domicile, jaunes_exterieur,
            corners_domicile, corners_exterieur
        ) VALUES (
            'La Liga', '2026-2027', ?, 'Barcelona', 'Sevilla',
            2, 1, 2, 2, 5, 4
        )
        """,
        (DATE_MATCH,),
    )
    foot.commit()

    resume = juger_pronos_weekend(
        foot,
        date_debut=WEEKEND,
        chemin_analyses=chemin_analyses,
    )
    foot.close()

    assert resume["nb_juges"] == 2
    assert resume["nb_vrais"] == 2
    assert resume["nb_faux"] == 0
    assert resume["hit_rate"] == 100.0

    # Second passage : déjà jugés → 0 nouveau.
    foot = sqlite3.connect(str(chemin_foot))
    foot.row_factory = sqlite3.Row
    resume2 = juger_pronos_weekend(
        foot,
        date_debut=WEEKEND,
        chemin_analyses=chemin_analyses,
    )
    foot.close()
    assert resume2["nb_juges"] == 0

    bilan = bilan_weekend_solo(WEEKEND, chemin_analyses=chemin_analyses)
    assert bilan.nb_juges == 2
    assert bilan.hit_rate == 100.0
    assert "victoire_1" in bilan.par_marche
    assert len(bilan.details) == 2


def test_juger_verdict_faux(tmp_path: Path):
    chemin_analyses, connexion_analyses = _base_analyses(tmp_path)
    _inserer_prono(connexion_analyses, "victoire_1", "Victoire Barcelona")
    connexion_analyses.commit()
    connexion_analyses.close()

    chemin_foot = _base_football(tmp_path)
    foot = sqlite3.connect(str(chemin_foot))
    foot.row_factory = sqlite3.Row
    foot.execute(
        """
        INSERT INTO matchs (
            championnat, saison, date, domicile, exterieur,
            buts_domicile, buts_exterieur
        ) VALUES (
            'La Liga', '2026-2027', ?, 'Barcelona', 'Sevilla', 0, 2
        )
        """,
        (DATE_MATCH,),
    )
    foot.commit()

    resume = juger_pronos_weekend(
        foot,
        date_debut=WEEKEND,
        chemin_analyses=chemin_analyses,
    )
    foot.close()
    assert resume["nb_juges"] == 1
    assert resume["nb_vrais"] == 0
    assert resume["nb_faux"] == 1
    assert resume["hit_rate"] == 0.0


def test_construire_pronos_depuis_figes(tmp_path: Path):
    chemin_analyses, connexion_analyses = _base_analyses(tmp_path)
    _inserer_prono(connexion_analyses, "btts", "Les deux équipes marquent", 86.0)
    _inserer_prono(
        connexion_analyses,
        "corners_over_95",
        "Plus de 9,5 corners",
        78.0,
        detail_json='{"detail": "Corners attendus.", "seuil_ligne": 9.5}',
    )
    connexion_analyses.commit()
    connexion_analyses.close()

    reponse = construire_pronos_depuis_figes(
        WEEKEND, chemin_analyses=chemin_analyses
    )
    assert reponse is not None
    assert reponse.source == "fige"
    assert reponse.fige_le is not None
    assert reponse.nb_matchs_avec_prono == 1
    match = reponse.pronos[0]
    assert match.domicile == "Barcelona"
    types = {m.type for m in match.marches}
    assert "btts" in types
    assert match.corners.disponible is True
    assert match.corners.probabilite == 78.0
