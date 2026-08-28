"""Service métier — Elo clubs (wrapper en migration)."""

from __future__ import annotations

from elo_clubs import elo_pour_equipe, enrichir_classement_elo

__all__ = ["elo_pour_equipe", "enrichir_classement_elo"]
