"""Endpoint API stats de calibration du modele (Phase 2)."""

from __future__ import annotations

import re
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Query

from calibration import agreger_metriques_saison
from calibrateur import infos_calibrateur
from historique_analyses import lister_resultats_avec_previsions, ouvrir_base

routeur_stats_modele = APIRouter()
MOTIF_SAISON = re.compile(r"^\d{4}-\d{4}$")


@routeur_stats_modele.get("/api/stats-modele")
def stats_modele_api(
    saison: str = Query(...),
    championnat: str | None = Query(None),
    inclure_retroactif: int = Query(
        0,
        description="1 pour inclure les previsions backfill (retroactif=1), 0 par defaut",
    ),
):
    """Agregats de calibration depuis analyses.db (previsions figees vs realite)."""
    if not MOTIF_SAISON.match(saison):
        raise HTTPException(400, "Format de saison invalide (ex. 2026-2027)")
    if inclure_retroactif not in (0, 1):
        raise HTTPException(400, "inclure_retroactif doit valoir 0 ou 1")
    champ_filtre = championnat.strip()[:80] if championnat else None
    connexion = ouvrir_base()
    try:
        resultats = lister_resultats_avec_previsions(
            connexion,
            saison,
            champ_filtre,
            inclure_retroactif=bool(inclure_retroactif),
        )
        global_stats = agreger_metriques_saison(resultats)
        par_championnat: dict[str, dict] = {}
        groupes: dict[str, list] = defaultdict(list)
        for ligne in resultats:
            groupes[ligne["championnat"]].append(ligne)
        for nom_champ, lignes in sorted(groupes.items()):
            par_championnat[nom_champ] = agreger_metriques_saison(lignes)
        return {
            "saison": saison,
            "championnat": champ_filtre,
            "inclure_retroactif": bool(inclure_retroactif),
            "disponible": global_stats["nb_matchs"] > 0,
            "metriques": global_stats,
            "par_championnat": par_championnat,
            "nb_resultats": global_stats["nb_matchs"],
            "calibrateur": infos_calibrateur(),
        }
    finally:
        connexion.close()
