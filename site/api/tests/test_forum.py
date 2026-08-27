"""Tests MVP forum — sujets et messages par championnat."""

import sqlite3

import pytest

import communaute
import forum


@pytest.fixture
def fichier_communaute_temp(tmp_path, monkeypatch):
    chemin = tmp_path / "communaute_test.db"
    monkeypatch.setattr(communaute, "FICHIER_COMMUNAUTE", chemin)
    monkeypatch.setattr(communaute, "_initialise", False)
    monkeypatch.setattr(forum, "_tables_ok", False)
    with communaute._verrou_limite:
        communaute._historique_commentaires.clear()
        communaute._historique_pronostics.clear()
        communaute._historique_reactions.clear()
        communaute._historique_ligues.clear()
        communaute._historique_connexion_ip.clear()
        communaute._historique_connexion_identifiant.clear()
        communaute._historique_inscription_ip.clear()
    with forum._verrou_limite:
        forum._historique_forum.clear()
        forum._historique_reactions_forum.clear()
        forum._historique_sondages_forum.clear()
    communaute.initialiser_base()
    forum.assurer_tables_forum()
    return chemin


@pytest.fixture
def client_forum(fichier_base_temp, fichier_communaute_temp, monkeypatch):
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


def _inscrire(client, email="forum@exemple.fr", pseudo="Forumiste", mot_de_passe="motdepasse1"):
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


def _lire_message_en_base(chemin_db, message_id):
    connexion = sqlite3.connect(chemin_db)
    connexion.row_factory = sqlite3.Row
    try:
        return connexion.execute(
            """
            SELECT id, contenu, supprime, supprime_le
            FROM forums_messages WHERE id = ?
            """,
            (message_id,),
        ).fetchone()
    finally:
        connexion.close()


def _lire_sujet_en_base(chemin_db, sujet_id):
    connexion = sqlite3.connect(chemin_db)
    connexion.row_factory = sqlite3.Row
    try:
        return connexion.execute(
            """
            SELECT id, titre, supprime, supprime_le
            FROM forums_sujets WHERE id = ?
            """,
            (sujet_id,),
        ).fetchone()
    finally:
        connexion.close()


def test_liste_espaces_publique(client_forum):
    reponse = client_forum.get("/api/forum")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert "espaces" in corps
    assert any(e["championnat"] == "La Liga" for e in corps["espaces"])
    assert "18" in corps["disclaimer"]
    assert "paris" in corps["disclaimer"].lower()


def test_creer_sujet_et_lister(client_forum):
    _inscrire(client_forum)
    creation = client_forum.post(
        "/api/forum/La%20Liga/sujets",
        json={
            "titre": "Discussions journée",
            "contenu": "Qui vous impressionne cette semaine ?",
        },
    )
    assert creation.status_code == 200
    sujet = creation.json()["sujet"]
    assert sujet["titre"] == "Discussions journée"
    assert sujet["nb_messages"] == 1

    liste = client_forum.get("/api/forum/La%20Liga/sujets")
    assert liste.status_code == 200
    sujets = liste.json()["sujets"]
    assert len(sujets) == 1
    assert sujets[0]["id"] == sujet["id"]


def test_messages_chronologiques_et_lecture_publique(client_forum):
    _inscrire(client_forum)
    creation = client_forum.post(
        "/api/forum/La%20Liga/sujets",
        json={"titre": "Fil ouvert", "contenu": "Premier message"},
    )
    sujet_id = creation.json()["sujet"]["id"]

    reponse = client_forum.post(
        f"/api/forum/sujets/{sujet_id}/messages",
        json={"contenu": "Deuxième message"},
    )
    assert reponse.status_code == 200

    client_forum.post("/api/communaute/deconnexion")
    detail = client_forum.get(f"/api/forum/sujets/{sujet_id}")
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert [m["contenu"] for m in messages] == ["Premier message", "Deuxième message"]


def test_poster_sans_connexion_refuse(client_forum):
    reponse = client_forum.post(
        "/api/forum/La%20Liga/sujets",
        json={"titre": "Sans compte", "contenu": "Ne doit pas passer"},
    )
    assert reponse.status_code == 401


def test_reaction_et_signalement(client_forum):
    _inscrire(client_forum)
    creation = client_forum.post(
        "/api/forum/Bundesliga/sujets",
        json={"titre": "Bayern", "contenu": "Très solides"},
    )
    message_id = creation.json()["message"]["id"]

    reaction = client_forum.post(
        f"/api/forum/messages/{message_id}/reactions",
        json={"type_reaction": "pouce"},
    )
    assert reaction.status_code == 200
    assert reaction.json()["active"] is True
    assert reaction.json()["reactions"]["pouce"] == 1

    signalement = client_forum.post(
        f"/api/forum/messages/{message_id}/signaler",
        json={"motif": "hors sujet"},
    )
    assert signalement.status_code == 200
    assert signalement.json()["ok"] is True


def test_message_avec_emojis_unicode(client_forum):
    """Les emojis unicode sont acceptés et renvoyés tels quels (pas de strip)."""
    _inscrire(client_forum)
    contenu = "Quel match ⚽🔥👏 Bravo !"
    creation = client_forum.post(
        "/api/forum/Ligue%201/sujets",
        json={"titre": "Emojis ok", "contenu": contenu},
    )
    assert creation.status_code == 200
    assert creation.json()["message"]["contenu"] == contenu

    sujet_id = creation.json()["sujet"]["id"]
    reponse = client_forum.post(
        f"/api/forum/sujets/{sujet_id}/messages",
        json={"contenu": "❤️👍"},
    )
    assert reponse.status_code == 200
    assert reponse.json()["message"]["contenu"] == "❤️👍"

    detail = client_forum.get(f"/api/forum/sujets/{sujet_id}")
    assert detail.status_code == 200
    contenus = [m["contenu"] for m in detail.json()["messages"]]
    assert contenu in contenus
    assert "❤️👍" in contenus


def test_championnat_invalide(client_forum):
    _inscrire(client_forum)
    reponse = client_forum.get("/api/forum/Coupe%20du%20monde/sujets")
    assert reponse.status_code == 400


def test_modifier_titre_et_message_auteur(client_forum):
    _inscrire(client_forum)
    creation = client_forum.post(
        "/api/forum/La%20Liga/sujets",
        json={"titre": "Titre initial", "contenu": "Contenu initial"},
    )
    assert creation.status_code == 200
    sujet_id = creation.json()["sujet"]["id"]
    message_id = creation.json()["message"]["id"]

    titre = client_forum.patch(
        f"/api/forum/sujets/{sujet_id}",
        json={"titre": "Titre modifié"},
    )
    assert titre.status_code == 200
    sujet = titre.json()["sujet"]
    assert sujet["titre"] == "Titre modifié"
    assert sujet["modifie"] is True
    assert sujet["date_modification"]

    message = client_forum.patch(
        f"/api/forum/messages/{message_id}",
        json={"contenu": "Contenu modifié"},
    )
    assert message.status_code == 200
    corps = message.json()["message"]
    assert corps["contenu"] == "Contenu modifié"
    assert corps["modifie"] is True
    assert corps["date_modification"]

    detail = client_forum.get(f"/api/forum/sujets/{sujet_id}")
    assert detail.status_code == 200
    assert detail.json()["sujet"]["titre"] == "Titre modifié"
    assert detail.json()["messages"][0]["contenu"] == "Contenu modifié"
    assert detail.json()["messages"][0]["modifie"] is True


def test_modifier_refuse_si_pas_auteur(client_forum):
    _inscrire(client_forum, email="auteur@exemple.fr", pseudo="AuteurForum")
    creation = client_forum.post(
        "/api/forum/Serie%20A/sujets",
        json={"titre": "Privé", "contenu": "Message auteur"},
    )
    sujet_id = creation.json()["sujet"]["id"]
    message_id = creation.json()["message"]["id"]
    client_forum.post("/api/communaute/deconnexion")

    _inscrire(client_forum, email="autre@exemple.fr", pseudo="AutreForum")
    refus_titre = client_forum.patch(
        f"/api/forum/sujets/{sujet_id}",
        json={"titre": "Hack"},
    )
    assert refus_titre.status_code == 403

    refus_msg = client_forum.patch(
        f"/api/forum/messages/{message_id}",
        json={"contenu": "Hack"},
    )
    assert refus_msg.status_code == 403


def test_admin_peut_modifier_sujet_et_message(client_forum, monkeypatch):
    monkeypatch.setattr(communaute, "email_admin_communaute", lambda: "admin@exemple.fr")
    _inscrire(client_forum, email="auteur2@exemple.fr", pseudo="Auteur2")
    creation = client_forum.post(
        "/api/forum/Bundesliga/sujets",
        json={"titre": "Avant admin", "contenu": "Texte avant"},
    )
    sujet_id = creation.json()["sujet"]["id"]
    message_id = creation.json()["message"]["id"]
    client_forum.post("/api/communaute/deconnexion")

    _inscrire(client_forum, email="admin@exemple.fr", pseudo="AdminForum")
    titre = client_forum.patch(
        f"/api/forum/sujets/{sujet_id}",
        json={"titre": "Corrigé par admin"},
    )
    assert titre.status_code == 200
    assert titre.json()["sujet"]["titre"] == "Corrigé par admin"

    message = client_forum.patch(
        f"/api/forum/messages/{message_id}",
        json={"contenu": "Corrigé par admin"},
    )
    assert message.status_code == 200
    assert message.json()["message"]["contenu"] == "Corrigé par admin"


def test_modifier_validation_longueur(client_forum):
    _inscrire(client_forum)
    creation = client_forum.post(
        "/api/forum/La%20Liga/sujets",
        json={"titre": "Court", "contenu": "Ok"},
    )
    sujet_id = creation.json()["sujet"]["id"]
    message_id = creation.json()["message"]["id"]

    titre_vide = client_forum.patch(
        f"/api/forum/sujets/{sujet_id}",
        json={"titre": "   "},
    )
    assert titre_vide.status_code == 400

    message_long = client_forum.patch(
        f"/api/forum/messages/{message_id}",
        json={"contenu": "x" * 1001},
    )
    assert message_long.status_code == 422


def test_supprimer_message_auteur(client_forum, fichier_communaute_temp):
    _inscrire(client_forum)
    creation = client_forum.post(
        "/api/forum/La%20Liga/sujets",
        json={"titre": "Fil", "contenu": "Premier"},
    )
    sujet_id = creation.json()["sujet"]["id"]
    client_forum.post(
        f"/api/forum/sujets/{sujet_id}/messages",
        json={"contenu": "Deuxième"},
    )
    detail = client_forum.get(f"/api/forum/sujets/{sujet_id}")
    message_id = detail.json()["messages"][1]["id"]

    suppression = client_forum.delete(f"/api/forum/messages/{message_id}")
    assert suppression.status_code == 200
    corps = suppression.json()
    assert corps["ok"] is True
    assert corps["sujet_supprime"] is False

    detail = client_forum.get(f"/api/forum/sujets/{sujet_id}")
    assert detail.status_code == 200
    contenus = [m["contenu"] for m in detail.json()["messages"]]
    assert contenus == ["Premier"]
    assert detail.json()["sujet"]["nb_messages"] == 1

    ligne = _lire_message_en_base(fichier_communaute_temp, message_id)
    assert ligne is not None
    assert ligne["contenu"] == "Deuxième"
    assert ligne["supprime"] == 1
    assert ligne["supprime_le"]


def test_supprimer_dernier_message_supprime_sujet(client_forum, fichier_communaute_temp):
    _inscrire(client_forum)
    creation = client_forum.post(
        "/api/forum/Serie%20A/sujets",
        json={"titre": "Seul", "contenu": "Unique"},
    )
    sujet_id = creation.json()["sujet"]["id"]
    message_id = creation.json()["message"]["id"]
    champ = creation.json()["sujet"]["championnat"]

    suppression = client_forum.delete(f"/api/forum/messages/{message_id}")
    assert suppression.status_code == 200
    assert suppression.json()["sujet_supprime"] is True

    detail = client_forum.get(f"/api/forum/sujets/{sujet_id}")
    assert detail.status_code == 404

    liste = client_forum.get(f"/api/forum/{champ.replace(' ', '%20')}/sujets")
    assert all(s["id"] != sujet_id for s in liste.json()["sujets"])

    msg_ligne = _lire_message_en_base(fichier_communaute_temp, message_id)
    assert msg_ligne["contenu"] == "Unique"
    assert msg_ligne["supprime"] == 1
    assert msg_ligne["supprime_le"]

    sujet_ligne = _lire_sujet_en_base(fichier_communaute_temp, sujet_id)
    assert sujet_ligne["titre"] == "Seul"
    assert sujet_ligne["supprime"] == 1
    assert sujet_ligne["supprime_le"]


def test_supprimer_message_refuse_si_pas_auteur(client_forum):
    _inscrire(client_forum, email="auteur-del@exemple.fr", pseudo="AuteurDel")
    creation = client_forum.post(
        "/api/forum/Bundesliga/sujets",
        json={"titre": "Privé del", "contenu": "Ne pas toucher"},
    )
    message_id = creation.json()["message"]["id"]
    client_forum.post("/api/communaute/deconnexion")

    _inscrire(client_forum, email="autre-del@exemple.fr", pseudo="AutreDel")
    refus = client_forum.delete(f"/api/forum/messages/{message_id}")
    assert refus.status_code == 403


def test_admin_peut_supprimer_message(client_forum, monkeypatch):
    monkeypatch.setattr(communaute, "email_admin_communaute", lambda: "admin-del@exemple.fr")
    _inscrire(client_forum, email="auteur3@exemple.fr", pseudo="Auteur3")
    creation = client_forum.post(
        "/api/forum/Premier%20League/sujets",
        json={"titre": "Admin del", "contenu": "À retirer"},
    )
    sujet_id = creation.json()["sujet"]["id"]
    client_forum.post(
        f"/api/forum/sujets/{sujet_id}/messages",
        json={"contenu": "Second"},
    )
    detail = client_forum.get(f"/api/forum/sujets/{sujet_id}")
    message_id = detail.json()["messages"][1]["id"]
    client_forum.post("/api/communaute/deconnexion")

    _inscrire(client_forum, email="admin-del@exemple.fr", pseudo="AdminDel")
    suppression = client_forum.delete(f"/api/forum/messages/{message_id}")
    assert suppression.status_code == 200
    assert suppression.json()["sujet_supprime"] is False


def test_supprimer_sujet_auteur(client_forum, fichier_communaute_temp):
    _inscrire(client_forum)
    creation = client_forum.post(
        "/api/forum/La%20Liga/sujets",
        json={"titre": "À effacer", "contenu": "Contenu"},
    )
    sujet_id = creation.json()["sujet"]["id"]
    message_id = creation.json()["message"]["id"]

    suppression = client_forum.delete(f"/api/forum/sujets/{sujet_id}")
    assert suppression.status_code == 200
    assert suppression.json()["sujet_supprime"] is True

    detail = client_forum.get(f"/api/forum/sujets/{sujet_id}")
    assert detail.status_code == 404

    sujet_ligne = _lire_sujet_en_base(fichier_communaute_temp, sujet_id)
    assert sujet_ligne["titre"] == "À effacer"
    assert sujet_ligne["supprime"] == 1
    assert sujet_ligne["supprime_le"]

    msg_ligne = _lire_message_en_base(fichier_communaute_temp, message_id)
    assert msg_ligne["contenu"] == "Contenu"
    assert msg_ligne["supprime"] == 1
    assert msg_ligne["supprime_le"]


def test_creer_sondage_et_voter(client_forum):
    _inscrire(client_forum)
    creation = client_forum.post(
        "/api/forum/La%20Liga/sujets",
        json={"titre": "Sondage journée", "contenu": "Votez !"},
    )
    sujet_id = creation.json()["sujet"]["id"]

    sondage = client_forum.post(
        f"/api/forum/sujets/{sujet_id}/sondage",
        json={
            "question": "Qui gagne le derby ?",
            "options": ["Domicile", "Nul", "Extérieur"],
        },
    )
    assert sondage.status_code == 200
    corps = sondage.json()["sondage"]
    assert corps["question"] == "Qui gagne le derby ?"
    assert len(corps["options"]) == 3
    assert corps["a_vote"] is False
    assert "nb_votes" not in corps["options"][0]

    option_id = corps["options"][0]["id"]
    vote = client_forum.post(
        f"/api/forum/sondages/{corps['id']}/votes",
        json={"option_id": option_id},
    )
    assert vote.status_code == 200
    apres = vote.json()["sondage"]
    assert apres["a_vote"] is True
    assert apres["mon_option_id"] == option_id
    assert apres["nb_votes_total"] == 1
    assert apres["options"][0]["nb_votes"] == 1
    assert apres["options"][0]["pourcentage"] == 100.0

    doublon = client_forum.post(
        f"/api/forum/sondages/{corps['id']}/votes",
        json={"option_id": corps["options"][1]["id"]},
    )
    assert doublon.status_code == 409

    detail = client_forum.get(f"/api/forum/sujets/{sujet_id}")
    assert detail.json()["sondage"]["id"] == corps["id"]


def test_un_seul_sondage_par_sujet(client_forum):
    _inscrire(client_forum)
    creation = client_forum.post(
        "/api/forum/Bundesliga/sujets",
        json={"titre": "Un sondage", "contenu": "Ok"},
    )
    sujet_id = creation.json()["sujet"]["id"]
    ok = client_forum.post(
        f"/api/forum/sujets/{sujet_id}/sondage",
        json={"question": "A ou B ?", "options": ["A", "B"]},
    )
    assert ok.status_code == 200
    refus = client_forum.post(
        f"/api/forum/sujets/{sujet_id}/sondage",
        json={"question": "Autre ?", "options": ["Oui", "Non"]},
    )
    assert refus.status_code == 409


def test_sondage_validation_options(client_forum):
    _inscrire(client_forum)
    creation = client_forum.post(
        "/api/forum/Serie%20A/sujets",
        json={"titre": "Valid", "contenu": "Msg"},
    )
    sujet_id = creation.json()["sujet"]["id"]
    trop_peu = client_forum.post(
        f"/api/forum/sujets/{sujet_id}/sondage",
        json={"question": "Seule option ?", "options": ["Unique"]},
    )
    assert trop_peu.status_code in (400, 422)


def test_supprimer_sondage_auteur(client_forum):
    _inscrire(client_forum)
    creation = client_forum.post(
        "/api/forum/Ligue%201/sujets",
        json={"titre": "Sondage à retirer", "contenu": "Msg"},
    )
    sujet_id = creation.json()["sujet"]["id"]
    sondage = client_forum.post(
        f"/api/forum/sujets/{sujet_id}/sondage",
        json={"question": "On garde ?", "options": ["Oui", "Non"]},
    ).json()["sondage"]
    suppression = client_forum.delete(f"/api/forum/sondages/{sondage['id']}")
    assert suppression.status_code == 200
    detail = client_forum.get(f"/api/forum/sujets/{sujet_id}")
    assert detail.json()["sondage"] is None


def test_repondre_a_message_parent(client_forum):
    """Créer un message avec message_parent_id du même sujet."""
    _inscrire(client_forum)
    creation = client_forum.post(
        "/api/forum/La%20Liga/sujets",
        json={"titre": "Réponses", "contenu": "Message d'origine pour citation"},
    )
    assert creation.status_code == 200
    sujet_id = creation.json()["sujet"]["id"]
    parent_id = creation.json()["message"]["id"]

    reponse = client_forum.post(
        f"/api/forum/sujets/{sujet_id}/messages",
        json={
            "contenu": "Je réponds à ce message",
            "message_parent_id": parent_id,
        },
    )
    assert reponse.status_code == 200
    message = reponse.json()["message"]
    assert message["message_parent_id"] == parent_id
    assert message["message_parent"]["id"] == parent_id
    assert message["message_parent"]["auteur_pseudo"] == "Forumiste"
    assert "origine" in message["message_parent"]["extrait"].lower() or (
        "Message d'origine" in message["message_parent"]["extrait"]
    )

    detail = client_forum.get(f"/api/forum/sujets/{sujet_id}")
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    cite = next(m for m in messages if m["id"] == message["id"])
    assert cite["message_parent_id"] == parent_id
    assert cite["message_parent"]["extrait"]


def test_parent_autre_sujet_refuse(client_forum):
    _inscrire(client_forum)
    sujet_a = client_forum.post(
        "/api/forum/La%20Liga/sujets",
        json={"titre": "Sujet A", "contenu": "Parent A"},
    ).json()
    sujet_b = client_forum.post(
        "/api/forum/La%20Liga/sujets",
        json={"titre": "Sujet B", "contenu": "Parent B"},
    ).json()
    refus = client_forum.post(
        f"/api/forum/sujets/{sujet_b['sujet']['id']}/messages",
        json={
            "contenu": "Réponse croisée",
            "message_parent_id": sujet_a["message"]["id"],
        },
    )
    assert refus.status_code == 400


def test_reaction_emoji_elargie(client_forum):
    """Réactions ballon / feu / rire acceptées en plus de pouce et cœur."""
    _inscrire(client_forum)
    creation = client_forum.post(
        "/api/forum/Premier%20League/sujets",
        json={"titre": "Emojis", "contenu": "Réagissez"},
    )
    message_id = creation.json()["message"]["id"]
    for type_r in ("ballon", "feu", "rire", "applaudir"):
        reaction = client_forum.post(
            f"/api/forum/messages/{message_id}/reactions",
            json={"type_reaction": type_r},
        )
        assert reaction.status_code == 200, type_r
        assert reaction.json()["active"] is True
        assert reaction.json()["reactions"][type_r] == 1

    detail = client_forum.get(f"/api/forum/sujets/{creation.json()['sujet']['id']}")
    types = detail.json()["types_reaction"]
    assert "ballon" in types
    assert "feu" in types
    assert "pouce" in types
