"""Tests unitaires (sans cle API) pour collecter_api_football."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
CHEMIN = RACINE / "collecter_api_football.py"


def charger_module():
    spec = importlib.util.spec_from_file_location("collecter_api_football", CHEMIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules["collecter_api_football"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


api = charger_module()


class TestErreursEtQuota(unittest.TestCase):
    def test_formater_erreurs_plan(self):
        data = {
            "errors": {
                "plan": "Free plans do not have access to this season, try from 2022 to 2024."
            },
            "response": [],
        }
        msg = api.formater_erreurs_api(data)
        self.assertIn("Free plans", msg)
        self.assertTrue(api.est_erreur_plan_saison(msg))

    def test_quota_restant_header_absent(self):
        class Fake:
            headers = {}

        self.assertIsNone(api.quota_restant(Fake()))

    def test_quota_restant_zero(self):
        class Fake:
            headers = {"x-ratelimit-requests-remaining": "0"}

        self.assertEqual(api.quota_restant(Fake()), 0)

    def test_cache_ignore_erreur(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            ancien = api.DOSSIER_CACHE
            api.DOSSIER_CACHE = Path(tmp)
            try:
                chemin = api.chemin_cache_fixtures(140, "2026-08-13", "2026-09-17")
                chemin.write_text(
                    '{"errors":{"plan":"Free plans do not have access to this season"},'
                    '"response":[]}',
                    encoding="utf-8",
                )
                self.assertIsNone(api.lire_cache_fixtures(140, "2026-08-13", "2026-09-17"))
                self.assertFalse(chemin.exists())
            finally:
                api.DOSSIER_CACHE = ancien


class TestParserEtFusion(unittest.TestCase):
    def test_parser_match_termine(self):
        item = {
            "fixture": {
                "date": "2026-08-20T19:00:00+00:00",
                "status": {"short": "FT"},
            },
            "league": {"round": "Regular Season - 2"},
            "teams": {
                "home": {"name": "Arsenal"},
                "away": {"name": "Chelsea"},
            },
            "goals": {"home": 2, "away": 1},
        }
        parse = api.parser_fixture(item, "Premier League", {"Arsenal", "Chelsea"})
        self.assertEqual(parse["type"], "match")
        self.assertEqual(parse["ligne"]["buts_domicile"], 2)
        self.assertEqual(parse["ligne"]["resultat"], "H")

    def test_parser_calendrier(self):
        item = {
            "fixture": {
                "date": "2026-09-01T15:30:00+00:00",
                "status": {"short": "NS"},
            },
            "league": {"round": "Regular Season - 4"},
            "teams": {
                "home": {"name": "Bayern Munich"},
                "away": {"name": "Dortmund"},
            },
            "goals": {"home": None, "away": None},
        }
        parse = api.parser_fixture(
            item, "Bundesliga", {"Bayern Munich", "Dortmund"}
        )
        self.assertEqual(parse["type"], "calendrier")
        self.assertEqual(parse["ligne"]["heure"], "15:30")
        self.assertEqual(parse["ligne"]["journee"], "Regular Season - 4")

    def test_fusionner_matchs_maj_et_ajout(self):
        existants = [
            {
                "championnat": "Ligue 1",
                "saison": api.SAISON,
                "date": "2026-08-20",
                "domicile": "PSG",
                "exterieur": "Marseille",
                "buts_domicile": "",
                "buts_exterieur": "",
                "resultat": "",
            }
        ]
        nouveaux = [
            {
                "championnat": "Ligue 1",
                "saison": api.SAISON,
                "date": "2026-08-20",
                "domicile": "PSG",
                "exterieur": "Marseille",
                "buts_domicile": 3,
                "buts_exterieur": 0,
                "resultat": "H",
            },
            {
                "championnat": "Ligue 1",
                "saison": api.SAISON,
                "date": "2026-08-21",
                "domicile": "Lyon",
                "exterieur": "Lille",
                "buts_domicile": 1,
                "buts_exterieur": 1,
                "resultat": "D",
            },
        ]
        resultat, maj, ajouts = api.fusionner_matchs(existants, nouveaux)
        self.assertEqual(maj, 1)
        self.assertEqual(ajouts, 1)
        self.assertEqual(resultat[0]["buts_domicile"], 3)
        self.assertEqual(len(resultat), 2)

    def test_fusionner_calendrier_anti_doublon(self):
        existant = [
            {
                "championnat": "Serie A",
                "saison": api.SAISON,
                "date": "2026-09-10",
                "heure": "20:45",
                "domicile": "Inter",
                "exterieur": "Milan",
                "journee": "5",
            }
        ]
        ajouts = [
            {
                "championnat": "Serie A",
                "saison": api.SAISON,
                "date": "2026-09-10",
                "heure": "20:45",
                "domicile": "Inter",
                "exterieur": "Milan",
                "journee": "Regular Season - 5",
            },
            {
                "championnat": "Serie A",
                "saison": api.SAISON,
                "date": "2026-09-11",
                "heure": "18:00",
                "domicile": "Roma",
                "exterieur": "Napoli",
                "journee": "5",
            },
        ]
        resultat, nb = api.fusionner_calendrier(existant, ajouts, [])
        self.assertEqual(nb, 1)
        self.assertEqual(len(resultat), 2)

    def test_skip_sans_cle(self):
        ancienne = os.environ.pop("CLE_API_FOOTBALL", None)
        original = api.charger_env
        api.charger_env = lambda _racine: None
        try:
            stats = api.collecter()
            self.assertEqual(stats["matchs_maj"], 0)
            self.assertEqual(stats["matchs_ajoutes"], 0)
            self.assertEqual(stats["calendrier_ajoutes"], 0)
        finally:
            api.charger_env = original
            if ancienne is not None:
                os.environ["CLE_API_FOOTBALL"] = ancienne


class TestCornersLdc(unittest.TestCase):
    def test_corners_manquants_ldc(self):
        matchs = [
            {
                "championnat": "Ligue des champions",
                "saison": "2025-2026",
                "date": "2026-01-10",
                "domicile": "PSG",
                "exterieur": "Bayern",
                "buts_domicile": 2,
                "buts_exterieur": 1,
                "corners_domicile": "",
                "corners_exterieur": "",
            },
            {
                "championnat": "Ligue des champions",
                "saison": "2025-2026",
                "date": "2026-01-09",
                "domicile": "Real",
                "exterieur": "City",
                "buts_domicile": 1,
                "buts_exterieur": 1,
                "corners_domicile": 5,
                "corners_exterieur": 4,
            },
            {
                "championnat": "Ligue 1",
                "saison": "2025-2026",
                "date": "2026-01-10",
                "domicile": "Lyon",
                "exterieur": "Lille",
                "buts_domicile": 1,
                "buts_exterieur": 0,
                "corners_domicile": "",
                "corners_exterieur": "",
            },
        ]
        sans = api.lister_ldc_sans_corners(matchs, limite=10)
        self.assertEqual(len(sans), 1)
        self.assertEqual(sans[0]["domicile"], "PSG")

    def test_extraire_corners_statistics(self):
        data = {
            "response": [
                {
                    "team": {"name": "Arsenal"},
                    "statistics": [{"type": "Corner Kicks", "value": 7}],
                },
                {
                    "team": {"name": "Chelsea"},
                    "statistics": [{"type": "Corner Kicks", "value": 3}],
                },
            ]
        }
        dom, ext = api.extraire_corners_statistics(data)
        self.assertEqual(dom, 7)
        self.assertEqual(ext, 3)

    def test_fusionner_corners_matchs(self):
        existants = [
            {
                "championnat": "Ligue des champions",
                "saison": api.SAISON,
                "date": "2026-01-10",
                "domicile": "PSG",
                "exterieur": "Bayern",
                "buts_domicile": 2,
                "buts_exterieur": 1,
                "corners_domicile": "",
                "corners_exterieur": "",
            }
        ]
        patches = [
            {
                "championnat": "Ligue des champions",
                "saison": api.SAISON,
                "date": "2026-01-10",
                "domicile": "PSG",
                "exterieur": "Bayern",
                "corners_domicile": 6,
                "corners_exterieur": 4,
            }
        ]
        resultat, nb = api.fusionner_corners_matchs(existants, patches)
        self.assertEqual(nb, 1)
        self.assertEqual(resultat[0]["corners_domicile"], 6)
        self.assertEqual(resultat[0]["corners_exterieur"], 4)

    def test_corners_ldc_sans_cle(self):
        ancienne = os.environ.pop("CLE_API_FOOTBALL", None)
        original = api.charger_env
        api.charger_env = lambda _racine: None
        try:
            stats = api.collecter_corners_ldc_fichier(limite=5)
            self.assertEqual(stats["corners_maj"], 0)
        finally:
            api.charger_env = original
            if ancienne is not None:
                os.environ["CLE_API_FOOTBALL"] = ancienne


if __name__ == "__main__":
    unittest.main()
