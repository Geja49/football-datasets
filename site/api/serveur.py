"""
API pour le site de stats (lecture + communauté Phases 1–2).
Usage (a la racine du projet) : python -m uvicorn site.api.serveur:app --reload --port 8001
"""

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import os
import re
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from analyse_rencontre import (
    LIGUES_NATIONALES,
    comparaison_previsions_reel,
    _bilan_match,
)
from historique_analyses import (
    lire_prevision_figee,
    lire_prevision_sans_date,
    lire_resultat,
    ouvrir_base as ouvrir_analyses,
    pred_depuis_prevision_figee,
)
from correspondances import (
    alias_noms_equipe,
    cle_nom,
    nom_pour_calendrier,
    nom_pour_joueurs,
    normaliser,
)
from photos_joueurs import DOSSIER_PHOTOS, photo_en_cache
from sites_officiels import SITES_CHAMPIONNATS, SITES_EQUIPES
from cotes import routeur_cotes
from communaute import charger_fichier_env, initialiser_base, routeur_communaute
from forum import assurer_tables_forum, routeur_forum
from stats_modele import routeur_stats_modele
from gestionnaires.accueil import routeur_accueil
from gestionnaires.analyse import routeur_analyse
from gestionnaires.classement import routeur_classement
from gestionnaires.equipes import routeur_equipes
from gestionnaires.joueurs import routeur_joueurs
from gestionnaires.meilleurs import routeur_meilleurs
from gestionnaires.solo import routeur_solo
from requetes.connexion import lignes_dict
from requetes.equipes import (
    choisir_nom_dans_competition as _choisir_nom_dans_competition,
    lire_couverture_defense,
    lire_site_equipe as _lire_site_equipe,
    table_existe as _table_existe,
)
from requetes.joueurs import saison_avec_joueurs
from requetes.matchs import (
    choisir_prochain_jour,
    lire_calendrier,
    lire_horaire_match as _lire_horaire_match,
    lister_buts_equipe_saison,
    lister_calendrier_jour,
    lister_lignes_xg,
    lister_matchs_joues_jour,
    lister_matchs_joues_saison,
    lister_matchs_radar_equipe as _lister_matchs_radar_equipe,
    lister_matchs_radar_ligue,
    saisons_disponibles as _saisons_disponibles,
)

RACINE = Path(__file__).resolve().parents[2]
FICHIER_BASE = RACINE / "donnees" / "football.db"
ORIGINES_CORS_DEFAUT = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)
CHAMPIONNATS = (
    "Premier League",
    "La Liga",
    "Bundesliga",
    "Serie A",
    "Ligue 1",
    "Super Lig",
    "Ligue des champions",
)
NOM_LDC = "Ligue des champions"
PHASE_LIGUE = "phase de ligue"
SAISON_COURANTE = "2026-2027"
MOTIF_SAISON = re.compile(r"^\d{4}-\d{4}$")

# Heures du calendrier = coup d'envoi local de la compétition (openfootball / sources).
FUSEAU_PAR_CHAMPIONNAT = {
    "Premier League": "Europe/London",
    "La Liga": "Europe/Madrid",
    "Bundesliga": "Europe/Berlin",
    "Serie A": "Europe/Rome",
    "Ligue 1": "Europe/Paris",
    "Super Lig": "Europe/Istanbul",
    "Ligue des champions": "Europe/Paris",
}


def commence_at_iso(date_str, heure_str, championnat=None):
    """Convertit date+heure locales de ligue en instant UTC ISO (Z)."""
    if not date_str or not heure_str:
        return ""
    texte_heure = str(heure_str).strip()
    if len(texte_heure) < 4 or ":" not in texte_heure:
        return ""
    try:
        parties = texte_heure.split(":")
        heures = int(parties[0])
        minutes = int(parties[1][:2])
        annee, mois, jour = (int(x) for x in str(date_str)[:10].split("-"))
        nom_fuseau = FUSEAU_PAR_CHAMPIONNAT.get(championnat) or "Europe/Paris"
        local = datetime(
            annee, mois, jour, heures, minutes, tzinfo=ZoneInfo(nom_fuseau)
        )
        return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError, OSError, ZoneInfoNotFoundError):
        return ""


def enrichir_horaires(matchs, championnat_defaut=None):
    """Ajoute commence_at (UTC) pour affichage fuseau navigateur."""
    for match in matchs:
        champ = match.get("championnat") or championnat_defaut
        match["commence_at"] = commence_at_iso(
            match.get("date"), match.get("heure"), champ
        )
        match["fuseau_source"] = FUSEAU_PAR_CHAMPIONNAT.get(
            champ, "Europe/Paris"
        )
    return matchs


def lire_origines_cors() -> list[str]:
    """Origines CORS depuis ORIGINES_CORS (virgules) ou défauts localhost."""
    charger_fichier_env()
    brut = (os.environ.get("ORIGINES_CORS") or "").strip()
    if not brut:
        return list(ORIGINES_CORS_DEFAUT)
    origines = [partie.strip() for partie in brut.split(",") if partie.strip()]
    return origines or list(ORIGINES_CORS_DEFAUT)


app = FastAPI(title="Stats championnats")
app.add_middleware(
    CORSMiddleware,
    allow_origins=lire_origines_cors(),
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.include_router(routeur_cotes)
app.include_router(routeur_communaute)
app.include_router(routeur_forum)
app.include_router(routeur_stats_modele)
app.include_router(routeur_accueil)
app.include_router(routeur_meilleurs)
app.include_router(routeur_classement)
app.include_router(routeur_equipes)
app.include_router(routeur_joueurs)
app.include_router(routeur_analyse)
app.include_router(routeur_solo)
initialiser_base()
assurer_tables_forum()


def lire_horaire_match(connexion, championnat, saison, domicile, exterieur):
    """Date, heure locale et commence_at UTC pour un match du calendrier."""
    brut = _lire_horaire_match(connexion, championnat, saison, domicile, exterieur)
    if not brut:
        return None
    heure = brut["heure"]
    return {
        "date": brut["date"],
        "heure": heure,
        "commence_at": commence_at_iso(brut["date"], heure, championnat),
    }


def ouvrir_base():
    if not FICHIER_BASE.exists():
        raise HTTPException(500, "Base introuvable. Lancez python scripts/creer_base.py")
    connexion = sqlite3.connect(FICHIER_BASE)
    connexion.row_factory = sqlite3.Row
    return connexion


def verifier_filtres(championnat: str, saison: str):
    if championnat not in CHAMPIONNATS:
        raise HTTPException(400, "Championnat inconnu")
    if not MOTIF_SAISON.match(saison):
        raise HTTPException(400, "Saison invalide")


def limiter_texte(valeur: str, taille=80):
    texte = (valeur or "").strip()
    if not texte or len(texte) > taille:
        raise HTTPException(400, "Nom invalide")
    return texte


def infos_site_equipe(connexion, nom_equipe):
    vide = {"nom_officiel": "", "url_site": "", "url_logo": "", "stade": ""}
    ligne = _lire_site_equipe(connexion, nom_equipe)
    data = ligne if ligne else vide.copy()
    if not data.get("url_site"):
        data["url_site"] = SITES_EQUIPES.get(nom_equipe, "")
    # Eviter une page feminine / mauvaise URL renvoyee par l'annuaire
    if nom_equipe in SITES_EQUIPES:
        data["url_site"] = SITES_EQUIPES[nom_equipe]
    return data


def infos_championnat(nom):
    fiche = SITES_CHAMPIONNATS.get(nom, {})
    return {
        "nom": nom,
        "url_site": fiche.get("url_site", ""),
        "nom_affichage": fiche.get("nom_affichage", nom),
    }


def charger_transferts_joueur(connexion, nom_joueur, limite=20):
    """Historique transferts (dump communautaire), matching exact sur le nom."""
    try:
        return lignes_dict(
            connexion.execute(
                """
                SELECT date_transfert, saison_transfert, club_depart,
                       club_arrivee, frais_eur, valeur_marche_eur
                FROM transferts_joueurs
                WHERE joueur = ?
                ORDER BY date_transfert DESC
                LIMIT ?
                """,
                (nom_joueur, limite),
            )
        )
    except sqlite3.OperationalError:
        return []


def charger_valeur_marche(connexion, nom_joueur):
    """Dump communautaire transfermarkt-datasets (CC0), matching best-effort."""
    try:
        lignes = lignes_dict(
            connexion.execute(
                """
                SELECT joueur, joueur_dump, age, club_dump, poste,
                       valeur_marche_eur, valeur_max_eur, derniere_saison_dump,
                       qualite_match, source, mention
                FROM valeurs_marche_joueurs
                WHERE joueur = ?
                LIMIT 1
                """,
                (nom_joueur,),
            )
        )
    except sqlite3.OperationalError:
        return None
    if not lignes:
        return None
    profil = lignes[0]
    profil["transferts_recents"] = charger_transferts_joueur(connexion, nom_joueur)
    return profil


MESSAGE_LDC_PAGE = (
    "Ligue des champions : scores et calendrier via openfootball ; "
    "buteurs joueur par joueur via OpenML (saisons 2013-2014 a 2020-2021). "
    "Pas de xG ni de stats defensives completes pour les saisons recentes ; "
    "les effectifs actuels reprennent souvent la ligue nationale du club."
)



AXES_JOUEUR = (
    ("buts", "Buts"),
    ("xg", "xG"),
    ("passes_decisives", "Passes D."),
    ("xa", "xA"),
    ("tirs", "Tirs"),
    ("minutes", "Minutes"),
)
NB_CLASSES_HISTO = 12
# Trop peu d'équipes / joueurs : pas de comparaison ligue fiable.
MIN_ECHANTILLON_LIGUE = 4
PLAFOND_BUTS_MATCH = 3.0
PLAFOND_XG_MATCH = 2.5
PLAFOND_TIRS_MATCH = 18.0
PLAFOND_FORME = 15.0


def nombre_ok(valeur):
    try:
        n = float(valeur)
    except (TypeError, ValueError):
        return 0.0
    if n != n:
        return 0.0
    return n


def moyenne_liste(valeurs):
    if not valeurs:
        return 0.0
    return sum(valeurs) / len(valeurs)


def mediane_liste(valeurs):
    if not valeurs:
        return 0.0
    triees = sorted(valeurs)
    n = len(triees)
    milieu = n // 2
    if n % 2:
        return triees[milieu]
    return (triees[milieu - 1] + triees[milieu]) / 2


def histogramme_simple(valeurs, plafond, nb_classes=NB_CLASSES_HISTO):
    comptes = [0] * nb_classes
    if plafond <= 0:
        return [{"n": 0} for _ in comptes]
    for v in valeurs:
        ratio = min(max(v / plafond, 0.0), 0.9999)
        comptes[int(ratio * nb_classes)] += 1
    return [{"n": c} for c in comptes]


def saison_pour_radar(saisons):
    """Saison la plus récente, ligue où le joueur a le plus joué (évite la LDC courte)."""
    if not saisons:
        return None
    annee = saisons[0].get("saison")
    candidates = [s for s in saisons if s.get("saison") == annee] or saisons
    return max(candidates, key=lambda s: nombre_ok(s.get("minutes")))


def reperes_joueur_ligue(connexion, championnat, saison):
    """Max, moyenne, médiane et histogrammes de la ligue pour le radar joueur."""
    try:
        lignes = lignes_dict(
            connexion.execute(
                """
                SELECT buts, xg, passes_decisives, xa, tirs, minutes
                FROM joueurs
                WHERE championnat = ? AND saison = ? AND minutes > 0
                """,
                (championnat, saison),
            )
        )
    except sqlite3.OperationalError:
        return None
    if len(lignes) < MIN_ECHANTILLON_LIGUE:
        return {
            "championnat": championnat,
            "saison": saison,
            "nb_joueurs": len(lignes),
            "reference": "moyenne",
            "axes": [],
            "message": (
                "Pas assez de joueurs dans le championnat pour comparer "
                f"(minimum {MIN_ECHANTILLON_LIGUE})."
            ),
        }
    axes = []
    for cle, libelle in AXES_JOUEUR:
        valeurs = [nombre_ok(ligne.get(cle)) for ligne in lignes]
        plafond = max(valeurs) if valeurs else 0.0
        axes.append(
            {
                "cle": cle,
                "libelle": libelle,
                "plafond": round(plafond, 2),
                "moyenne": round(moyenne_liste(valeurs), 2),
                "mediane": round(mediane_liste(valeurs), 2),
                "histogramme": histogramme_simple(valeurs, plafond),
            }
        )
    return {
        "championnat": championnat,
        "saison": saison,
        "nb_joueurs": len(lignes),
        "reference": "moyenne",
        "axes": axes,
    }


def _cote_match_equipe(match, nom_equipe):
    domicile = match.get("domicile") == nom_equipe
    a_xg = match.get("xg_domicile") is not None and match.get("xg_exterieur") is not None
    a_tirs = match.get("tirs_domicile") is not None and match.get("tirs_exterieur") is not None
    buts = nombre_ok(match.get("buts_domicile") if domicile else match.get("buts_exterieur"))
    contre = nombre_ok(match.get("buts_exterieur") if domicile else match.get("buts_domicile"))
    return {
        "date": match.get("date") or "",
        "buts": buts,
        "contre": contre,
        "xg": nombre_ok(match.get("xg_domicile") if domicile else match.get("xg_exterieur"))
        if a_xg
        else None,
        "xg_contre": nombre_ok(
            match.get("xg_exterieur") if domicile else match.get("xg_domicile")
        )
        if a_xg
        else None,
        "tirs": nombre_ok(match.get("tirs_domicile") if domicile else match.get("tirs_exterieur"))
        if a_tirs
        else None,
        "points": 3 if buts > contre else (1 if buts == contre else 0),
    }


def _stats_equipes_ligue(matchs):
    """Moyennes par match et forme (5 derniers) pour chaque équipe de la ligue."""
    par_equipe = defaultdict(list)
    for match in matchs:
        if match.get("buts_domicile") is None or match.get("buts_exterieur") is None:
            continue
        for nom in (match.get("domicile"), match.get("exterieur")):
            if nom:
                par_equipe[nom].append(_cote_match_equipe(match, nom))

    stats = []
    for nom, cotes in par_equipe.items():
        if not cotes:
            continue
        nb = len(cotes)
        avec_xg = [c for c in cotes if c["xg"] is not None]
        avec_tirs = [c for c in cotes if c["tirs"] is not None]
        recents = sorted(cotes, key=lambda c: c["date"], reverse=True)[:5]
        forme = sum(c["points"] for c in recents)
        ligne = {
            "equipe": nom,
            "buts": moyenne_liste([c["buts"] for c in cotes]),
            "defense": moyenne_liste([c["contre"] for c in cotes]),
            "forme": float(forme),
            "nb_matchs": nb,
        }
        if avec_xg:
            ligne["xg_match"] = moyenne_liste([c["xg"] for c in avec_xg])
            ligne["xg_encaisse"] = moyenne_liste([c["xg_contre"] for c in avec_xg])
        if avec_tirs:
            ligne["tirs"] = moyenne_liste([c["tirs"] for c in avec_tirs])
        stats.append(ligne)
    return stats


def reperes_equipe_ligue(connexion, championnat, saison):
    """Moyenne / médiane / histogrammes des équipes du championnat (même saison)."""
    matchs = lister_matchs_radar_ligue(connexion, championnat, saison)
    if matchs is None:
        return None
    if not matchs:
        return {
            "championnat": championnat,
            "saison": saison,
            "nb_equipes": 0,
            "reference": "moyenne",
            "axes": [],
            "message": "Pas assez de matchs joués dans le championnat pour comparer.",
        }
    joindre_xg(connexion, championnat, saison, matchs)
    stats = _stats_equipes_ligue(matchs)
    if len(stats) < MIN_ECHANTILLON_LIGUE:
        return {
            "championnat": championnat,
            "saison": saison,
            "nb_equipes": len(stats),
            "reference": "moyenne",
            "axes": [],
            "message": (
                "Pas assez d'équipes avec des matchs joués pour comparer "
                f"(minimum {MIN_ECHANTILLON_LIGUE})."
            ),
        }

    series = (
        ("buts", "Buts", False, PLAFOND_BUTS_MATCH),
        ("xg_match", "xG", False, PLAFOND_XG_MATCH),
        ("tirs", "Tirs", False, PLAFOND_TIRS_MATCH),
        ("forme", "Forme", False, PLAFOND_FORME),
        ("defense", "Solidité", True, PLAFOND_BUTS_MATCH),
        ("xg_encaisse", "xG encaissés", True, PLAFOND_XG_MATCH),
    )
    axes = []
    for cle, libelle, inverser, plafond_defaut in series:
        bruts = [nombre_ok(s[cle]) for s in stats if cle in s]
        if len(bruts) < MIN_ECHANTILLON_LIGUE:
            continue
        plafond = max(max(bruts), plafond_defaut)
        pour_histo = (
            [plafond - min(v, plafond) for v in bruts] if inverser else bruts
        )
        axes.append(
            {
                "cle": cle,
                "libelle": libelle,
                "plafond": round(plafond, 2),
                "moyenne": round(moyenne_liste(bruts), 3),
                "mediane": round(mediane_liste(bruts), 3),
                "inverser": inverser,
                "histogramme": histogramme_simple(pour_histo, plafond),
            }
        )
    if not axes:
        return {
            "championnat": championnat,
            "saison": saison,
            "nb_equipes": len(stats),
            "reference": "moyenne",
            "axes": [],
            "message": "Données ligue insuffisantes pour les métriques du radar.",
        }
    return {
        "championnat": championnat,
        "saison": saison,
        "nb_equipes": len(stats),
        "reference": "moyenne",
        "axes": axes,
    }


def matchs_classement(matchs, championnat):
    """LDC : uniquement la phase de ligue (pas les barrages ni l'elimination)."""
    if championnat != NOM_LDC:
        return matchs
    if not any((m.get("phase") or "").strip() for m in matchs):
        return matchs
    return [m for m in matchs if (m.get("phase") or "").strip() == PHASE_LIGUE]


def calculer_classement(matchs):
    stats = defaultdict(
        lambda: {"j": 0, "v": 0, "n": 0, "d": 0, "bp": 0, "bc": 0, "pts": 0}
    )

    def ajouter(equipe, bp, bc, pts, v, n, d):
        ligne = stats[equipe]
        ligne["j"] += 1
        ligne["v"] += v
        ligne["n"] += n
        ligne["d"] += d
        ligne["bp"] += bp
        ligne["bc"] += bc
        ligne["pts"] += pts

    for match in matchs:
        domicile = match["domicile"]
        exterieur = match["exterieur"]
        if match["buts_domicile"] is None or match["buts_exterieur"] is None:
            continue
        bp = int(match["buts_domicile"])
        bc = int(match["buts_exterieur"])
        if match["resultat"] == "H":
            ajouter(domicile, bp, bc, 3, 1, 0, 0)
            ajouter(exterieur, bc, bp, 0, 0, 0, 1)
        elif match["resultat"] == "A":
            ajouter(domicile, bp, bc, 0, 0, 0, 1)
            ajouter(exterieur, bc, bp, 3, 1, 0, 0)
        else:
            ajouter(domicile, bp, bc, 1, 0, 1, 0)
            ajouter(exterieur, bc, bp, 1, 0, 1, 0)

    classement = sorted(
        stats.items(),
        key=lambda item: (item[1]["pts"], item[1]["bp"] - item[1]["bc"], item[1]["bp"]),
        reverse=True,
    )
    resultat = []
    for rang, (equipe, ligne) in enumerate(classement, start=1):
        resultat.append(
            {
                "rang": rang,
                "equipe": equipe,
                "pts": ligne["pts"],
                "j": ligne["j"],
                "v": ligne["v"],
                "n": ligne["n"],
                "d": ligne["d"],
                "bp": ligne["bp"],
                "bc": ligne["bc"],
                "diff": ligne["bp"] - ligne["bc"],
            }
        )
    return resultat


def saisons_disponibles(connexion, championnat=None):
    """Liste les saisons en base ; la saison en cours apparait meme si peu de donnees."""
    return _saisons_disponibles(connexion, championnat, SAISON_COURANTE)


def ajouter_logos_programme(connexion, programme):
    cache = {}

    def logo(nom):
        if nom not in cache:
            cache[nom] = infos_site_equipe(connexion, nom).get("url_logo", "")
        return cache[nom]

    for match in programme:
        match["url_logo_domicile"] = logo(match["domicile"])
        match["url_logo_exterieur"] = logo(match["exterieur"])
    return programme


def fusionner_programme(joues, avenir, championnat=None):
    vus = set()
    programme = []
    for match in joues:
        vus.add((match["domicile"], match["exterieur"]))
        programme.append(
            {
                "date": match.get("date", ""),
                "heure": match.get("heure") or "",
                "journee": match.get("journee") or "",
                "championnat": match.get("championnat") or championnat or "",
                "domicile": match["domicile"],
                "exterieur": match["exterieur"],
                "buts_domicile": match.get("buts_domicile"),
                "buts_exterieur": match.get("buts_exterieur"),
                "joue": True,
                "xg_domicile": None,
                "xg_exterieur": None,
            }
        )
    for match in avenir:
        cle = (match["domicile"], match["exterieur"])
        if cle in vus:
            continue
        vus.add(cle)
        programme.append(
            {
                "date": match.get("date", ""),
                "heure": match.get("heure") or "",
                "journee": match.get("journee") or "",
                "championnat": match.get("championnat") or championnat or "",
                "domicile": match["domicile"],
                "exterieur": match["exterieur"],
                "buts_domicile": None,
                "buts_exterieur": None,
                "joue": False,
                "xg_domicile": None,
                "xg_exterieur": None,
            }
        )
    programme.sort(key=lambda m: (m["date"] or "", m["heure"] or "", m["domicile"]))
    enrichir_horaires(programme, championnat)
    return programme


def joindre_journee(connexion, championnat, saison, matchs):
    """Ajoute le numero de journee depuis le calendrier (best-effort)."""
    if not matchs:
        return matchs
    index = {}
    for ligne in lire_calendrier(connexion, championnat, saison):
        cle = (ligne.get("domicile"), ligne.get("exterieur"))
        if ligne.get("journee"):
            index[cle] = ligne["journee"]
    for match in matchs:
        if match.get("journee"):
            continue
        cle = (match.get("domicile"), match.get("exterieur"))
        if cle in index:
            match["journee"] = index[cle]
        else:
            match["journee"] = match.get("journee") or ""
    return matchs


def joindre_xg(connexion, championnat, saison, matchs):
    """Ajoute xg_domicile / xg_exterieur via matchs_xg (noms Understat)."""
    if not matchs:
        return matchs
    lignes = lister_lignes_xg(connexion, championnat, saison)
    if lignes is None:
        for match in matchs:
            match.setdefault("xg_domicile", None)
            match.setdefault("xg_exterieur", None)
        return matchs
    noms = []
    vus = set()
    par_date = {}
    par_paire = {}
    for ligne in lignes:
        for nom in (ligne["domicile"], ligne["exterieur"]):
            if nom not in vus:
                vus.add(nom)
                noms.append(nom)
        xg_d = (
            None
            if ligne["xg_domicile"] is None
            else round(float(ligne["xg_domicile"]), 2)
        )
        xg_e = (
            None
            if ligne["xg_exterieur"] is None
            else round(float(ligne["xg_exterieur"]), 2)
        )
        couple = (xg_d, xg_e)
        par_date[(ligne["date"], ligne["domicile"], ligne["exterieur"])] = couple
        par_paire[(ligne["domicile"], ligne["exterieur"])] = couple
    for match in matchs:
        nom_d = nom_pour_joueurs(match["domicile"], noms)
        nom_e = nom_pour_joueurs(match["exterieur"], noms)
        couple = par_date.get((match.get("date"), nom_d, nom_e))
        if not couple:
            couple = par_paire.get((nom_d, nom_e))
        if couple:
            match["xg_domicile"], match["xg_exterieur"] = couple
        else:
            match["xg_domicile"] = None
            match["xg_exterieur"] = None
    return matchs


LIMITE_EQUIPE = 8
LIMITE_LIGUE = 10


def resoudre_nom_equipe(nom, matchs):
    """Ath Madrid, Atletico Madrid, Atl. Madrid -> nom du calendrier."""
    nom = (nom or "").strip()
    if not nom:
        return ""
    connus = []
    vus = set()
    for match in matchs:
        for cote in (match.get("domicile"), match.get("exterieur")):
            if cote and cote not in vus:
                vus.add(cote)
                connus.append(cote)
    if nom in vus:
        return nom
    alias = nom_pour_calendrier(nom, connus)
    if alias in vus:
        return alias
    cible = normaliser(nom)
    if len(cible) >= 4:
        for connu in connus:
            if normaliser(connu) == cible:
                return connu
    return nom


def filtrer_matchs_a_venir(programme, aujourd_hui):
    return [
        match
        for match in programme
        if not match.get("joue") and (match.get("date") or "") >= aujourd_hui
    ]


def extraire_prochaine_journee(prochains, taille=LIMITE_LIGUE):
    if not prochains:
        return []
    pris = []
    for match in prochains:
        if pris and len(pris) >= taille and match["date"] != pris[-1]["date"]:
            break
        pris.append(match)
    return pris


def annoter_pour_equipe(matchs, nom_equipe):
    annotes = []
    for brut in matchs:
        match = dict(brut)
        if match["domicile"] == nom_equipe:
            match["lieu"] = "Domicile"
            match["adversaire"] = match["exterieur"]
        else:
            match["lieu"] = "Extérieur"
            match["adversaire"] = match["domicile"]
        annotes.append(match)
    return annotes


MESSAGE_LDC_JOUEUR = (
    "Ligue des champions : buts par joueur disponibles seulement pour "
    "OpenML 2013-2021. Les saisons recentes n'ont pas de stats joueur LDC ici."
)
MESSAGE_DEFENSE_ABSENT = (
    "Non disponible pour cette saison/compétition. "
    "Les tacles, interceptions, duels et arrêts viennent de StatsBomb Open Data "
    "et du jeu Wyscout 2017-2018 (licence CC BY). "
    "Les 5 ligues 2025-2026 n'y figurent pas."
)
CHAMPS_DEFENSE = (
    "matchs",
    "tacles",
    "tacles_reussis",
    "interceptions",
    "blocs",
    "degagements",
    "duels",
    "duels_gagnes",
    "recoveries",
    "pressions",
    "arrets",
    "xg_tirs_subis",
)


def table_existe(connexion, nom):
    return _table_existe(connexion, nom)


def fusionner_defense_sources(lignes):
    """Une ligne par joueur/saison : on garde la source avec le plus de matchs."""
    meilleur = {}
    for ligne in lignes:
        cle = (
            ligne.get("championnat"),
            ligne.get("saison"),
            (ligne.get("equipe") or "").lower(),
            (ligne.get("joueur") or "").lower(),
        )
        actuel = meilleur.get(cle)
        if actuel is None or nombre_ok(ligne.get("matchs")) > nombre_ok(
            actuel.get("matchs")
        ):
            meilleur[cle] = ligne
    return list(meilleur.values())


def totaux_defense(lignes):
    totaux = {champ: 0 for champ in CHAMPS_DEFENSE}
    totaux["xg_tirs_subis"] = 0.0
    totaux["matchs"] = 0
    for ligne in lignes:
        totaux["matchs"] = max(totaux["matchs"], int(nombre_ok(ligne.get("matchs"))))
        totaux["xg_tirs_subis"] += nombre_ok(ligne.get("xg_tirs_subis"))
        for champ in CHAMPS_DEFENSE:
            if champ in ("matchs", "xg_tirs_subis"):
                continue
            totaux[champ] += int(nombre_ok(ligne.get(champ)))
    totaux["xg_tirs_subis"] = round(totaux["xg_tirs_subis"], 2)
    totaux["a_xg_subis"] = totaux["xg_tirs_subis"] > 0
    totaux["a_pressions"] = totaux["pressions"] > 0
    totaux["a_recoveries"] = totaux["recoveries"] > 0
    return totaux


def message_couverture_defense(connexion, championnat, saison):
    if not table_existe(connexion, "couverture_sources"):
        return MESSAGE_DEFENSE_ABSENT, False
    lignes = lire_couverture_defense(connexion, championnat, saison)
    if lignes is None:
        return MESSAGE_DEFENSE_ABSENT, False
    if not lignes:
        return MESSAGE_DEFENSE_ABSENT, False
    sources = ", ".join(sorted({ligne["source"] for ligne in lignes if ligne.get("source")}))
    extra = (lignes[0].get("commentaire") or "").strip()
    message = f"Source : {sources}."
    if extra:
        message = f"{message} {extra}"
    return message, True


def equipe_defense_connue(nom, aliases):
    cibles_norm = {normaliser(a) for a in aliases if a}
    cibles_cle = {cle_nom(a) for a in aliases if a}
    nom_n = normaliser(nom)
    nom_c = cle_nom(nom)
    if nom in aliases or nom_n in cibles_norm or nom_c in cibles_cle:
        return True
    if len(nom_n) >= 6:
        for cible in cibles_norm:
            if len(cible) >= 6 and (nom_n in cible or cible in nom_n):
                return True
    return False


def charger_defense_equipe(connexion, championnat, saison, nom_equipe, alias):
    vide = {
        "disponible": False,
        "message": MESSAGE_DEFENSE_ABSENT,
        "totaux": None,
        "joueurs": [],
        "gardiens": [],
    }
    if not table_existe(connexion, "actions_defensives"):
        return vide
    aliases = alias_noms_equipe(nom_equipe)
    for nom in alias or []:
        if nom and nom not in aliases:
            aliases.append(nom)
    try:
        lignes = fusionner_defense_sources(
            lignes_dict(
                connexion.execute(
                    """
                    SELECT championnat, saison, equipe, joueur, matchs,
                           tacles, tacles_reussis, interceptions, blocs,
                           degagements, duels, duels_gagnes, recoveries,
                           pressions, arrets, xg_tirs_subis, source
                    FROM actions_defensives
                    WHERE championnat = ? AND saison = ?
                    """,
                    (championnat, saison),
                )
            )
        )
    except sqlite3.OperationalError:
        return vide
    du_club = [
        ligne
        for ligne in lignes
        if equipe_defense_connue(ligne.get("equipe") or "", aliases)
    ]
    message, connue = message_couverture_defense(connexion, championnat, saison)
    if not du_club:
        vide["message"] = (
            message
            if not connue
            else (
                "Pas de stats défensives pour ce club dans cette saison "
                "(saison absente ou partielle dans l'open data)."
            )
        )
        return vide
    gardiens = [
        {
            "joueur": ligne["joueur"],
            "arrets": int(nombre_ok(ligne.get("arrets"))),
            "xg_tirs_subis": round(nombre_ok(ligne.get("xg_tirs_subis")), 2),
            "matchs": int(nombre_ok(ligne.get("matchs"))),
        }
        for ligne in du_club
        if nombre_ok(ligne.get("arrets")) > 0 or nombre_ok(ligne.get("xg_tirs_subis")) > 0
    ]
    gardiens.sort(key=lambda x: x["arrets"], reverse=True)
    joueurs = sorted(
        du_club,
        key=lambda x: (
            nombre_ok(x.get("tacles")) + nombre_ok(x.get("interceptions")),
            nombre_ok(x.get("matchs")),
        ),
        reverse=True,
    )
    return {
        "disponible": True,
        "message": message,
        "totaux": totaux_defense(du_club),
        "joueurs": joueurs[:40],
        "gardiens": gardiens[:8],
    }


def charger_defense_joueur(connexion, nom_joueur):
    vide = {
        "disponible": False,
        "message": (
            "Pas de stats défensives pour ce joueur dans les jeux ouverts "
            "(souvent hors 2015-2016 / 2017-2018)."
        ),
        "saisons": [],
    }
    if not table_existe(connexion, "actions_defensives"):
        vide["message"] = MESSAGE_DEFENSE_ABSENT
        return vide
    try:
        toutes = fusionner_defense_sources(
            lignes_dict(
                connexion.execute(
                    """
                    SELECT championnat, saison, equipe, joueur, matchs,
                           tacles, tacles_reussis, interceptions, blocs,
                           degagements, duels, duels_gagnes, recoveries,
                           pressions, arrets, xg_tirs_subis, source
                    FROM actions_defensives
                    WHERE lower(joueur) = lower(?)
                    ORDER BY saison DESC
                    """,
                    (nom_joueur,),
                )
            )
        )
        if not toutes:
            cible = normaliser(nom_joueur)
            cible_cle = cle_nom(nom_joueur)
            if len(cible) >= 5:
                candidates = lignes_dict(
                    connexion.execute(
                        """
                        SELECT championnat, saison, equipe, joueur, matchs,
                               tacles, tacles_reussis, interceptions, blocs,
                               degagements, duels, duels_gagnes, recoveries,
                               pressions, arrets, xg_tirs_subis, source
                        FROM actions_defensives
                        """
                    )
                )
                toutes = fusionner_defense_sources(
                    [
                        ligne
                        for ligne in candidates
                        if normaliser(ligne.get("joueur") or "") == cible
                        or cle_nom(ligne.get("joueur") or "") == cible_cle
                    ]
                )
    except sqlite3.OperationalError:
        return vide
    if not toutes:
        return vide
    toutes.sort(key=lambda x: (x.get("saison") or ""), reverse=True)
    return {
        "disponible": True,
        "message": (
            "Chiffres réels (StatsBomb Open Data et/ou Wyscout 2017-2018). "
            "Pas les 5 ligues 2025-2026. "
            "xG des tirs subis = xG StatsBomb des tirs, pas un PSxG."
        ),
        "saisons": toutes,
    }


def choisir_nom_dans_competition(connexion, championnat, saison, noms):
    """Nom tel qu'il apparait dans les matchs (ou le calendrier) de la competition."""
    return _choisir_nom_dans_competition(connexion, championnat, saison, noms)


def sommer_buts_equipe(connexion, saison, noms):
    """Buts marques par competition, saison donnee, noms deja alignes."""
    vides = defaultdict(lambda: {"buts": 0, "matchs": 0})
    if not noms:
        return vides
    connus = set(noms)
    competitions = list(LIGUES_NATIONALES) + [NOM_LDC]
    lignes = lister_buts_equipe_saison(connexion, saison, competitions, noms)
    for ligne in lignes:
        if ligne["buts_domicile"] is None or ligne["buts_exterieur"] is None:
            continue
        if ligne["domicile"] in connus:
            marques = int(ligne["buts_domicile"])
        elif ligne["exterieur"] in connus:
            marques = int(ligne["buts_exterieur"])
        else:
            continue
        stats = vides[ligne["championnat"]]
        stats["buts"] += marques
        stats["matchs"] += 1
    return vides


def resume_buts_equipe(connexion, saison, nom_equipe, championnat_page):
    """Championnat national + Ligue des champions + total, pour la saison."""
    noms = alias_noms_equipe(nom_equipe)
    par_comp = sommer_buts_equipe(connexion, saison, noms)
    buts_ldc = par_comp.get(NOM_LDC, {}).get("buts", 0)
    matchs_ldc = par_comp.get(NOM_LDC, {}).get("matchs", 0)
    ligue = championnat_page if championnat_page in LIGUES_NATIONALES else ""
    if not ligue:
        for nom_ligue in LIGUES_NATIONALES:
            if nom_ligue in par_comp:
                ligue = nom_ligue
                break
    buts_ligue = par_comp.get(ligue, {}).get("buts", 0) if ligue else 0
    matchs_ligue = par_comp.get(ligue, {}).get("matchs", 0) if ligue else 0
    return {
        "championnat": buts_ligue,
        "libelle_championnat": ligue or "Championnat",
        "ligue_des_champions": buts_ldc,
        "total": buts_ligue + buts_ldc,
        "matchs_championnat": matchs_ligue,
        "matchs_ldc": matchs_ldc,
        "alias": noms,
    }


def charger_matchs_radar_equipe(connexion, saison, noms):
    """Matchs joues ligue + LDC, pour les moyennes du radar."""
    competitions = list(LIGUES_NATIONALES) + [NOM_LDC]
    matchs = _lister_matchs_radar_equipe(connexion, saison, competitions, noms)
    for match in matchs:
        match["joue"] = True
    return matchs


def ldc_par_joueur_en_base(connexion, nom_joueur=None):
    """True seulement s'il existe des buteurs LDC (Understat n'en a pas)."""
    try:
        if nom_joueur:
            ligne = connexion.execute(
                """
                SELECT 1 FROM joueurs
                WHERE joueur = ? AND championnat = ?
                LIMIT 1
                """,
                (nom_joueur, NOM_LDC),
            ).fetchone()
        else:
            ligne = connexion.execute(
                "SELECT 1 FROM joueurs WHERE championnat = ? LIMIT 1",
                (NOM_LDC,),
            ).fetchone()
    except sqlite3.OperationalError:
        return False
    return bool(ligne)


def resume_buts_joueur(saisons, ldc_disponible):
    """Total = ligue. Pas de buts LDC inventes s'ils ne sont pas en base."""
    buts_ligue = 0
    buts_ldc = 0
    for ligne in saisons:
        n = int(nombre_ok(ligne.get("buts")))
        if ligne.get("championnat") == NOM_LDC:
            buts_ldc += n
        else:
            buts_ligue += n
    if ldc_disponible:
        return {
            "championnat": buts_ligue,
            "ligue_des_champions": buts_ldc,
            "total": buts_ligue + buts_ldc,
            "ldc_par_joueur": True,
            "message_ldc": "",
        }
    return {
        "championnat": buts_ligue,
        "ligue_des_champions": None,
        "total": buts_ligue,
        "ldc_par_joueur": False,
        "message_ldc": MESSAGE_LDC_JOUEUR,
    }


def joueurs_depuis_ligue(connexion, nom_equipe, saison):
    """Si la LDC n'a pas de joueurs, on reprend ceux du club en ligue nationale."""
    ligues = [nom for nom in CHAMPIONNATS if nom != NOM_LDC]
    places = ", ".join(["?"] * len(ligues))
    noms = [
        row[0]
        for row in connexion.execute(
            f"""
            SELECT DISTINCT equipe FROM joueurs
            WHERE saison = ? AND championnat IN ({places})
            """,
            (saison, *ligues),
        )
    ]
    nom_stats = nom_pour_joueurs(nom_equipe, noms)
    return lignes_dict(
        connexion.execute(
            f"""
            SELECT joueur, poste, matchs, minutes, buts, passes_decisives,
                   tirs, passes_cles, xg, xa, xg_chaine, xg_construction,
                   carton_jaune, carton_rouge, equipe
            FROM joueurs
            WHERE saison = ? AND championnat IN ({places})
              AND (equipe = ? OR equipe LIKE ? OR equipe LIKE ?)
            ORDER BY buts DESC, minutes DESC
            """,
            (
                saison,
                *ligues,
                nom_stats,
                nom_stats + ",%",
                "%," + nom_stats,
            ),
        )
    )


def charger_programme_saison(connexion, championnat, saison):
    joues = lister_matchs_joues_saison(connexion, championnat, saison)
    avenir = lire_calendrier(connexion, championnat, saison)
    programme = fusionner_programme(joues, avenir, championnat)
    joindre_journee(connexion, championnat, saison, programme)
    joindre_xg(connexion, championnat, saison, programme)
    return programme


def top_joueurs_accueil_par_ligue(connexion, colonne_tri, champs_stats):
    resultats = []
    for ligue in LIGUES_NATIONALES:
        saison = saison_avec_joueurs(connexion, ligue)
        joueurs = []
        if saison:
            joueurs = lignes_dict(
                connexion.execute(
                    f"""
                    SELECT joueur, equipe, poste, matchs, minutes, {champs_stats}
                    FROM joueurs
                    WHERE championnat = ? AND saison = ? AND minutes > 0
                    ORDER BY {colonne_tri} DESC, minutes DESC
                    LIMIT 5
                    """,
                    (ligue, saison),
                )
            )
            for joueur in joueurs:
                joueur["url_photo"] = photo_en_cache(connexion, joueur["joueur"])
        resultats.append(
            {
                "championnat": ligue,
                "saison": saison or "",
                "joueurs": joueurs,
            }
        )
    return resultats


def buteurs_par_ligue(connexion):
    return top_joueurs_accueil_par_ligue(connexion, "buts", "buts, xg")


def passeurs_par_ligue(connexion):
    return top_joueurs_accueil_par_ligue(
        connexion, "passes_decisives", "passes_decisives, xa"
    )


def choisir_jour_matchs(connexion, aujourd_hui):
    return choisir_prochain_jour(connexion, aujourd_hui)


def charger_matchs_jour(connexion, jour):
    joues = lister_matchs_joues_jour(connexion, jour)
    avenir = lister_calendrier_jour(connexion, jour)
    vus = {}
    programme = []
    for match in joues:
        cle = (match["championnat"], match["domicile"], match["exterieur"])
        item = {
            "date": match["date"],
            "heure": "",
            "journee": "",
            "championnat": match["championnat"],
            "saison": match["saison"],
            "domicile": match["domicile"],
            "exterieur": match["exterieur"],
            "buts_domicile": match.get("buts_domicile"),
            "buts_exterieur": match.get("buts_exterieur"),
            "joue": True,
        }
        vus[cle] = item
        programme.append(item)
    for match in avenir:
        cle = (match["championnat"], match["domicile"], match["exterieur"])
        if cle in vus:
            vus[cle]["heure"] = match.get("heure") or ""
            vus[cle]["journee"] = match.get("journee") or ""
            continue
        programme.append(
            {
                "date": match.get("date", ""),
                "heure": match.get("heure") or "",
                "journee": match.get("journee") or "",
                "championnat": match["championnat"],
                "saison": match["saison"],
                "domicile": match["domicile"],
                "exterieur": match["exterieur"],
                "buts_domicile": None,
                "buts_exterieur": None,
                "joue": False,
            }
        )
    programme.sort(
        key=lambda m: (m.get("heure") or "", m["championnat"], m["domicile"])
    )
    enrichir_horaires(programme)
    ajouter_logos_programme(connexion, programme)
    return programme


def enrichir_avec_prevision_figee(resultat, championnat, saison, nom_domicile, nom_exterieur):
    """
    Si une prevision a ete enregistree avant le match, l'exposer et
    (pour un match joue) recalculer bilan/comparaison sur la prevision FIGEE.
    """
    resultat["prevision_figee"] = None
    connexion_hist = None
    try:
        connexion_hist = ouvrir_analyses()
        date_ref = None
        match_joue = resultat.get("match_joue") or {}
        if match_joue.get("joue"):
            date_ref = match_joue.get("date")
        else:
            a_venir = resultat.get("match_a_venir") or {}
            date_ref = a_venir.get("date")

        prevision = None
        if date_ref:
            prevision = lire_prevision_figee(
                connexion_hist, championnat, saison, date_ref, nom_domicile, nom_exterieur
            )
        if not prevision:
            prevision = lire_prevision_sans_date(
                connexion_hist, championnat, saison, nom_domicile, nom_exterieur
            )
        if not prevision:
            return

        pred_figee = pred_depuis_prevision_figee(prevision)
        meta = {
            "genere_le": prevision.get("genere_le"),
            "version_modele": prevision.get("version_modele"),
            "date_match": prevision.get("date_match"),
            "prediction": pred_figee,
        }
        resultat_hist = lire_resultat(connexion_hist, prevision["id"])
        if resultat_hist:
            meta["resultat"] = {
                "match_joue_le": resultat_hist.get("match_joue_le"),
                "issue_reelle": resultat_hist.get("issue_reelle"),
                "score_exact_ok": resultat_hist.get("score_exact_ok"),
                "bilan": resultat_hist.get("bilan"),
            }

        resultat["prevision_figee"] = meta

        # Match joue + prevision figee : remplacer les champs predictifs live
        # pour que le bilan affiche la prevision enregistree (pas un recalcul).
        if not match_joue.get("joue"):
            return

        live = resultat.get("prediction") or {}
        fusion = dict(live)
        for cle in (
            "xg_prevu_domicile",
            "xg_prevu_exterieur",
            "xg_total",
            "score_plus_probable",
            "probabilite_score",
            "commentaire_score",
            "scores_frequents",
            "p_victoire_domicile",
            "p_nul",
            "p_victoire_exterieur",
            "p_les_deux_marquent",
            "p_plus_de_2_buts",
            "cartons",
            "scenarios",
            "recit",
            "texte",
        ):
            if cle in pred_figee:
                fusion[cle] = pred_figee[cle]
        if resultat_hist and resultat_hist.get("bilan"):
            bilan_stocke = resultat_hist["bilan"]
            fusion["bilan"] = {
                "points": bilan_stocke.get("points") or [],
            }
            if bilan_stocke.get("comparaison"):
                fusion["comparaison"] = bilan_stocke["comparaison"]
            else:
                fusion["comparaison"] = comparaison_previsions_reel(pred_figee, match_joue)
        else:
            fusion["bilan"] = _bilan_match(pred_figee, match_joue)
            fusion["comparaison"] = comparaison_previsions_reel(pred_figee, match_joue)
        fusion["depuis_historique"] = True
        fusion["genere_le"] = prevision.get("genere_le")
        resultat["prediction"] = fusion
    except Exception:
        # L'historique ne doit jamais casser l'analyse live.
        return
    finally:
        if connexion_hist is not None:
            connexion_hist.close()
DOSSIER_PHOTOS.mkdir(parents=True, exist_ok=True)
app.mount("/photos", StaticFiles(directory=str(DOSSIER_PHOTOS)), name="photos")
