"""Connexion SQLite et utilitaires de lecture."""

from __future__ import annotations

from pathlib import Path
import sqlite3

from fastapi import HTTPException

RACINE = Path(__file__).resolve().parents[2]
FICHIER_BASE = RACINE / "donnees" / "football.db"


def lignes_dict(curseur):
    """Convertit un curseur SQLite en liste de dictionnaires."""
    return [dict(ligne) for ligne in curseur.fetchall()]


def ouvrir_base(fichier=None):
    """Ouvre football.db (ou un chemin de test)."""
    chemin = fichier or FICHIER_BASE
    if not chemin.exists():
        raise HTTPException(500, "Base introuvable. Lancez python scripts/creer_base.py")
    connexion = sqlite3.connect(chemin)
    connexion.row_factory = sqlite3.Row
    return connexion
