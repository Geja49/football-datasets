"""
Enrichit les portraits manquants (TheSportsDB + Wikipedia).

Batch raisonnable : top buteurs sans photo, sans scrape de sites clubs.
Usage : python scripts/enrichir_photos_joueurs.py [--limite 40]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "site" / "api"))

from photos_joueurs import obtenir_photo, photo_en_cache  # noqa: E402

FICHIER_BASE = RACINE / "donnees" / "football.db"
PAUSE_S = 0.7


def lister_cibles(connexion, limite):
    """Joueurs les plus buteurs sans fichier photo utilisable."""
    lignes = connexion.execute(
        """
        SELECT j.joueur, MAX(j.equipe) AS equipe, SUM(j.buts) AS buts
        FROM joueurs j
        LEFT JOIN photos_joueurs p ON p.joueur = j.joueur
        WHERE (p.fichier IS NULL OR p.fichier = '')
        GROUP BY j.joueur
        ORDER BY buts DESC
        LIMIT ?
        """,
        (limite,),
    ).fetchall()
    return [(row[0], (row[1] or "").split(",")[0].strip()) for row in lignes]


def main():
    parser = argparse.ArgumentParser(description="Enrichir photos joueurs")
    parser.add_argument("--limite", type=int, default=40)
    args = parser.parse_args()
    if not FICHIER_BASE.exists():
        print("Base introuvable. Lancez scripts/creer_base.py")
        return
    connexion = sqlite3.connect(FICHIER_BASE)
    connexion.row_factory = sqlite3.Row
    cibles = lister_cibles(connexion, max(1, min(args.limite, 80)))
    print(f"Enrichissement photos : {len(cibles)} joueurs (max {args.limite})")
    ok = 0
    for i, (nom, equipe) in enumerate(cibles, 1):
        if photo_en_cache(connexion, nom):
            print(f"  [{i}] {nom} : deja en cache")
            continue
        # Retente meme apres un echec precedent (fichier vide en base).
        url = obtenir_photo(connexion, nom, equipe, forcer=True)
        if url:
            ok += 1
            print(f"  [{i}] {nom} -> {url}")
        else:
            print(f"  [{i}] {nom} : aucune source")
        time.sleep(PAUSE_S)
    print(f"Termine : {ok}/{len(cibles)} nouvelles photos")
    connexion.close()


if __name__ == "__main__":
    main()
