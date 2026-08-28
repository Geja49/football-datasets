"""Logique métier — top buteurs / passeurs."""

from __future__ import annotations

from fastapi import HTTPException

from photos_joueurs import photo_en_cache
from requetes.joueurs import COLONNES_MEILLEURS, lister_meilleurs, saison_avec_joueurs

MESSAGE_LDC_MEILLEURS = (
    "Buteurs LDC : OpenML 2013-2021. "
    "Pas de xG ni de saisons recentes cote joueurs."
)


def construire_reponse_meilleurs(
    connexion,
    championnat,
    saison,
    type_classement,
    nom_ldc,
    message_ldc_page,
    infos_championnat,
):
    """Assemble la réponse JSON /api/meilleurs."""
    if type_classement == "dribbles":
        return {
            "type": type_classement,
            "disponible": False,
            "raison": (
                "Understat ne fournit pas les dribbles. "
                "Il faudrait une autre source (par exemple FBref)."
            ),
            "joueurs": [],
            "championnat": infos_championnat(championnat),
            "saison": saison,
            "saison_utilisee": saison,
            "saison_de_secours": False,
            "message": "",
        }

    colonne = COLONNES_MEILLEURS.get(type_classement)
    if not colonne:
        raise HTTPException(400, "Type inconnu (buts, passes ou dribbles)")

    joueurs = lister_meilleurs(connexion, championnat, saison, colonne)
    saison_utilisee = saison
    message = ""
    if not joueurs:
        autre = saison_avec_joueurs(connexion, championnat)
        if autre and autre != saison:
            joueurs = lister_meilleurs(connexion, championnat, autre, colonne)
            if joueurs:
                saison_utilisee = autre
                libelle = "buteur" if type_classement == "buts" else "passeur"
                message = (
                    f"Aucun {libelle} pour {saison}. "
                    f"Affichage de la saison {autre}."
                )

    for joueur in joueurs:
        joueur["url_photo"] = photo_en_cache(connexion, joueur["joueur"])

    if not joueurs:
        libelle = "buteur" if type_classement == "buts" else "passeur"
        message = f"Aucun {libelle} pour {championnat} en {saison}."

    if championnat == nom_ldc and not message:
        message = MESSAGE_LDC_MEILLEURS
    elif championnat == nom_ldc and message:
        message = (
            f"{message} Sources : openfootball (scores) + OpenML 2013-2021 (buteurs)."
        )

    return {
        "type": type_classement,
        "disponible": True,
        "joueurs": joueurs,
        "championnat": infos_championnat(championnat),
        "saison": saison,
        "saison_utilisee": saison_utilisee,
        "saison_de_secours": saison_utilisee != saison,
        "message": message,
        "mention_sources": message_ldc_page if championnat == nom_ldc else "",
    }
