"""Gestionnaire HTTP — page d'accueil."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter

routeur_accueil = APIRouter(tags=["accueil"])


@routeur_accueil.get("/api/accueil")
def accueil():
    """Championnats, saisons, matchs du jour, tops buteurs/passeurs."""
    import serveur

    connexion = serveur.ouvrir_base()
    try:
        aujourd_hui = date.today().isoformat()
        jour = serveur.choisir_jour_matchs(connexion, aujourd_hui)
        matchs_jour = serveur.charger_matchs_jour(connexion, jour) if jour else []
        return {
            "championnats": [serveur.infos_championnat(nom) for nom in serveur.CHAMPIONNATS],
            "saisons": serveur.saisons_disponibles(connexion),
            "jour": jour or aujourd_hui,
            "matchs_jour": matchs_jour,
            "buteurs": serveur.buteurs_par_ligue(connexion),
            "passeurs": serveur.passeurs_par_ligue(connexion),
        }
    finally:
        connexion.close()
