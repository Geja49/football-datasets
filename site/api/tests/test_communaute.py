"""Tests Phase 1 — comptes et commentaires communauté."""

import pytest

import communaute


@pytest.fixture
def fichier_communaute_temp(tmp_path, monkeypatch):
    chemin = tmp_path / "communaute_test.db"
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
def client_communaute(fichier_base_temp, fichier_communaute_temp, monkeypatch):
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


def test_inscription_et_moi(client_communaute):
    reponse = _inscrire(client_communaute)
    assert reponse.status_code == 200
    assert reponse.json()["utilisateur"]["pseudo"] == "Testeur"
    assert reponse.json()["utilisateur"]["changements_pseudo_restants"] == 4

    moi = client_communaute.get("/api/communaute/moi")
    assert moi.status_code == 200
    assert moi.json()["utilisateur"]["pseudo"] == "Testeur"
    assert moi.json()["utilisateur"]["changements_pseudo_restants"] == 4


def test_inscription_sans_cgu_refusee(client_communaute):
    reponse = client_communaute.post(
        "/api/communaute/inscription",
        json={
            "email": "autre@exemple.fr",
            "pseudo": "Autre",
            "mot_de_passe": "motdepasse1",
            "age_18_plus": True,
            "cgu_acceptees": False,
        },
    )
    assert reponse.status_code == 400


def test_connexion_par_email(client_communaute):
    _inscrire(client_communaute)
    client_communaute.post("/api/communaute/deconnexion")

    reponse = client_communaute.post(
        "/api/communaute/connexion",
        json={"identifiant": "test@exemple.fr", "mot_de_passe": "motdepasse1"},
    )
    assert reponse.status_code == 200
    assert reponse.json()["utilisateur"]["pseudo"] == "Testeur"


def test_connexion_par_pseudo(client_communaute):
    _inscrire(client_communaute)
    client_communaute.post("/api/communaute/deconnexion")

    reponse = client_communaute.post(
        "/api/communaute/connexion",
        json={"identifiant": "Testeur", "mot_de_passe": "motdepasse1"},
    )
    assert reponse.status_code == 200
    assert reponse.json()["utilisateur"]["pseudo"] == "Testeur"

    # Pseudo insensible à la casse
    client_communaute.post("/api/communaute/deconnexion")
    reponse_casse = client_communaute.post(
        "/api/communaute/connexion",
        json={"identifiant": "testeur", "mot_de_passe": "motdepasse1"},
    )
    assert reponse_casse.status_code == 200


def test_connexion_identifiant_incorrect(client_communaute):
    _inscrire(client_communaute)
    client_communaute.post("/api/communaute/deconnexion")

    reponse = client_communaute.post(
        "/api/communaute/connexion",
        json={"identifiant": "Inexistant", "mot_de_passe": "motdepasse1"},
    )
    assert reponse.status_code == 401
    assert "Identifiant ou mot de passe incorrect" in reponse.json()["detail"]

    mauvais_mdp = client_communaute.post(
        "/api/communaute/connexion",
        json={"identifiant": "Testeur", "mot_de_passe": "mauvaismdp"},
    )
    assert mauvais_mdp.status_code == 401
    assert mauvais_mdp.json()["detail"] == reponse.json()["detail"]


def test_commentaire_publication_et_liste(client_communaute):
    _inscrire(client_communaute)
    publication = client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Real Madrid",
            "contenu": "Match très ouvert selon les stats.",
        },
    )
    assert publication.status_code == 200
    assert publication.json()["commentaire"]["contenu"].startswith("Match")

    liste = client_communaute.get(
        "/api/communaute/commentaires",
        params={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Real Madrid",
        },
    )
    assert liste.status_code == 200
    assert len(liste.json()["commentaires"]) == 1
    assert "disclaimer" in liste.json()


def test_commentaire_requiert_connexion(client_communaute):
    reponse = client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Real Madrid",
            "contenu": "Sans session",
        },
    )
    assert reponse.status_code == 401


def test_signalement_commentaire(client_communaute):
    _inscrire(client_communaute, email="a@exemple.fr", pseudo="Alice")
    publication = client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Sevilla",
            "contenu": "Commentaire à signaler",
        },
    )
    commentaire_id = publication.json()["commentaire"]["id"]

    client_communaute.post("/api/communaute/deconnexion")
    _inscrire(client_communaute, email="b@exemple.fr", pseudo="Bob")

    signalement = client_communaute.post(
        f"/api/communaute/commentaires/{commentaire_id}/signaler",
        json={"motif": "Spam"},
    )
    assert signalement.status_code == 200


def test_suppression_admin(client_communaute, monkeypatch):
    monkeypatch.setattr(communaute, "email_admin_communaute", lambda: "admin@exemple.fr")
    _inscrire(
        client_communaute,
        email="admin@exemple.fr",
        pseudo="Admin",
        mot_de_passe="motdepasse1",
    )
    publication = client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Valencia",
            "contenu": "À modérer",
        },
    )
    commentaire_id = publication.json()["commentaire"]["id"]

    suppression = client_communaute.delete(f"/api/communaute/commentaires/{commentaire_id}")
    assert suppression.status_code == 200

    liste = client_communaute.get(
        "/api/communaute/commentaires",
        params={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Valencia",
        },
    )
    assert liste.json()["commentaires"] == []


def _ajouter_match_futur(chemin_base, domicile="Barcelona", exterieur="Valencia", jours=30):
    import sqlite3
    from datetime import date, timedelta

    jour = (date.today() + timedelta(days=jours)).isoformat()
    connexion = sqlite3.connect(chemin_base)
    connexion.execute(
        """
        INSERT INTO calendrier (date, heure, journee, championnat, saison, domicile, exterieur)
        VALUES (?, '20:00', '20', 'La Liga', '2026-2027', ?, ?)
        """,
        (jour, domicile, exterieur),
    )
    connexion.commit()
    connexion.close()


def test_depot_pronostic_score(client_communaute, fichier_base_temp, monkeypatch):
    monkeypatch.setattr(communaute, "FICHIER_FOOTBALL", fichier_base_temp)
    _ajouter_match_futur(fichier_base_temp)
    _inscrire(client_communaute)

    depot = client_communaute.post(
        "/api/communaute/pronostics",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Valencia",
            "type_pronostic": "score",
            "buts_domicile": 2,
            "buts_exterieur": 1,
        },
    )
    assert depot.status_code == 200
    prono = depot.json()["pronostic"]
    assert prono["type_pronostic"] == "score"
    assert prono["buts_domicile"] == 2
    assert prono["verrouille"] is False

    lecture = client_communaute.get(
        "/api/communaute/pronostics",
        params={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Valencia",
        },
    )
    assert lecture.status_code == 200
    assert lecture.json()["pronostic"]["libelle"] == "2 – 1"


def test_depot_pronostic_1x2(client_communaute, fichier_base_temp, monkeypatch):
    monkeypatch.setattr(communaute, "FICHIER_FOOTBALL", fichier_base_temp)
    _ajouter_match_futur(fichier_base_temp, "Sevilla", "Real Madrid")
    _inscrire(client_communaute, email="1x2@exemple.fr", pseudo="Pronostiqueur")

    depot = client_communaute.post(
        "/api/communaute/pronostics",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Sevilla",
            "exterieur": "Real Madrid",
            "type_pronostic": "1x2",
            "resultat_1x2": "N",
        },
    )
    assert depot.status_code == 200
    assert depot.json()["pronostic"]["resultat_1x2"] == "N"


def test_pronostic_requiert_connexion(client_communaute):
    reponse = client_communaute.post(
        "/api/communaute/pronostics",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Valencia",
            "type_pronostic": "score",
            "buts_domicile": 1,
            "buts_exterieur": 0,
        },
    )
    assert reponse.status_code == 401


def test_pronostic_match_deja_joue_refuse(client_communaute, fichier_base_temp, monkeypatch):
    monkeypatch.setattr(communaute, "FICHIER_FOOTBALL", fichier_base_temp)
    _inscrire(client_communaute, email="joue@exemple.fr", pseudo="Tardif")

    reponse = client_communaute.post(
        "/api/communaute/pronostics",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Sevilla",
            "type_pronostic": "score",
            "buts_domicile": 1,
            "buts_exterieur": 0,
        },
    )
    assert reponse.status_code == 409


def test_pronostic_verrouille_apres_coup_envoi(
    client_communaute, fichier_base_temp, monkeypatch
):
    monkeypatch.setattr(communaute, "FICHIER_FOOTBALL", fichier_base_temp)
    import sqlite3

    connexion = sqlite3.connect(fichier_base_temp)
    connexion.execute(
        """
        INSERT INTO calendrier (date, heure, journee, championnat, saison, domicile, exterieur)
        VALUES ('2020-01-01', '12:00', '1', 'La Liga', '2026-2027', 'Barcelona', 'Valencia')
        """
    )
    connexion.commit()
    connexion.close()

    _inscrire(client_communaute, email="lock@exemple.fr", pseudo="Lock")

    reponse = client_communaute.post(
        "/api/communaute/pronostics",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Valencia",
            "type_pronostic": "score",
            "buts_domicile": 0,
            "buts_exterieur": 0,
        },
    )
    assert reponse.status_code == 409


def test_mes_pronostics(client_communaute, fichier_base_temp, monkeypatch):
    monkeypatch.setattr(communaute, "FICHIER_FOOTBALL", fichier_base_temp)
    _ajouter_match_futur(fichier_base_temp)
    _inscrire(client_communaute, email="mes@exemple.fr", pseudo="Historique")

    client_communaute.post(
        "/api/communaute/pronostics",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Valencia",
            "type_pronostic": "score",
            "buts_domicile": 3,
            "buts_exterieur": 2,
        },
    )

    liste = client_communaute.get("/api/communaute/pronostics/mes-pronos")
    assert liste.status_code == 200
    assert len(liste.json()["pronostics"]) == 1
    assert "disclaimer" in liste.json()


def test_modification_pronostic_avant_coup_envoi(
    client_communaute, fichier_base_temp, monkeypatch
):
    monkeypatch.setattr(communaute, "FICHIER_FOOTBALL", fichier_base_temp)
    _ajouter_match_futur(fichier_base_temp)
    _inscrire(client_communaute, email="modif@exemple.fr", pseudo="Modifieur")

    client_communaute.post(
        "/api/communaute/pronostics",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Valencia",
            "type_pronostic": "score",
            "buts_domicile": 1,
            "buts_exterieur": 0,
        },
    )

    maj = client_communaute.post(
        "/api/communaute/pronostics",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Valencia",
            "type_pronostic": "1x2",
            "resultat_1x2": "2",
        },
    )
    assert maj.status_code == 200
    assert maj.json()["pronostic"]["type_pronostic"] == "1x2"
    assert maj.json()["pronostic"]["resultat_1x2"] == "2"


def test_calculer_points_pronostic():
    ligne_score_exact = {
        "type_pronostic": "score",
        "buts_domicile": 2,
        "buts_exterieur": 1,
        "resultat_1x2": None,
    }
    ligne_bon_vainqueur = {
        "type_pronostic": "score",
        "buts_domicile": 3,
        "buts_exterieur": 0,
        "resultat_1x2": None,
    }
    ligne_1x2 = {
        "type_pronostic": "1x2",
        "buts_domicile": None,
        "buts_exterieur": None,
        "resultat_1x2": "N",
    }
    resultat = {"buts_domicile": 2, "buts_exterieur": 1}

    assert communaute.calculer_points_pronostic(ligne_score_exact, resultat)["points"] == 3
    assert communaute.calculer_points_pronostic(ligne_bon_vainqueur, resultat)["points"] == 1
    assert communaute.calculer_points_pronostic(ligne_1x2, {"buts_domicile": 1, "buts_exterieur": 1})["points"] == 1


def _inserer_pronostic_direct(chemin_communaute, utilisateur_id, donnees):
    import sqlite3

    connexion = sqlite3.connect(chemin_communaute)
    connexion.execute(
        """
        INSERT INTO pronostics (
            utilisateur_id, championnat, saison, domicile, exterieur,
            type_pronostic, buts_domicile, buts_exterieur, resultat_1x2,
            commence_at, cree_le, verrouille
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            utilisateur_id,
            donnees["championnat"],
            donnees["saison"],
            donnees["domicile"],
            donnees["exterieur"],
            donnees["type_pronostic"],
            donnees.get("buts_domicile"),
            donnees.get("buts_exterieur"),
            donnees.get("resultat_1x2"),
            "2026-08-15T18:00:00Z",
            "2026-08-14T12:00:00Z",
        ),
    )
    connexion.commit()
    connexion.close()


def test_classement_pronos(client_communaute, fichier_communaute_temp, fichier_base_temp, monkeypatch):
    monkeypatch.setattr(communaute, "FICHIER_FOOTBALL", fichier_base_temp)
    _inscrire(client_communaute, email="a@exemple.fr", pseudo="Alice")
    alice_id = client_communaute.get("/api/communaute/moi").json()["utilisateur"]["id"]
    _inserer_pronostic_direct(
        fichier_communaute_temp,
        alice_id,
        {
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Sevilla",
            "type_pronostic": "score",
            "buts_domicile": 2,
            "buts_exterieur": 0,
        },
    )

    client_communaute.post("/api/communaute/deconnexion")
    _inscrire(client_communaute, email="b@exemple.fr", pseudo="Bob")
    bob_id = client_communaute.get("/api/communaute/moi").json()["utilisateur"]["id"]
    _inserer_pronostic_direct(
        fichier_communaute_temp,
        bob_id,
        {
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Real Madrid",
            "exterieur": "Valencia",
            "type_pronostic": "1x2",
            "resultat_1x2": "N",
        },
    )

    reponse = client_communaute.get(
        "/api/communaute/classement",
        params={"championnat": "La Liga", "saison": "2026-2027"},
    )
    assert reponse.status_code == 200
    data = reponse.json()
    assert data["championnat"] == "La Liga"
    assert "regle_points" in data
    assert "disclaimer" in data
    classement = data["classement"]
    assert len(classement) == 2
    assert classement[0]["pseudo"] == "Alice"
    assert classement[0]["points"] == 3
    assert classement[1]["points"] == 1


def test_profil_public(client_communaute, fichier_communaute_temp, fichier_base_temp, monkeypatch):
    monkeypatch.setattr(communaute, "FICHIER_FOOTBALL", fichier_base_temp)
    _inscrire(client_communaute, email="profil@exemple.fr", pseudo="ProfilTest")
    uid = client_communaute.get("/api/communaute/moi").json()["utilisateur"]["id"]
    _inserer_pronostic_direct(
        fichier_communaute_temp,
        uid,
        {
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Sevilla",
            "type_pronostic": "score",
            "buts_domicile": 2,
            "buts_exterieur": 0,
        },
    )

    reponse = client_communaute.get("/api/communaute/profil/ProfilTest")
    assert reponse.status_code == 200
    profil = reponse.json()["profil"]
    assert profil["pseudo"] == "ProfilTest"
    assert profil["points_total"] == 3
    assert profil["nb_pronos"] == 1


def test_classement_sans_connexion(client_communaute):
    reponse = client_communaute.get(
        "/api/communaute/classement",
        params={"championnat": "La Liga", "saison": "2026-2027"},
    )
    assert reponse.status_code == 200


def test_config_communaute(client_communaute):
    reponse = client_communaute.get("/api/communaute/config")
    assert reponse.status_code == 200
    data = reponse.json()
    assert data["oauth_google_actif"] is False
    assert "disclaimer" in data


def test_reaction_commentaire_toggle(client_communaute):
    _inscrire(client_communaute)
    publication = client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Athletic",
            "contenu": "Commentaire avec réactions",
        },
    )
    commentaire_id = publication.json()["commentaire"]["id"]

    ajout = client_communaute.post(
        f"/api/communaute/commentaires/{commentaire_id}/reactions"
    )
    assert ajout.status_code == 200
    assert ajout.json()["nb_reactions"] == 1
    assert ajout.json()["utilisateur_a_reagi"] is True

    retrait = client_communaute.post(
        f"/api/communaute/commentaires/{commentaire_id}/reactions"
    )
    assert retrait.status_code == 200
    assert retrait.json()["nb_reactions"] == 0
    assert retrait.json()["utilisateur_a_reagi"] is False


def test_reactions_dans_liste_commentaires(client_communaute):
    _inscrire(client_communaute, email="react@exemple.fr", pseudo="Reacteur")
    publication = client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Girona",
            "contenu": "Pour la liste",
        },
    )
    commentaire_id = publication.json()["commentaire"]["id"]
    client_communaute.post(f"/api/communaute/commentaires/{commentaire_id}/reactions")

    liste = client_communaute.get(
        "/api/communaute/commentaires",
        params={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Girona",
        },
    )
    assert liste.status_code == 200
    item = liste.json()["commentaires"][0]
    assert item["nb_reactions"] == 1
    assert item["utilisateur_a_reagi"] is True


def test_reaction_requiert_connexion(client_communaute):
    reponse = client_communaute.post("/api/communaute/commentaires/1/reactions")
    assert reponse.status_code == 401


def test_matchs_sans_prono(client_communaute, fichier_base_temp, monkeypatch):
    monkeypatch.setattr(communaute, "FICHIER_FOOTBALL", fichier_base_temp)
    _ajouter_match_futur(fichier_base_temp, "Barcelona", "Getafe", jours=2)
    _inscrire(client_communaute, email="sans@exemple.fr", pseudo="SansProno")

    reponse = client_communaute.get("/api/communaute/pronostics/sans-prono")
    assert reponse.status_code == 200
    data = reponse.json()
    assert data["nb"] >= 1
    assert any(
        m["domicile"] == "Barcelona" and m["exterieur"] == "Getafe"
        for m in data["matchs"]
    )


def test_connexion_google_non_configuree(client_communaute, monkeypatch):
    monkeypatch.setattr(communaute, "google_client_id", lambda: "")
    reponse = client_communaute.post(
        "/api/communaute/connexion/google",
        json={"id_token": "jeton-invalide"},
    )
    assert reponse.status_code == 503


def test_reponse_commentaire(client_communaute):
    _inscrire(client_communaute, email="parent@exemple.fr", pseudo="Parent")
    publication = client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Osasuna",
            "contenu": "Commentaire parent",
        },
    )
    parent_id = publication.json()["commentaire"]["id"]

    reponse = client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Osasuna",
            "contenu": "Réponse imbriquée",
            "commentaire_parent_id": parent_id,
        },
    )
    assert reponse.status_code == 200
    assert reponse.json()["commentaire"]["commentaire_parent_id"] == parent_id

    liste = client_communaute.get(
        "/api/communaute/commentaires",
        params={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Osasuna",
        },
    )
    assert liste.status_code == 200
    commentaires = liste.json()["commentaires"]
    assert len(commentaires) == 1
    assert len(commentaires[0]["reponses"]) == 1
    assert commentaires[0]["reponses"][0]["contenu"] == "Réponse imbriquée"


def test_reponse_a_reponse_refusee(client_communaute):
    _inscrire(client_communaute, email="niv@exemple.fr", pseudo="Niveaux")
    parent = client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Cadiz",
            "contenu": "Parent",
        },
    ).json()["commentaire"]["id"]
    enfant = client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Cadiz",
            "contenu": "Enfant",
            "commentaire_parent_id": parent,
        },
    ).json()["commentaire"]["id"]

    refuse = client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Cadiz",
            "contenu": "Petit-enfant",
            "commentaire_parent_id": enfant,
        },
    )
    assert refuse.status_code == 400


def test_reactions_types_pouce_et_coeur(client_communaute):
    _inscrire(client_communaute, email="emo@exemple.fr", pseudo="Emojis")
    publication = client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Betis",
            "contenu": "Réactions multiples",
        },
    )
    commentaire_id = publication.json()["commentaire"]["id"]

    pouce = client_communaute.post(
        f"/api/communaute/commentaires/{commentaire_id}/reactions",
        json={"type_reaction": "pouce"},
    )
    assert pouce.status_code == 200
    assert pouce.json()["reactions"]["pouce"] == 1

    coeur = client_communaute.post(
        f"/api/communaute/commentaires/{commentaire_id}/reactions",
        json={"type_reaction": "coeur"},
    )
    assert coeur.status_code == 200
    assert coeur.json()["reactions"]["coeur"] == 1
    assert coeur.json()["nb_reactions"] == 2
    assert set(coeur.json()["mes_reactions"]) == {"pouce", "coeur"}

    retrait = client_communaute.post(
        f"/api/communaute/commentaires/{commentaire_id}/reactions",
        json={"type_reaction": "pouce"},
    )
    assert retrait.json()["reactions"]["pouce"] == 0
    assert retrait.json()["nb_reactions"] == 1


def test_pronos_journee(client_communaute, fichier_base_temp, monkeypatch):
    monkeypatch.setattr(communaute, "FICHIER_FOOTBALL", fichier_base_temp)
    import sqlite3
    from datetime import date, timedelta

    jour = (date.today() + timedelta(days=20)).isoformat()
    connexion = sqlite3.connect(fichier_base_temp)
    connexion.execute(
        """
        INSERT INTO calendrier (date, heure, journee, championnat, saison, domicile, exterieur)
        VALUES (?, '20:00', '7', 'La Liga', '2026-2027', 'Barcelona', 'Valencia')
        """,
        (jour,),
    )
    connexion.execute(
        """
        INSERT INTO calendrier (date, heure, journee, championnat, saison, domicile, exterieur)
        VALUES (?, '18:00', '7', 'La Liga', '2026-2027', 'Sevilla', 'Getafe')
        """,
        (jour,),
    )
    connexion.commit()
    connexion.close()

    _inscrire(client_communaute, email="journee@exemple.fr", pseudo="Journee")

    liste_j = client_communaute.get(
        "/api/communaute/pronostics/journees",
        params={"championnat": "La Liga", "saison": "2026-2027"},
    )
    assert liste_j.status_code == 200
    assert "7" in liste_j.json()["journees"]

    detail = client_communaute.get(
        "/api/communaute/pronostics/journee",
        params={"championnat": "La Liga", "saison": "2026-2027", "journee": "7"},
    )
    assert detail.status_code == 200
    assert detail.json()["nb"] == 2
    assert "disclaimer" in detail.json()


def test_ligue_privee_creer_rejoindre_classement(
    client_communaute, fichier_communaute_temp, fichier_base_temp, monkeypatch
):
    monkeypatch.setattr(communaute, "FICHIER_FOOTBALL", fichier_base_temp)
    _inscrire(client_communaute, email="createur@exemple.fr", pseudo="Createur")
    creation = client_communaute.post(
        "/api/communaute/ligues",
        json={"nom": "Amis du foot"},
    )
    assert creation.status_code == 200
    code = creation.json()["ligue"]["code_invitation"]
    assert len(code) >= 6

    createur_id = client_communaute.get("/api/communaute/moi").json()["utilisateur"]["id"]
    _inserer_pronostic_direct(
        fichier_communaute_temp,
        createur_id,
        {
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Sevilla",
            "type_pronostic": "score",
            "buts_domicile": 2,
            "buts_exterieur": 0,
        },
    )

    client_communaute.post("/api/communaute/deconnexion")
    _inscrire(client_communaute, email="ami@exemple.fr", pseudo="Ami")
    rejoindre = client_communaute.post(
        "/api/communaute/ligues/rejoindre",
        json={"code_invitation": code},
    )
    assert rejoindre.status_code == 200
    assert rejoindre.json()["ligue"]["nb_membres"] == 2

    detail = client_communaute.get(f"/api/communaute/ligues/{code}")
    assert detail.status_code == 200
    assert len(detail.json()["membres"]) == 2

    classement = client_communaute.get(
        f"/api/communaute/ligues/{code}/classement",
        params={"championnat": "La Liga", "saison": "2026-2027"},
    )
    assert classement.status_code == 200
    assert classement.json()["classement"][0]["pseudo"] == "Createur"
    assert classement.json()["classement"][0]["points"] == 3


def test_ligue_requiert_connexion(client_communaute):
    reponse = client_communaute.post(
        "/api/communaute/ligues",
        json={"nom": "Sans session"},
    )
    assert reponse.status_code == 401


def test_mes_ligues_liste(client_communaute):
    _inscrire(client_communaute, email="liste@exemple.fr", pseudo="Listeur")
    client_communaute.post("/api/communaute/ligues", json={"nom": "Ma ligue"})
    liste = client_communaute.get("/api/communaute/ligues")
    assert liste.status_code == 200
    assert len(liste.json()["ligues"]) == 1
    assert liste.json()["ligues"][0]["nom"] == "Ma ligue"
    assert "lien_invitation" in liste.json()["ligues"][0]


def test_commentaire_spam_url_refuse(client_communaute):
    _inscrire(client_communaute, email="spam@exemple.fr", pseudo="Spammeur")
    reponse = client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Athletic",
            "contenu": "Regarde https://exemple.com c'est ouf",
        },
    )
    assert reponse.status_code == 400


def test_profil_enrichi_maj(client_communaute):
    _inscrire(client_communaute, email="bio@exemple.fr", pseudo="BioFan")
    maj = client_communaute.patch(
        "/api/communaute/moi/profil",
        json={"bio": "Fan du ballon rond", "equipe_favorite": "Barcelona"},
    )
    assert maj.status_code == 200
    assert maj.json()["utilisateur"]["bio"] == "Fan du ballon rond"
    assert maj.json()["utilisateur"]["equipe_favorite"] == "Barcelona"
    assert maj.json()["utilisateur"]["changements_pseudo_restants"] == 4

    profil = client_communaute.get("/api/communaute/profil/BioFan")
    assert profil.status_code == 200
    assert profil.json()["profil"]["bio"] == "Fan du ballon rond"
    assert profil.json()["profil"]["equipe_favorite"] == "Barcelona"
    assert "taux_exacts" in profil.json()["profil"]
    assert "historique_recent" in profil.json()["profil"]


def test_changement_pseudo_limite_quatre(client_communaute):
    _inscrire(client_communaute, email="pseudo@exemple.fr", pseudo="PseudoZero")
    moi = client_communaute.get("/api/communaute/moi")
    assert moi.status_code == 200
    assert moi.json()["utilisateur"]["changements_pseudo_restants"] == 4

    meme = client_communaute.patch(
        "/api/communaute/moi/profil",
        json={"pseudo": "PseudoZero"},
    )
    assert meme.status_code == 200
    assert meme.json()["utilisateur"]["changements_pseudo_restants"] == 4

    for i, nouveau in enumerate(
        ("PseudoUn", "PseudoDeux", "PseudoTrois", "PseudoQuatre"), start=1
    ):
        maj = client_communaute.patch(
            "/api/communaute/moi/profil",
            json={"pseudo": nouveau},
        )
        assert maj.status_code == 200
        assert maj.json()["utilisateur"]["pseudo"] == nouveau
        assert maj.json()["utilisateur"]["changements_pseudo_restants"] == 4 - i

    refuse = client_communaute.patch(
        "/api/communaute/moi/profil",
        json={"pseudo": "PseudoCinq"},
    )
    assert refuse.status_code == 400
    assert "limite" in refuse.json()["detail"].lower()

    profil = client_communaute.get("/api/communaute/profil/PseudoQuatre")
    assert profil.status_code == 200
    assert profil.json()["profil"]["pseudo"] == "PseudoQuatre"

    ancien = client_communaute.get("/api/communaute/profil/PseudoZero")
    assert ancien.status_code == 404


def test_changement_pseudo_unicite_et_validation(client_communaute):
    _inscrire(client_communaute, email="a@exemple.fr", pseudo="AlphaUser")
    client_communaute.post("/api/communaute/deconnexion")
    _inscrire(client_communaute, email="b@exemple.fr", pseudo="BetaUser")

    pris = client_communaute.patch(
        "/api/communaute/moi/profil",
        json={"pseudo": "alphauser"},
    )
    assert pris.status_code == 409

    invalide = client_communaute.patch(
        "/api/communaute/moi/profil",
        json={"pseudo": "ab"},
    )
    assert invalide.status_code in (400, 422)

    vide = client_communaute.patch(
        "/api/communaute/moi/profil",
        json={"pseudo": "   "},
    )
    assert vide.status_code in (400, 422)


def test_catalogue_avatars(client_communaute):
    reponse = client_communaute.get("/api/communaute/avatars")
    assert reponse.status_code == 200
    avatars = reponse.json()["avatars"]
    assert len(avatars) == 80
    assert avatars[0]["id"] == "joueur-foot-01"
    assert avatars[0]["libelle"]
    assert avatars[11]["id"] == "joueur-foot-12"
    assert avatars[12]["id"] == "avatar-legende-01"
    assert avatars[29]["id"] == "avatar-legende-18"
    assert avatars[30]["id"] == "avatar-legende-b-01"
    assert avatars[30]["libelle"] == "Légende foot 19"
    assert avatars[-1]["id"] == "avatar-legende-b-50"
    assert avatars[-1]["libelle"] == "Légende foot 68"


def test_profil_avatar_maj(client_communaute):
    _inscrire(client_communaute, email="avatar@exemple.fr", pseudo="AvatarFan")
    maj = client_communaute.patch(
        "/api/communaute/moi/profil",
        json={"avatar_id": "joueur-foot-01"},
    )
    assert maj.status_code == 200
    assert maj.json()["utilisateur"]["avatar_id"] == "joueur-foot-01"

    moi = client_communaute.get("/api/communaute/moi")
    assert moi.json()["utilisateur"]["avatar_id"] == "joueur-foot-01"

    profil = client_communaute.get("/api/communaute/profil/AvatarFan")
    assert profil.json()["profil"]["avatar_id"] == "joueur-foot-01"

    legacy = client_communaute.patch(
        "/api/communaute/moi/profil",
        json={"avatar_id": "ballon-vert"},
    )
    assert legacy.status_code == 200
    assert legacy.json()["utilisateur"]["avatar_id"] == "joueur-foot-03"

    invalide = client_communaute.patch(
        "/api/communaute/moi/profil",
        json={"avatar_id": "inconnu"},
    )
    assert invalide.status_code == 400

    reinit = client_communaute.patch(
        "/api/communaute/moi/profil",
        json={"avatar_id": ""},
    )
    assert reinit.status_code == 200
    assert reinit.json()["utilisateur"]["avatar_id"] == ""

    pack_b = client_communaute.patch(
        "/api/communaute/moi/profil",
        json={"avatar_id": "avatar-legende-b-25"},
    )
    assert pack_b.status_code == 200
    assert pack_b.json()["utilisateur"]["avatar_id"] == "avatar-legende-b-25"


def test_commentaire_inclut_avatar(client_communaute):
    _inscrire(client_communaute, email="comavatar@exemple.fr", pseudo="ComAvatar")
    client_communaute.patch(
        "/api/communaute/moi/profil",
        json={"avatar_id": "joueur-foot-12"},
    )
    reponse = client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Athletic",
            "contenu": "Commentaire avec avatar",
        },
    )
    assert reponse.status_code == 200
    commentaire = reponse.json()["commentaire"]
    assert commentaire["avatar_id"] == "joueur-foot-12"

    liste = client_communaute.get(
        "/api/communaute/commentaires",
        params={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Athletic",
        },
    )
    assert liste.json()["commentaires"][0]["avatar_id"] == "joueur-foot-12"


def test_notifications_reponse_commentaire(client_communaute):
    _inscrire(client_communaute, email="auteur@exemple.fr", pseudo="AuteurNotif")
    parent = client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Athletic",
            "contenu": "Mon commentaire initial",
        },
    ).json()["commentaire"]["id"]

    client_communaute.post("/api/communaute/deconnexion")
    _inscrire(client_communaute, email="repondeur@exemple.fr", pseudo="Repondeur")
    client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Athletic",
            "contenu": "Ma réponse",
            "commentaire_parent_id": parent,
        },
    )

    client_communaute.post("/api/communaute/deconnexion")
    client_communaute.post(
        "/api/communaute/connexion",
        json={"identifiant": "auteur@exemple.fr", "mot_de_passe": "motdepasse1"},
    )
    notifs = client_communaute.get("/api/communaute/notifications")
    assert notifs.status_code == 200
    assert notifs.json()["nb_non_lues"] >= 1
    types = {n["type_notification"] for n in notifs.json()["notifications"]}
    assert "reponse_commentaire" in types

    compte = client_communaute.get("/api/communaute/notifications/compte")
    assert compte.status_code == 200
    assert compte.json()["nb_non_lues"] >= 1

    tout = client_communaute.post("/api/communaute/notifications/lues")
    assert tout.status_code == 200
    compte2 = client_communaute.get("/api/communaute/notifications/compte")
    assert compte2.json()["nb_non_lues"] == 0


def test_admin_signalements(client_communaute, monkeypatch):
    monkeypatch.setattr(communaute, "email_admin_communaute", lambda: "admin@exemple.fr")
    _inscrire(
        client_communaute,
        email="admin@exemple.fr",
        pseudo="AdminMod",
    )
    publication = client_communaute.post(
        "/api/communaute/commentaires",
        json={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Athletic",
            "contenu": "Commentaire a signaler",
        },
    )
    commentaire_id = publication.json()["commentaire"]["id"]

    client_communaute.post("/api/communaute/deconnexion")
    _inscrire(client_communaute, email="sig@exemple.fr", pseudo="Signaleur")
    client_communaute.post(
        f"/api/communaute/commentaires/{commentaire_id}/signaler",
        json={"motif": "spam"},
    )

    client_communaute.post("/api/communaute/deconnexion")
    client_communaute.post(
        "/api/communaute/connexion",
        json={"identifiant": "admin@exemple.fr", "mot_de_passe": "motdepasse1"},
    )
    file_ = client_communaute.get("/api/communaute/admin/signalements")
    assert file_.status_code == 200
    assert len(file_.json()["signalements"]) >= 1
    sid = file_.json()["signalements"][0]["id"]

    traite = client_communaute.post(
        f"/api/communaute/admin/signalements/{sid}/traiter",
        json={"statut": "traite"},
    )
    assert traite.status_code == 200
    ouverts = client_communaute.get(
        "/api/communaute/admin/signalements",
        params={"statut": "ouvert"},
    )
    assert all(s["id"] != sid for s in ouverts.json()["signalements"])


def test_pronostics_lot(client_communaute, fichier_base_temp, monkeypatch):
    monkeypatch.setattr(communaute, "FICHIER_FOOTBALL", fichier_base_temp)
    import sqlite3
    from datetime import date, timedelta

    jour = (date.today() + timedelta(days=25)).isoformat()
    connexion = sqlite3.connect(fichier_base_temp)
    connexion.execute(
        """
        INSERT INTO calendrier (date, heure, journee, championnat, saison, domicile, exterieur)
        VALUES (?, '20:00', '9', 'La Liga', '2026-2027', 'Barcelona', 'Valencia')
        """,
        (jour,),
    )
    connexion.execute(
        """
        INSERT INTO calendrier (date, heure, journee, championnat, saison, domicile, exterieur)
        VALUES (?, '18:00', '9', 'La Liga', '2026-2027', 'Sevilla', 'Getafe')
        """,
        (jour,),
    )
    connexion.commit()
    connexion.close()

    _inscrire(client_communaute, email="lot@exemple.fr", pseudo="LotProno")
    lot = client_communaute.post(
        "/api/communaute/pronostics/lot",
        json={
            "pronostics": [
                {
                    "championnat": "La Liga",
                    "saison": "2026-2027",
                    "domicile": "Barcelona",
                    "exterieur": "Valencia",
                    "type_pronostic": "1x2",
                    "resultat_1x2": "1",
                },
                {
                    "championnat": "La Liga",
                    "saison": "2026-2027",
                    "domicile": "Sevilla",
                    "exterieur": "Getafe",
                    "type_pronostic": "score",
                    "buts_domicile": 2,
                    "buts_exterieur": 1,
                },
            ]
        },
    )
    assert lot.status_code == 200
    assert lot.json()["nb_ok"] == 2

    mes = client_communaute.get("/api/communaute/pronostics/mes-pronos")
    assert mes.status_code == 200
    assert "stats" in mes.json()
    assert "taux_exacts" in mes.json()["stats"]


def test_messages_ligue_et_classement_journee(
    client_communaute, fichier_communaute_temp, fichier_base_temp, monkeypatch
):
    monkeypatch.setattr(communaute, "FICHIER_FOOTBALL", fichier_base_temp)
    import sqlite3

    connexion = sqlite3.connect(fichier_base_temp)
    connexion.execute(
        """
        INSERT INTO calendrier (date, heure, journee, championnat, saison, domicile, exterieur)
        VALUES ('2026-08-20', '20:00', '3', 'La Liga', '2026-2027', 'Barcelona', 'Sevilla')
        """
    )
    connexion.commit()
    connexion.close()

    _inscrire(client_communaute, email="chat@exemple.fr", pseudo="Chatteur")
    creation = client_communaute.post(
        "/api/communaute/ligues",
        json={"nom": "Ligue chat"},
    )
    code = creation.json()["ligue"]["code_invitation"]

    msg = client_communaute.post(
        f"/api/communaute/ligues/{code}/messages",
        json={"contenu": "Bonjour la ligue"},
    )
    assert msg.status_code == 200

    liste = client_communaute.get(f"/api/communaute/ligues/{code}/messages")
    assert liste.status_code == 200
    assert len(liste.json()["messages"]) == 1

    msg_emoji = client_communaute.post(
        f"/api/communaute/ligues/{code}/messages",
        json={"contenu": "Allez ⚽🔥"},
    )
    assert msg_emoji.status_code == 200
    assert msg_emoji.json()["message"]["contenu"] == "Allez ⚽🔥"

    uid = client_communaute.get("/api/communaute/moi").json()["utilisateur"]["id"]
    _inserer_pronostic_direct(
        fichier_communaute_temp,
        uid,
        {
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Sevilla",
            "type_pronostic": "score",
            "buts_domicile": 2,
            "buts_exterieur": 0,
        },
    )

    classement = client_communaute.get(
        f"/api/communaute/ligues/{code}/classement",
        params={"championnat": "La Liga", "saison": "2026-2027", "journee": "3"},
    )
    assert classement.status_code == 200
    assert classement.json()["journee"] == "3"
    assert len(classement.json()["classement"]) >= 1


def test_cookie_secure_selon_env(monkeypatch):
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    monkeypatch.delenv("ENVIRONNEMENT", raising=False)
    assert communaute.cookie_secure_actif() is False

    monkeypatch.setenv("COOKIE_SECURE", "1")
    assert communaute.cookie_secure_actif() is True

    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.setenv("ENVIRONNEMENT", "production")
    assert communaute.cookie_secure_actif() is False

    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    monkeypatch.setenv("ENVIRONNEMENT", "production")
    assert communaute.cookie_secure_actif() is True


def test_cookie_session_flag_secure(client_communaute, monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "1")
    reponse = _inscrire(client_communaute, email="secure@exemple.fr", pseudo="SecureUser")
    assert reponse.status_code == 200
    set_cookie = reponse.headers.get("set-cookie", "")
    assert "session_communaute=" in set_cookie
    assert "Secure" in set_cookie


def test_cookie_session_sans_secure_en_dev(client_communaute, monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.delenv("ENVIRONNEMENT", raising=False)
    reponse = _inscrire(client_communaute, email="devcookie@exemple.fr", pseudo="DevCookie")
    assert reponse.status_code == 200
    set_cookie = reponse.headers.get("set-cookie", "")
    assert "session_communaute=" in set_cookie
    assert "Secure" not in set_cookie


def test_limite_connexion_par_ip(client_communaute, monkeypatch):
    monkeypatch.setattr(communaute, "LIMITE_CONNEXION", 3)
    _inscrire(client_communaute)
    client_communaute.post("/api/communaute/deconnexion")

    for _ in range(3):
        reponse = client_communaute.post(
            "/api/communaute/connexion",
            json={"identifiant": "Testeur", "mot_de_passe": "mauvaismdp"},
        )
        assert reponse.status_code == 401

    bloque = client_communaute.post(
        "/api/communaute/connexion",
        json={"identifiant": "Testeur", "mot_de_passe": "motdepasse1"},
    )
    assert bloque.status_code == 429
    assert "Trop de tentatives" in bloque.json()["detail"]


def test_limite_inscription_par_ip(client_communaute, monkeypatch):
    monkeypatch.setattr(communaute, "LIMITE_INSCRIPTION", 2)

    premiere = _inscrire(client_communaute, email="a1@exemple.fr", pseudo="UserA1")
    assert premiere.status_code == 200
    deuxieme = _inscrire(client_communaute, email="a2@exemple.fr", pseudo="UserA2")
    assert deuxieme.status_code == 200
    troisieme = _inscrire(client_communaute, email="a3@exemple.fr", pseudo="UserA3")
    assert troisieme.status_code == 429
    assert "inscription" in troisieme.json()["detail"].lower()


def test_sondage_match_1n2(client_communaute):
    _inscrire(client_communaute)
    params = {
        "championnat": "La Liga",
        "saison": "2026-2027",
        "domicile": "Real Madrid",
        "exterieur": "Barcelona",
    }
    lecture = client_communaute.get("/api/communaute/sondage-match", params=params)
    assert lecture.status_code == 200
    sondage = lecture.json()["sondage"]
    assert sondage["question"] == "Qui va gagner ?"
    assert [o["choix"] for o in sondage["options"]] == ["1", "N", "2"]
    assert sondage["a_vote"] is False

    vote = client_communaute.post(
        "/api/communaute/sondage-match",
        json={**params, "choix": "1"},
    )
    assert vote.status_code == 200
    apres = vote.json()["sondage"]
    assert apres["a_vote"] is True
    assert apres["mon_choix"] == "1"
    assert apres["nb_votes_total"] == 1
    assert apres["options"][0]["pourcentage"] == 100.0

    doublon = client_communaute.post(
        "/api/communaute/sondage-match",
        json={**params, "choix": "N"},
    )
    assert doublon.status_code == 409

    mauvais = client_communaute.post(
        "/api/communaute/sondage-match",
        json={**params, "choix": "X"},
    )
    assert mauvais.status_code in (400, 422)


def test_comparer_pronos_au_modele(tmp_path, monkeypatch):
    import sqlite3
    from pathlib import Path

    from historique_analyses import assurer_schema, enregistrer_prevision, ouvrir_base

    chemin_foot = tmp_path / "foot_test.db"
    connexion_foot = sqlite3.connect(chemin_foot)
    connexion_foot.execute(
        """
        CREATE TABLE matchs (
            date TEXT, saison TEXT, championnat TEXT,
            domicile TEXT, exterieur TEXT,
            buts_domicile INTEGER, buts_exterieur INTEGER
        )
        """
    )
    connexion_foot.execute(
        """
        INSERT INTO matchs VALUES
        ('2026-08-10', '2026-2027', 'La Liga', 'Barcelona', 'Sevilla', 2, 1)
        """
    )
    connexion_foot.commit()
    connexion_foot.close()

    chemin_analyses = tmp_path / "analyses_test.db"
    connexion_analyses = ouvrir_base(chemin_analyses)
    assurer_schema(connexion_analyses)
    enregistrer_prevision(
        connexion_analyses,
        championnat="La Liga",
        saison="2026-2027",
        date_match="2026-08-10",
        domicile="Barcelona",
        exterieur="Sevilla",
        prediction={
            "p_victoire_domicile": 60.0,
            "p_nul": 25.0,
            "p_victoire_exterieur": 15.0,
        },
    )
    connexion_analyses.close()

    monkeypatch.setattr(communaute, "FICHIER_FOOTBALL", chemin_foot)
    monkeypatch.setattr(
        communaute,
        "ouvrir_base_analyses",
        lambda chemin=None: ouvrir_base(chemin_analyses),
    )

    prono_correct = {
        "championnat": "La Liga",
        "saison": "2026-2027",
        "domicile": "Barcelona",
        "exterieur": "Sevilla",
        "type_pronostic": "1x2",
        "resultat_1x2": "1",
        "buts_domicile": None,
        "buts_exterieur": None,
        "commence_at": "2026-08-10T20:00:00",
    }
    prono_rate = {
        **prono_correct,
        "resultat_1x2": "2",
    }

    stats = communaute.comparer_pronos_au_modele([prono_correct, prono_rate])
    assert stats["nb_pronos"] == 2
    assert stats["nb_corrects_utilisateur"] == 1
    assert stats["nb_corrects_modele"] == 2
    assert stats["score_utilisateur"] == 50.0
    assert stats["score_modele"] == 100.0
