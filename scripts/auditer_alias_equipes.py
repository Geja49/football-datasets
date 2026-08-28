"""
Audit des correspondances de noms d'equipes (calendrier vs matchs vs ClubElo).

Usage (racine du projet) :
    python scripts/auditer_alias_equipes.py
    python scripts/auditer_alias_equipes.py --saison 2026-2027
    python scripts/auditer_alias_equipes.py --csv manquants.csv
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
DOSSIER_API = RACINE / "site" / "api"
FICHIER_FOOTBALL = RACINE / "donnees" / "football.db"
SAISON_DEFAUT = "2026-2027"

if str(DOSSIER_API) not in sys.path:
    sys.path.insert(0, str(DOSSIER_API))

from alias_equipes import normaliser_nom_calendrier  # noqa: E402
from correspondances import alias_noms_equipe, normaliser  # noqa: E402
from elo_clubs import elo_pour_equipe  # noqa: E402


def ouvrir_football(chemin: Path | None = None) -> sqlite3.Connection:
    fichier = chemin or FICHIER_FOOTBALL
    if not fichier.is_file():
        raise FileNotFoundError(f"Base introuvable : {fichier}")
    connexion = sqlite3.connect(str(fichier))
    connexion.row_factory = sqlite3.Row
    return connexion


def _noms_matchs_championnat(
    connexion: sqlite3.Connection,
    championnat: str,
    saison: str,
) -> set[str]:
    """Noms connus dans matchs pour un championnat (saison courante puis historique)."""
    noms: set[str] = set()
    for requete, params in (
        (
            """
            SELECT domicile AS nom FROM matchs
            WHERE championnat = ? AND saison = ?
            UNION
            SELECT exterieur FROM matchs
            WHERE championnat = ? AND saison = ?
            """,
            (championnat, saison, championnat, saison),
        ),
        (
            """
            SELECT domicile AS nom FROM matchs WHERE championnat = ?
            UNION
            SELECT exterieur FROM matchs WHERE championnat = ?
            """,
            (championnat, championnat),
        ),
    ):
        for ligne in connexion.execute(requete, params):
            if ligne["nom"]:
                noms.add(ligne["nom"])
        if noms:
            break
    return noms


def _trouve_dans_matchs(nom_calendrier: str, noms_matchs: set[str]) -> bool:
    norm = normaliser_nom_calendrier(nom_calendrier, noms_matchs)
    aliases = alias_noms_equipe(norm)
    norm_matchs = {normaliser(n) for n in noms_matchs}
    for alias in aliases:
        if alias in noms_matchs or normaliser(alias) in norm_matchs:
            return True
    return False


def _trouve_elo(connexion: sqlite3.Connection, nom_calendrier: str, noms_matchs: set[str]) -> bool:
    norm = normaliser_nom_calendrier(nom_calendrier, noms_matchs)
    aliases = alias_noms_equipe(norm)
    paquet = elo_pour_equipe(connexion, aliases, force_api=False)
    return bool(paquet.get("disponible"))


def lister_clubs_calendrier(connexion: sqlite3.Connection, saison: str) -> list[dict]:
    """Clubs uniques du calendrier avec leur championnat."""
    vus: set[tuple[str, str]] = set()
    lignes: list[dict] = []
    for row in connexion.execute(
        """
        SELECT championnat, domicile AS club FROM calendrier WHERE saison = ?
        UNION
        SELECT championnat, exterieur FROM calendrier WHERE saison = ?
        ORDER BY championnat, club
        """,
        (saison, saison),
    ):
        cle = (row["championnat"], row["club"])
        if cle in vus or not row["club"]:
            continue
        vus.add(cle)
        lignes.append({"championnat": row["championnat"], "club": row["club"]})
    return lignes


def auditer(connexion: sqlite3.Connection, saison: str) -> list[dict]:
    """Retourne les clubs sans correspondance matchs et/ou ClubElo."""
    clubs = lister_clubs_calendrier(connexion, saison)
    noms_par_champ: dict[str, set[str]] = {}
    manquants: list[dict] = []

    for entree in clubs:
        champ = entree["championnat"]
        club = entree["club"]
        if champ not in noms_par_champ:
            noms_par_champ[champ] = _noms_matchs_championnat(connexion, champ, saison)
        noms_matchs = noms_par_champ[champ]
        norm = normaliser_nom_calendrier(club, noms_matchs)
        ok_matchs = _trouve_dans_matchs(club, noms_matchs)
        ok_elo = _trouve_elo(connexion, club, noms_matchs)
        if not ok_matchs or not ok_elo:
            manquants.append(
                {
                    "championnat": champ,
                    "club_calendrier": club,
                    "nom_normalise": norm,
                    "matchs_ok": ok_matchs,
                    "elo_ok": ok_elo,
                }
            )
    return manquants


def afficher_texte(saison: str, manquants: list[dict]) -> None:
    print(f"\nAudit alias equipes — saison {saison}")
    print("=" * 72)
    if not manquants:
        print("Tous les clubs du calendrier ont une correspondance matchs et ClubElo.")
        return
    print(f"{len(manquants)} club(s) sans correspondance complete :\n")
    for ligne in manquants:
        flags = []
        if not ligne["matchs_ok"]:
            flags.append("matchs")
        if not ligne["elo_ok"]:
            flags.append("ClubElo")
        print(
            f"  [{ligne['championnat']}] {ligne['club_calendrier']} "
            f"-> {ligne['nom_normalise']}  (manque : {', '.join(flags)})"
        )


def exporter_csv(chemin: Path, manquants: list[dict]) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", newline="", encoding="utf-8") as fichier:
        writer = csv.DictWriter(
            fichier,
            fieldnames=[
                "championnat",
                "club_calendrier",
                "nom_normalise",
                "matchs_ok",
                "elo_ok",
            ],
        )
        writer.writeheader()
        writer.writerows(manquants)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit des alias equipes (calendrier / matchs / ClubElo)")
    parser.add_argument("--saison", default=SAISON_DEFAUT)
    parser.add_argument("--csv", default=None, help="Export CSV des manquants")
    parser.add_argument(
        "--fichier-football",
        default=None,
        help="Chemin alternatif football.db",
    )
    args = parser.parse_args()

    chemin = Path(args.fichier_football) if args.fichier_football else None
    connexion = ouvrir_football(chemin)
    try:
        manquants = auditer(connexion, args.saison)
    finally:
        connexion.close()

    afficher_texte(args.saison, manquants)
    if args.csv:
        exporter_csv(Path(args.csv), manquants)
        print(f"\nExport CSV : {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
