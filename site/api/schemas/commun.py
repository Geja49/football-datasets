"""Constantes et validateurs partagés pour les schémas d'entrée API."""

from __future__ import annotations

import re

CHAMPIONNATS_VALIDES = (
    "Premier League",
    "La Liga",
    "Bundesliga",
    "Serie A",
    "Ligue 1",
    "Super Lig",
    "Ligue des champions",
)

MOTIF_SAISON = re.compile(r"^\d{4}-\d{4}$")
MOTIF_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MOTIF_PSEUDO = re.compile(r"^[A-Za-z0-9_\-\s]{3,30}$")
MOTIF_CODE_LIGUE = re.compile(r"^[A-Z0-9]{6,12}$")
MOTIF_NOM_EQUIPE = re.compile(r"^[^\x00-\x1f<>]{1,80}$")

LONGUEUR_COMMENTAIRE_MAX = 500
LONGUEUR_PSEUDO_MAX = 30
LONGUEUR_MOT_DE_PASSE_MIN = 8
LONGUEUR_MOT_DE_PASSE_MAX = 128
LONGUEUR_NOM_LIGUE_MAX = 40
LONGUEUR_BIO_MAX = 160
LONGUEUR_EQUIPE_FAVORITE_MAX = 60
LONGUEUR_MESSAGE_LIGUE_MAX = 300
LONGUEUR_MOTIF_MAX = 200
LONGUEUR_TEXTE_MATCH_MAX = 80
LONGUEUR_SAISON_MAX = 16
LONGUEUR_JOURNEE_MAX = 16
LONGUEUR_TITRE_FORUM_MAX = 120
LONGUEUR_MESSAGE_FORUM_MAX = 1000
LONGUEUR_QUESTION_SONDAGE_MAX = 160
LONGUEUR_OPTION_SONDAGE_MAX = 80
LONGUEUR_RECHERCHE_MAX = 80
LONGUEUR_NOM_JOUEUR_MAX = 80

SCORE_BUTS_MAX = 15
LIMITE_PRONOS_LOT = 20
NB_OPTIONS_SONDAGE_MIN = 2
NB_OPTIONS_SONDAGE_MAX = 6

TYPES_REACTION = ("pouce", "coeur", "ballon", "feu", "rire", "applaudir")
CHOIX_SONDAGE_MATCH = ("1", "N", "2")
TYPES_PRONOSTIC = ("score", "1x2")
RESULTATS_1X2 = ("1", "N", "2")


def nettoyer_chaine(valeur: object) -> str:
    """Retire les espaces en début/fin ; chaîne vide si None."""
    if valeur is None:
        return ""
    if not isinstance(valeur, str):
        return str(valeur).strip()
    return valeur.strip()


def refuser_vide(valeur: str, message: str) -> str:
    if not valeur:
        raise ValueError(message)
    return valeur
