"""Service métier — analyse de rencontre (wrapper en migration)."""

from __future__ import annotations

from analyse_rencontre import (
    LIGUES_NATIONALES,
    analyser_rencontre,
    comparaison_previsions_reel,
    lister_equipes_analyse,
    serie_forme_matchs,
    _bilan_match,
)

__all__ = [
    "LIGUES_NATIONALES",
    "analyser_rencontre",
    "comparaison_previsions_reel",
    "lister_equipes_analyse",
    "serie_forme_matchs",
    "_bilan_match",
]
