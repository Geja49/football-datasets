"""Requêtes SQL — calendrier Solo + pronos/verdicts figés (analyses.db)."""

from __future__ import annotations

import sqlite3

from modeles.commun import CHAMPIONNATS_VALIDES
from requetes.connexion import lignes_dict

CHAMPIONNATS_SOLO = CHAMPIONNATS_VALIDES


def lister_matchs_weekend_calendrier(
    connexion,
    date_debut: str,
    date_fin: str,
    championnat: str | None = None,
    limite: int = 80,
):
    """Matchs à venir du calendrier dans la fenêtre ven–lun (Big 5 + Super Lig + LDC)."""
    championnats = (championnat,) if championnat else CHAMPIONNATS_SOLO
    places = ", ".join(["?"] * len(championnats))
    params = [date_debut, date_fin, *championnats]
    try:
        return lignes_dict(
            connexion.execute(
                f"""
                SELECT c.date, c.heure, c.journee, c.championnat, c.saison,
                       c.domicile, c.exterieur
                FROM calendrier c
                LEFT JOIN matchs m ON
                    m.championnat = c.championnat
                    AND m.saison = c.saison
                    AND m.date = c.date
                    AND m.domicile = c.domicile
                    AND m.exterieur = c.exterieur
                    AND m.buts_domicile IS NOT NULL
                    AND m.buts_exterieur IS NOT NULL
                WHERE c.date >= ? AND c.date <= ?
                  AND c.championnat IN ({places})
                  AND m.rowid IS NULL
                ORDER BY c.date, c.heure, c.championnat
                LIMIT ?
                """,
                (*params, limite),
            )
        )
    except sqlite3.OperationalError:
        return []


def compter_pronos_solo_weekend(
    connexion_analyses: sqlite3.Connection,
    weekend_debut: str,
    championnat: str | None = None,
) -> int:
    """Nombre de marchés Solo figés pour un weekend."""
    if championnat:
        ligne = connexion_analyses.execute(
            """
            SELECT COUNT(*) AS n FROM pronos_solo
            WHERE weekend_debut = ? AND championnat = ?
            """,
            (weekend_debut, championnat),
        ).fetchone()
    else:
        ligne = connexion_analyses.execute(
            """
            SELECT COUNT(*) AS n FROM pronos_solo
            WHERE weekend_debut = ?
            """,
            (weekend_debut,),
        ).fetchone()
    return int(ligne["n"] if ligne else 0)


def date_fige_weekend(
    connexion_analyses: sqlite3.Connection,
    weekend_debut: str,
) -> str | None:
    """Horodatage du premier fige pour ce weekend (ou None)."""
    ligne = connexion_analyses.execute(
        """
        SELECT MIN(fige_le) AS fige_le FROM pronos_solo
        WHERE weekend_debut = ?
        """,
        (weekend_debut,),
    ).fetchone()
    if not ligne or not ligne["fige_le"]:
        return None
    return str(ligne["fige_le"])


def inserer_prono_solo(
    connexion_analyses: sqlite3.Connection,
    *,
    cle_match: str,
    weekend_debut: str,
    championnat: str,
    saison: str,
    date_match: str,
    domicile: str,
    exterieur: str,
    type_marche: str,
    libelle_marche: str | None,
    probabilite: float,
    detail_json: str | None,
    fige_le: str,
    prevision_id: int | None = None,
    remplacer: bool = False,
) -> bool:
    """
    Insert un marché figé.
    Retourne True si une ligne a été écrite (insert ou mise à jour).
    """
    existante = connexion_analyses.execute(
        """
        SELECT id FROM pronos_solo
        WHERE cle_match = ? AND type_marche = ? AND weekend_debut = ?
        """,
        (cle_match, type_marche, weekend_debut),
    ).fetchone()

    if existante and not remplacer:
        return False

    if existante and remplacer:
        # Supprimer l'ancien verdict : le snapshot est refait.
        connexion_analyses.execute(
            "DELETE FROM verdicts_solo WHERE prono_solo_id = ?",
            (int(existante["id"]),),
        )
        connexion_analyses.execute(
            """
            UPDATE pronos_solo SET
                championnat = ?, saison = ?, date_match = ?,
                domicile = ?, exterieur = ?, libelle_marche = ?,
                probabilite = ?, detail_json = ?, fige_le = ?,
                prevision_id = ?
            WHERE id = ?
            """,
            (
                championnat,
                saison,
                date_match,
                domicile,
                exterieur,
                libelle_marche,
                probabilite,
                detail_json,
                fige_le,
                prevision_id,
                int(existante["id"]),
            ),
        )
        return True

    curseur = connexion_analyses.execute(
        """
        INSERT INTO pronos_solo (
            cle_match, weekend_debut, championnat, saison, date_match,
            domicile, exterieur, type_marche, libelle_marche, probabilite,
            detail_json, fige_le, prevision_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cle_match,
            weekend_debut,
            championnat,
            saison,
            date_match,
            domicile,
            exterieur,
            type_marche,
            libelle_marche,
            probabilite,
            detail_json,
            fige_le,
            prevision_id,
        ),
    )
    return curseur.rowcount > 0


def lister_pronos_solo_weekend(
    connexion_analyses: sqlite3.Connection,
    weekend_debut: str,
    championnat: str | None = None,
):
    """Pronos figés + verdict éventuel pour un weekend."""
    if championnat:
        return lignes_dict(
            connexion_analyses.execute(
                """
                SELECT p.*,
                       v.vrai AS verdict_vrai,
                       v.motif_code AS verdict_motif_code,
                       v.motif_texte AS verdict_motif_texte,
                       v.buts_domicile AS verdict_buts_domicile,
                       v.buts_exterieur AS verdict_buts_exterieur,
                       v.juge_le AS verdict_juge_le
                FROM pronos_solo p
                LEFT JOIN verdicts_solo v ON v.prono_solo_id = p.id
                WHERE p.weekend_debut = ? AND p.championnat = ?
                ORDER BY p.date_match, p.championnat, p.domicile, p.type_marche
                """,
                (weekend_debut, championnat),
            )
        )
    return lignes_dict(
        connexion_analyses.execute(
            """
            SELECT p.*,
                   v.vrai AS verdict_vrai,
                   v.motif_code AS verdict_motif_code,
                   v.motif_texte AS verdict_motif_texte,
                   v.buts_domicile AS verdict_buts_domicile,
                   v.buts_exterieur AS verdict_buts_exterieur,
                   v.juge_le AS verdict_juge_le
            FROM pronos_solo p
            LEFT JOIN verdicts_solo v ON v.prono_solo_id = p.id
            WHERE p.weekend_debut = ?
            ORDER BY p.date_match, p.championnat, p.domicile, p.type_marche
            """,
            (weekend_debut,),
        )
    )


def lister_pronos_solo_sans_verdict(
    connexion_analyses: sqlite3.Connection,
    weekend_debut: str | None = None,
):
    """Pronos figés encore sans verdict (optionnellement filtrés par weekend)."""
    if weekend_debut:
        return lignes_dict(
            connexion_analyses.execute(
                """
                SELECT p.*
                FROM pronos_solo p
                LEFT JOIN verdicts_solo v ON v.prono_solo_id = p.id
                WHERE v.id IS NULL AND p.weekend_debut = ?
                ORDER BY p.date_match, p.id
                """,
                (weekend_debut,),
            )
        )
    return lignes_dict(
        connexion_analyses.execute(
            """
            SELECT p.*
            FROM pronos_solo p
            LEFT JOIN verdicts_solo v ON v.prono_solo_id = p.id
            WHERE v.id IS NULL
            ORDER BY p.weekend_debut, p.date_match, p.id
            """
        )
    )


def inserer_verdict_solo(
    connexion_analyses: sqlite3.Connection,
    *,
    prono_solo_id: int,
    vrai: bool,
    motif_code: str | None,
    motif_texte: str | None,
    buts_domicile: int | None,
    buts_exterieur: int | None,
    juge_le: str,
) -> None:
    """Enregistre un verdict (ignore si déjà présent)."""
    connexion_analyses.execute(
        """
        INSERT OR IGNORE INTO verdicts_solo (
            prono_solo_id, vrai, motif_code, motif_texte,
            buts_domicile, buts_exterieur, juge_le
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            prono_solo_id,
            1 if vrai else 0,
            motif_code,
            motif_texte,
            buts_domicile,
            buts_exterieur,
            juge_le,
        ),
    )


def lire_score_match_football(
    connexion_foot: sqlite3.Connection,
    championnat: str,
    saison: str,
    date_match: str,
    domicile: str,
    exterieur: str,
) -> dict | None:
    """Score + cartons/corners si le match est joué dans football.db."""
    try:
        ligne = connexion_foot.execute(
            """
            SELECT buts_domicile, buts_exterieur,
                   jaunes_domicile, jaunes_exterieur,
                   corners_domicile, corners_exterieur
            FROM matchs
            WHERE championnat = ? AND saison = ?
              AND date = ? AND domicile = ? AND exterieur = ?
              AND buts_domicile IS NOT NULL AND buts_exterieur IS NOT NULL
            LIMIT 1
            """,
            (championnat, saison, date_match[:10], domicile, exterieur),
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    if not ligne:
        # Repli sans date exacte (même logique que lire_match_joue).
        try:
            ligne = connexion_foot.execute(
                """
                SELECT buts_domicile, buts_exterieur,
                       jaunes_domicile, jaunes_exterieur,
                       corners_domicile, corners_exterieur
                FROM matchs
                WHERE championnat = ? AND saison = ?
                  AND domicile = ? AND exterieur = ?
                  AND buts_domicile IS NOT NULL AND buts_exterieur IS NOT NULL
                ORDER BY date DESC
                LIMIT 1
                """,
                (championnat, saison, domicile, exterieur),
            ).fetchone()
        except sqlite3.OperationalError:
            return None
    if not ligne:
        return None
    return {
        "buts_domicile": int(ligne["buts_domicile"]),
        "buts_exterieur": int(ligne["buts_exterieur"]),
        "jaunes_domicile": (
            int(ligne["jaunes_domicile"])
            if ligne["jaunes_domicile"] is not None
            else None
        ),
        "jaunes_exterieur": (
            int(ligne["jaunes_exterieur"])
            if ligne["jaunes_exterieur"] is not None
            else None
        ),
        "corners_domicile": (
            int(ligne["corners_domicile"])
            if ligne["corners_domicile"] is not None
            else None
        ),
        "corners_exterieur": (
            int(ligne["corners_exterieur"])
            if ligne["corners_exterieur"] is not None
            else None
        ),
    }
