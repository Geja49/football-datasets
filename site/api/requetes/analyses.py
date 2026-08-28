"""Requêtes SQL — analyses.db (prévisions figées, cache IA)."""

from __future__ import annotations

# Lecture isolée : délégation au module historique en attendant extraction complète.
from historique_analyses import (
    cle_match,
    lire_prevision_figee,
    lire_prevision_sans_date,
    lire_resultat,
    lister_resultats_avec_previsions,
    ouvrir_base,
    pred_depuis_prevision_figee,
)

__all__ = [
    "cle_match",
    "lire_prevision_figee",
    "lire_prevision_sans_date",
    "lire_resultat",
    "lister_resultats_avec_previsions",
    "ouvrir_base",
    "pred_depuis_prevision_figee",
]
