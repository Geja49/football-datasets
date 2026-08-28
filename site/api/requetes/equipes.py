"""Requêtes SQL — équipes, classement, sites (football.db)."""

from __future__ import annotations

import sqlite3

from requetes.connexion import lignes_dict


def lire_site_equipe(connexion, nom_equipe):
    """Fiche site officiel / logo depuis sites_equipes."""
    try:
        ligne = connexion.execute(
            """
            SELECT nom_officiel, url_site, url_logo, stade
            FROM sites_equipes
            WHERE equipe = ?
            """,
            (nom_equipe,),
        ).fetchone()
    except sqlite3.OperationalError:
        ligne = None
    return dict(ligne) if ligne else None


def choisir_nom_dans_competition(connexion, championnat, saison, noms):
    """Nom tel qu'il apparaît dans les matchs (ou le calendrier) de la compétition."""
    if not noms:
        return ""
    places = ", ".join(["?"] * len(noms))
    requete = f"""
        SELECT nom FROM (
            SELECT domicile AS nom FROM matchs
            WHERE championnat = ? AND saison = ? AND domicile IN ({places})
            UNION
            SELECT exterieur FROM matchs
            WHERE championnat = ? AND saison = ? AND exterieur IN ({places})
        )
        LIMIT 1
        """
    ligne = connexion.execute(
        requete,
        (championnat, saison, *noms, championnat, saison, *noms),
    ).fetchone()
    if ligne:
        return ligne[0]
    try:
        ligne = connexion.execute(
            f"""
            SELECT nom FROM (
                SELECT domicile AS nom FROM calendrier
                WHERE championnat = ? AND saison = ? AND domicile IN ({places})
                UNION
                SELECT exterieur FROM calendrier
                WHERE championnat = ? AND saison = ? AND exterieur IN ({places})
            )
            LIMIT 1
            """,
            (championnat, saison, *noms, championnat, saison, *noms),
        ).fetchone()
    except sqlite3.OperationalError:
        ligne = None
    return ligne[0] if ligne else noms[0]


def lister_equipes_distinctes_joueurs(connexion, championnat, saison):
    """Noms d'équipes Understat pour une compétition."""
    return [
        row[0]
        for row in connexion.execute(
            """
            SELECT DISTINCT equipe FROM joueurs
            WHERE championnat = ? AND saison = ?
            """,
            (championnat, saison),
        )
    ]


def lister_noms_equipes_ligues(connexion, saison, ligues):
    """Noms d'équipes distinctes dans les ligues nationales (hors LDC)."""
    if not ligues:
        return []
    places = ", ".join(["?"] * len(ligues))
    return [
        row[0]
        for row in connexion.execute(
            f"""
            SELECT DISTINCT equipe FROM joueurs
            WHERE saison = ? AND championnat IN ({places})
            """,
            (saison, *ligues),
        )
    ]


def lister_joueurs_equipe(connexion, championnat, saison, nom_stats):
    """Effectif Understat d'une équipe (matching flexible sur le nom)."""
    return lignes_dict(
        connexion.execute(
            """
            SELECT joueur, poste, matchs, minutes, buts, passes_decisives,
                   tirs, passes_cles, xg, xa, xg_chaine, xg_construction,
                   carton_jaune, carton_rouge, equipe
            FROM joueurs
            WHERE championnat = ? AND saison = ?
              AND (equipe = ? OR equipe LIKE ? OR equipe LIKE ?)
            ORDER BY buts DESC, minutes DESC
            """,
            (
                championnat,
                saison,
                nom_stats,
                nom_stats + ",%",
                "%," + nom_stats,
            ),
        )
    )


def lister_joueurs_equipe_ldc_fallback(connexion, ligues, saison, nom_stats):
    """Effectif depuis les ligues nationales quand la LDC n'a pas de joueurs."""
    if not ligues:
        return []
    places = ", ".join(["?"] * len(ligues))
    return lignes_dict(
        connexion.execute(
            f"""
            SELECT joueur, poste, matchs, minutes, buts, passes_decisives,
                   tirs, passes_cles, xg, xa, xg_chaine, xg_construction,
                   carton_jaune, carton_rouge, equipe
            FROM joueurs
            WHERE championnat IN ({places}) AND saison = ?
              AND (equipe = ? OR equipe LIKE ? OR equipe LIKE ?)
            ORDER BY buts DESC, minutes DESC
            """,
            (
                *ligues,
                saison,
                nom_stats,
                nom_stats + ",%",
                "%," + nom_stats,
            ),
        )
    )


def table_existe(connexion, nom):
    """Vérifie l'existence d'une table SQLite."""
    ligne = connexion.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (nom,),
    ).fetchone()
    return bool(ligne)


def lire_couverture_defense(connexion, championnat, saison):
    """Lignes couverture_sources pour une compétition."""
    try:
        return lignes_dict(
            connexion.execute(
                """
                SELECT source, nb_matchs, complet, commentaire
                FROM couverture_sources
                WHERE championnat = ? AND saison = ?
                """,
                (championnat, saison),
            )
        )
    except sqlite3.OperationalError:
        return None
