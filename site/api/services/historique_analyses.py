"""Service métier — historique des analyses (wrapper en migration)."""

from __future__ import annotations

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
