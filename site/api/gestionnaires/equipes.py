"""Gestionnaire HTTP — fiches équipe, équipes analyse, défense."""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Query

from correspondances import alias_noms_equipe, nom_pour_joueurs
from modeles.parametres import ParametresEquipe, ParametresFiltreChampionnatSaison
from photos_joueurs import photo_en_cache
from requetes.equipes import (
    choisir_nom_dans_competition,
    lister_equipes_distinctes_joueurs,
    lister_joueurs_equipe,
    lister_joueurs_equipe_ldc_fallback,
)
from requetes.matchs import lister_matchs_equipe_fiche
from services.analyse import lister_equipes_analyse

routeur_equipes = APIRouter(tags=["equipes"])


@routeur_equipes.get("/api/equipe")
def fiche_equipe(filtres: Annotated[ParametresEquipe, Query()]):
    import serveur

    championnat, saison = filtres.championnat, filtres.saison
    nom_page = filtres.equipe
    connexion = serveur.ouvrir_base()
    try:
        noms_alias = alias_noms_equipe(nom_page)
        nom_matchs = (
            choisir_nom_dans_competition(connexion, championnat, saison, noms_alias)
            or nom_page
        )
        resume_buts = serveur.resume_buts_equipe(connexion, saison, nom_page, championnat)
        matchs_radar = serveur.charger_matchs_radar_equipe(
            connexion, saison, resume_buts["alias"]
        )
        par_xg = defaultdict(list)
        for match in matchs_radar:
            par_xg[match.get("championnat")].append(match)
        for nom_comp, groupe in par_xg.items():
            if nom_comp and nom_comp != serveur.NOM_LDC:
                serveur.joindre_xg(connexion, nom_comp, saison, groupe)
        matchs = lister_matchs_equipe_fiche(connexion, championnat, saison, nom_matchs)
        for match in matchs:
            match["joue"] = True
            match["heure"] = match.get("heure") or ""
            match["journee"] = match.get("journee") or ""
        vus = {(m["domicile"], m["exterieur"]) for m in matchs}
        for ligne in serveur.lire_calendrier(connexion, championnat, saison, nom_matchs):
            cle = (ligne["domicile"], ligne["exterieur"])
            if cle in vus:
                continue
            vus.add(cle)
            matchs.append(
                {
                    "date": ligne["date"],
                    "heure": ligne.get("heure") or "",
                    "journee": ligne.get("journee") or "",
                    "domicile": ligne["domicile"],
                    "exterieur": ligne["exterieur"],
                    "buts_domicile": None,
                    "buts_exterieur": None,
                    "resultat": None,
                    "tirs_domicile": None,
                    "tirs_exterieur": None,
                    "tirs_cadres_domicile": None,
                    "tirs_cadres_exterieur": None,
                    "jaunes_domicile": None,
                    "jaunes_exterieur": None,
                    "rouges_domicile": None,
                    "rouges_exterieur": None,
                    "xg_domicile": None,
                    "xg_exterieur": None,
                    "joue": False,
                }
            )
        matchs.sort(key=lambda m: (m["date"] or "", m.get("heure") or ""))
        serveur.joindre_journee(connexion, championnat, saison, matchs)
        serveur.joindre_xg(connexion, championnat, saison, matchs)
        serveur.enrichir_horaires(matchs, championnat)
        serveur.ajouter_logos_programme(connexion, matchs)
        noms_understat = lister_equipes_distinctes_joueurs(connexion, championnat, saison)
        nom_stats = nom_pour_joueurs(nom_matchs, noms_understat)
        joueurs = lister_joueurs_equipe(connexion, championnat, saison, nom_stats)
        if not joueurs and championnat == serveur.NOM_LDC:
            ligues = [nom for nom in serveur.CHAMPIONNATS if nom != serveur.NOM_LDC]
            joueurs = lister_joueurs_equipe_ldc_fallback(
                connexion, ligues, saison, nom_stats
            )
        for joueur in joueurs:
            joueur["url_photo"] = photo_en_cache(connexion, joueur["joueur"])
        alias_radar = resume_buts.pop("alias")
        defense = serveur.charger_defense_equipe(
            connexion, championnat, saison, nom_matchs, alias_radar
        )
        reperes = serveur.reperes_equipe_ligue(connexion, championnat, saison)
        from elo_clubs import elo_pour_equipe

        elo = elo_pour_equipe(connexion, alias_radar, force_api=False)
        payload = {
            "equipe": nom_matchs,
            "nom_stats": nom_stats,
            "matchs": matchs,
            "matchs_radar": matchs_radar,
            "alias_equipe": alias_radar,
            "buts": resume_buts,
            "joueurs": joueurs,
            "defense": defense,
            "reperes": reperes,
            "elo": elo,
            "site": serveur.infos_site_equipe(connexion, nom_matchs),
            "championnat": serveur.infos_championnat(championnat),
        }
        if championnat == serveur.NOM_LDC:
            payload["mention_sources"] = serveur.MESSAGE_LDC_PAGE
        return payload
    finally:
        connexion.close()


@routeur_equipes.get("/api/equipes-analyse")
def equipes_analyse(filtres: Annotated[ParametresFiltreChampionnatSaison, Query()]):
    championnat, saison = filtres.championnat, filtres.saison
    import serveur

    connexion = serveur.ouvrir_base()
    try:
        noms = lister_equipes_analyse(connexion, championnat, saison)
        equipes = []
        for nom in noms:
            fiche = serveur.infos_site_equipe(connexion, nom)
            equipes.append(
                {
                    "equipe": nom,
                    "url_logo": fiche.get("url_logo", ""),
                }
            )
        return {
            "equipes": equipes,
            "championnat": serveur.infos_championnat(championnat),
            "saison": saison,
        }
    finally:
        connexion.close()
