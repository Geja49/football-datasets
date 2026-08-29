"""Tests — endpoint admin Solo (pronos weekend)."""

from datetime import date, timedelta

import communaute
import pytest

from services.solo import (
    SEUIL_CORNERS,
    SEUIL_PROBABILITE,
    _info_corners,
    _reparer_cache_pronos,
    _signal_match_physique,
    extraire_marches_qualifies,
    grouper_pronos_par_championnat,
    plage_weekend,
    vendredi_weekend,
    vider_cache_solo,
)
from modeles.solo import MatchPronoWeekend, MarcheQualifie, CornersMatch


@pytest.fixture
def fichier_communaute_temp(tmp_path, monkeypatch):
    chemin = tmp_path / "communaute_solo_test.db"
    monkeypatch.setattr(communaute, "FICHIER_COMMUNAUTE", chemin)
    monkeypatch.setattr(communaute, "_initialise", False)
    with communaute._verrou_limite:
        communaute._historique_commentaires.clear()
        communaute._historique_pronostics.clear()
        communaute._historique_sondages_match.clear()
        communaute._historique_reactions.clear()
        communaute._historique_ligues.clear()
        communaute._historique_messages_ligue.clear()
        communaute._historique_connexion_ip.clear()
        communaute._historique_connexion_identifiant.clear()
        communaute._historique_inscription_ip.clear()
    communaute.initialiser_base()
    return chemin


@pytest.fixture
def client_solo(fichier_base_temp, fichier_communaute_temp, monkeypatch):
    import cotes
    import serveur

    monkeypatch.setattr(serveur, "FICHIER_BASE", fichier_base_temp)
    monkeypatch.setattr(cotes, "FICHIER_BASE", fichier_base_temp)
    monkeypatch.setattr(cotes, "lire_cle_api", lambda: "")
    with cotes._verrou:
        cotes._cache["expire"] = 0.0
        cotes._cache["matchs"] = None
        cotes._cache["erreur"] = ""

    from fastapi.testclient import TestClient

    return TestClient(serveur.app)


def _inscrire(client, email="test@exemple.fr", pseudo="Testeur", mot_de_passe="motdepasse1"):
    return client.post(
        "/api/communaute/inscription",
        json={
            "email": email,
            "pseudo": pseudo,
            "mot_de_passe": mot_de_passe,
            "age_18_plus": True,
            "cgu_acceptees": True,
        },
    )


def test_vendredi_weekend_lundi():
    assert vendredi_weekend(date(2026, 8, 31)) == date(2026, 8, 28)
    assert vendredi_weekend(date(2026, 9, 1)) == date(2026, 9, 4)


def test_plage_weekend():
    debut, fin = plage_weekend(date(2026, 8, 28))
    assert debut == date(2026, 8, 28)
    assert fin == date(2026, 8, 31)


def test_filtre_85_pourcent():
    prediction = {
        "p_victoire_domicile": 90.0,
        "p_victoire_exterieur": 5.0,
        "p_les_deux_marquent": 70.0,
        "p_plus_de_2_buts": 88.0,
        "cartons": {
            "jaunes_match": 3.0,
            "moyenne_championnat": 4.0,
            "rythme": "calme",
            "texte": "Match calme.",
        },
    }
    marches = extraire_marches_qualifies(prediction, "Barcelona", "Real Madrid")
    types = {m.type for m in marches}
    assert "victoire_domicile" in types
    assert "over_2_5" in types
    assert "btts" not in types
    assert "victoire_exterieur" not in types
    assert all(m.probabilite is None or m.probabilite >= 85 for m in marches if m.type != "cartons_jaunes")


def test_info_corners_signal_eleve():
    info = _info_corners(
        {
            "corners": {
                "corners_match": 11.0,
                "moyenne_championnat": 9.0,
                "rythme": "eleve",
                "texte": "Beaucoup de corners attendus.",
                "p_corners_total_over": 72.0,
                "titre": "Corners élevés",
            }
        }
    )
    assert info.disponible is True
    assert info.probabilite is None
    assert info.detail


def test_info_corners_seuil_75_pourcent():
    info = _info_corners(
        {
            "corners": {
                "corners_match": 10.0,
                "moyenne_championnat": 9.0,
                "rythme": "normal",
                "texte": "Over 9.5 plausible.",
                "p_corners_total_over": SEUIL_CORNERS + 1.0,
                "titre": "Corners",
            }
        }
    )
    assert info.probabilite == SEUIL_CORNERS + 1.0

    info_sous_seuil = _info_corners(
        {
            "corners": {
                "corners_match": 10.0,
                "moyenne_championnat": 9.0,
                "rythme": "normal",
                "p_corners_total_over": SEUIL_CORNERS - 1.0,
            }
        }
    )
    assert info_sous_seuil.probabilite is None


def test_seuils_corners_vs_autres_marches():
    assert SEUIL_CORNERS == 75.0
    assert SEUIL_PROBABILITE == 85.0


def test_grouper_pronos_par_championnat():
    def _match(champ, date, heure, domicile="A", exterieur="B"):
        return MatchPronoWeekend(
            championnat=champ,
            saison="2026-2027",
            date=date,
            heure=heure,
            domicile=domicile,
            exterieur=exterieur,
            marches=[
                MarcheQualifie(type="btts", libelle="BTTS", probabilite=90.0),
            ],
            corners=CornersMatch(disponible=False, message="non disponible"),
        )

    resultats = [
        _match("Serie A", "2026-08-30", "18:00"),
        _match("Premier League", "2026-08-29", "15:00"),
        _match("Premier League", "2026-08-29", "20:00"),
        _match("La Liga", "2026-08-30", "21:00"),
    ]
    pronos_plats, groupes = grouper_pronos_par_championnat(resultats)

    assert [g.championnat for g in groupes] == [
        "Premier League",
        "La Liga",
        "Serie A",
    ]
    assert len(groupes[0].pronos) == 2
    assert [m.heure for m in groupes[0].pronos] == ["15:00", "20:00"]
    assert len(pronos_plats) == 4
    assert pronos_plats[0].championnat == "Premier League"


def test_cartons_signal_fort():
    prediction = {
        "p_victoire_domicile": 50.0,
        "p_victoire_exterieur": 30.0,
        "p_les_deux_marquent": 55.0,
        "p_plus_de_2_buts": 60.0,
        "cartons": {
            "jaunes_match": 6.5,
            "moyenne_championnat": 4.0,
            "rythme": "cartonne",
            "texte": "Match cartonné attendu.",
        },
    }
    marches = extraire_marches_qualifies(prediction, "A", "B")
    cartons = [m for m in marches if m.type == "cartons_jaunes"]
    assert len(cartons) == 1
    assert cartons[0].signal_fort is True


def test_signal_match_physique():
    actif = _signal_match_physique(
        {
            "fautes": {"rythme": "physique", "fautes_match": 28.0},
            "cartons": {"rythme": "dans_la_moyenne", "jaunes_match": 4.0},
        }
    )
    assert actif.actif is True
    assert "fautes" in (actif.detail or "").lower()

    inactif = _signal_match_physique(
        {
            "fautes": {"rythme": "dans_la_moyenne", "fautes_match": 22.0},
            "cartons": {"rythme": "calme", "jaunes_match": 3.0},
        }
    )
    assert inactif.actif is False


def test_reparer_cache_pronos_sans_groupes():
    pronos = [
        MatchPronoWeekend(
            championnat="La Liga",
            saison="2026-2027",
            date="2026-08-30",
            domicile="Barcelona",
            exterieur="Sevilla",
            marches=[
                MarcheQualifie(type="btts", libelle="BTTS", probabilite=90.0),
            ],
            corners=CornersMatch(disponible=False, message="non disponible"),
        ).model_dump(),
    ]
    repare = _reparer_cache_pronos(
        {
            "avertissement": "test",
            "weekend": {
                "date_debut": "2026-08-28",
                "date_fin": "2026-08-31",
                "libelle": "28–31 août 2026",
            },
            "seuil_probabilite": 85.0,
            "nb_matchs_analyses": 1,
            "nb_matchs_avec_prono": 1,
            "pronos": pronos,
        }
    )
    assert len(repare["pronos_par_championnat"]) == 1
    assert repare["pronos_par_championnat"][0]["championnat"] == "La Liga"
    assert len(repare["pronos_par_championnat"][0]["pronos"]) == 1


def test_pronos_weekend_refuse_non_admin(client_solo):
    vider_cache_solo()
    _inscrire(client_solo, email="user@exemple.fr", pseudo="User")
    reponse = client_solo.get("/api/solo/pronos-weekend")
    assert reponse.status_code == 403


def test_pronos_weekend_refuse_sans_connexion(client_solo):
    vider_cache_solo()
    reponse = client_solo.get("/api/solo/pronos-weekend")
    assert reponse.status_code == 401


def test_pronos_weekend_admin(client_solo, fichier_base_temp, monkeypatch):
    import sqlite3

    vider_cache_solo()
    monkeypatch.setattr(communaute, "email_admin_communaute", lambda: "admin@exemple.fr")
    _inscrire(client_solo, email="admin@exemple.fr", pseudo="AdminSolo")

    vendredi = vendredi_weekend(date(2026, 8, 22))
    samedi = vendredi + timedelta(days=1)
    connexion = sqlite3.connect(fichier_base_temp)
    connexion.execute(
        """
        INSERT INTO calendrier (date, heure, journee, championnat, saison, domicile, exterieur)
        VALUES (?, '20:00', '4', 'La Liga', '2026-2027', 'Barcelona', 'Sevilla')
        """,
        (samedi.isoformat(),),
    )
    connexion.commit()
    connexion.close()

    prediction_forte = {
        "score_plus_probable": "3-0",
        "p_victoire_domicile": 92.0,
        "p_victoire_exterieur": 3.0,
        "p_nul": 5.0,
        "p_les_deux_marquent": 40.0,
        "p_plus_de_2_buts": 86.0,
        "cartons": {
            "jaunes_match": 3.5,
            "moyenne_championnat": 4.0,
            "rythme": "calme",
            "texte": "Calme.",
        },
        "corners": {
            "corners_match": 10.5,
            "moyenne_championnat": 9.0,
            "rythme": "eleve",
            "texte": "Corners attendus.",
            "p_corners_total_over": 88.0,
            "titre": "Corners élevés",
        },
    }

    def _fake_analyser(connexion, championnat, saison, domicile, exterieur, date_limite=None):
        return {
            "prediction": prediction_forte,
            "domicile": {"nom": domicile},
            "exterieur": {"nom": exterieur},
        }

    monkeypatch.setattr("services.solo.analyser_rencontre", _fake_analyser)

    reponse = client_solo.get(
        "/api/solo/pronos-weekend",
        params={"date_debut": vendredi.isoformat()},
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["seuil_probabilite"] == 85.0
    assert "avertissement" in corps
    assert corps["nb_matchs_avec_prono"] >= 1
    assert len(corps["pronos_par_championnat"]) >= 1
    assert corps["pronos_par_championnat"][0]["championnat"] == "La Liga"
    prono = corps["pronos_par_championnat"][0]["pronos"][0]
    assert prono["domicile"] == "Barcelona"
    types = {m["type"] for m in prono["marches"]}
    assert "victoire_domicile" in types
    assert "over_2_5" in types
    assert prono["corners"]["disponible"] is True
    assert prono["corners"]["probabilite"] == 88.0
    assert "Corners" in (prono["corners"]["detail"] or "")
