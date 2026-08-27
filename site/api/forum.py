"""
Forum communautaire type Telegram — un espace public par championnat.
Sujets + messages chronologiques. Auth cookie partagée avec communaute.py.
Base : donnees/communaute.db (tables forums_*).
"""

from collections import defaultdict
import threading
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from avatars import lire_avatar_id_ligne
from communaute import (
    CHAMPIONNATS_VALIDES,
    TYPES_REACTION,
    initialiser_base,
    maintenant_iso,
    ouvrir_base,
    session_optionnelle,
    utilisateur_connecte,
    valider_type_reaction,
)

LONGUEUR_TITRE_MAX = 120
LONGUEUR_MESSAGE_MAX = 1000
LONGUEUR_MOTIF_MAX = 200
LONGUEUR_QUESTION_SONDAGE_MAX = 160
LONGUEUR_OPTION_SONDAGE_MAX = 80
LONGUEUR_EXTRAIT_PARENT = 80
NB_OPTIONS_SONDAGE_MIN = 2
NB_OPTIONS_SONDAGE_MAX = 6
LIMITE_FORUM = 8
FENETRE_FORUM_SEC = 600
LIMITE_REACTIONS_FORUM = 40
FENETRE_REACTIONS_FORUM_SEC = 600
LIMITE_SONDAGES_FORUM = 10
FENETRE_SONDAGES_FORUM_SEC = 600

DISCLAIMER_FORUM = (
    "Forum communautaire à titre informatif uniquement. "
    "Les messages sont des avis d'utilisateurs et ne constituent pas un conseil "
    "en paris sportifs. Réservé aux 18 ans et plus."
)

routeur_forum = APIRouter(prefix="/api/forum", tags=["forum"])

_verrou_init = threading.Lock()
_tables_ok = False
_verrou_limite = threading.Lock()
_historique_forum: dict[int, list[float]] = defaultdict(list)
_historique_reactions_forum: dict[int, list[float]] = defaultdict(list)
_historique_sondages_forum: dict[int, list[float]] = defaultdict(list)


def assurer_tables_forum():
    """Crée les tables forum si besoin (idempotent, sans toucher au reste)."""
    global _tables_ok
    initialiser_base()
    with _verrou_init:
        if _tables_ok:
            return
        connexion = ouvrir_base()
        try:
            connexion.executescript(
                """
                CREATE TABLE IF NOT EXISTS forums_sujets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    championnat TEXT NOT NULL,
                    titre TEXT NOT NULL,
                    auteur_id INTEGER NOT NULL,
                    cree_le TEXT NOT NULL,
                    dernier_message_le TEXT NOT NULL,
                    nb_messages INTEGER NOT NULL DEFAULT 0,
                    date_modification TEXT,
                    supprime INTEGER NOT NULL DEFAULT 0,
                    supprime_le TEXT,
                    FOREIGN KEY (auteur_id) REFERENCES utilisateurs(id)
                );
                CREATE INDEX IF NOT EXISTS idx_forums_sujets_champ
                    ON forums_sujets(championnat, dernier_message_le DESC);
                CREATE TABLE IF NOT EXISTS forums_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sujet_id INTEGER NOT NULL,
                    auteur_id INTEGER NOT NULL,
                    contenu TEXT NOT NULL,
                    cree_le TEXT NOT NULL,
                    date_modification TEXT,
                    message_parent_id INTEGER,
                    supprime INTEGER NOT NULL DEFAULT 0,
                    supprime_le TEXT,
                    FOREIGN KEY (sujet_id) REFERENCES forums_sujets(id),
                    FOREIGN KEY (auteur_id) REFERENCES utilisateurs(id),
                    FOREIGN KEY (message_parent_id) REFERENCES forums_messages(id)
                );
                CREATE INDEX IF NOT EXISTS idx_forums_messages_sujet
                    ON forums_messages(sujet_id, cree_le ASC);
                CREATE TABLE IF NOT EXISTS forums_signalements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    utilisateur_id INTEGER,
                    motif TEXT,
                    cree_le TEXT NOT NULL,
                    FOREIGN KEY (message_id) REFERENCES forums_messages(id),
                    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
                );
                CREATE TABLE IF NOT EXISTS forums_reactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    utilisateur_id INTEGER NOT NULL,
                    type_reaction TEXT NOT NULL DEFAULT 'pouce',
                    cree_le TEXT NOT NULL,
                    FOREIGN KEY (message_id) REFERENCES forums_messages(id),
                    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id),
                    UNIQUE(message_id, utilisateur_id, type_reaction)
                );
                CREATE INDEX IF NOT EXISTS idx_forums_reactions_message
                    ON forums_reactions(message_id);
                CREATE TABLE IF NOT EXISTS forums_sondages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sujet_id INTEGER NOT NULL,
                    auteur_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    cree_le TEXT NOT NULL,
                    supprime INTEGER NOT NULL DEFAULT 0,
                    supprime_le TEXT,
                    FOREIGN KEY (sujet_id) REFERENCES forums_sujets(id),
                    FOREIGN KEY (auteur_id) REFERENCES utilisateurs(id)
                );
                CREATE INDEX IF NOT EXISTS idx_forums_sondages_sujet
                    ON forums_sondages(sujet_id);
                CREATE TABLE IF NOT EXISTS forums_sondage_options (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sondage_id INTEGER NOT NULL,
                    libelle TEXT NOT NULL,
                    ordre INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (sondage_id) REFERENCES forums_sondages(id)
                );
                CREATE INDEX IF NOT EXISTS idx_forums_sondage_options
                    ON forums_sondage_options(sondage_id, ordre ASC);
                CREATE TABLE IF NOT EXISTS forums_sondage_votes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sondage_id INTEGER NOT NULL,
                    option_id INTEGER NOT NULL,
                    utilisateur_id INTEGER NOT NULL,
                    cree_le TEXT NOT NULL,
                    FOREIGN KEY (sondage_id) REFERENCES forums_sondages(id),
                    FOREIGN KEY (option_id) REFERENCES forums_sondage_options(id),
                    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id),
                    UNIQUE(sondage_id, utilisateur_id)
                );
                CREATE INDEX IF NOT EXISTS idx_forums_sondage_votes
                    ON forums_sondage_votes(sondage_id);
                """
            )
            migrer_schema_forum(connexion)
            connexion.commit()
        finally:
            connexion.close()
        _tables_ok = True


def migrer_schema_forum(connexion):
    """Ajoute colonnes manquantes pour les bases forum déjà créées."""
    colonnes_sujets = {
        row[1] for row in connexion.execute("PRAGMA table_info(forums_sujets)").fetchall()
    }
    if "date_modification" not in colonnes_sujets:
        connexion.execute(
            "ALTER TABLE forums_sujets ADD COLUMN date_modification TEXT"
        )
    if "supprime" not in colonnes_sujets:
        connexion.execute(
            "ALTER TABLE forums_sujets ADD COLUMN supprime INTEGER NOT NULL DEFAULT 0"
        )
    if "supprime_le" not in colonnes_sujets:
        connexion.execute("ALTER TABLE forums_sujets ADD COLUMN supprime_le TEXT")
    colonnes_messages = {
        row[1]
        for row in connexion.execute("PRAGMA table_info(forums_messages)").fetchall()
    }
    if "date_modification" not in colonnes_messages:
        connexion.execute(
            "ALTER TABLE forums_messages ADD COLUMN date_modification TEXT"
        )
    if "supprime" not in colonnes_messages:
        connexion.execute(
            "ALTER TABLE forums_messages ADD COLUMN supprime INTEGER NOT NULL DEFAULT 0"
        )
    if "supprime_le" not in colonnes_messages:
        connexion.execute("ALTER TABLE forums_messages ADD COLUMN supprime_le TEXT")
    if "message_parent_id" not in colonnes_messages:
        connexion.execute(
            "ALTER TABLE forums_messages ADD COLUMN message_parent_id INTEGER"
        )
    connexion.executescript(
        """
        CREATE TABLE IF NOT EXISTS forums_sondages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sujet_id INTEGER NOT NULL,
            auteur_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            cree_le TEXT NOT NULL,
            supprime INTEGER NOT NULL DEFAULT 0,
            supprime_le TEXT,
            FOREIGN KEY (sujet_id) REFERENCES forums_sujets(id),
            FOREIGN KEY (auteur_id) REFERENCES utilisateurs(id)
        );
        CREATE INDEX IF NOT EXISTS idx_forums_sondages_sujet
            ON forums_sondages(sujet_id);
        CREATE TABLE IF NOT EXISTS forums_sondage_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sondage_id INTEGER NOT NULL,
            libelle TEXT NOT NULL,
            ordre INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (sondage_id) REFERENCES forums_sondages(id)
        );
        CREATE INDEX IF NOT EXISTS idx_forums_sondage_options
            ON forums_sondage_options(sondage_id, ordre ASC);
        CREATE TABLE IF NOT EXISTS forums_sondage_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sondage_id INTEGER NOT NULL,
            option_id INTEGER NOT NULL,
            utilisateur_id INTEGER NOT NULL,
            cree_le TEXT NOT NULL,
            FOREIGN KEY (sondage_id) REFERENCES forums_sondages(id),
            FOREIGN KEY (option_id) REFERENCES forums_sondage_options(id),
            FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id),
            UNIQUE(sondage_id, utilisateur_id)
        );
        CREATE INDEX IF NOT EXISTS idx_forums_sondage_votes
            ON forums_sondage_votes(sondage_id);
        """
    )


def peut_modifier_contenu(utilisateur, auteur_id: int) -> bool:
    """Auteur du contenu ou administrateur."""
    if utilisateur["id"] == auteur_id:
        return True
    return bool(utilisateur["est_admin"])


def verifier_limite_forum(utilisateur_id: int):
    maintenant = time.time()
    with _verrou_limite:
        historique = _historique_forum[utilisateur_id]
        historique[:] = [
            instant
            for instant in historique
            if maintenant - instant < FENETRE_FORUM_SEC
        ]
        if len(historique) >= LIMITE_FORUM:
            raise HTTPException(
                429,
                "Trop de messages forum récents. Réessayez dans quelques minutes.",
            )
        historique.append(maintenant)


def verifier_limite_reactions_forum(utilisateur_id: int):
    maintenant = time.time()
    with _verrou_limite:
        historique = _historique_reactions_forum[utilisateur_id]
        historique[:] = [
            instant
            for instant in historique
            if maintenant - instant < FENETRE_REACTIONS_FORUM_SEC
        ]
        if len(historique) >= LIMITE_REACTIONS_FORUM:
            raise HTTPException(
                429,
                "Trop de réactions forum récentes. Réessayez dans quelques minutes.",
            )
        historique.append(maintenant)


def verifier_limite_sondages_forum(utilisateur_id: int):
    maintenant = time.time()
    with _verrou_limite:
        historique = _historique_sondages_forum[utilisateur_id]
        historique[:] = [
            instant
            for instant in historique
            if maintenant - instant < FENETRE_SONDAGES_FORUM_SEC
        ]
        if len(historique) >= LIMITE_SONDAGES_FORUM:
            raise HTTPException(
                429,
                "Trop d'actions sondage récentes. Réessayez dans quelques minutes.",
            )
        historique.append(maintenant)


def valider_championnat(championnat: str) -> str:
    texte = (championnat or "").strip()
    if texte not in CHAMPIONNATS_VALIDES:
        raise HTTPException(400, "Championnat invalide")
    return texte


def valider_titre(titre: str) -> str:
    texte = (titre or "").strip()
    if not texte:
        raise HTTPException(400, "Titre vide")
    if len(texte) > LONGUEUR_TITRE_MAX:
        raise HTTPException(
            400, f"Titre trop long (max {LONGUEUR_TITRE_MAX} caractères)"
        )
    return texte


def valider_contenu_message(contenu: str) -> str:
    texte = (contenu or "").strip()
    if not texte:
        raise HTTPException(400, "Message vide")
    if len(texte) > LONGUEUR_MESSAGE_MAX:
        raise HTTPException(
            400, f"Message trop long (max {LONGUEUR_MESSAGE_MAX} caractères)"
        )
    return texte


def valider_question_sondage(question: str) -> str:
    texte = (question or "").strip()
    if not texte:
        raise HTTPException(400, "Question de sondage vide")
    if len(texte) > LONGUEUR_QUESTION_SONDAGE_MAX:
        raise HTTPException(
            400,
            f"Question trop longue (max {LONGUEUR_QUESTION_SONDAGE_MAX} caractères)",
        )
    return texte


def valider_options_sondage(options: list[str]) -> list[str]:
    nettoyees: list[str] = []
    vues: set[str] = set()
    for brut in options or []:
        texte = (brut or "").strip()
        if not texte:
            continue
        if len(texte) > LONGUEUR_OPTION_SONDAGE_MAX:
            raise HTTPException(
                400,
                f"Option trop longue (max {LONGUEUR_OPTION_SONDAGE_MAX} caractères)",
            )
        cle = texte.casefold()
        if cle in vues:
            continue
        vues.add(cle)
        nettoyees.append(texte)
    if len(nettoyees) < NB_OPTIONS_SONDAGE_MIN:
        raise HTTPException(
            400, f"Au moins {NB_OPTIONS_SONDAGE_MIN} options distinctes requises"
        )
    if len(nettoyees) > NB_OPTIONS_SONDAGE_MAX:
        raise HTTPException(
            400, f"Maximum {NB_OPTIONS_SONDAGE_MAX} options autorisées"
        )
    return nettoyees


def serialiser_sujet(ligne) -> dict:
    date_modif = ligne["date_modification"] if "date_modification" in ligne.keys() else None
    return {
        "id": ligne["id"],
        "championnat": ligne["championnat"],
        "titre": ligne["titre"],
        "auteur_id": ligne["auteur_id"],
        "auteur_pseudo": ligne["auteur_pseudo"],
        "auteur_avatar_id": lire_avatar_id_ligne(ligne),
        "cree_le": ligne["cree_le"],
        "dernier_message_le": ligne["dernier_message_le"],
        "nb_messages": ligne["nb_messages"],
        "date_modification": date_modif,
        "modifie": bool(date_modif),
    }


def compter_reactions_messages(
    connexion, message_ids: list[int]
) -> dict[int, dict[str, int]]:
    vide = {t: 0 for t in TYPES_REACTION}
    if not message_ids:
        return {}
    placeholders = ",".join("?" * len(message_ids))
    lignes = connexion.execute(
        f"""
        SELECT message_id, type_reaction, COUNT(*) AS nb
        FROM forums_reactions
        WHERE message_id IN ({placeholders})
        GROUP BY message_id, type_reaction
        """,
        message_ids,
    ).fetchall()
    resultat: dict[int, dict[str, int]] = {mid: dict(vide) for mid in message_ids}
    for row in lignes:
        mid = row["message_id"]
        type_r = row["type_reaction"]
        if type_r in resultat[mid]:
            resultat[mid][type_r] = row["nb"]
    return resultat


def reactions_utilisateur_messages(
    connexion, utilisateur_id: int, message_ids: list[int]
) -> dict[int, set[str]]:
    if not utilisateur_id or not message_ids:
        return {}
    placeholders = ",".join("?" * len(message_ids))
    lignes = connexion.execute(
        f"""
        SELECT message_id, type_reaction FROM forums_reactions
        WHERE utilisateur_id = ? AND message_id IN ({placeholders})
        """,
        [utilisateur_id, *message_ids],
    ).fetchall()
    resultat: dict[int, set[str]] = defaultdict(set)
    for row in lignes:
        resultat[row["message_id"]].add(row["type_reaction"])
    return resultat


def extrait_message_parent(contenu: str) -> str:
    """Extrait court pour citation « En réponse à … »."""
    texte = (contenu or "").strip()
    if len(texte) <= LONGUEUR_EXTRAIT_PARENT:
        return texte
    return texte[: LONGUEUR_EXTRAIT_PARENT - 1].rstrip() + "…"


def valider_message_parent(connexion, sujet_id: int, message_parent_id: int | None):
    """Vérifie que le parent existe, n'est pas supprimé et appartient au sujet."""
    if message_parent_id is None:
        return None
    if message_parent_id < 1:
        raise HTTPException(400, "Identifiant de message parent invalide")
    parent = connexion.execute(
        """
        SELECT m.id, m.sujet_id, m.contenu, m.supprime,
               u.pseudo AS auteur_pseudo
        FROM forums_messages m
        JOIN utilisateurs u ON u.id = m.auteur_id
        WHERE m.id = ?
        """,
        (message_parent_id,),
    ).fetchone()
    if not parent or parent["supprime"] or parent["sujet_id"] != sujet_id:
        raise HTTPException(400, "Message parent invalide pour ce sujet")
    return parent


def infos_parent_depuis_ligne(ligne) -> dict | None:
    """Construit le bloc parent depuis une ligne JOIN (colonnes parent_*)."""
    parent_id = None
    try:
        parent_id = ligne["message_parent_id"]
    except (KeyError, IndexError):
        parent_id = None
    if not parent_id:
        return None
    try:
        parent_supprime = ligne["parent_supprime"]
    except (KeyError, IndexError):
        parent_supprime = 1
    if parent_supprime:
        return {
            "id": parent_id,
            "auteur_pseudo": None,
            "extrait": "Message supprimé",
            "supprime": True,
        }
    try:
        contenu_parent = ligne["parent_contenu"]
        pseudo_parent = ligne["parent_pseudo"]
    except (KeyError, IndexError):
        return {
            "id": parent_id,
            "auteur_pseudo": None,
            "extrait": "Message introuvable",
            "supprime": True,
        }
    return {
        "id": parent_id,
        "auteur_pseudo": pseudo_parent,
        "extrait": extrait_message_parent(contenu_parent or ""),
        "supprime": False,
    }


def serialiser_message(ligne, reactions=None, mes_reactions=None) -> dict:
    reactions = reactions or {t: 0 for t in TYPES_REACTION}
    mes_reactions = list(mes_reactions or [])
    date_modif = ligne["date_modification"] if "date_modification" in ligne.keys() else None
    try:
        message_parent_id = ligne["message_parent_id"]
    except (KeyError, IndexError):
        message_parent_id = None
    parent = infos_parent_depuis_ligne(ligne)
    return {
        "id": ligne["id"],
        "sujet_id": ligne["sujet_id"],
        "auteur_id": ligne["auteur_id"],
        "auteur_pseudo": ligne["auteur_pseudo"],
        "auteur_avatar_id": lire_avatar_id_ligne(ligne),
        "contenu": ligne["contenu"],
        "cree_le": ligne["cree_le"],
        "date_modification": date_modif,
        "modifie": bool(date_modif),
        "message_parent_id": message_parent_id,
        "message_parent": parent,
        "reactions": reactions,
        "mes_reactions": mes_reactions,
        "nb_reactions": sum(reactions.values()),
    }


def lire_sondage_sujet(connexion, sujet_id: int, utilisateur_id: int = 0):
    """Retourne le sondage actif d'un sujet, ou None."""
    sondage = connexion.execute(
        """
        SELECT id, sujet_id, auteur_id, question, cree_le
        FROM forums_sondages
        WHERE sujet_id = ? AND supprime = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        (sujet_id,),
    ).fetchone()
    if not sondage:
        return None
    return serialiser_sondage(connexion, sondage, utilisateur_id)


def serialiser_sondage(connexion, sondage, utilisateur_id: int = 0) -> dict:
    options = connexion.execute(
        """
        SELECT id, libelle, ordre
        FROM forums_sondage_options
        WHERE sondage_id = ?
        ORDER BY ordre ASC, id ASC
        """,
        (sondage["id"],),
    ).fetchall()
    compteurs = {
        row["option_id"]: row["nb"]
        for row in connexion.execute(
            """
            SELECT option_id, COUNT(*) AS nb
            FROM forums_sondage_votes
            WHERE sondage_id = ?
            GROUP BY option_id
            """,
            (sondage["id"],),
        ).fetchall()
    }
    mon_option_id = None
    if utilisateur_id:
        mon_vote = connexion.execute(
            """
            SELECT option_id FROM forums_sondage_votes
            WHERE sondage_id = ? AND utilisateur_id = ?
            """,
            (sondage["id"], utilisateur_id),
        ).fetchone()
        if mon_vote:
            mon_option_id = mon_vote["option_id"]
    a_vote = mon_option_id is not None
    total = sum(compteurs.values())
    options_out = []
    for opt in options:
        nb = compteurs.get(opt["id"], 0)
        item = {
            "id": opt["id"],
            "libelle": opt["libelle"],
            "ordre": opt["ordre"],
        }
        if a_vote:
            item["nb_votes"] = nb
            item["pourcentage"] = round(100.0 * nb / total, 1) if total else 0.0
        options_out.append(item)
    return {
        "id": sondage["id"],
        "sujet_id": sondage["sujet_id"],
        "auteur_id": sondage["auteur_id"],
        "question": sondage["question"],
        "cree_le": sondage["cree_le"],
        "options": options_out,
        "nb_votes_total": total if a_vote else None,
        "mon_option_id": mon_option_id,
        "a_vote": a_vote,
    }


class SujetCreerBody(BaseModel):
    titre: str = Field(..., min_length=1, max_length=LONGUEUR_TITRE_MAX)
    contenu: str = Field(..., min_length=1, max_length=LONGUEUR_MESSAGE_MAX)


class SujetModifierBody(BaseModel):
    titre: str = Field(..., min_length=1, max_length=LONGUEUR_TITRE_MAX)


class MessageCreerBody(BaseModel):
    contenu: str = Field(..., min_length=1, max_length=LONGUEUR_MESSAGE_MAX)
    message_parent_id: int | None = None


class MessageModifierBody(BaseModel):
    contenu: str = Field(..., min_length=1, max_length=LONGUEUR_MESSAGE_MAX)


class SignalementBody(BaseModel):
    motif: str = Field("", max_length=LONGUEUR_MOTIF_MAX)


class ReactionBody(BaseModel):
    type_reaction: str = "pouce"


class SondageCreerBody(BaseModel):
    question: str = Field(..., min_length=1, max_length=LONGUEUR_QUESTION_SONDAGE_MAX)
    options: list[str] = Field(
        ...,
        min_length=NB_OPTIONS_SONDAGE_MIN,
        max_length=NB_OPTIONS_SONDAGE_MAX,
    )


class SondageVoteBody(BaseModel):
    option_id: int


@routeur_forum.get("")
@routeur_forum.get("/")
def lister_espaces_forum():
    """Liste des championnats avec compteurs de sujets (lecture publique)."""
    assurer_tables_forum()
    connexion = ouvrir_base()
    try:
        compteurs = {
            row["championnat"]: row["nb"]
            for row in connexion.execute(
                """
                SELECT championnat, COUNT(*) AS nb
                FROM forums_sujets
                WHERE supprime = 0
                GROUP BY championnat
                """
            ).fetchall()
        }
        espaces = [
            {
                "championnat": nom,
                "nb_sujets": compteurs.get(nom, 0),
            }
            for nom in CHAMPIONNATS_VALIDES
        ]
        return {"espaces": espaces, "disclaimer": DISCLAIMER_FORUM}
    finally:
        connexion.close()


@routeur_forum.get("/{championnat}/sujets")
def lister_sujets(championnat: str):
    assurer_tables_forum()
    champ = valider_championnat(championnat)
    connexion = ouvrir_base()
    try:
        lignes = connexion.execute(
            """
            SELECT s.id, s.championnat, s.titre, s.auteur_id, s.cree_le,
                   s.dernier_message_le, s.nb_messages, s.date_modification,
                   u.pseudo AS auteur_pseudo, u.avatar_id
            FROM forums_sujets s
            JOIN utilisateurs u ON u.id = s.auteur_id
            WHERE s.championnat = ? AND s.supprime = 0
            ORDER BY s.dernier_message_le DESC
            LIMIT 100
            """,
            (champ,),
        ).fetchall()
        return {
            "championnat": champ,
            "sujets": [serialiser_sujet(row) for row in lignes],
            "disclaimer": DISCLAIMER_FORUM,
        }
    finally:
        connexion.close()


@routeur_forum.post("/{championnat}/sujets")
def creer_sujet(championnat: str, donnees: SujetCreerBody, request: Request):
    assurer_tables_forum()
    utilisateur, connexion = utilisateur_connecte(request)
    verifier_limite_forum(utilisateur["id"])
    champ = valider_championnat(championnat)
    titre = valider_titre(donnees.titre)
    contenu = valider_contenu_message(donnees.contenu)
    instant = maintenant_iso()
    try:
        curseur = connexion.execute(
            """
            INSERT INTO forums_sujets (
                championnat, titre, auteur_id, cree_le, dernier_message_le, nb_messages
            ) VALUES (?, ?, ?, ?, ?, 1)
            """,
            (champ, titre, utilisateur["id"], instant, instant),
        )
        sujet_id = curseur.lastrowid
        curseur_msg = connexion.execute(
            """
            INSERT INTO forums_messages (sujet_id, auteur_id, contenu, cree_le)
            VALUES (?, ?, ?, ?)
            """,
            (sujet_id, utilisateur["id"], contenu, instant),
        )
        connexion.commit()
        return {
            "sujet": {
                "id": sujet_id,
                "championnat": champ,
                "titre": titre,
                "auteur_id": utilisateur["id"],
                "auteur_pseudo": utilisateur["pseudo"],
                "auteur_avatar_id": lire_avatar_id_ligne(utilisateur),
                "cree_le": instant,
                "dernier_message_le": instant,
                "nb_messages": 1,
                "date_modification": None,
                "modifie": False,
            },
            "message": {
                "id": curseur_msg.lastrowid,
                "sujet_id": sujet_id,
                "auteur_id": utilisateur["id"],
                "auteur_pseudo": utilisateur["pseudo"],
                "auteur_avatar_id": lire_avatar_id_ligne(utilisateur),
                "contenu": contenu,
                "cree_le": instant,
                "date_modification": None,
                "modifie": False,
                "message_parent_id": None,
                "message_parent": None,
                "reactions": {t: 0 for t in TYPES_REACTION},
                "mes_reactions": [],
                "nb_reactions": 0,
            },
            "disclaimer": DISCLAIMER_FORUM,
        }
    finally:
        connexion.close()


@routeur_forum.get("/sujets/{sujet_id}")
def lire_sujet(sujet_id: int, request: Request):
    assurer_tables_forum()
    if sujet_id < 1:
        raise HTTPException(400, "Identifiant de sujet invalide")
    utilisateur, connexion_session = session_optionnelle(request)
    connexion = connexion_session or ouvrir_base()
    fermer = connexion_session is None
    try:
        sujet = connexion.execute(
            """
            SELECT s.id, s.championnat, s.titre, s.auteur_id, s.cree_le,
                   s.dernier_message_le, s.nb_messages, s.date_modification,
                   u.pseudo AS auteur_pseudo, u.avatar_id
            FROM forums_sujets s
            JOIN utilisateurs u ON u.id = s.auteur_id
            WHERE s.id = ? AND s.supprime = 0
            """,
            (sujet_id,),
        ).fetchone()
        if not sujet:
            raise HTTPException(404, "Sujet introuvable")
        lignes = connexion.execute(
            """
            SELECT m.id, m.sujet_id, m.auteur_id, m.contenu, m.cree_le,
                   m.date_modification, m.message_parent_id,
                   u.pseudo AS auteur_pseudo, u.avatar_id,
                   p.contenu AS parent_contenu,
                   p.supprime AS parent_supprime,
                   up.pseudo AS parent_pseudo
            FROM forums_messages m
            JOIN utilisateurs u ON u.id = m.auteur_id
            LEFT JOIN forums_messages p ON p.id = m.message_parent_id
            LEFT JOIN utilisateurs up ON up.id = p.auteur_id
            WHERE m.sujet_id = ? AND m.supprime = 0
            ORDER BY m.cree_le ASC
            LIMIT 500
            """,
            (sujet_id,),
        ).fetchall()
        ids = [row["id"] for row in lignes]
        compteurs = compter_reactions_messages(connexion, ids)
        mes = reactions_utilisateur_messages(
            connexion, utilisateur["id"] if utilisateur else 0, ids
        )
        messages = [
            serialiser_message(
                row,
                reactions=compteurs.get(row["id"], {t: 0 for t in TYPES_REACTION}),
                mes_reactions=sorted(mes.get(row["id"], set())),
            )
            for row in lignes
        ]
        utilisateur_id = utilisateur["id"] if utilisateur else 0
        return {
            "sujet": serialiser_sujet(sujet),
            "messages": messages,
            "sondage": lire_sondage_sujet(connexion, sujet_id, utilisateur_id),
            "types_reaction": list(TYPES_REACTION),
            "disclaimer": DISCLAIMER_FORUM,
        }
    finally:
        if fermer:
            connexion.close()
        elif connexion_session:
            connexion_session.close()


@routeur_forum.post("/sujets/{sujet_id}/messages")
def publier_message(sujet_id: int, donnees: MessageCreerBody, request: Request):
    assurer_tables_forum()
    if sujet_id < 1:
        raise HTTPException(400, "Identifiant de sujet invalide")
    utilisateur, connexion = utilisateur_connecte(request)
    verifier_limite_forum(utilisateur["id"])
    contenu = valider_contenu_message(donnees.contenu)
    instant = maintenant_iso()
    try:
        sujet = connexion.execute(
            """
            SELECT id FROM forums_sujets WHERE id = ? AND supprime = 0
            """,
            (sujet_id,),
        ).fetchone()
        if not sujet:
            raise HTTPException(404, "Sujet introuvable")
        parent = valider_message_parent(connexion, sujet_id, donnees.message_parent_id)
        parent_id = parent["id"] if parent else None
        curseur = connexion.execute(
            """
            INSERT INTO forums_messages (
                sujet_id, auteur_id, contenu, cree_le, message_parent_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (sujet_id, utilisateur["id"], contenu, instant, parent_id),
        )
        connexion.execute(
            """
            UPDATE forums_sujets
            SET dernier_message_le = ?, nb_messages = nb_messages + 1
            WHERE id = ?
            """,
            (instant, sujet_id),
        )
        connexion.commit()
        message_parent = None
        if parent:
            message_parent = {
                "id": parent["id"],
                "auteur_pseudo": parent["auteur_pseudo"],
                "extrait": extrait_message_parent(parent["contenu"]),
                "supprime": False,
            }
        return {
            "message": {
                "id": curseur.lastrowid,
                "sujet_id": sujet_id,
                "auteur_id": utilisateur["id"],
                "auteur_pseudo": utilisateur["pseudo"],
                "auteur_avatar_id": lire_avatar_id_ligne(utilisateur),
                "contenu": contenu,
                "cree_le": instant,
                "date_modification": None,
                "modifie": False,
                "message_parent_id": parent_id,
                "message_parent": message_parent,
                "reactions": {t: 0 for t in TYPES_REACTION},
                "mes_reactions": [],
                "nb_reactions": 0,
            }
        }
    finally:
        connexion.close()


@routeur_forum.patch("/sujets/{sujet_id}")
def modifier_sujet(sujet_id: int, donnees: SujetModifierBody, request: Request):
    """Modifie le titre d'un sujet (auteur ou admin)."""
    assurer_tables_forum()
    if sujet_id < 1:
        raise HTTPException(400, "Identifiant de sujet invalide")
    utilisateur, connexion = utilisateur_connecte(request)
    titre = valider_titre(donnees.titre)
    instant = maintenant_iso()
    try:
        sujet = connexion.execute(
            """
            SELECT s.id, s.championnat, s.titre, s.auteur_id, s.cree_le,
                   s.dernier_message_le, s.nb_messages, s.date_modification,
                   u.pseudo AS auteur_pseudo, u.avatar_id
            FROM forums_sujets s
            JOIN utilisateurs u ON u.id = s.auteur_id
            WHERE s.id = ? AND s.supprime = 0
            """,
            (sujet_id,),
        ).fetchone()
        if not sujet:
            raise HTTPException(404, "Sujet introuvable")
        if not peut_modifier_contenu(utilisateur, sujet["auteur_id"]):
            raise HTTPException(403, "Seul l'auteur ou un admin peut modifier ce sujet")
        connexion.execute(
            """
            UPDATE forums_sujets
            SET titre = ?, date_modification = ?
            WHERE id = ?
            """,
            (titre, instant, sujet_id),
        )
        connexion.commit()
        return {
            "sujet": {
                "id": sujet["id"],
                "championnat": sujet["championnat"],
                "titre": titre,
                "auteur_id": sujet["auteur_id"],
                "auteur_pseudo": sujet["auteur_pseudo"],
                "auteur_avatar_id": lire_avatar_id_ligne(sujet),
                "cree_le": sujet["cree_le"],
                "dernier_message_le": sujet["dernier_message_le"],
                "nb_messages": sujet["nb_messages"],
                "date_modification": instant,
                "modifie": True,
            }
        }
    finally:
        connexion.close()


@routeur_forum.patch("/messages/{message_id}")
def modifier_message(message_id: int, donnees: MessageModifierBody, request: Request):
    """Modifie le contenu d'un message (auteur ou admin)."""
    assurer_tables_forum()
    if message_id < 1:
        raise HTTPException(400, "Identifiant de message invalide")
    utilisateur, connexion = utilisateur_connecte(request)
    contenu = valider_contenu_message(donnees.contenu)
    instant = maintenant_iso()
    try:
        message = connexion.execute(
            """
            SELECT m.id, m.sujet_id, m.auteur_id, m.contenu, m.cree_le,
                   m.date_modification, m.message_parent_id,
                   u.pseudo AS auteur_pseudo, u.avatar_id,
                   p.contenu AS parent_contenu,
                   p.supprime AS parent_supprime,
                   up.pseudo AS parent_pseudo
            FROM forums_messages m
            JOIN utilisateurs u ON u.id = m.auteur_id
            LEFT JOIN forums_messages p ON p.id = m.message_parent_id
            LEFT JOIN utilisateurs up ON up.id = p.auteur_id
            WHERE m.id = ? AND m.supprime = 0
            """,
            (message_id,),
        ).fetchone()
        if not message:
            raise HTTPException(404, "Message introuvable")
        if not peut_modifier_contenu(utilisateur, message["auteur_id"]):
            raise HTTPException(
                403, "Seul l'auteur ou un admin peut modifier ce message"
            )
        connexion.execute(
            """
            UPDATE forums_messages
            SET contenu = ?, date_modification = ?
            WHERE id = ?
            """,
            (contenu, instant, message_id),
        )
        connexion.commit()
        compteurs = compter_reactions_messages(connexion, [message_id])
        mes = reactions_utilisateur_messages(connexion, utilisateur["id"], [message_id])
        reactions = compteurs.get(message_id, {t: 0 for t in TYPES_REACTION})
        serialise = serialiser_message(
            message,
            reactions=reactions,
            mes_reactions=sorted(mes.get(message_id, set())),
        )
        serialise["contenu"] = contenu
        serialise["date_modification"] = instant
        serialise["modifie"] = True
        return {"message": serialise}
    finally:
        connexion.close()


@routeur_forum.delete("/messages/{message_id}")
def supprimer_message(message_id: int, request: Request):
    """Soft-delete d'un message (auteur ou admin). Si plus aucun message, soft-delete du sujet."""
    assurer_tables_forum()
    if message_id < 1:
        raise HTTPException(400, "Identifiant de message invalide")
    utilisateur, connexion = utilisateur_connecte(request)
    try:
        message = connexion.execute(
            """
            SELECT id, sujet_id, auteur_id
            FROM forums_messages
            WHERE id = ? AND supprime = 0
            """,
            (message_id,),
        ).fetchone()
        if not message:
            raise HTTPException(404, "Message introuvable")
        if not peut_modifier_contenu(utilisateur, message["auteur_id"]):
            raise HTTPException(
                403, "Seul l'auteur ou un admin peut supprimer ce message"
            )
        sujet_id = message["sujet_id"]
        instant = maintenant_iso()
        connexion.execute(
            """
            UPDATE forums_messages
            SET supprime = 1, supprime_le = ?
            WHERE id = ? AND supprime = 0
            """,
            (instant, message_id),
        )
        connexion.execute(
            """
            UPDATE forums_sujets
            SET nb_messages = CASE
                WHEN nb_messages > 0 THEN nb_messages - 1
                ELSE 0
            END
            WHERE id = ? AND supprime = 0
            """,
            (sujet_id,),
        )
        restants = connexion.execute(
            """
            SELECT COUNT(*) AS nb FROM forums_messages
            WHERE sujet_id = ? AND supprime = 0
            """,
            (sujet_id,),
        ).fetchone()["nb"]
        sujet_supprime = restants == 0
        if sujet_supprime:
            connexion.execute(
                """
                UPDATE forums_sujets
                SET supprime = 1, supprime_le = ?, nb_messages = 0
                WHERE id = ? AND supprime = 0
                """,
                (instant, sujet_id),
            )
            connexion.execute(
                """
                UPDATE forums_sondages
                SET supprime = 1, supprime_le = ?
                WHERE sujet_id = ? AND supprime = 0
                """,
                (instant, sujet_id),
            )
        else:
            dernier = connexion.execute(
                """
                SELECT cree_le FROM forums_messages
                WHERE sujet_id = ? AND supprime = 0
                ORDER BY cree_le DESC
                LIMIT 1
                """,
                (sujet_id,),
            ).fetchone()
            if dernier:
                connexion.execute(
                    """
                    UPDATE forums_sujets
                    SET dernier_message_le = ?, nb_messages = ?
                    WHERE id = ?
                    """,
                    (dernier["cree_le"], restants, sujet_id),
                )
        connexion.commit()
        return {
            "ok": True,
            "sujet_id": sujet_id,
            "sujet_supprime": sujet_supprime,
        }
    finally:
        connexion.close()


@routeur_forum.delete("/sujets/{sujet_id}")
def supprimer_sujet(sujet_id: int, request: Request):
    """Soft-delete d'un sujet entier (auteur du sujet ou admin)."""
    assurer_tables_forum()
    if sujet_id < 1:
        raise HTTPException(400, "Identifiant de sujet invalide")
    utilisateur, connexion = utilisateur_connecte(request)
    try:
        sujet = connexion.execute(
            """
            SELECT id, auteur_id FROM forums_sujets
            WHERE id = ? AND supprime = 0
            """,
            (sujet_id,),
        ).fetchone()
        if not sujet:
            raise HTTPException(404, "Sujet introuvable")
        if not peut_modifier_contenu(utilisateur, sujet["auteur_id"]):
            raise HTTPException(
                403, "Seul l'auteur ou un admin peut supprimer ce sujet"
            )
        instant = maintenant_iso()
        connexion.execute(
            """
            UPDATE forums_sujets
            SET supprime = 1, supprime_le = ?
            WHERE id = ? AND supprime = 0
            """,
            (instant, sujet_id),
        )
        connexion.execute(
            """
            UPDATE forums_messages
            SET supprime = 1, supprime_le = ?
            WHERE sujet_id = ? AND supprime = 0
            """,
            (instant, sujet_id),
        )
        connexion.execute(
            """
            UPDATE forums_sondages
            SET supprime = 1, supprime_le = ?
            WHERE sujet_id = ? AND supprime = 0
            """,
            (instant, sujet_id),
        )
        connexion.commit()
        return {"ok": True, "sujet_id": sujet_id, "sujet_supprime": True}
    finally:
        connexion.close()


@routeur_forum.post("/messages/{message_id}/signaler")
def signaler_message(
    message_id: int, request: Request, donnees: SignalementBody | None = None
):
    assurer_tables_forum()
    if message_id < 1:
        raise HTTPException(400, "Identifiant de message invalide")
    utilisateur, connexion = utilisateur_connecte(request)
    motif = ((donnees.motif if donnees else "") or "").strip()[:LONGUEUR_MOTIF_MAX]
    try:
        message = connexion.execute(
            """
            SELECT id FROM forums_messages WHERE id = ? AND supprime = 0
            """,
            (message_id,),
        ).fetchone()
        if not message:
            raise HTTPException(404, "Message introuvable")
        connexion.execute(
            """
            INSERT INTO forums_signalements (
                message_id, utilisateur_id, motif, cree_le
            ) VALUES (?, ?, ?, ?)
            """,
            (message_id, utilisateur["id"], motif or None, maintenant_iso()),
        )
        connexion.commit()
        return {"ok": True}
    finally:
        connexion.close()


@routeur_forum.post("/messages/{message_id}/reactions")
def basculer_reaction_message(
    message_id: int, donnees: ReactionBody, request: Request
):
    assurer_tables_forum()
    if message_id < 1:
        raise HTTPException(400, "Identifiant de message invalide")
    utilisateur, connexion = utilisateur_connecte(request)
    verifier_limite_reactions_forum(utilisateur["id"])
    type_r = valider_type_reaction(donnees.type_reaction)
    try:
        message = connexion.execute(
            """
            SELECT id FROM forums_messages WHERE id = ? AND supprime = 0
            """,
            (message_id,),
        ).fetchone()
        if not message:
            raise HTTPException(404, "Message introuvable")
        existant = connexion.execute(
            """
            SELECT id FROM forums_reactions
            WHERE message_id = ? AND utilisateur_id = ? AND type_reaction = ?
            """,
            (message_id, utilisateur["id"], type_r),
        ).fetchone()
        if existant:
            connexion.execute(
                "DELETE FROM forums_reactions WHERE id = ?", (existant["id"],)
            )
            active = False
        else:
            connexion.execute(
                """
                INSERT INTO forums_reactions (
                    message_id, utilisateur_id, type_reaction, cree_le
                ) VALUES (?, ?, ?, ?)
                """,
                (message_id, utilisateur["id"], type_r, maintenant_iso()),
            )
            active = True
        connexion.commit()
        compteurs = compter_reactions_messages(connexion, [message_id])
        mes = reactions_utilisateur_messages(connexion, utilisateur["id"], [message_id])
        reactions = compteurs.get(message_id, {t: 0 for t in TYPES_REACTION})
        return {
            "active": active,
            "type_reaction": type_r,
            "reactions": reactions,
            "mes_reactions": sorted(mes.get(message_id, set())),
            "nb_reactions": sum(reactions.values()),
        }
    finally:
        connexion.close()


@routeur_forum.post("/sujets/{sujet_id}/sondage")
def creer_sondage_sujet(sujet_id: int, donnees: SondageCreerBody, request: Request):
    """Crée un sondage sur un sujet (un seul sondage actif par sujet)."""
    assurer_tables_forum()
    if sujet_id < 1:
        raise HTTPException(400, "Identifiant de sujet invalide")
    utilisateur, connexion = utilisateur_connecte(request)
    verifier_limite_sondages_forum(utilisateur["id"])
    question = valider_question_sondage(donnees.question)
    options = valider_options_sondage(donnees.options)
    instant = maintenant_iso()
    try:
        sujet = connexion.execute(
            """
            SELECT id, auteur_id FROM forums_sujets
            WHERE id = ? AND supprime = 0
            """,
            (sujet_id,),
        ).fetchone()
        if not sujet:
            raise HTTPException(404, "Sujet introuvable")
        existant = connexion.execute(
            """
            SELECT id FROM forums_sondages
            WHERE sujet_id = ? AND supprime = 0
            """,
            (sujet_id,),
        ).fetchone()
        if existant:
            raise HTTPException(409, "Ce sujet a déjà un sondage")
        curseur = connexion.execute(
            """
            INSERT INTO forums_sondages (sujet_id, auteur_id, question, cree_le)
            VALUES (?, ?, ?, ?)
            """,
            (sujet_id, utilisateur["id"], question, instant),
        )
        sondage_id = curseur.lastrowid
        for index, libelle in enumerate(options):
            connexion.execute(
                """
                INSERT INTO forums_sondage_options (sondage_id, libelle, ordre)
                VALUES (?, ?, ?)
                """,
                (sondage_id, libelle, index),
            )
        connexion.commit()
        sondage = connexion.execute(
            """
            SELECT id, sujet_id, auteur_id, question, cree_le
            FROM forums_sondages WHERE id = ?
            """,
            (sondage_id,),
        ).fetchone()
        return {
            "sondage": serialiser_sondage(connexion, sondage, utilisateur["id"]),
        }
    finally:
        connexion.close()


@routeur_forum.post("/sondages/{sondage_id}/votes")
def voter_sondage_forum(sondage_id: int, donnees: SondageVoteBody, request: Request):
    """Enregistre un vote (1 par utilisateur, non modifiable)."""
    assurer_tables_forum()
    if sondage_id < 1:
        raise HTTPException(400, "Identifiant de sondage invalide")
    if donnees.option_id < 1:
        raise HTTPException(400, "Option invalide")
    utilisateur, connexion = utilisateur_connecte(request)
    verifier_limite_sondages_forum(utilisateur["id"])
    try:
        sondage = connexion.execute(
            """
            SELECT id, sujet_id, auteur_id, question, cree_le
            FROM forums_sondages
            WHERE id = ? AND supprime = 0
            """,
            (sondage_id,),
        ).fetchone()
        if not sondage:
            raise HTTPException(404, "Sondage introuvable")
        sujet = connexion.execute(
            """
            SELECT id FROM forums_sujets WHERE id = ? AND supprime = 0
            """,
            (sondage["sujet_id"],),
        ).fetchone()
        if not sujet:
            raise HTTPException(404, "Sujet introuvable")
        option = connexion.execute(
            """
            SELECT id FROM forums_sondage_options
            WHERE id = ? AND sondage_id = ?
            """,
            (donnees.option_id, sondage_id),
        ).fetchone()
        if not option:
            raise HTTPException(400, "Option invalide pour ce sondage")
        deja = connexion.execute(
            """
            SELECT id FROM forums_sondage_votes
            WHERE sondage_id = ? AND utilisateur_id = ?
            """,
            (sondage_id, utilisateur["id"]),
        ).fetchone()
        if deja:
            raise HTTPException(409, "Vous avez déjà voté à ce sondage")
        connexion.execute(
            """
            INSERT INTO forums_sondage_votes (
                sondage_id, option_id, utilisateur_id, cree_le
            ) VALUES (?, ?, ?, ?)
            """,
            (sondage_id, donnees.option_id, utilisateur["id"], maintenant_iso()),
        )
        connexion.commit()
        return {
            "sondage": serialiser_sondage(connexion, sondage, utilisateur["id"]),
        }
    finally:
        connexion.close()


@routeur_forum.delete("/sondages/{sondage_id}")
def supprimer_sondage_forum(sondage_id: int, request: Request):
    """Soft-delete d'un sondage (auteur du sondage ou admin)."""
    assurer_tables_forum()
    if sondage_id < 1:
        raise HTTPException(400, "Identifiant de sondage invalide")
    utilisateur, connexion = utilisateur_connecte(request)
    try:
        sondage = connexion.execute(
            """
            SELECT id, auteur_id FROM forums_sondages
            WHERE id = ? AND supprime = 0
            """,
            (sondage_id,),
        ).fetchone()
        if not sondage:
            raise HTTPException(404, "Sondage introuvable")
        if not peut_modifier_contenu(utilisateur, sondage["auteur_id"]):
            raise HTTPException(
                403, "Seul l'auteur ou un admin peut supprimer ce sondage"
            )
        connexion.execute(
            """
            UPDATE forums_sondages
            SET supprime = 1, supprime_le = ?
            WHERE id = ? AND supprime = 0
            """,
            (maintenant_iso(), sondage_id),
        )
        connexion.commit()
        return {"ok": True, "sondage_id": sondage_id}
    finally:
        connexion.close()
