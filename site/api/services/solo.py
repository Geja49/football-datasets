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
from requetes.solo import lister_matchs_weekend_calendrier
from services.analyse import analyser_rencontre

SEUIL_PROBABILITE = 85.0
SEUIL_CORNERS = 75.0
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


def extraire_marches_qualifies(
    prediction: dict,
    domicile: str,
    exterieur: str,
    seuil: float = SEUIL_PROBABILITE,
) -> list[MarcheQualifie]:
    """Extrait les marchés ≥ seuil % (1X2 victoire, BTTS, over 2.5, cartons)."""
    marches: list[MarcheQualifie] = []

    p_dom = prediction.get("p_victoire_domicile")
    if p_dom is not None and p_dom >= seuil:
        marches.append(
            MarcheQualifie(
                type="victoire_domicile",
                libelle=f"Victoire {domicile}",
                probabilite=float(p_dom),
            )
        )

    p_ext = prediction.get("p_victoire_exterieur")
    if p_ext is not None and p_ext >= seuil:
        marches.append(
            MarcheQualifie(
                type="victoire_exterieur",
                libelle=f"Victoire {exterieur}",
                probabilite=float(p_ext),
            )
        )

    p_btts = prediction.get("p_les_deux_marquent")
    if p_btts is not None and p_btts >= seuil:
        marches.append(
            MarcheQualifie(
                type="btts",
                libelle="Les deux équipes marquent",
                probabilite=float(p_btts),
            )
        )

    p_o25 = prediction.get("p_plus_de_2_buts")
    if p_o25 is not None and p_o25 >= seuil:
        marches.append(
            MarcheQualifie(
                type="over_2_5",
                libelle="Plus de 2,5 buts",
                probabilite=float(p_o25),
            )
        )

    cartons = prediction.get("cartons") or {}
    marche_cartons = _marche_cartons(cartons, seuil)
    if marche_cartons:
        marches.append(marche_cartons)

    marches.sort(key=lambda m: m.probabilite or 0.0, reverse=True)
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
    return MarcheQualifie(
        type="cartons_jaunes",
        libelle=libelle,
        probabilite=proba if proba >= seuil else None,
        signal_fort=signal_fort,
        detail=cartons.get("texte"),
    )


def _info_corners(prediction: dict) -> CornersMatch:
    """Corners prévus : signal élevé ou probabilité over 9.5 si ≥ SEUIL_CORNERS %."""
    corners = prediction.get("corners") or {}
    total = corners.get("corners_match")
    if total is None:
        return CornersMatch(disponible=False, message="non disponible")

    moy = corners.get("moyenne_championnat") or total
    seuil_eleve = max(1, math.ceil(float(moy) * SEUIL_FORCE))
    proba_eleve = round(
        100 * _poisson_au_moins(seuil_eleve, float(total)), 1
    )
    p_over = corners.get("p_corners_total_over")
    signal_fort = corners.get("rythme") == "eleve"

    probabilite = None
    if p_over is not None and float(p_over) >= SEUIL_CORNERS:
        probabilite = float(p_over)
    elif proba_eleve >= SEUIL_CORNERS:
        probabilite = proba_eleve

    return CornersMatch(
        disponible=True,
        probabilite=probabilite,
        detail=corners.get("texte"),
        message=None if probabilite or signal_fort else corners.get("titre"),
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


def _cle_tri_match(match: MatchPronoWeekend) -> tuple[str, str]:
    """Tri intra-groupe : date puis heure."""
    return (match.date, match.heure or "")


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


def construire_pronos_weekend(
    connexion,
    date_debut: str | None = None,
    championnat: str | None = None,
) -> ReponsePronosWeekend:
    """Analyse live des matchs du weekend et retourne les pronos ≥ 85 %."""
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
        return ReponsePronosWeekend(**cache)

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
        if not marches:
            continue
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
                marches=marches,
                corners=_info_corners(pred),
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
        seuil_probabilite=SEUIL_PROBABILITE,
        nb_matchs_analyses=len(lignes),
        nb_matchs_avec_prono=len(resultats),
        pronos=pronos_plats,
        pronos_par_championnat=groupes,
    )
    _ecrire_cache(cle, reponse.model_dump())
    return reponse


def championnats_solo() -> tuple[str, ...]:
    """Compétitions couvertes par Solo."""
    return CHAMPIONNATS_VALIDES
