"""Tests Elo point-in-time (classements_elo historiques)."""

from __future__ import annotations

import sqlite3

from elo_clubs import elo_differentiel, lire_elo_a_date


def _creer_base_elo():
    connexion = sqlite3.connect(":memory:")
    connexion.row_factory = sqlite3.Row
    connexion.executescript(
        """
        CREATE TABLE classements_elo (
            date TEXT, rang TEXT, club TEXT, pays TEXT,
            niveau TEXT, elo REAL, source TEXT
        );
        """
    )
    donnees = [
        ("2026-01-01", "1", "Barcelona", "ESP", "1", 1850.0, "clubelo"),
        ("2026-01-01", "2", "Real Madrid", "ESP", "1", 1820.0, "clubelo"),
        ("2026-06-01", "1", "Barcelona", "ESP", "1", 1900.0, "clubelo"),
        ("2026-06-01", "2", "Real Madrid", "ESP", "1", 1880.0, "clubelo"),
    ]
    connexion.executemany(
        "INSERT INTO classements_elo VALUES (?,?,?,?,?,?,?)", donnees
    )
    connexion.commit()
    return connexion


def test_lire_elo_a_date_prend_snapshot_anterieur():
    connexion = _creer_base_elo()
    try:
        lignes, date_ref, mode = lire_elo_a_date(connexion, "2026-03-15")
        assert mode == "historique"
        assert date_ref == "2026-01-01"
        assert len(lignes) == 2
        barca = next(l for l in lignes if l["club"] == "Barcelona")
        assert barca["elo"] == 1850.0
    finally:
        connexion.close()


def test_lire_elo_a_date_sans_donnee_avant_limite():
    connexion = _creer_base_elo()
    try:
        lignes, date_ref, mode = lire_elo_a_date(connexion, "2025-12-01")
        assert mode == "indisponible"
        assert lignes == []
        assert date_ref is None
    finally:
        connexion.close()


def test_elo_differentiel_avec_date_limite():
    connexion = _creer_base_elo()
    try:
        paquet = elo_differentiel(
            connexion, "Barcelona", "Real Madrid", date_limite="2026-03-15"
        )
        assert paquet["disponible"] is True
        assert paquet["differentiel"] == 30.0
        assert paquet["date"] == "2026-01-01"
        assert paquet.get("date_limite") == "2026-03-15"
    finally:
        connexion.close()
