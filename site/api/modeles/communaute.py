"""Modèles Pydantic des corps de requête communauté (POST/PATCH)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from modeles.commun import (
    LONGUEUR_BIO_MAX,
    LONGUEUR_COMMENTAIRE_MAX,
    LONGUEUR_EQUIPE_FAVORITE_MAX,
    LONGUEUR_MESSAGE_LIGUE_MAX,
    LONGUEUR_MOT_DE_PASSE_MAX,
    LONGUEUR_MOT_DE_PASSE_MIN,
    LONGUEUR_MOTIF_MAX,
    LONGUEUR_NOM_LIGUE_MAX,
    LONGUEUR_PSEUDO_MAX,
    LONGUEUR_SAISON_MAX,
    LONGUEUR_TEXTE_MATCH_MAX,
    LIMITE_PRONOS_LOT,
    MOTIF_CODE_LIGUE,
    MOTIF_EMAIL,
    MOTIF_PSEUDO,
    SCORE_BUTS_MAX,
    refuser_vide,
)

_CONFIG_ENTREE = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InscriptionBody(BaseModel):
    model_config = _CONFIG_ENTREE

    email: str = Field(..., max_length=254)
    pseudo: str = Field(..., max_length=LONGUEUR_PSEUDO_MAX)
    mot_de_passe: str = Field(
        ...,
        min_length=LONGUEUR_MOT_DE_PASSE_MIN,
        max_length=LONGUEUR_MOT_DE_PASSE_MAX,
    )
    age_18_plus: bool = False
    cgu_acceptees: bool = False

    @field_validator("email")
    @classmethod
    def valider_email_format(cls, valeur: str) -> str:
        texte = valeur.lower()
        if not MOTIF_EMAIL.match(texte):
            raise ValueError("Adresse e-mail invalide")
        return texte

    @field_validator("pseudo")
    @classmethod
    def valider_pseudo_format(cls, valeur: str) -> str:
        if not MOTIF_PSEUDO.match(valeur):
            raise ValueError(
                "Pseudo invalide (3 à 30 caractères : lettres, chiffres, espaces, - ou _)"
            )
        return valeur


class ConnexionBody(BaseModel):
    """identifiant = pseudo ou e-mail. Le champ email reste accepté (compatibilité)."""

    model_config = _CONFIG_ENTREE

    identifiant: str = Field(default="", max_length=254)
    email: str = Field(default="", max_length=254)
    mot_de_passe: str = Field(..., max_length=LONGUEUR_MOT_DE_PASSE_MAX)

    @field_validator("mot_de_passe")
    @classmethod
    def mot_de_passe_non_vide(cls, valeur: str) -> str:
        return refuser_vide(valeur, "Mot de passe requis")


class CommentaireBody(BaseModel):
    model_config = _CONFIG_ENTREE

    championnat: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)
    saison: str = Field(..., max_length=LONGUEUR_SAISON_MAX)
    domicile: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)
    exterieur: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)
    contenu: str = Field(..., min_length=1, max_length=LONGUEUR_COMMENTAIRE_MAX)
    commentaire_parent_id: int | None = Field(default=None, ge=1)


class SignalementBody(BaseModel):
    model_config = _CONFIG_ENTREE

    motif: str = Field(default="", max_length=LONGUEUR_MOTIF_MAX)


class ReactionBody(BaseModel):
    model_config = _CONFIG_ENTREE

    type_reaction: Literal[
        "pouce", "coeur", "ballon", "feu", "rire", "applaudir"
    ] = "pouce"


class PronosticBody(BaseModel):
    model_config = _CONFIG_ENTREE

    championnat: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)
    saison: str = Field(..., max_length=LONGUEUR_SAISON_MAX)
    domicile: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)
    exterieur: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)
    type_pronostic: Literal["score", "1x2"]
    buts_domicile: int | None = Field(default=None, ge=0, le=SCORE_BUTS_MAX)
    buts_exterieur: int | None = Field(default=None, ge=0, le=SCORE_BUTS_MAX)
    resultat_1x2: Literal["1", "N", "2"] | None = None

    @field_validator("type_pronostic", mode="before")
    @classmethod
    def normaliser_type(cls, valeur: object) -> object:
        if isinstance(valeur, str):
            return valeur.strip().lower()
        return valeur

    @field_validator("resultat_1x2", mode="before")
    @classmethod
    def normaliser_1x2(cls, valeur: object) -> object:
        if isinstance(valeur, str):
            return valeur.strip().upper()
        return valeur

    @field_validator("championnat", "saison", "domicile", "exterieur")
    @classmethod
    def champs_match_non_vides(cls, valeur: str) -> str:
        return refuser_vide(valeur, "Champ match obligatoire")

    @model_validator(mode="after")
    def coherence_pronostic(self) -> "PronosticBody":
        if self.domicile == self.exterieur:
            raise ValueError("Les deux équipes doivent être différentes")
        if self.type_pronostic == "score":
            if self.buts_domicile is None or self.buts_exterieur is None:
                raise ValueError("Score domicile et extérieur requis")
            if self.resultat_1x2 is not None:
                raise ValueError("resultat_1x2 interdit pour un pronostic score")
        elif self.type_pronostic == "1x2":
            if self.resultat_1x2 is None:
                raise ValueError("Résultat 1X2 requis")
            if self.buts_domicile is not None or self.buts_exterieur is not None:
                raise ValueError("buts_domicile/buts_exterieur interdits pour un pronostic 1x2")
        return self


class SondageMatchVoteBody(BaseModel):
    model_config = _CONFIG_ENTREE

    championnat: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)
    saison: str = Field(..., max_length=LONGUEUR_SAISON_MAX)
    domicile: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)
    exterieur: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)
    choix: Literal["1", "N", "2"]


class GoogleConnexionBody(BaseModel):
    model_config = _CONFIG_ENTREE

    id_token: str = Field(..., min_length=1, max_length=8192)


class LigueCreerBody(BaseModel):
    model_config = _CONFIG_ENTREE

    nom: str = Field(..., min_length=1, max_length=LONGUEUR_NOM_LIGUE_MAX)


class LigueRejoindreBody(BaseModel):
    model_config = _CONFIG_ENTREE

    code_invitation: str = Field(..., min_length=6, max_length=12)

    @field_validator("code_invitation")
    @classmethod
    def valider_code(cls, valeur: str) -> str:
        texte = valeur.upper()
        if not MOTIF_CODE_LIGUE.match(texte):
            raise ValueError("Code d'invitation invalide")
        return texte


class ProfilMajBody(BaseModel):
    model_config = _CONFIG_ENTREE

    bio: str = Field(default="", max_length=LONGUEUR_BIO_MAX)
    equipe_favorite: str = Field(default="", max_length=LONGUEUR_EQUIPE_FAVORITE_MAX)
    avatar_id: str | None = Field(default=None, max_length=32)
    pseudo: str | None = Field(default=None, max_length=LONGUEUR_PSEUDO_MAX)

    @field_validator("pseudo")
    @classmethod
    def valider_pseudo_optionnel(cls, valeur: str | None) -> str | None:
        if valeur is None:
            return None
        if not MOTIF_PSEUDO.match(valeur):
            raise ValueError("Pseudo invalide")
        return valeur


class MessageLigueBody(BaseModel):
    model_config = _CONFIG_ENTREE

    contenu: str = Field(..., min_length=1, max_length=LONGUEUR_MESSAGE_LIGUE_MAX)


class PronosticsLotBody(BaseModel):
    model_config = _CONFIG_ENTREE

    pronostics: list[PronosticBody] = Field(
        default_factory=list,
        max_length=LIMITE_PRONOS_LOT,
    )


class SignalementTraiterBody(BaseModel):
    model_config = _CONFIG_ENTREE

    statut: Literal["ouvert", "traite"] = "traite"
