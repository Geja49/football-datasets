"""Gestionnaire HTTP — analyse de rencontre (classique + IA)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from modeles.parametres import ParametresAnalyseIa, ParametresRencontre
from services.analyse import analyser_rencontre
from services.cotes import lecture_marche_pour_analyse
from services.historique_analyses import (
    cle_match,
    ouvrir_base as ouvrir_analyses,
)
from services.ia_analyse import (
    enregistrer_analyse_ia_cachee,
    generer_analyse_ia,
    generer_faits_pour_ia,
    lire_analyse_ia_cachee,
)

routeur_analyse = APIRouter(tags=["analyse"])


@routeur_analyse.get("/api/analyse-rencontre")
def analyse_rencontre_api(filtres: Annotated[ParametresRencontre, Query()]):
    import serveur

    championnat, saison = filtres.championnat, filtres.saison
    nom_domicile, nom_exterieur = filtres.domicile, filtres.exterieur
    connexion = serveur.ouvrir_base()
    try:
        try:
            resultat = analyser_rencontre(
                connexion, championnat, saison, nom_domicile, nom_exterieur
            )
        except ValueError as erreur:
            raise HTTPException(400, str(erreur)) from erreur
        for cote in ("domicile", "exterieur"):
            site = serveur.infos_site_equipe(connexion, resultat[cote]["nom"])
            resultat[cote]["url_logo"] = site.get("url_logo", "")
        resultat["championnat"] = serveur.infos_championnat(championnat)
        date_match = None
        match_joue = resultat.get("match_joue") or {}
        if match_joue.get("joue"):
            date_match = match_joue.get("date")
        resultat["lecture_marche"] = lecture_marche_pour_analyse(
            championnat,
            nom_domicile,
            nom_exterieur,
            date_match=date_match,
            prediction=resultat.get("prediction"),
        )
        if not match_joue.get("joue"):
            resultat["match_a_venir"] = serveur.lire_horaire_match(
                connexion, championnat, saison, nom_domicile, nom_exterieur
            )
        else:
            resultat["match_a_venir"] = None
        serveur.enrichir_avec_prevision_figee(
            resultat, championnat, saison, nom_domicile, nom_exterieur
        )
        return resultat
    finally:
        connexion.close()


@routeur_analyse.get("/api/analyse-rencontre/ia")
def analyse_rencontre_ia_api(filtres: Annotated[ParametresAnalyseIa, Query()]):
    """Analyse narrative IA (LLM ou template) à partir de faits vérifiables."""
    import serveur

    championnat, saison = filtres.championnat, filtres.saison
    nom_domicile, nom_exterieur = filtres.domicile, filtres.exterieur
    regerer = filtres.regerer
    connexion = serveur.ouvrir_base()
    try:
        try:
            resultat = analyser_rencontre(
                connexion, championnat, saison, nom_domicile, nom_exterieur
            )
        except ValueError as erreur:
            raise HTTPException(400, str(erreur)) from erreur

        match_joue = resultat.get("match_joue") or {}
        if not match_joue.get("joue"):
            resultat["match_a_venir"] = serveur.lire_horaire_match(
                connexion, championnat, saison, nom_domicile, nom_exterieur
            )
        else:
            resultat["match_a_venir"] = None

        serveur.enrichir_avec_prevision_figee(
            resultat, championnat, saison, nom_domicile, nom_exterieur
        )
        prevision_figee = resultat.get("prevision_figee")

        date_ref = None
        if match_joue.get("joue"):
            date_ref = match_joue.get("date")
        elif resultat.get("match_a_venir"):
            date_ref = resultat["match_a_venir"].get("date")
        if not date_ref and prevision_figee:
            date_ref = prevision_figee.get("date_match")
        date_ref = (date_ref or "")[:10]

        cle = cle_match(championnat, saison, date_ref, nom_domicile, nom_exterieur)
        connexion_ia = ouvrir_analyses()
        try:
            if not regerer:
                cache = lire_analyse_ia_cachee(connexion_ia, cle)
                if cache and cache.get("texte"):
                    return {
                        "texte": cache["texte"],
                        "source": cache["source"],
                        "genere_le": cache.get("genere_le"),
                        "cle_match": cle,
                        "depuis_cache": True,
                    }

            faits = generer_faits_pour_ia(
                resultat.get("prediction") or {},
                prevision_figee,
                championnat=championnat,
                saison=saison,
                domicile=nom_domicile,
                exterieur=nom_exterieur,
                domicile_profil=resultat.get("domicile"),
                exterieur_profil=resultat.get("exterieur"),
                confrontations=resultat.get("confrontations"),
            )
            produit = generer_analyse_ia(faits)
            enregistrer_analyse_ia_cachee(
                connexion_ia,
                cle,
                produit["texte"],
                produit["source"],
                faits,
            )
            return {
                "texte": produit["texte"],
                "source": produit["source"],
                "genere_le": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "cle_match": cle,
                "depuis_cache": False,
            }
        finally:
            connexion_ia.close()
    finally:
        connexion.close()
