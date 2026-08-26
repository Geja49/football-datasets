"""Tests unitaires des helpers serveur (sans HTTP)."""

import pytest
from fastapi import HTTPException

from serveur import (
    NOM_LDC,
    SAISON_COURANTE,
    calculer_classement,
    filtrer_matchs_a_venir,
    histogramme_simple,
    matchs_classement,
    mediane_liste,
    moyenne_liste,
    nombre_ok,
    saisons_disponibles,
    verifier_filtres,
)


def test_nombre_ok():
    assert nombre_ok("3.5") == 3.5
    assert nombre_ok(None) == 0.0
    assert nombre_ok("x") == 0.0


def test_histogramme_simple():
    histo = histogramme_simple([0, 5, 10], 10, nb_classes=5)
    assert len(histo) == 5
    assert sum(case["n"] for case in histo) == 3


def test_moyenne_et_mediane_liste():
    assert moyenne_liste([1, 2, 3]) == 2.0
    assert mediane_liste([1, 2, 3]) == 2.0
    assert mediane_liste([1, 2, 3, 4]) == 2.5
    assert moyenne_liste([]) == 0.0
    assert mediane_liste([]) == 0.0


def test_calculer_classement():
    matchs = [
        {
            "domicile": "A",
            "exterieur": "B",
            "buts_domicile": 2,
            "buts_exterieur": 0,
            "resultat": "H",
        },
        {
            "domicile": "B",
            "exterieur": "A",
            "buts_domicile": 1,
            "buts_exterieur": 1,
            "resultat": "D",
        },
    ]
    classement = calculer_classement(matchs)
    assert classement[0]["equipe"] == "A"
    assert classement[0]["pts"] == 4
    assert classement[0]["j"] == 2
    assert classement[0]["rang"] == 1
    assert classement[1]["equipe"] == "B"
    assert classement[1]["pts"] == 1


def test_matchs_classement_filtre_ldc():
    matchs = [
        {"phase": "phase de ligue", "domicile": "A"},
        {"phase": "barrages", "domicile": "B"},
        {"phase": "", "domicile": "C"},
    ]
    filtres = matchs_classement(matchs, NOM_LDC)
    assert len(filtres) == 1
    assert filtres[0]["domicile"] == "A"
    assert matchs_classement(matchs, "La Liga") == matchs


def test_saisons_disponibles_inclut_saison_courante(connexion_memoire):
    saisons = saisons_disponibles(connexion_memoire, "La Liga")
    assert SAISON_COURANTE in saisons
    assert "2025-2026" in saisons
    assert saisons[0] == SAISON_COURANTE


def test_filtrer_matchs_a_venir():
    programme = [
        {"joue": True, "date": "2026-08-01"},
        {"joue": False, "date": "2026-08-20"},
        {"joue": False, "date": "2026-08-10"},
    ]
    avenir = filtrer_matchs_a_venir(programme, "2026-08-15")
    assert len(avenir) == 1
    assert avenir[0]["date"] == "2026-08-20"


def test_verifier_filtres_ok():
    verifier_filtres("La Liga", "2026-2027")


def test_verifier_filtres_erreur():
    with pytest.raises(HTTPException) as erreur:
        verifier_filtres("Ligue inventée", "2026-2027")
    assert erreur.value.status_code == 400
    with pytest.raises(HTTPException):
        verifier_filtres("La Liga", "2026")
