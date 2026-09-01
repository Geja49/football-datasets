"""Service — figer les pronos Solo avant le weekend et juger après."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone

from historique_analyses import cle_match, ouvrir_base as ouvrir_analyses
from modeles.solo import (
    CornersMatch,
    DetailVerdictSolo,
    MarcheQualifie,
    MatchPronoWeekend,
    ReponseBilanSolo,
    ReponsePronosWeekend,
    StatHitRate,
    VerdictMarche,
    WeekendInfo,
)
from requetes.solo import (
    compter_pronos_solo_weekend,
    date_fige_weekend,
    inserer_prono_solo,
    inserer_verdict_solo,
    lire_score_match_football,
    lister_pronos_solo_sans_verdict,
    lister_pronos_solo_weekend,
)
from services.solo import (
    AVERTISSEMENT_SOLO,
    LIGNE_CORNERS_OVER_8_5,
    SEUIL_CORNERS_FORT,
    SEUIL_HAUTE_CONFIANCE,
    SEUIL_MISE_EN_AVANT,
    SEUIL_PROBABILITE,
    _cle_tri_marche,
    construire_pronos_weekend,
    enrichir_logos_pronos,
    filtrer_reponse_pronos_utilisateur,
    grouper_pronos_par_championnat,
    libelle_weekend,
    plage_weekend,
    vendredi_weekend,
)

# Types stockés en analyses.db (schéma Phase 1).
TYPE_VERS_API = {
    "victoire_1": "victoire_domicile",
    "victoire_2": "victoire_exterieur",
    "btts": "btts",
    "over_15": "over_1_5",
    "over_15_dom": "over_1_5_domicile",
    "over_15_ext": "over_1_5_exterieur",
    "over_25": "over_2_5",
    "cartons": "cartons_jaunes",
    "cartons_15": "cartons_over_1_5",
    "cartons_15_dom": "cartons_over_1_5_domicile",
    "cartons_15_ext": "cartons_over_1_5_exterieur",
}
TYPE_DEPUIS_API = {v: k for k, v in TYPE_VERS_API.items()}
TYPE_CORNERS = "corners_over_95"

# Types BD cartons : conservés pour calibration, exclus du bilan utilisateur.
TYPES_MARCHES_CARTONS_BD = frozenset({
    "cartons",
    "cartons_15",
    "cartons_15_dom",
    "cartons_15_ext",
})

SEUIL_CARTONS_DEFAUT = 4
# Seuil page bilan écarts : ne garder que les marchés figés ≥ 70 %.
SEUIL_BILAN_PRONOS = 70.0


def _maintenant_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _weekend_iso(date_debut: str | None) -> str:
    if date_debut:
        return date_debut[:10]
    return vendredi_weekend().isoformat()


def weekend_est_fige(
    weekend_debut: str,
    championnat: str | None = None,
    chemin_analyses=None,
) -> bool:
    """True si au moins un marché Solo est figé pour ce weekend."""
    connexion = ouvrir_analyses(chemin_analyses)
    try:
        return compter_pronos_solo_weekend(connexion, weekend_debut, championnat) > 0
    finally:
        connexion.close()


def figer_pronos_weekend(
    connexion_foot,
    *,
    date_debut: str | None = None,
    championnat: str | None = None,
    forcer: bool = False,
    chemin_analyses=None,
) -> dict:
    """
    Snapshot des marchés Solo (mêmes critères que la page live) dans analyses.db.
    Victoire / buts potentiel / corners total prévu > 8 — pas de filtre 85 % / 75 %.
    """
    weekend = _weekend_iso(date_debut)
    reponse = construire_pronos_weekend(
        connexion_foot,
        date_debut=weekend,
        championnat=championnat,
    )
    fige_le = _maintenant_iso()
    nb_figes = 0
    nb_ignores = 0

    connexion_analyses = ouvrir_analyses(chemin_analyses)
    try:
        for match in reponse.pronos:
            cle = cle_match(
                match.championnat,
                match.saison,
                match.date,
                match.domicile,
                match.exterieur,
            )
            for marche in match.marches:
                type_db = TYPE_DEPUIS_API.get(marche.type)
                if not type_db:
                    continue
                proba = float(marche.probabilite) if marche.probabilite is not None else 0.0
                if marche.type == "cartons_jaunes" and marche.signal_fort and proba <= 0:
                    proba = SEUIL_HAUTE_CONFIANCE  # signal fort sans % chiffré
                detail = {
                    "signal_fort": marche.signal_fort,
                    "haute_confiance": marche.haute_confiance,
                    "mise_en_avant": marche.mise_en_avant,
                    "detail": marche.detail,
                    "type_api": marche.type,
                }
                if marche.type == "cartons_jaunes":
                    detail["seuil_jaunes"] = _extraire_seuil_cartons(marche.libelle)
                if marche.type == "over_2_5":
                    detail["buts_prevus_total"] = match.buts_prevus_total
                    detail["proba_over_2_5"] = match.proba_over_2_5

                ecrit = inserer_prono_solo(
                    connexion_analyses,
                    cle_match=cle,
                    weekend_debut=weekend,
                    championnat=match.championnat,
                    saison=match.saison,
                    date_match=match.date[:10],
                    domicile=match.domicile,
                    exterieur=match.exterieur,
                    type_marche=type_db,
                    libelle_marche=marche.libelle,
                    probabilite=proba,
                    detail_json=json.dumps(detail, ensure_ascii=False),
                    fige_le=fige_le,
                    remplacer=forcer,
                )
                if ecrit:
                    nb_figes += 1
                else:
                    nb_ignores += 1

            # Corners : même critère live (total prévu > 8).
            corners = match.corners
            if (
                corners
                and corners.disponible
                and corners.potentiel
                and corners.probabilite is not None
            ):
                ligne = float(corners.ligne_over or LIGNE_CORNERS_OVER_8_5)
                detail_c = {
                    "detail": corners.detail,
                    "type_api": TYPE_CORNERS,
                    "seuil_ligne": ligne,
                    "total_prevu": corners.total_prevu,
                    "potentiel": True,
                    "fort": bool(corners.fort),
                    "haute_confiance": corners.haute_confiance,
                    "mise_en_avant": corners.mise_en_avant,
                }
                libelle_c = f"Plus de {ligne} corners"
                if corners.total_prevu is not None:
                    libelle_c = (
                        f"Corners (≈ {float(corners.total_prevu):.1f} prévus) "
                        f"— plus de {ligne}"
                    )
                ecrit = inserer_prono_solo(
                    connexion_analyses,
                    cle_match=cle,
                    weekend_debut=weekend,
                    championnat=match.championnat,
                    saison=match.saison,
                    date_match=match.date[:10],
                    domicile=match.domicile,
                    exterieur=match.exterieur,
                    type_marche=TYPE_CORNERS,
                    libelle_marche=libelle_c,
                    probabilite=float(corners.probabilite),
                    detail_json=json.dumps(detail_c, ensure_ascii=False),
                    fige_le=fige_le,
                    remplacer=forcer,
                )
                if ecrit:
                    nb_figes += 1
                else:
                    nb_ignores += 1

        connexion_analyses.commit()
    finally:
        connexion_analyses.close()

    return {
        "weekend_debut": weekend,
        "nb_marches_figes": nb_figes,
        "nb_marches_ignores": nb_ignores,
        "nb_matchs_avec_prono": reponse.nb_matchs_avec_prono,
        "forcer": forcer,
        "fige_le": fige_le,
    }


def _extraire_seuil_cartons(libelle: str | None) -> int:
    """Extrait N depuis « Plus de N cartons jaunes », sinon seuil défaut."""
    if not libelle:
        return SEUIL_CARTONS_DEFAUT
    parties = libelle.lower().split()
    for i, mot in enumerate(parties):
        if mot == "de" and i + 1 < len(parties):
            try:
                # « Plus de 3 cartons » → vrai si total >= 4
                return int(parties[i + 1]) + 1
            except ValueError:
                break
    return SEUIL_CARTONS_DEFAUT


def _extraire_buts_prevus(detail: str | None) -> float | None:
    """Extrait le total buts depuis « Total buts prévu ≈ 2.6 »."""
    if not detail:
        return None
    marqueur = "≈"
    if marqueur not in detail:
        return None
    suite = detail.split(marqueur, 1)[1].strip().replace(",", ".")
    nombre = ""
    for car in suite:
        if car.isdigit() or car == ".":
            nombre += car
        elif nombre:
            break
    try:
        return float(nombre) if nombre else None
    except ValueError:
        return None


def evaluer_verdict_marche(
    type_marche: str,
    score: dict,
    detail_json: str | None = None,
) -> tuple[bool | None, str, str]:
    """
    Détermine vrai/faux + motif pour un type_marche.
    Retourne (vrai, motif_code, motif_texte). vrai=None si non jugable.
    """
    buts_d = int(score["buts_domicile"])
    buts_e = int(score["buts_exterieur"])
    detail: dict = {}
    if detail_json:
        try:
            detail = json.loads(detail_json)
        except (json.JSONDecodeError, TypeError):
            detail = {}

    if type_marche == "victoire_1":
        vrai = buts_d > buts_e
        if vrai:
            return True, "victoire_domicile", f"Victoire domicile {buts_d}-{buts_e}"
        return False, "issue_inversee", f"Pas de victoire domicile ({buts_d}-{buts_e})"

    if type_marche == "victoire_2":
        vrai = buts_e > buts_d
        if vrai:
            return True, "victoire_exterieur", f"Victoire extérieur {buts_d}-{buts_e}"
        return False, "issue_inversee", f"Pas de victoire extérieur ({buts_d}-{buts_e})"

    if type_marche == "btts":
        vrai = buts_d > 0 and buts_e > 0
        if vrai:
            return True, "btts_ok", f"Les deux ont marqué ({buts_d}-{buts_e})"
        return False, "btts_rate", f"BTTS non réalisé ({buts_d}-{buts_e})"

    if type_marche == "over_25":
        total = buts_d + buts_e
        vrai = total > 2.5
        if vrai:
            return True, "over_25_ok", f"Plus de 2,5 buts ({total} buts)"
        return False, "under_expected", f"Moins de 2,5 buts ({total} buts)"

    if type_marche == "over_15":
        total = buts_d + buts_e
        vrai = total > 1.5
        if vrai:
            return True, "over_15_ok", f"Plus de 1,5 buts ({total} buts)"
        return False, "under_15", f"Moins de 1,5 buts ({total} buts)"

    if type_marche == "over_15_dom":
        vrai = buts_d > 1.5
        if vrai:
            return True, "over_15_dom_ok", f"Domicile {buts_d} buts (> 1,5)"
        return False, "over_15_dom_rate", f"Domicile {buts_d} buts (≤ 1,5)"

    if type_marche == "over_15_ext":
        vrai = buts_e > 1.5
        if vrai:
            return True, "over_15_ext_ok", f"Extérieur {buts_e} buts (> 1,5)"
        return False, "over_15_ext_rate", f"Extérieur {buts_e} buts (≤ 1,5)"

    if type_marche == "cartons":
        j_d = score.get("jaunes_domicile")
        j_e = score.get("jaunes_exterieur")
        if j_d is None and j_e is None:
            return None, "cartons_indisponibles", "Cartons jaunes absents du score"
        total_j = (j_d or 0) + (j_e or 0)
        seuil = int(detail.get("seuil_jaunes") or SEUIL_CARTONS_DEFAUT)
        vrai = total_j >= seuil
        if vrai:
            return True, "cartons_eleves", f"{total_j} jaunes (≥ {seuil})"
        return False, "cartons_sous_seuil", f"{total_j} jaunes (< {seuil})"

    if type_marche == "cartons_15":
        j_d = score.get("jaunes_domicile")
        j_e = score.get("jaunes_exterieur")
        if j_d is None and j_e is None:
            return None, "cartons_indisponibles", "Cartons jaunes absents du score"
        total_j = (j_d or 0) + (j_e or 0)
        vrai = total_j > 1.5
        if vrai:
            return True, "cartons_15_ok", f"{total_j} jaunes (> 1,5)"
        return False, "cartons_15_rate", f"{total_j} jaunes (≤ 1,5)"

    if type_marche == "cartons_15_dom":
        j_d = score.get("jaunes_domicile")
        if j_d is None:
            return None, "cartons_indisponibles", "Cartons domicile absents"
        vrai = int(j_d) > 1.5
        if vrai:
            return True, "cartons_15_dom_ok", f"Domicile {j_d} jaunes (> 1,5)"
        return False, "cartons_15_dom_rate", f"Domicile {j_d} jaunes (≤ 1,5)"

    if type_marche == "cartons_15_ext":
        j_e = score.get("jaunes_exterieur")
        if j_e is None:
            return None, "cartons_indisponibles", "Cartons extérieur absents"
        vrai = int(j_e) > 1.5
        if vrai:
            return True, "cartons_15_ext_ok", f"Extérieur {j_e} jaunes (> 1,5)"
        return False, "cartons_15_ext_rate", f"Extérieur {j_e} jaunes (≤ 1,5)"

    if type_marche == TYPE_CORNERS:
        c_d = score.get("corners_domicile")
        c_e = score.get("corners_exterieur")
        if c_d is None and c_e is None:
            return None, "corners_indisponibles", "Corners absents du score"
        total_c = (c_d or 0) + (c_e or 0)
        ligne = float(detail.get("seuil_ligne") or 9.5)
        vrai = total_c > ligne
        if vrai:
            return True, "corners_over_ok", f"{total_c} corners (> {ligne})"
        return False, "corners_under", f"{total_c} corners (≤ {ligne})"

    return None, "type_inconnu", f"Type de marché inconnu : {type_marche}"


def juger_pronos_weekend(
    connexion_foot,
    *,
    date_debut: str | None = None,
    chemin_analyses=None,
) -> dict:
    """Juge les pronos Solo sans verdict dont le match est joué."""
    weekend = date_debut[:10] if date_debut else None
    connexion_analyses = ouvrir_analyses(chemin_analyses)
    juge_le = _maintenant_iso()
    nb_juges = 0
    nb_vrais = 0
    nb_faux = 0
    nb_attente = 0
    nb_non_jugables = 0

    try:
        a_juger = lister_pronos_solo_sans_verdict(connexion_analyses, weekend)
        for prono in a_juger:
            score = lire_score_match_football(
                connexion_foot,
                prono["championnat"],
                prono["saison"],
                prono["date_match"],
                prono["domicile"],
                prono["exterieur"],
            )
            if not score:
                nb_attente += 1
                continue

            vrai, motif_code, motif_texte = evaluer_verdict_marche(
                prono["type_marche"],
                score,
                prono.get("detail_json"),
            )
            if vrai is None:
                nb_non_jugables += 1
                continue

            inserer_verdict_solo(
                connexion_analyses,
                prono_solo_id=int(prono["id"]),
                vrai=vrai,
                motif_code=motif_code,
                motif_texte=motif_texte,
                buts_domicile=score["buts_domicile"],
                buts_exterieur=score["buts_exterieur"],
                juge_le=juge_le,
            )
            nb_juges += 1
            if vrai:
                nb_vrais += 1
            else:
                nb_faux += 1

        connexion_analyses.commit()
    finally:
        connexion_analyses.close()

    hit_rate = round(100.0 * nb_vrais / nb_juges, 1) if nb_juges else None
    return {
        "weekend_debut": weekend,
        "nb_juges": nb_juges,
        "nb_vrais": nb_vrais,
        "nb_faux": nb_faux,
        "nb_attente_score": nb_attente,
        "nb_non_jugables": nb_non_jugables,
        "hit_rate": hit_rate,
        "juge_le": juge_le,
    }


def _verdict_depuis_ligne(ligne: dict) -> VerdictMarche | None:
    if ligne.get("verdict_vrai") is None:
        return None
    return VerdictMarche(
        vrai=bool(ligne["verdict_vrai"]),
        motif_code=ligne.get("verdict_motif_code"),
        motif_texte=ligne.get("verdict_motif_texte"),
        buts_domicile=ligne.get("verdict_buts_domicile"),
        buts_exterieur=ligne.get("verdict_buts_exterieur"),
        juge_le=ligne.get("verdict_juge_le"),
    )


def construire_pronos_depuis_figes(
    weekend_debut: str,
    championnat: str | None = None,
    chemin_analyses=None,
) -> ReponsePronosWeekend | None:
    """Reconstruit la réponse Solo à partir des marchés figés en BD."""
    connexion = ouvrir_analyses(chemin_analyses)
    try:
        lignes = lister_pronos_solo_weekend(connexion, weekend_debut, championnat)
        fige_le = date_fige_weekend(connexion, weekend_debut)
    finally:
        connexion.close()

    if not lignes:
        return None

    vendredi = datetime.strptime(weekend_debut[:10], "%Y-%m-%d").date()
    debut, fin = plage_weekend(vendredi)

    # Regrouper par match.
    par_match: dict[tuple, list] = defaultdict(list)
    meta_match: dict[tuple, dict] = {}
    for ligne in lignes:
        cle = (
            ligne["championnat"],
            ligne["saison"],
            ligne["date_match"],
            ligne["domicile"],
            ligne["exterieur"],
        )
        par_match[cle].append(ligne)
        meta_match[cle] = ligne

    resultats: list[MatchPronoWeekend] = []
    for cle, marches_lignes in par_match.items():
        meta = meta_match[cle]
        marches: list[MarcheQualifie] = []
        corners = CornersMatch(disponible=False, message="non disponible")
        buts_prevus_total: float | None = None
        proba_over_2_5: float | None = None

        for ligne in marches_lignes:
            type_db = ligne["type_marche"]
            verdict = _verdict_depuis_ligne(ligne)
            detail = {}
            if ligne.get("detail_json"):
                try:
                    detail = json.loads(ligne["detail_json"])
                except (json.JSONDecodeError, TypeError):
                    detail = {}

            if type_db == TYPE_CORNERS:
                total_prevu = detail.get("total_prevu")
                ligne_over = detail.get("seuil_ligne")
                total_f = float(total_prevu) if total_prevu is not None else None
                fort = bool(detail.get("fort"))
                if not fort and total_f is not None:
                    fort = total_f > SEUIL_CORNERS_FORT
                proba_c = float(ligne["probabilite"])
                haute_c = bool(
                    detail.get("haute_confiance", proba_c >= SEUIL_HAUTE_CONFIANCE)
                )
                mise_c = bool(
                    detail.get("mise_en_avant", proba_c >= SEUIL_MISE_EN_AVANT)
                ) or haute_c
                corners = CornersMatch(
                    disponible=True,
                    probabilite=proba_c,
                    total_prevu=total_f,
                    ligne_over=float(ligne_over) if ligne_over is not None else None,
                    potentiel=bool(detail.get("potentiel", True)),
                    fort=fort,
                    haute_confiance=haute_c,
                    mise_en_avant=mise_c,
                    detail=detail.get("detail") or ligne.get("libelle_marche"),
                    message=None,
                    verdict=verdict,
                )
                continue

            type_api = TYPE_VERS_API.get(type_db, type_db)
            proba = float(ligne["probabilite"])
            if type_api == "over_2_5":
                proba_over_2_5 = proba
                brut_buts = detail.get("buts_prevus_total")
                if brut_buts is not None:
                    buts_prevus_total = float(brut_buts)
                elif buts_prevus_total is None:
                    buts_prevus_total = _extraire_buts_prevus(detail.get("detail"))
            haute = bool(
                detail.get("haute_confiance", proba >= SEUIL_HAUTE_CONFIANCE)
            )
            mise = bool(
                detail.get("mise_en_avant", proba >= SEUIL_MISE_EN_AVANT)
            ) or haute
            marches.append(
                MarcheQualifie(
                    type=type_api,  # type: ignore[arg-type]
                    libelle=ligne.get("libelle_marche") or type_db,
                    probabilite=proba,
                    signal_fort=bool(detail.get("signal_fort")),
                    haute_confiance=haute,
                    mise_en_avant=mise,
                    detail=detail.get("detail"),
                    verdict=verdict,
                )
            )

        marches.sort(key=_cle_tri_marche)
        if not marches and not corners.disponible:
            continue

        resultats.append(
            MatchPronoWeekend(
                championnat=meta["championnat"],
                saison=meta["saison"],
                date=meta["date_match"],
                heure=None,
                journee=None,
                domicile=meta["domicile"],
                exterieur=meta["exterieur"],
                score_modal=None,
                buts_prevus_total=buts_prevus_total,
                proba_over_2_5=proba_over_2_5,
                marches=marches,
                corners=corners,
            )
        )

    pronos_plats, groupes = grouper_pronos_par_championnat(resultats)
    return filtrer_reponse_pronos_utilisateur(
        ReponsePronosWeekend(
            avertissement=AVERTISSEMENT_SOLO,
            weekend=WeekendInfo(
                date_debut=debut.isoformat(),
                date_fin=fin.isoformat(),
                libelle=libelle_weekend(debut, fin),
            ),
            seuil_probabilite=SEUIL_PROBABILITE,
            seuil_mise_en_avant=SEUIL_MISE_EN_AVANT,
            nb_matchs_analyses=len(resultats),
            nb_matchs_avec_prono=len(resultats),
            pronos=pronos_plats,
            pronos_par_championnat=groupes,
            source="fige",
            fige_le=fige_le,
        )
    )


def construire_pronos_weekend_ou_figes(
    connexion_foot,
    date_debut: str | None = None,
    championnat: str | None = None,
    chemin_analyses=None,
) -> ReponsePronosWeekend:
    """Préfère les pronos figés si présents, sinon calcul live."""
    weekend = _weekend_iso(date_debut)
    figes = construire_pronos_depuis_figes(
        weekend, championnat=championnat, chemin_analyses=chemin_analyses
    )
    if figes is not None:
        return enrichir_logos_pronos(connexion_foot, figes)
    live = filtrer_reponse_pronos_utilisateur(
        construire_pronos_weekend(
            connexion_foot,
            date_debut=weekend,
            championnat=championnat,
        )
    )
    return enrichir_logos_pronos(
        connexion_foot,
        live.model_copy(
            update={
                "source": "live",
                "fige_le": None,
            }
        ),
    )


def bilan_weekend_solo(
    weekend_debut: str | None = None,
    championnat: str | None = None,
    chemin_analyses=None,
    proba_min: float | None = None,
) -> ReponseBilanSolo:
    """Hit-rate et détail des verdicts pour un weekend figé.

    Si ``proba_min`` est fourni, ne retient que les marchés figés dont la
    probabilité prédite est ≥ ce seuil (ex. page bilan ≥ 70 %).
    """
    weekend = _weekend_iso(weekend_debut)
    vendredi = datetime.strptime(weekend, "%Y-%m-%d").date()
    debut, fin = plage_weekend(vendredi)

    connexion = ouvrir_analyses(chemin_analyses)
    try:
        lignes = lister_pronos_solo_weekend(connexion, weekend, championnat)
        fige_le = date_fige_weekend(connexion, weekend)
    finally:
        connexion.close()

    lignes = [
        ligne
        for ligne in lignes
        if ligne["type_marche"] not in TYPES_MARCHES_CARTONS_BD
    ]

    if proba_min is not None:
        lignes = [
            ligne
            for ligne in lignes
            if ligne.get("probabilite") is not None
            and float(ligne["probabilite"]) >= float(proba_min)
        ]

    par_marche: dict[str, dict] = defaultdict(lambda: {"vrais": 0, "total": 0})
    par_champ: dict[str, dict] = defaultdict(lambda: {"vrais": 0, "total": 0})
    details = []
    nb_juges = 0
    nb_vrais = 0

    for ligne in lignes:
        if ligne.get("verdict_vrai") is None:
            continue
        nb_juges += 1
        est_vrai = bool(ligne["verdict_vrai"])
        if est_vrai:
            nb_vrais += 1
        type_m = ligne["type_marche"]
        champ = ligne["championnat"]
        par_marche[type_m]["total"] += 1
        par_champ[champ]["total"] += 1
        if est_vrai:
            par_marche[type_m]["vrais"] += 1
            par_champ[champ]["vrais"] += 1
        details.append(
            DetailVerdictSolo(
                championnat=champ,
                date_match=ligne["date_match"],
                domicile=ligne["domicile"],
                exterieur=ligne["exterieur"],
                type_marche=type_m,
                libelle_marche=ligne.get("libelle_marche"),
                probabilite=float(ligne["probabilite"]),
                vrai=est_vrai,
                motif_code=ligne.get("verdict_motif_code"),
                motif_texte=ligne.get("verdict_motif_texte"),
                buts_domicile=ligne.get("verdict_buts_domicile"),
                buts_exterieur=ligne.get("verdict_buts_exterieur"),
            )
        )

    def _taux(bloc: dict) -> float | None:
        if not bloc["total"]:
            return None
        return round(100.0 * bloc["vrais"] / bloc["total"], 1)

    return ReponseBilanSolo(
        weekend=WeekendInfo(
            date_debut=debut.isoformat(),
            date_fin=fin.isoformat(),
            libelle=libelle_weekend(debut, fin),
        ),
        fige_le=fige_le,
        seuil_probabilite=float(proba_min) if proba_min is not None else None,
        nb_pronos=len(lignes),
        nb_juges=nb_juges,
        nb_vrais=nb_vrais,
        nb_faux=nb_juges - nb_vrais,
        hit_rate=round(100.0 * nb_vrais / nb_juges, 1) if nb_juges else None,
        par_marche={
            k: StatHitRate(vrais=v["vrais"], total=v["total"], hit_rate=_taux(v))
            for k, v in sorted(par_marche.items())
        },
        par_championnat={
            k: StatHitRate(vrais=v["vrais"], total=v["total"], hit_rate=_taux(v))
            for k, v in sorted(par_champ.items())
        },
        details=details,
    )
