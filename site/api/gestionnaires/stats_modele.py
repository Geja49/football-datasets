"""Gestionnaire HTTP — stats de calibration du modèle."""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Query

from calibration import agreger_metriques_saison
from calibrateur import infos_calibrateur
from historique_analyses import lister_resultats_avec_previsions, ouvrir_base
from modeles.parametres import ParametresStatsModele

routeur_stats_modele = APIRouter(tags=["stats-modele"])


@routeur_stats_modele.get("/api/stats-modele")
def stats_modele_api(filtres: Annotated[ParametresStatsModele, Query()]):
    """Agregats de calibration depuis analyses.db (previsions figees vs realite)."""
    saison = filtres.saison
    champ_filtre = filtres.championnat
    inclure_retroactif = filtres.inclure_retroactif
    connexion = ouvrir_base()
    try:
        resultats = lister_resultats_avec_previsions(
            connexion,
            saison,
            champ_filtre,
            inclure_retroactif=bool(inclure_retroactif),
        )
        global_stats = agreger_metriques_saison(resultats)
        par_championnat: dict[str, dict] = {}
        groupes: dict[str, list] = defaultdict(list)
        for ligne in resultats:
            groupes[ligne["championnat"]].append(ligne)
        for nom_champ, lignes in sorted(groupes.items()):
            par_championnat[nom_champ] = agreger_metriques_saison(lignes)
        return {
            "saison": saison,
            "championnat": champ_filtre,
            "inclure_retroactif": bool(inclure_retroactif),
            "disponible": global_stats["nb_matchs"] > 0,
            "metriques": global_stats,
            "par_championnat": par_championnat,
            "nb_resultats": global_stats["nb_matchs"],
            "calibrateur": infos_calibrateur(),
        }
    finally:
        connexion.close()
