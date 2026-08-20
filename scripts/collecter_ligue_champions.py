"""
Collecte Ligue des champions depuis openfootball (GitHub, domaine public).

Saisons visees : 2020-2021 a 2026-2027 (si le fichier existe).
Pas d'Understat ni football-data.co.uk (ils n'ont pas la CL).
"""

import csv
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "site" / "api"))
from correspondances import nom_depuis_openfootball

DOSSIER_SORTIE = Path("donnees/cinq_championnats")
NOM_LDC = "Ligue des champions"
ANNEES = tuple(range(2020, 2027))
URL_FICHIER = (
    "https://raw.githubusercontent.com/openfootball/champions-league/"
    "master/{dossier}/cl.txt"
)
SESSION_WEB = requests.Session()
SESSION_WEB.headers.update(
    {
        "User-Agent": "StatsChampionnats/1.0 (projet local; openfootball LDC)"
    }
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
MOTIF_EQUIPE = r".+? \([A-Z]{3}\)"
MOTIF_MATCH = re.compile(rf"^({MOTIF_EQUIPE})\s+v\s+({MOTIF_EQUIPE})(?:\s+(.+))?$")
MOTIF_SCORE_PEN = re.compile(r"(\d+)-(\d+)\s+pen\.\s+(\d+)-(\d+)")
MOTIF_SCORE_AET = re.compile(r"(\d+)-(\d+)\s+a\.e\.t\.")
MOTIF_SCORE = re.compile(r"(\d+)-(\d+)(?:\s+\((\d+)-(\d+)\))?")

CHAMPS_VIDES = {
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


def libelle_saison(annee):
    return f"{annee}-{annee + 1}"


def dossier_saison(annee):
    return f"{annee}-{str(annee + 1)[-2:]}"


def lire_phase(en_tete):
    texte = (en_tete or "").lower()
    journee = ""
    match_j = re.search(r"matchday\s+(\d+)", texte)
    if match_j:
        journee = match_j.group(1)
    if texte.startswith("group") or texte.startswith("gruppe"):
        lettre = texte.split()[-1] if texte.split() else ""
        return "phase de groupes", lettre
    if texte.startswith("league"):
        return "phase de ligue", journee
    if texte.startswith("playoff"):
        return "barrages", journee
    if "round of 16" in texte or "huitieme" in texte:
        return "huitiemes", journee
    if "quarter" in texte or "quart" in texte:
        return "quarts", journee
    if "semi" in texte or "demie" in texte:
        return "demies", journee
    if "final" in texte:
        return "finale", journee
    return "autre", journee


def lire_score(reste):
    """Renvoie (buts_dom, buts_ext, buts_dom_mt, buts_ext_mt). Vide si non joue."""
    texte = (reste or "").strip()
    if not texte:
        return "", "", "", ""
    pen = MOTIF_SCORE_PEN.search(texte)
    if pen:
        return pen.group(3), pen.group(4), "", ""
    aet = MOTIF_SCORE_AET.search(texte)
    if aet:
        return aet.group(1), aet.group(2), "", ""
    simple = MOTIF_SCORE.search(texte)
    if not simple:
        return "", "", "", ""
    return simple.group(1), simple.group(2), simple.group(3) or "", simple.group(4) or ""


def resultat_depuis_buts(buts_domicile, buts_exterieur):
    try:
        domicile = int(buts_domicile)
        exterieur = int(buts_exterieur)
    except (TypeError, ValueError):
        return ""
    if domicile > exterieur:
        return "H"
    if domicile < exterieur:
        return "A"
    return "D"


def parser_football_txt(texte, saison, noms_ligues):
    matchs = []
    calendrier = []
    phase = "phase de ligue"
    journee = ""
    date_iso = ""
    annee = int(saison[:4])
    heure = ""

    for brut in texte.splitlines():
        ligne = brut.rstrip()
        if not ligne.strip() or ligne.strip().startswith("#") or ligne.startswith("="):
            continue
        if ligne.strip().startswith("▪") or ligne.strip().startswith("*"):
            en_tete = ligne.strip().lstrip("▪* ").strip()
            phase, journee = lire_phase(en_tete)
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

        reste_match = ligne
        heure_lue = MOTIF_HEURE.match(ligne)
        if heure_lue:
            heure = heure_lue.group(1).zfill(5)
            reste_match = heure_lue.group(2).strip()
        else:
            reste_match = ligne.strip()

        parties = MOTIF_MATCH.match(reste_match)
        if not parties or not date_iso:
            continue
        domicile = nom_depuis_openfootball(parties.group(1), noms_ligues)
        exterieur = nom_depuis_openfootball(parties.group(2), noms_ligues)
        buts_d, buts_e, buts_d_mt, buts_e_mt = lire_score(parties.group(3))
        if buts_d != "" and buts_e != "":
            ligne = {
                "championnat": NOM_LDC,
                "saison": saison,
                "date": date_iso,
                "domicile": domicile,
                "exterieur": exterieur,
                "buts_domicile": buts_d,
                "buts_exterieur": buts_e,
                "resultat": resultat_depuis_buts(buts_d, buts_e),
                "phase": phase,
                **CHAMPS_VIDES,
                "buts_domicile_mt": buts_d_mt,
                "buts_exterieur_mt": buts_e_mt,
            }
            if buts_d_mt != "" and buts_e_mt != "":
                ligne["resultat_mt"] = resultat_depuis_buts(buts_d_mt, buts_e_mt)
            matchs.append(ligne)
        else:
            calendrier.append(
                {
                    "championnat": NOM_LDC,
                    "saison": saison,
                    "date": date_iso,
                    "heure": heure,
                    "domicile": domicile,
                    "exterieur": exterieur,
                    "journee": f"{phase} {journee}".strip(),
                }
            )
    return matchs, calendrier


def telecharger_saison(annee):
    saison = libelle_saison(annee)
    url = URL_FICHIER.format(dossier=dossier_saison(annee))
    try:
        reponse = SESSION_WEB.get(url, timeout=30)
    except requests.RequestException as exc:
        print(f"   {saison}: telechargement impossible ({exc})")
        return None
    if reponse.status_code == 404:
        print(f"   {saison}: pas encore de fichier openfootball")
        return None
    if reponse.status_code != 200 or " v " not in reponse.text:
        print(f"   {saison}: fichier invalide (HTTP {reponse.status_code})")
        return None
    reponse.encoding = "utf-8"
    return reponse.text


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


def sans_ldc(lignes):
    return [l for l in lignes if l.get("championnat") != NOM_LDC]


def noms_cinq_ligues(matchs):
    noms = set()
    for match in matchs:
        if match.get("championnat") == NOM_LDC:
            continue
        noms.add(match.get("domicile") or "")
        noms.add(match.get("exterieur") or "")
    noms.discard("")
    return noms


def equipes_depuis_matchs(matchs):
    vus = set()
    equipes = []
    for match in matchs:
        for nom in (match["domicile"], match["exterieur"]):
            cle = (match["championnat"], match["saison"], nom)
            if not nom or cle in vus:
                continue
            vus.add(cle)
            equipes.append(
                {
                    "championnat": match["championnat"],
                    "saison": match["saison"],
                    "equipe": nom,
                }
            )
    return equipes


def fusionner(anciennes, nouvelles):
    return sans_ldc(anciennes) + nouvelles


def collecter():
    chemin_matchs = DOSSIER_SORTIE / "matchs.csv"
    matchs_existants = lire_csv(chemin_matchs)
    noms_ligues = noms_cinq_ligues(matchs_existants)
    matchs_ldc = []
    calendrier_ldc = []

    for annee in ANNEES:
        saison = libelle_saison(annee)
        print(f"  openfootball LDC {saison}...")
        texte = telecharger_saison(annee)
        if not texte:
            continue
        joues, avenir = parser_football_txt(texte, saison, noms_ligues)
        print(f"     {len(joues)} joues, {len(avenir)} a venir")
        matchs_ldc.extend(joues)
        calendrier_ldc.extend(avenir)
        time.sleep(0.5)

    ecrire_csv(chemin_matchs, fusionner(matchs_existants, matchs_ldc))
    ecrire_csv(
        DOSSIER_SORTIE / "calendrier.csv",
        fusionner(lire_csv(DOSSIER_SORTIE / "calendrier.csv"), calendrier_ldc),
    )
    equipes = lire_csv(DOSSIER_SORTIE / "equipes.csv")
    ecrire_csv(
        DOSSIER_SORTIE / "equipes.csv",
        fusionner(equipes, equipes_depuis_matchs(matchs_ldc)),
    )
    return matchs_ldc, calendrier_ldc


def main():
    print("Ligue des champions (openfootball)...")
    matchs, calendrier = collecter()
    print(f"   {len(matchs)} matchs LDC au total")
    print(f"   {len(calendrier)} matchs a venir LDC")
    for annee in ANNEES:
        saison = libelle_saison(annee)
        n = sum(1 for m in matchs if m["saison"] == saison)
        print(f"      {saison}: {n} joues")


if __name__ == "__main__":
    main()
