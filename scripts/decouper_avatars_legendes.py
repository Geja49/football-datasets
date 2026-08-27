"""Découpe une grille d'avatars circulaires en fichiers PNG individuels.

Usage :
    python scripts/decouper_avatars_legendes.py [chemin_image_source]

Par défaut, lit l'image fournie par l'utilisateur et écrit dans
site/frontend/public/avatars/avatar-legende-XX.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

LIGNES = 3
COLONNES = 6
DOSSIER_SORTIE = (
    Path(__file__).resolve().parents[1] / "site" / "frontend" / "public" / "avatars"
)

# Libellés génériques (évite noms de joueurs / marques)
LIBELLES = (
    "Portrait foot 1",
    "Portrait foot 2",
    "Portrait foot 3",
    "Portrait foot 4",
    "Portrait foot 5",
    "Portrait foot 6",
    "Portrait foot 7",
    "Portrait foot 8",
    "Portrait foot 9",
    "Portrait foot 10",
    "Portrait foot 11",
    "Portrait foot 12",
    "Portrait foot 13",
    "Portrait foot 14",
    "Portrait foot 15",
    "Portrait foot 16",
    "Portrait foot 17",
    "Portrait foot 18",
)


def _masque_non_blanc(arr: np.ndarray, seuil: int = 248) -> np.ndarray:
    return (arr[:, :, 0] < seuil) | (arr[:, :, 1] < seuil) | (arr[:, :, 2] < seuil)


def _centre_et_rayon(mask: np.ndarray, x0: int, y0: int) -> tuple[int, int, int]:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        raise ValueError("Cellule vide — badge introuvable")
    cx = x0 + int((xs.min() + xs.max()) // 2)
    cy = y0 + int((ys.min() + ys.max()) // 2)
    rayon = int(max(xs.max() - xs.min(), ys.max() - ys.min()) // 2)
    return cx, cy, rayon


def _rendre_fond_transparent(image: Image.Image, seuil: int = 245) -> Image.Image:
    """Rend transparent le fond blanc autour du badge."""
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
    """Masque les coins carrés restants pour un rendu circulaire propre."""
    rgba = image.convert("RGBA")
    w, h = rgba.size
    cx, cy = w // 2, h // 2
    rayon = min(w, h) // 2 - marge
    masque = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(masque)
    draw.ellipse((cx - rayon, cy - rayon, cx + rayon, cy + rayon), fill=255)
    rgba.putalpha(Image.fromarray(np.minimum(np.array(rgba.split()[3]), np.array(masque))))
    return rgba


def decouper_grille(chemin_source: Path, dossier_sortie: Path) -> list[tuple[str, str]]:
    image = Image.open(chemin_source).convert("RGBA")
    largeur, hauteur = image.size
    arr = np.array(image)
    mask_global = _masque_non_blanc(arr)
    fichiers: list[tuple[str, str]] = []
    index = 0

    dossier_sortie.mkdir(parents=True, exist_ok=True)

    for ligne in range(LIGNES):
        for colonne in range(COLONNES):
            index += 1
            ident = f"avatar-legende-{index:02d}"
            x0 = colonne * largeur // COLONNES
            x1 = (colonne + 1) * largeur // COLONNES
            y0 = ligne * hauteur // LIGNES
            y1 = (ligne + 1) * hauteur // LIGNES

            sous_masque = mask_global[y0:y1, x0:x1]
            cx, cy, rayon = _centre_et_rayon(sous_masque, x0, y0)

            # Carré serré autour du cercle (inclut bordure métallique)
            padding = max(4, rayon // 20)
            taille = (rayon + padding) * 2
            gauche = max(0, cx - rayon - padding)
            haut = max(0, cy - rayon - padding)
            droite = min(largeur, gauche + taille)
            bas = min(hauteur, haut + taille)

            extrait = image.crop((gauche, haut, droite, bas))
            extrait = _rendre_fond_transparent(extrait)
            extrait = _appliquer_masque_cercle(extrait)

            # Normaliser en carré pour affichage cohérent
            cote = max(extrait.size)
            carre = Image.new("RGBA", (cote, cote), (0, 0, 0, 0))
            ox = (cote - extrait.width) // 2
            oy = (cote - extrait.height) // 2
            carre.paste(extrait, (ox, oy), extrait)

            chemin_sortie = dossier_sortie / f"{ident}.png"
            carre.save(chemin_sortie, "PNG", optimize=True)
            fichiers.append((ident, LIBELLES[index - 1]))
            print(f"Écrit {chemin_sortie.name} ({carre.width}x{carre.height})")

    return fichiers


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage : python scripts/decouper_avatars_legendes.py <chemin_image_grille>"
        )
    chemin = Path(sys.argv[1])
    if not chemin.is_file():
        raise SystemExit(f"Image introuvable : {chemin}")

    decouper_grille(chemin, DOSSIER_SORTIE)


if __name__ == "__main__":
    main()
