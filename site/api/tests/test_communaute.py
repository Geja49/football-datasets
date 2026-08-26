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
        communaute._historique_reactions.clear()
        communaute._historique_ligues.clear()
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

    moi = client_communaute.get("/api/communaute/moi")
    assert moi.status_code == 200
    assert moi.json()["utilisateur"]["pseudo"] == "Testeur"


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
