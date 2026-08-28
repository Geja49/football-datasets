"""Gestionnaire HTTP — fiche joueur, recherche."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from modeles.parametres import ParametresJoueur, ParametresRecherche
from photos_joueurs import obtenir_photo
from requetes.connexion import lignes_dict
from requetes.matchs import rechercher_equipes_par_motif

routeur_joueurs = APIRouter(tags=["joueurs"])


@routeur_joueurs.get("/api/joueur")
def fiche_joueur(filtres: Annotated[ParametresJoueur, Query()]):
    import serveur

    nom_joueur = filtres.nom
    championnat = filtres.championnat
    filtre_ligue = championnat if championnat and championnat != serveur.NOM_LDC else None
    connexion = serveur.ouvrir_base()
    try:
        if filtre_ligue:
            saisons = lignes_dict(
                connexion.execute(
                    """
                    SELECT championnat, saison, equipe, poste, matchs, minutes,
                           buts, passes_decisives, tirs, passes_cles, xg, xa,
                           xg_chaine, xg_construction, carton_jaune, carton_rouge
                    FROM joueurs
                    WHERE joueur = ? AND championnat = ?
                    ORDER BY saison DESC
                    """,
                    (nom_joueur, filtre_ligue),
                )
            )
        else:
            saisons = lignes_dict(
                connexion.execute(
                    """
                    SELECT championnat, saison, equipe, poste, matchs, minutes,
                           buts, passes_decisives, tirs, passes_cles, xg, xa,
                           xg_chaine, xg_construction, carton_jaune, carton_rouge
                    FROM joueurs
                    WHERE joueur = ?
                    ORDER BY saison DESC, championnat
                    """,
                    (nom_joueur,),
                )
            )
        if not saisons:
            raise HTTPException(404, "Joueur introuvable")
        club_recent = (saisons[0].get("equipe") or "").split(",")[0]
        ligne_radar = serveur.saison_pour_radar(saisons)
        reperes = None
        if ligne_radar:
            reperes = serveur.reperes_joueur_ligue(
                connexion,
                ligne_radar.get("championnat"),
                ligne_radar.get("saison"),
            )
        return {
            "joueur": nom_joueur,
            "saisons": saisons,
            "url_photo": obtenir_photo(connexion, nom_joueur, club_recent),
            "reperes": reperes,
            "buts": serveur.resume_buts_joueur(
                saisons, serveur.ldc_par_joueur_en_base(connexion, nom_joueur)
            ),
            "defense": serveur.charger_defense_joueur(connexion, nom_joueur),
            "valeur_marche": serveur.charger_valeur_marche(connexion, nom_joueur),
            "transferts": serveur.charger_transferts_joueur(connexion, nom_joueur),
        }
    finally:
        connexion.close()


@routeur_joueurs.get("/api/recherche")
def recherche(filtres: Annotated[ParametresRecherche, Query()]):
    texte = filtres.q.replace("%", "").replace("_", "")
    if len(texte) < 2:
        raise HTTPException(400, "Recherche trop courte")
    motif = f"%{texte}%"
    import serveur

    connexion = serveur.ouvrir_base()
    try:
        joueurs = lignes_dict(
            connexion.execute(
                """
                SELECT DISTINCT joueur, equipe, championnat, saison, buts
                FROM joueurs
                WHERE joueur LIKE ?
                ORDER BY saison DESC, buts DESC
                LIMIT 20
                """,
                (motif,),
            )
        )
        equipes = rechercher_equipes_par_motif(connexion, motif)
        return {"joueurs": joueurs, "equipes": equipes}
    finally:
        connexion.close()
