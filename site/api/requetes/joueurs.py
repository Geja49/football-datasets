"""Requêtes SQL liées aux joueurs (football.db)."""

from __future__ import annotations

import sqlite3

from requetes.connexion import lignes_dict

COLONNES_MEILLEURS = {
    "buts": "buts",
    "passes": "passes_decisives",
}


def lister_meilleurs(connexion, championnat, saison, colonne):
    """Top 20 joueurs pour une colonne (buts ou passes_decisives)."""
    return lignes_dict(
        connexion.execute(
            f"""
            SELECT joueur, equipe, poste, matchs, minutes,
                   buts, passes_decisives, tirs, xg, xa
            FROM joueurs
            WHERE championnat = ? AND saison = ? AND minutes > 0
            ORDER BY {colonne} DESC, minutes DESC
            LIMIT 20
            """,
            (championnat, saison),
        )
    )


def saison_avec_joueurs(connexion, championnat):
    """Dernière saison avec des minutes jouées pour un championnat."""
    try:
        ligne = connexion.execute(
            """
            SELECT saison FROM joueurs
            WHERE championnat = ? AND minutes > 0
            GROUP BY saison
            ORDER BY saison DESC
            LIMIT 1
            """,
            (championnat,),
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    return ligne[0] if ligne else None
