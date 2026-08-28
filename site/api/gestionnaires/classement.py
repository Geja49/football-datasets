"""Gestionnaire HTTP — classement, Elo, calendrier, prochains matchs."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from modeles.parametres import (
    ParametresClassement,
    ParametresElo,
    ParametresFiltreChampionnatSaison,
    ParametresProchainsMatchs,
)

routeur_classement = APIRouter(tags=["classement"])


@routeur_classement.get("/api/classement")
def classement(filtres: Annotated[ParametresClassement, Query()]):
    import serveur

    championnat, saison, elo = filtres.championnat, filtres.saison, filtres.elo
    connexion = serveur.ouvrir_base()
    try:
        from requetes.matchs import lister_matchs_classement

        matchs = lister_matchs_classement(connexion, championnat, saison)
        classement_calc = serveur.calculer_classement(
            serveur.matchs_classement(matchs, championnat)
        )
        from analyse_rencontre import serie_forme_matchs

        for ligne in classement_calc:
            ligne["forme"] = serie_forme_matchs(matchs, ligne["equipe"])
            ligne.update(serveur.infos_site_equipe(connexion, ligne["equipe"]))
        elo_meta = {"disponible": False, "message": "", "date": "", "source": ""}
        if elo:
            from elo_clubs import enrichir_classement_elo

            elo_meta = enrichir_classement_elo(connexion, classement_calc, force_api=False)
        payload = {
            "classement": classement_calc,
            "championnat": serveur.infos_championnat(championnat),
            "saisons": serveur.saisons_disponibles(connexion, championnat),
            "format": "phase_de_ligue" if championnat == serveur.NOM_LDC else "ligue",
            "elo": elo_meta,
        }
        if championnat == serveur.NOM_LDC:
            payload["mention_sources"] = serveur.MESSAGE_LDC_PAGE
        return payload
    finally:
        connexion.close()


@routeur_classement.get("/api/elo")
def elo_api(filtres: Annotated[ParametresElo, Query()]):
    """Force relative ClubElo pour un club (retry soft via forcer=1)."""
    import serveur

    from correspondances import alias_noms_equipe

    nom = filtres.equipe
    connexion = serveur.ouvrir_base()
    try:
        alias = alias_noms_equipe(nom)
        from elo_clubs import elo_pour_equipe

        return elo_pour_equipe(connexion, alias, force_api=bool(filtres.forcer))
    finally:
        connexion.close()


@routeur_classement.get("/api/calendrier")
def calendrier_api(filtres: Annotated[ParametresFiltreChampionnatSaison, Query()]):
    championnat, saison = filtres.championnat, filtres.saison
    import serveur

    connexion = serveur.ouvrir_base()
    try:
        programme = serveur.charger_programme_saison(connexion, championnat, saison)
        serveur.ajouter_logos_programme(connexion, programme)
        payload = {
            "programme": programme,
            "championnat": serveur.infos_championnat(championnat),
            "saison": saison,
            "saisons": serveur.saisons_disponibles(connexion, championnat),
            "format": "phase_de_ligue" if championnat == serveur.NOM_LDC else "ligue",
        }
        if championnat == serveur.NOM_LDC:
            payload["mention_sources"] = serveur.MESSAGE_LDC_PAGE
        return payload
    finally:
        connexion.close()


@routeur_classement.get("/api/prochains_matchs")
def prochains_matchs_api(filtres: Annotated[ParametresProchainsMatchs, Query()]):
    championnat, saison = filtres.championnat, filtres.saison
    equipe, limite = filtres.equipe, filtres.limite
    import serveur

    connexion = serveur.ouvrir_base()
    try:
        aujourd_hui = date.today().isoformat()
        programme = serveur.charger_programme_saison(connexion, championnat, saison)
        prochains = serveur.filtrer_matchs_a_venir(programme, aujourd_hui)
        nom_equipe = ""
        if equipe:
            nom_equipe = serveur.resoudre_nom_equipe(equipe, programme)
        matchs_equipe = []
        if nom_equipe:
            du_club = [
                match
                for match in prochains
                if match["domicile"] == nom_equipe or match["exterieur"] == nom_equipe
            ]
            matchs_equipe = serveur.annoter_pour_equipe(du_club[:limite], nom_equipe)
        matchs_ligue = serveur.extraire_prochaine_journee(prochains)
        serveur.ajouter_logos_programme(connexion, matchs_equipe)
        serveur.ajouter_logos_programme(connexion, matchs_ligue)
        return {
            "equipe": nom_equipe,
            "aujourd_hui": aujourd_hui,
            "matchs_equipe": matchs_equipe,
            "matchs_ligue": matchs_ligue,
            "championnat": serveur.infos_championnat(championnat),
            "saison": saison,
        }
    finally:
        connexion.close()
