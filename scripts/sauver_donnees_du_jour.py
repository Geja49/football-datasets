"""
Sauve un JSON date avec les donnees recoltees du jour.

Usage (apres la collecte, a la racine) :
    python scripts/sauver_donnees_du_jour.py
"""

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 23h heure de l'Est en ete = UTC-4 (pas besoin du paquet tzdata).
FUSEAU = timezone(timedelta(hours=-4))
DOSSIER_CSV = Path("donnees/cinq_championnats")
DOSSIER_JSON = Path("rapports/donnees")
ANNEE_COURANTE = 2026
SAISON_COURANTE = f"{ANNEE_COURANTE}-{ANNEE_COURANTE + 1}"

COLONNES_ENTIER = {
    "buts_domicile",
    "buts_exterieur",
    "buts_domicile_mt",
    "buts_exterieur_mt",
    "tirs_domicile",
    "tirs_exterieur",
    "tirs_cadres_domicile",
    "tirs_cadres_exterieur",
    "fautes_domicile",
    "fautes_exterieur",
    "corners_domicile",
    "corners_exterieur",
    "jaunes_domicile",
    "jaunes_exterieur",
    "rouges_domicile",
    "rouges_exterieur",
    "matchs",
    "minutes",
    "buts",
    "passes_decisives",
    "tirs",
    "passes_cles",
    "buts_hors_penalty",
    "carton_jaune",
    "carton_rouge",
}
COLONNES_REEL = {
    "xg",
    "xa",
    "xg_hors_penalty",
    "xg_chaine",
    "xg_construction",
    "xg_domicile",
    "xg_exterieur",
}


def convertir(nom, valeur):
    if valeur is None or str(valeur).strip() == "":
        return None
    if nom in COLONNES_ENTIER:
        return int(float(valeur))
    if nom in COLONNES_REEL:
        return float(valeur)
    return valeur


def lire_csv(nom_fichier):
    chemin = DOSSIER_CSV / nom_fichier
    if not chemin.exists():
        return []
    with open(chemin, newline="", encoding="utf-8") as fichier:
        return [
            {nom: convertir(nom, ligne.get(nom, "")) for nom in ligne}
            for ligne in csv.DictReader(fichier)
        ]


def filtrer_saison(lignes, saison):
    return [ligne for ligne in lignes if ligne.get("saison") == saison]


def filtrer_date(lignes, journee):
    return [ligne for ligne in lignes if (ligne.get("date") or "")[:10] == journee]


def main():
    maintenant = datetime.now(FUSEAU)
    journee = maintenant.strftime("%Y-%m-%d")
    matchs = lire_csv("matchs.csv")
    matchs_xg = lire_csv("matchs_xg.csv")
    calendrier = lire_csv("calendrier.csv")
    joueurs = lire_csv("joueurs.csv")
    sortie = {
        "date": journee,
        "heure": maintenant.strftime("%H:%M"),
        "fuseau": "UTC-4",
        "saison": SAISON_COURANTE,
        "matchs_du_jour": filtrer_date(matchs, journee),
        "matchs_xg_du_jour": filtrer_date(matchs_xg, journee),
        "matchs": filtrer_saison(matchs, SAISON_COURANTE),
        "matchs_xg": filtrer_saison(matchs_xg, SAISON_COURANTE),
        "calendrier": filtrer_saison(calendrier, SAISON_COURANTE),
        "joueurs": filtrer_saison(joueurs, SAISON_COURANTE),
    }
    DOSSIER_JSON.mkdir(parents=True, exist_ok=True)
    chemin = DOSSIER_JSON / f"{journee}.json"
    chemin.write_text(
        json.dumps(sortie, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"JSON du jour : {chemin}")
    print(f"  matchs du jour : {len(sortie['matchs_du_jour'])}")
    print(f"  matchs {SAISON_COURANTE} : {len(sortie['matchs'])}")
    print(f"  joueurs {SAISON_COURANTE} : {len(sortie['joueurs'])}")


if __name__ == "__main__":
    main()
