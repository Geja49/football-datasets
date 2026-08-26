"""
Elo clubs via ClubElo (API publique HTTPS) + cache SQLite optionnel.

Pas de scrape de sites interdits. Timeout court pour ne pas bloquer l'UI ;
en cas d'echec : message honnete + possibilite de reessayer.
"""

from __future__ import annotations

import csv
import io
import sqlite3
from datetime import date, timedelta

import requests

from correspondances import normaliser

URL_JOUR = "https://api.clubelo.com/{date}"
TIMEOUT_API = 8
SOURCE = "clubelo"
PAYS_CIBLES = {"ENG", "ESP", "GER", "ITA", "FRA"}

SESSION = requests.Session()
SESSION.headers.update(
    {"User-Agent": "StatsChampionnats/1.0 (projet local; ClubElo API)"}
)

# Cache memoire processus (evite de re-telecharger a chaque fiche).
_CACHE_ELO = {"date": "", "lignes": [], "erreur": ""}


def table_elo_existe(connexion):
    ligne = connexion.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'classements_elo'"
    ).fetchone()
    return bool(ligne)


def lire_elo_base(connexion):
    if not table_elo_existe(connexion):
        return []
    try:
        return [
            dict(row)
            for row in connexion.execute(
                """
                SELECT date, rang, club, pays, niveau, elo, source
                FROM classements_elo
                ORDER BY elo DESC
                """
            )
        ]
    except sqlite3.OperationalError:
        return []


def telecharger_elo_jour(jour):
    url = URL_JOUR.format(date=jour.isoformat())
    reponse = SESSION.get(url, timeout=TIMEOUT_API)
    reponse.raise_for_status()
    texte = reponse.text
    if "Elo" not in texte[:200] and "Club" not in texte[:200]:
        raise ValueError("reponse ClubElo inattendue")
    return texte


def parser_elo(texte, jour):
    lignes = []
    lecteur = csv.DictReader(io.StringIO(texte))
    for row in lecteur:
        pays = (row.get("Country") or "").strip().upper()
        if pays not in PAYS_CIBLES:
            continue
        try:
            elo = float(row.get("Elo") or 0)
        except ValueError:
            continue
        lignes.append(
            {
                "date": jour.isoformat(),
                "rang": (row.get("Rank") or "").strip(),
                "club": (row.get("Club") or "").strip(),
                "pays": pays,
                "niveau": (row.get("Level") or "").strip(),
                "elo": round(elo, 1),
                "source": SOURCE,
            }
        )
    return lignes


def charger_elo_api(force=False):
    """Telecharge le classement ClubElo (cache memoire)."""
    global _CACHE_ELO
    if not force and _CACHE_ELO["lignes"]:
        return {
            "disponible": True,
            "date": _CACHE_ELO["date"],
            "lignes": _CACHE_ELO["lignes"],
            "message": "",
            "source": SOURCE,
        }
    if not force and _CACHE_ELO["erreur"] and not _CACHE_ELO["lignes"]:
        # Soft retry : force=True ignore ce court-circuit.
        return {
            "disponible": False,
            "date": "",
            "lignes": [],
            "message": _CACHE_ELO["erreur"],
            "source": SOURCE,
        }

    dernier_exc = None
    for decalage in range(0, 5):
        jour = date.today() - timedelta(days=decalage)
        try:
            texte = telecharger_elo_jour(jour)
            lignes = parser_elo(texte, jour)
            if not lignes:
                continue
            _CACHE_ELO = {"date": jour.isoformat(), "lignes": lignes, "erreur": ""}
            return {
                "disponible": True,
                "date": jour.isoformat(),
                "lignes": lignes,
                "message": "",
                "source": SOURCE,
            }
        except (requests.Timeout, requests.ConnectionError) as exc:
            dernier_exc = exc
            break
        except (requests.RequestException, ValueError, csv.Error) as exc:
            dernier_exc = exc
            continue

    if isinstance(dernier_exc, (requests.Timeout, requests.ConnectionError)):
        message = (
            "ClubElo ne repond pas (timeout / reseau). "
            "La force relative Elo est temporairement indisponible."
        )
    else:
        message = (
            "Impossible de charger ClubElo pour le moment. "
            "La force relative Elo est temporairement indisponible."
        )
    _CACHE_ELO = {"date": "", "lignes": [], "erreur": message}
    return {
        "disponible": False,
        "date": "",
        "lignes": [],
        "message": message,
        "source": SOURCE,
    }


def charger_elo(connexion, force_api=False):
    """Prefere la table SQLite si presente, sinon API live."""
    lignes = lire_elo_base(connexion)
    if lignes and not force_api:
        date_ref = lignes[0].get("date") or ""
        return {
            "disponible": True,
            "date": date_ref,
            "lignes": lignes,
            "message": "",
            "source": lignes[0].get("source") or SOURCE,
        }
    return charger_elo_api(force=force_api)


def score_correspondance(nom_equipe, nom_elo):
    a = normaliser(nom_equipe)
    b = normaliser(nom_elo)
    if not a or not b:
        return 0
    if a == b:
        return 100
    if a in b or b in a:
        return 80
    # Jetons communs (ex. "bayern munich" / "bayern").
    ta = set(a.split())
    tb = set(b.split())
    if not ta or not tb:
        return 0
    commun = ta & tb
    if not commun:
        return 0
    return int(60 * len(commun) / max(len(ta), len(tb)))


def trouver_ligne_elo(lignes, noms_alias):
    meilleurs = []
    for alias in noms_alias or []:
        for ligne in lignes:
            score = score_correspondance(alias, ligne.get("club") or "")
            if score >= 60:
                meilleurs.append((score, ligne))
    if not meilleurs:
        return None
    meilleurs.sort(key=lambda x: (-x[0], -float(x[1].get("elo") or 0)))
    return meilleurs[0][1]


def elo_pour_equipe(connexion, noms_alias, force_api=False):
    paquet = charger_elo(connexion, force_api=force_api)
    if not paquet["disponible"]:
        return {
            "disponible": False,
            "message": paquet["message"],
            "source": paquet["source"],
            "date": "",
            "club_elo": "",
            "elo": None,
            "rang": None,
            "pays": "",
            "force_relative": None,
        }
    ligne = trouver_ligne_elo(paquet["lignes"], noms_alias)
    if not ligne:
        return {
            "disponible": False,
            "message": (
                "Pas de correspondance ClubElo pour ce club "
                "(noms differents). Pas de force relative affichee."
            ),
            "source": paquet["source"],
            "date": paquet["date"],
            "club_elo": "",
            "elo": None,
            "rang": None,
            "pays": "",
            "force_relative": None,
        }
    elos = [float(l.get("elo") or 0) for l in paquet["lignes"] if l.get("elo") is not None]
    elo_min = min(elos) if elos else 0
    elo_max = max(elos) if elos else 1
    elo_val = float(ligne.get("elo") or 0)
    if elo_max > elo_min:
        force = round((elo_val - elo_min) / (elo_max - elo_min), 3)
    else:
        force = 0.5
    return {
        "disponible": True,
        "message": "",
        "source": paquet["source"],
        "date": paquet["date"],
        "club_elo": ligne.get("club") or "",
        "elo": elo_val,
        "rang": ligne.get("rang") or "",
        "pays": ligne.get("pays") or "",
        "force_relative": force,
    }


def enrichir_classement_elo(connexion, classement, force_api=False):
    """Ajoute elo / force_relative aux lignes du classement (best-effort).

    Par defaut : table SQLite seulement (pas d'appel live) pour ne pas
    ralentir la page classement si ClubElo timeout.
    """
    if force_api:
        paquet = charger_elo(connexion, force_api=True)
    else:
        lignes = lire_elo_base(connexion)
        if lignes:
            paquet = {
                "disponible": True,
                "date": lignes[0].get("date") or "",
                "lignes": lignes,
                "message": "",
                "source": lignes[0].get("source") or SOURCE,
            }
        else:
            paquet = {
                "disponible": False,
                "date": "",
                "lignes": [],
                "message": (
                    "Elo non charge en base (ClubElo). "
                    "Lancez scripts/collecter_clubelo.py, "
                    "ou ouvrez une fiche club pour tenter l'API avec retry."
                ),
                "source": SOURCE,
            }
    meta = {
        "disponible": paquet["disponible"],
        "message": paquet["message"],
        "date": paquet.get("date") or "",
        "source": paquet.get("source") or SOURCE,
    }
    if not paquet["disponible"]:
        for ligne in classement:
            ligne["elo"] = None
            ligne["force_relative"] = None
        return meta

    elos = [float(l.get("elo") or 0) for l in paquet["lignes"] if l.get("elo") is not None]
    elo_min = min(elos) if elos else 0
    elo_max = max(elos) if elos else 1

    for ligne in classement:
        trouve = trouver_ligne_elo(paquet["lignes"], [ligne.get("equipe")])
        if not trouve:
            ligne["elo"] = None
            ligne["force_relative"] = None
            continue
        elo_val = float(trouve.get("elo") or 0)
        ligne["elo"] = elo_val
        if elo_max > elo_min:
            ligne["force_relative"] = round((elo_val - elo_min) / (elo_max - elo_min), 3)
        else:
            ligne["force_relative"] = 0.5
    return meta
