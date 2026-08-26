"""
Calendrier des 5 ligues depuis openfootball (GitHub, CC0).

Complement a Understat + fixtures.csv : openfootball publie souvent
les 38 journees des le debut de saison.

Usage : python scripts/collecter_calendrier_openfootball.py
"""

import csv
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "site" / "api"))
from correspondances import (
    cle_nom,
    nom_depuis_openfootball,
    nom_pour_calendrier,
    normaliser,
)

DOSSIER_SORTIE = Path("donnees/cinq_championnats")
ANNEE_COURANTE = 2026
PAUSE_SECONDES = 0.4

# Repos / chemins openfootball pour la saison courante (Football.TXT).
SOURCES = (
    {
        "nom": "Premier League",
        "url": (
            "https://raw.githubusercontent.com/openfootball/england/"
            "master/{dossier}/1-premierleague.txt"
        ),
    },
    {
        "nom": "La Liga",
        "url": (
            "https://raw.githubusercontent.com/openfootball/espana/"
            "master/{dossier}/1-liga.txt"
        ),
    },
    {
        "nom": "Bundesliga",
        "url": (
            "https://raw.githubusercontent.com/openfootball/deutschland/"
            "master/{dossier}/1-bundesliga.txt"
        ),
    },
    {
        "nom": "Serie A",
        "url": (
            "https://raw.githubusercontent.com/openfootball/italy/"
            "master/{dossier}/1-seriea.txt"
        ),
    },
    {
        "nom": "Ligue 1",
        "url": (
            "https://raw.githubusercontent.com/openfootball/europe/"
            "master/france/{dossier}_fr1.txt"
        ),
    },
)

MOIS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}
JOURS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MOTIF_DATE = re.compile(
    r"^\s*(" + "|".join(JOURS) + r")\s+([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(\d{4}))?\s*$"
)
MOTIF_HEURE = re.compile(r"^\s*(\d{1,2}:\d{2})\s+(.+)$")
# Domestic : "Arsenal FC  v Coventry City FC  3-0" (sans code pays).
MOTIF_MATCH = re.compile(
    r"^(.+?)\s{2,}v\s{2,}(.+?)(?:\s{2,}(\d+-\d+.*))?$"
)
MOTIF_MATCH_SOUPLE = re.compile(
    r"^(.+?)\s+v\s+(.+?)(?:\s+(\d+-\d+.*))?$"
)
MOTIF_JOURNEE = re.compile(r"matchday\s+(\d+)", re.IGNORECASE)
SUFFIXES = (
    " FC",
    " AFC",
    " CF",
    " SC",
    " AC",
    " BK",
    " SV",
    " FK",
    " Calcio",
)
PREFIXES = (
    "1. ",
    "AS ",
    "US ",
    "AC ",
    "FC ",
    "SSC ",
    "ACF ",
    "SS ",
    "UD ",
    "CD ",
    "RC ",
    "RCD ",
    "CA ",
)

SESSION_WEB = requests.Session()
SESSION_WEB.headers.update(
    {
        "User-Agent": "StatsChampionnats/1.0 (projet local; openfootball calendrier)"
    }
)


def libelle_saison(annee):
    return f"{annee}-{annee + 1}"


def dossier_saison(annee):
    return f"{annee}-{str(annee + 1)[-2:]}"


def simplifier_club(nom):
    texte = (nom or "").strip()
    for _ in range(3):
        change = False
        for suffixe in SUFFIXES:
            if texte.upper().endswith(suffixe.upper()):
                texte = texte[: -len(suffixe)].strip()
                change = True
        for prefixe in PREFIXES:
            if texte.upper().startswith(prefixe.upper()):
                texte = texte[len(prefixe) :].strip()
                change = True
        if not change:
            break
    return texte


def equipes_compatibles(a, b):
    na = cle_nom(simplifier_club(a)).replace(" ", "")
    nb = cle_nom(simplifier_club(b)).replace(" ", "")
    if not na or not nb:
        return False
    if na == nb:
        return True
    # Fallback alphanumerique (Dep. A Coruna / Deportivo La Coruna).
    na2 = normaliser(simplifier_club(a))
    nb2 = normaliser(simplifier_club(b))
    if na2 and nb2 and (na2 == nb2 or (len(na2) >= 5 and len(nb2) >= 5 and (na2 in nb2 or nb2 in na2))):
        return True
    if len(na) >= 5 and len(nb) >= 5 and (na in nb or nb in na):
        return True
    return False


def deja_present(ligne, index_par_date, joues_index):
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


def fusionner(existant, ajouts, matchs_joues):
    """Ajoute les matchs openfootball absents (anti-doublons noms longs/courts)."""
    index = {}
    for l in existant:
        cle = (l.get("championnat"), l.get("saison"), l.get("date"))
        index.setdefault(cle, []).append((l.get("domicile"), l.get("exterieur")))
    joues_index = {}
    for m in matchs_joues:
        cle = (m.get("championnat"), m.get("saison"), m.get("date"))
        joues_index.setdefault(cle, []).append((m.get("domicile"), m.get("exterieur")))

    resultat = list(existant)
    nb = 0
    for ligne in ajouts:
        if not ligne.get("domicile") or not ligne.get("exterieur"):
            continue
        if deja_present(ligne, index, joues_index):
            continue
        cle = (ligne.get("championnat"), ligne.get("saison"), ligne.get("date"))
        index.setdefault(cle, []).append((ligne.get("domicile"), ligne.get("exterieur")))
        resultat.append(ligne)
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


def aligner_nom(nom_brut, noms_connus):
    candidats = [nom_brut, simplifier_club(nom_brut)]
    for candidat in candidats:
        alias = nom_depuis_openfootball(candidat, noms_connus)
        if alias in noms_connus:
            return alias
        aligne = nom_pour_calendrier(alias, noms_connus)
        if aligne in noms_connus:
            return aligne
        aligne2 = nom_pour_calendrier(simplifier_club(alias), noms_connus)
        if aligne2 in noms_connus:
            return aligne2
        for connu in noms_connus:
            if equipes_compatibles(candidat, connu):
                return connu
    return simplifier_club(nom_brut) or nom_brut.strip()


def lire_csv(chemin):
    if not chemin.exists():
        return []
    with open(chemin, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ecrire_csv(chemin, lignes):
    if not lignes:
        return
    champs = []
    vus = set()
    for ligne in lignes:
        for nom in ligne:
            if nom not in vus:
                vus.add(nom)
                champs.append(nom)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=champs, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(lignes)


def noms_connus_saison(matchs, championnat, saison):
    noms = set()
    for match in matchs:
        if match.get("championnat") != championnat or match.get("saison") != saison:
            continue
        noms.add(match.get("domicile") or "")
        noms.add(match.get("exterieur") or "")
    noms.discard("")
    return noms


def parser_calendrier(texte, championnat, saison, noms_connus):
    lignes = []
    journee = ""
    date_iso = ""
    annee = int(saison[:4])
    heure = ""

    for brut in texte.splitlines():
        ligne = brut.rstrip()
        if not ligne.strip() or ligne.strip().startswith("#") or ligne.startswith("="):
            continue
        if ligne.strip().startswith(("▪", "*", "?")):
            en_tete = ligne.strip().lstrip("▪*? ").strip()
            trouve = MOTIF_JOURNEE.search(en_tete)
            journee = trouve.group(1) if trouve else ""
            heure = ""
            continue

        date_lue = MOTIF_DATE.match(ligne)
        if date_lue:
            mois = MOIS.get(date_lue.group(2), 0)
            jour = int(date_lue.group(3))
            if date_lue.group(4):
                annee = int(date_lue.group(4))
            if mois:
                date_iso = f"{annee}-{mois:02d}-{jour:02d}"
            heure = ""
            continue

        heure_lue = MOTIF_HEURE.match(ligne)
        if heure_lue:
            heure = heure_lue.group(1).zfill(5)
            reste = heure_lue.group(2).strip()
        else:
            reste = ligne.strip()

        parties = MOTIF_MATCH.match(reste) or MOTIF_MATCH_SOUPLE.match(reste)
        if not parties or not date_iso:
            continue
        if (parties.group(3) or "").strip():
            continue
        domicile = aligner_nom(parties.group(1), noms_connus)
        exterieur = aligner_nom(parties.group(2), noms_connus)
        if not domicile or not exterieur or cle_nom(domicile) == cle_nom(exterieur):
            continue
        lignes.append(
            {
                "championnat": championnat,
                "saison": saison,
                "date": date_iso,
                "heure": heure,
                "domicile": domicile,
                "exterieur": exterieur,
                "journee": journee,
            }
        )
    return lignes


def telecharger(url):
    try:
        reponse = SESSION_WEB.get(url, timeout=40)
    except requests.RequestException as exc:
        print(f"   impossible ({exc})")
        return None
    if reponse.status_code == 404:
        print("   fichier absent (404)")
        return None
    if reponse.status_code != 200 or " v " not in reponse.text:
        print(f"   reponse invalide ({reponse.status_code})")
        return None
    reponse.encoding = "utf-8"
    return reponse.text


def main():
    saison = libelle_saison(ANNEE_COURANTE)
    dossier = dossier_saison(ANNEE_COURANTE)
    matchs = lire_csv(DOSSIER_SORTIE / "matchs.csv")
    calendrier = lire_csv(DOSSIER_SORTIE / "calendrier.csv")
    ajouts = []

    print(f"Calendrier openfootball {saison}...")
    for source in SOURCES:
        url = source["url"].format(dossier=dossier)
        print(f"  {source['nom']}...")
        texte = telecharger(url)
        time.sleep(PAUSE_SECONDES)
        if not texte:
            continue
        noms = noms_connus_saison(matchs, source["nom"], saison)
        # Si la saison n'a pas encore de matchs, prendre la precedente.
        if not noms:
            noms = noms_connus_saison(
                matchs, source["nom"], libelle_saison(ANNEE_COURANTE - 1)
            )
        lignes = parser_calendrier(texte, source["nom"], saison, noms)
        print(f"     {len(lignes)} matchs a venir (brut)")
        ajouts.extend(lignes)

    calendrier, nb = fusionner(calendrier, ajouts, matchs)
    ecrire_csv(DOSSIER_SORTIE / "calendrier.csv", calendrier)
    print(f"   {nb} matchs ajoutes au calendrier (total {len(calendrier)})")


if __name__ == "__main__":
    main()
