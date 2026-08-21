"""
Cotes des matchs a venir (The Odds API), cote serveur uniquement.

Cles sports : https://the-odds-api.com/sports-odds-data/sports-apis.html
La cle (CLE_API_COTES ou ODDS_API_KEY) ne sort jamais du serveur.
"""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import os
import sqlite3
import threading
import time

import requests
from fastapi import APIRouter, HTTPException, Query

RACINE = Path(__file__).resolve().parents[2]
FICHIER_BASE = RACINE / "donnees" / "football.db"
URL_BASE = "https://api.the-odds-api.com/v4/sports"
TIMEOUT_HTTP = 12
DUREE_CACHE_OK = 45 * 60
DUREE_CACHE_ERREUR = 10 * 60
MAX_BOOKMAKERS = 3
LIMITE_CALENDRIER = 80
JOURS_CALENDRIER = 45

# Doc officielle The Odds API (sports-apis.html), aout 2026.
COMPETITIONS = (
    ("soccer_epl", "Premier League"),
    ("soccer_spain_la_liga", "La Liga"),
    ("soccer_germany_bundesliga", "Bundesliga"),
    ("soccer_italy_serie_a", "Serie A"),
    ("soccer_france_ligue_one", "Ligue 1"),
    ("soccer_uefa_champs_league", "Ligue des champions"),
)
NOMS_COMPETITIONS = tuple(nom for _, nom in COMPETITIONS)
PREFERENCE_BOOKMAKERS = (
    "pinnacle",
    "betfair_ex_eu",
    "unibet",
    "bet365",
    "1xbet",
    "williamhill",
    "bwin",
    "unibet_eu",
)

MESSAGES = {
    "sans_cle": (
        "Configurez CLE_API_COTES (ou ODDS_API_KEY) dans le fichier .env "
        "à la racine du projet pour afficher les cotes."
    ),
    "cle_refusee": "Clé API cotes refusée. Vérifiez CLE_API_COTES.",
    "quota": "Quota The Odds API atteint. Réessayez plus tard.",
    "service_indisponible": "Les cotes sont temporairement indisponibles.",
}

routeur_cotes = APIRouter()
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "StatsChampionnats/1.0 (cotes matchs a venir)"})

_verrou = threading.Lock()
_cache = {"expire": 0.0, "matchs": None, "erreur": ""}


def charger_fichier_env():
    chemin = RACINE / ".env"
    if not chemin.exists():
        return
    for brut in chemin.read_text(encoding="utf-8").splitlines():
        ligne = brut.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        cle = cle.strip()
        valeur = valeur.strip().strip('"').strip("'")
        if cle and cle not in os.environ:
            os.environ[cle] = valeur


def lire_cle_api():
    charger_fichier_env()
    return (os.environ.get("CLE_API_COTES") or os.environ.get("ODDS_API_KEY") or "").strip()


def parser_instant(texte):
    if not texte:
        return None
    texte = str(texte).replace("Z", "+00:00")
    try:
        instant = datetime.fromisoformat(texte)
    except ValueError:
        return None
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant


def est_a_venir(instant):
    return instant is not None and instant > datetime.now(timezone.utc)


def arrondir_cote(valeur):
    try:
        nombre = float(valeur)
    except (TypeError, ValueError):
        return None
    if nombre != nombre or nombre <= 1:
        return None
    return round(nombre, 2)


def extraire_1n2(marches, nom_domicile, nom_exterieur):
    for marche in marches or []:
        if marche.get("key") != "h2h":
            continue
        domicile = nul = exterieur = None
        for issue in marche.get("outcomes") or []:
            nom = issue.get("name") or ""
            prix = arrondir_cote(issue.get("price"))
            if prix is None:
                continue
            nom_bas = nom.strip().lower()
            if nom_bas in ("draw", "tie", "x"):
                nul = prix
            elif nom == nom_domicile:
                domicile = prix
            elif nom == nom_exterieur:
                exterieur = prix
        if domicile and nul and exterieur:
            return {"domicile": domicile, "nul": nul, "exterieur": exterieur}
    return None


def moyenne_cotes(liste):
    if not liste:
        return None
    n = len(liste)
    return {
        "domicile": round(sum(c["domicile"] for c in liste) / n, 2),
        "nul": round(sum(c["nul"] for c in liste) / n, 2),
        "exterieur": round(sum(c["exterieur"] for c in liste) / n, 2),
    }


def meilleure_cotes(liste):
    if not liste:
        return None
    return {
        "domicile": max(c["domicile"] for c in liste),
        "nul": max(c["nul"] for c in liste),
        "exterieur": max(c["exterieur"] for c in liste),
    }


def brut_event_noms(evenement):
    return evenement.get("home_team") or "", evenement.get("away_team") or ""


def choisir_bookmakers(evenement):
    domicile, exterieur = brut_event_noms(evenement)
    complets = []
    for book in evenement.get("bookmakers") or []:
        cotes = extraire_1n2(book.get("markets"), domicile, exterieur)
        if not cotes:
            continue
        complets.append(
            {
                "cle": book.get("key") or "",
                "nom": (book.get("title") or book.get("key") or "").strip(),
                **cotes,
            }
        )
    rang = {cle: index for index, cle in enumerate(PREFERENCE_BOOKMAKERS)}
    complets.sort(key=lambda b: (rang.get(b["cle"], 99), b["nom"]))
    pris = []
    vus = set()
    for book in complets:
        nom = book["nom"]
        if not nom or nom in vus:
            continue
        vus.add(nom)
        pris.append(
            {
                "nom": nom,
                "domicile": book["domicile"],
                "nul": book["nul"],
                "exterieur": book["exterieur"],
            }
        )
        if len(pris) >= MAX_BOOKMAKERS:
            break
    return pris, complets


def normaliser_evenement(evenement, championnat):
    instant = parser_instant(evenement.get("commence_time"))
    if not est_a_venir(instant):
        return None
    domicile, exterieur = brut_event_noms(evenement)
    if not domicile or not exterieur:
        return None
    bookmakers, toutes = choisir_bookmakers(evenement)
    cotes_brutes = [
        {
            "domicile": b["domicile"],
            "nul": b["nul"],
            "exterieur": b["exterieur"],
        }
        for b in toutes
    ]
    return {
        "championnat": championnat,
        "date": instant.date().isoformat(),
        "heure": instant.strftime("%H:%M"),
        "commence_at": instant.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "domicile": domicile,
        "exterieur": exterieur,
        "cotes": {
            "moyenne": moyenne_cotes(cotes_brutes),
            "meilleure": meilleure_cotes(cotes_brutes),
        }
        if cotes_brutes
        else None,
        "bookmakers": bookmakers,
    }


def telecharger_sport(cle_api, cle_sport):
    url = f"{URL_BASE}/{cle_sport}/odds"
    try:
        reponse = SESSION.get(
            url,
            params={
                "apiKey": cle_api,
                "regions": "eu",
                "markets": "h2h",
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            },
            timeout=TIMEOUT_HTTP,
        )
    except requests.RequestException:
        return None, "service_indisponible"
    if reponse.status_code == 401:
        return None, "cle_refusee"
    if reponse.status_code == 429:
        return None, "quota"
    if reponse.status_code >= 400:
        return None, "service_indisponible"
    try:
        data = reponse.json()
    except ValueError:
        return None, "service_indisponible"
    if not isinstance(data, list):
        return None, "service_indisponible"
    return data, None


def telecharger_tous(cle_api):
    matchs = []
    erreur = ""
    for cle_sport, nom in COMPETITIONS:
        data, code = telecharger_sport(cle_api, cle_sport)
        if code == "cle_refusee" or code == "quota":
            return [], code
        if code:
            erreur = code
            continue
        for evenement in data:
            item = normaliser_evenement(evenement, nom)
            if item:
                matchs.append(item)
    matchs.sort(key=lambda m: (NOMS_COMPETITIONS.index(m["championnat"]), m["commence_at"]))
    return matchs, erreur


def matchs_depuis_calendrier():
    if not FICHIER_BASE.exists():
        return []
    connexion = sqlite3.connect(FICHIER_BASE)
    connexion.row_factory = sqlite3.Row
    aujourd = date.today().isoformat()
    horizon = (date.today() + timedelta(days=JOURS_CALENDRIER)).isoformat()
    placeholders = ",".join("?" * len(NOMS_COMPETITIONS))
    params = [aujourd, horizon, *NOMS_COMPETITIONS]
    lignes = []
    try:
        try:
            lignes = connexion.execute(
                f"""
                SELECT date, heure, championnat, domicile, exterieur
                FROM calendrier
                WHERE date >= ? AND date <= ?
                  AND championnat IN ({placeholders})
                ORDER BY date, heure, championnat
                LIMIT {LIMITE_CALENDRIER}
                """,
                params,
            ).fetchall()
        except sqlite3.OperationalError:
            lignes = []
        if not lignes:
            try:
                lignes = connexion.execute(
                    f"""
                    SELECT date, '' AS heure, championnat, domicile, exterieur
                    FROM matchs
                    WHERE date >= ? AND date <= ?
                      AND championnat IN ({placeholders})
                      AND buts_domicile IS NULL
                    ORDER BY date, championnat
                    LIMIT {LIMITE_CALENDRIER}
                    """,
                    params,
                ).fetchall()
            except sqlite3.OperationalError:
                lignes = []
    finally:
        connexion.close()
    resultat = []
    for ligne in lignes:
        resultat.append(
            {
                "championnat": ligne["championnat"],
                "date": ligne["date"] or "",
                "heure": (ligne["heure"] or "").strip(),
                "commence_at": "",
                "domicile": ligne["domicile"],
                "exterieur": ligne["exterieur"],
                "cotes": None,
                "bookmakers": [],
            }
        )
    return resultat


def cache_valide():
    return _cache["matchs"] is not None and time.time() < _cache["expire"]


def obtenir_matchs_api(cle_api):
    with _verrou:
        if cache_valide():
            return _cache["matchs"], _cache["erreur"]
        matchs, code = telecharger_tous(cle_api)
        _cache["matchs"] = matchs
        _cache["erreur"] = code
        duree = DUREE_CACHE_OK if not code else DUREE_CACHE_ERREUR
        if matchs and code:
            duree = DUREE_CACHE_OK
        _cache["expire"] = time.time() + duree
        return matchs, code


def payload(cle_configuree, message, matchs):
    return {
        "cle_configuree": cle_configuree,
        "message": message,
        "competitions": list(NOMS_COMPETITIONS),
        "matchs": matchs,
    }


def _formes_nom_equipe(nom):
    """Variantes normalisées pour rapprocher Odds API et football.db."""
    from correspondances import alias_noms_equipe, normaliser

    formes = set()
    for variante in alias_noms_equipe(nom) or [nom]:
        cle = normaliser(variante)
        if cle:
            formes.add(cle)
    return formes


def noms_equipes_proches(nom_a, nom_b):
    formes_a = _formes_nom_equipe(nom_a)
    formes_b = _formes_nom_equipe(nom_b)
    if not formes_a or not formes_b:
        return False
    if formes_a & formes_b:
        return True
    for a in formes_a:
        for b in formes_b:
            if len(a) >= 4 and len(b) >= 4 and (a in b or b in a):
                return True
    return False


def _ecart_jours(date_a, date_b):
    if not date_a or not date_b:
        return None
    try:
        a = date.fromisoformat(str(date_a)[:10])
        b = date.fromisoformat(str(date_b)[:10])
    except ValueError:
        return None
    return abs((a - b).days)


def trouver_match_cotes(championnat, domicile, exterieur, date_match=None):
    """
    Retrouve un match du cache Odds API (cotes moyennes 1-N-2).
    Sans clé ou sans correspondance : None. Ne fabrique jamais de cote.
    """
    cle = lire_cle_api()
    if not cle:
        return None
    try:
        matchs, _code = obtenir_matchs_api(cle)
    except Exception:
        return None
    if not matchs:
        return None

    candidats = []
    for match in matchs:
        if not match.get("cotes") or not match["cotes"].get("moyenne"):
            continue
        if not noms_equipes_proches(match.get("domicile"), domicile):
            continue
        if not noms_equipes_proches(match.get("exterieur"), exterieur):
            continue
        score = 20
        if championnat and match.get("championnat") == championnat:
            score += 10
        ecart = _ecart_jours(date_match, match.get("date"))
        if ecart is None:
            score += 0
        elif ecart == 0:
            score += 8
        elif ecart == 1:
            score += 4
        elif ecart > 3:
            score -= 5
        candidats.append((score, match))

    if not candidats:
        return None
    candidats.sort(key=lambda item: item[0], reverse=True)
    meilleur_score, meilleur = candidats[0]
    if meilleur_score < 20:
        return None
    return meilleur


def _probabilites_implicites(cotes):
    inverses = {
        "domicile": 1.0 / cotes["domicile"],
        "nul": 1.0 / cotes["nul"],
        "exterieur": 1.0 / cotes["exterieur"],
    }
    total = sum(inverses.values()) or 1.0
    return {
        cle: round(100.0 * valeur / total, 1) for cle, valeur in inverses.items()
    }


def _issue_favorite(probabilites):
    return max(probabilites, key=probabilites.get)


def _libelle_confiance(probabilites, favori):
    p_fav = probabilites[favori]
    autres = [probabilites[cle] for cle in probabilites if cle != favori]
    ecart = p_fav - max(autres)
    if p_fav >= 55 and ecart >= 15:
        return "favori_net", "le favori net du marché"
    if p_fav >= 45 and ecart >= 8:
        return "leger", "le léger favori du marché"
    return "match_ouvert", "favori d'un match ouvert selon le marché"


def _issue_statistique(prediction):
    if not prediction:
        return None
    probs = {
        "domicile": float(prediction.get("p_victoire_domicile") or 0),
        "nul": float(prediction.get("p_nul") or 0),
        "exterieur": float(prediction.get("p_victoire_exterieur") or 0),
    }
    return _issue_favorite(probs)


def _nom_issue(issue, nom_domicile, nom_exterieur):
    if issue == "domicile":
        return nom_domicile
    if issue == "exterieur":
        return nom_exterieur
    return "match nul"


def construire_lecture_marche(
    cotes_1n2, nom_domicile, nom_exterieur, prediction=None, meta=None
):
    """Bloc JSON pour l'analyse : marché vs scénario statistique, sans tipster."""
    if not cotes_1n2:
        return None
    try:
        cotes = {
            "domicile": float(cotes_1n2["domicile"]),
            "nul": float(cotes_1n2["nul"]),
            "exterieur": float(cotes_1n2["exterieur"]),
        }
    except (KeyError, TypeError, ValueError):
        return None
    if min(cotes.values()) <= 1:
        return None

    probs = _probabilites_implicites(cotes)
    favori = _issue_favorite(probs)
    confiance_cle, confiance_texte = _libelle_confiance(probs, favori)
    favori_nom = _nom_issue(favori, nom_domicile, nom_exterieur)
    issue_stats = _issue_statistique(prediction)

    if issue_stats is None:
        accord = "inconnu"
        accord_texte = (
            "Pas assez d'éléments pour comparer marché et scénario statistique."
        )
    elif issue_stats == favori:
        accord = "accord"
        accord_texte = (
            f"Le scénario statistique et le marché vont dans le même sens "
            f"({favori_nom})."
        )
    elif favori != "nul" and issue_stats != "nul" and favori != issue_stats:
        accord = "divergence"
        accord_texte = (
            f"Divergence : le marché penche vers {favori_nom}, "
            f"alors que le modèle statistique voit plutôt "
            f"{_nom_issue(issue_stats, nom_domicile, nom_exterieur)}."
        )
    else:
        accord = "partiel"
        accord_texte = (
            f"Lecture mitigée : le marché désigne {favori_nom}, "
            f"le modèle statistique penche vers "
            f"{_nom_issue(issue_stats, nom_domicile, nom_exterieur)}."
        )

    if favori == "nul":
        if confiance_cle == "favori_net":
            phrase_favori = "Le marché voit clairement un match nul."
        elif confiance_cle == "leger":
            phrase_favori = "Le marché penche légèrement vers un match nul."
        else:
            phrase_favori = "Le marché ne désigne pas de favori clair (nul le plus probable)."
    else:
        phrase_favori = f"{favori_nom} est {confiance_texte}."
    texte = (
        f"Cotes moyennes 1 / N / 2 : {cotes['domicile']:.2f} / "
        f"{cotes['nul']:.2f} / {cotes['exterieur']:.2f}. "
        f"{phrase_favori} {accord_texte}"
    )

    return {
        "disponible": True,
        "cotes": {
            "domicile": round(cotes["domicile"], 2),
            "nul": round(cotes["nul"], 2),
            "exterieur": round(cotes["exterieur"], 2),
        },
        "probabilites_implicites": probs,
        "favori": favori,
        "favori_nom": favori_nom,
        "confiance": confiance_cle,
        "confiance_texte": confiance_texte,
        "accord_statistique": accord,
        "texte": texte,
        "disclaimer": (
            "Lecture informative des cotes pré-match — pas un conseil de pari."
        ),
        "source": "moyenne bookmakers (EU)",
        "date": (meta or {}).get("date") or "",
        "noms_api": {
            "domicile": (meta or {}).get("domicile") or "",
            "exterieur": (meta or {}).get("exterieur") or "",
        },
    }


def lecture_marche_pour_analyse(
    championnat, domicile, exterieur, date_match=None, prediction=None
):
    """
    Enrichit l'analyse si des cotes existent pour la rencontre.
    Sans clé / sans match : None (l'analyse reste inchangée).
    """
    try:
        match = trouver_match_cotes(championnat, domicile, exterieur, date_match)
        if not match:
            return None
        moyenne = (match.get("cotes") or {}).get("moyenne")
        return construire_lecture_marche(
            moyenne,
            domicile,
            exterieur,
            prediction=prediction,
            meta=match,
        )
    except Exception:
        return None


@routeur_cotes.get("/api/cotes")
def cotes_api(championnat: str | None = Query(None)):
    nom = championnat.strip() if isinstance(championnat, str) else ""
    if nom and nom not in NOMS_COMPETITIONS:
        raise HTTPException(400, "Championnat inconnu")
    cle = lire_cle_api()
    if not cle:
        matchs = matchs_depuis_calendrier()
        if nom:
            matchs = [m for m in matchs if m["championnat"] == nom]
        return payload(False, MESSAGES["sans_cle"], matchs)
    try:
        matchs, code = obtenir_matchs_api(cle)
    except Exception:
        matchs, code = [], "service_indisponible"
    message = MESSAGES.get(code, "") if code else ""
    if not matchs:
        calendrier = matchs_depuis_calendrier()
        if nom:
            calendrier = [m for m in calendrier if m["championnat"] == nom]
        if not message:
            message = MESSAGES["service_indisponible"] if code else ""
        return payload(True, message, calendrier)
    if nom:
        matchs = [m for m in matchs if m["championnat"] == nom]
    return payload(True, "", matchs)
