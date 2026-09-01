"""Tests — endpoint admin Solo (pronos weekend)."""

from datetime import date, timedelta

import communaute
import pytest

from services.solo import (
    SEUIL_CORNERS_POTENTIEL,
    SEUIL_HAUTE_CONFIANCE,
    SEUIL_MISE_EN_AVANT,
    SEUIL_PROBABILITE,
    TYPES_MARCHES_CARTONS_API,
    _info_corners,
    _reparer_cache_pronos,
    _signal_match_physique,
    est_marche_cartons_api,
    extraire_marches_qualifies,
    filtrer_marches_pour_utilisateur,
    filtrer_reponse_pronos_utilisateur,
    grouper_pronos_par_championnat,
    plage_weekend,
    vendredi_weekend,
    vider_cache_solo,
)
from modeles.solo import (
    CornersMatch,
    GroupePronosChampionnat,
    MarcheQualifie,
    MatchPronoWeekend,
    ReponsePronosWeekend,
    WeekendInfo,
)


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


def test_victoire_toujours_incluse_sans_seuil_85():
    prediction = {
        "p_victoire_domicile": 62.0,
        "p_victoire_exterieur": 18.0,
        "p_nul": 20.0,
        "p_les_deux_marquent": 40.0,
        "p_plus_de_2_buts": 45.0,
        "xg_total": 1.8,
        "cartons": {
            "jaunes_match": 3.0,
            "moyenne_championnat": 4.0,
            "rythme": "calme",
        },
    }
    marches = extraire_marches_qualifies(prediction, "Barcelona", "Real Madrid")
    types = {m.type for m in marches}
    assert "victoire_domicile" in types
    assert "victoire_exterieur" not in types
    assert "over_2_5" not in types
    assert "btts" not in types
    victoire = next(m for m in marches if m.type == "victoire_domicile")
    assert victoire.probabilite == 62.0
    assert victoire.haute_confiance is False
    assert victoire.mise_en_avant is False


def test_deux_victoires_si_match_ouvert():
    prediction = {
        "p_victoire_domicile": 38.0,
        "p_victoire_exterieur": 34.0,
        "p_nul": 28.0,
        "p_les_deux_marquent": 40.0,
        "p_plus_de_2_buts": 40.0,
        "xg_total": 1.5,
    }
    marches = extraire_marches_qualifies(prediction, "A", "B")
    types = {m.type for m in marches}
    assert "victoire_domicile" in types
    assert "victoire_exterieur" in types


def test_buts_et_jaunes_over_1_5():
    prediction = {
        "p_victoire_domicile": 48.0,
        "p_victoire_exterieur": 28.0,
        "p_plus_de_2_buts": 40.0,
        "xg_total": 2.4,
        "xg_prevu_domicile": 1.7,
        "xg_prevu_exterieur": 0.7,
        "cartons": {
            "jaunes_match": 4.2,
            "jaunes_domicile": 2.1,
            "jaunes_exterieur": 2.1,
            "moyenne_championnat": 4.0,
            "rythme": "dans_la_moyenne",
        },
    }
    marches = extraire_marches_qualifies(prediction, "PSG", "Nantes")
    types = {m.type for m in marches}
    assert "over_1_5" in types
    assert "over_1_5_domicile" in types
    assert "cartons_over_1_5" in types
    assert "cartons_over_1_5_domicile" in types
    assert "cartons_over_1_5_exterieur" in types
    # Nantes à 0.7 xG : pas de +1.5 équipe
    assert "over_1_5_exterieur" not in types


def test_filtrer_marches_cartons_utilisateur():
    """Les marchés cartons restent en extraction mais sont masqués utilisateur."""
    prediction = {
        "p_victoire_domicile": 48.0,
        "p_victoire_exterieur": 28.0,
        "p_plus_de_2_buts": 40.0,
        "xg_total": 2.4,
        "xg_prevu_domicile": 1.7,
        "cartons": {
            "jaunes_match": 4.2,
            "jaunes_domicile": 2.1,
            "jaunes_exterieur": 2.1,
            "moyenne_championnat": 4.0,
            "rythme": "dans_la_moyenne",
        },
    }
    marches = extraire_marches_qualifies(prediction, "PSG", "Nantes")
    types_bruts = {m.type for m in marches}
    assert "cartons_over_1_5" in types_bruts
    filtres = filtrer_marches_pour_utilisateur(marches)
    types_filtres = {m.type for m in filtres}
    assert not types_filtres & TYPES_MARCHES_CARTONS_API
    assert "over_1_5" in types_filtres
    assert all(est_marche_cartons_api(t) for t in types_bruts - types_filtres)


def test_filtrer_reponse_pronos_exclut_match_sans_autre_marche():
    """Un match avec uniquement des cartons disparaît de la réponse utilisateur."""
    match = MatchPronoWeekend(
        championnat="Ligue 1",
        saison="2026-2027",
        date="2026-08-29",
        domicile="PSG",
        exterieur="Nantes",
        marches=[
            MarcheQualifie(
                type="cartons_over_1_5",
                libelle="Plus de 1,5 cartons jaunes",
                probabilite=72.0,
            )
        ],
        corners=CornersMatch(disponible=False, message="non disponible"),
    )
    reponse = ReponsePronosWeekend(
        avertissement="test",
        weekend=WeekendInfo(
            date_debut="2026-08-28",
            date_fin="2026-08-31",
            libelle="test",
        ),
        seuil_probabilite=85.0,
        seuil_mise_en_avant=75.0,
        nb_matchs_analyses=1,
        nb_matchs_avec_prono=1,
        pronos=[match],
        pronos_par_championnat=[
            GroupePronosChampionnat(championnat="Ligue 1", pronos=[match])
        ],
    )
    filtree = filtrer_reponse_pronos_utilisateur(reponse)
    assert filtree.nb_matchs_avec_prono == 0
    assert filtree.pronos == []


def test_buts_potentiel_xg_sans_seuil_85():
    prediction = {
        "p_victoire_domicile": 40.0,
        "p_victoire_exterieur": 30.0,
        "p_les_deux_marquent": 55.0,
        "p_plus_de_2_buts": 58.0,
        "xg_total": 2.6,
    }
    marches = extraire_marches_qualifies(prediction, "A", "B")
    over = [m for m in marches if m.type == "over_2_5"]
    assert len(over) == 1
    assert over[0].probabilite == 58.0
    assert over[0].haute_confiance is False
    assert over[0].mise_en_avant is False
    assert over[0].detail and "2.6" in over[0].detail


def test_buts_potentiel_proba_utile_sans_xg():
    prediction = {
        "p_victoire_domicile": 45.0,
        "p_victoire_exterieur": 25.0,
        "p_plus_de_2_buts": 61.0,
        "xg_total": 1.9,
    }
    marches = extraire_marches_qualifies(prediction, "A", "B")
    assert any(m.type == "over_2_5" for m in marches)


def test_btts_reste_haute_confiance():
    prediction = {
        "p_victoire_domicile": 50.0,
        "p_victoire_exterieur": 20.0,
        "p_les_deux_marquent": 90.0,
        "p_plus_de_2_buts": 40.0,
        "xg_total": 1.5,
    }
    marches = extraire_marches_qualifies(prediction, "A", "B")
    btts = [m for m in marches if m.type == "btts"]
    assert len(btts) == 1
    assert btts[0].haute_confiance is True
    assert btts[0].mise_en_avant is True


def test_mise_en_avant_entre_75_et_85():
    prediction = {
        "p_victoire_domicile": 78.0,
        "p_victoire_exterieur": 12.0,
        "p_nul": 10.0,
        "p_les_deux_marquent": 40.0,
        "p_plus_de_2_buts": 45.0,
        "xg_total": 1.8,
    }
    marches = extraire_marches_qualifies(prediction, "A", "B")
    victoire = next(m for m in marches if m.type == "victoire_domicile")
    assert victoire.haute_confiance is False
    assert victoire.mise_en_avant is True


def test_tri_marches_mise_en_avant_en_tete():
    prediction = {
        "p_victoire_domicile": 55.0,
        "p_victoire_exterieur": 25.0,
        "p_nul": 20.0,
        "p_les_deux_marquent": 40.0,
        "p_plus_de_2_buts": 80.0,
        "xg_total": 2.8,
        "xg_prevu_domicile": 1.9,
        "xg_prevu_exterieur": 0.9,
    }
    marches = extraire_marches_qualifies(prediction, "A", "B")
    assert marches[0].mise_en_avant is True
    assert marches[0].probabilite >= SEUIL_MISE_EN_AVANT
    # Les marchés ≥ 75 % précèdent ceux en dessous.
    idx_sous_seuil = next(
        i for i, m in enumerate(marches) if (m.probabilite or 0) < SEUIL_MISE_EN_AVANT
    )
    assert all(
        (m.probabilite or 0) >= SEUIL_MISE_EN_AVANT for m in marches[:idx_sous_seuil]
    )


def test_info_corners_potentiel_au_dessus_de_8():
    info = _info_corners(
        {
            "corners": {
                "corners_match": 9.2,
                "moyenne_championnat": 9.0,
                "rythme": "eleve",
                "texte": "Beaucoup de corners attendus.",
                "p_corners_total_over": 55.0,
                "titre": "Corners élevés",
            }
        }
    )
    assert info.disponible is True
    assert info.potentiel is True
    assert info.fort is True
    assert info.total_prevu == 9.2
    assert info.ligne_over == 8.5
    assert info.probabilite is not None
    assert info.probabilite > 0


def test_info_corners_potentiel_sans_fort():
    info = _info_corners(
        {
            "corners": {
                "corners_match": 8.4,
                "moyenne_championnat": 9.0,
                "rythme": "eleve",
                "p_corners_total_over": 48.0,
            }
        }
    )
    assert info.potentiel is True
    assert info.fort is False
    assert info.ligne_over == 8.5


def test_info_corners_sous_seuil_potentiel():
    info = _info_corners(
        {
            "corners": {
                "corners_match": 7.5,
                "moyenne_championnat": 9.0,
                "rythme": "normal",
                "p_corners_total_over": 40.0,
                "titre": "Corners",
            }
        }
    )
    assert info.disponible is True
    assert info.potentiel is False
    assert info.fort is False
    assert info.total_prevu == 7.5
    assert info.total_prevu <= SEUIL_CORNERS_POTENTIEL


def test_seuils_badge_haute_confiance():
    assert SEUIL_HAUTE_CONFIANCE == 85.0
    assert SEUIL_PROBABILITE == 85.0
    assert SEUIL_MISE_EN_AVANT == 75.0
    assert SEUIL_CORNERS_POTENTIEL == 8.0


def test_grouper_pronos_corners_fort_en_tete():
    def _match(champ, date, heure, total_corners=None, domicile="A", exterieur="B"):
        if total_corners is None:
            corners = CornersMatch(disponible=False, message="non disponible")
        else:
            corners = CornersMatch(
                disponible=True,
                total_prevu=total_corners,
                potentiel=total_corners > 8,
                fort=total_corners > 9,
                probabilite=55.0,
                ligne_over=8.5,
            )
        return MatchPronoWeekend(
            championnat=champ,
            saison="2026-2027",
            date=date,
            heure=heure,
            domicile=domicile,
            exterieur=exterieur,
            marches=[
                MarcheQualifie(type="victoire_domicile", libelle="Victoire A", probabilite=55.0),
            ],
            corners=corners,
        )

    resultats = [
        _match("Premier League", "2026-08-29", "15:00", total_corners=7.0),
        _match("Premier League", "2026-08-29", "12:00", total_corners=9.5),
        _match("Premier League", "2026-08-29", "18:00", total_corners=8.5),
    ]
    _, groupes = grouper_pronos_par_championnat(resultats)
    heures = [m.heure for m in groupes[0].pronos]
    assert heures == ["12:00", "18:00", "15:00"]


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
        "p_plus_de_2_buts": 40.0,
        "xg_total": 1.5,
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
    assert "super utilisateurs" in reponse.json()["detail"].lower() or (
        "administrateurs" in reponse.json()["detail"].lower()
    )


def test_pronos_weekend_refuse_sans_connexion(client_solo):
    vider_cache_solo()
    reponse = client_solo.get("/api/solo/pronos-weekend")
    assert reponse.status_code == 401


def _preparer_match_weekend(fichier_base_temp):
    import sqlite3

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
    return vendredi


def _patch_analyser_forte(monkeypatch):
    prediction_forte = {
        "score_plus_probable": "3-0",
        "p_victoire_domicile": 72.0,
        "p_victoire_exterieur": 12.0,
        "p_nul": 16.0,
        "p_les_deux_marquent": 40.0,
        "p_plus_de_2_buts": 64.0,
        "xg_total": 2.8,
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
            "p_corners_total_over": 68.0,
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


def test_pronos_weekend_admin(client_solo, fichier_base_temp, monkeypatch):
    vider_cache_solo()
    monkeypatch.setattr(communaute, "email_admin_communaute", lambda: "admin@exemple.fr")
    _inscrire(client_solo, email="admin@exemple.fr", pseudo="AdminSolo")

    vendredi = _preparer_match_weekend(fichier_base_temp)
    _patch_analyser_forte(monkeypatch)

    reponse = client_solo.get(
        "/api/solo/pronos-weekend",
        params={"date_debut": vendredi.isoformat()},
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["seuil_probabilite"] == 85.0
    assert corps["seuil_mise_en_avant"] == 75.0
    assert "avertissement" in corps
    assert corps["nb_matchs_avec_prono"] >= 1
    assert len(corps["pronos_par_championnat"]) >= 1
    assert corps["pronos_par_championnat"][0]["championnat"] == "La Liga"
    prono = corps["pronos_par_championnat"][0]["pronos"][0]
    assert prono["domicile"] == "Barcelona"
    types = {m["type"] for m in prono["marches"]}
    assert "victoire_domicile" in types
    assert "over_2_5" in types
    assert not types & set(TYPES_MARCHES_CARTONS_API)
    victoire = next(m for m in prono["marches"] if m["type"] == "victoire_domicile")
    assert victoire["mise_en_avant"] is False
    assert victoire["haute_confiance"] is False
    assert prono["corners"]["disponible"] is True
    assert prono["corners"]["potentiel"] is True
    assert prono["corners"]["fort"] is True
    assert prono["corners"]["total_prevu"] == 10.5
    assert prono["corners"]["ligne_over"] == 8.5
    assert prono["corners"]["probabilite"] is not None
    assert "Corners" in (prono["corners"]["detail"] or "")
    assert prono["buts_prevus_total"] == 2.8
    assert prono["proba_over_2_5"] == 64.0


def test_pronos_weekend_super_utilisateur(client_solo, fichier_base_temp, monkeypatch):
    """Un super utilisateur (non admin) a accès aux pronos Solo."""
    vider_cache_solo()
    inscription = _inscrire(
        client_solo, email="super@exemple.fr", pseudo="SuperSolo"
    )
    assert inscription.status_code == 200
    corps_session = client_solo.get("/api/communaute/moi").json()
    assert corps_session["utilisateur"]["est_admin"] is False
    assert corps_session["utilisateur"]["super_utilisateur"] is False

    connexion = communaute.ouvrir_base()
    try:
        connexion.execute(
            "UPDATE utilisateurs SET super_utilisateur = 1 WHERE email = ?",
            ("super@exemple.fr",),
        )
        connexion.commit()
    finally:
        connexion.close()

    # Recharger la session pour exposer le flag mis à jour
    client_solo.post(
        "/api/communaute/connexion",
        json={"identifiant": "super@exemple.fr", "mot_de_passe": "motdepasse1"},
    )
    moi = client_solo.get("/api/communaute/moi").json()
    assert moi["utilisateur"]["super_utilisateur"] is True
    assert moi["utilisateur"]["est_admin"] is False

    vendredi = _preparer_match_weekend(fichier_base_temp)
    _patch_analyser_forte(monkeypatch)

    reponse = client_solo.get(
        "/api/solo/pronos-weekend",
        params={"date_debut": vendredi.isoformat()},
    )
    assert reponse.status_code == 200
    assert reponse.json()["nb_matchs_avec_prono"] >= 1


def test_a_acces_solo_helper():
    assert communaute.a_acces_solo({"est_admin": True, "super_utilisateur": 0}) is True
    assert communaute.a_acces_solo({"est_admin": 0, "super_utilisateur": 1}) is True
    assert communaute.a_acces_solo({"est_admin": False, "super_utilisateur": False}) is False
    assert communaute.a_acces_solo({"est_admin": False}) is False


def test_bilan_pronos_refuse_non_admin(client_solo):
    _inscrire(client_solo, email="user-bilan@exemple.fr", pseudo="UserBilan")
    reponse = client_solo.get("/api/solo/bilan-pronos")
    assert reponse.status_code == 403
    detail = reponse.json()["detail"].lower()
    assert "administrateurs" in detail or "super utilisateurs" in detail


def test_bilan_pronos_filtre_70(client_solo, tmp_path, monkeypatch):
    """GET /api/solo/bilan-pronos ne renvoie que les marchés ≥ 70 %."""
    import historique_analyses
    from historique_analyses import assurer_schema, ouvrir_base
    from requetes.solo import inserer_prono_solo, inserer_verdict_solo
    from services.solo_fige import SEUIL_BILAN_PRONOS

    chemin = tmp_path / "analyses_bilan_api.db"
    monkeypatch.setattr(historique_analyses, "FICHIER_ANALYSES", chemin)

    weekend = "2026-08-28"
    connexion = ouvrir_base(chemin)
    assurer_schema(connexion)
    for type_m, libelle, proba in (
        ("victoire_1", "Victoire Barça", 88.0),
        ("over_25", "Over 2.5", 55.0),
        ("btts", "BTTS", 71.0),
    ):
        inserer_prono_solo(
            connexion,
            cle_match="la liga|2026-2027|2026-08-29|barcelona|sevilla",
            weekend_debut=weekend,
            championnat="La Liga",
            saison="2026-2027",
            date_match="2026-08-29",
            domicile="Barcelona",
            exterieur="Sevilla",
            type_marche=type_m,
            libelle_marche=libelle,
            probabilite=proba,
            detail_json=None,
            fige_le="2026-08-28T12:00:00Z",
        )
    connexion.commit()
    for ligne in connexion.execute("SELECT id, type_marche FROM pronos_solo").fetchall():
        inserer_verdict_solo(
            connexion,
            prono_solo_id=int(ligne["id"]),
            vrai=True,
            motif_code="ok",
            motif_texte="ok",
            buts_domicile=2,
            buts_exterieur=1,
            juge_le="2026-08-30T10:00:00Z",
        )
    connexion.commit()
    connexion.close()

    monkeypatch.setattr(communaute, "email_admin_communaute", lambda: "admin-bilan@exemple.fr")
    _inscrire(client_solo, email="admin-bilan@exemple.fr", pseudo="AdminBilan")

    reponse = client_solo.get(
        "/api/solo/bilan-pronos",
        params={"date_debut": weekend},
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["seuil_probabilite"] == SEUIL_BILAN_PRONOS
    assert corps["nb_pronos"] == 2
    assert corps["nb_juges"] == 2
    assert corps["hit_rate"] == 100.0
    assert all(d["probabilite"] >= 70.0 for d in corps["details"])
    types = {d["type_marche"] for d in corps["details"]}
    assert "over_25" not in types
    assert "victoire_1" in types
    assert "btts" in types
