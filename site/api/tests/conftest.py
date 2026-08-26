"""Fixtures partagées : chemin API + base SQLite minimale."""

from pathlib import Path
import sqlite3
import sys

import pytest

DOSSIER_API = Path(__file__).resolve().parents[1]
if str(DOSSIER_API) not in sys.path:
    sys.path.insert(0, str(DOSSIER_API))


SCHEMA_MATCHS = """
CREATE TABLE matchs (
    championnat TEXT,
    saison TEXT,
    date TEXT,
    domicile TEXT,
    exterieur TEXT,
    buts_domicile INTEGER,
    buts_exterieur INTEGER,
    resultat TEXT,
    phase TEXT,
    tirs_domicile INTEGER,
    tirs_exterieur INTEGER,
    tirs_cadres_domicile INTEGER,
    tirs_cadres_exterieur INTEGER,
    jaunes_domicile INTEGER,
    jaunes_exterieur INTEGER,
    rouges_domicile INTEGER,
    rouges_exterieur INTEGER
)
"""

SCHEMA_MATCHS_XG = """
CREATE TABLE matchs_xg (
    championnat TEXT,
    saison TEXT,
    date TEXT,
    domicile TEXT,
    exterieur TEXT,
    xg_domicile REAL,
    xg_exterieur REAL
)
"""

SCHEMA_CALENDRIER = """
CREATE TABLE calendrier (
    date TEXT,
    heure TEXT,
    journee TEXT,
    championnat TEXT,
    saison TEXT,
    domicile TEXT,
    exterieur TEXT
)
"""

SCHEMA_JOUEURS = """
CREATE TABLE joueurs (
    joueur TEXT,
    equipe TEXT,
    championnat TEXT,
    saison TEXT,
    poste TEXT,
    matchs INTEGER,
    minutes INTEGER,
    buts INTEGER,
    passes_decisives INTEGER,
    tirs INTEGER,
    passes_cles INTEGER,
    xg REAL,
    xa REAL,
    xg_chaine REAL,
    xg_construction REAL,
    carton_jaune INTEGER,
    carton_rouge INTEGER
)
"""

SCHEMA_SITES = """
CREATE TABLE sites_equipes (
    equipe TEXT,
    nom_officiel TEXT,
    url_site TEXT,
    url_logo TEXT,
    stade TEXT
)
"""


def _remplir_base(connexion):
    """2–3 matchs La Liga 2026-2027 + un peu d'historique pour les moyennes."""
    historique = [
        (
            "La Liga",
            "2025-2026",
            "2025-09-01",
            "Barcelona",
            "Real Madrid",
            2,
            1,
            "H",
            12,
            10,
            5,
            4,
            2,
            3,
            0,
            0,
            1.8,
            1.2,
        ),
        (
            "La Liga",
            "2025-2026",
            "2025-09-08",
            "Real Madrid",
            "Barcelona",
            1,
            1,
            "D",
            11,
            11,
            4,
            5,
            2,
            2,
            0,
            0,
            1.4,
            1.5,
        ),
        (
            "La Liga",
            "2025-2026",
            "2025-09-15",
            "Barcelona",
            "Sevilla",
            3,
            0,
            "H",
            14,
            8,
            6,
            2,
            1,
            2,
            0,
            0,
            2.1,
            0.6,
        ),
        (
            "La Liga",
            "2025-2026",
            "2025-09-22",
            "Sevilla",
            "Real Madrid",
            0,
            2,
            "A",
            9,
            13,
            3,
            5,
            3,
            1,
            0,
            0,
            0.7,
            1.9,
        ),
        (
            "La Liga",
            "2025-2026",
            "2025-09-29",
            "Barcelona",
            "Valencia",
            2,
            0,
            "H",
            13,
            7,
            5,
            2,
            1,
            2,
            0,
            0,
            1.7,
            0.5,
        ),
        (
            "La Liga",
            "2025-2026",
            "2025-10-06",
            "Valencia",
            "Real Madrid",
            1,
            3,
            "A",
            8,
            14,
            2,
            6,
            2,
            1,
            0,
            0,
            0.9,
            2.0,
        ),
        (
            "La Liga",
            "2025-2026",
            "2025-10-13",
            "Sevilla",
            "Barcelona",
            1,
            2,
            "A",
            10,
            12,
            3,
            5,
            2,
            2,
            0,
            0,
            1.1,
            1.6,
        ),
        (
            "La Liga",
            "2025-2026",
            "2025-10-20",
            "Real Madrid",
            "Sevilla",
            2,
            1,
            "H",
            12,
            9,
            5,
            3,
            1,
            3,
            0,
            0,
            1.9,
            0.8,
        ),
        (
            "La Liga",
            "2025-2026",
            "2025-10-27",
            "Valencia",
            "Barcelona",
            0,
            1,
            "A",
            7,
            11,
            2,
            4,
            2,
            1,
            0,
            0,
            0.6,
            1.3,
        ),
        (
            "La Liga",
            "2025-2026",
            "2025-11-03",
            "Real Madrid",
            "Valencia",
            3,
            1,
            "H",
            15,
            6,
            7,
            2,
            1,
            2,
            0,
            0,
            2.2,
            0.7,
        ),
    ]
    for (
        champ,
        saison,
        date_m,
        dom,
        ext,
        bd,
        be,
        res,
        td,
        te,
        tcd,
        tce,
        jd,
        je,
        rd,
        re,
        xgd,
        xge,
    ) in historique:
        connexion.execute(
            """
            INSERT INTO matchs (
                championnat, saison, date, domicile, exterieur,
                buts_domicile, buts_exterieur, resultat, phase,
                tirs_domicile, tirs_exterieur,
                tirs_cadres_domicile, tirs_cadres_exterieur,
                jaunes_domicile, jaunes_exterieur,
                rouges_domicile, rouges_exterieur
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (champ, saison, date_m, dom, ext, bd, be, res, td, te, tcd, tce, jd, je, rd, re),
        )
        connexion.execute(
            """
            INSERT INTO matchs_xg (
                championnat, saison, date, domicile, exterieur,
                xg_domicile, xg_exterieur
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (champ, saison, date_m, dom, ext, xgd, xge),
        )

    # Saison courante 2026-2027 : 2 matchs joués + 1 à venir.
    connexion.execute(
        """
        INSERT INTO matchs (
            championnat, saison, date, domicile, exterieur,
            buts_domicile, buts_exterieur, resultat, phase,
            tirs_domicile, tirs_exterieur,
            tirs_cadres_domicile, tirs_cadres_exterieur,
            jaunes_domicile, jaunes_exterieur,
            rouges_domicile, rouges_exterieur
        ) VALUES
        ('La Liga', '2026-2027', '2026-08-15', 'Barcelona', 'Sevilla',
         2, 0, 'H', NULL, 13, 8, 5, 2, 1, 2, 0, 0),
        ('La Liga', '2026-2027', '2026-08-16', 'Real Madrid', 'Valencia',
         1, 1, 'D', NULL, 11, 9, 4, 3, 2, 2, 0, 0)
        """
    )
    connexion.execute(
        """
        INSERT INTO calendrier (date, heure, journee, championnat, saison, domicile, exterieur)
        VALUES
        ('2026-08-22', '21:00', '3', 'La Liga', '2026-2027', 'Barcelona', 'Real Madrid'),
        ('2026-08-23', '18:00', '3', 'La Liga', '2026-2027', 'Sevilla', 'Valencia')
        """
    )
    connexion.execute(
        """
        INSERT INTO sites_equipes (equipe, nom_officiel, url_site, url_logo, stade)
        VALUES
        ('Barcelona', 'FC Barcelona', 'https://www.fcbarcelona.com', '', 'Camp Nou'),
        ('Real Madrid', 'Real Madrid CF', 'https://www.realmadrid.com', '', 'Bernabeu')
        """
    )
    # Joueurs : saison précédente Bundesliga (pour tester le fallback 2026-2027 vide).
    connexion.execute(
        """
        INSERT INTO joueurs (
            joueur, equipe, championnat, saison, poste,
            matchs, minutes, buts, passes_decisives, tirs, xg, xa
        ) VALUES
        ('Kane', 'Bayern Munich', 'Bundesliga', '2025-2026', 'F',
         30, 2700, 26, 8, 90, 22.5, 6.1),
        ('Musiala', 'Bayern Munich', 'Bundesliga', '2025-2026', 'M',
         28, 2400, 12, 10, 55, 10.2, 8.4),
        ('Lewandowski', 'Barcelona', 'La Liga', '2026-2027', 'F',
         2, 180, 2, 0, 8, 1.8, 0.1),
        ('Yamal', 'Barcelona', 'La Liga', '2026-2027', 'F',
         2, 170, 1, 2, 5, 0.8, 1.2)
        """
    )
    connexion.commit()


@pytest.fixture
def connexion_memoire():
    connexion = sqlite3.connect(":memory:")
    connexion.row_factory = sqlite3.Row
    for schema in (
        SCHEMA_MATCHS,
        SCHEMA_MATCHS_XG,
        SCHEMA_CALENDRIER,
        SCHEMA_JOUEURS,
        SCHEMA_SITES,
    ):
        connexion.execute(schema)
    _remplir_base(connexion)
    yield connexion
    connexion.close()


@pytest.fixture
def fichier_base_temp(tmp_path):
    chemin = tmp_path / "football_test.db"
    connexion = sqlite3.connect(chemin)
    connexion.row_factory = sqlite3.Row
    for schema in (
        SCHEMA_MATCHS,
        SCHEMA_MATCHS_XG,
        SCHEMA_CALENDRIER,
        SCHEMA_JOUEURS,
        SCHEMA_SITES,
    ):
        connexion.execute(schema)
    _remplir_base(connexion)
    connexion.close()
    return chemin


@pytest.fixture
def client_api(fichier_base_temp, monkeypatch):
    """TestClient FastAPI branché sur une copie SQLite temporaire."""
    import cotes
    import serveur

    monkeypatch.setattr(serveur, "FICHIER_BASE", fichier_base_temp)
    monkeypatch.setattr(cotes, "FICHIER_BASE", fichier_base_temp)
    # Pas d'appel réseau : cache vide + pas de clé.
    monkeypatch.setattr(cotes, "lire_cle_api", lambda: "")
    with cotes._verrou:
        cotes._cache["expire"] = 0.0
        cotes._cache["matchs"] = None
        cotes._cache["erreur"] = ""

    from fastapi.testclient import TestClient

    return TestClient(serveur.app)
