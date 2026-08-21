"""Helpers partages pour les stats defensives (CSV + noms)."""

import csv
from pathlib import Path

DOSSIER_SORTIE = Path("donnees/cinq_championnats")
FICHIER_DEFENSE = DOSSIER_SORTIE / "actions_defensives.csv"
FICHIER_COUVERTURE = DOSSIER_SORTIE / "couverture_sources.csv"

COLONNES_DEFENSE = [
    "championnat",
    "saison",
    "equipe",
    "joueur",
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
    "source",
]

COLONNES_COUVERTURE = [
    "championnat",
    "saison",
    "source",
    "nb_matchs",
    "complet",
    "commentaire",
]


def stats_vides():
    return {
        "matchs_ids": set(),
        "tacles": 0,
        "tacles_reussis": 0,
        "interceptions": 0,
        "blocs": 0,
        "degagements": 0,
        "duels": 0,
        "duels_gagnes": 0,
        "recoveries": 0,
        "pressions": 0,
        "arrets": 0,
        "xg_tirs_subis": 0.0,
    }


def ligne_defense(championnat, saison, equipe, joueur, stats, source):
    return {
        "championnat": championnat,
        "saison": saison,
        "equipe": equipe,
        "joueur": joueur,
        "matchs": len(stats["matchs_ids"]),
        "tacles": stats["tacles"],
        "tacles_reussis": stats["tacles_reussis"],
        "interceptions": stats["interceptions"],
        "blocs": stats["blocs"],
        "degagements": stats["degagements"],
        "duels": stats["duels"],
        "duels_gagnes": stats["duels_gagnes"],
        "recoveries": stats["recoveries"],
        "pressions": stats["pressions"],
        "arrets": stats["arrets"],
        "xg_tirs_subis": round(stats["xg_tirs_subis"], 2),
        "source": source,
    }


def lire_csv(chemin):
    if not Path(chemin).exists():
        return []
    with open(chemin, newline="", encoding="utf-8") as fichier:
        return list(csv.DictReader(fichier))


def ecrire_csv(chemin, lignes, champs=None):
    chemin = Path(chemin)
    if not lignes and not champs:
        return
    if not champs:
        champs = []
        vus = set()
        for ligne in lignes:
            for nom in ligne:
                if nom not in vus:
                    vus.add(nom)
                    champs.append(nom)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", newline="", encoding="utf-8") as fichier:
        writer = csv.DictWriter(fichier, fieldnames=champs, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(lignes)


def remplacer_source(chemin, source, nouvelles, champs):
    anciennes = [ligne for ligne in lire_csv(chemin) if ligne.get("source") != source]
    ecrire_csv(chemin, anciennes + nouvelles, champs)


def saison_tirets(nom):
    """2015/2016 -> 2015-2016."""
    texte = (nom or "").replace("/", "-")
    parties = texte.split("-")
    if len(parties) == 2 and len(parties[1]) == 2:
        siecle = parties[0][:2]
        return f"{parties[0]}-{siecle}{parties[1]}"
    return texte


def charger_env(racine):
    """Charge .env sans ecraser les variables deja presentes. Ne journalise jamais la valeur."""
    import os

    chemin = Path(racine) / ".env"
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
