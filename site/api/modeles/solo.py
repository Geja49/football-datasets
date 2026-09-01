"""Modèles Pydantic — page Solo (pronos weekend)."""

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
    """Marché Solo (victoire / buts / cartons / BTTS)."""

    type: Literal[
        "victoire_domicile",
        "victoire_exterieur",
        "btts",
        "over_1_5",
        "over_1_5_domicile",
        "over_1_5_exterieur",
        "over_2_5",
        "cartons_jaunes",
        "cartons_over_1_5",
        "cartons_over_1_5_domicile",
        "cartons_over_1_5_exterieur",
    ]
    libelle: str
    probabilite: float | None = None
    signal_fort: bool = False
    haute_confiance: bool = False
    mise_en_avant: bool = False
    detail: str | None = None
    verdict: VerdictMarche | None = None


class CornersMatch(BaseModel):
    """Corners — total prévu ; potentiel si total > 8 ; fort si > 9."""

    disponible: bool
    message: str | None = None
    probabilite: float | None = None
    total_prevu: float | None = None
    ligne_over: float | None = None
    potentiel: bool = False
    fort: bool = False
    haute_confiance: bool = False
    mise_en_avant: bool = False
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
    url_logo_domicile: str | None = None
    url_logo_exterieur: str | None = None
    score_modal: str | None = None
    # Affiche compacte : potentiel buts (xG total + proba over 1.5 / 2.5).
    buts_prevus_total: float | None = None
    proba_over_1_5: float | None = None
    proba_over_2_5: float | None = None
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
    seuil_mise_en_avant: float = 75.0
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


class ParametresBilanPronos(ParametresPronosWeekend):
    """Query GET /api/solo/bilan-pronos (écarts ≥ seuil)."""

    proba_min: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Probabilité minimale prédite (défaut serveur : 70).",
    )


class ReponseBilanSolo(BaseModel):
    """Réponse GET /api/solo/bilan-weekend et /api/solo/bilan-pronos."""

    weekend: WeekendInfo
    fige_le: str | None = None
    seuil_probabilite: float | None = None
    nb_pronos: int
    nb_juges: int
    nb_vrais: int
    nb_faux: int
    hit_rate: float | None = None
    par_marche: dict[str, StatHitRate]
    par_championnat: dict[str, StatHitRate]
    details: list[DetailVerdictSolo]
