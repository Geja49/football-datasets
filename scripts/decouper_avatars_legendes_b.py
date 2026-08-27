"""Découpe la grille 5×10 de badges légendes (pack B) en PNG individuels.

Usage :
    python scripts/decouper_avatars_legendes_b.py [chemin_image_source]

Écrit site/frontend/public/avatars/avatar-legende-b-XX.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

DOSSIER_SORTIE = (
    Path(__file__).resolve().parents[1] / "site" / "frontend" / "public" / "avatars"
)
IMAGE_DEFAUT = (
    Path(__file__).resolve().parents[1].parent
    / ".cursor"
    / "projects"
    / "c-Users-sekei-football-datasets"
    / "assets"
    / "c__Users_sekei_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images_image-fb311b7f-fecb-4ae3-95e7-1a0084b8de34.png"
)
NB_BADGES = 50
DEBUT_LIBELLE = 19  # suite numérique après le pack A (18 badges)


def _masque_non_blanc(arr: np.ndarray, seuil: int = 248) -> np.ndarray:
    return (arr[:, :, 0] < seuil) | (arr[:, :, 1] < seuil) | (arr[:, :, 2] < seuil)


def _detecter_bandes_lignes(mask: np.ndarray, seuil_pixels: int = 100) -> list[tuple[int, int]]:
    """Repère les bandes horizontales contenant des badges (gère espacement irrégulier)."""
    densite = mask.sum(axis=1)
    bandes: list[tuple[int, int]] = []
    debut: int | None = None
    for y, nb in enumerate(densite):
        actif = nb >= seuil_pixels
        if actif and debut is None:
            debut = y
        elif not actif and debut is not None:
            bandes.append((debut, y - 1))
            debut = None
    if debut is not None:
        bandes.append((debut, len(densite) - 1))
    return bandes


def _detecter_colonnes_ligne(mask_ligne: np.ndarray, seuil_pixels: int = 5) -> list[tuple[int, int]]:
    """Repère les colonnes d'une bande horizontale."""
    densite = mask_ligne.sum(axis=0)
    colonnes: list[tuple[int, int]] = []
    debut: int | None = None
    for x, nb in enumerate(densite):
        actif = nb >= seuil_pixels
        if actif and debut is None:
            debut = x
        elif not actif and debut is not None:
            colonnes.append((debut, x - 1))
            debut = None
    if debut is not None:
        colonnes.append((debut, len(densite) - 1))
    return colonnes


def _centre_et_rayon(mask: np.ndarray, x0: int, y0: int) -> tuple[int, int, int]:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        raise ValueError("Cellule vide — badge introuvable")
    cx = x0 + int((xs.min() + xs.max()) // 2)
    cy = y0 + int((ys.min() + ys.max()) // 2)
    rayon = int(max(xs.max() - xs.min(), ys.max() - ys.min()) // 2)
    return cx, cy, rayon


def _rendre_fond_transparent(image: Image.Image, seuil: int = 245) -> Image.Image:
    rgba = image.convert("RGBA")
    donnees = np.array(rgba)
    blanc = (
        (donnees[:, :, 0] >= seuil)
        & (donnees[:, :, 1] >= seuil)
        & (donnees[:, :, 2] >= seuil)
    )
    donnees[blanc, 3] = 0
    return Image.fromarray(donnees, "RGBA")


def _appliquer_masque_cercle(image: Image.Image, marge: int = 2) -> Image.Image:
    rgba = image.convert("RGBA")
    w, h = rgba.size
    cx, cy = w // 2, h // 2
    rayon = min(w, h) // 2 - marge
    masque = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(masque)
    draw.ellipse((cx - rayon, cy - rayon, cx + rayon, cy + rayon), fill=255)
    rgba.putalpha(Image.fromarray(np.minimum(np.array(rgba.split()[3]), np.array(masque))))
    return rgba


def _libelle_pour_index(index: int) -> str:
    return f"Légende foot {DEBUT_LIBELLE + index - 1}"


def decouper_grille(chemin_source: Path, dossier_sortie: Path) -> list[tuple[str, str]]:
    image = Image.open(chemin_source).convert("RGBA")
    largeur, hauteur = image.size
    arr = np.array(image)
    mask_global = _masque_non_blanc(arr)

    bandes = _detecter_bandes_lignes(mask_global)
    if len(bandes) != 5:
        raise ValueError(f"Attendu 5 lignes, détecté {len(bandes)} : {bandes}")

    dossier_sortie.mkdir(parents=True, exist_ok=True)
    fichiers: list[tuple[str, str]] = []
    index = 0

    for y0, y1 in bandes:
        sous_ligne = mask_global[y0 : y1 + 1, :]
        colonnes = _detecter_colonnes_ligne(sous_ligne)
        if len(colonnes) != 10:
            raise ValueError(f"Ligne y={y0}-{y1} : attendu 10 colonnes, détecté {len(colonnes)}")

        for x0, x1 in colonnes:
            index += 1
            ident = f"avatar-legende-b-{index:02d}"
            sous_masque = mask_global[y0 : y1 + 1, x0 : x1 + 1]
            cx, cy, rayon = _centre_et_rayon(sous_masque, x0, y0)

            padding = max(4, rayon // 20)
            taille = (rayon + padding) * 2
            gauche = max(0, cx - rayon - padding)
            haut = max(0, cy - rayon - padding)
            droite = min(largeur, gauche + taille)
            bas = min(hauteur, haut + taille)

            extrait = image.crop((gauche, haut, droite, bas))
            extrait = _rendre_fond_transparent(extrait)
            extrait = _appliquer_masque_cercle(extrait)

            cote = max(extrait.size)
            carre = Image.new("RGBA", (cote, cote), (0, 0, 0, 0))
            ox = (cote - extrait.width) // 2
            oy = (cote - extrait.height) // 2
            carre.paste(extrait, (ox, oy), extrait)

            chemin_sortie = dossier_sortie / f"{ident}.png"
            carre.save(chemin_sortie, "PNG", optimize=True)
            fichiers.append((ident, _libelle_pour_index(index)))
            print(f"Écrit {chemin_sortie.name} ({carre.width}x{carre.height})")

    if index != NB_BADGES:
        raise ValueError(f"Attendu {NB_BADGES} badges, découpé {index}")

    return fichiers


def main() -> None:
    chemin = Path(sys.argv[1]) if len(sys.argv) > 1 else IMAGE_DEFAUT
    if not chemin.is_file():
        alt = Path(__file__).resolve().parents[1] / "assets" / chemin.name
        if alt.is_file():
            chemin = alt
        else:
            raise SystemExit(f"Image introuvable : {chemin}")

    decouper_grille(chemin, DOSSIER_SORTIE)


if __name__ == "__main__":
    main()
