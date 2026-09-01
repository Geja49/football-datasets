"""Service métier — pronos weekend admin Solo."""

from __future__ import annotations

import math
import time
from datetime import date, datetime, timedelta
from threading import Lock

from analyse_rencontre import SEUIL_FORCE, _poisson
from modeles.commun import CHAMPIONNATS_VALIDES
from modeles.solo import (
    CornersMatch,
    GroupePronosChampionnat,
    MarcheQualifie,
    MatchPronoWeekend,
    ReponsePronosWeekend,
    SignalMatchPhysique,
    WeekendInfo,
)
from requetes.equipes import lire_site_equipe
from requetes.solo import lister_matchs_weekend_calendrier
from services.analyse import analyser_rencontre

# Badge « haute confiance » (affichage) — plus un filtre d'exclusion.
SEUIL_HAUTE_CONFIANCE = 85.0
# Alias conservé pour scripts / fige / tests.
SEUIL_PROBABILITE = SEUIL_HAUTE_CONFIANCE
# Badge « confiance ≥ 75 % » — mise en avant visuelle / tri.
SEUIL_MISE_EN_AVANT = 75.0
# Ancien seuil corners (probabilité) — conservé pour compatibilité imports.
SEUIL_CORNERS = 75.0
# Critères « potentiel » Solo (plus de filtre 85 % / 75 %).
SEUIL_CORNERS_POTENTIEL = 8.0
SEUIL_CORNERS_FORT = 9.0
SEUIL_BUTS_POTENTIEL = 2.0
SEUIL_BUTS_1_5 = 1.5
SEUIL_JAUNES_1_5 = 1.5
# Over corners affiché en priorité quand total prévu > 8.
LIGNE_CORNERS_OVER_8_5 = 8.5
LIGNE_CORNERS_OVER_9_5 = 9.5
# Écart max (points) pour proposer les deux victoires 1 et 2.
ECART_MAX_DEUX_VICTOIRES = 12.0
PROBA_MIN_DEUXIEME_VICTOIRE = 28.0
# Over 2.5 « utile » si la proba dépasse ce plancher (sinon xG total > 2).
SEUIL_OVER_25_UTILE = 50.0
# Over 1.5 buts / jaunes : plancher de proba pour afficher le potentiel.
SEUIL_OVER_15_UTILE = 55.0
SEUIL_OVER_EQUIPE_15_UTILE = 50.0
SEUIL_OVER_JAUNES_15_UTILE = 55.0

# Marchés cartons : conservés en BD / fige, masqués aux utilisateurs.
TYPES_MARCHES_CARTONS_API = frozenset({
    "cartons_jaunes",
    "cartons_over_1_5",
    "cartons_over_1_5_domicile",
    "cartons_over_1_5_exterieur",
})

MAX_MATCHS_WEEKEND = 80
DUREE_CACHE_SECONDES = 90

AVERTISSEMENT_SOLO = (
    "Scénarios statistiques recalculés en direct à partir des données en base. "
    "Ce n'est pas un conseil de paris sportifs."
)

_verrou_cache = Lock()
_cache_pronos: dict[tuple, tuple[float, dict]] = {}


def vendredi_weekend(reference: date | None = None) -> date:
    """Vendredi du weekend actif ou prochain (ven 00h → lun 23h59)."""
    ref = reference or date.today()
    wd = ref.weekday()
    if wd == 0:
        return ref - timedelta(days=3)
    if wd <= 3:
        return ref + timedelta(days=4 - wd)
    return ref - timedelta(days=wd - 4)


def plage_weekend(date_vendredi: date) -> tuple[date, date]:
    """Retourne (vendredi, lundi) à partir du vendredi de référence."""
    return date_vendredi, date_vendredi + timedelta(days=3)


def libelle_weekend(date_debut: date, date_fin: date) -> str:
    """Libellé court pour l'interface."""
    mois = (
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    )
    if date_debut.month == date_fin.month:
        return f"{date_debut.day}–{date_fin.day} {mois[date_fin.month - 1]} {date_fin.year}"
    return (
        f"{date_debut.day} {mois[date_debut.month - 1]} – "
        f"{date_fin.day} {mois[date_fin.month - 1]} {date_fin.year}"
    )


def _poisson_au_moins(k: int, lam: float) -> float:
    """P(X >= k) pour X ~ Poisson(lam)."""
    if k <= 0:
        return 1.0
    lam = max(0.01, lam)
    cumul = sum(_poisson(i, lam) for i in range(k))
    return max(0.0, min(1.0, 1.0 - cumul))


def est_marche_cartons_api(type_marche: str) -> bool:
    """True si le type correspond à un marché cartons (masqué utilisateur)."""
    return type_marche in TYPES_MARCHES_CARTONS_API


def filtrer_marches_pour_utilisateur(
    marches: list[MarcheQualifie],
) -> list[MarcheQualifie]:
    """Retire les marchés cartons de l'affichage (conservés en BD / fige)."""
    return [m for m in marches if not est_marche_cartons_api(m.type)]


def filtrer_reponse_pronos_utilisateur(
    reponse: ReponsePronosWeekend,
) -> ReponsePronosWeekend:
    """Masque les marchés cartons ; exclut les matchs sans autre marché ni corners."""
    pronos_filtres: list[MatchPronoWeekend] = []
    for match in reponse.pronos:
        marches = filtrer_marches_pour_utilisateur(match.marches)
        corners_ok = match.corners.disponible and match.corners.potentiel
        if not marches and not corners_ok:
            continue
        pronos_filtres.append(match.model_copy(update={"marches": marches}))
    _, groupes = grouper_pronos_par_championnat(pronos_filtres)
    return reponse.model_copy(
        update={
            "pronos": pronos_filtres,
            "pronos_par_championnat": groupes,
            "nb_matchs_avec_prono": len(pronos_filtres),
        }
    )


def _haute_confiance(proba: float | None) -> bool:
    return proba is not None and float(proba) >= SEUIL_HAUTE_CONFIANCE


def _mise_en_avant(proba: float | None) -> bool:
    """True si proba ≥ 75 % (inclut la haute confiance ≥ 85 %)."""
    return proba is not None and float(proba) >= SEUIL_MISE_EN_AVANT


def _cle_tri_marche(marche: MarcheQualifie) -> tuple:
    """Marchés ≥ 75 % d'abord, haute confiance (≥ 85 %) en tête, puis proba."""
    proba = float(marche.probabilite or 0.0)
    if marche.haute_confiance or proba >= SEUIL_HAUTE_CONFIANCE:
        niveau = 2
    elif marche.mise_en_avant or proba >= SEUIL_MISE_EN_AVANT:
        niveau = 1
    else:
        niveau = 0
    return (-niveau, -proba)


def _ajouter_victoires(
    marches: list[MarcheQualifie],
    prediction: dict,
    domicile: str,
    exterieur: str,
) -> None:
    """Toujours l'issue 1/2 la plus probable ; les deux si match ouvert."""
    p_dom = prediction.get("p_victoire_domicile")
    p_ext = prediction.get("p_victoire_exterieur")
    if p_dom is None and p_ext is None:
        return

    val_dom = float(p_dom) if p_dom is not None else -1.0
    val_ext = float(p_ext) if p_ext is not None else -1.0

    def _marche_dom() -> MarcheQualifie:
        return MarcheQualifie(
            type="victoire_domicile",
            libelle=f"Victoire {domicile}",
            probabilite=float(p_dom),
            haute_confiance=_haute_confiance(p_dom),
            mise_en_avant=_mise_en_avant(p_dom),
        )

    def _marche_ext() -> MarcheQualifie:
        return MarcheQualifie(
            type="victoire_exterieur",
            libelle=f"Victoire {exterieur}",
            probabilite=float(p_ext),
            haute_confiance=_haute_confiance(p_ext),
            mise_en_avant=_mise_en_avant(p_ext),
        )

    if val_dom >= val_ext and p_dom is not None:
        marches.append(_marche_dom())
        if (
            p_ext is not None
            and val_ext >= PROBA_MIN_DEUXIEME_VICTOIRE
            and (val_dom - val_ext) <= ECART_MAX_DEUX_VICTOIRES
        ):
            marches.append(_marche_ext())
    elif p_ext is not None:
        marches.append(_marche_ext())
        if (
            p_dom is not None
            and val_dom >= PROBA_MIN_DEUXIEME_VICTOIRE
            and (val_ext - val_dom) <= ECART_MAX_DEUX_VICTOIRES
        ):
            marches.append(_marche_dom())


def _potentiel_plus_de_2_buts(prediction: dict) -> bool:
    """True si xG/buts prévus > 2 ou proba over 2.5 utile (> 50 %)."""
    xg_total = prediction.get("xg_total")
    if xg_total is not None and float(xg_total) > SEUIL_BUTS_POTENTIEL:
        return True
    p_o25 = prediction.get("p_plus_de_2_buts")
    if p_o25 is not None and float(p_o25) > SEUIL_OVER_25_UTILE:
        return True
    return False


def _proba_over_1_5_buts(prediction: dict) -> float | None:
    """P(total buts ≥ 2) via Poisson (xG domicile + extérieur)."""
    lam_d = prediction.get("xg_prevu_domicile")
    lam_e = prediction.get("xg_prevu_exterieur")
    if lam_d is None and lam_e is None:
        xg = prediction.get("xg_total")
        if xg is None:
            return None
        return round(100 * _poisson_au_moins(2, float(xg)), 1)
    total = float(lam_d or 0) + float(lam_e or 0)
    return round(100 * _poisson_au_moins(2, total), 1)


def _potentiel_plus_de_1_5_buts(prediction: dict, proba_o15: float | None) -> bool:
    xg_total = prediction.get("xg_total")
    if xg_total is not None and float(xg_total) > SEUIL_BUTS_1_5:
        return True
    if proba_o15 is not None and float(proba_o15) >= SEUIL_OVER_15_UTILE:
        return True
    return False


def _potentiel_equipe_1_5(lam: float | None, proba: float | None) -> bool:
    if lam is not None and float(lam) > SEUIL_BUTS_1_5:
        return True
    if proba is not None and float(proba) >= SEUIL_OVER_EQUIPE_15_UTILE:
        return True
    return False


def _ajouter_marches_buts_1_5(
    marches: list[MarcheQualifie],
    prediction: dict,
    domicile: str,
    exterieur: str,
) -> float | None:
    """Over 1.5 match + équipes susceptibles de marquer +1.5."""
    proba_match = _proba_over_1_5_buts(prediction)
    if _potentiel_plus_de_1_5_buts(prediction, proba_match) and proba_match is not None:
        xg = prediction.get("xg_total")
        detail = f"Total buts prévu ≈ {float(xg):.1f}" if xg is not None else None
        marches.append(
            MarcheQualifie(
                type="over_1_5",
                libelle="Plus de 1,5 buts",
                probabilite=float(proba_match),
                haute_confiance=_haute_confiance(proba_match),
                mise_en_avant=_mise_en_avant(proba_match),
                detail=detail,
            )
        )

    lam_d = prediction.get("xg_prevu_domicile")
    lam_e = prediction.get("xg_prevu_exterieur")
    if lam_d is not None:
        proba_d = round(100 * _poisson_au_moins(2, float(lam_d)), 1)
        if _potentiel_equipe_1_5(float(lam_d), proba_d):
            marches.append(
                MarcheQualifie(
                    type="over_1_5_domicile",
                    libelle=f"{domicile} marque +1,5",
                    probabilite=proba_d,
                    haute_confiance=_haute_confiance(proba_d),
                    mise_en_avant=_mise_en_avant(proba_d),
                    detail=f"Buts prévus ≈ {float(lam_d):.1f}",
                )
            )
    if lam_e is not None:
        proba_e = round(100 * _poisson_au_moins(2, float(lam_e)), 1)
        if _potentiel_equipe_1_5(float(lam_e), proba_e):
            marches.append(
                MarcheQualifie(
                    type="over_1_5_exterieur",
                    libelle=f"{exterieur} marque +1,5",
                    probabilite=proba_e,
                    haute_confiance=_haute_confiance(proba_e),
                    mise_en_avant=_mise_en_avant(proba_e),
                    detail=f"Buts prévus ≈ {float(lam_e):.1f}",
                )
            )
    return proba_match


def _ajouter_marches_jaunes_1_5(
    marches: list[MarcheQualifie],
    cartons: dict,
    domicile: str,
    exterieur: str,
) -> None:
    """Over 1.5 cartons jaunes match + équipes susceptibles."""
    jaunes_match = cartons.get("jaunes_match")
    if jaunes_match is not None:
        proba = round(100 * _poisson_au_moins(2, float(jaunes_match)), 1)
        if float(jaunes_match) > SEUIL_JAUNES_1_5 or proba >= SEUIL_OVER_JAUNES_15_UTILE:
            marches.append(
                MarcheQualifie(
                    type="cartons_over_1_5",
                    libelle="Plus de 1,5 cartons jaunes",
                    probabilite=proba,
                    haute_confiance=_haute_confiance(proba),
                    mise_en_avant=_mise_en_avant(proba),
                    detail=f"Jaunes prévus ≈ {float(jaunes_match):.1f}",
                )
            )

    j_dom = cartons.get("jaunes_domicile")
    if j_dom is not None:
        proba_d = round(100 * _poisson_au_moins(2, float(j_dom)), 1)
        if float(j_dom) > SEUIL_JAUNES_1_5 or proba_d >= SEUIL_OVER_EQUIPE_15_UTILE:
            marches.append(
                MarcheQualifie(
                    type="cartons_over_1_5_domicile",
                    libelle=f"{domicile} +1,5 carton jaune",
                    probabilite=proba_d,
                    haute_confiance=_haute_confiance(proba_d),
                    mise_en_avant=_mise_en_avant(proba_d),
                    detail=f"Jaunes prévus ≈ {float(j_dom):.1f}",
                )
            )

    j_ext = cartons.get("jaunes_exterieur")
    if j_ext is not None:
        proba_e = round(100 * _poisson_au_moins(2, float(j_ext)), 1)
        if float(j_ext) > SEUIL_JAUNES_1_5 or proba_e >= SEUIL_OVER_EQUIPE_15_UTILE:
            marches.append(
                MarcheQualifie(
                    type="cartons_over_1_5_exterieur",
                    libelle=f"{exterieur} +1,5 carton jaune",
                    probabilite=proba_e,
                    haute_confiance=_haute_confiance(proba_e),
                    mise_en_avant=_mise_en_avant(proba_e),
                    detail=f"Jaunes prévus ≈ {float(j_ext):.1f}",
                )
            )


def extraire_marches_qualifies(
    prediction: dict,
    domicile: str,
    exterieur: str,
    seuil: float = SEUIL_HAUTE_CONFIANCE,
) -> list[MarcheQualifie]:
    """
    Marchés Solo sans filtre d'exclusion 85 % sur victoire / buts / jaunes 1.5.

    - Victoire : issue 1 ou 2 la plus probable (les deux si sensé).
    - Buts : over 1.5 (match + équipes) et over 2.5 si potentiel.
    - Cartons : over 1.5 (match + équipes) ; ligne haute confiance séparée.
    - BTTS : uniquement en haute confiance (≥ seuil).
    """
    marches: list[MarcheQualifie] = []

    _ajouter_victoires(marches, prediction, domicile, exterieur)

    p_btts = prediction.get("p_les_deux_marquent")
    if p_btts is not None and float(p_btts) >= seuil:
        marches.append(
            MarcheQualifie(
                type="btts",
                libelle="Les deux équipes marquent",
                probabilite=float(p_btts),
                haute_confiance=True,
                mise_en_avant=True,
            )
        )

    _ajouter_marches_buts_1_5(marches, prediction, domicile, exterieur)

    p_o25 = prediction.get("p_plus_de_2_buts")
    if p_o25 is not None and _potentiel_plus_de_2_buts(prediction):
        xg = prediction.get("xg_total")
        detail = None
        if xg is not None:
            detail = f"Total buts prévu ≈ {float(xg):.1f}"
        marches.append(
            MarcheQualifie(
                type="over_2_5",
                libelle="Plus de 2,5 buts",
                probabilite=float(p_o25),
                haute_confiance=_haute_confiance(p_o25),
                mise_en_avant=_mise_en_avant(p_o25),
                detail=detail,
            )
        )

    cartons = prediction.get("cartons") or {}
    _ajouter_marches_jaunes_1_5(marches, cartons, domicile, exterieur)
    marche_cartons = _marche_cartons(cartons, seuil)
    if marche_cartons:
        marches.append(marche_cartons)

    marches.sort(key=_cle_tri_marche)
    return marches


def _marche_cartons(cartons: dict, seuil: float) -> MarcheQualifie | None:
    """Cartons jaunes : probabilité Poisson ou signal fort « match cartonné »."""
    jaunes = cartons.get("jaunes_match")
    if jaunes is None:
        return None
    moy = cartons.get("moyenne_championnat") or jaunes
    seuil_cartons = max(1, math.ceil(float(moy) * SEUIL_FORCE))
    proba = round(100 * _poisson_au_moins(seuil_cartons, float(jaunes)), 1)
    signal_fort = cartons.get("rythme") == "cartonne"
    if proba < seuil and not signal_fort:
        return None
    libelle = (
        f"Plus de {seuil_cartons - 1} cartons jaunes"
        if seuil_cartons > 1
        else "Cartons jaunes élevés"
    )
    proba_affichee = proba if proba >= seuil else None
    return MarcheQualifie(
        type="cartons_jaunes",
        libelle=libelle,
        probabilite=proba_affichee,
        signal_fort=signal_fort,
        haute_confiance=_haute_confiance(proba_affichee),
        mise_en_avant=_mise_en_avant(proba_affichee),
        detail=cartons.get("texte"),
    )


def _info_corners(prediction: dict) -> CornersMatch:
    """
    Corners : potentiel si total prévu > 8, fort si > 9.
    Affiche le total prévu + proba over 8.5 (prioritaire) ou 9.5.
    """
    corners = prediction.get("corners") or {}
    total = corners.get("corners_match")
    if total is None:
        return CornersMatch(disponible=False, message="non disponible")

    total_f = float(total)
    potentiel = total_f > SEUIL_CORNERS_POTENTIEL
    fort = total_f > SEUIL_CORNERS_FORT
    p_over_9_5 = corners.get("p_corners_total_over")
    if p_over_9_5 is not None:
        p_over_9_5 = float(p_over_9_5)
    else:
        p_over_9_5 = round(100 * _poisson_au_moins(10, total_f), 1)

    p_over_8_5 = round(100 * _poisson_au_moins(9, total_f), 1)

    # Ligne affichée : 8.5 dès que potentiel > 8, sinon 9.5 si dispo.
    if potentiel:
        ligne = LIGNE_CORNERS_OVER_8_5
        probabilite = p_over_8_5
    else:
        ligne = LIGNE_CORNERS_OVER_9_5
        probabilite = p_over_9_5

    detail = corners.get("texte")
    if not detail:
        detail = f"Environ {total_f:.1f} corners prévus au total."

    return CornersMatch(
        disponible=True,
        probabilite=probabilite,
        total_prevu=total_f,
        ligne_over=ligne,
        detail=detail,
        potentiel=potentiel,
        fort=fort,
        haute_confiance=_haute_confiance(probabilite),
        mise_en_avant=_mise_en_avant(probabilite),
        message=None if potentiel else corners.get("titre"),
    )


def _signal_match_physique(prediction: dict) -> SignalMatchPhysique:
    """Actif si fautes « physique » ou cartons « cartonné »."""
    fautes = prediction.get("fautes") or {}
    cartons = prediction.get("cartons") or {}
    physique_fautes = fautes.get("rythme") == "physique"
    physique_cartons = cartons.get("rythme") == "cartonne"
    if not physique_fautes and not physique_cartons:
        return SignalMatchPhysique(actif=False)
    parties = []
    if physique_fautes and fautes.get("fautes_match") is not None:
        parties.append(f"environ {fautes['fautes_match']} fautes")
    if physique_cartons and cartons.get("jaunes_match") is not None:
        parties.append(f"environ {cartons['jaunes_match']} jaunes")
    detail = "Match physique"
    if parties:
        detail += " : " + ", ".join(parties)
    return SignalMatchPhysique(actif=True, detail=detail)


def _cle_cache(date_debut: str, date_fin: str, championnat: str | None) -> tuple:
    return (date_debut, date_fin, championnat or "")


def _indice_championnat(nom: str) -> int:
    """Ordre d'affichage (PL, La Liga, …, LDC)."""
    try:
        return CHAMPIONNATS_VALIDES.index(nom)
    except ValueError:
        return len(CHAMPIONNATS_VALIDES)


def _cle_tri_match(match: MatchPronoWeekend) -> tuple:
    """Tri intra-groupe : fort corners d’abord, puis potentiel, puis date/heure."""
    corners = match.corners
    priorite_fort = 0
    priorite_potentiel = 0
    if corners and corners.disponible:
        if corners.fort or (
            corners.total_prevu is not None
            and float(corners.total_prevu) > SEUIL_CORNERS_FORT
        ):
            priorite_fort = 1
        if corners.potentiel:
            priorite_potentiel = 1
    return (-priorite_fort, -priorite_potentiel, match.date, match.heure or "")


def grouper_pronos_par_championnat(
    resultats: list[MatchPronoWeekend],
) -> tuple[list[MatchPronoWeekend], list[GroupePronosChampionnat]]:
    """Groupe par championnat (ordre canonique) ; matchs triés par date/heure."""
    par_champ: dict[str, list[MatchPronoWeekend]] = {}
    for match in resultats:
        par_champ.setdefault(match.championnat, []).append(match)

    groupes: list[GroupePronosChampionnat] = []
    pronos_plats: list[MatchPronoWeekend] = []

    noms_ordres = sorted(par_champ.keys(), key=_indice_championnat)
    for nom in noms_ordres:
        matchs = sorted(par_champ[nom], key=_cle_tri_match)
        groupes.append(GroupePronosChampionnat(championnat=nom, pronos=matchs))
        pronos_plats.extend(matchs)

    return pronos_plats, groupes


def _reparer_cache_pronos(payload: dict) -> dict:
    """Reconstruit pronos_par_championnat si le cache est incomplet."""
    groupes = payload.get("pronos_par_championnat") or []
    pronos = payload.get("pronos") or []
    if groupes or not pronos:
        return payload
    _, groupes_reconstruits = grouper_pronos_par_championnat(
        [MatchPronoWeekend(**match) for match in pronos]
    )
    payload = dict(payload)
    payload["pronos_par_championnat"] = [
        groupe.model_dump() for groupe in groupes_reconstruits
    ]
    if not payload.get("nb_matchs_avec_prono"):
        payload["nb_matchs_avec_prono"] = len(pronos)
    return payload


def _lire_cache(cle: tuple) -> dict | None:
    with _verrou_cache:
        entree = _cache_pronos.get(cle)
        if not entree:
            return None
        expire, payload = entree
        if time.monotonic() > expire:
            _cache_pronos.pop(cle, None)
            return None
        return payload


def _ecrire_cache(cle: tuple, payload: dict) -> None:
    with _verrou_cache:
        _cache_pronos[cle] = (time.monotonic() + DUREE_CACHE_SECONDES, payload)
        if len(_cache_pronos) > 20:
            maintenant = time.monotonic()
            expirees = [k for k, (exp, _) in _cache_pronos.items() if exp < maintenant]
            for k in expirees:
                _cache_pronos.pop(k, None)


def vider_cache_solo() -> None:
    """Utilitaire tests — vide le cache mémoire."""
    with _verrou_cache:
        _cache_pronos.clear()


def enrichir_logos_pronos(connexion, reponse: ReponsePronosWeekend) -> ReponsePronosWeekend:
    """Ajoute les blasons équipes (sites_equipes) si disponibles."""
    cache: dict[str, str | None] = {}

    def logo(nom: str) -> str | None:
        if nom not in cache:
            site = lire_site_equipe(connexion, nom)
            url = (site or {}).get("url_logo") or ""
            cache[nom] = url.strip() or None
        return cache[nom]

    for match in reponse.pronos:
        match.url_logo_domicile = logo(match.domicile)
        match.url_logo_exterieur = logo(match.exterieur)
    for groupe in reponse.pronos_par_championnat:
        for match in groupe.pronos:
            match.url_logo_domicile = logo(match.domicile)
            match.url_logo_exterieur = logo(match.exterieur)
    return reponse


def construire_pronos_weekend(
    connexion,
    date_debut: str | None = None,
    championnat: str | None = None,
) -> ReponsePronosWeekend:
    """Analyse live : victoires, buts (potentiel > 2) et corners (total > 8)."""
    if date_debut:
        vendredi = datetime.strptime(date_debut, "%Y-%m-%d").date()
    else:
        vendredi = vendredi_weekend()
    debut, fin = plage_weekend(vendredi)
    debut_iso = debut.isoformat()
    fin_iso = fin.isoformat()

    cle = _cle_cache(debut_iso, fin_iso, championnat)
    cache = _lire_cache(cle)
    if cache:
        cache = _reparer_cache_pronos(cache)
        return enrichir_logos_pronos(connexion, ReponsePronosWeekend(**cache))

    lignes = lister_matchs_weekend_calendrier(
        connexion,
        debut_iso,
        fin_iso,
        championnat=championnat,
        limite=MAX_MATCHS_WEEKEND,
    )

    resultats: list[MatchPronoWeekend] = []
    for ligne in lignes:
        try:
            analyse = analyser_rencontre(
                connexion,
                ligne["championnat"],
                ligne["saison"],
                ligne["domicile"],
                ligne["exterieur"],
            )
        except ValueError:
            continue
        pred = analyse.get("prediction") or {}
        marches = extraire_marches_qualifies(
            pred,
            ligne["domicile"],
            ligne["exterieur"],
        )
        corners = _info_corners(pred)
        # Afficher si marché retenu OU potentiel corners > 8.
        if not marches and not (corners.disponible and corners.potentiel):
            continue
        xg = pred.get("xg_total")
        p_o25 = pred.get("p_plus_de_2_buts")
        p_o15 = _proba_over_1_5_buts(pred)
        resultats.append(
            MatchPronoWeekend(
                championnat=ligne["championnat"],
                saison=ligne["saison"],
                date=ligne["date"],
                heure=ligne.get("heure") or None,
                journee=ligne.get("journee") or None,
                domicile=ligne["domicile"],
                exterieur=ligne["exterieur"],
                score_modal=pred.get("score_plus_probable"),
                buts_prevus_total=float(xg) if xg is not None else None,
                proba_over_1_5=float(p_o15) if p_o15 is not None else None,
                proba_over_2_5=float(p_o25) if p_o25 is not None else None,
                marches=marches,
                corners=corners,
                match_physique=_signal_match_physique(pred),
            )
        )

    pronos_plats, groupes = grouper_pronos_par_championnat(resultats)

    reponse = ReponsePronosWeekend(
        avertissement=AVERTISSEMENT_SOLO,
        weekend=WeekendInfo(
            date_debut=debut_iso,
            date_fin=fin_iso,
            libelle=libelle_weekend(debut, fin),
        ),
        seuil_probabilite=SEUIL_HAUTE_CONFIANCE,
        seuil_mise_en_avant=SEUIL_MISE_EN_AVANT,
        nb_matchs_analyses=len(lignes),
        nb_matchs_avec_prono=len(resultats),
        pronos=pronos_plats,
        pronos_par_championnat=groupes,
    )
    enrichir_logos_pronos(connexion, reponse)
    _ecrire_cache(cle, reponse.model_dump())
    return reponse


def championnats_solo() -> tuple[str, ...]:
    """Compétitions couvertes par Solo."""
    return CHAMPIONNATS_VALIDES
