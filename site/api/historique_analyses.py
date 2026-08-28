"""
Historique systematique des analyses de match (MVP Phase 1).

Base separee donnees/analyses.db — survit aux rebuilds de football.db.
Ne pas confondre avec communaute.db (social uniquement).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sqlite3
import threading

from calibration import calculer_metriques_match, score_exact_ok

RACINE = Path(__file__).resolve().parents[2]
FICHIER_ANALYSES = RACINE / "donnees" / "analyses.db"
FICHIER_CODE_MODELE = Path(__file__).resolve().parent / "analyse_rencontre.py"
NOM_MODELE_DEFAUT = "poisson-xg-elo-v2"
NOM_MODELE_CALIBRE = "poisson-xg-elo-cal-v3"


def nom_modele_actuel() -> str:
    """Version du modele : v3 si calibrateur actif, sinon v2."""
    try:
        from calibrateur import calibrateur_actif

        if calibrateur_actif():
            return NOM_MODELE_CALIBRE
    except ImportError:
        pass
    return NOM_MODELE_DEFAUT

_verrou_schema = threading.Lock()
_schema_pret = False


def cle_match(championnat: str, saison: str, date_match: str, domicile: str, exterieur: str) -> str:
    """Cle stable et lisible pour un match (sans collision sur les champs usuels)."""
    parties = [
        (championnat or "").strip().lower(),
        (saison or "").strip(),
        (date_match or "").strip()[:10],
        (domicile or "").strip().lower(),
        (exterieur or "").strip().lower(),
    ]
    return "|".join(parties)


def hash_code_modele(chemin: Path | None = None) -> str:
    """Empreinte du fichier moteur pour versionner les previsions."""
    cible = chemin or FICHIER_CODE_MODELE
    if not cible.is_file():
        return "inconnu"
    return hashlib.sha256(cible.read_bytes()).hexdigest()[:16]


def _maintenant_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ouvrir_base(chemin: Path | None = None) -> sqlite3.Connection:
    """Ouvre analyses.db et cree le schema si besoin."""
    global _schema_pret
    fichier = Path(chemin) if chemin else FICHIER_ANALYSES
    fichier.parent.mkdir(parents=True, exist_ok=True)
    connexion = sqlite3.connect(str(fichier), timeout=30)
    connexion.row_factory = sqlite3.Row
    connexion.execute("PRAGMA foreign_keys = ON")
    with _verrou_schema:
        if chemin or not _schema_pret:
            assurer_schema(connexion)
            if not chemin:
                _schema_pret = True
    return connexion


def assurer_schema(connexion: sqlite3.Connection) -> None:
    """Cree les tables d'historique si elles n'existent pas."""
    connexion.executescript(
        """
        CREATE TABLE IF NOT EXISTS versions_modele (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            hash_code TEXT NOT NULL,
            cree_le TEXT NOT NULL,
            UNIQUE (nom, hash_code)
        );

        CREATE TABLE IF NOT EXISTS previsions_match (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cle_match TEXT NOT NULL UNIQUE,
            championnat TEXT NOT NULL,
            saison TEXT NOT NULL,
            date_match TEXT NOT NULL,
            domicile TEXT NOT NULL,
            exterieur TEXT NOT NULL,
            version_modele_id INTEGER NOT NULL,
            genere_le TEXT NOT NULL,
            xg_prevu_domicile REAL,
            xg_prevu_exterieur REAL,
            p_victoire_domicile REAL,
            p_nul REAL,
            p_victoire_exterieur REAL,
            score_plus_probable TEXT,
            p_les_deux_marquent REAL,
            p_plus_de_2_buts REAL,
            jaunes_domicile REAL,
            jaunes_exterieur REAL,
            payload_json TEXT NOT NULL,
            FOREIGN KEY (version_modele_id) REFERENCES versions_modele(id)
        );

        CREATE TABLE IF NOT EXISTS resultats_analyse (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prevision_id INTEGER NOT NULL UNIQUE,
            match_joue_le TEXT NOT NULL,
            buts_domicile INTEGER,
            buts_exterieur INTEGER,
            xg_reel_domicile REAL,
            xg_reel_exterieur REAL,
            jaunes_domicile INTEGER,
            jaunes_exterieur INTEGER,
            issue_reelle TEXT,
            score_exact_ok INTEGER,
            bilan_json TEXT NOT NULL,
            FOREIGN KEY (prevision_id) REFERENCES previsions_match(id)
        );

        CREATE INDEX IF NOT EXISTS idx_previsions_saison
            ON previsions_match (saison, championnat, date_match);

        CREATE TABLE IF NOT EXISTS analyses_ia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cle_match TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            contenu_json TEXT NOT NULL,
            genere_le TEXT NOT NULL
        );
        """
    )
    _migrer_colonnes_resultats(connexion)
    _migrer_colonnes_previsions(connexion)
    connexion.commit()


def _migrer_colonnes_previsions(connexion: sqlite3.Connection) -> None:
    """Ajoute retroactif si absent (backfill matchs deja joues)."""
    existantes = {
        row[1]
        for row in connexion.execute("PRAGMA table_info(previsions_match)")
    }
    if "retroactif" not in existantes:
        connexion.execute(
            "ALTER TABLE previsions_match ADD COLUMN retroactif INTEGER NOT NULL DEFAULT 0"
        )


def _migrer_colonnes_resultats(connexion: sqlite3.Connection) -> None:
    """Ajoute les colonnes de calibration Phase 2 si absentes."""
    colonnes = {
        "brier_score": "REAL",
        "log_loss": "REAL",
        "mae_xg": "REAL",
        "issue_1x2_ok": "INTEGER",
        "btts_ok": "INTEGER",
        "o25_ok": "INTEGER",
    }
    existantes = {
        row[1]
        for row in connexion.execute("PRAGMA table_info(resultats_analyse)")
    }
    for nom, type_col in colonnes.items():
        if nom not in existantes:
            connexion.execute(
                f"ALTER TABLE resultats_analyse ADD COLUMN {nom} {type_col}"
            )


def obtenir_ou_creer_version_modele(
    connexion: sqlite3.Connection,
    nom: str | None = None,
    hash_code: str | None = None,
) -> int:
    """Retourne l'id de version du modele courant (cree si besoin)."""
    nom_effectif = nom or nom_modele_actuel()
    empreinte = hash_code or hash_code_modele()
    ligne = connexion.execute(
        """
        SELECT id FROM versions_modele
        WHERE nom = ? AND hash_code = ?
        """,
        (nom_effectif, empreinte),
    ).fetchone()
    if ligne:
        return int(ligne["id"])
    curseur = connexion.execute(
        """
        INSERT INTO versions_modele (nom, hash_code, cree_le)
        VALUES (?, ?, ?)
        """,
        (nom_effectif, empreinte, _maintenant_iso()),
    )
    connexion.commit()
    return int(curseur.lastrowid)


def _extraire_champs_pred(prediction: dict) -> dict:
    cartons = prediction.get("cartons") or {}
    return {
        "xg_prevu_domicile": prediction.get("xg_prevu_domicile"),
        "xg_prevu_exterieur": prediction.get("xg_prevu_exterieur"),
        "p_victoire_domicile": prediction.get("p_victoire_domicile"),
        "p_nul": prediction.get("p_nul"),
        "p_victoire_exterieur": prediction.get("p_victoire_exterieur"),
        "score_plus_probable": prediction.get("score_plus_probable"),
        "p_les_deux_marquent": prediction.get("p_les_deux_marquent"),
        "p_plus_de_2_buts": prediction.get("p_plus_de_2_buts"),
        "jaunes_domicile": cartons.get("jaunes_domicile"),
        "jaunes_exterieur": cartons.get("jaunes_exterieur"),
    }


def enregistrer_prevision(
    connexion: sqlite3.Connection,
    championnat: str,
    saison: str,
    date_match: str,
    domicile: str,
    exterieur: str,
    prediction: dict,
    version_modele_id: int | None = None,
    payload_complet: dict | None = None,
    retroactif: bool = False,
) -> int | None:
    """
    Enregistre une prevision si la cle_match n'existe pas encore.
    Retourne l'id (existant ou cree), ou None si prediction vide.
    """
    if not prediction:
        return None
    cle = cle_match(championnat, saison, date_match, domicile, exterieur)
    existante = connexion.execute(
        "SELECT id FROM previsions_match WHERE cle_match = ?",
        (cle,),
    ).fetchone()
    if existante:
        return int(existante["id"])

    version_id = version_modele_id or obtenir_ou_creer_version_modele(connexion)
    champs = _extraire_champs_pred(prediction)
    payload = payload_complet if payload_complet is not None else prediction
    curseur = connexion.execute(
        """
        INSERT INTO previsions_match (
            cle_match, championnat, saison, date_match, domicile, exterieur,
            version_modele_id, genere_le,
            xg_prevu_domicile, xg_prevu_exterieur,
            p_victoire_domicile, p_nul, p_victoire_exterieur,
            score_plus_probable, p_les_deux_marquent, p_plus_de_2_buts,
            jaunes_domicile, jaunes_exterieur, payload_json, retroactif
        ) VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?
        )
        """,
        (
            cle,
            championnat,
            saison,
            (date_match or "")[:10],
            domicile,
            exterieur,
            version_id,
            _maintenant_iso(),
            champs["xg_prevu_domicile"],
            champs["xg_prevu_exterieur"],
            champs["p_victoire_domicile"],
            champs["p_nul"],
            champs["p_victoire_exterieur"],
            champs["score_plus_probable"],
            champs["p_les_deux_marquent"],
            champs["p_plus_de_2_buts"],
            champs["jaunes_domicile"],
            champs["jaunes_exterieur"],
            json.dumps(payload, ensure_ascii=False),
            1 if retroactif else 0,
        ),
    )
    connexion.commit()
    return int(curseur.lastrowid)


def lire_prevision_figee(
    connexion: sqlite3.Connection,
    championnat: str,
    saison: str,
    date_match: str,
    domicile: str,
    exterieur: str,
) -> dict | None:
    """Lit une prevision figees + meta version (sans le resultat)."""
    cle = cle_match(championnat, saison, date_match, domicile, exterieur)
    return lire_prevision_par_cle(connexion, cle)


def lire_prevision_par_cle(connexion: sqlite3.Connection, cle: str) -> dict | None:
    ligne = connexion.execute(
        """
        SELECT p.*, v.nom AS version_nom, v.hash_code AS version_hash
        FROM previsions_match p
        JOIN versions_modele v ON v.id = p.version_modele_id
        WHERE p.cle_match = ?
        """,
        (cle,),
    ).fetchone()
    if not ligne:
        return None
    return _ligne_prevision_vers_dict(ligne)


def lire_prevision_sans_date(
    connexion: sqlite3.Connection,
    championnat: str,
    saison: str,
    domicile: str,
    exterieur: str,
) -> dict | None:
    """Fallback si la date exacte n'est pas connue (dernier enregistrement)."""
    ligne = connexion.execute(
        """
        SELECT p.*, v.nom AS version_nom, v.hash_code AS version_hash
        FROM previsions_match p
        JOIN versions_modele v ON v.id = p.version_modele_id
        WHERE p.championnat = ? AND p.saison = ?
          AND lower(p.domicile) = lower(?) AND lower(p.exterieur) = lower(?)
        ORDER BY p.date_match DESC, p.id DESC
        LIMIT 1
        """,
        (championnat, saison, domicile, exterieur),
    ).fetchone()
    if not ligne:
        return None
    return _ligne_prevision_vers_dict(ligne)


def _ligne_prevision_vers_dict(ligne: sqlite3.Row) -> dict:
    try:
        payload = json.loads(ligne["payload_json"] or "{}")
    except json.JSONDecodeError:
        payload = {}
    cles = ligne.keys()
    version = {
        "id": int(ligne["version_modele_id"]),
        "nom": ligne["version_nom"] if "version_nom" in cles else NOM_MODELE_DEFAUT,
        "hash_code": ligne["version_hash"] if "version_hash" in cles else "",
    }
    return {
        "id": int(ligne["id"]),
        "cle_match": ligne["cle_match"],
        "championnat": ligne["championnat"],
        "saison": ligne["saison"],
        "date_match": ligne["date_match"],
        "domicile": ligne["domicile"],
        "exterieur": ligne["exterieur"],
        "genere_le": ligne["genere_le"],
        "version_modele": version,
        "xg_prevu_domicile": ligne["xg_prevu_domicile"],
        "xg_prevu_exterieur": ligne["xg_prevu_exterieur"],
        "p_victoire_domicile": ligne["p_victoire_domicile"],
        "p_nul": ligne["p_nul"],
        "p_victoire_exterieur": ligne["p_victoire_exterieur"],
        "score_plus_probable": ligne["score_plus_probable"],
        "p_les_deux_marquent": ligne["p_les_deux_marquent"],
        "p_plus_de_2_buts": ligne["p_plus_de_2_buts"],
        "jaunes_domicile": ligne["jaunes_domicile"],
        "jaunes_exterieur": ligne["jaunes_exterieur"],
        "prediction": payload,
        "retroactif": bool(ligne["retroactif"]) if "retroactif" in cles else False,
    }


def prevision_existe(connexion: sqlite3.Connection, cle: str) -> bool:
    ligne = connexion.execute(
        "SELECT 1 FROM previsions_match WHERE cle_match = ? LIMIT 1",
        (cle,),
    ).fetchone()
    return ligne is not None


def resultat_existe_pour_prevision(connexion: sqlite3.Connection, prevision_id: int) -> bool:
    ligne = connexion.execute(
        "SELECT 1 FROM resultats_analyse WHERE prevision_id = ? LIMIT 1",
        (prevision_id,),
    ).fetchone()
    return ligne is not None


def issue_depuis_buts(buts_domicile: int, buts_exterieur: int) -> str:
    if buts_domicile > buts_exterieur:
        return "1"
    if buts_domicile < buts_exterieur:
        return "2"
    return "N"


def enregistrer_resultat(
    connexion: sqlite3.Connection,
    prevision_id: int,
    match_joue: dict,
    bilan: dict,
) -> int | None:
    """
    Enregistre le resultat compare a une prevision figee.
    Ignore si deja present (idempotent).
    """
    if resultat_existe_pour_prevision(connexion, prevision_id):
        ligne = connexion.execute(
            "SELECT id FROM resultats_analyse WHERE prevision_id = ?",
            (prevision_id,),
        ).fetchone()
        return int(ligne["id"]) if ligne else None

    buts_d = int(match_joue["buts_domicile"])
    buts_e = int(match_joue["buts_exterieur"])
    pred_ligne = connexion.execute(
        """
        SELECT score_plus_probable, xg_prevu_domicile, xg_prevu_exterieur,
               p_victoire_domicile, p_nul, p_victoire_exterieur,
               p_les_deux_marquent, p_plus_de_2_buts
        FROM previsions_match WHERE id = ?
        """,
        (prevision_id,),
    ).fetchone()
    champs_prevision = dict(pred_ligne) if pred_ligne else {}
    issue_reelle = issue_depuis_buts(buts_d, buts_e)
    match_pour_metriques = {
        **match_joue,
        "buts_domicile": buts_d,
        "buts_exterieur": buts_e,
        "issue_reelle": issue_reelle,
        "xg_reel_domicile": match_joue.get("xg_domicile"),
        "xg_reel_exterieur": match_joue.get("xg_exterieur"),
    }
    metriques = calculer_metriques_match(champs_prevision, match_pour_metriques)
    date_joue = (match_joue.get("date") or "")[:10]

    def _bool_int(val: bool | None) -> int | None:
        if val is None:
            return None
        return 1 if val else 0

    curseur = connexion.execute(
        """
        INSERT INTO resultats_analyse (
            prevision_id, match_joue_le,
            buts_domicile, buts_exterieur,
            xg_reel_domicile, xg_reel_exterieur,
            jaunes_domicile, jaunes_exterieur,
            issue_reelle, score_exact_ok, bilan_json,
            brier_score, log_loss, mae_xg,
            issue_1x2_ok, btts_ok, o25_ok
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            prevision_id,
            date_joue,
            buts_d,
            buts_e,
            match_joue.get("xg_domicile"),
            match_joue.get("xg_exterieur"),
            match_joue.get("jaunes_domicile"),
            match_joue.get("jaunes_exterieur"),
            issue_reelle,
            1 if metriques["score_exact_ok"] else 0,
            json.dumps(bilan, ensure_ascii=False),
            metriques.get("brier_score"),
            metriques.get("log_loss"),
            metriques.get("mae_xg"),
            _bool_int(metriques.get("issue_1x2_ok")),
            _bool_int(metriques.get("btts_ok")),
            _bool_int(metriques.get("o25_ok")),
        ),
    )
    connexion.commit()
    return int(curseur.lastrowid)


def lire_resultat(connexion: sqlite3.Connection, prevision_id: int) -> dict | None:
    ligne = connexion.execute(
        "SELECT * FROM resultats_analyse WHERE prevision_id = ?",
        (prevision_id,),
    ).fetchone()
    if not ligne:
        return None
    try:
        bilan = json.loads(ligne["bilan_json"] or "{}")
    except json.JSONDecodeError:
        bilan = {}
    cles = ligne.keys()
    return {
        "id": int(ligne["id"]),
        "prevision_id": int(ligne["prevision_id"]),
        "match_joue_le": ligne["match_joue_le"],
        "buts_domicile": ligne["buts_domicile"],
        "buts_exterieur": ligne["buts_exterieur"],
        "xg_reel_domicile": ligne["xg_reel_domicile"],
        "xg_reel_exterieur": ligne["xg_reel_exterieur"],
        "jaunes_domicile": ligne["jaunes_domicile"],
        "jaunes_exterieur": ligne["jaunes_exterieur"],
        "issue_reelle": ligne["issue_reelle"],
        "score_exact_ok": bool(ligne["score_exact_ok"]),
        "brier_score": ligne["brier_score"] if "brier_score" in cles else None,
        "log_loss": ligne["log_loss"] if "log_loss" in cles else None,
        "mae_xg": ligne["mae_xg"] if "mae_xg" in cles else None,
        "issue_1x2_ok": bool(ligne["issue_1x2_ok"]) if ligne["issue_1x2_ok"] is not None else None,
        "btts_ok": bool(ligne["btts_ok"]) if ligne["btts_ok"] is not None else None,
        "o25_ok": bool(ligne["o25_ok"]) if ligne["o25_ok"] is not None else None,
        "bilan": bilan,
    }


def lister_resultats_avec_previsions(
    connexion: sqlite3.Connection,
    saison: str,
    championnat: str | None = None,
    inclure_retroactif: bool = False,
) -> list[dict]:
    """Liste les resultats enregistres avec metriques et meta prevision.

    Par defaut, exclut les previsions retroactif=1 (backfill historique).
    """
    sql = """
        SELECT
            r.id AS resultat_id,
            r.prevision_id,
            r.match_joue_le,
            r.buts_domicile,
            r.buts_exterieur,
            r.xg_reel_domicile,
            r.xg_reel_exterieur,
            r.issue_reelle,
            r.score_exact_ok,
            r.brier_score,
            r.log_loss,
            r.mae_xg,
            r.issue_1x2_ok,
            r.btts_ok,
            r.o25_ok,
            p.championnat,
            p.saison,
            p.date_match,
            p.domicile,
            p.exterieur,
            p.xg_prevu_domicile,
            p.xg_prevu_exterieur,
            p.p_victoire_domicile,
            p.p_nul,
            p.p_victoire_exterieur,
            p.score_plus_probable,
            v.nom AS version_nom
        FROM resultats_analyse r
        JOIN previsions_match p ON p.id = r.prevision_id
        JOIN versions_modele v ON v.id = p.version_modele_id
        WHERE p.saison = ?
    """
    params: list = [saison]
    if not inclure_retroactif:
        sql += " AND COALESCE(p.retroactif, 0) = 0"
    if championnat:
        sql += " AND p.championnat = ?"
        params.append(championnat)
    sql += " ORDER BY r.match_joue_le, p.championnat, p.domicile"

    lignes = connexion.execute(sql, params).fetchall()
    resultats = []
    for ligne in lignes:
        cles = ligne.keys()
        resultats.append(
            {
                "championnat": ligne["championnat"],
                "saison": ligne["saison"],
                "date_match": ligne["date_match"],
                "domicile": ligne["domicile"],
                "exterieur": ligne["exterieur"],
                "match_joue_le": ligne["match_joue_le"],
                "version_modele": ligne["version_nom"],
                "score_exact_ok": bool(ligne["score_exact_ok"]),
                "issue_1x2_ok": bool(ligne["issue_1x2_ok"])
                if ligne["issue_1x2_ok"] is not None
                else None,
                "btts_ok": bool(ligne["btts_ok"]) if ligne["btts_ok"] is not None else None,
                "o25_ok": bool(ligne["o25_ok"]) if ligne["o25_ok"] is not None else None,
                "brier_score": ligne["brier_score"],
                "log_loss": ligne["log_loss"],
                "mae_xg": ligne["mae_xg"],
                "issue_reelle": ligne["issue_reelle"],
                "buts_domicile": ligne["buts_domicile"],
                "buts_exterieur": ligne["buts_exterieur"],
                "score_plus_probable": ligne["score_plus_probable"],
            }
        )
    return resultats


def pred_depuis_prevision_figee(prevision: dict) -> dict:
    """Reconstruit un dict prediction utilisable par _bilan_match / comparaison."""
    payload = dict(prevision.get("prediction") or {})
    # Garantir les champs structures meme si payload partiel.
    for cle in (
        "xg_prevu_domicile",
        "xg_prevu_exterieur",
        "p_victoire_domicile",
        "p_nul",
        "p_victoire_exterieur",
        "score_plus_probable",
        "p_les_deux_marquent",
        "p_plus_de_2_buts",
    ):
        if cle not in payload and prevision.get(cle) is not None:
            payload[cle] = prevision[cle]
    if "cartons" not in payload:
        payload["cartons"] = {
            "jaunes_domicile": prevision.get("jaunes_domicile"),
            "jaunes_exterieur": prevision.get("jaunes_exterieur"),
        }
    return payload
