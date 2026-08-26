"""
Cree une base SQLite et y importe les CSV des championnats (5 ligues + LDC).
Usage : python scripts/creer_base.py
"""

import csv
import os
import sqlite3
import time
from pathlib import Path

DOSSIER = Path("donnees/cinq_championnats")
FICHIER_BASE = Path("donnees/football.db")

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
    "nb_matchs",
    "complet",
    "rang",
    "niveau",
    "age",
    "valeur_marche_eur",
    "valeur_max_eur",
    "derniere_saison_dump",
    "frais_eur",
}
COLONNES_REEL = {
    "xg",
    "xa",
    "xg_hors_penalty",
    "xg_chaine",
    "xg_construction",
    "xg_domicile",
    "xg_exterieur",
    "xg_tirs_subis",
    "elo",
}

TABLES = {
    "matchs": "matchs.csv",
    "matchs_xg": "matchs_xg.csv",
    "joueurs": "joueurs.csv",
    "equipes": "equipes.csv",
    "sites_equipes": "sites_equipes.csv",
    "calendrier": "calendrier.csv",
    "actions_defensives": "actions_defensives.csv",
    "couverture_sources": "couverture_sources.csv",
    "classements_elo": "classements_elo.csv",
    "valeurs_marche_joueurs": "valeurs_marche_joueurs.csv",
    "transferts_joueurs": "transferts_joueurs.csv",
}

INDEXS = [
    "CREATE INDEX IF NOT EXISTS idx_matchs_saison ON matchs (championnat, saison)",
    "CREATE INDEX IF NOT EXISTS idx_matchs_equipes ON matchs (domicile, exterieur)",
    "CREATE INDEX IF NOT EXISTS idx_joueurs_saison ON joueurs (championnat, saison)",
    "CREATE INDEX IF NOT EXISTS idx_joueurs_equipe ON joueurs (equipe)",
    "CREATE INDEX IF NOT EXISTS idx_joueurs_nom ON joueurs (joueur)",
    "CREATE INDEX IF NOT EXISTS idx_calendrier_saison ON calendrier (championnat, saison)",
    "CREATE INDEX IF NOT EXISTS idx_calendrier_equipes ON calendrier (domicile, exterieur)",
    "CREATE INDEX IF NOT EXISTS idx_defense_saison ON actions_defensives (championnat, saison)",
    "CREATE INDEX IF NOT EXISTS idx_defense_equipe ON actions_defensives (equipe)",
    "CREATE INDEX IF NOT EXISTS idx_defense_joueur ON actions_defensives (joueur)",
    "CREATE INDEX IF NOT EXISTS idx_elo_pays ON classements_elo (pays, niveau)",
    "CREATE INDEX IF NOT EXISTS idx_elo_club ON classements_elo (club)",
    "CREATE INDEX IF NOT EXISTS idx_valeurs_joueur ON valeurs_marche_joueurs (joueur)",
    "CREATE INDEX IF NOT EXISTS idx_transferts_joueur ON transferts_joueurs (joueur)",
]


def type_sql(nom):
    if nom in COLONNES_ENTIER:
        return "INTEGER"
    if nom in COLONNES_REEL:
        return "REAL"
    return "TEXT"


def convertir(nom, valeur):
    if valeur is None or str(valeur).strip() == "":
        return None
    if nom in COLONNES_ENTIER:
        return int(float(valeur))
    if nom in COLONNES_REEL:
        return float(valeur)
    return valeur


def creer_table(connexion, nom_table, colonnes):
    definition = ", ".join(f"{col} {type_sql(col)}" for col in colonnes)
    connexion.execute(f"DROP TABLE IF EXISTS {nom_table}")
    connexion.execute(f"CREATE TABLE {nom_table} ({definition})")


def importer_csv(connexion, nom_table, chemin):
    with open(chemin, newline="", encoding="utf-8") as fichier:
        lecteur = csv.DictReader(fichier)
        colonnes = lecteur.fieldnames
        creer_table(connexion, nom_table, colonnes)
        places = ", ".join(["?"] * len(colonnes))
        noms = ", ".join(colonnes)
        requete = f"INSERT INTO {nom_table} ({noms}) VALUES ({places})"
        lignes = []
        for ligne in lecteur:
            lignes.append([convertir(col, ligne.get(col, "")) for col in colonnes])
        connexion.executemany(requete, lignes)
    return len(lignes)


def sauver_photos(chemin_base):
    if not chemin_base.exists():
        return []
    connexion = sqlite3.connect(chemin_base)
    try:
        return list(
            connexion.execute(
                "SELECT joueur, fichier, source FROM photos_joueurs"
            )
        )
    except sqlite3.OperationalError:
        return []
    finally:
        connexion.close()


def restaurer_photos(connexion, lignes):
    if not lignes:
        return
    connexion.execute(
        """
        CREATE TABLE IF NOT EXISTS photos_joueurs (
            joueur TEXT PRIMARY KEY,
            fichier TEXT,
            source TEXT
        )
        """
    )
    connexion.executemany(
        "INSERT OR REPLACE INTO photos_joueurs (joueur, fichier, source) VALUES (?, ?, ?)",
        lignes,
    )


def remplacer_base(temporaire):
    for essai in range(8):
        try:
            os.replace(temporaire, FICHIER_BASE)
            return
        except PermissionError:
            print("  base encore ouverte, nouvel essai...")
            time.sleep(1)
    raise PermissionError(f"Impossible de remplacer {FICHIER_BASE}")


def main():
    FICHIER_BASE.parent.mkdir(parents=True, exist_ok=True)
    photos = sauver_photos(FICHIER_BASE)
    temporaire = FICHIER_BASE.with_name("football-nouveau.db")
    if temporaire.exists():
        temporaire.unlink()

    connexion = sqlite3.connect(temporaire)
    try:
        for nom_table, nom_fichier in TABLES.items():
            chemin = DOSSIER / nom_fichier
            if not chemin.exists():
                print(f"  {nom_table}: fichier absent, ignore")
                continue
            nb = importer_csv(connexion, nom_table, chemin)
            print(f"  {nom_table}: {nb} lignes")
        for index in INDEXS:
            try:
                connexion.execute(index)
            except sqlite3.OperationalError:
                continue
        restaurer_photos(connexion, photos)
        connexion.commit()
    finally:
        connexion.close()

    remplacer_base(temporaire)
    print(f"Base creee : {FICHIER_BASE.resolve()}")


if __name__ == "__main__":
    main()
