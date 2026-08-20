"""
Telecharge et stocke les portraits des joueurs (fichiers locaux).
Sources publiques alimentees par les clubs (TheSportsDB, Wikipedia).
On n'attaque pas les CMS des 139 sites officiels (Cloudflare / conditions d'usage).
"""

import re
import unicodedata
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parents[2]
DOSSIER_PHOTOS = RACINE / "donnees" / "photos_joueurs"
SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "StatsChampionnats/1.0 (projet local; portraits joueurs)"
    }
)
TAILLE_MAX = 2_000_000


def slug_joueur(nom):
    texte = unicodedata.normalize("NFKD", nom or "")
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = texte.lower()
    texte = re.sub(r"[^a-z0-9]+", "-", texte).strip("-")
    return texte[:80] or "joueur"


def variantes_nom(nom):
    vus = []
    for candidat in (nom, sans_accents(nom)):
        if candidat and candidat not in vus:
            vus.append(candidat)
            yield candidat


def sans_accents(nom):
    texte = unicodedata.normalize("NFKD", nom or "")
    return "".join(c for c in texte if not unicodedata.combining(c))


def garantir_table(connexion):
    connexion.execute(
        """
        CREATE TABLE IF NOT EXISTS photos_joueurs (
            joueur TEXT PRIMARY KEY,
            fichier TEXT,
            source TEXT
        )
        """
    )
    connexion.commit()


def photo_en_cache(connexion, nom):
    garantir_table(connexion)
    ligne = connexion.execute(
        "SELECT fichier FROM photos_joueurs WHERE joueur = ?",
        (nom,),
    ).fetchone()
    if not ligne or not ligne[0]:
        return ""
    chemin = DOSSIER_PHOTOS / ligne[0]
    if chemin.exists():
        return f"/photos/{ligne[0]}"
    return ""


def deja_cherche(connexion, nom):
    garantir_table(connexion)
    ligne = connexion.execute(
        "SELECT joueur FROM photos_joueurs WHERE joueur = ?",
        (nom,),
    ).fetchone()
    return bool(ligne)


def enregistrer(connexion, nom, fichier, source):
    garantir_table(connexion)
    connexion.execute(
        "INSERT OR REPLACE INTO photos_joueurs (joueur, fichier, source) VALUES (?, ?, ?)",
        (nom, fichier, source),
    )
    connexion.commit()


def telecharger_image(url, destination):
    if not url or not url.startswith("https://"):
        return False
    try:
        reponse = SESSION.get(url, timeout=10, stream=True)
        reponse.raise_for_status()
        type_media = (reponse.headers.get("Content-Type") or "").split(";")[0]
        if not type_media.startswith("image/"):
            return False
        contenu = reponse.content[: TAILLE_MAX + 1]
        if not contenu or len(contenu) > TAILLE_MAX:
            return False
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(contenu)
        return True
    except requests.RequestException:
        return False


def url_thesportsdb(nom, equipe=""):
    for variante in variantes_nom(nom):
        try:
            reponse = SESSION.get(
                "https://www.thesportsdb.com/api/v1/json/3/searchplayers.php",
                params={"p": variante},
                timeout=10,
            )
            reponse.raise_for_status()
            joueurs = (reponse.json() or {}).get("player") or []
        except requests.RequestException:
            continue
        nom_cible = sans_accents(nom).lower()
        club_cible = sans_accents(equipe).lower()
        for j in joueurs:
            sport = (j.get("strSport") or "").lower()
            if sport and sport not in ("soccer", "association football"):
                continue
            nom_api = sans_accents(j.get("strPlayer") or "").lower()
            if nom_cible not in nom_api and nom_api not in nom_cible:
                continue
            if club_cible:
                club = sans_accents(j.get("strTeam") or "").lower()
                if club and club_cible[:6] not in club and club[:6] not in club_cible:
                    if nom_api != nom_cible:
                        continue
            for cle in ("strCutout", "strThumb", "strRender"):
                url = j.get(cle) or ""
                if url.startswith("http"):
                    return url.replace("http://", "https://")
    return ""


def url_wikipedia(nom, langue="en"):
    hote = f"https://{langue}.wikipedia.org/w/api.php"
    suffixe = "footballer" if langue == "en" else "footballeur"
    try:
        recherche = SESSION.get(
            hote,
            params={
                "action": "query",
                "list": "search",
                "srsearch": f"{nom} {suffixe}",
                "format": "json",
                "srlimit": 1,
            },
            timeout=10,
        )
        recherche.raise_for_status()
        resultats = (recherche.json().get("query") or {}).get("search") or []
        if not resultats:
            return ""
        titre = resultats[0]["title"]
        visuel = SESSION.get(
            hote,
            params={
                "action": "query",
                "titles": titre,
                "prop": "pageimages",
                "pithumbsize": 400,
                "format": "json",
            },
            timeout=10,
        )
        visuel.raise_for_status()
        pages = (visuel.json().get("query") or {}).get("pages") or {}
        for page in pages.values():
            source = ((page.get("thumbnail") or {}).get("source")) or ""
            if source.startswith("http"):
                return source.replace("http://", "https://")
    except requests.RequestException:
        return ""
    return ""


def obtenir_photo(connexion, nom, equipe=""):
    deja = photo_en_cache(connexion, nom)
    if deja:
        return deja
    if deja_cherche(connexion, nom):
        return ""
    slug = slug_joueur(nom)
    for source, chercheur in (
        ("thesportsdb", lambda: url_thesportsdb(nom, equipe)),
        ("wikipedia-en", lambda: url_wikipedia(nom, "en")),
        ("wikipedia-fr", lambda: url_wikipedia(nom, "fr")),
    ):
        url = chercheur()
        if not url:
            continue
        extension = ".png" if ".png" in url.lower() else ".jpg"
        fichier = f"{slug}{extension}"
        destination = DOSSIER_PHOTOS / fichier
        if telecharger_image(url, destination):
            enregistrer(connexion, nom, fichier, source)
            return f"/photos/{fichier}"
    enregistrer(connexion, nom, "", "aucun")
    return ""
