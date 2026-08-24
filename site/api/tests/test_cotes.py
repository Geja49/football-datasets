"""Tests unitaires cotes.py — parsing / matching / lecture marché (sans API réelle)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import cotes


def test_arrondir_cote():
    assert cotes.arrondir_cote("2.55") == 2.55
    assert cotes.arrondir_cote(1.0) is None
    assert cotes.arrondir_cote("abc") is None
    assert cotes.arrondir_cote(None) is None


def test_parser_instant_et_a_venir():
    futur = (datetime.now(timezone.utc) + timedelta(days=2)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    instant = cotes.parser_instant(futur)
    assert instant is not None
    assert cotes.est_a_venir(instant)
    assert cotes.parser_instant("pas-une-date") is None
    assert not cotes.est_a_venir(None)


def test_extraire_1n2():
    marches = [
        {
            "key": "h2h",
            "outcomes": [
                {"name": "Barcelona", "price": 2.1},
                {"name": "Draw", "price": 3.4},
                {"name": "Real Madrid", "price": 3.2},
            ],
        }
    ]
    cotes_1n2 = cotes.extraire_1n2(marches, "Barcelona", "Real Madrid")
    assert cotes_1n2 == {"domicile": 2.1, "nul": 3.4, "exterieur": 3.2}


def test_moyenne_et_meilleure_cotes():
    liste = [
        {"domicile": 2.0, "nul": 3.0, "exterieur": 4.0},
        {"domicile": 2.2, "nul": 3.2, "exterieur": 3.8},
    ]
    assert cotes.moyenne_cotes(liste) == {
        "domicile": 2.1,
        "nul": 3.1,
        "exterieur": 3.9,
    }
    assert cotes.meilleure_cotes(liste) == {
        "domicile": 2.2,
        "nul": 3.2,
        "exterieur": 4.0,
    }
    assert cotes.moyenne_cotes([]) is None


def test_normaliser_evenement_ignore_passe():
    passe = {
        "home_team": "A",
        "away_team": "B",
        "commence_time": "2020-01-01T12:00:00Z",
        "bookmakers": [],
    }
    assert cotes.normaliser_evenement(passe, "La Liga") is None


def test_normaliser_evenement_futur():
    debut = (datetime.now(timezone.utc) + timedelta(days=3)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    evenement = {
        "home_team": "Barcelona",
        "away_team": "Real Madrid",
        "commence_time": debut,
        "bookmakers": [
            {
                "key": "pinnacle",
                "title": "Pinnacle",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Barcelona", "price": 2.05},
                            {"name": "Draw", "price": 3.5},
                            {"name": "Real Madrid", "price": 3.4},
                        ],
                    }
                ],
            }
        ],
    }
    item = cotes.normaliser_evenement(evenement, "La Liga")
    assert item is not None
    assert item["championnat"] == "La Liga"
    assert item["domicile"] == "Barcelona"
    assert item["cotes"]["moyenne"]["domicile"] == 2.05
    assert len(item["bookmakers"]) == 1


def test_construire_lecture_marche_accord():
    lecture = cotes.construire_lecture_marche(
        {"domicile": 1.8, "nul": 3.6, "exterieur": 4.5},
        "Barcelona",
        "Sevilla",
        prediction={
            "p_victoire_domicile": 55.0,
            "p_nul": 25.0,
            "p_victoire_exterieur": 20.0,
        },
    )
    assert lecture is not None
    assert lecture["disponible"] is True
    assert lecture["favori"] == "domicile"
    assert lecture["accord_statistique"] == "accord"
    assert "disclaimer" in lecture
    assert lecture["cotes"]["domicile"] == 1.8


def test_construire_lecture_marche_sans_cotes():
    assert cotes.construire_lecture_marche(None, "A", "B") is None
    assert (
        cotes.construire_lecture_marche(
            {"domicile": 1.0, "nul": 2.0, "exterieur": 3.0}, "A", "B"
        )
        is None
    )


def test_noms_equipes_proches():
    assert cotes.noms_equipes_proches("Man City", "Manchester City")
    assert not cotes.noms_equipes_proches("Barcelona", "Sevilla")


def test_telecharger_sport_mock_ok(monkeypatch):
    reponse = MagicMock()
    reponse.status_code = 200
    reponse.json.return_value = []
    monkeypatch.setattr(cotes.SESSION, "get", lambda *a, **k: reponse)
    data, code = cotes.telecharger_sport("fake-key", "soccer_spain_la_liga")
    assert data == []
    assert code is None


def test_telecharger_sport_mock_cle_refusee(monkeypatch):
    reponse = MagicMock()
    reponse.status_code = 401
    monkeypatch.setattr(cotes.SESSION, "get", lambda *a, **k: reponse)
    data, code = cotes.telecharger_sport("bad", "soccer_epl")
    assert data is None
    assert code == "cle_refusee"


def test_lecture_marche_pour_analyse_sans_cle(monkeypatch):
    monkeypatch.setattr(cotes, "lire_cle_api", lambda: "")
    assert (
        cotes.lecture_marche_pour_analyse(
            "La Liga", "Barcelona", "Real Madrid"
        )
        is None
    )


def test_trouver_match_cotes_avec_cache(monkeypatch):
    debut = (datetime.now(timezone.utc) + timedelta(days=2)).date().isoformat()
    faux_matchs = [
        {
            "championnat": "La Liga",
            "date": debut,
            "domicile": "Barcelona",
            "exterieur": "Real Madrid",
            "cotes": {
                "moyenne": {"domicile": 2.1, "nul": 3.4, "exterieur": 3.3}
            },
        }
    ]
    monkeypatch.setattr(cotes, "lire_cle_api", lambda: "cle-test")
    monkeypatch.setattr(
        cotes, "obtenir_matchs_api", lambda cle: (faux_matchs, "")
    )
    trouve = cotes.trouver_match_cotes(
        "La Liga", "Barcelona", "Real Madrid", date_match=debut
    )
    assert trouve is not None
    assert trouve["cotes"]["moyenne"]["domicile"] == 2.1
