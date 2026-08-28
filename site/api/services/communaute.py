"""Service métier — communauté (wrapper en migration)."""

from __future__ import annotations

from communaute import (
    charger_fichier_env,
    initialiser_base,
    routeur_communaute,
)

__all__ = ["charger_fichier_env", "initialiser_base", "routeur_communaute"]
