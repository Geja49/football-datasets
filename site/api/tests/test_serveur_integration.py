"""Tests d'intégration FastAPI (DB temporaire, sans Odds API)."""


def test_accueil(client_api):
    reponse = client_api.get("/api/accueil")
    assert reponse.status_code == 200
    data = reponse.json()
    assert "championnats" in data
    assert "saisons" in data
    assert "2026-2027" in data["saisons"]
    assert len(data["championnats"]) >= 5
    assert "buteurs" in data
    assert "passeurs" in data
    assert len(data["buteurs"]) >= 1
    assert len(data["passeurs"]) >= 1
    la_liga_buteurs = next(l for l in data["buteurs"] if l["championnat"] == "La Liga")
    assert la_liga_buteurs["saison"] == "2026-2027"
    assert len(la_liga_buteurs["joueurs"]) >= 1
    assert la_liga_buteurs["joueurs"][0]["joueur"] == "Lewandowski"
    la_liga_passeurs = next(l for l in data["passeurs"] if l["championnat"] == "La Liga")
    assert la_liga_passeurs["saison"] == "2026-2027"
    assert len(la_liga_passeurs["joueurs"]) >= 1
    assert la_liga_passeurs["joueurs"][0]["joueur"] == "Yamal"
    assert la_liga_passeurs["joueurs"][0]["passes_decisives"] == 2


def test_classement_la_liga(client_api):
    reponse = client_api.get(
        "/api/classement",
        params={"championnat": "La Liga", "saison": "2026-2027"},
    )
    assert reponse.status_code == 200
    data = reponse.json()
    assert "classement" in data
    assert data["format"] == "ligue"
    assert isinstance(data["classement"], list)
    assert len(data["classement"]) >= 2
    premiere = data["classement"][0]
    for cle in ("rang", "equipe", "pts", "j", "v", "n", "d"):
        assert cle in premiere


def test_calendrier(client_api):
    reponse = client_api.get(
        "/api/calendrier",
        params={"championnat": "La Liga", "saison": "2026-2027"},
    )
    assert reponse.status_code == 200
    data = reponse.json()
    assert "programme" in data
    assert data["saison"] == "2026-2027"
    assert any(
        m["domicile"] == "Barcelona" and m["exterieur"] == "Real Madrid"
        for m in data["programme"]
    )


def test_equipes_analyse(client_api):
    reponse = client_api.get(
        "/api/equipes-analyse",
        params={"championnat": "La Liga", "saison": "2026-2027"},
    )
    assert reponse.status_code == 200
    data = reponse.json()
    noms = {e["equipe"] for e in data["equipes"]}
    assert "Barcelona" in noms
    assert "Real Madrid" in noms


def test_analyse_rencontre(client_api):
    reponse = client_api.get(
        "/api/analyse-rencontre",
        params={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Real Madrid",
        },
    )
    assert reponse.status_code == 200
    data = reponse.json()
    assert data["saison_demandee"] == "2026-2027"
    assert "prediction" in data
    pred = data["prediction"]
    assert "score_plus_probable" in pred
    assert "scores_frequents" in pred
    assert "p_victoire_domicile" in pred
    # Sans clé API : pas de cotes inventées.
    assert data.get("lecture_marche") is None
    assert "domicile" in data and "exterieur" in data
    assert data["domicile"]["nom"] == "Barcelona"


def test_analyse_rencontre_equipes_identiques(client_api):
    reponse = client_api.get(
        "/api/analyse-rencontre",
        params={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "domicile": "Barcelona",
            "exterieur": "Barcelona",
        },
    )
    assert reponse.status_code == 400


def test_championnat_inconnu(client_api):
    reponse = client_api.get(
        "/api/classement",
        params={"championnat": "Ligue inventée", "saison": "2026-2027"},
    )
    assert reponse.status_code == 400


def test_cotes_sans_cle(client_api):
    reponse = client_api.get("/api/cotes")
    assert reponse.status_code == 200
    data = reponse.json()
    assert data["cle_configuree"] is False
    assert "message" in data
    assert "competitions" in data
    assert isinstance(data["matchs"], list)
    for match in data["matchs"]:
        assert match.get("cotes") is None
        assert match.get("bookmakers") == []


def test_meilleurs_buteurs_saison_courante(client_api):
    reponse = client_api.get(
        "/api/meilleurs",
        params={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "type": "buts",
        },
    )
    assert reponse.status_code == 200
    data = reponse.json()
    assert data["disponible"] is True
    assert data["saison_de_secours"] is False
    assert data["saison_utilisee"] == "2026-2027"
    assert len(data["joueurs"]) >= 1
    assert data["joueurs"][0]["joueur"] == "Lewandowski"
    assert "url_photo" in data["joueurs"][0]
    assert isinstance(data["joueurs"][0]["url_photo"], str)


def test_meilleurs_passeurs_saison_courante(client_api):
    reponse = client_api.get(
        "/api/meilleurs",
        params={
            "championnat": "La Liga",
            "saison": "2026-2027",
            "type": "passes",
        },
    )
    assert reponse.status_code == 200
    data = reponse.json()
    assert data["disponible"] is True
    assert data["saison_utilisee"] == "2026-2027"
    assert len(data["joueurs"]) >= 1
    assert data["joueurs"][0]["joueur"] == "Yamal"
    assert data["joueurs"][0]["passes_decisives"] == 2


def test_meilleurs_fallback_saison_si_vide(client_api):
    """Saison sans joueurs → dernière saison non vide + message clair."""
    reponse = client_api.get(
        "/api/meilleurs",
        params={
            "championnat": "Bundesliga",
            "saison": "2026-2027",
            "type": "buts",
        },
    )
    assert reponse.status_code == 200
    data = reponse.json()
    assert data["saison"] == "2026-2027"
    assert data["saison_de_secours"] is True
    assert data["saison_utilisee"] == "2025-2026"
    assert "Aucun buteur" in data["message"]
    assert data["joueurs"][0]["joueur"] == "Kane"
