"""Modèles Pydantic des paramètres de requête GET (query string)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from modeles.commun import (
    CHAMPIONNATS_VALIDES,
    LONGUEUR_JOURNEE_MAX,
    LONGUEUR_NOM_JOUEUR_MAX,
    LONGUEUR_PSEUDO_MAX,
    LONGUEUR_RECHERCHE_MAX,
    LONGUEUR_SAISON_MAX,
    LONGUEUR_TEXTE_MATCH_MAX,
    MOTIF_NOM_EQUIPE,
    MOTIF_SAISON,
    nettoyer_chaine,
    refuser_vide,
)

_CONFIG_QUERY = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _valider_championnat(valeur: str) -> str:
    texte = refuser_vide(valeur, "Championnat requis")
    if texte not in CHAMPIONNATS_VALIDES:
        raise ValueError("Championnat inconnu")
    return texte


def _valider_saison(valeur: str) -> str:
    texte = refuser_vide(valeur, "Saison requise")
    if len(texte) > LONGUEUR_SAISON_MAX:
        raise ValueError("Saison invalide")
    if not MOTIF_SAISON.match(texte):
        raise ValueError("Saison invalide (format attendu : 2026-2027)")
    return texte


def _valider_nom_equipe(valeur: str, obligatoire: bool = True) -> str:
    texte = nettoyer_chaine(valeur)
    if not texte:
        if obligatoire:
            raise ValueError("Nom d'équipe requis")
        return ""
    if len(texte) > LONGUEUR_TEXTE_MATCH_MAX:
        raise ValueError("Nom d'équipe trop long")
    if not MOTIF_NOM_EQUIPE.match(texte):
        raise ValueError("Nom d'équipe invalide")
    return texte


class ParametresFiltreChampionnatSaison(BaseModel):
    """championnat + saison (routes stats / calendrier)."""

    model_config = _CONFIG_QUERY

    championnat: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)
    saison: str = Field(..., max_length=LONGUEUR_SAISON_MAX)

    @field_validator("championnat")
    @classmethod
    def champ_valide(cls, valeur: str) -> str:
        return _valider_championnat(valeur)

    @field_validator("saison")
    @classmethod
    def saison_valide(cls, valeur: str) -> str:
        return _valider_saison(valeur)


class ParametresClassement(ParametresFiltreChampionnatSaison):
    elo: int = Field(default=0, ge=0, le=1)


class ParametresEquipe(ParametresFiltreChampionnatSaison):
    equipe: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)

    @field_validator("equipe")
    @classmethod
    def equipe_valide(cls, valeur: str) -> str:
        return _valider_nom_equipe(valeur)


class ParametresProchainsMatchs(ParametresFiltreChampionnatSaison):
    equipe: str | None = Field(default=None, max_length=LONGUEUR_TEXTE_MATCH_MAX)
    limite: int = Field(default=8, ge=1, le=20)

    @field_validator("equipe")
    @classmethod
    def equipe_optionnelle(cls, valeur: str | None) -> str | None:
        if valeur is None or not valeur:
            return None
        return _valider_nom_equipe(valeur)


class ParametresRencontre(ParametresFiltreChampionnatSaison):
    domicile: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)
    exterieur: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)

    @field_validator("domicile", "exterieur")
    @classmethod
    def equipes_valides(cls, valeur: str) -> str:
        return _valider_nom_equipe(valeur)

    @field_validator("exterieur")
    @classmethod
    def equipes_distinctes(cls, valeur: str, info) -> str:
        domicile = info.data.get("domicile")
        if domicile and valeur == domicile:
            raise ValueError("Les deux équipes doivent être différentes")
        return valeur


class ParametresAnalyseIa(ParametresRencontre):
    regerer: bool = False


class ParametresElo(BaseModel):
    model_config = _CONFIG_QUERY

    equipe: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)
    forcer: int = Field(default=0, ge=0, le=1)

    @field_validator("equipe")
    @classmethod
    def equipe_valide(cls, valeur: str) -> str:
        return _valider_nom_equipe(valeur)


class ParametresJoueur(BaseModel):
    model_config = _CONFIG_QUERY

    nom: str = Field(..., min_length=1, max_length=LONGUEUR_NOM_JOUEUR_MAX)
    championnat: str | None = Field(default=None, max_length=LONGUEUR_TEXTE_MATCH_MAX)

    @field_validator("championnat")
    @classmethod
    def championnat_optionnel(cls, valeur: str | None) -> str | None:
        if valeur is None or not valeur:
            return None
        return _valider_championnat(valeur)


class ParametresRecherche(BaseModel):
    model_config = _CONFIG_QUERY

    q: str = Field(..., min_length=2, max_length=LONGUEUR_RECHERCHE_MAX)


class ParametresMeilleurs(ParametresFiltreChampionnatSaison):
    type: Literal["buts", "passes", "dribbles"] = Field(..., alias="type")

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )


class ParametresStatsModele(BaseModel):
    model_config = _CONFIG_QUERY

    saison: str = Field(..., max_length=LONGUEUR_SAISON_MAX)
    championnat: str | None = Field(default=None, max_length=LONGUEUR_TEXTE_MATCH_MAX)
    inclure_retroactif: int = Field(default=0, ge=0, le=1)

    @field_validator("saison")
    @classmethod
    def saison_valide(cls, valeur: str) -> str:
        return _valider_saison(valeur)

    @field_validator("championnat")
    @classmethod
    def championnat_optionnel(cls, valeur: str | None) -> str | None:
        if valeur is None or not valeur:
            return None
        return _valider_championnat(valeur)


class ParametresMatchCommunaute(BaseModel):
    """Filtre match pour commentaires / pronostics / sondage-match."""

    model_config = _CONFIG_QUERY

    championnat: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)
    saison: str = Field(..., max_length=LONGUEUR_SAISON_MAX)
    domicile: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)
    exterieur: str = Field(..., max_length=LONGUEUR_TEXTE_MATCH_MAX)

    @field_validator("championnat", "domicile", "exterieur")
    @classmethod
    def texte_match(cls, valeur: str) -> str:
        return refuser_vide(valeur, "Paramètre match invalide")

    @field_validator("saison")
    @classmethod
    def saison_texte(cls, valeur: str) -> str:
        texte = refuser_vide(valeur, "Saison requise")
        if len(texte) > LONGUEUR_SAISON_MAX:
            raise ValueError("Saison invalide")
        return texte

    @field_validator("exterieur")
    @classmethod
    def equipes_distinctes(cls, valeur: str, info) -> str:
        domicile = info.data.get("domicile")
        if domicile and valeur == domicile:
            raise ValueError("Les deux équipes doivent être différentes")
        return valeur


class ParametresClassementCommunaute(ParametresFiltreChampionnatSaison):
    """Classement pronos communauté (championnats validés côté communaute)."""


class ParametresJourneePronos(ParametresFiltreChampionnatSaison):
    journee: str = Field(..., max_length=LONGUEUR_JOURNEE_MAX)

    @field_validator("journee")
    @classmethod
    def journee_valide(cls, valeur: str) -> str:
        return refuser_vide(valeur, "Journée requise")


class ParametresClassementLigue(ParametresFiltreChampionnatSaison):
    journee: str = Field(default="", max_length=LONGUEUR_JOURNEE_MAX)
