"""Modèles Pydantic des corps de requête forum (POST/PATCH)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from modeles.commun import (
    LONGUEUR_MESSAGE_FORUM_MAX,
    LONGUEUR_MOTIF_MAX,
    LONGUEUR_OPTION_SONDAGE_MAX,
    LONGUEUR_QUESTION_SONDAGE_MAX,
    LONGUEUR_TITRE_FORUM_MAX,
    NB_OPTIONS_SONDAGE_MAX,
    NB_OPTIONS_SONDAGE_MIN,
    nettoyer_chaine,
)

_CONFIG_ENTREE = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SujetCreerBody(BaseModel):
    model_config = _CONFIG_ENTREE

    titre: str = Field(..., min_length=1, max_length=LONGUEUR_TITRE_FORUM_MAX)
    contenu: str = Field(..., min_length=1, max_length=LONGUEUR_MESSAGE_FORUM_MAX)


class SujetModifierBody(BaseModel):
    model_config = _CONFIG_ENTREE

    titre: str = Field(..., min_length=1, max_length=LONGUEUR_TITRE_FORUM_MAX)


class MessageCreerBody(BaseModel):
    model_config = _CONFIG_ENTREE

    contenu: str = Field(..., min_length=1, max_length=LONGUEUR_MESSAGE_FORUM_MAX)
    message_parent_id: int | None = Field(default=None, ge=1)


class MessageModifierBody(BaseModel):
    model_config = _CONFIG_ENTREE

    contenu: str = Field(..., min_length=1, max_length=LONGUEUR_MESSAGE_FORUM_MAX)


class SignalementBody(BaseModel):
    model_config = _CONFIG_ENTREE

    motif: str = Field(default="", max_length=LONGUEUR_MOTIF_MAX)


class ReactionBody(BaseModel):
    model_config = _CONFIG_ENTREE

    type_reaction: Literal[
        "pouce", "coeur", "ballon", "feu", "rire", "applaudir"
    ] = "pouce"


class SondageCreerBody(BaseModel):
    model_config = _CONFIG_ENTREE

    question: str = Field(..., min_length=1, max_length=LONGUEUR_QUESTION_SONDAGE_MAX)
    options: list[str] = Field(
        ...,
        min_length=NB_OPTIONS_SONDAGE_MIN,
        max_length=NB_OPTIONS_SONDAGE_MAX,
    )

    @field_validator("options", mode="before")
    @classmethod
    def nettoyer_options(cls, valeur: list) -> list[str]:
        nettoyees: list[str] = []
        vues: set[str] = set()
        for brut in valeur or []:
            texte = nettoyer_chaine(brut)
            if not texte:
                continue
            if len(texte) > LONGUEUR_OPTION_SONDAGE_MAX:
                raise ValueError(
                    f"Option trop longue (max {LONGUEUR_OPTION_SONDAGE_MAX} caractères)"
                )
            cle = texte.casefold()
            if cle in vues:
                continue
            vues.add(cle)
            nettoyees.append(texte)
        return nettoyees

    @model_validator(mode="after")
    def assez_options(self) -> "SondageCreerBody":
        if len(self.options) < NB_OPTIONS_SONDAGE_MIN:
            raise ValueError(
                f"Au moins {NB_OPTIONS_SONDAGE_MIN} options distinctes requises"
            )
        return self


class SondageVoteBody(BaseModel):
    model_config = _CONFIG_ENTREE

    option_id: int = Field(..., ge=1)
