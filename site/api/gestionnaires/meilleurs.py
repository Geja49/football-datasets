"""Gestionnaire HTTP — top buteurs / passeurs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from modeles.parametres import ParametresMeilleurs
from services.meilleurs import construire_reponse_meilleurs

routeur_meilleurs = APIRouter(tags=["meilleurs"])


@routeur_meilleurs.get("/api/meilleurs")
def meilleurs_api(filtres: Annotated[ParametresMeilleurs, Query()]):
    """Top 20 buteurs ou passeurs. Les dribbles n'existent pas chez Understat."""
    import serveur

    connexion = serveur.ouvrir_base()
    try:
        return construire_reponse_meilleurs(
            connexion,
            filtres.championnat,
            filtres.saison,
            filtres.type,
            serveur.NOM_LDC,
            serveur.MESSAGE_LDC_PAGE,
            serveur.infos_championnat,
        )
    finally:
        connexion.close()
