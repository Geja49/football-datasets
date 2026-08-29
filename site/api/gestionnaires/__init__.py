"""Routeurs FastAPI (handlers HTTP)."""

from gestionnaires.accueil import routeur_accueil
from gestionnaires.analyse import routeur_analyse
from gestionnaires.classement import routeur_classement
from gestionnaires.communaute import routeur_communaute
from gestionnaires.cotes import routeur_cotes
from gestionnaires.equipes import routeur_equipes
from gestionnaires.forum import routeur_forum
from gestionnaires.joueurs import routeur_joueurs
from gestionnaires.meilleurs import routeur_meilleurs
from gestionnaires.solo import routeur_solo
from gestionnaires.stats_modele import routeur_stats_modele

__all__ = [
    "routeur_accueil",
    "routeur_analyse",
    "routeur_classement",
    "routeur_communaute",
    "routeur_cotes",
    "routeur_equipes",
    "routeur_forum",
    "routeur_joueurs",
    "routeur_meilleurs",
    "routeur_solo",
    "routeur_stats_modele",
]
