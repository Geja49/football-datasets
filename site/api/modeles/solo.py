"""Modèles Pydantic — page admin Solo (pronos weekend)."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from modeles.commun import CHAMPIONNATS_VALIDES, refuser_vide

_CONFIG_QUERY = ConfigDict(extra="forbid", str_strip_whitespace=True)
MOTIF_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ParametresPronosWeekend(BaseModel):
    """Query GET /api/solo/pronos-weekend."""

    model_config = _CONFIG_QUERY

    date_debut: str | None = Field(
        default=None,
        description="Vendredi du weekend (YYYY-MM-DD). Défaut : prochain ven–lun.",
    )
    championnat: str | None = Field(
        default=None,
        max_length=80,
        description="Filtrer sur une compétition (Big 5, Super Lig, LDC).",
    )

    @field_validator("date_debut")
    @classmethod
    def date_debut_valide(cls, valeur: str | None) -> str | None:
        if valeur is None or not valeur:
            return None
        texte = valeur.strip()
        if not MOTIF_DATE.match(texte):
            raise ValueError("date_debut invalide (format YYYY-MM-DD attendu)")
        return texte

    @field_validator("championnat")
    @classmethod
    def championnat_optionnel(cls, valeur: str | None) -> str | None:
        if valeur is None or not valeur:
            return None
        texte = refuser_vide(valeur, "Championnat invalide")
        if texte not in CHAMPIONNATS_VALIDES:
            raise ValueError("Championnat inconnu")
        return texte


class VerdictMarche(BaseModel):
    """Verdict post-match d'un marché Solo figé."""

    vrai: bool
    motif_code: str | None = None
    motif_texte: str | None = None
    buts_domicile: int | None = None
    buts_exterieur: int | None = None
    juge_le: str | None = None


class MarcheQualifie(BaseModel):
    """Marché retenu pour un match (seuil ≥ 85 % ou signal cartons)."""

    type: Literal[
        "victoire_domicile",
        "victoire_exterieur",
        "btts",
        "over_2_5",
        "cartons_jaunes",
    ]
    libelle: str
    probabilite: float | None = None
    signal_fort: bool = False
    detail: str | None = None
    verdict: VerdictMarche | None = None


class CornersMatch(BaseModel):
    """Corners — prévision Poisson (total attendu, signal élevé)."""

    disponible: bool
    message: str | None = None
    probabilite: float | None = None
    detail: str | None = None
    verdict: VerdictMarche | None = None


class SignalMatchPhysique(BaseModel):
    """Signal Solo : fautes et/ou cartons élevés (match physique)."""

    actif: bool = False
    detail: str | None = None


class MatchPronoWeekend(BaseModel):
    """Match analysé avec ses marchés qualifiés."""

    championnat: str
    saison: str
    date: str
    heure: str | None = None
    journee: str | None = None
    domicile: str
    exterieur: str
    score_modal: str | None = None
    marches: list[MarcheQualifie]
    corners: CornersMatch
    match_physique: SignalMatchPhysique = Field(
        default_factory=SignalMatchPhysique
    )


class GroupePronosChampionnat(BaseModel):
    """Pronos d'un championnat pour le weekend."""

    championnat: str
    pronos: list[MatchPronoWeekend]


class WeekendInfo(BaseModel):
    """Plage ven 00h → lun 23h59."""

    date_debut: str
    date_fin: str
    libelle: str


class ReponsePronosWeekend(BaseModel):
    """Réponse GET /api/solo/pronos-weekend."""

    avertissement: str
    weekend: WeekendInfo
    seuil_probabilite: float
    nb_matchs_analyses: int
    nb_matchs_avec_prono: int
    pronos: list[MatchPronoWeekend]
    pronos_par_championnat: list[GroupePronosChampionnat]
    source: Literal["live", "fige"] = "live"
    fige_le: str | None = None


class StatHitRate(BaseModel):
    """Compteurs et taux de réussite."""

    vrais: int
    total: int
    hit_rate: float | None = None


class DetailVerdictSolo(BaseModel):
    """Ligne de bilan (un marché jugé)."""

    championnat: str
    date_match: str
    domicile: str
    exterieur: str
    type_marche: str
    libelle_marche: str | None = None
    probabilite: float
    vrai: bool
    motif_code: str | None = None
    motif_texte: str | None = None
    buts_domicile: int | None = None
    buts_exterieur: int | None = None


class ReponseBilanSolo(BaseModel):
    """Réponse GET /api/solo/bilan-weekend."""

    weekend: WeekendInfo
    fige_le: str | None = None
    nb_pronos: int
    nb_juges: int
    nb_vrais: int
    nb_faux: int
    hit_rate: float | None = None
    par_marche: dict[str, StatHitRate]
    par_championnat: dict[str, StatHitRate]
    details: list[DetailVerdictSolo]
