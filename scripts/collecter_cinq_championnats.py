"""
Collecte des 5 grands championnats depuis 1993-94 :
- matchs : CSV locaux (football-data.co.uk), y compris 1993-2019
- joueurs et xG : Understat (depuis 2020, deja en CSV)
- calendrier : Understat (dates isResult=false) + fixtures.csv en complement

Conserve les lignes Ligue des champions deja presentes.
Pour rafraichir la LDC : python scripts/collecter_ligue_champions.py
"""

import csv
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "site" / "api"))
from correspondances import nom_pour_calendrier

DOSSIER_SORTIE = Path("donnees/cinq_championnats")
ANNEE_MIN = 1993
ANNEE_COURANTE = 2026
SAISONS_UNDERSTAT = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
PAUSE_SECONDES = 1.2

CHAMPIONNATS = [
    {"dossier": "premier-league", "nom": "Premier League", "understat": "EPL", "code": "E0"},
    {"dossier": "la-liga", "nom": "La Liga", "understat": "La_liga", "code": "SP1"},
    {"dossier": "bundesliga", "nom": "Bundesliga", "understat": "Bundesliga", "code": "D1"},
    {"dossier": "serie-a", "nom": "Serie A", "understat": "Serie_A", "code": "I1"},
    {"dossier": "ligue-1", "nom": "Ligue 1", "understat": "Ligue_1", "code": "F1"},
]
CODES_VERS_NOM = {champ["code"]: champ["nom"] for champ in CHAMPIONNATS}
COLONNES_MATCH = [
    "Date",
    "HomeTeam",
    "AwayTeam",
    "FTHG",
    "FTAG",
    "FTR",
    "HTHG",
    "HTAG",
    "HTR",
    "Referee",
    "HS",
    "AS",
    "HST",
    "AST",
    "HF",
    "AF",
    "HC",
    "AC",
    "HY",
    "AY",
    "HR",
    "AR",
]
SESSION_WEB = requests.Session()
SESSION_WEB.headers.update(
    {
        "User-Agent": "StatsChampionnats/1.0 (projet local; resultats championnats)"
    }
)


def annee_debut(fichier):
    code = fichier.stem.replace("season-", "")[:2]
    annee = int(code)
    return 1900 + annee if annee >= 69 else 2000 + annee


def libelle_saison(annee):
    return f"{annee}-{annee + 1}"


def code_fichier_saison(annee):
    return f"{str(annee)[-2:]}{str(annee + 1)[-2:]}"


def normaliser_date(valeur):
    texte = (valeur or "").strip()
    if len(texte) >= 10 and texte[4] == "-" and texte[7] == "-":
        return texte[:10]
    parties = texte.replace("-", "/").split("/")
    if len(parties) != 3:
        return texte
    jour, mois, annee = parties
    if len(annee) == 2:
        annee = "20" + annee
    return f"{annee}-{mois.zfill(2)}-{jour.zfill(2)}"


def extraire_heure(date_heure):
    texte = date_heure or ""
    if len(texte) >= 16 and texte[10] in " T":
        return texte[11:16]
    return ""


def saison_depuis_date(date):
    try:
        annee = int(date[:4])
        mois = int(date[5:7])
    except (TypeError, ValueError):
        return libelle_saison(ANNEE_COURANTE)
    if mois >= 7:
        return libelle_saison(annee)
    return libelle_saison(annee - 1)


def telecharger_matchs_saison(annee):
    code = code_fichier_saison(annee)
    for champ in CHAMPIONNATS:
        url = f"https://www.football-data.co.uk/mmz4281/{code}/{champ['code']}.csv"
        chemin = Path("datasets") / champ["dossier"] / f"season-{code}.csv"
        try:
            reponse = SESSION_WEB.get(url, timeout=30)
        except requests.RequestException as exc:
            print(f"   {champ['nom']}: telechargement impossible ({exc})")
            continue
        if reponse.status_code != 200 or "HomeTeam" not in reponse.text[:800]:
            print(f"   {champ['nom']}: pas encore de fichier 20{code[:2]}-20{code[2:]}")
            continue
        reponse.encoding = reponse.apparent_encoding or "utf-8"
        lecteur = csv.DictReader(reponse.text.splitlines())
        lignes = []
        for ligne in lecteur:
            if not (ligne.get("Date") or "").strip():
                continue
            propre = {col: (ligne.get(col) or "").strip() for col in COLONNES_MATCH}
            propre["Date"] = normaliser_date(propre["Date"])
            lignes.append(propre)
        if not lignes:
            print(f"   {champ['nom']}: fichier vide")
            continue
        chemin.parent.mkdir(parents=True, exist_ok=True)
        with open(chemin, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLONNES_MATCH)
            writer.writeheader()
            writer.writerows(lignes)
        print(f"   {champ['nom']}: {len(lignes)} matchs -> {chemin}")


def arrondi(valeur, decimales=2):
    try:
        return round(float(valeur), decimales)
    except (TypeError, ValueError):
        return ""


def collecter_matchs_locaux():
    matchs = []
    for champ in CHAMPIONNATS:
        dossier = Path("datasets") / champ["dossier"]
        fichiers = sorted(dossier.glob("season-*.csv"), key=annee_debut)
        for fichier in fichiers:
            debut = annee_debut(fichier)
            if debut < ANNEE_MIN:
                continue
            with open(fichier, newline="", encoding="utf-8", errors="replace") as f:
                for ligne in csv.DictReader(f):
                    if not (ligne.get("Date") or "").strip():
                        continue
                    matchs.append(
                        {
                            "championnat": champ["nom"],
                            "saison": libelle_saison(debut),
                            "date": normaliser_date(ligne.get("Date", "")),
                            "domicile": (ligne.get("HomeTeam") or "").strip(),
                            "exterieur": (ligne.get("AwayTeam") or "").strip(),
                            "buts_domicile": ligne.get("FTHG", ""),
                            "buts_exterieur": ligne.get("FTAG", ""),
                            "resultat": ligne.get("FTR", ""),
                            "buts_domicile_mt": ligne.get("HTHG", ""),
                            "buts_exterieur_mt": ligne.get("HTAG", ""),
                            "resultat_mt": ligne.get("HTR", ""),
                            "arbitre": ligne.get("Referee", ""),
                            "tirs_domicile": ligne.get("HS", ""),
                            "tirs_exterieur": ligne.get("AS", ""),
                            "tirs_cadres_domicile": ligne.get("HST", ""),
                            "tirs_cadres_exterieur": ligne.get("AST", ""),
                            "fautes_domicile": ligne.get("HF", ""),
                            "fautes_exterieur": ligne.get("AF", ""),
                            "corners_domicile": ligne.get("HC", ""),
                            "corners_exterieur": ligne.get("AC", ""),
                            "jaunes_domicile": ligne.get("HY", ""),
                            "jaunes_exterieur": ligne.get("AY", ""),
                            "rouges_domicile": ligne.get("HR", ""),
                            "rouges_exterieur": ligne.get("AR", ""),
                        }
                    )
    return matchs


def session_understat():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )
    return session


def lire_ligue_understat(session, slug, annee):
    page = f"https://understat.com/league/{slug}/{annee}"
    session.get(page, timeout=30)
    reponse = session.get(
        f"https://understat.com/getLeagueData/{slug}/{annee}",
        headers={"X-Requested-With": "XMLHttpRequest"},
        timeout=30,
    )
    reponse.raise_for_status()
    return reponse.json()


def collecter_understat(annees=None):
    session = session_understat()
    joueurs = []
    matchs_xg = []
    calendrier = []
    erreurs = []
    annees = annees if annees is not None else SAISONS_UNDERSTAT

    for champ in CHAMPIONNATS:
        for annee in annees:
            saison = libelle_saison(annee)
            print(f"  Understat {champ['nom']} {saison}...")
            try:
                data = lire_ligue_understat(session, champ["understat"], annee)
            except Exception as exc:
                erreurs.append(f"{champ['nom']} {saison}: {exc}")
                time.sleep(PAUSE_SECONDES)
                continue

            for j in data.get("players") or []:
                joueurs.append(
                    {
                        "championnat": champ["nom"],
                        "saison": saison,
                        "equipe": j.get("team_title", ""),
                        "joueur": j.get("player_name", ""),
                        "poste": j.get("position", ""),
                        "matchs": j.get("games", ""),
                        "minutes": j.get("time", ""),
                        "buts": j.get("goals", ""),
                        "passes_decisives": j.get("assists", ""),
                        "tirs": j.get("shots", ""),
                        "passes_cles": j.get("key_passes", ""),
                        "xg": arrondi(j.get("xG")),
                        "xa": arrondi(j.get("xA")),
                        "buts_hors_penalty": j.get("npg", ""),
                        "xg_hors_penalty": arrondi(j.get("npxG")),
                        "xg_chaine": arrondi(j.get("xGChain")),
                        "xg_construction": arrondi(j.get("xGBuildup")),
                        "carton_jaune": j.get("yellow_cards", ""),
                        "carton_rouge": j.get("red_cards", ""),
                    }
                )

            for m in data.get("dates") or []:
                domicile = (m.get("h") or {}).get("title", "")
                exterieur = (m.get("a") or {}).get("title", "")
                if not domicile or not exterieur:
                    continue
                date_heure = m.get("datetime") or ""
                date = date_heure[:10]
                heure = extraire_heure(date_heure)
                if not m.get("isResult"):
                    calendrier.append(
                        {
                            "championnat": champ["nom"],
                            "saison": saison,
                            "date": date,
                            "heure": heure,
                            "domicile": domicile,
                            "exterieur": exterieur,
                            "journee": "",
                        }
                    )
                    continue
                buts = m.get("goals") or {}
                xg = m.get("xG") or {}
                matchs_xg.append(
                    {
                        "championnat": champ["nom"],
                        "saison": saison,
                        "date": date,
                        "domicile": domicile,
                        "exterieur": exterieur,
                        "buts_domicile": buts.get("h", ""),
                        "buts_exterieur": buts.get("a", ""),
                        "xg_domicile": arrondi(xg.get("h")),
                        "xg_exterieur": arrondi(xg.get("a")),
                        "resultat": m.get("result", ""),
                    }
                )
            time.sleep(PAUSE_SECONDES)

    return joueurs, matchs_xg, calendrier, erreurs


def equipes_depuis_joueurs(joueurs):
    vus = set()
    equipes = []
    for j in joueurs:
        cle = (j["championnat"], j["saison"], j["equipe"])
        if not j["equipe"] or cle in vus:
            continue
        vus.add(cle)
        equipes.append(
            {
                "championnat": j["championnat"],
                "saison": j["saison"],
                "equipe": j["equipe"],
            }
        )
    return sorted(equipes, key=lambda x: (x["championnat"], x["saison"], x["equipe"]))


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


def lire_csv(chemin):
    if not chemin.exists():
        return []
    with open(chemin, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def remplacer_saison(anciennes, saison, nouvelles):
    conservees = [ligne for ligne in anciennes if ligne.get("saison") != saison]
    return conservees + nouvelles


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


def completer_matchs_depuis_xg(matchs, matchs_xg):
    """Ajoute les matchs Understat absents de football-data (noms alignes)."""
    noms_par_saison = {}
    vus = set()
    for match in matchs:
        cle_saison = (match["championnat"], match["saison"])
        noms_par_saison.setdefault(cle_saison, set()).update(
            [match["domicile"], match["exterieur"]]
        )
        vus.add(
            (match["championnat"], match["saison"], match["date"], match["domicile"], match["exterieur"])
        )

    champs_vides = {
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
    ajouts = []
    for xg in matchs_xg:
        noms = noms_par_saison.get((xg["championnat"], xg["saison"]), set())
        domicile = nom_pour_calendrier(xg["domicile"], noms)
        exterieur = nom_pour_calendrier(xg["exterieur"], noms)
        cle = (xg["championnat"], xg["saison"], xg["date"], domicile, exterieur)
        if cle in vus:
            continue
        vus.add(cle)
        ajouts.append(
            {
                "championnat": xg["championnat"],
                "saison": xg["saison"],
                "date": xg["date"],
                "domicile": domicile,
                "exterieur": exterieur,
                "buts_domicile": xg["buts_domicile"],
                "buts_exterieur": xg["buts_exterieur"],
                "resultat": resultat_depuis_buts(xg["buts_domicile"], xg["buts_exterieur"]),
                **champs_vides,
            }
        )
    return matchs + ajouts, ajouts


def collecter_fixtures_semaine():
    """Complements de la semaine (mar/ven), pas le calendrier 38 journees."""
    url = "https://www.football-data.co.uk/fixtures.csv"
    try:
        reponse = SESSION_WEB.get(url, timeout=30)
    except requests.RequestException as exc:
        print(f"   fixtures.csv: telechargement impossible ({exc})")
        return []
    if reponse.status_code != 200 or "HomeTeam" not in reponse.text[:800]:
        print("   fixtures.csv: fichier indisponible")
        return []
    reponse.encoding = reponse.apparent_encoding or "utf-8"
    texte = reponse.text.lstrip("\ufeff")
    saison_cible = libelle_saison(ANNEE_COURANTE)
    lignes = []
    for ligne in csv.DictReader(texte.splitlines()):
        code = (ligne.get("Div") or "").strip()
        if code not in CODES_VERS_NOM:
            continue
        date = normaliser_date(ligne.get("Date"))
        domicile = (ligne.get("HomeTeam") or "").strip()
        exterieur = (ligne.get("AwayTeam") or "").strip()
        if not date or not domicile or not exterieur:
            continue
        saison = saison_depuis_date(date)
        if saison != saison_cible:
            continue
        lignes.append(
            {
                "championnat": CODES_VERS_NOM[code],
                "saison": saison,
                "date": date,
                "heure": (ligne.get("Time") or "").strip()[:5],
                "domicile": domicile,
                "exterieur": exterieur,
                "journee": "",
            }
        )
    return lignes


def noms_equipes_matchs(matchs):
    noms = {}
    for match in matchs:
        cle = (match["championnat"], match["saison"])
        noms.setdefault(cle, set()).update([match["domicile"], match["exterieur"]])
    return noms


def aligner_ligne_calendrier(ligne, noms_par_saison):
    noms = noms_par_saison.get((ligne["championnat"], ligne["saison"]), set())
    return {
        "championnat": ligne["championnat"],
        "saison": ligne["saison"],
        "date": ligne["date"],
        "heure": ligne.get("heure") or "",
        "domicile": nom_pour_calendrier(ligne["domicile"], noms),
        "exterieur": nom_pour_calendrier(ligne["exterieur"], noms),
        "journee": ligne.get("journee") or "",
    }


def fusionner_calendrier(understat, fixtures, matchs):
    noms = noms_equipes_matchs(matchs)
    joues = {
        (m["championnat"], m["saison"], m["domicile"], m["exterieur"]) for m in matchs
    }
    vus = set()
    resultat = []
    for source in (understat, fixtures):
        for brut in source:
            ligne = aligner_ligne_calendrier(brut, noms)
            if not ligne["domicile"] or not ligne["exterieur"]:
                continue
            cle = (
                ligne["championnat"],
                ligne["saison"],
                ligne["domicile"],
                ligne["exterieur"],
            )
            if cle in joues or cle in vus:
                continue
            vus.add(cle)
            resultat.append(ligne)
    resultat.sort(
        key=lambda x: (x["championnat"], x["saison"], x["date"], x["heure"], x["domicile"])
    )
    return resultat


def main():
    print(f"0/3 Telechargement football-data {libelle_saison(ANNEE_COURANTE)}...")
    telecharger_matchs_saison(ANNEE_COURANTE)

    print("1/3 Matchs locaux depuis 1993...")
    matchs = collecter_matchs_locaux()
    print(f"   {len(matchs)} matchs football-data")

    print(f"2/3 Joueurs, xG et calendrier Understat {libelle_saison(ANNEE_COURANTE)}...")
    joueurs_nouveaux, xg_nouveaux, calendrier_understat, erreurs = collecter_understat(
        [ANNEE_COURANTE]
    )
    saison = libelle_saison(ANNEE_COURANTE)
    joueurs = remplacer_saison(lire_csv(DOSSIER_SORTIE / "joueurs.csv"), saison, joueurs_nouveaux)
    matchs_xg = remplacer_saison(lire_csv(DOSSIER_SORTIE / "matchs_xg.csv"), saison, xg_nouveaux)
    matchs, ajouts = completer_matchs_depuis_xg(matchs, xg_nouveaux)
    print("   Complements fixtures.csv (semaine)...")
    fixtures = collecter_fixtures_semaine()
    calendrier_nouveaux = fusionner_calendrier(calendrier_understat, fixtures, matchs)
    calendrier = remplacer_saison(
        lire_csv(DOSSIER_SORTIE / "calendrier.csv"), saison, calendrier_nouveaux
    )
    ldc_matchs = [
        ligne
        for ligne in lire_csv(DOSSIER_SORTIE / "matchs.csv")
        if ligne.get("championnat") == "Ligue des champions"
    ]
    ldc_calendrier = [
        ligne
        for ligne in lire_csv(DOSSIER_SORTIE / "calendrier.csv")
        if ligne.get("championnat") == "Ligue des champions"
    ]
    ldc_equipes = [
        ligne
        for ligne in lire_csv(DOSSIER_SORTIE / "equipes.csv")
        if ligne.get("championnat") == "Ligue des champions"
    ]
    calendrier = [
        ligne
        for ligne in calendrier
        if ligne.get("championnat") != "Ligue des champions"
    ]
    ecrire_csv(DOSSIER_SORTIE / "matchs.csv", matchs + ldc_matchs)
    ecrire_csv(DOSSIER_SORTIE / "joueurs.csv", joueurs)
    ecrire_csv(DOSSIER_SORTIE / "matchs_xg.csv", matchs_xg)
    ecrire_csv(DOSSIER_SORTIE / "calendrier.csv", calendrier + ldc_calendrier)
    equipes = equipes_depuis_joueurs(joueurs) + ldc_equipes
    ecrire_csv(DOSSIER_SORTIE / "equipes.csv", equipes)

    print(f"   {len(matchs)} matchs -> {DOSSIER_SORTIE / 'matchs.csv'}")
    if ajouts:
        print(f"   {len(ajouts)} matchs Understat ajoutes (absents de football-data)")
    print(f"   {len(joueurs_nouveaux)} joueurs {saison}")
    print(f"   {len(xg_nouveaux)} matchs xG {saison}")
    print(f"   {len(calendrier_nouveaux)} matchs a venir {saison}")
    for champ in CHAMPIONNATS:
        n = sum(1 for c in calendrier_nouveaux if c["championnat"] == champ["nom"])
        print(f"      {champ['nom']}: {n}")
    if fixtures:
        print(f"   {len(fixtures)} lignes fixtures.csv (avant fusion)")
    print(f"   {len(joueurs)} lignes joueurs au total")
    if erreurs:
        print("Erreurs :")
        for err in erreurs:
            print(f"   {err}")


if __name__ == "__main__":
    main()
