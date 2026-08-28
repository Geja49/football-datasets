"""Requêtes SQL — matchs, calendrier, confrontations (football.db)."""

from __future__ import annotations

import sqlite3

from requetes.connexion import lignes_dict

SAISON_COURANTE_DEFAUT = "2026-2027"


def lire_horaire_match(connexion, championnat, saison, domicile, exterieur):
    """Date et heure locale d'un match du calendrier."""
    try:
        ligne = connexion.execute(
            """
            SELECT date, heure FROM calendrier
            WHERE championnat = ? AND saison = ?
              AND domicile = ? AND exterieur = ?
            ORDER BY date ASC
            LIMIT 1
            """,
            (championnat, saison, domicile, exterieur),
        ).fetchone()
    except sqlite3.OperationalError:
        ligne = None
    if not ligne:
        return None
    return {"date": ligne["date"], "heure": ligne["heure"] or ""}


def lire_calendrier(connexion, championnat, saison, equipe=None):
    """Lignes calendrier pour une compétition (optionnellement filtrées par équipe)."""
    try:
        if equipe:
            curseur = connexion.execute(
                """
                SELECT date, heure, journee, domicile, exterieur
                FROM calendrier
                WHERE championnat = ? AND saison = ?
                  AND (domicile = ? OR exterieur = ?)
                ORDER BY date, heure
                """,
                (championnat, saison, equipe, equipe),
            )
        else:
            curseur = connexion.execute(
                """
                SELECT date, heure, journee, domicile, exterieur
                FROM calendrier
                WHERE championnat = ? AND saison = ?
                ORDER BY date, heure
                """,
                (championnat, saison),
            )
        return lignes_dict(curseur)
    except sqlite3.OperationalError:
        return []


def saisons_disponibles(connexion, championnat=None, saison_courante=SAISON_COURANTE_DEFAUT):
    """Liste les saisons en base ; la saison en cours apparaît même si peu de données."""
    saisons = {saison_courante}
    for table in ("matchs", "calendrier"):
        try:
            if championnat:
                curseur = connexion.execute(
                    f"SELECT saison FROM {table} WHERE championnat = ? GROUP BY saison",
                    (championnat,),
                )
            else:
                curseur = connexion.execute(f"SELECT saison FROM {table} GROUP BY saison")
            for row in curseur:
                saisons.add(row[0])
        except sqlite3.OperationalError:
            continue
    return sorted(saisons, reverse=True)


def lister_matchs_classement(connexion, championnat, saison):
    """Matchs d'une compétition pour le calcul du classement."""
    try:
        return lignes_dict(
            connexion.execute(
                """
                SELECT date, domicile, exterieur, buts_domicile, buts_exterieur, resultat, phase
                FROM matchs
                WHERE championnat = ? AND saison = ?
                """,
                (championnat, saison),
            )
        )
    except sqlite3.OperationalError:
        return lignes_dict(
            connexion.execute(
                """
                SELECT date, domicile, exterieur, buts_domicile, buts_exterieur, resultat
                FROM matchs
                WHERE championnat = ? AND saison = ?
                """,
                (championnat, saison),
            )
        )


def lister_matchs_joues_saison(connexion, championnat, saison):
    """Matchs joués d'une compétition (programme / calendrier)."""
    return lignes_dict(
        connexion.execute(
            """
            SELECT date, domicile, exterieur, buts_domicile, buts_exterieur
            FROM matchs
            WHERE championnat = ? AND saison = ?
            ORDER BY date
            """,
            (championnat, saison),
        )
    )


def lister_matchs_joues_jour(connexion, jour):
    """Matchs joués à une date donnée (toutes compétitions)."""
    return lignes_dict(
        connexion.execute(
            """
            SELECT date, saison, championnat, domicile, exterieur,
                   buts_domicile, buts_exterieur
            FROM matchs
            WHERE date = ?
            """,
            (jour,),
        )
    )


def lister_calendrier_jour(connexion, jour):
    """Matchs à venir du calendrier pour une date."""
    try:
        return lignes_dict(
            connexion.execute(
                """
                SELECT date, saison, championnat, heure, journee,
                       domicile, exterieur
                FROM calendrier
                WHERE date = ?
                """,
                (jour,),
            )
        )
    except sqlite3.OperationalError:
        return []


def choisir_prochain_jour(connexion, aujourd_hui):
    """Premier jour avec match joué ou à venir à partir d'aujourd'hui."""
    try:
        ligne = connexion.execute(
            """
            SELECT MIN(date) FROM (
                SELECT date FROM matchs WHERE date >= ?
                UNION
                SELECT date FROM calendrier WHERE date >= ?
            )
            """,
            (aujourd_hui, aujourd_hui),
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    return ligne[0] if ligne and ligne[0] else None


def lister_lignes_xg(connexion, championnat, saison):
    """Lignes xG Understat pour une compétition."""
    try:
        return connexion.execute(
            """
            SELECT date, domicile, exterieur, xg_domicile, xg_exterieur
            FROM matchs_xg
            WHERE championnat = ? AND saison = ?
            """,
            (championnat, saison),
        ).fetchall()
    except sqlite3.OperationalError:
        return None


def lister_matchs_equipe_fiche(connexion, championnat, saison, nom_equipe):
    """Matchs joués d'une équipe dans une compétition."""
    return lignes_dict(
        connexion.execute(
            """
            SELECT date, domicile, exterieur, buts_domicile, buts_exterieur,
                   resultat, tirs_domicile, tirs_exterieur,
                   tirs_cadres_domicile, tirs_cadres_exterieur,
                   jaunes_domicile, jaunes_exterieur,
                   rouges_domicile, rouges_exterieur
            FROM matchs
            WHERE championnat = ? AND saison = ?
              AND (domicile = ? OR exterieur = ?)
            ORDER BY date
            """,
            (championnat, saison, nom_equipe, nom_equipe),
        )
    )


def lister_matchs_radar_ligue(connexion, championnat, saison):
    """Matchs joués avec stats pour le radar équipe ligue."""
    try:
        return lignes_dict(
            connexion.execute(
                """
                SELECT date, domicile, exterieur, buts_domicile, buts_exterieur,
                       tirs_domicile, tirs_exterieur
                FROM matchs
                WHERE championnat = ? AND saison = ?
                  AND buts_domicile IS NOT NULL
                  AND buts_exterieur IS NOT NULL
                ORDER BY date
                """,
                (championnat, saison),
            )
        )
    except sqlite3.OperationalError:
        return None


def lister_matchs_radar_equipe(connexion, saison, competitions, noms):
    """Matchs joués ligue + LDC pour le radar d'une équipe."""
    if not noms:
        return []
    places_noms = ", ".join(["?"] * len(noms))
    places_comp = ", ".join(["?"] * len(competitions))
    return lignes_dict(
        connexion.execute(
            f"""
            SELECT date, domicile, exterieur, buts_domicile, buts_exterieur,
                   tirs_domicile, tirs_exterieur, championnat
            FROM matchs
            WHERE saison = ?
              AND championnat IN ({places_comp})
              AND (domicile IN ({places_noms}) OR exterieur IN ({places_noms}))
              AND buts_domicile IS NOT NULL
              AND buts_exterieur IS NOT NULL
            ORDER BY date
            """,
            (saison, *competitions, *noms, *noms),
        )
    )


def lister_buts_equipe_saison(connexion, saison, competitions, noms):
    """Buts marqués par compétition pour une liste de noms d'équipe."""
    if not noms:
        return []
    places_noms = ", ".join(["?"] * len(noms))
    places_comp = ", ".join(["?"] * len(competitions))
    return connexion.execute(
        f"""
        SELECT championnat, domicile, exterieur, buts_domicile, buts_exterieur
        FROM matchs
        WHERE saison = ?
          AND championnat IN ({places_comp})
          AND (domicile IN ({places_noms}) OR exterieur IN ({places_noms}))
        """,
        (saison, *competitions, *noms, *noms),
    )


def rechercher_equipes_par_motif(connexion, motif):
    """Équipes dont le nom correspond au motif (matchs joués)."""
    return lignes_dict(
        connexion.execute(
            """
            SELECT DISTINCT domicile AS equipe, championnat, saison
            FROM matchs
            WHERE domicile LIKE ?
            UNION
            SELECT DISTINCT exterieur, championnat, saison
            FROM matchs
            WHERE exterieur LIKE ?
            ORDER BY saison DESC
            LIMIT 15
            """,
            (motif, motif),
        )
    )
