"""Gestionnaire HTTP — page Solo (pronos weekend)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from communaute import a_acces_solo, utilisateur_connecte
from modeles.solo import (
    ParametresBilanPronos,
    ParametresPronosWeekend,
    ReponseBilanSolo,
    ReponsePronosWeekend,
)
from services.solo_fige import (
    SEUIL_BILAN_PRONOS,
    bilan_weekend_solo,
    construire_pronos_weekend_ou_figes,
)

routeur_solo = APIRouter(tags=["solo"])


def _exiger_acces_solo(request: Request) -> None:
    """Admin ou super utilisateur — même garde pour Solo et analyses liées."""
    utilisateur, connexion_comm = utilisateur_connecte(request)
    try:
        if not a_acces_solo(utilisateur):
            raise HTTPException(
                403,
                "Accès réservé aux administrateurs et super utilisateurs",
            )
    finally:
        connexion_comm.close()


@routeur_solo.get("/api/solo/pronos-weekend", response_model=ReponsePronosWeekend)
def pronos_weekend_api(
    request: Request,
    filtres: Annotated[ParametresPronosWeekend, Query()],
):
    """Pronos Solo du weekend : figés si snapshot BD, sinon recalcul live."""
    _exiger_acces_solo(request)

    import serveur

    connexion = serveur.ouvrir_base()
    try:
        return construire_pronos_weekend_ou_figes(
            connexion,
            date_debut=filtres.date_debut,
            championnat=filtres.championnat,
        )
    finally:
        connexion.close()


@routeur_solo.get("/api/solo/pronos-figes", response_model=ReponsePronosWeekend)
def pronos_figes_api(
    request: Request,
    filtres: Annotated[ParametresPronosWeekend, Query()],
):
    """Pronos Solo figés uniquement (404 si weekend non figé)."""
    _exiger_acces_solo(request)

    from services.solo import vendredi_weekend
    from services.solo_fige import construire_pronos_depuis_figes

    weekend = filtres.date_debut or vendredi_weekend().isoformat()
    reponse = construire_pronos_depuis_figes(
        weekend, championnat=filtres.championnat
    )
    if reponse is None:
        raise HTTPException(404, "Aucun prono Solo figé pour ce weekend")
    return reponse


@routeur_solo.get("/api/solo/bilan-weekend", response_model=ReponseBilanSolo)
def bilan_weekend_api(
    request: Request,
    filtres: Annotated[ParametresPronosWeekend, Query()],
):
    """Bilan hit-rate des marchés Solo figés (après jugement)."""
    _exiger_acces_solo(request)
    return bilan_weekend_solo(
        weekend_debut=filtres.date_debut,
        championnat=filtres.championnat,
    )


@routeur_solo.get("/api/solo/bilan-pronos", response_model=ReponseBilanSolo)
def bilan_pronos_api(
    request: Request,
    filtres: Annotated[ParametresBilanPronos, Query()],
):
    """Écarts pronos vs réalité — marchés figés à proba ≥ seuil (défaut 70 %)."""
    _exiger_acces_solo(request)
    seuil = (
        float(filtres.proba_min)
        if filtres.proba_min is not None
        else SEUIL_BILAN_PRONOS
    )
    return bilan_weekend_solo(
        weekend_debut=filtres.date_debut,
        championnat=filtres.championnat,
        proba_min=seuil,
    )
