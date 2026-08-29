"""Tests — boucle d'amélioration Solo (figer / juger / calibrer)."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

RACINE = Path(__file__).resolve().parents[3]
SCRIPTS = RACINE / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import boucle_amelioration as boucle  # noqa: E402


def _dt(annee, mois, jour, heure=12, minute=0) -> datetime:
    """Datetime locale naïve (comme un PC Windows sans UTC forcé)."""
    return datetime(annee, mois, jour, heure, minute).astimezone()


def test_doit_figer_vendredi():
    assert boucle.doit_figer_aujourdhui(_dt(2026, 8, 28, 10)) is True  # vendredi


def test_doit_figer_jeudi_soir():
    assert boucle.doit_figer_aujourdhui(_dt(2026, 8, 27, 18)) is True
    assert boucle.doit_figer_aujourdhui(_dt(2026, 8, 27, 17, 59)) is False


def test_doit_figer_autres_jours():
    assert boucle.doit_figer_aujourdhui(_dt(2026, 8, 26, 20)) is False  # mercredi
    assert boucle.doit_figer_aujourdhui(_dt(2026, 8, 31, 12)) is False  # lundi


def test_doit_figer_forcer():
    assert boucle.doit_figer_aujourdhui(_dt(2026, 8, 26, 10), forcer=True) is True


def test_doit_juger_toujours():
    assert boucle.doit_juger_aujourdhui(_dt(2026, 8, 26)) is True
    assert boucle.doit_juger_aujourdhui(_dt(2026, 8, 31)) is True


def test_suggestion_seuils_garde_fous():
    assert boucle.suggestion_seuils(40.0, 10) is None  # trop peu de verdicts
    assert boucle.suggestion_seuils(70.0, 25) is None  # hit-rate OK
    assert boucle.suggestion_seuils(None, 50) is None
    msg = boucle.suggestion_seuils(40.0, 25)
    assert msg is not None
    assert "Hit-rate Solo faible" in msg
    assert "aucun changement automatique" in msg


def test_executer_boucle_skip_figer_si_deja_fige(tmp_path: Path):
    """Relancer un vendredi ne re-fige pas si weekend déjà présent."""
    vendredi = _dt(2026, 8, 28, 12)

    with (
        patch.object(boucle, "doit_figer_aujourdhui", return_value=True),
        patch.object(
            boucle,
            "etape_figer",
            return_value={
                "action": "figer",
                "statut": "skip",
                "weekend_debut": "2026-08-28",
                "nb_figes": 0,
                "message": "Weekend 2026-08-28 déjà figé — skip",
            },
        ) as mock_figer,
        patch.object(
            boucle,
            "etape_juger",
            return_value={
                "action": "juger",
                "statut": "ok",
                "nb_juges": 0,
                "nb_vrais": 0,
                "nb_faux": 0,
                "message": "0 marché(s) jugé(s)",
            },
        ),
        patch.object(
            boucle,
            "etape_calibrateur",
            return_value={
                "action": "calibrateur",
                "statut": "skip",
                "message": "Pas assez de données",
            },
        ),
        patch.object(
            boucle,
            "enregistrer_bilan_solo",
            return_value={
                "global": {"nb_juges": 0, "nb_vrais": 0, "hit_rate": None},
                "suggestion": None,
            },
        ),
    ):
        resume = boucle.executer_boucle(
            maintenant=vendredi,
            skip_calibrateur=False,
        )

    mock_figer.assert_called_once()
    etape_figer = next(e for e in resume["etapes"] if e["action"] == "figer")
    assert etape_figer["statut"] == "skip"
    assert etape_figer["nb_figes"] == 0
    assert resume["ok"] is True


def test_executer_boucle_hors_fenetre_figer():
    mercredi = _dt(2026, 8, 26, 12)

    with (
        patch.object(
            boucle,
            "etape_juger",
            return_value={
                "action": "juger",
                "statut": "ok",
                "nb_juges": 2,
                "nb_vrais": 1,
                "nb_faux": 1,
                "hit_rate": 50.0,
                "message": "2 marché(s) jugé(s)",
            },
        ) as mock_juger,
        patch.object(
            boucle,
            "etape_figer",
            side_effect=AssertionError("ne doit pas figer"),
        ),
        patch.object(
            boucle,
            "enregistrer_bilan_solo",
            return_value={
                "global": {"nb_juges": 2, "nb_vrais": 1, "hit_rate": 50.0},
                "suggestion": None,
            },
        ),
        patch.object(
            boucle,
            "etape_calibrateur",
            return_value={
                "action": "calibrateur",
                "statut": "skip",
                "message": "skip",
            },
        ),
    ):
        resume = boucle.executer_boucle(maintenant=mercredi)

    mock_juger.assert_called_once()
    etape_figer = next(e for e in resume["etapes"] if e["action"] == "figer")
    assert etape_figer["statut"] == "skip"
    assert "Hors fenetre" in etape_figer["message"]


def test_executer_boucle_skip_calibrateur():
    with (
        patch.object(boucle, "doit_figer_aujourdhui", return_value=False),
        patch.object(
            boucle,
            "etape_juger",
            return_value={
                "action": "juger",
                "statut": "ok",
                "nb_juges": 0,
                "nb_vrais": 0,
                "nb_faux": 0,
                "message": "0",
            },
        ),
        patch.object(
            boucle,
            "enregistrer_bilan_solo",
            return_value={"global": {"nb_juges": 0, "hit_rate": None}, "suggestion": None},
        ),
        patch.object(boucle, "etape_calibrateur") as mock_cal,
    ):
        resume = boucle.executer_boucle(
            maintenant=_dt(2026, 8, 26),
            skip_calibrateur=True,
        )

    mock_cal.assert_not_called()
    etape = next(e for e in resume["etapes"] if e["action"] == "calibrateur")
    assert etape["statut"] == "skip"


def test_enregistrer_bilan_solo_json(tmp_path: Path):
    cible = tmp_path / "bilan_solo.json"
    faux_stats = {
        "weekends": {
            "2026-08-28": {
                "nb_juges": 10,
                "nb_vrais": 4,
                "nb_faux": 6,
                "hit_rate": 40.0,
            }
        },
        "global": {
            "nb_juges": 25,
            "nb_vrais": 10,
            "nb_faux": 15,
            "hit_rate": 40.0,
        },
    }
    with patch.object(boucle, "_stats_verdicts_globaux", return_value=faux_stats):
        bilan = boucle.enregistrer_bilan_solo(chemin=cible)

    assert cible.is_file()
    data = json.loads(cible.read_text(encoding="utf-8"))
    assert data["global"]["hit_rate"] == 40.0
    assert data["suggestion"] is not None
    assert data["garde_fous"]["seuils_auto"] is False
    assert bilan["suggestion"] == data["suggestion"]


def test_etape_figer_skip_si_weekend_deja_fige():
    """Imports dynamiques dans etape_figer : patcher les modules source."""
    import services.solo as solo_mod
    import services.solo_fige as fige_mod

    weekend = MagicMock()
    weekend.isoformat.return_value = "2026-08-28"

    with (
        patch.object(solo_mod, "vendredi_weekend", return_value=weekend),
        patch.object(fige_mod, "weekend_est_fige", return_value=True),
        patch.object(fige_mod, "figer_pronos_weekend") as mock_figer,
    ):
        resultat = boucle.etape_figer(forcer=False)

    assert resultat["statut"] == "skip"
    assert resultat["nb_figes"] == 0
    assert "fige" in resultat["message"].lower() or "figé" in resultat["message"].lower()
    mock_figer.assert_not_called()
