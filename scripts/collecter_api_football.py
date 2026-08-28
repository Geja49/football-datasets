"""
Collecte optionnelle API-Football (api-sports.io).

Sans CLE_API_FOOTBALL : skip propre (rien n'est ecrit).
Avec cle (priorite free tier ~100 req/jour) :
  1) fixtures / scores recents : Big 5 + Super Lig (+ LDC si quota)
     → fusion anti-doublons dans matchs.csv et calendrier.csv
  2) stats joueurs defensives (une ligue, paginees, cache) si quota restant

Rotation : 1–2 ligues domestiques par jour + LDC en bonus.
Pas de cotes. Pas de telechargement massif.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "site" / "api"))
from correspondances import nom_pour_calendrier, normaliser
from defense_commune import (
    COLONNES_COUVERTURE,
    COLONNES_DEFENSE,
    FICHIER_COUVERTURE,
    FICHIER_DEFENSE,
    charger_env,
    ecrire_csv,
    lire_csv,
    remplacer_source,
    stats_vides,
    ligne_defense,
)

RACINE = Path(__file__).resolve().parents[1]
DOSSIER_SORTIE = Path("donnees/cinq_championnats")
SOURCE = "api-football"
URL_BASE = "https://v3.football.api-sports.io"
DOSSIER_CACHE = Path("donnees/cache_api_football")
PAUSE = 1.2
QUOTA_MINIMUM = 12
# Annee de debut de saison API (2026 → saison 2026-2027).
ANNEE_SAISON = 2026
SAISON = f"{ANNEE_SAISON}-{ANNEE_SAISON + 1}"
LIGUES_PAR_JOUR = 2
JOURS_PASSE = 14
JOURS_AVENIR = 21

STATUTS_TERMINES = frozenset({"FT", "AET", "PEN"})

# Une seule ligue joueurs par run (pages nombreuses).
LIGUES = (
    {"id": 39, "nom": "Premier League"},
    {"id": 140, "nom": "La Liga"},
    {"id": 78, "nom": "Bundesliga"},
    {"id": 135, "nom": "Serie A"},
    {"id": 61, "nom": "Ligue 1"},
    {"id": 203, "nom": "Super Lig"},
)
LIGUE_LDC = {"id": 2, "nom": "Ligue des champions", "ldc": True}

CHAMPS_VIDES_MATCH = {
    "buts_domicile_mt": "",
    "buts_exterieur_mt": "",
    "resultat_mt": "",
    "arbitre": "",
    "tirs_domicile": "",
    "tirs_exterieur": "",
    "tirs_cadres_domicile": "",
    "tirs_cadres_exterieur": "",
    "fautes_domicile": "",
    "fautes_exterieur": "",
    "corners_domicile": "",
    "corners_exterieur": "",
    "jaunes_domicile": "",
    "jaunes_exterieur": "",
    "rouges_domicile": "",
    "rouges_exterieur": "",
}


def quota_restant(reponse):
    """Lit le quota restant. None si header absent (ne pas confondre avec 0)."""
    brut = reponse.headers.get("x-ratelimit-requests-remaining")
    if brut is None or brut == "":
        return None
    try:
        return int(brut)
    except ValueError:
        return None


def formater_erreurs_api(data):
    """Extrait le message d'erreur API-Football (dict ou liste)."""
    if not isinstance(data, dict):
        return ""
    erreurs = data.get("errors")
    if not erreurs:
        return ""
    if isinstance(erreurs, dict):
        parties = [f"{k}: {v}" for k, v in erreurs.items() if v]
        return " ; ".join(parties)
    if isinstance(erreurs, list):
        return " ; ".join(str(e) for e in erreurs if e)
    return str(erreurs)


def est_erreur_plan_saison(message):
    bas = (message or "").lower()
    return "free plans do not have access to this season" in bas or (
        "plan" in bas and "season" in bas
    )


def message_quota_epuise(restant=0):
    print(
        f"   quota journalier epuise (restant={restant}). "
        "Attendre le reset quotidien (dashboard api-football) "
        "ou passer au plan Pro."
    )


def message_plan_saison(detail=""):
    print(
        f"   plan free : saison {ANNEE_SAISON} inaccessible"
        + (f" ({detail})" if detail else "")
        + ". Free = saisons historiques (souvent 2022–2024) ; "
        "fixtures 2026-2027 = plan Pro. "
        "Verifier la cle sur https://dashboard.api-football.com "
        "(pas RapidAPI)."
    )


def resultat_depuis_buts(buts_d, buts_e):
    try:
        d, e = int(buts_d), int(buts_e)
    except (TypeError, ValueError):
        return ""
    if d > e:
        return "H"
    if d < e:
        return "A"
    return "D"


def equipes_compatibles(a, b):
    na = normaliser(a or "")
    nb = normaliser(b or "")
    if not na or not nb:
        return False
    if na == nb:
        return True
    if len(na) >= 5 and len(nb) >= 5 and (na in nb or nb in na):
        return True
    return False


def noms_connus(matchs, championnat, saison):
    noms = set()
    for match in matchs:
        if match.get("championnat") != championnat or match.get("saison") != saison:
            continue
        noms.add(match.get("domicile") or "")
        noms.add(match.get("exterieur") or "")
    noms.discard("")
    return noms


def aligner_equipe(nom_brut, noms):
    if not nom_brut:
        return ""
    if nom_brut in noms:
        return nom_brut
    aligne = nom_pour_calendrier(nom_brut, noms)
    if aligne in noms:
        return aligne
    for connu in noms:
        if equipes_compatibles(nom_brut, connu):
            return connu
    return nom_brut.strip()


def ecrire_csv_matchs(chemin, lignes):
    if not lignes:
        return
    champs = []
    vus = set()
    for ligne in lignes:
        for nom in ligne:
            if nom not in vus:
                vus.add(nom)
                champs.append(nom)
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", newline="", encoding="utf-8") as fichier:
        writer = csv.DictWriter(fichier, fieldnames=champs, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(lignes)


def _lire_json_cache(chemin):
    """Lit un cache JSON ; ignore et supprime les reponses d'erreur API."""
    if not chemin.exists():
        return None
    data = json.loads(chemin.read_text(encoding="utf-8"))
    if formater_erreurs_api(data):
        chemin.unlink(missing_ok=True)
        return None
    return data


def lire_page_cache_joueurs(ligue_id, page):
    return _lire_json_cache(
        DOSSIER_CACHE / f"joueurs_{ligue_id}_{ANNEE_SAISON}_{page}.json"
    )


def sauver_page_joueurs(ligue_id, page, data):
    if formater_erreurs_api(data):
        return
    DOSSIER_CACHE.mkdir(parents=True, exist_ok=True)
    chemin = DOSSIER_CACHE / f"joueurs_{ligue_id}_{ANNEE_SAISON}_{page}.json"
    chemin.write_text(json.dumps(data), encoding="utf-8")


def chemin_cache_fixtures(ligue_id, debut, fin):
    return DOSSIER_CACHE / f"fixtures_{ligue_id}_{ANNEE_SAISON}_{debut}_{fin}.json"


def lire_cache_fixtures(ligue_id, debut, fin):
    return _lire_json_cache(chemin_cache_fixtures(ligue_id, debut, fin))


def sauver_cache_fixtures(ligue_id, debut, fin, data):
    if formater_erreurs_api(data):
        return
    DOSSIER_CACHE.mkdir(parents=True, exist_ok=True)
    chemin_cache_fixtures(ligue_id, debut, fin).write_text(
        json.dumps(data), encoding="utf-8"
    )


def choisir_ligue_joueurs():
    """Reprend la premiere ligue sans cache joueurs complet."""
    for ligue in LIGUES:
        marqueur = DOSSIER_CACHE / f"complet_{ligue['id']}_{ANNEE_SAISON}.txt"
        if not marqueur.exists():
            return ligue
    return LIGUES[0]


def choisir_ligues_fixtures():
    """
    Rotation journaliere : 1–2 ligues domestiques + LDC en fin de liste.
    L'index tourne avec le jour (ordinal) pour repartir le quota.
    """
    index = date.today().toordinal() % len(LIGUES)
    selection = []
    for i in range(min(LIGUES_PAR_JOUR, len(LIGUES))):
        selection.append(LIGUES[(index + i) % len(LIGUES)])
    selection.append(LIGUE_LDC)
    return selection


def fenetre_dates(aujourdhui=None):
    jour = aujourdhui or date.today()
    debut = (jour - timedelta(days=JOURS_PASSE)).isoformat()
    fin = (jour + timedelta(days=JOURS_AVENIR)).isoformat()
    return debut, fin


def parser_fixture(item, championnat, noms):
    """Transforme une reponse fixtures API en ligne match ou calendrier."""
    fixture = item.get("fixture") or {}
    teams = item.get("teams") or {}
    goals = item.get("goals") or {}
    league = item.get("league") or {}
    statut = ((fixture.get("status") or {}).get("short") or "").upper()
    date_brut = fixture.get("date") or ""
    try:
        dt = datetime.fromisoformat(date_brut.replace("Z", "+00:00"))
        date_iso = dt.date().isoformat()
        heure = dt.strftime("%H:%M")
    except ValueError:
        date_iso = (date_brut or "")[:10]
        heure = ""
    domicile = aligner_equipe((teams.get("home") or {}).get("name") or "", noms)
    exterieur = aligner_equipe((teams.get("away") or {}).get("name") or "", noms)
    if not domicile or not exterieur or not date_iso:
        return None
    round_api = (league.get("round") or "").strip()
    buts_d = goals.get("home")
    buts_e = goals.get("away")
    termine = statut in STATUTS_TERMINES and buts_d is not None and buts_e is not None
    if termine:
        ligne = {
            "championnat": championnat,
            "saison": SAISON,
            "date": date_iso,
            "domicile": domicile,
            "exterieur": exterieur,
            "buts_domicile": int(buts_d),
            "buts_exterieur": int(buts_e),
            "resultat": resultat_depuis_buts(buts_d, buts_e),
            **CHAMPS_VIDES_MATCH,
        }
        if championnat == LIGUE_LDC["nom"]:
            ligne["phase"] = round_api or "phase de ligue"
        return {"type": "match", "ligne": ligne}
    return {
        "type": "calendrier",
        "ligne": {
            "championnat": championnat,
            "saison": SAISON,
            "date": date_iso,
            "heure": heure,
            "domicile": domicile,
            "exterieur": exterieur,
            "journee": round_api,
        },
    }


def trouver_index_match(existants, candidat):
    for i, ligne in enumerate(existants):
        if ligne.get("championnat") != candidat.get("championnat"):
            continue
        if ligne.get("saison") != candidat.get("saison"):
            continue
        if ligne.get("date") != candidat.get("date"):
            continue
        if equipes_compatibles(ligne.get("domicile"), candidat.get("domicile")) and (
            equipes_compatibles(ligne.get("exterieur"), candidat.get("exterieur"))
        ):
            return i
    return None


def fusionner_matchs(existants, nouveaux):
    """Met a jour les scores existants ou ajoute les matchs termines absents."""
    resultat = [dict(l) for l in existants]
    maj = 0
    ajouts = 0
    for candidat in nouveaux:
        idx = trouver_index_match(resultat, candidat)
        if idx is None:
            resultat.append(dict(candidat))
            ajouts += 1
            continue
        cible = resultat[idx]
        change = False
        for cle in ("buts_domicile", "buts_exterieur", "resultat"):
            nouveau_val = candidat.get(cle)
            if nouveau_val is None or nouveau_val == "":
                continue
            ancien = cible.get(cle)
            if str(ancien) != str(nouveau_val):
                cible[cle] = nouveau_val
                change = True
        if change:
            maj += 1
    return resultat, maj, ajouts


def deja_au_calendrier(ligne, index_par_date, joues_index):
    cle_date = (ligne.get("championnat"), ligne.get("saison"), ligne.get("date"))
    for domicile, exterieur in joues_index.get(cle_date, []):
        if equipes_compatibles(ligne.get("domicile"), domicile) and equipes_compatibles(
            ligne.get("exterieur"), exterieur
        ):
            return True
    for domicile, exterieur in index_par_date.get(cle_date, []):
        if equipes_compatibles(ligne.get("domicile"), domicile) and equipes_compatibles(
            ligne.get("exterieur"), exterieur
        ):
            return True
    return False


def fusionner_calendrier(existant, ajouts, matchs_joues):
    """Ajoute les a venir absents ; retire ceux deja joues (anti-doublons)."""
    joues_index = {}
    for m in matchs_joues:
        cle = (m.get("championnat"), m.get("saison"), m.get("date"))
        joues_index.setdefault(cle, []).append((m.get("domicile"), m.get("exterieur")))

    filtre = []
    for l in existant:
        cle = (l.get("championnat"), l.get("saison"), l.get("date"))
        est_joue = False
        for domicile, exterieur in joues_index.get(cle, []):
            if equipes_compatibles(l.get("domicile"), domicile) and equipes_compatibles(
                l.get("exterieur"), exterieur
            ):
                est_joue = True
                break
        if not est_joue:
            filtre.append(l)

    index = {}
    for l in filtre:
        cle = (l.get("championnat"), l.get("saison"), l.get("date"))
        index.setdefault(cle, []).append((l.get("domicile"), l.get("exterieur")))

    resultat = list(filtre)
    nb = 0
    for ligne in ajouts:
        if not ligne.get("domicile") or not ligne.get("exterieur"):
            continue
        if deja_au_calendrier(ligne, index, joues_index):
            continue
        cle = (ligne.get("championnat"), ligne.get("saison"), ligne.get("date"))
        index.setdefault(cle, []).append((ligne.get("domicile"), ligne.get("exterieur")))
        resultat.append(dict(ligne))
        nb += 1
    resultat.sort(
        key=lambda x: (
            x.get("championnat") or "",
            x.get("saison") or "",
            x.get("date") or "",
            x.get("heure") or "",
            x.get("domicile") or "",
        )
    )
    return resultat, nb


def requete_json(session, chemin, params, cache_lire, cache_sauver):
    """GET API avec cache disque. Retourne (data, restant|None, depuis_cache)."""
    cache = cache_lire()
    if cache is not None:
        return cache, None, True
    try:
        reponse = session.get(f"{URL_BASE}{chemin}", params=params, timeout=30)
    except requests.RequestException as exc:
        print(f"   requete impossible ({exc})")
        return None, None, False
    if reponse.status_code == 429:
        message_quota_epuise(0)
        return None, 0, False
    if reponse.status_code in (401, 403):
        print(
            f"   HTTP {reponse.status_code} : cle invalide ou non autorisee. "
            "Verifier CLE_API_FOOTBALL sur dashboard.api-football.com "
            "(header x-apisports-key, pas RapidAPI)."
        )
        return None, quota_restant(reponse), False
    if reponse.status_code != 200:
        print(f"   HTTP {reponse.status_code}, ignore.")
        return None, quota_restant(reponse), False
    restant = quota_restant(reponse)
    data = reponse.json()
    # Ne jamais mettre en cache une reponse d'erreur (sinon 0 matchs « fantomes »).
    if not formater_erreurs_api(data):
        cache_sauver(data)
    time.sleep(PAUSE)
    return data, restant, False


def collecter_fixtures_ligue(session, ligue, matchs_existants, debut, fin):
    noms = noms_connus(matchs_existants, ligue["nom"], SAISON)
    # Pour la LDC, elargir aux clubs deja connus toutes saisons.
    if ligue.get("ldc"):
        for match in matchs_existants:
            if match.get("championnat") == ligue["nom"]:
                noms.add(match.get("domicile") or "")
                noms.add(match.get("exterieur") or "")
        noms.discard("")

    data, restant, depuis_cache = requete_json(
        session,
        "/fixtures",
        {
            "league": ligue["id"],
            "season": ANNEE_SAISON,
            "from": debut,
            "to": fin,
        },
        lambda: lire_cache_fixtures(ligue["id"], debut, fin),
        lambda d: sauver_cache_fixtures(ligue["id"], debut, fin, d),
    )
    if data is None:
        return [], [], restant, False, False

    detail_err = formater_erreurs_api(data)
    if detail_err:
        if est_erreur_plan_saison(detail_err):
            message_plan_saison(detail_err)
            return [], [], restant, False, True
        print(f"   {ligue['nom']}: erreur API — {detail_err}")
        return [], [], restant, False, False

    matchs = []
    calendrier = []
    for item in data.get("response") or []:
        parse = parser_fixture(item, ligue["nom"], noms)
        if not parse:
            continue
        if parse["type"] == "match":
            matchs.append(parse["ligne"])
        else:
            calendrier.append(parse["ligne"])
    source = "cache" if depuis_cache else "API"
    print(
        f"   {ligue['nom']}: {len(matchs)} termines, "
        f"{len(calendrier)} a venir ({source})"
    )
    if not matchs and not calendrier:
        print(
            f"   {ligue['nom']}: 0 resultat (ligue={ligue['id']}, "
            f"season={ANNEE_SAISON}, {debut}→{fin}). "
            "Verifier saison/ids ou quota sur le dashboard."
        )
    return matchs, calendrier, restant, True, False


def collecter_joueurs(session, restant_initial=None):
    """Stats defensives joueurs — une ligue, pages cachees (couteux en quota)."""
    if restant_initial is not None and restant_initial <= 0:
        message_quota_epuise(restant_initial)
        print("   stats joueurs ignorees.")
        return [], []
    if restant_initial is not None and restant_initial < QUOTA_MINIMUM:
        print(
            f"   stats joueurs ignorees (quota restant {restant_initial} "
            f"< {QUOTA_MINIMUM})."
        )
        return [], []

    ligue = choisir_ligue_joueurs()
    page = 1
    pages_total = 1
    fusion = {}
    restant = restant_initial
    while page <= pages_total:
        cache = lire_page_cache_joueurs(ligue["id"], page)
        if cache is None:
            if restant is not None and restant < QUOTA_MINIMUM:
                print(f"   quota restant {restant}, stop stats joueurs.")
                break
            try:
                reponse = session.get(
                    f"{URL_BASE}/players",
                    params={
                        "league": ligue["id"],
                        "season": ANNEE_SAISON,
                        "page": page,
                    },
                    timeout=30,
                )
            except requests.RequestException as exc:
                print(f"   requete joueurs impossible ({exc})")
                break
            if reponse.status_code == 429:
                message_quota_epuise(0)
                break
            if reponse.status_code != 200:
                print(f"   joueurs HTTP {reponse.status_code}, ignore.")
                break
            restant = quota_restant(reponse)
            cache = reponse.json()
            detail_err = formater_erreurs_api(cache)
            if detail_err:
                if est_erreur_plan_saison(detail_err):
                    message_plan_saison(detail_err)
                else:
                    print(f"   joueurs: erreur API — {detail_err}")
                break
            sauver_page_joueurs(ligue["id"], page, cache)
            if restant and restant < QUOTA_MINIMUM:
                print(f"   quota restant {restant}, derniere page joueurs.")
                pages_total = page
            time.sleep(PAUSE)
        paging = cache.get("paging") or {}
        pages_total = int(paging.get("total") or page)
        for item in cache.get("response") or []:
            fiche = item.get("player") or {}
            for bloc in item.get("statistics") or []:
                equipe = ((bloc.get("team") or {}).get("name")) or ""
                joueur = (fiche.get("name") or "").strip()
                if not joueur or not equipe:
                    continue
                tacles = bloc.get("tackles") or {}
                duels = bloc.get("duels") or {}
                gardien = bloc.get("goalkeeper") or {}
                jeux = bloc.get("games") or {}
                cle_j = (ligue["nom"], equipe, joueur)
                if cle_j not in fusion:
                    fusion[cle_j] = stats_vides()
                stats = fusion[cle_j]
                stats["matchs_ids"].add(page)
                stats["tacles"] += int(tacles.get("total") or 0)
                stats["interceptions"] += int(tacles.get("interceptions") or 0)
                stats["blocs"] += int(tacles.get("blocks") or 0)
                stats["duels"] += int(duels.get("total") or 0)
                stats["duels_gagnes"] += int(duels.get("won") or 0)
                stats["arrets"] += int(gardien.get("saves") or 0)
                apparitions = int(
                    jeux.get("appearences") or jeux.get("appearances") or 0
                )
                if apparitions:
                    stats["matchs_ids"] = set(range(apparitions))
        print(f"   {ligue['nom']} joueurs page {page}/{pages_total}")
        page += 1

    if pages_total >= 1 and page > pages_total:
        marqueur = DOSSIER_CACHE / f"complet_{ligue['id']}_{ANNEE_SAISON}.txt"
        DOSSIER_CACHE.mkdir(parents=True, exist_ok=True)
        marqueur.write_text("ok", encoding="utf-8")

    lignes = [
        ligne_defense(championnat, SAISON, equipe, joueur, stats, SOURCE)
        for (championnat, equipe, joueur), stats in fusion.items()
    ]
    if not lignes:
        print("   aucune ligne joueurs (saison vide ou quota).")
        return [], []
    remplacer_source(FICHIER_DEFENSE, SOURCE, lignes, COLONNES_DEFENSE)
    couverture = [
        {
            "championnat": ligue["nom"],
            "saison": SAISON,
            "source": SOURCE,
            "nb_matchs": "",
            "complet": 0,
            "commentaire": (
                "Fixtures + stats joueurs API ; une ligue joueurs a la fois, cachees."
            ),
        }
    ]
    anciennes = [l for l in lire_csv(FICHIER_COUVERTURE) if l.get("source") != SOURCE]
    ecrire_csv(FICHIER_COUVERTURE, anciennes + couverture, COLONNES_COUVERTURE)
    print(f"   {len(lignes)} joueurs {ligue['nom']} {SAISON}")
    return lignes, couverture


def collecter():
    charger_env(RACINE)
    cle = (os.environ.get("CLE_API_FOOTBALL") or "").strip()
    print("API-Football (optionnel)...")
    if not cle:
        print("   API-Football ignoree (pas de cle)")
        return {
            "matchs_maj": 0,
            "matchs_ajoutes": 0,
            "calendrier_ajoutes": 0,
            "joueurs": 0,
        }

    session = requests.Session()
    session.headers.update(
        {
            "x-apisports-key": cle,
            "User-Agent": "StatsChampionnats/1.0 (projet local; API-Football)",
        }
    )

    chemin_matchs = DOSSIER_SORTIE / "matchs.csv"
    chemin_calendrier = DOSSIER_SORTIE / "calendrier.csv"
    matchs = lire_csv(chemin_matchs)
    calendrier = lire_csv(chemin_calendrier)
    debut, fin = fenetre_dates()
    print(f"   fenetre fixtures {debut} → {fin} (saison {SAISON})")

    nouveaux_matchs = []
    nouveaux_cal = []
    restant = None
    for ligue in choisir_ligues_fixtures():
        if restant is not None and restant <= 0:
            message_quota_epuise(restant)
            break
        if restant is not None and restant < QUOTA_MINIMUM:
            print(
                f"   quota restant {restant} (< {QUOTA_MINIMUM}), stop fixtures. "
                "Attendre le reset quotidien ou plan Pro."
            )
            break
        # LDC seulement si encore du quota apres les ligues du jour.
        if ligue.get("ldc") and restant is not None and restant < QUOTA_MINIMUM + 5:
            print("   LDC ignoree (quota reserve).")
            break
        m, c, restant, ok, plan_bloque = collecter_fixtures_ligue(
            session, ligue, matchs, debut, fin
        )
        if plan_bloque:
            print("   arret : plan free incompatible avec la saison courante.")
            break
        if not ok:
            if restant is not None and restant <= 0:
                message_quota_epuise(restant)
                break
            continue
        nouveaux_matchs.extend(m)
        nouveaux_cal.extend(c)

    matchs, nb_maj, nb_ajouts = fusionner_matchs(matchs, nouveaux_matchs)
    calendrier, nb_cal = fusionner_calendrier(calendrier, nouveaux_cal, matchs)
    if nb_maj or nb_ajouts:
        ecrire_csv_matchs(chemin_matchs, matchs)
    if nb_cal or nouveaux_matchs:
        ecrire_csv_matchs(chemin_calendrier, calendrier)

    print(f"   {nb_maj} matchs mis a jour, {nb_ajouts} matchs ajoutes")
    print(f"   {nb_cal} lignes calendrier ajoutees")

    # Secondaire : stats joueurs seulement si on connait le quota restant.
    if restant is None:
        print("   stats joueurs ignorees (fixtures en cache ; quota non mesure).")
        return {
            "matchs_maj": nb_maj,
            "matchs_ajoutes": nb_ajouts,
            "calendrier_ajoutes": nb_cal,
            "joueurs": 0,
        }
    lignes_j, _ = collecter_joueurs(session, restant_initial=restant)
    return {
        "matchs_maj": nb_maj,
        "matchs_ajoutes": nb_ajouts,
        "calendrier_ajoutes": nb_cal,
        "joueurs": len(lignes_j),
    }


def main():
    collecter()


if __name__ == "__main__":
    main()
