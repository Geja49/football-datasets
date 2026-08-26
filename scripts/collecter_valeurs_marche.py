"""
Valeurs de marche joueurs depuis le dump communautaire transfermarkt-datasets.

Source (snapshot deja publie, CC0) :
  https://github.com/dcaribou/transfermarkt-datasets
  miroir CSV :
  https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/players.csv.gz
  https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfers.csv.gz
  Kaggle (optionnel) : davidcariboo/player-scores

ATTENTION : dump tiers issu de Transfermarkt (zone grise juridique) ;
licence du repo = CC0, mais ce n'est PAS une source officielle ni a jour live.
INTERDIT : scraper Transfermarkt, transfermarkt-scraper, appels HTTP a transfermarkt.*.

Usage : python scripts/collecter_valeurs_marche.py
"""

from __future__ import annotations

import csv
import gzip
import io
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "site" / "api"))
from correspondances import normaliser

DOSSIER_SORTIE = Path("donnees/cinq_championnats")
FICHIER_JOUEURS_LOCAL = DOSSIER_SORTIE / "joueurs.csv"
FICHIER_VALEURS = DOSSIER_SORTIE / "valeurs_marche_joueurs.csv"
FICHIER_TRANSFERTS = DOSSIER_SORTIE / "transferts_joueurs.csv"
DOSSIER_CACHE = Path("donnees/cache_valeurs_marche")

# Mirror public du dump (pas transfermarkt.*).
URL_JOUEURS = (
    "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/players.csv.gz"
)
URL_TRANSFERTS = (
    "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfers.csv.gz"
)
SOURCE = "dump_transfermarkt_datasets_cc0"
MENTION = "estimation dump public, pas à jour live"
TIMEOUT = 180

COLONNES_VALEURS = [
    "joueur",
    "joueur_dump",
    "age",
    "club_dump",
    "poste",
    "valeur_marche_eur",
    "valeur_max_eur",
    "derniere_saison_dump",
    "id_joueur_dump",
    "qualite_match",
    "source",
    "mention",
]

COLONNES_TRANSFERTS = [
    "joueur",
    "date_transfert",
    "saison_transfert",
    "club_depart",
    "club_arrivee",
    "frais_eur",
    "valeur_marche_eur",
    "id_joueur_dump",
    "source",
]

SESSION = requests.Session()
SESSION.headers.update(
    {"User-Agent": "StatsChampionnats/1.0 (dump public transfermarkt-datasets)"}
)


def normaliser_nom(nom: str) -> str:
    """Normalisation robuste (accents, ponctuation) pour le matching."""
    texte = unicodedata.normalize("NFKD", nom or "")
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    base = normaliser(texte)
    return base or "".join(c for c in texte.lower() if c.isalnum())


def telecharger_csv_gz(url: str, nom_cache: str) -> list[dict]:
    DOSSIER_CACHE.mkdir(parents=True, exist_ok=True)
    chemin = DOSSIER_CACHE / nom_cache
    print(f"  telechargement {url} ...")
    try:
        reponse = SESSION.get(url, timeout=TIMEOUT)
        reponse.raise_for_status()
        chemin.write_bytes(reponse.content)
    except requests.RequestException as exc:
        if chemin.exists():
            print(f"  reseau KO ({exc}), cache local {chemin.name}")
        else:
            raise SystemExit(f"Impossible de telecharger {url}: {exc}") from exc
    brut = chemin.read_bytes()
    try:
        texte = gzip.decompress(brut).decode("utf-8", errors="replace")
    except OSError:
        texte = brut.decode("utf-8", errors="replace")
    return list(csv.DictReader(io.StringIO(texte)))


def lire_noms_understat() -> set[str]:
    if not FICHIER_JOUEURS_LOCAL.exists():
        raise SystemExit(f"Fichier absent : {FICHIER_JOUEURS_LOCAL}")
    noms: set[str] = set()
    with open(FICHIER_JOUEURS_LOCAL, newline="", encoding="utf-8") as f:
        for ligne in csv.DictReader(f):
            nom = (ligne.get("joueur") or "").strip()
            if nom:
                noms.add(nom)
    return noms


def entier_ou_none(valeur) -> int | None:
    if valeur is None or str(valeur).strip() == "":
        return None
    try:
        return int(float(valeur))
    except ValueError:
        return None


def age_depuis_naissance(texte: str, aujourdhui: date | None = None) -> int | None:
    if not texte or not str(texte).strip():
        return None
    brut = str(texte).strip()[:10]
    try:
        naissance = datetime.strptime(brut, "%Y-%m-%d").date()
    except ValueError:
        return None
    ref = aujourdhui or date.today()
    annees = ref.year - naissance.year
    if (ref.month, ref.day) < (naissance.month, naissance.day):
        annees -= 1
    return annees if 10 <= annees <= 60 else None


def score_candidat(ligne: dict) -> tuple:
    """Preferer valeur recente / elevee pour departager homonymes."""
    valeur = entier_ou_none(ligne.get("market_value_in_eur")) or 0
    saison = entier_ou_none(ligne.get("last_season")) or 0
    return (saison, valeur)


def indexer_dump(joueurs_dump: list[dict]) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for ligne in joueurs_dump:
        nom = (ligne.get("name") or "").strip()
        if not nom:
            continue
        cle = normaliser_nom(nom)
        if len(cle) < 3:
            continue
        index.setdefault(cle, []).append(ligne)
    return index


def choisir_candidat(candidats: list[dict]) -> tuple[dict, str]:
    uniques = {c.get("player_id"): c for c in candidats}
    liste = list(uniques.values())
    if len(liste) == 1:
        return liste[0], "exact"
    liste.sort(key=score_candidat, reverse=True)
    return liste[0], "ambigu_meilleur"


def apparier(noms_understat: set[str], index_dump: dict[str, list[dict]]):
    correspondances: dict[str, tuple[dict, str]] = {}
    for nom in noms_understat:
        cle = normaliser_nom(nom)
        candidats = index_dump.get(cle)
        if not candidats:
            continue
        dump, qualite = choisir_candidat(candidats)
        correspondances[nom] = (dump, qualite)
    return correspondances


def ecrire_csv(chemin: Path, colonnes: list[str], lignes: list[dict]):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=colonnes)
        writer.writeheader()
        writer.writerows(lignes)


def construire_valeurs(correspondances: dict) -> list[dict]:
    lignes = []
    for joueur, (dump, qualite) in sorted(correspondances.items()):
        lignes.append(
            {
                "joueur": joueur,
                "joueur_dump": (dump.get("name") or "").strip(),
                "age": age_depuis_naissance(dump.get("date_of_birth") or ""),
                "club_dump": (dump.get("current_club_name") or "").strip(),
                "poste": (dump.get("position") or dump.get("sub_position") or "").strip(),
                "valeur_marche_eur": entier_ou_none(dump.get("market_value_in_eur")),
                "valeur_max_eur": entier_ou_none(
                    dump.get("highest_market_value_in_eur")
                ),
                "derniere_saison_dump": entier_ou_none(dump.get("last_season")),
                "id_joueur_dump": (dump.get("player_id") or "").strip(),
                "qualite_match": qualite,
                "source": SOURCE,
                "mention": MENTION,
            }
        )
    return lignes


def construire_transferts(
    correspondances: dict, transferts_dump: list[dict]
) -> list[dict]:
    ids = {
        (dump.get("player_id") or "").strip(): joueur
        for joueur, (dump, _) in correspondances.items()
        if (dump.get("player_id") or "").strip()
    }
    lignes = []
    for t in transferts_dump:
        pid = (t.get("player_id") or "").strip()
        joueur = ids.get(pid)
        if not joueur:
            continue
        frais = entier_ou_none(t.get("transfer_fee"))
        # Ignorer lignes sans frais ni valeur (souvent 0 / fin de contrat).
        valeur = entier_ou_none(t.get("market_value_in_eur"))
        lignes.append(
            {
                "joueur": joueur,
                "date_transfert": (t.get("transfer_date") or "").strip()[:10],
                "saison_transfert": (t.get("transfer_season") or "").strip(),
                "club_depart": (t.get("from_club_name") or "").strip(),
                "club_arrivee": (t.get("to_club_name") or "").strip(),
                "frais_eur": frais,
                "valeur_marche_eur": valeur,
                "id_joueur_dump": pid,
                "source": SOURCE,
            }
        )
    lignes.sort(key=lambda x: (x["joueur"], x["date_transfert"]), reverse=True)
    return lignes


def main():
    print(
        "Valeurs de marche (dump transfermarkt-datasets CC0, "
        "sans scrape Transfermarkt)..."
    )
    noms = lire_noms_understat()
    print(f"  {len(noms)} joueurs Understat uniques")

    joueurs_dump = telecharger_csv_gz(URL_JOUEURS, "players.csv.gz")
    print(f"  dump joueurs : {len(joueurs_dump)} lignes")
    transferts_dump = telecharger_csv_gz(URL_TRANSFERTS, "transfers.csv.gz")
    print(f"  dump transferts : {len(transferts_dump)} lignes")

    index = indexer_dump(joueurs_dump)
    correspondances = apparier(noms, index)
    valeurs = construire_valeurs(correspondances)
    transferts = construire_transferts(correspondances, transferts_dump)

    ecrire_csv(FICHIER_VALEURS, COLONNES_VALEURS, valeurs)
    ecrire_csv(FICHIER_TRANSFERTS, COLONNES_TRANSFERTS, transferts)

    avec_valeur = sum(1 for v in valeurs if v.get("valeur_marche_eur"))
    exact = sum(1 for v in valeurs if v.get("qualite_match") == "exact")
    print(f"  -> {FICHIER_VALEURS} : {len(valeurs)} matches ({avec_valeur} avec valeur)")
    print(f"     dont {exact} exacts, {len(valeurs) - exact} ambigu_meilleur")
    print(f"  -> {FICHIER_TRANSFERTS} : {len(transferts)} lignes")
    print(f"  couverture : {100.0 * len(valeurs) / max(1, len(noms)):.1f}% des noms Understat")


if __name__ == "__main__":
    main()
