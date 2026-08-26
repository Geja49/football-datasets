"""
Joueurs et defense LDC depuis OpenML dataset 43510 (CC0).

Source : https://www.openml.org/d/43510
(miroir Kaggle « UEFA Champions league Player Statistics »,
 licence declaree CC0: Public Domain ; saisons 2013-2014 a 2019-2020).

Couvre buts, passes, tirs, cartons, tacles, interceptions, etc.
Pas de xG. Pas de stats de match (agregats saison / joueur).
Pas de scrape live.

Usage : python scripts/collecter_joueurs_ldc_openml.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "site" / "api"))
from correspondances import normaliser, nom_depuis_openfootball
from defense_commune import (
    COLONNES_COUVERTURE,
    COLONNES_DEFENSE,
    DOSSIER_SORTIE,
    FICHIER_COUVERTURE,
    FICHIER_DEFENSE,
    ecrire_csv,
    lire_csv,
    remplacer_source,
)

NOM_LDC = "Ligue des champions"
SOURCE = "openml_ldc"
URL_ARFF = (
    "https://www.openml.org/data/v1/download/22102335/"
    "UEFA-Champions-league-Player-Statistics.arff"
)
DOSSIER_CACHE = Path("donnees/cache_openml_ldc")
FICHIER_CACHE = DOSSIER_CACHE / "joueurs_ldc_openml.arff"

COLONNES_JOUEURS = [
    "championnat",
    "saison",
    "equipe",
    "joueur",
    "poste",
    "matchs",
    "minutes",
    "buts",
    "passes_decisives",
    "tirs",
    "passes_cles",
    "xg",
    "xa",
    "buts_hors_penalty",
    "xg_hors_penalty",
    "xg_chaine",
    "xg_construction",
    "carton_jaune",
    "carton_rouge",
]

# Slugs OpenML / Sofascore-like -> noms football-data du projet.
ALIAS_EQUIPES = {
    "manchester-united": "Man United",
    "manchester-city": "Man City",
    "tottenham": "Tottenham",
    "chelsea": "Chelsea",
    "arsenal": "Arsenal",
    "liverpool": "Liverpool",
    "real-madrid": "Real Madrid",
    "barcelona": "Barcelona",
    "atletico-madrid": "Ath Madrid",
    "sevilla": "Sevilla",
    "valencia": "Valencia CF",
    "villarreal": "Villarreal",
    "athletic-club": "Ath Bilbao",
    "real-sociedad": "Sociedad",
    "bayern-munich": "Bayern Munich",
    "borussia-dortmund": "Dortmund",
    "bayer-04-leverkusen": "Leverkusen",
    "bayer-leverkusen": "Leverkusen",
    "rb-leipzig": "RB Leipzig",
    "schalke-04": "Schalke 04",
    "wolfsburg": "Wolfsburg",
    "monchengladbach": "M'gladbach",
    "borussia-mgladbach": "M'gladbach",
    "juventus": "Juventus",
    "inter": "Inter",
    "ac-milan": "Milan",
    "napoli": "Napoli",
    "roma": "Roma",
    "lazio": "Lazio",
    "atalanta": "Atalanta",
    "paris-saint-germain": "Paris SG",
    "lyon": "Olympique Lyonnais",
    "monaco": "Monaco",
    "as-monaco": "Monaco",
    "lille": "Lille",
    "marseille": "Marseille",
    "ajax": "Ajax",
    "psv": "PSV",
    "porto": "Porto",
    "benfica": "Benfica",
    "sporting-cp": "Sporting CP",
    "celtic": "Celtic",
    "galatasaray": "Galatasaray",
    "olympiakos-piraeus": "Olympiakos Piraeus",
    "olympiacos": "Olympiakos Piraeus",
    "shakhtar-donetsk": "Shakhtar Donetsk",
    "dynamo-kyiv": "Dynamo Kyiv",
    "zenit": "Zenit St. Petersburg",
    "cska-moscow": "CSKA Moskva",
    "lokomotiv-moscow": "Lokomotiv Moskva",
    "red-star-belgrade": "Crvena Zvezda",
    "crvena-zvezda": "Crvena Zvezda",
    "dinamo-zagreb": "Dinamo Zagreb",
    "club-brugge": "Club Brugge",
    "anderlecht": "Anderlecht",
    "basel": "Basel",
    "young-boys": "BSC Young Boys",
    "salzburg": "RB Salzburg",
    "red-bull-salzburg": "RB Salzburg",
    "slavia-prague": "Slavia Prague",
    "viktoria-plzen": "Viktoria Plzen",
    "genk": "KRC Genk",
}


def telecharger_arff():
    DOSSIER_CACHE.mkdir(parents=True, exist_ok=True)
    if FICHIER_CACHE.exists() and FICHIER_CACHE.stat().st_size > 1000:
        return FICHIER_CACHE.read_text(encoding="utf-8", errors="replace")
    print("Telechargement OpenML 43510 (CC0)...")
    session = requests.Session()
    session.headers.update(
        {"User-Agent": "StatsChampionnats/1.0 (projet local; OpenML LDC CC0)"}
    )
    reponse = session.get(URL_ARFF, timeout=180)
    reponse.raise_for_status()
    texte = reponse.content.decode("utf-8", errors="replace")
    FICHIER_CACHE.write_text(texte, encoding="utf-8")
    return texte


def decouper_ligne_arff(ligne):
    """Decoupe une ligne @DATA en tenant compte des guillemets."""
    champs = []
    courant = []
    dans_guillemets = False
    for car in ligne:
        if car == "'" and not dans_guillemets:
            dans_guillemets = True
            continue
        if car == "'" and dans_guillemets:
            dans_guillemets = False
            continue
        if car == "," and not dans_guillemets:
            champs.append("".join(courant).strip())
            courant = []
            continue
        courant.append(car)
    champs.append("".join(courant).strip())
    return champs


def lire_arff(texte):
    attributs = []
    for ligne in texte.splitlines():
        propre = ligne.strip()
        if propre.upper().startswith("@ATTRIBUTE"):
            parties = propre.split()
            if len(parties) >= 2:
                attributs.append(parties[1])
        if propre.upper() == "@DATA":
            break
    debut = texte.upper().find("@DATA")
    if debut < 0:
        return attributs, []
    corps = texte[debut:].splitlines()[1:]
    lignes = []
    for brut in corps:
        ligne = brut.strip()
        if not ligne or ligne.startswith("%"):
            continue
        valeurs = decouper_ligne_arff(ligne)
        if len(valeurs) != len(attributs):
            continue
        lignes.append(dict(zip(attributs, valeurs)))
    return attributs, lignes


def saison_depuis_openml(valeur):
    """13/14 -> 2013-2014."""
    texte = valeur or ""
    match = re.search(r"(\d{2})/(\d{2})", texte)
    if not match:
        return ""
    debut, fin = int(match.group(1)), int(match.group(2))
    return f"20{debut:02d}-20{fin:02d}"


def entier_ou_vide(valeur):
    if valeur is None or valeur == "" or valeur == "?":
        return ""
    try:
        return str(int(float(valeur)))
    except (TypeError, ValueError):
        return ""


def nom_equipe(slug, noms_connus):
    cle = (slug or "").strip().lower().replace(" ", "-")
    if cle in ALIAS_EQUIPES:
        return ALIAS_EQUIPES[cle]
    libelle = cle.replace("-", " ").strip()
    via_of = nom_depuis_openfootball(libelle.title(), noms_connus)
    if via_of:
        return via_of
    cible = normaliser(libelle)
    for nom in noms_connus:
        if cible and (cible == normaliser(nom) or cible in normaliser(nom)):
            return nom
    return libelle.title() if libelle else slug


def noms_equipes_ldc():
    noms = set()
    for chemin in (
        DOSSIER_SORTIE / "equipes.csv",
        DOSSIER_SORTIE / "matchs.csv",
    ):
        for ligne in lire_csv(chemin):
            if ligne.get("championnat") != NOM_LDC:
                continue
            if chemin.name == "equipes.csv":
                noms.add(ligne.get("equipe") or "")
            else:
                noms.add(ligne.get("domicile") or "")
                noms.add(ligne.get("exterieur") or "")
    noms.discard("")
    return noms


def convertir_ligne(brut, noms_connus):
    saison = saison_depuis_openml(brut.get("season_year") or brut.get("season"))
    joueur = (brut.get("name") or "").strip()
    if not saison or not joueur:
        return None, None
    equipe = nom_equipe(brut.get("team") or "", noms_connus)
    matchs = entier_ou_vide(brut.get("appearances"))
    minutes = entier_ou_vide(brut.get("minutesPlayed"))
    buts = entier_ou_vide(brut.get("goals"))
    assists = entier_ou_vide(brut.get("assists"))
    tirs = entier_ou_vide(brut.get("totalShots"))
    passes_cles = entier_ou_vide(brut.get("keyPasses"))
    jaunes = entier_ou_vide(brut.get("yellowCards"))
    rouges = entier_ou_vide(brut.get("redCards"))
    penalties = entier_ou_vide(brut.get("penaltyGoals"))
    buts_hp = ""
    if buts != "" and penalties != "":
        buts_hp = str(max(0, int(buts) - int(penalties)))
    elif buts != "":
        buts_hp = buts

    joueur_ligne = {
        "championnat": NOM_LDC,
        "saison": saison,
        "equipe": equipe,
        "joueur": joueur,
        "poste": "",
        "matchs": matchs,
        "minutes": minutes,
        "buts": buts,
        "passes_decisives": assists,
        "tirs": tirs,
        "passes_cles": passes_cles,
        "xg": "",
        "xa": "",
        "buts_hors_penalty": buts_hp,
        "xg_hors_penalty": "",
        "xg_chaine": "",
        "xg_construction": "",
        "carton_jaune": jaunes,
        "carton_rouge": rouges,
    }
    defense = {
        "championnat": NOM_LDC,
        "saison": saison,
        "equipe": equipe,
        "joueur": joueur,
        "matchs": matchs,
        "tacles": entier_ou_vide(brut.get("tackles")),
        "tacles_reussis": entier_ou_vide(brut.get("tacklesWon")),
        "interceptions": entier_ou_vide(brut.get("interceptions")),
        "blocs": entier_ou_vide(brut.get("blockedShots")),
        "degagements": entier_ou_vide(brut.get("clearances")),
        "duels": "",
        "duels_gagnes": entier_ou_vide(brut.get("totalDuelsWon")),
        "recoveries": "",
        "pressions": "",
        "arrets": entier_ou_vide(brut.get("saves")),
        "xg_tirs_subis": "",
        "source": SOURCE,
    }
    return joueur_ligne, defense


def fusionner_joueurs(anciens, nouveaux):
    autres = [l for l in anciens if l.get("championnat") != NOM_LDC]
    return autres + nouveaux


def couverture(defense_lignes):
    par_saison = {}
    for ligne in defense_lignes:
        saison = ligne.get("saison") or ""
        par_saison.setdefault(saison, 0)
        par_saison[saison] += 1
    sorties = []
    for saison, nb in sorted(par_saison.items()):
        sorties.append(
            {
                "championnat": NOM_LDC,
                "saison": saison,
                "source": SOURCE,
                "nb_matchs": "0",
                "complet": "0",
                "commentaire": (
                    f"{nb} joueurs (OpenML 43510 CC0, agregats saison ; "
                    "pas de xG ; 2013-2020)"
                ),
            }
        )
    return sorties


def collecter():
    texte = telecharger_arff()
    _attributs, bruts = lire_arff(texte)
    print(f"  {len(bruts)} lignes OpenML lues")
    noms_connus = noms_equipes_ldc()
    joueurs = []
    defenses = []
    for brut in bruts:
        j, d = convertir_ligne(brut, noms_connus)
        if j:
            joueurs.append(j)
            defenses.append(d)
    print(f"  {len(joueurs)} joueurs LDC convertis")

    chemin_joueurs = DOSSIER_SORTIE / "joueurs.csv"
    anciens = lire_csv(chemin_joueurs)
    ecrire_csv(chemin_joueurs, fusionner_joueurs(anciens, joueurs), COLONNES_JOUEURS)
    remplacer_source(FICHIER_DEFENSE, SOURCE, defenses, COLONNES_DEFENSE)

    anciennes_couv = [
        l for l in lire_csv(FICHIER_COUVERTURE) if l.get("source") != SOURCE
    ]
    ecrire_csv(
        FICHIER_COUVERTURE,
        anciennes_couv + couverture(defenses),
        COLONNES_COUVERTURE,
    )
    return joueurs, defenses


def main():
    print("Joueurs LDC (OpenML 43510, CC0)...")
    joueurs, defenses = collecter()
    saisons = sorted({j["saison"] for j in joueurs})
    print(f"   saisons: {', '.join(saisons)}")
    print(f"   defense: {len(defenses)} lignes source={SOURCE}")


if __name__ == "__main__":
    main()
