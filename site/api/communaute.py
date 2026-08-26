"""
Comptes, sessions, commentaires (Phase 1), pronostics (Phase 2),
classement communauté (Phase 3), enrichissements Phase 4,
réponses/réactions et ligues privées (enrichissements communauté).
Base SQLite séparée : donnees/communaute.db
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import os
import re
import secrets
import sqlite3
import threading
import time

import requests
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from passlib.context import CryptContext

RACINE = Path(__file__).resolve().parents[2]
FICHIER_COMMUNAUTE = RACINE / "donnees" / "communaute.db"
FICHIER_FOOTBALL = RACINE / "donnees" / "football.db"

NOM_COOKIE_SESSION = "session_communaute"
DUREE_SESSION_JOURS = 14
LONGUEUR_COMMENTAIRE_MAX = 500
LONGUEUR_PSEUDO_MAX = 30
LONGUEUR_MOT_DE_PASSE_MIN = 8
LIMITE_COMMENTAIRES = 5
FENETRE_COMMENTAIRES_SEC = 600
LIMITE_PRONOSTICS = 15
FENETRE_PRONOSTICS_SEC = 600
LIMITE_REACTIONS = 40
FENETRE_REACTIONS_SEC = 600
LIMITE_LIGUES = 10
FENETRE_LIGUES_SEC = 600
LIMITE_MATCHS_SANS_PRONO = 12
HORIZON_SANS_PRONO_JOURS = 7
SCORE_BUTS_MAX = 15
TYPES_REACTION = ("pouce", "coeur")
LIBELLES_REACTION = {"pouce": "👍", "coeur": "❤️"}
LONGUEUR_NOM_LIGUE_MAX = 40
LONGUEUR_CODE_LIGUE = 8
MOTIF_CODE_LIGUE = re.compile(r"^[A-Z0-9]{6,12}$")

MOTIF_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MOTIF_PSEUDO = re.compile(r"^[A-Za-z0-9_\-\s]{3,30}$")

FUSEAU_PAR_CHAMPIONNAT = {
    "Premier League": "Europe/London",
    "La Liga": "Europe/Madrid",
    "Bundesliga": "Europe/Berlin",
    "Serie A": "Europe/Rome",
    "Ligue 1": "Europe/Paris",
    "Ligue des champions": "Europe/Paris",
}

DISCLAIMER_COMMUNAUTE = (
    "Les commentaires sont des avis d'utilisateurs à titre informatif uniquement. "
    "Ils ne constituent pas un conseil en paris sportifs. Réservé aux 18 ans et plus."
)

DISCLAIMER_PRONOSTICS = (
    "Vos pronostics sont privés et servent uniquement à suivre vos prévisions à titre "
    "informatif. Ils ne constituent pas un conseil en paris sportifs. "
    "Réservé aux 18 ans et plus."
)

DISCLAIMER_CLASSEMENT = (
    "Classement ludique à titre informatif — aucun gain monétaire, lot ou récompense "
    "financière. Les points ne constituent pas un conseil en paris sportifs. "
    "Réservé aux 18 ans et plus."
)

DISCLAIMER_LIGUES = (
    "Ligues privées ludiques entre amis — aucun gain monétaire. "
    "Les points ne constituent pas un conseil en paris sportifs. "
    "Réservé aux 18 ans et plus."
)

REGLE_POINTS = (
    "Score exact : 3 pts · Bon vainqueur (1X2) avec un prono score : 1 pt · "
    "Pronostic 1X2 correct : 1 pt"
)

CHAMPIONNATS_VALIDES = (
    "Premier League",
    "La Liga",
    "Bundesliga",
    "Serie A",
    "Ligue 1",
    "Ligue des champions",
)

POINTS_SCORE_EXACT = 3
POINTS_BON_VAINQUEUR = 1
POINTS_1X2_EXACT = 1

contexte_mots_de_passe = CryptContext(schemes=["bcrypt"], deprecated="auto")
routeur_communaute = APIRouter(prefix="/api/communaute", tags=["communaute"])

_verrou_init = threading.Lock()
_initialise = False
_verrou_limite = threading.Lock()
_historique_commentaires: dict[int, list[float]] = defaultdict(list)
_historique_pronostics: dict[int, list[float]] = defaultdict(list)
_historique_reactions: dict[int, list[float]] = defaultdict(list)
_historique_ligues: dict[int, list[float]] = defaultdict(list)


def charger_fichier_env():
    chemin = RACINE / ".env"
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


def email_admin_communaute():
    charger_fichier_env()
    return (os.environ.get("EMAIL_ADMIN_COMMUNAUTE") or "").strip().lower()


def google_client_id():
    charger_fichier_env()
    return (os.environ.get("GOOGLE_CLIENT_ID") or "").strip()


def ouvrir_base():
    FICHIER_COMMUNAUTE.parent.mkdir(parents=True, exist_ok=True)
    connexion = sqlite3.connect(FICHIER_COMMUNAUTE)
    connexion.row_factory = sqlite3.Row
    return connexion


def initialiser_base():
    global _initialise
    with _verrou_init:
        if _initialise:
            return
        connexion = ouvrir_base()
        try:
            connexion.executescript(
                """
                CREATE TABLE IF NOT EXISTS utilisateurs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    pseudo TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    mot_de_passe_hash TEXT NOT NULL,
                    google_id TEXT,
                    est_admin INTEGER NOT NULL DEFAULT 0,
                    age_confirme INTEGER NOT NULL DEFAULT 0,
                    cgu_acceptees INTEGER NOT NULL DEFAULT 0,
                    cree_le TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_utilisateurs_google_id
                    ON utilisateurs(google_id) WHERE google_id IS NOT NULL;
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    utilisateur_id INTEGER NOT NULL,
                    expire_le TEXT NOT NULL,
                    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
                );
                CREATE TABLE IF NOT EXISTS commentaires (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    utilisateur_id INTEGER NOT NULL,
                    championnat TEXT NOT NULL,
                    saison TEXT NOT NULL,
                    domicile TEXT NOT NULL,
                    exterieur TEXT NOT NULL,
                    contenu TEXT NOT NULL,
                    cree_le TEXT NOT NULL,
                    supprime INTEGER NOT NULL DEFAULT 0,
                    commentaire_parent_id INTEGER,
                    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id),
                    FOREIGN KEY (commentaire_parent_id) REFERENCES commentaires(id)
                );
                CREATE TABLE IF NOT EXISTS signalements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    commentaire_id INTEGER NOT NULL,
                    utilisateur_id INTEGER,
                    motif TEXT,
                    cree_le TEXT NOT NULL,
                    FOREIGN KEY (commentaire_id) REFERENCES commentaires(id),
                    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
                );
                CREATE INDEX IF NOT EXISTS idx_commentaires_match
                    ON commentaires(championnat, saison, domicile, exterieur);
                CREATE INDEX IF NOT EXISTS idx_sessions_utilisateur
                    ON sessions(utilisateur_id);
                CREATE TABLE IF NOT EXISTS pronostics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    utilisateur_id INTEGER NOT NULL,
                    championnat TEXT NOT NULL,
                    saison TEXT NOT NULL,
                    domicile TEXT NOT NULL,
                    exterieur TEXT NOT NULL,
                    type_pronostic TEXT NOT NULL,
                    buts_domicile INTEGER,
                    buts_exterieur INTEGER,
                    resultat_1x2 TEXT,
                    commence_at TEXT NOT NULL,
                    cree_le TEXT NOT NULL,
                    verrouille INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id),
                    UNIQUE(utilisateur_id, championnat, saison, domicile, exterieur)
                );
                CREATE INDEX IF NOT EXISTS idx_pronostics_utilisateur
                    ON pronostics(utilisateur_id, cree_le DESC);
                CREATE TABLE IF NOT EXISTS reactions_commentaires (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    commentaire_id INTEGER NOT NULL,
                    utilisateur_id INTEGER NOT NULL,
                    type_reaction TEXT NOT NULL DEFAULT 'pouce',
                    cree_le TEXT NOT NULL,
                    FOREIGN KEY (commentaire_id) REFERENCES commentaires(id),
                    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id),
                    UNIQUE(commentaire_id, utilisateur_id, type_reaction)
                );
                CREATE INDEX IF NOT EXISTS idx_reactions_commentaire
                    ON reactions_commentaires(commentaire_id);
                CREATE TABLE IF NOT EXISTS ligues_privees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom TEXT NOT NULL,
                    code_invitation TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    createur_id INTEGER NOT NULL,
                    cree_le TEXT NOT NULL,
                    FOREIGN KEY (createur_id) REFERENCES utilisateurs(id)
                );
                CREATE TABLE IF NOT EXISTS membres_ligue (
                    ligue_id INTEGER NOT NULL,
                    utilisateur_id INTEGER NOT NULL,
                    rejoint_le TEXT NOT NULL,
                    PRIMARY KEY (ligue_id, utilisateur_id),
                    FOREIGN KEY (ligue_id) REFERENCES ligues_privees(id),
                    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
                );
                CREATE INDEX IF NOT EXISTS idx_membres_ligue_utilisateur
                    ON membres_ligue(utilisateur_id);
                """
            )
            migrer_schema_communaute(connexion)
            connexion.commit()
        finally:
            connexion.close()
        _initialise = True


def migrer_schema_communaute(connexion):
    """Ajoute colonnes / tables manquantes pour les bases déjà créées."""
    colonnes_com = {
        row[1] for row in connexion.execute("PRAGMA table_info(commentaires)").fetchall()
    }
    if "commentaire_parent_id" not in colonnes_com:
        connexion.execute(
            "ALTER TABLE commentaires ADD COLUMN commentaire_parent_id INTEGER"
        )
    connexion.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_commentaires_parent
        ON commentaires(commentaire_parent_id)
        """
    )

    colonnes_react = {
        row[1]
        for row in connexion.execute("PRAGMA table_info(reactions_commentaires)").fetchall()
    }
    if "type_reaction" not in colonnes_react:
        connexion.executescript(
            """
            CREATE TABLE reactions_commentaires_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                commentaire_id INTEGER NOT NULL,
                utilisateur_id INTEGER NOT NULL,
                type_reaction TEXT NOT NULL DEFAULT 'pouce',
                cree_le TEXT NOT NULL,
                FOREIGN KEY (commentaire_id) REFERENCES commentaires(id),
                FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id),
                UNIQUE(commentaire_id, utilisateur_id, type_reaction)
            );
            INSERT INTO reactions_commentaires_v2 (
                id, commentaire_id, utilisateur_id, type_reaction, cree_le
            )
            SELECT id, commentaire_id, utilisateur_id, 'pouce', cree_le
            FROM reactions_commentaires;
            DROP TABLE reactions_commentaires;
            ALTER TABLE reactions_commentaires_v2 RENAME TO reactions_commentaires;
            CREATE INDEX IF NOT EXISTS idx_reactions_commentaire
                ON reactions_commentaires(commentaire_id);
            """
        )

    connexion.executescript(
        """
        CREATE TABLE IF NOT EXISTS ligues_privees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            code_invitation TEXT NOT NULL UNIQUE COLLATE NOCASE,
            createur_id INTEGER NOT NULL,
            cree_le TEXT NOT NULL,
            FOREIGN KEY (createur_id) REFERENCES utilisateurs(id)
        );
        CREATE TABLE IF NOT EXISTS membres_ligue (
            ligue_id INTEGER NOT NULL,
            utilisateur_id INTEGER NOT NULL,
            rejoint_le TEXT NOT NULL,
            PRIMARY KEY (ligue_id, utilisateur_id),
            FOREIGN KEY (ligue_id) REFERENCES ligues_privees(id),
            FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
        );
        CREATE INDEX IF NOT EXISTS idx_membres_ligue_utilisateur
            ON membres_ligue(utilisateur_id);
        """
    )

    colonnes = {
        row[1]
        for row in connexion.execute("PRAGMA table_info(utilisateurs)").fetchall()
    }
    if "google_id" not in colonnes:
        connexion.execute("ALTER TABLE utilisateurs ADD COLUMN google_id TEXT")
        connexion.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_utilisateurs_google_id
            ON utilisateurs(google_id) WHERE google_id IS NOT NULL
            """
        )


def maintenant_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def valider_email(email: str) -> str:
    texte = (email or "").strip().lower()
    if not texte or len(texte) > 254 or not MOTIF_EMAIL.match(texte):
        raise HTTPException(400, "Adresse e-mail invalide")
    return texte


def valider_pseudo(pseudo: str) -> str:
    texte = (pseudo or "").strip()
    if not MOTIF_PSEUDO.match(texte):
        raise HTTPException(
            400,
            "Pseudo invalide (3 à 30 caractères : lettres, chiffres, espaces, - ou _)",
        )
    return texte


def valider_mot_de_passe(mot_de_passe: str) -> str:
    texte = mot_de_passe or ""
    if len(texte) < LONGUEUR_MOT_DE_PASSE_MIN:
        raise HTTPException(400, f"Mot de passe : minimum {LONGUEUR_MOT_DE_PASSE_MIN} caractères")
    if len(texte) > 128:
        raise HTTPException(400, "Mot de passe trop long")
    return texte


def valider_texte_match(valeur: str, nom: str, taille_max: int = 80) -> str:
    texte = (valeur or "").strip()
    if not texte or len(texte) > taille_max:
        raise HTTPException(400, f"{nom} invalide")
    return texte


def valider_commentaire(contenu: str) -> str:
    texte = (contenu or "").strip()
    if not texte:
        raise HTTPException(400, "Commentaire vide")
    if len(texte) > LONGUEUR_COMMENTAIRE_MAX:
        raise HTTPException(
            400,
            f"Commentaire trop long (max {LONGUEUR_COMMENTAIRE_MAX} caractères)",
        )
    return texte


def utilisateur_public(ligne) -> dict:
    return {
        "id": ligne["id"],
        "pseudo": ligne["pseudo"],
        "est_admin": bool(ligne["est_admin"]),
    }


def creer_session(connexion, utilisateur_id: int) -> str:
    session_id = secrets.token_urlsafe(32)
    expire = datetime.now(timezone.utc) + timedelta(days=DUREE_SESSION_JOURS)
    connexion.execute(
        """
        INSERT INTO sessions (id, utilisateur_id, expire_le)
        VALUES (?, ?, ?)
        """,
        (session_id, utilisateur_id, expire.strftime("%Y-%m-%dT%H:%M:%SZ")),
    )
    return session_id


def poser_cookie_session(reponse: Response, session_id: str):
    reponse.set_cookie(
        key=NOM_COOKIE_SESSION,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=DUREE_SESSION_JOURS * 86400,
        path="/",
    )


def effacer_cookie_session(reponse: Response):
    reponse.delete_cookie(key=NOM_COOKIE_SESSION, path="/")


def session_active(connexion, session_id: str | None):
    if not session_id:
        return None
    ligne = connexion.execute(
        """
        SELECT s.id AS session_id, s.expire_le, u.id, u.email, u.pseudo,
               u.mot_de_passe_hash, u.est_admin, u.age_confirme, u.cgu_acceptees, u.cree_le
        FROM sessions s
        JOIN utilisateurs u ON u.id = s.utilisateur_id
        WHERE s.id = ?
        """,
        (session_id,),
    ).fetchone()
    if not ligne:
        return None
    try:
        expire = datetime.fromisoformat(ligne["expire_le"].replace("Z", "+00:00"))
    except ValueError:
        connexion.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        connexion.commit()
        return None
    if expire <= datetime.now(timezone.utc):
        connexion.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        connexion.commit()
        return None
    return ligne


def utilisateur_connecte(request: Request):
    initialiser_base()
    session_id = request.cookies.get(NOM_COOKIE_SESSION)
    connexion = ouvrir_base()
    try:
        ligne = session_active(connexion, session_id)
        if not ligne:
            raise HTTPException(401, "Connexion requise")
        return ligne, connexion
    except HTTPException:
        connexion.close()
        raise


def verifier_limite_commentaires(utilisateur_id: int):
    maintenant = time.time()
    with _verrou_limite:
        historique = _historique_commentaires[utilisateur_id]
        historique[:] = [
            instant
            for instant in historique
            if maintenant - instant < FENETRE_COMMENTAIRES_SEC
        ]
        if len(historique) >= LIMITE_COMMENTAIRES:
            raise HTTPException(
                429,
                "Trop de commentaires récents. Réessayez dans quelques minutes.",
            )
        historique.append(maintenant)


def verifier_limite_pronostics(utilisateur_id: int):
    maintenant = time.time()
    with _verrou_limite:
        historique = _historique_pronostics[utilisateur_id]
        historique[:] = [
            instant
            for instant in historique
            if maintenant - instant < FENETRE_PRONOSTICS_SEC
        ]
        if len(historique) >= LIMITE_PRONOSTICS:
            raise HTTPException(
                429,
                "Trop de pronostics récents. Réessayez dans quelques minutes.",
            )
        historique.append(maintenant)


def verifier_limite_reactions(utilisateur_id: int):
    maintenant = time.time()
    with _verrou_limite:
        historique = _historique_reactions[utilisateur_id]
        historique[:] = [
            instant
            for instant in historique
            if maintenant - instant < FENETRE_REACTIONS_SEC
        ]
        if len(historique) >= LIMITE_REACTIONS:
            raise HTTPException(
                429,
                "Trop de réactions récentes. Réessayez dans quelques minutes.",
            )
        historique.append(maintenant)


def verifier_limite_ligues(utilisateur_id: int):
    maintenant = time.time()
    with _verrou_limite:
        historique = _historique_ligues[utilisateur_id]
        historique[:] = [
            instant
            for instant in historique
            if maintenant - instant < FENETRE_LIGUES_SEC
        ]
        if len(historique) >= LIMITE_LIGUES:
            raise HTTPException(
                429,
                "Trop d'actions sur les ligues. Réessayez dans quelques minutes.",
            )
        historique.append(maintenant)


def session_optionnelle(request: Request):
    initialiser_base()
    session_id = request.cookies.get(NOM_COOKIE_SESSION)
    if not session_id:
        return None, None
    connexion = ouvrir_base()
    ligne = session_active(connexion, session_id)
    if not ligne:
        connexion.close()
        return None, None
    return ligne, connexion


def valider_type_reaction(type_reaction: str | None) -> str:
    texte = (type_reaction or "pouce").strip().lower()
    if texte not in TYPES_REACTION:
        raise HTTPException(
            400,
            f"Type de réaction invalide ({', '.join(TYPES_REACTION)})",
        )
    return texte


def compter_reactions(connexion, commentaire_ids: list[int]) -> dict[int, dict[str, int]]:
    """Retourne {commentaire_id: {type: nb, ...}}."""
    vide = {t: 0 for t in TYPES_REACTION}
    if not commentaire_ids:
        return {}
    placeholders = ",".join("?" * len(commentaire_ids))
    lignes = connexion.execute(
        f"""
        SELECT commentaire_id, type_reaction, COUNT(*) AS nb
        FROM reactions_commentaires
        WHERE commentaire_id IN ({placeholders})
        GROUP BY commentaire_id, type_reaction
        """,
        commentaire_ids,
    ).fetchall()
    resultat: dict[int, dict[str, int]] = {
        cid: dict(vide) for cid in commentaire_ids
    }
    for row in lignes:
        cid = row["commentaire_id"]
        type_r = row["type_reaction"]
        if type_r in resultat[cid]:
            resultat[cid][type_r] = row["nb"]
    return resultat


def reactions_utilisateur(
    connexion, utilisateur_id: int, commentaire_ids: list[int]
) -> dict[int, set[str]]:
    """Retourne {commentaire_id: {types...}} pour l'utilisateur."""
    if not commentaire_ids or not utilisateur_id:
        return {}
    placeholders = ",".join("?" * len(commentaire_ids))
    lignes = connexion.execute(
        f"""
        SELECT commentaire_id, type_reaction FROM reactions_commentaires
        WHERE utilisateur_id = ? AND commentaire_id IN ({placeholders})
        """,
        [utilisateur_id, *commentaire_ids],
    ).fetchall()
    resultat: dict[int, set[str]] = defaultdict(set)
    for row in lignes:
        resultat[row["commentaire_id"]].add(row["type_reaction"])
    return resultat


def serialiser_commentaire(
    row,
    reactions=None,
    mes_reactions=None,
    reponses=None,
) -> dict:
    reactions = reactions or {t: 0 for t in TYPES_REACTION}
    mes_reactions = list(mes_reactions or [])
    nb_total = sum(reactions.values())
    parent_id = None
    try:
        parent_id = row["commentaire_parent_id"]
    except (KeyError, IndexError, TypeError):
        if isinstance(row, dict):
            parent_id = row.get("commentaire_parent_id")
    return {
        "id": row["id"],
        "pseudo": row["pseudo"],
        "contenu": row["contenu"],
        "cree_le": row["cree_le"],
        "utilisateur_id": row["utilisateur_id"],
        "commentaire_parent_id": parent_id,
        "reactions": reactions,
        "mes_reactions": mes_reactions,
        "nb_reactions": nb_total,
        "utilisateur_a_reagi": bool(mes_reactions),
        "reponses": reponses or [],
    }


def verifier_token_google(id_token: str) -> dict:
    client_id = google_client_id()
    if not client_id:
        raise HTTPException(503, "Connexion Google non configurée sur ce serveur")
    texte = (id_token or "").strip()
    if not texte or len(texte) > 8192:
        raise HTTPException(400, "Jeton Google invalide")
    try:
        reponse = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": texte},
            timeout=10,
        )
    except requests.RequestException as err:
        raise HTTPException(502, "Vérification Google indisponible") from err
    if reponse.status_code != 200:
        raise HTTPException(401, "Jeton Google invalide ou expiré")
    donnees = reponse.json()
    if donnees.get("aud") != client_id:
        raise HTTPException(401, "Jeton Google invalide pour cette application")
    email = (donnees.get("email") or "").strip().lower()
    if not email or donnees.get("email_verified") not in ("true", True, "True", 1):
        raise HTTPException(401, "E-mail Google non vérifié")
    return donnees


def pseudo_depuis_google(donnees: dict) -> str:
    candidats = [
        (donnees.get("name") or "").strip(),
        (donnees.get("given_name") or "").strip(),
        email.split("@")[0] if (email := (donnees.get("email") or "")) else "",
    ]
    for brut in candidats:
        texte = re.sub(r"[^A-Za-z0-9_\-\s]", "", brut).strip()
        if len(texte) >= 3:
            return texte[:LONGUEUR_PSEUDO_MAX]
    return f"Joueur{secrets.token_hex(3)}"


def pseudo_disponible(connexion, pseudo: str) -> str:
    base = valider_pseudo(pseudo)
    if not connexion.execute(
        "SELECT 1 FROM utilisateurs WHERE pseudo = ? COLLATE NOCASE",
        (base,),
    ).fetchone():
        return base
    for suffixe in range(2, 100):
        candidat = f"{base[:LONGUEUR_PSEUDO_MAX - len(str(suffixe)) - 1]}{suffixe}"
        if not connexion.execute(
            "SELECT 1 FROM utilisateurs WHERE pseudo = ? COLLATE NOCASE",
            (candidat,),
        ).fetchone():
            return candidat
    raise HTTPException(409, "Impossible de générer un pseudo unique")


def lister_matchs_sans_prono(utilisateur_id: int) -> list[dict]:
    if not FICHIER_FOOTBALL.exists():
        return []
    maintenant = datetime.now(timezone.utc)
    limite = maintenant + timedelta(days=HORIZON_SANS_PRONO_JOURS)
    connexion_foot = sqlite3.connect(FICHIER_FOOTBALL)
    connexion_foot.row_factory = sqlite3.Row
    connexion_comm = ouvrir_base()
    try:
        pronos_existants = {
            (
                row["championnat"],
                row["saison"],
                row["domicile"],
                row["exterieur"],
            )
            for row in connexion_comm.execute(
                """
                SELECT championnat, saison, domicile, exterieur
                FROM pronostics WHERE utilisateur_id = ?
                """,
                (utilisateur_id,),
            ).fetchall()
        }
        lignes = connexion_foot.execute(
            """
            SELECT c.date, c.heure, c.championnat, c.saison, c.domicile, c.exterieur
            FROM calendrier c
            WHERE c.championnat IN (?, ?, ?, ?, ?, ?)
              AND c.date >= date('now', '-1 day')
            ORDER BY c.date ASC, c.heure ASC
            LIMIT 400
            """,
            CHAMPIONNATS_VALIDES,
        ).fetchall()
        resultat = []
        for ligne in lignes:
            if match_deja_joue(
                ligne["championnat"],
                ligne["saison"],
                ligne["domicile"],
                ligne["exterieur"],
            ):
                continue
            commence_at = commence_at_iso(
                ligne["date"], ligne["heure"], ligne["championnat"]
            )
            instant = parser_instant_iso(commence_at)
            if not instant or instant <= maintenant or instant > limite:
                continue
            cle = (
                ligne["championnat"],
                ligne["saison"],
                ligne["domicile"],
                ligne["exterieur"],
            )
            if cle in pronos_existants:
                continue
            resultat.append(
                {
                    "championnat": ligne["championnat"],
                    "saison": ligne["saison"],
                    "domicile": ligne["domicile"],
                    "exterieur": ligne["exterieur"],
                    "date": ligne["date"],
                    "heure": ligne["heure"],
                    "commence_at": commence_at,
                }
            )
            if len(resultat) >= LIMITE_MATCHS_SANS_PRONO:
                break
        return resultat
    finally:
        connexion_foot.close()
        connexion_comm.close()


def commence_at_iso(date_str, heure_str, championnat=None):
    """Convertit date+heure locales de ligue en instant UTC ISO (Z)."""
    if not date_str or not heure_str:
        return ""
    texte_heure = str(heure_str).strip()
    if len(texte_heure) < 4 or ":" not in texte_heure:
        return ""
    try:
        parties = texte_heure.split(":")
        heures = int(parties[0])
        minutes = int(parties[1][:2])
        annee, mois, jour = (int(x) for x in str(date_str)[:10].split("-"))
        nom_fuseau = FUSEAU_PAR_CHAMPIONNAT.get(championnat) or "Europe/Paris"
        local = datetime(
            annee, mois, jour, heures, minutes, tzinfo=ZoneInfo(nom_fuseau)
        )
        return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError, OSError, ZoneInfoNotFoundError):
        return ""


def parser_instant_iso(texte: str):
    if not texte:
        return None
    try:
        return datetime.fromisoformat(texte.replace("Z", "+00:00"))
    except ValueError:
        return None


def est_verrouille(commence_at: str, maintenant=None) -> bool:
    instant = parser_instant_iso(commence_at)
    if not instant:
        return True
    ref = maintenant or datetime.now(timezone.utc)
    return ref >= instant


def lire_commence_at_match(championnat: str, saison: str, domicile: str, exterieur: str):
    if not FICHIER_FOOTBALL.exists():
        return ""
    connexion = sqlite3.connect(FICHIER_FOOTBALL)
    connexion.row_factory = sqlite3.Row
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
        if not ligne:
            return ""
        return commence_at_iso(ligne["date"], ligne["heure"], championnat)
    finally:
        connexion.close()


def match_deja_joue(championnat: str, saison: str, domicile: str, exterieur: str) -> bool:
    if not FICHIER_FOOTBALL.exists():
        return False
    connexion = sqlite3.connect(FICHIER_FOOTBALL)
    connexion.row_factory = sqlite3.Row
    try:
        ligne = connexion.execute(
            """
            SELECT 1 FROM matchs
            WHERE championnat = ? AND saison = ?
              AND domicile = ? AND exterieur = ?
              AND buts_domicile IS NOT NULL
              AND buts_exterieur IS NOT NULL
            LIMIT 1
            """,
            (championnat, saison, domicile, exterieur),
        ).fetchone()
        return ligne is not None
    finally:
        connexion.close()


def lire_resultat_match(championnat: str, saison: str, domicile: str, exterieur: str):
    if not FICHIER_FOOTBALL.exists():
        return None
    connexion = sqlite3.connect(FICHIER_FOOTBALL)
    connexion.row_factory = sqlite3.Row
    try:
        ligne = connexion.execute(
            """
            SELECT date, buts_domicile, buts_exterieur FROM matchs
            WHERE championnat = ? AND saison = ?
              AND domicile = ? AND exterieur = ?
              AND buts_domicile IS NOT NULL
              AND buts_exterieur IS NOT NULL
            ORDER BY date DESC
            LIMIT 1
            """,
            (championnat, saison, domicile, exterieur),
        ).fetchone()
        if not ligne:
            return None
        return {
            "date": ligne["date"],
            "buts_domicile": int(ligne["buts_domicile"]),
            "buts_exterieur": int(ligne["buts_exterieur"]),
        }
    finally:
        connexion.close()


def resultat_1x2(buts_domicile: int, buts_exterieur: int) -> str:
    if buts_domicile > buts_exterieur:
        return "1"
    if buts_domicile < buts_exterieur:
        return "2"
    return "N"


def calculer_points_pronostic(ligne, resultat):
    """Attribue les points d'un pronostic une fois le match terminé."""
    if not resultat:
        return None
    bd = resultat["buts_domicile"]
    be = resultat["buts_exterieur"]
    reel = resultat_1x2(bd, be)
    if ligne["type_pronostic"] == "score":
        if ligne["buts_domicile"] == bd and ligne["buts_exterieur"] == be:
            return {
                "points": POINTS_SCORE_EXACT,
                "type_reussite": "score_exact",
                "exact": True,
            }
        prono_reel = resultat_1x2(ligne["buts_domicile"], ligne["buts_exterieur"])
        if prono_reel == reel:
            return {
                "points": POINTS_BON_VAINQUEUR,
                "type_reussite": "bon_vainqueur",
                "exact": False,
            }
        return {"points": 0, "type_reussite": "rate", "exact": False}
    exact = ligne["resultat_1x2"] == reel
    return {
        "points": POINTS_1X2_EXACT if exact else 0,
        "type_reussite": "1x2_exact" if exact else "rate",
        "exact": exact,
    }


def evaluer_pronostic(ligne, resultat):
    if not resultat:
        return None
    bd = resultat["buts_domicile"]
    be = resultat["buts_exterieur"]
    points_info = calculer_points_pronostic(ligne, resultat)
    if ligne["type_pronostic"] == "score":
        return {
            "exact": points_info["exact"],
            "score_reel": f"{bd} – {be}",
            "points": points_info["points"],
            "type_reussite": points_info["type_reussite"],
        }
    reel = resultat_1x2(bd, be)
    return {
        "exact": points_info["exact"],
        "resultat_reel": reel,
        "score_reel": f"{bd} – {be}",
        "points": points_info["points"],
        "type_reussite": points_info["type_reussite"],
    }


def attribuer_badges(stats: dict) -> list[str]:
    badges = []
    nb_pronos = stats.get("nb_pronos", 0)
    nb_exacts = stats.get("nb_exacts", 0)
    if nb_pronos >= 10:
        badges.append("10 pronos")
    if nb_pronos >= 25:
        badges.append("25 pronos")
    if nb_exacts >= 1:
        badges.append("Score exact")
    if nb_exacts >= 3:
        badges.append("Sniper")
    return badges


def valider_filtres_classement(championnat: str, saison: str):
    champ = valider_texte_match(championnat, "Championnat")
    if champ not in CHAMPIONNATS_VALIDES:
        raise HTTPException(400, "Championnat inconnu")
    sais = valider_texte_match(saison, "Saison", 16)
    if not re.match(r"^\d{4}-\d{4}$", sais):
        raise HTTPException(400, "Saison invalide")
    return champ, sais


def calculer_classement_pronos(
    championnat: str, saison: str, utilisateur_ids: list[int] | None = None
) -> list[dict]:
    """Calcule le classement à partir des pronostics et des scores réels."""
    initialiser_base()
    connexion = ouvrir_base()
    try:
        if utilisateur_ids is not None:
            if not utilisateur_ids:
                return []
            placeholders = ",".join("?" * len(utilisateur_ids))
            lignes = connexion.execute(
                f"""
                SELECT p.*, u.pseudo, u.id AS utilisateur_id
                FROM pronostics p
                JOIN utilisateurs u ON u.id = p.utilisateur_id
                WHERE p.championnat = ? AND p.saison = ?
                  AND p.utilisateur_id IN ({placeholders})
                """,
                (championnat, saison, *utilisateur_ids),
            ).fetchall()
        else:
            lignes = connexion.execute(
                """
                SELECT p.*, u.pseudo, u.id AS utilisateur_id
                FROM pronostics p
                JOIN utilisateurs u ON u.id = p.utilisateur_id
                WHERE p.championnat = ? AND p.saison = ?
                """,
                (championnat, saison),
            ).fetchall()
    finally:
        connexion.close()

    stats: dict[int, dict] = {}
    for prono in lignes:
        uid = prono["utilisateur_id"]
        if uid not in stats:
            stats[uid] = {
                "utilisateur_id": uid,
                "pseudo": prono["pseudo"],
                "points": 0,
                "nb_pronos": 0,
                "nb_evalues": 0,
                "nb_exacts": 0,
                "nb_bons_vainqueurs": 0,
            }
        entree = stats[uid]
        entree["nb_pronos"] += 1
        resultat = lire_resultat_match(
            prono["championnat"],
            prono["saison"],
            prono["domicile"],
            prono["exterieur"],
        )
        if not resultat:
            continue
        entree["nb_evalues"] += 1
        points_info = calculer_points_pronostic(prono, resultat)
        entree["points"] += points_info["points"]
        if points_info["type_reussite"] == "score_exact":
            entree["nb_exacts"] += 1
        elif points_info["type_reussite"] in ("bon_vainqueur", "1x2_exact"):
            entree["nb_bons_vainqueurs"] += 1

    # Membres sans prono n'apparaissent pas tant qu'ils n'ont pas de prono

    classement = sorted(
        stats.values(),
        key=lambda x: (
            -x["points"],
            -x["nb_exacts"],
            -x["nb_bons_vainqueurs"],
            -x["nb_pronos"],
            x["pseudo"].lower(),
        ),
    )
    for rang, entree in enumerate(classement, start=1):
        entree["rang"] = rang
        entree["badges"] = attribuer_badges(entree)
    return classement


def generer_code_ligue(connexion) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    for _ in range(40):
        code = "".join(secrets.choice(alphabet) for _ in range(LONGUEUR_CODE_LIGUE))
        if not connexion.execute(
            "SELECT 1 FROM ligues_privees WHERE code_invitation = ? COLLATE NOCASE",
            (code,),
        ).fetchone():
            return code
    raise HTTPException(500, "Impossible de générer un code d'invitation")


def valider_nom_ligue(nom: str) -> str:
    texte = (nom or "").strip()
    if len(texte) < 3 or len(texte) > LONGUEUR_NOM_LIGUE_MAX:
        raise HTTPException(
            400,
            f"Nom de ligue invalide (3 à {LONGUEUR_NOM_LIGUE_MAX} caractères)",
        )
    return texte


def valider_code_invitation(code: str) -> str:
    texte = (code or "").strip().upper()
    if not MOTIF_CODE_LIGUE.match(texte):
        raise HTTPException(400, "Code d'invitation invalide")
    return texte


def lire_ligue_par_code(connexion, code: str):
    return connexion.execute(
        """
        SELECT l.*, u.pseudo AS createur_pseudo
        FROM ligues_privees l
        JOIN utilisateurs u ON u.id = l.createur_id
        WHERE l.code_invitation = ? COLLATE NOCASE
        """,
        (code,),
    ).fetchone()


def ids_membres_ligue(connexion, ligue_id: int) -> list[int]:
    return [
        row["utilisateur_id"]
        for row in connexion.execute(
            "SELECT utilisateur_id FROM membres_ligue WHERE ligue_id = ?",
            (ligue_id,),
        ).fetchall()
    ]


def serialiser_ligue(ligne, nb_membres: int = 0, est_membre: bool = False) -> dict:
    return {
        "id": ligne["id"],
        "nom": ligne["nom"],
        "code_invitation": ligne["code_invitation"],
        "createur_id": ligne["createur_id"],
        "createur_pseudo": ligne["createur_pseudo"]
        if "createur_pseudo" in ligne.keys()
        else None,
        "cree_le": ligne["cree_le"],
        "nb_membres": nb_membres,
        "est_membre": est_membre,
    }


def lister_matchs_journee(championnat: str, saison: str, journee: str) -> list[dict]:
    if not FICHIER_FOOTBALL.exists():
        return []
    connexion = sqlite3.connect(FICHIER_FOOTBALL)
    connexion.row_factory = sqlite3.Row
    try:
        lignes = connexion.execute(
            """
            SELECT date, heure, journee, championnat, saison, domicile, exterieur
            FROM calendrier
            WHERE championnat = ? AND saison = ? AND journee = ?
            ORDER BY date ASC, heure ASC
            """,
            (championnat, saison, journee),
        ).fetchall()
        resultat = []
        for ligne in lignes:
            commence_at = commence_at_iso(
                ligne["date"], ligne["heure"], ligne["championnat"]
            )
            resultat.append(
                {
                    "championnat": ligne["championnat"],
                    "saison": ligne["saison"],
                    "domicile": ligne["domicile"],
                    "exterieur": ligne["exterieur"],
                    "date": ligne["date"],
                    "heure": ligne["heure"],
                    "journee": str(ligne["journee"]),
                    "commence_at": commence_at,
                    "verrouille": est_verrouille(commence_at) if commence_at else True,
                    "match_deja_joue": match_deja_joue(
                        ligne["championnat"],
                        ligne["saison"],
                        ligne["domicile"],
                        ligne["exterieur"],
                    ),
                }
            )
        return resultat
    finally:
        connexion.close()


def lister_journees_disponibles(championnat: str, saison: str) -> list[str]:
    if not FICHIER_FOOTBALL.exists():
        return []
    connexion = sqlite3.connect(FICHIER_FOOTBALL)
    try:
        lignes = connexion.execute(
            """
            SELECT DISTINCT journee FROM calendrier
            WHERE championnat = ? AND saison = ?
              AND journee IS NOT NULL AND TRIM(journee) != ''
            ORDER BY CAST(journee AS INTEGER) ASC, journee ASC
            """,
            (championnat, saison),
        ).fetchall()
        return [str(row[0]) for row in lignes]
    finally:
        connexion.close()


def profil_public_stats(pseudo: str) -> dict | None:
    initialiser_base()
    connexion = ouvrir_base()
    try:
        utilisateur = connexion.execute(
            "SELECT id, pseudo FROM utilisateurs WHERE pseudo = ? COLLATE NOCASE",
            (pseudo.strip(),),
        ).fetchone()
        if not utilisateur:
            return None
        lignes = connexion.execute(
            """
            SELECT p.*, u.pseudo
            FROM pronostics p
            JOIN utilisateurs u ON u.id = p.utilisateur_id
            WHERE p.utilisateur_id = ?
            ORDER BY p.commence_at DESC
            """,
            (utilisateur["id"],),
        ).fetchall()
    finally:
        connexion.close()

    if not lignes:
        return {
            "pseudo": utilisateur["pseudo"],
            "points_total": 0,
            "nb_pronos": 0,
            "nb_evalues": 0,
            "nb_exacts": 0,
            "nb_bons_vainqueurs": 0,
            "par_championnat": [],
            "badges": [],
        }

    points_total = 0
    nb_evalues = 0
    nb_exacts = 0
    nb_bons_vainqueurs = 0
    par_champ: dict[tuple[str, str], dict] = {}

    for prono in lignes:
        cle = (prono["championnat"], prono["saison"])
        if cle not in par_champ:
            par_champ[cle] = {
                "championnat": prono["championnat"],
                "saison": prono["saison"],
                "points": 0,
                "nb_pronos": 0,
                "nb_evalues": 0,
            }
        par_champ[cle]["nb_pronos"] += 1
        resultat = lire_resultat_match(
            prono["championnat"],
            prono["saison"],
            prono["domicile"],
            prono["exterieur"],
        )
        if not resultat:
            continue
        nb_evalues += 1
        par_champ[cle]["nb_evalues"] += 1
        points_info = calculer_points_pronostic(prono, resultat)
        points_total += points_info["points"]
        par_champ[cle]["points"] += points_info["points"]
        if points_info["type_reussite"] == "score_exact":
            nb_exacts += 1
        elif points_info["type_reussite"] in ("bon_vainqueur", "1x2_exact"):
            nb_bons_vainqueurs += 1

    stats = {
        "pseudo": utilisateur["pseudo"],
        "points_total": points_total,
        "nb_pronos": len(lignes),
        "nb_evalues": nb_evalues,
        "nb_exacts": nb_exacts,
        "nb_bons_vainqueurs": nb_bons_vainqueurs,
        "par_championnat": sorted(
            par_champ.values(),
            key=lambda x: (-x["points"], x["championnat"]),
        ),
    }
    stats["badges"] = attribuer_badges(stats)
    return stats


def serialiser_pronostic(ligne, maintenant=None):
    verrouille = est_verrouille(ligne["commence_at"], maintenant)
    if verrouille and not ligne["verrouille"]:
        verrouille = True
    data = {
        "id": ligne["id"],
        "championnat": ligne["championnat"],
        "saison": ligne["saison"],
        "domicile": ligne["domicile"],
        "exterieur": ligne["exterieur"],
        "type_pronostic": ligne["type_pronostic"],
        "buts_domicile": ligne["buts_domicile"],
        "buts_exterieur": ligne["buts_exterieur"],
        "resultat_1x2": ligne["resultat_1x2"],
        "commence_at": ligne["commence_at"],
        "cree_le": ligne["cree_le"],
        "verrouille": verrouille,
    }
    if ligne["type_pronostic"] == "score":
        data["libelle"] = f"{ligne['buts_domicile']} – {ligne['buts_exterieur']}"
    else:
        libelles = {"1": "Victoire domicile", "N": "Match nul", "2": "Victoire extérieur"}
        data["libelle"] = libelles.get(ligne["resultat_1x2"], ligne["resultat_1x2"])
    resultat = lire_resultat_match(
        ligne["championnat"],
        ligne["saison"],
        ligne["domicile"],
        ligne["exterieur"],
    )
    if resultat:
        data["resultat_match"] = resultat
        data["evaluation"] = evaluer_pronostic(ligne, resultat)
    return data


def valider_pronostic(donnees: "PronosticBody"):
    champ = valider_texte_match(donnees.championnat, "Championnat")
    sais = valider_texte_match(donnees.saison, "Saison", 16)
    dom = valider_texte_match(donnees.domicile, "Domicile")
    ext = valider_texte_match(donnees.exterieur, "Extérieur")
    if dom == ext:
        raise HTTPException(400, "Les deux équipes doivent être différentes")
    type_prono = (donnees.type_pronostic or "").strip().lower()
    if type_prono not in ("score", "1x2"):
        raise HTTPException(400, "Type de pronostic invalide (score ou 1x2)")
    buts_d = None
    buts_e = None
    resultat_1x2 = None
    if type_prono == "score":
        if donnees.buts_domicile is None or donnees.buts_exterieur is None:
            raise HTTPException(400, "Score domicile et extérieur requis")
        buts_d = int(donnees.buts_domicile)
        buts_e = int(donnees.buts_exterieur)
        if buts_d < 0 or buts_e < 0 or buts_d > SCORE_BUTS_MAX or buts_e > SCORE_BUTS_MAX:
            raise HTTPException(400, f"Score invalide (0 à {SCORE_BUTS_MAX} buts)")
    else:
        resultat_1x2 = (donnees.resultat_1x2 or "").strip().upper()
        if resultat_1x2 not in ("1", "N", "2"):
            raise HTTPException(400, "Résultat 1X2 invalide (1, N ou 2)")
    return champ, sais, dom, ext, type_prono, buts_d, buts_e, resultat_1x2


class InscriptionBody(BaseModel):
    email: str
    pseudo: str
    mot_de_passe: str
    age_18_plus: bool = False
    cgu_acceptees: bool = False


class ConnexionBody(BaseModel):
    """identifiant = pseudo ou e-mail. Le champ email reste accepté (compatibilité)."""

    identifiant: str = ""
    email: str = ""
    mot_de_passe: str


class CommentaireBody(BaseModel):
    championnat: str
    saison: str
    domicile: str
    exterieur: str
    contenu: str = Field(max_length=LONGUEUR_COMMENTAIRE_MAX)
    commentaire_parent_id: int | None = None


class SignalementBody(BaseModel):
    motif: str = Field(default="", max_length=200)


class ReactionBody(BaseModel):
    type_reaction: str = "pouce"


class PronosticBody(BaseModel):
    championnat: str
    saison: str
    domicile: str
    exterieur: str
    type_pronostic: str
    buts_domicile: int | None = None
    buts_exterieur: int | None = None
    resultat_1x2: str | None = None


class GoogleConnexionBody(BaseModel):
    id_token: str = Field(max_length=8192)


class LigueCreerBody(BaseModel):
    nom: str = Field(max_length=LONGUEUR_NOM_LIGUE_MAX)


class LigueRejoindreBody(BaseModel):
    code_invitation: str = Field(max_length=12)


@routeur_communaute.get("/config")
def lire_config_communaute():
    client_id = google_client_id()
    return {
        "oauth_google_actif": bool(client_id),
        "google_client_id": client_id,
        "disclaimer": DISCLAIMER_COMMUNAUTE,
    }


@routeur_communaute.post("/connexion/google")
def connexion_google(donnees: GoogleConnexionBody, response: Response):
    initialiser_base()
    infos = verifier_token_google(donnees.id_token)
    email = valider_email(infos.get("email", ""))
    google_id = (infos.get("sub") or "").strip()
    if not google_id:
        raise HTTPException(401, "Identifiant Google manquant")

    connexion = ouvrir_base()
    try:
        ligne = connexion.execute(
            "SELECT * FROM utilisateurs WHERE email = ? OR google_id = ?",
            (email, google_id),
        ).fetchone()
        if ligne:
            if not ligne["google_id"]:
                connexion.execute(
                    "UPDATE utilisateurs SET google_id = ? WHERE id = ?",
                    (google_id, ligne["id"]),
                )
            utilisateur_id = ligne["id"]
        else:
            pseudo = pseudo_disponible(connexion, pseudo_depuis_google(infos))
            hash_mdp = contexte_mots_de_passe.hash(secrets.token_urlsafe(32))
            est_admin = 1 if email == email_admin_communaute() else 0
            curseur = connexion.execute(
                """
                INSERT INTO utilisateurs (
                    email, pseudo, mot_de_passe_hash, google_id,
                    est_admin, age_confirme, cgu_acceptees, cree_le
                ) VALUES (?, ?, ?, ?, ?, 1, 1, ?)
                """,
                (email, pseudo, hash_mdp, google_id, est_admin, maintenant_iso()),
            )
            utilisateur_id = curseur.lastrowid
            ligne = connexion.execute(
                "SELECT * FROM utilisateurs WHERE id = ?",
                (utilisateur_id,),
            ).fetchone()

        session_id = creer_session(connexion, utilisateur_id)
        connexion.commit()
        poser_cookie_session(response, session_id)
        return {"utilisateur": utilisateur_public(ligne)}
    except sqlite3.IntegrityError as err:
        raise HTTPException(409, "Compte Google déjà associé à un autre profil") from err
    finally:
        connexion.close()


@routeur_communaute.get("/disclaimer")
def lire_disclaimer():
    return {"texte": DISCLAIMER_COMMUNAUTE}


@routeur_communaute.post("/inscription")
def inscription(donnees: InscriptionBody, response: Response):
    initialiser_base()
    email = valider_email(donnees.email)
    pseudo = valider_pseudo(donnees.pseudo)
    mot_de_passe = valider_mot_de_passe(donnees.mot_de_passe)
    if not donnees.age_18_plus:
        raise HTTPException(400, "Vous devez confirmer avoir 18 ans ou plus")
    if not donnees.cgu_acceptees:
        raise HTTPException(400, "Vous devez accepter les conditions d'utilisation")

    hash_mdp = contexte_mots_de_passe.hash(mot_de_passe)
    est_admin = 1 if email == email_admin_communaute() else 0
    connexion = ouvrir_base()
    try:
        try:
            curseur = connexion.execute(
                """
                INSERT INTO utilisateurs (
                    email, pseudo, mot_de_passe_hash,
                    est_admin, age_confirme, cgu_acceptees, cree_le
                ) VALUES (?, ?, ?, ?, 1, 1, ?)
                """,
                (email, pseudo, hash_mdp, est_admin, maintenant_iso()),
            )
        except sqlite3.IntegrityError as err:
            message = str(err).lower()
            if "email" in message:
                raise HTTPException(409, "Cet e-mail est déjà utilisé") from err
            raise HTTPException(409, "Ce pseudo est déjà pris") from err
        utilisateur_id = curseur.lastrowid
        session_id = creer_session(connexion, utilisateur_id)
        connexion.commit()
        poser_cookie_session(response, session_id)
        ligne = connexion.execute(
            "SELECT * FROM utilisateurs WHERE id = ?",
            (utilisateur_id,),
        ).fetchone()
        return {"utilisateur": utilisateur_public(ligne)}
    finally:
        connexion.close()


def trouver_utilisateur_par_identifiant(connexion_db, identifiant: str):
    """Cherche par e-mail si l'identifiant contient @, sinon par pseudo."""
    texte = (identifiant or "").strip()
    if not texte:
        return None
    if "@" in texte:
        email = valider_email(texte)
        return connexion_db.execute(
            "SELECT * FROM utilisateurs WHERE email = ?",
            (email,),
        ).fetchone()
    return connexion_db.execute(
        "SELECT * FROM utilisateurs WHERE pseudo = ? COLLATE NOCASE",
        (texte,),
    ).fetchone()


@routeur_communaute.post("/connexion")
def connexion(donnees: ConnexionBody, response: Response):
    initialiser_base()
    identifiant = (donnees.identifiant or donnees.email or "").strip()
    if not identifiant:
        raise HTTPException(400, "Pseudo ou e-mail requis")
    mot_de_passe = valider_mot_de_passe(donnees.mot_de_passe)
    message_echec = "Identifiant ou mot de passe incorrect"
    connexion_db = ouvrir_base()
    try:
        ligne = trouver_utilisateur_par_identifiant(connexion_db, identifiant)
        if not ligne or not contexte_mots_de_passe.verify(
            mot_de_passe, ligne["mot_de_passe_hash"]
        ):
            raise HTTPException(401, message_echec)
        session_id = creer_session(connexion_db, ligne["id"])
        connexion_db.commit()
        poser_cookie_session(response, session_id)
        return {"utilisateur": utilisateur_public(ligne)}
    finally:
        connexion_db.close()


@routeur_communaute.post("/deconnexion")
def deconnexion(request: Request, response: Response):
    initialiser_base()
    session_id = request.cookies.get(NOM_COOKIE_SESSION)
    if session_id:
        connexion = ouvrir_base()
        try:
            connexion.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            connexion.commit()
        finally:
            connexion.close()
    effacer_cookie_session(response)
    return {"ok": True}


@routeur_communaute.get("/moi")
def moi(request: Request):
    initialiser_base()
    session_id = request.cookies.get(NOM_COOKIE_SESSION)
    connexion = ouvrir_base()
    try:
        ligne = session_active(connexion, session_id)
        if not ligne:
            raise HTTPException(401, "Non connecté")
        return {"utilisateur": utilisateur_public(ligne)}
    finally:
        connexion.close()


@routeur_communaute.get("/commentaires")
def lister_commentaires(
    request: Request,
    championnat: str,
    saison: str,
    domicile: str,
    exterieur: str,
):
    initialiser_base()
    champ = valider_texte_match(championnat, "Championnat")
    sais = valider_texte_match(saison, "Saison", 16)
    dom = valider_texte_match(domicile, "Domicile")
    ext = valider_texte_match(exterieur, "Extérieur")
    utilisateur, connexion_session = session_optionnelle(request)
    connexion = connexion_session or ouvrir_base()
    fermer_apres = connexion_session is None
    try:
        lignes = connexion.execute(
            """
            SELECT c.id, c.contenu, c.cree_le, c.commentaire_parent_id,
                   u.pseudo, u.id AS utilisateur_id
            FROM commentaires c
            JOIN utilisateurs u ON u.id = c.utilisateur_id
            WHERE c.supprime = 0
              AND c.championnat = ?
              AND c.saison = ?
              AND c.domicile = ?
              AND c.exterieur = ?
            ORDER BY c.cree_le ASC
            """,
            (champ, sais, dom, ext),
        ).fetchall()
        ids = [row["id"] for row in lignes]
        compteurs = compter_reactions(connexion, ids)
        mes_reactions = reactions_utilisateur(
            connexion, utilisateur["id"] if utilisateur else 0, ids
        )
        par_id = {}
        for row in lignes:
            par_id[row["id"]] = serialiser_commentaire(
                row,
                reactions=compteurs.get(row["id"], {t: 0 for t in TYPES_REACTION}),
                mes_reactions=sorted(mes_reactions.get(row["id"], set())),
                reponses=[],
            )
        racines = []
        for row in lignes:
            item = par_id[row["id"]]
            parent_id = row["commentaire_parent_id"]
            if parent_id and parent_id in par_id:
                par_id[parent_id]["reponses"].append(item)
            else:
                racines.append(item)
        return {
            "commentaires": racines,
            "types_reaction": list(TYPES_REACTION),
            "disclaimer": DISCLAIMER_COMMUNAUTE,
        }
    finally:
        if fermer_apres:
            connexion.close()
        elif connexion_session:
            connexion_session.close()


@routeur_communaute.post("/commentaires")
def publier_commentaire(donnees: CommentaireBody, request: Request):
    utilisateur, connexion = utilisateur_connecte(request)
    verifier_limite_commentaires(utilisateur["id"])
    champ = valider_texte_match(donnees.championnat, "Championnat")
    sais = valider_texte_match(donnees.saison, "Saison", 16)
    dom = valider_texte_match(donnees.domicile, "Domicile")
    ext = valider_texte_match(donnees.exterieur, "Extérieur")
    contenu = valider_commentaire(donnees.contenu)
    parent_id = donnees.commentaire_parent_id
    try:
        if parent_id is not None:
            if parent_id < 1:
                raise HTTPException(400, "Commentaire parent invalide")
            parent = connexion.execute(
                """
                SELECT id, commentaire_parent_id, championnat, saison, domicile, exterieur
                FROM commentaires
                WHERE id = ? AND supprime = 0
                """,
                (parent_id,),
            ).fetchone()
            if not parent:
                raise HTTPException(404, "Commentaire parent introuvable")
            if parent["commentaire_parent_id"] is not None:
                raise HTTPException(
                    400, "Impossible de répondre à une réponse (un seul niveau)"
                )
            if (
                parent["championnat"] != champ
                or parent["saison"] != sais
                or parent["domicile"] != dom
                or parent["exterieur"] != ext
            ):
                raise HTTPException(400, "Le parent ne correspond pas à ce match")
        curseur = connexion.execute(
            """
            INSERT INTO commentaires (
                utilisateur_id, championnat, saison, domicile, exterieur,
                contenu, cree_le, commentaire_parent_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                utilisateur["id"],
                champ,
                sais,
                dom,
                ext,
                contenu,
                maintenant_iso(),
                parent_id,
            ),
        )
        connexion.commit()
        return {
            "commentaire": serialiser_commentaire(
                {
                    "id": curseur.lastrowid,
                    "pseudo": utilisateur["pseudo"],
                    "contenu": contenu,
                    "cree_le": maintenant_iso(),
                    "utilisateur_id": utilisateur["id"],
                    "commentaire_parent_id": parent_id,
                },
            )
        }
    finally:
        connexion.close()


@routeur_communaute.get("/commentaires/{commentaire_id}/reactions")
def lire_reactions_commentaire(commentaire_id: int, request: Request):
    initialiser_base()
    if commentaire_id < 1:
        raise HTTPException(400, "Identifiant de commentaire invalide")
    utilisateur, connexion_session = session_optionnelle(request)
    connexion = connexion_session or ouvrir_base()
    fermer_apres = connexion_session is None
    try:
        commentaire = connexion.execute(
            "SELECT id FROM commentaires WHERE id = ? AND supprime = 0",
            (commentaire_id,),
        ).fetchone()
        if not commentaire:
            raise HTTPException(404, "Commentaire introuvable")
        compteurs = compter_reactions(connexion, [commentaire_id])
        mes = reactions_utilisateur(
            connexion, utilisateur["id"] if utilisateur else 0, [commentaire_id]
        )
        reactions = compteurs.get(commentaire_id, {t: 0 for t in TYPES_REACTION})
        mes_liste = sorted(mes.get(commentaire_id, set()))
        return {
            "commentaire_id": commentaire_id,
            "reactions": reactions,
            "mes_reactions": mes_liste,
            "nb_reactions": sum(reactions.values()),
            "utilisateur_a_reagi": bool(mes_liste),
            "types_reaction": list(TYPES_REACTION),
        }
    finally:
        if fermer_apres:
            connexion.close()
        elif connexion_session:
            connexion_session.close()


@routeur_communaute.post("/commentaires/{commentaire_id}/reactions")
def basculer_reaction_commentaire(
    commentaire_id: int,
    request: Request,
    donnees: ReactionBody | None = None,
):
    if commentaire_id < 1:
        raise HTTPException(400, "Identifiant de commentaire invalide")
    utilisateur, connexion = utilisateur_connecte(request)
    verifier_limite_reactions(utilisateur["id"])
    type_reaction = valider_type_reaction(
        donnees.type_reaction if donnees else "pouce"
    )
    try:
        commentaire = connexion.execute(
            "SELECT id FROM commentaires WHERE id = ? AND supprime = 0",
            (commentaire_id,),
        ).fetchone()
        if not commentaire:
            raise HTTPException(404, "Commentaire introuvable")
        existante = connexion.execute(
            """
            SELECT id FROM reactions_commentaires
            WHERE commentaire_id = ? AND utilisateur_id = ? AND type_reaction = ?
            """,
            (commentaire_id, utilisateur["id"], type_reaction),
        ).fetchone()
        if existante:
            connexion.execute(
                "DELETE FROM reactions_commentaires WHERE id = ?",
                (existante["id"],),
            )
        else:
            connexion.execute(
                """
                INSERT INTO reactions_commentaires (
                    commentaire_id, utilisateur_id, type_reaction, cree_le
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    commentaire_id,
                    utilisateur["id"],
                    type_reaction,
                    maintenant_iso(),
                ),
            )
        connexion.commit()
        compteurs = compter_reactions(connexion, [commentaire_id])
        mes = reactions_utilisateur(connexion, utilisateur["id"], [commentaire_id])
        reactions = compteurs.get(commentaire_id, {t: 0 for t in TYPES_REACTION})
        mes_liste = sorted(mes.get(commentaire_id, set()))
        return {
            "commentaire_id": commentaire_id,
            "type_reaction": type_reaction,
            "reactions": reactions,
            "mes_reactions": mes_liste,
            "nb_reactions": sum(reactions.values()),
            "utilisateur_a_reagi": bool(mes_liste),
        }
    finally:
        connexion.close()


@routeur_communaute.post("/commentaires/{commentaire_id}/signaler")
def signaler_commentaire(
    commentaire_id: int,
    donnees: SignalementBody,
    request: Request,
):
    utilisateur, connexion = utilisateur_connecte(request)
    motif = (donnees.motif or "").strip()[:200]
    try:
        commentaire = connexion.execute(
            "SELECT id FROM commentaires WHERE id = ? AND supprime = 0",
            (commentaire_id,),
        ).fetchone()
        if not commentaire:
            raise HTTPException(404, "Commentaire introuvable")
        connexion.execute(
            """
            INSERT INTO signalements (commentaire_id, utilisateur_id, motif, cree_le)
            VALUES (?, ?, ?, ?)
            """,
            (commentaire_id, utilisateur["id"], motif, maintenant_iso()),
        )
        connexion.commit()
        return {"ok": True, "message": "Signalement enregistré"}
    finally:
        connexion.close()


@routeur_communaute.delete("/commentaires/{commentaire_id}")
def supprimer_commentaire(commentaire_id: int, request: Request):
    utilisateur, connexion = utilisateur_connecte(request)
    if not utilisateur["est_admin"]:
        raise HTTPException(403, "Action réservée aux administrateurs")
    try:
        curseur = connexion.execute(
            """
            UPDATE commentaires SET supprime = 1
            WHERE id = ? AND supprime = 0
            """,
            (commentaire_id,),
        )
        if curseur.rowcount == 0:
            raise HTTPException(404, "Commentaire introuvable")
        connexion.commit()
        return {"ok": True}
    finally:
        connexion.close()


@routeur_communaute.get("/pronostics/sans-prono")
def lister_matchs_a_pronostiquer(request: Request):
    utilisateur, connexion = utilisateur_connecte(request)
    try:
        matchs = lister_matchs_sans_prono(utilisateur["id"])
        return {
            "matchs": matchs,
            "nb": len(matchs),
            "horizon_jours": HORIZON_SANS_PRONO_JOURS,
            "disclaimer": DISCLAIMER_PRONOSTICS,
        }
    finally:
        connexion.close()


@routeur_communaute.get("/pronostics/disclaimer")
def lire_disclaimer_pronostics():
    return {"texte": DISCLAIMER_PRONOSTICS}


@routeur_communaute.get("/pronostics/mes-pronos")
def lister_mes_pronostics(request: Request):
    utilisateur, connexion = utilisateur_connecte(request)
    try:
        lignes = connexion.execute(
            """
            SELECT * FROM pronostics
            WHERE utilisateur_id = ?
            ORDER BY commence_at DESC, cree_le DESC
            """,
            (utilisateur["id"],),
        ).fetchall()
        return {
            "pronostics": [serialiser_pronostic(row) for row in lignes],
            "disclaimer": DISCLAIMER_PRONOSTICS,
        }
    finally:
        connexion.close()


@routeur_communaute.get("/pronostics")
def lire_pronostic_match(
    request: Request,
    championnat: str,
    saison: str,
    domicile: str,
    exterieur: str,
):
    utilisateur, connexion = utilisateur_connecte(request)
    champ = valider_texte_match(championnat, "Championnat")
    sais = valider_texte_match(saison, "Saison", 16)
    dom = valider_texte_match(domicile, "Domicile")
    ext = valider_texte_match(exterieur, "Extérieur")
    try:
        ligne = connexion.execute(
            """
            SELECT * FROM pronostics
            WHERE utilisateur_id = ?
              AND championnat = ? AND saison = ?
              AND domicile = ? AND exterieur = ?
            """,
            (utilisateur["id"], champ, sais, dom, ext),
        ).fetchone()
        return {
            "pronostic": serialiser_pronostic(ligne) if ligne else None,
            "disclaimer": DISCLAIMER_PRONOSTICS,
            "match_deja_joue": match_deja_joue(champ, sais, dom, ext),
            "commence_at": lire_commence_at_match(champ, sais, dom, ext),
        }
    finally:
        connexion.close()


@routeur_communaute.post("/pronostics")
def deposer_pronostic(donnees: PronosticBody, request: Request):
    utilisateur, connexion = utilisateur_connecte(request)
    verifier_limite_pronostics(utilisateur["id"])
    champ, sais, dom, ext, type_prono, buts_d, buts_e, resultat_1x2 = valider_pronostic(
        donnees
    )
    if match_deja_joue(champ, sais, dom, ext):
        raise HTTPException(409, "Le match est déjà terminé")
    commence_at = lire_commence_at_match(champ, sais, dom, ext)
    if not commence_at:
        raise HTTPException(400, "Horaire du match introuvable — pronostic impossible")
    if est_verrouille(commence_at):
        raise HTTPException(409, "Le coup d'envoi est passé — pronostic verrouillé")
    try:
        existant = connexion.execute(
            """
            SELECT id, commence_at, verrouille FROM pronostics
            WHERE utilisateur_id = ?
              AND championnat = ? AND saison = ?
              AND domicile = ? AND exterieur = ?
            """,
            (utilisateur["id"], champ, sais, dom, ext),
        ).fetchone()
        if existant:
            if est_verrouille(existant["commence_at"]) or existant["verrouille"]:
                raise HTTPException(409, "Pronostic verrouillé — modification impossible")
            connexion.execute(
                """
                UPDATE pronostics SET
                    type_pronostic = ?,
                    buts_domicile = ?,
                    buts_exterieur = ?,
                    resultat_1x2 = ?,
                    commence_at = ?,
                    cree_le = ?,
                    verrouille = 0
                WHERE id = ?
                """,
                (
                    type_prono,
                    buts_d,
                    buts_e,
                    resultat_1x2,
                    commence_at,
                    maintenant_iso(),
                    existant["id"],
                ),
            )
            pronostic_id = existant["id"]
        else:
            curseur = connexion.execute(
                """
                INSERT INTO pronostics (
                    utilisateur_id, championnat, saison, domicile, exterieur,
                    type_pronostic, buts_domicile, buts_exterieur, resultat_1x2,
                    commence_at, cree_le, verrouille
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    utilisateur["id"],
                    champ,
                    sais,
                    dom,
                    ext,
                    type_prono,
                    buts_d,
                    buts_e,
                    resultat_1x2,
                    commence_at,
                    maintenant_iso(),
                ),
            )
            pronostic_id = curseur.lastrowid
        connexion.commit()
        ligne = connexion.execute(
            "SELECT * FROM pronostics WHERE id = ?",
            (pronostic_id,),
        ).fetchone()
        return {"pronostic": serialiser_pronostic(ligne)}
    except sqlite3.IntegrityError as err:
        raise HTTPException(409, "Un pronostic existe déjà pour ce match") from err
    finally:
        connexion.close()


@routeur_communaute.get("/classement")
def lire_classement_pronos(championnat: str, saison: str):
    champ, sais = valider_filtres_classement(championnat, saison)
    classement = calculer_classement_pronos(champ, sais)
    return {
        "championnat": champ,
        "saison": sais,
        "classement": classement,
        "regle_points": REGLE_POINTS,
        "disclaimer": DISCLAIMER_CLASSEMENT,
    }


@routeur_communaute.get("/profil/{pseudo}")
def lire_profil_public(pseudo: str):
    pseudo_valide = valider_pseudo(pseudo)
    profil = profil_public_stats(pseudo_valide)
    if not profil:
        raise HTTPException(404, "Utilisateur introuvable")
    return {
        "profil": profil,
        "regle_points": REGLE_POINTS,
        "disclaimer": DISCLAIMER_CLASSEMENT,
    }


@routeur_communaute.get("/pronostics/journees")
def lister_journees_pronos(championnat: str, saison: str):
    champ, sais = valider_filtres_classement(championnat, saison)
    journees = lister_journees_disponibles(champ, sais)
    return {
        "championnat": champ,
        "saison": sais,
        "journees": journees,
        "disclaimer": DISCLAIMER_PRONOSTICS,
    }


@routeur_communaute.get("/pronostics/journee")
def lire_pronos_journee(
    request: Request,
    championnat: str,
    saison: str,
    journee: str,
):
    champ, sais = valider_filtres_classement(championnat, saison)
    jour = valider_texte_match(journee, "Journée", 16)
    utilisateur, connexion = utilisateur_connecte(request)
    try:
        matchs = lister_matchs_journee(champ, sais, jour)
        for match in matchs:
            ligne = connexion.execute(
                """
                SELECT * FROM pronostics
                WHERE utilisateur_id = ?
                  AND championnat = ? AND saison = ?
                  AND domicile = ? AND exterieur = ?
                """,
                (
                    utilisateur["id"],
                    match["championnat"],
                    match["saison"],
                    match["domicile"],
                    match["exterieur"],
                ),
            ).fetchone()
            match["pronostic"] = serialiser_pronostic(ligne) if ligne else None
        return {
            "championnat": champ,
            "saison": sais,
            "journee": jour,
            "matchs": matchs,
            "nb": len(matchs),
            "regle_points": REGLE_POINTS,
            "disclaimer": DISCLAIMER_PRONOSTICS,
        }
    finally:
        connexion.close()


@routeur_communaute.get("/ligues")
def lister_mes_ligues(request: Request):
    utilisateur, connexion = utilisateur_connecte(request)
    try:
        lignes = connexion.execute(
            """
            SELECT l.*, u.pseudo AS createur_pseudo,
                   (SELECT COUNT(*) FROM membres_ligue m WHERE m.ligue_id = l.id) AS nb_membres
            FROM ligues_privees l
            JOIN membres_ligue ml ON ml.ligue_id = l.id
            JOIN utilisateurs u ON u.id = l.createur_id
            WHERE ml.utilisateur_id = ?
            ORDER BY l.cree_le DESC
            """,
            (utilisateur["id"],),
        ).fetchall()
        return {
            "ligues": [
                serialiser_ligue(row, nb_membres=row["nb_membres"], est_membre=True)
                for row in lignes
            ],
            "disclaimer": DISCLAIMER_LIGUES,
            "regle_points": REGLE_POINTS,
        }
    finally:
        connexion.close()


@routeur_communaute.post("/ligues")
def creer_ligue(donnees: LigueCreerBody, request: Request):
    utilisateur, connexion = utilisateur_connecte(request)
    verifier_limite_ligues(utilisateur["id"])
    nom = valider_nom_ligue(donnees.nom)
    try:
        code = generer_code_ligue(connexion)
        curseur = connexion.execute(
            """
            INSERT INTO ligues_privees (nom, code_invitation, createur_id, cree_le)
            VALUES (?, ?, ?, ?)
            """,
            (nom, code, utilisateur["id"], maintenant_iso()),
        )
        ligue_id = curseur.lastrowid
        connexion.execute(
            """
            INSERT INTO membres_ligue (ligue_id, utilisateur_id, rejoint_le)
            VALUES (?, ?, ?)
            """,
            (ligue_id, utilisateur["id"], maintenant_iso()),
        )
        connexion.commit()
        ligne = lire_ligue_par_code(connexion, code)
        return {
            "ligue": serialiser_ligue(ligne, nb_membres=1, est_membre=True),
            "disclaimer": DISCLAIMER_LIGUES,
        }
    finally:
        connexion.close()


@routeur_communaute.post("/ligues/rejoindre")
def rejoindre_ligue(donnees: LigueRejoindreBody, request: Request):
    utilisateur, connexion = utilisateur_connecte(request)
    verifier_limite_ligues(utilisateur["id"])
    code = valider_code_invitation(donnees.code_invitation)
    try:
        ligne = lire_ligue_par_code(connexion, code)
        if not ligne:
            raise HTTPException(404, "Ligue introuvable")
        deja = connexion.execute(
            """
            SELECT 1 FROM membres_ligue
            WHERE ligue_id = ? AND utilisateur_id = ?
            """,
            (ligne["id"], utilisateur["id"]),
        ).fetchone()
        if not deja:
            connexion.execute(
                """
                INSERT INTO membres_ligue (ligue_id, utilisateur_id, rejoint_le)
                VALUES (?, ?, ?)
                """,
                (ligne["id"], utilisateur["id"], maintenant_iso()),
            )
            connexion.commit()
        nb = connexion.execute(
            "SELECT COUNT(*) AS n FROM membres_ligue WHERE ligue_id = ?",
            (ligne["id"],),
        ).fetchone()["n"]
        return {
            "ligue": serialiser_ligue(ligne, nb_membres=nb, est_membre=True),
            "disclaimer": DISCLAIMER_LIGUES,
        }
    finally:
        connexion.close()


@routeur_communaute.get("/ligues/{code}")
def lire_ligue(code: str, request: Request):
    utilisateur, connexion = utilisateur_connecte(request)
    code_valide = valider_code_invitation(code)
    try:
        ligne = lire_ligue_par_code(connexion, code_valide)
        if not ligne:
            raise HTTPException(404, "Ligue introuvable")
        membres = connexion.execute(
            """
            SELECT u.id, u.pseudo, m.rejoint_le
            FROM membres_ligue m
            JOIN utilisateurs u ON u.id = m.utilisateur_id
            WHERE m.ligue_id = ?
            ORDER BY m.rejoint_le ASC
            """,
            (ligne["id"],),
        ).fetchall()
        est_membre = any(m["id"] == utilisateur["id"] for m in membres)
        if not est_membre:
            raise HTTPException(403, "Vous n'êtes pas membre de cette ligue")
        return {
            "ligue": serialiser_ligue(
                ligne, nb_membres=len(membres), est_membre=True
            ),
            "membres": [
                {
                    "utilisateur_id": m["id"],
                    "pseudo": m["pseudo"],
                    "rejoint_le": m["rejoint_le"],
                }
                for m in membres
            ],
            "disclaimer": DISCLAIMER_LIGUES,
            "regle_points": REGLE_POINTS,
        }
    finally:
        connexion.close()


@routeur_communaute.get("/ligues/{code}/classement")
def classement_ligue(code: str, request: Request, championnat: str, saison: str):
    utilisateur, connexion = utilisateur_connecte(request)
    code_valide = valider_code_invitation(code)
    champ, sais = valider_filtres_classement(championnat, saison)
    try:
        ligne = lire_ligue_par_code(connexion, code_valide)
        if not ligne:
            raise HTTPException(404, "Ligue introuvable")
        ids = ids_membres_ligue(connexion, ligne["id"])
        if utilisateur["id"] not in ids:
            raise HTTPException(403, "Vous n'êtes pas membre de cette ligue")
        classement = calculer_classement_pronos(champ, sais, utilisateur_ids=ids)
        return {
            "ligue": serialiser_ligue(
                ligne, nb_membres=len(ids), est_membre=True
            ),
            "championnat": champ,
            "saison": sais,
            "classement": classement,
            "regle_points": REGLE_POINTS,
            "disclaimer": DISCLAIMER_LIGUES,
        }
    finally:
        connexion.close()
