"""Service métier — analyse IA (wrapper en migration)."""

from __future__ import annotations

from ia_analyse import (
    enregistrer_analyse_ia_cachee,
    generer_analyse_ia,
    generer_faits_pour_ia,
    lire_analyse_ia_cachee,
)

__all__ = [
    "enregistrer_analyse_ia_cachee",
    "generer_analyse_ia",
    "generer_faits_pour_ia",
    "lire_analyse_ia_cachee",
]
