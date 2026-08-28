"""Services métier de l'API."""

from services.analyse import (
    LIGUES_NATIONALES,
    analyser_rencontre,
    comparaison_previsions_reel,
    lister_equipes_analyse,
    serie_forme_matchs,
)
from services.calibration import agreger_metriques_saison
from services.calibrateur import infos_calibrateur
from services.communaute import charger_fichier_env, initialiser_base, routeur_communaute
from services.cotes import lecture_marche_pour_analyse, routeur_cotes
from services.elo import elo_pour_equipe, enrichir_classement_elo
from services.forum import assurer_tables_forum, routeur_forum
from services.historique_analyses import (
    cle_match,
    lire_prevision_figee,
    lire_prevision_sans_date,
    lire_resultat,
    lister_resultats_avec_previsions,
    ouvrir_base,
    pred_depuis_prevision_figee,
)
from services.ia_analyse import (
    enregistrer_analyse_ia_cachee,
    generer_analyse_ia,
    generer_faits_pour_ia,
    lire_analyse_ia_cachee,
)
from services.meilleurs import construire_reponse_meilleurs

__all__ = [
    "LIGUES_NATIONALES",
    "agreger_metriques_saison",
    "analyser_rencontre",
    "assurer_tables_forum",
    "charger_fichier_env",
    "cle_match",
    "comparaison_previsions_reel",
    "construire_reponse_meilleurs",
    "elo_pour_equipe",
    "enregistrer_analyse_ia_cachee",
    "enrichir_classement_elo",
    "generer_analyse_ia",
    "generer_faits_pour_ia",
    "infos_calibrateur",
    "initialiser_base",
    "lecture_marche_pour_analyse",
    "lire_analyse_ia_cachee",
    "lire_prevision_figee",
    "lire_prevision_sans_date",
    "lire_resultat",
    "lister_equipes_analyse",
    "lister_resultats_avec_previsions",
    "ouvrir_base",
    "pred_depuis_prevision_figee",
    "routeur_communaute",
    "routeur_cotes",
    "routeur_forum",
    "serie_forme_matchs",
]
