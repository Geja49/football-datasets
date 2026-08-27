"""Catalogue d'avatars prédéfinis (pas d'upload utilisateur)."""

from fastapi import HTTPException

# Identifiants stables — fichiers : site/frontend/public/avatars/{id}.svg ou .png
CATALOGUE_AVATARS: tuple[dict[str, str], ...] = (
    {"id": "joueur-foot-01", "libelle": "Attaquant rouge"},
    {"id": "joueur-foot-02", "libelle": "Milieu bleu"},
    {"id": "joueur-foot-03", "libelle": "Défenseur vert"},
    {"id": "joueur-foot-04", "libelle": "Gardien jaune"},
    {"id": "joueur-foot-05", "libelle": "Capitaine blanc"},
    {"id": "joueur-foot-06", "libelle": "Ailier violet"},
    {"id": "joueur-foot-07", "libelle": "Polyvalent orange"},
    {"id": "joueur-foot-08", "libelle": "Stopper noir"},
    {"id": "joueur-foot-09", "libelle": "Meneur rose"},
    {"id": "joueur-foot-10", "libelle": "Jeune prodige"},
    {"id": "joueur-foot-11", "libelle": "Vétéran"},
    {"id": "joueur-foot-12", "libelle": "Star dorée"},
    {"id": "avatar-legende-01", "libelle": "Portrait foot 1"},
    {"id": "avatar-legende-02", "libelle": "Portrait foot 2"},
    {"id": "avatar-legende-03", "libelle": "Portrait foot 3"},
    {"id": "avatar-legende-04", "libelle": "Portrait foot 4"},
    {"id": "avatar-legende-05", "libelle": "Portrait foot 5"},
    {"id": "avatar-legende-06", "libelle": "Portrait foot 6"},
    {"id": "avatar-legende-07", "libelle": "Portrait foot 7"},
    {"id": "avatar-legende-08", "libelle": "Portrait foot 8"},
    {"id": "avatar-legende-09", "libelle": "Portrait foot 9"},
    {"id": "avatar-legende-10", "libelle": "Portrait foot 10"},
    {"id": "avatar-legende-11", "libelle": "Portrait foot 11"},
    {"id": "avatar-legende-12", "libelle": "Portrait foot 12"},
    {"id": "avatar-legende-13", "libelle": "Portrait foot 13"},
    {"id": "avatar-legende-14", "libelle": "Portrait foot 14"},
    {"id": "avatar-legende-15", "libelle": "Portrait foot 15"},
    {"id": "avatar-legende-16", "libelle": "Portrait foot 16"},
    {"id": "avatar-legende-17", "libelle": "Portrait foot 17"},
    {"id": "avatar-legende-18", "libelle": "Portrait foot 18"},
    *(
        {
            "id": f"avatar-legende-b-{i:02d}",
            "libelle": f"Légende foot {18 + i}",
        }
        for i in range(1, 51)
    ),
)

IDS_AVATARS_VALIDES = frozenset(item["id"] for item in CATALOGUE_AVATARS)

# Rétrocompatibilité : anciens identifiants → portrait joueur-foot
ANCIEN_VERS_NOUVEAU: dict[str, str] = {
    "ballon-vert": "joueur-foot-03",
    "ballon-or": "joueur-foot-12",
    "maillot-bleu": "joueur-foot-02",
    "maillot-rouge": "joueur-foot-01",
    "sifflet": "joueur-foot-05",
    "crampon": "joueur-foot-08",
    "gardien": "joueur-foot-04",
    "trophee": "joueur-foot-12",
    **{f"avatar-voxel-{i:02d}": f"joueur-foot-{((i - 1) % 12) + 1:02d}" for i in range(1, 11)},
    **{f"avatar-argile-{i:02d}": f"joueur-foot-{((i + 2) % 12) + 1:02d}" for i in range(1, 6)},
    **{f"avatar-robot-{i:02d}": f"joueur-foot-{((i + 5) % 12) + 1:02d}" for i in range(1, 6)},
}


def _normaliser_avatar_id(avatar_id: str) -> str:
    """Convertit un identifiant legacy en identifiant catalogue actuel."""
    texte = (avatar_id or "").strip()
    if not texte:
        return ""
    if texte in IDS_AVATARS_VALIDES:
        return texte
    return ANCIEN_VERS_NOUVEAU.get(texte, "")


def valider_avatar_id(avatar_id: str | None) -> str:
    """Retourne un identifiant valide ou une chaîne vide (initiales)."""
    texte = (avatar_id or "").strip()
    if not texte:
        return ""
    normalise = _normaliser_avatar_id(texte)
    if normalise:
        return normalise
    raise HTTPException(400, "Avatar inconnu")


def lire_avatar_id_ligne(ligne) -> str:
    """Lit avatar_id depuis une ligne SQLite ; ignore les valeurs invalides."""
    try:
        if "avatar_id" not in ligne.keys():
            return ""
        brut = (ligne["avatar_id"] or "").strip()
    except (IndexError, KeyError, TypeError):
        return ""
    return _normaliser_avatar_id(brut)
