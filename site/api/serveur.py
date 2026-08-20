"""
API lecture seule pour le site de stats.
Usage (a la racine du projet) : python -m uvicorn site.api.serveur:app --reload --port 8000
Les endpoints sont en GET uniquement.
"""

from collections import defaultdict
from datetime import date
from pathlib import Path
import re
import sqlite3

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from analyse_rencontre import (
    LIGUES_NATIONALES,
    analyser_rencontre,
    lister_equipes_analyse,
    serie_forme_matchs,
)
from correspondances import nom_pour_calendrier, nom_pour_joueurs, normaliser
from photos_joueurs import DOSSIER_PHOTOS, obtenir_photo, photo_en_cache
from sites_officiels import SITES_CHAMPIONNATS, SITES_EQUIPES

RACINE = Path(__file__).resolve().parents[2]
FICHIER_BASE = RACINE / "donnees" / "football.db"
CHAMPIONNATS = (
    "Premier League",
    "La Liga",
    "Bundesliga",
    "Serie A",
    "Ligue 1",
    "Ligue des champions",
)
NOM_LDC = "Ligue des champions"
PHASE_LIGUE = "phase de ligue"
MOTIF_SAISON = re.compile(r"^\d{4}-\d{4}$")

app = FastAPI(title="Stats championnats")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def ouvrir_base():
    if not FICHIER_BASE.exists():
        raise HTTPException(500, "Base introuvable. Lancez python scripts/creer_base.py")
    connexion = sqlite3.connect(FICHIER_BASE)
    connexion.row_factory = sqlite3.Row
    return connexion


def verifier_filtres(championnat: str, saison: str):
    if championnat not in CHAMPIONNATS:
        raise HTTPException(400, "Championnat inconnu")
    if not MOTIF_SAISON.match(saison):
        raise HTTPException(400, "Saison invalide")


def limiter_texte(valeur: str, taille=80):
    texte = (valeur or "").strip()
    if not texte or len(texte) > taille:
        raise HTTPException(400, "Nom invalide")
    return texte


def infos_site_equipe(connexion, nom_equipe):
    vide = {"nom_officiel": "", "url_site": "", "url_logo": "", "stade": ""}
    try:
        ligne = connexion.execute(
            """
            SELECT nom_officiel, url_site, url_logo, stade
            FROM sites_equipes
            WHERE equipe = ?
            """,
            (nom_equipe,),
        ).fetchone()
    except sqlite3.OperationalError:
        ligne = None
    data = dict(ligne) if ligne else vide.copy()
    if not data.get("url_site"):
        data["url_site"] = SITES_EQUIPES.get(nom_equipe, "")
    # Eviter une page feminine / mauvaise URL renvoyee par l'annuaire
    if nom_equipe in SITES_EQUIPES:
        data["url_site"] = SITES_EQUIPES[nom_equipe]
    return data


def infos_championnat(nom):
    fiche = SITES_CHAMPIONNATS.get(nom, {})
    return {
        "nom": nom,
        "url_site": fiche.get("url_site", ""),
        "nom_affichage": fiche.get("nom_affichage", nom),
    }


def lignes_dict(curseur):
    return [dict(ligne) for ligne in curseur.fetchall()]


def matchs_classement(matchs, championnat):
    """LDC : uniquement la phase de ligue (pas les barrages ni l'elimination)."""
    if championnat != NOM_LDC:
        return matchs
    if not any((m.get("phase") or "").strip() for m in matchs):
        return matchs
    return [m for m in matchs if (m.get("phase") or "").strip() == PHASE_LIGUE]


def calculer_classement(matchs):
    stats = defaultdict(
        lambda: {"j": 0, "v": 0, "n": 0, "d": 0, "bp": 0, "bc": 0, "pts": 0}
    )

    def ajouter(equipe, bp, bc, pts, v, n, d):
        ligne = stats[equipe]
        ligne["j"] += 1
        ligne["v"] += v
        ligne["n"] += n
        ligne["d"] += d
        ligne["bp"] += bp
        ligne["bc"] += bc
        ligne["pts"] += pts

    for match in matchs:
        domicile = match["domicile"]
        exterieur = match["exterieur"]
        if match["buts_domicile"] is None or match["buts_exterieur"] is None:
            continue
        bp = int(match["buts_domicile"])
        bc = int(match["buts_exterieur"])
        if match["resultat"] == "H":
            ajouter(domicile, bp, bc, 3, 1, 0, 0)
            ajouter(exterieur, bc, bp, 0, 0, 0, 1)
        elif match["resultat"] == "A":
            ajouter(domicile, bp, bc, 0, 0, 0, 1)
            ajouter(exterieur, bc, bp, 3, 1, 0, 0)
        else:
            ajouter(domicile, bp, bc, 1, 0, 1, 0)
            ajouter(exterieur, bc, bp, 1, 0, 1, 0)

    classement = sorted(
        stats.items(),
        key=lambda item: (item[1]["pts"], item[1]["bp"] - item[1]["bc"], item[1]["bp"]),
        reverse=True,
    )
    resultat = []
    for rang, (equipe, ligne) in enumerate(classement, start=1):
        resultat.append(
            {
                "rang": rang,
                "equipe": equipe,
                "pts": ligne["pts"],
                "j": ligne["j"],
                "v": ligne["v"],
                "n": ligne["n"],
                "d": ligne["d"],
                "bp": ligne["bp"],
                "bc": ligne["bc"],
                "diff": ligne["bp"] - ligne["bc"],
            }
        )
    return resultat


def saisons_disponibles(connexion, championnat=None):
    saisons = set()
    for table in ("matchs", "calendrier"):
        try:
            if championnat:
                curseur = connexion.execute(
                    f"SELECT saison FROM {table} WHERE championnat = ? GROUP BY saison",
                    (championnat,),
                )
            else:
                curseur = connexion.execute(
                    f"SELECT saison FROM {table} GROUP BY saison"
                )
            for row in curseur:
                saisons.add(row[0])
        except sqlite3.OperationalError:
            continue
    return sorted(saisons, reverse=True)


def lire_calendrier(connexion, championnat, saison, equipe=None):
    try:
        if equipe:
            curseur = connexion.execute(
                """
                SELECT date, heure, journee, domicile, exterieur
                FROM calendrier
                WHERE championnat = ? AND saison = ?
                  AND (domicile = ? OR exterieur = ?)
                ORDER BY date, heure
                """,
                (championnat, saison, equipe, equipe),
            )
        else:
            curseur = connexion.execute(
                """
                SELECT date, heure, journee, domicile, exterieur
                FROM calendrier
                WHERE championnat = ? AND saison = ?
                ORDER BY date, heure
                """,
                (championnat, saison),
            )
        return lignes_dict(curseur)
    except sqlite3.OperationalError:
        return []


def ajouter_logos_programme(connexion, programme):
    cache = {}

    def logo(nom):
        if nom not in cache:
            cache[nom] = infos_site_equipe(connexion, nom).get("url_logo", "")
        return cache[nom]

    for match in programme:
        match["url_logo_domicile"] = logo(match["domicile"])
        match["url_logo_exterieur"] = logo(match["exterieur"])
    return programme


def fusionner_programme(joues, avenir):
    vus = set()
    programme = []
    for match in joues:
        vus.add((match["domicile"], match["exterieur"]))
        programme.append(
            {
                "date": match.get("date", ""),
                "heure": match.get("heure") or "",
                "journee": match.get("journee") or "",
                "domicile": match["domicile"],
                "exterieur": match["exterieur"],
                "buts_domicile": match.get("buts_domicile"),
                "buts_exterieur": match.get("buts_exterieur"),
                "joue": True,
                "xg_domicile": None,
                "xg_exterieur": None,
            }
        )
    for match in avenir:
        cle = (match["domicile"], match["exterieur"])
        if cle in vus:
            continue
        vus.add(cle)
        programme.append(
            {
                "date": match.get("date", ""),
                "heure": match.get("heure") or "",
                "journee": match.get("journee") or "",
                "domicile": match["domicile"],
                "exterieur": match["exterieur"],
                "buts_domicile": None,
                "buts_exterieur": None,
                "joue": False,
                "xg_domicile": None,
                "xg_exterieur": None,
            }
        )
    programme.sort(key=lambda m: (m["date"] or "", m["heure"] or "", m["domicile"]))
    return programme


def joindre_xg(connexion, championnat, saison, matchs):
    """Ajoute xg_domicile / xg_exterieur via matchs_xg (noms Understat)."""
    if not matchs:
        return matchs
    try:
        lignes = connexion.execute(
            """
            SELECT date, domicile, exterieur, xg_domicile, xg_exterieur
            FROM matchs_xg
            WHERE championnat = ? AND saison = ?
            """,
            (championnat, saison),
        ).fetchall()
    except sqlite3.OperationalError:
        for match in matchs:
            match.setdefault("xg_domicile", None)
            match.setdefault("xg_exterieur", None)
        return matchs
    noms = []
    vus = set()
    par_date = {}
    par_paire = {}
    for ligne in lignes:
        for nom in (ligne["domicile"], ligne["exterieur"]):
            if nom not in vus:
                vus.add(nom)
                noms.append(nom)
        xg_d = (
            None
            if ligne["xg_domicile"] is None
            else round(float(ligne["xg_domicile"]), 2)
        )
        xg_e = (
            None
            if ligne["xg_exterieur"] is None
            else round(float(ligne["xg_exterieur"]), 2)
        )
        couple = (xg_d, xg_e)
        par_date[(ligne["date"], ligne["domicile"], ligne["exterieur"])] = couple
        par_paire[(ligne["domicile"], ligne["exterieur"])] = couple
    for match in matchs:
        nom_d = nom_pour_joueurs(match["domicile"], noms)
        nom_e = nom_pour_joueurs(match["exterieur"], noms)
        couple = par_date.get((match.get("date"), nom_d, nom_e))
        if not couple:
            couple = par_paire.get((nom_d, nom_e))
        if couple:
            match["xg_domicile"], match["xg_exterieur"] = couple
        else:
            match["xg_domicile"] = None
            match["xg_exterieur"] = None
    return matchs


LIMITE_EQUIPE = 8
LIMITE_LIGUE = 10


def resoudre_nom_equipe(nom, matchs):
    """Ath Madrid, Atletico Madrid, Atl. Madrid -> nom du calendrier."""
    nom = (nom or "").strip()
    if not nom:
        return ""
    connus = []
    vus = set()
    for match in matchs:
        for cote in (match.get("domicile"), match.get("exterieur")):
            if cote and cote not in vus:
                vus.add(cote)
                connus.append(cote)
    if nom in vus:
        return nom
    alias = nom_pour_calendrier(nom, connus)
    if alias in vus:
        return alias
    cible = normaliser(nom)
    if len(cible) >= 4:
        for connu in connus:
            if normaliser(connu) == cible:
                return connu
    return nom


def filtrer_matchs_a_venir(programme, aujourd_hui):
    return [
        match
        for match in programme
        if not match.get("joue") and (match.get("date") or "") >= aujourd_hui
    ]


def extraire_prochaine_journee(prochains, taille=LIMITE_LIGUE):
    if not prochains:
        return []
    pris = []
    for match in prochains:
        if pris and len(pris) >= taille and match["date"] != pris[-1]["date"]:
            break
        pris.append(match)
    return pris


def annoter_pour_equipe(matchs, nom_equipe):
    annotes = []
    for brut in matchs:
        match = dict(brut)
        if match["domicile"] == nom_equipe:
            match["lieu"] = "Domicile"
            match["adversaire"] = match["exterieur"]
        else:
            match["lieu"] = "Extérieur"
            match["adversaire"] = match["domicile"]
        annotes.append(match)
    return annotes


def joueurs_depuis_ligue(connexion, nom_equipe, saison):
    """Si la LDC n'a pas de joueurs, on reprend ceux du club en ligue nationale."""
    ligues = [nom for nom in CHAMPIONNATS if nom != NOM_LDC]
    places = ", ".join(["?"] * len(ligues))
    noms = [
        row[0]
        for row in connexion.execute(
            f"""
            SELECT DISTINCT equipe FROM joueurs
            WHERE saison = ? AND championnat IN ({places})
            """,
            (saison, *ligues),
        )
    ]
    nom_stats = nom_pour_joueurs(nom_equipe, noms)
    return lignes_dict(
        connexion.execute(
            f"""
            SELECT joueur, poste, matchs, minutes, buts, passes_decisives,
                   tirs, passes_cles, xg, xa, carton_jaune, carton_rouge, equipe
            FROM joueurs
            WHERE saison = ? AND championnat IN ({places})
              AND (equipe = ? OR equipe LIKE ? OR equipe LIKE ?)
            ORDER BY buts DESC, minutes DESC
            """,
            (
                saison,
                *ligues,
                nom_stats,
                nom_stats + ",%",
                "%," + nom_stats,
            ),
        )
    )


def charger_programme_saison(connexion, championnat, saison):
    joues = lignes_dict(
        connexion.execute(
            """
            SELECT date, domicile, exterieur, buts_domicile, buts_exterieur
            FROM matchs
            WHERE championnat = ? AND saison = ?
            ORDER BY date
            """,
            (championnat, saison),
        )
    )
    avenir = lire_calendrier(connexion, championnat, saison)
    programme = fusionner_programme(joues, avenir)
    joindre_xg(connexion, championnat, saison, programme)
    return programme


def saison_avec_joueurs(connexion, championnat):
    try:
        ligne = connexion.execute(
            """
            SELECT saison FROM joueurs
            WHERE championnat = ? AND minutes > 0
            GROUP BY saison
            ORDER BY saison DESC
            LIMIT 1
            """,
            (championnat,),
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    return ligne[0] if ligne else None


def buteurs_par_ligue(connexion):
    resultats = []
    for ligue in LIGUES_NATIONALES:
        saison = saison_avec_joueurs(connexion, ligue)
        joueurs = []
        if saison:
            joueurs = lignes_dict(
                connexion.execute(
                    """
                    SELECT joueur, equipe, poste, matchs, minutes, buts, xg
                    FROM joueurs
                    WHERE championnat = ? AND saison = ? AND minutes > 0
                    ORDER BY buts DESC, minutes DESC
                    LIMIT 3
                    """,
                    (ligue, saison),
                )
            )
            for joueur in joueurs:
                joueur["url_photo"] = photo_en_cache(connexion, joueur["joueur"])
        resultats.append(
            {
                "championnat": ligue,
                "saison": saison or "",
                "joueurs": joueurs,
            }
        )
    return resultats


def choisir_jour_matchs(connexion, aujourd_hui):
    try:
        ligne = connexion.execute(
            """
            SELECT MIN(date) FROM (
                SELECT date FROM matchs WHERE date >= ?
                UNION
                SELECT date FROM calendrier WHERE date >= ?
            )
            """,
            (aujourd_hui, aujourd_hui),
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    return ligne[0] if ligne and ligne[0] else None


def charger_matchs_jour(connexion, jour):
    joues = lignes_dict(
        connexion.execute(
            """
            SELECT date, saison, championnat, domicile, exterieur,
                   buts_domicile, buts_exterieur
            FROM matchs
            WHERE date = ?
            """,
            (jour,),
        )
    )
    try:
        avenir = lignes_dict(
            connexion.execute(
                """
                SELECT date, saison, championnat, heure, journee,
                       domicile, exterieur
                FROM calendrier
                WHERE date = ?
                """,
                (jour,),
            )
        )
    except sqlite3.OperationalError:
        avenir = []
    vus = {}
    programme = []
    for match in joues:
        cle = (match["championnat"], match["domicile"], match["exterieur"])
        item = {
            "date": match["date"],
            "heure": "",
            "journee": "",
            "championnat": match["championnat"],
            "saison": match["saison"],
            "domicile": match["domicile"],
            "exterieur": match["exterieur"],
            "buts_domicile": match.get("buts_domicile"),
            "buts_exterieur": match.get("buts_exterieur"),
            "joue": True,
        }
        vus[cle] = item
        programme.append(item)
    for match in avenir:
        cle = (match["championnat"], match["domicile"], match["exterieur"])
        if cle in vus:
            vus[cle]["heure"] = match.get("heure") or ""
            vus[cle]["journee"] = match.get("journee") or ""
            continue
        programme.append(
            {
                "date": match.get("date", ""),
                "heure": match.get("heure") or "",
                "journee": match.get("journee") or "",
                "championnat": match["championnat"],
                "saison": match["saison"],
                "domicile": match["domicile"],
                "exterieur": match["exterieur"],
                "buts_domicile": None,
                "buts_exterieur": None,
                "joue": False,
            }
        )
    programme.sort(
        key=lambda m: (m.get("heure") or "", m["championnat"], m["domicile"])
    )
    ajouter_logos_programme(connexion, programme)
    return programme


@app.get("/api/accueil")
def accueil():
    connexion = ouvrir_base()
    try:
        aujourd_hui = date.today().isoformat()
        jour = choisir_jour_matchs(connexion, aujourd_hui)
        matchs_jour = charger_matchs_jour(connexion, jour) if jour else []
        return {
            "championnats": [infos_championnat(nom) for nom in CHAMPIONNATS],
            "saisons": saisons_disponibles(connexion),
            "jour": jour or aujourd_hui,
            "matchs_jour": matchs_jour,
            "buteurs": buteurs_par_ligue(connexion),
        }
    finally:
        connexion.close()


@app.get("/api/classement")
def classement(
    championnat: str = Query(...),
    saison: str = Query(...),
):
    verifier_filtres(championnat, saison)
    connexion = ouvrir_base()
    try:
        try:
            matchs = lignes_dict(
                connexion.execute(
                    """
                    SELECT date, domicile, exterieur, buts_domicile, buts_exterieur, resultat, phase
                    FROM matchs
                    WHERE championnat = ? AND saison = ?
                    """,
                    (championnat, saison),
                )
            )
        except sqlite3.OperationalError:
            matchs = lignes_dict(
                connexion.execute(
                    """
                    SELECT date, domicile, exterieur, buts_domicile, buts_exterieur, resultat
                    FROM matchs
                    WHERE championnat = ? AND saison = ?
                    """,
                    (championnat, saison),
                )
            )
        classement = calculer_classement(matchs_classement(matchs, championnat))
        for ligne in classement:
            ligne["forme"] = serie_forme_matchs(matchs, ligne["equipe"])
            ligne.update(infos_site_equipe(connexion, ligne["equipe"]))
        return {
            "classement": classement,
            "championnat": infos_championnat(championnat),
            "saisons": saisons_disponibles(connexion, championnat),
            "format": "phase_de_ligue" if championnat == NOM_LDC else "ligue",
        }
    finally:
        connexion.close()


@app.get("/api/calendrier")
def calendrier_api(
    championnat: str = Query(...),
    saison: str = Query(...),
):
    verifier_filtres(championnat, saison)
    connexion = ouvrir_base()
    try:
        programme = charger_programme_saison(connexion, championnat, saison)
        ajouter_logos_programme(connexion, programme)
        return {
            "programme": programme,
            "championnat": infos_championnat(championnat),
            "saison": saison,
            "saisons": saisons_disponibles(connexion, championnat),
            "format": "phase_de_ligue" if championnat == NOM_LDC else "ligue",
        }
    finally:
        connexion.close()


@app.get("/api/equipe")
def fiche_equipe(
    championnat: str = Query(...),
    saison: str = Query(...),
    equipe: str = Query(...),
):
    verifier_filtres(championnat, saison)
    nom_matchs = limiter_texte(equipe)
    connexion = ouvrir_base()
    try:
        matchs = lignes_dict(
            connexion.execute(
                """
                SELECT date, domicile, exterieur, buts_domicile, buts_exterieur,
                       resultat, tirs_domicile, tirs_exterieur,
                       tirs_cadres_domicile, tirs_cadres_exterieur,
                       jaunes_domicile, jaunes_exterieur,
                       rouges_domicile, rouges_exterieur
                FROM matchs
                WHERE championnat = ? AND saison = ?
                  AND (domicile = ? OR exterieur = ?)
                ORDER BY date
                """,
                (championnat, saison, nom_matchs, nom_matchs),
            )
        )
        for match in matchs:
            match["joue"] = True
            match["heure"] = match.get("heure") or ""
        vus = {(m["domicile"], m["exterieur"]) for m in matchs}
        for ligne in lire_calendrier(connexion, championnat, saison, nom_matchs):
            cle = (ligne["domicile"], ligne["exterieur"])
            if cle in vus:
                continue
            vus.add(cle)
            matchs.append(
                {
                    "date": ligne["date"],
                    "heure": ligne.get("heure") or "",
                    "domicile": ligne["domicile"],
                    "exterieur": ligne["exterieur"],
                    "buts_domicile": None,
                    "buts_exterieur": None,
                    "resultat": None,
                    "tirs_domicile": None,
                    "tirs_exterieur": None,
                    "tirs_cadres_domicile": None,
                    "tirs_cadres_exterieur": None,
                    "jaunes_domicile": None,
                    "jaunes_exterieur": None,
                    "rouges_domicile": None,
                    "rouges_exterieur": None,
                    "xg_domicile": None,
                    "xg_exterieur": None,
                    "joue": False,
                }
            )
        matchs.sort(key=lambda m: (m["date"] or "", m.get("heure") or ""))
        joindre_xg(connexion, championnat, saison, matchs)
        ajouter_logos_programme(connexion, matchs)
        noms_understat = [
            row[0]
            for row in connexion.execute(
                """
                SELECT DISTINCT equipe FROM joueurs
                WHERE championnat = ? AND saison = ?
                """,
                (championnat, saison),
            )
        ]
        nom_stats = nom_pour_joueurs(nom_matchs, noms_understat)
        joueurs = lignes_dict(
            connexion.execute(
                """
                SELECT joueur, poste, matchs, minutes, buts, passes_decisives,
                       tirs, passes_cles, xg, xa, carton_jaune, carton_rouge, equipe
                FROM joueurs
                WHERE championnat = ? AND saison = ?
                  AND (equipe = ? OR equipe LIKE ? OR equipe LIKE ?)
                ORDER BY buts DESC, minutes DESC
                """,
                (
                    championnat,
                    saison,
                    nom_stats,
                    nom_stats + ",%",
                    "%," + nom_stats,
                ),
            )
        )
        if not joueurs and championnat == NOM_LDC:
            joueurs = joueurs_depuis_ligue(connexion, nom_matchs, saison)
        for joueur in joueurs:
            joueur["url_photo"] = photo_en_cache(connexion, joueur["joueur"])
        return {
            "equipe": nom_matchs,
            "nom_stats": nom_stats,
            "matchs": matchs,
            "joueurs": joueurs,
            "site": infos_site_equipe(connexion, nom_matchs),
            "championnat": infos_championnat(championnat),
        }
    finally:
        connexion.close()


@app.get("/api/joueur")
def fiche_joueur(nom: str = Query(...), championnat: str | None = None):
    nom_joueur = limiter_texte(nom)
    if championnat and championnat not in CHAMPIONNATS:
        raise HTTPException(400, "Championnat inconnu")
    connexion = ouvrir_base()
    try:
        if championnat:
            saisons = lignes_dict(
                connexion.execute(
                    """
                    SELECT championnat, saison, equipe, poste, matchs, minutes,
                           buts, passes_decisives, tirs, xg, xa,
                           carton_jaune, carton_rouge
                    FROM joueurs
                    WHERE joueur = ? AND championnat = ?
                    ORDER BY saison DESC
                    """,
                    (nom_joueur, championnat),
                )
            )
        else:
            saisons = lignes_dict(
                connexion.execute(
                    """
                    SELECT championnat, saison, equipe, poste, matchs, minutes,
                           buts, passes_decisives, tirs, xg, xa,
                           carton_jaune, carton_rouge
                    FROM joueurs
                    WHERE joueur = ?
                    ORDER BY saison DESC, championnat
                    """,
                    (nom_joueur,),
                )
            )
        if not saisons:
            raise HTTPException(404, "Joueur introuvable")
        club_recent = (saisons[0].get("equipe") or "").split(",")[0]
        return {
            "joueur": nom_joueur,
            "saisons": saisons,
            "url_photo": obtenir_photo(connexion, nom_joueur, club_recent),
        }
    finally:
        connexion.close()


@app.get("/api/recherche")
def recherche(q: str = Query(..., min_length=2, max_length=80)):
    texte = q.strip().replace("%", "").replace("_", "")
    if len(texte) < 2:
        raise HTTPException(400, "Recherche trop courte")
    motif = f"%{texte}%"
    connexion = ouvrir_base()
    try:
        joueurs = lignes_dict(
            connexion.execute(
                """
                SELECT DISTINCT joueur, equipe, championnat, saison, buts
                FROM joueurs
                WHERE joueur LIKE ?
                ORDER BY saison DESC, buts DESC
                LIMIT 20
                """,
                (motif,),
            )
        )
        equipes = lignes_dict(
            connexion.execute(
                """
                SELECT DISTINCT domicile AS equipe, championnat, saison
                FROM matchs
                WHERE domicile LIKE ?
                UNION
                SELECT DISTINCT exterieur, championnat, saison
                FROM matchs
                WHERE exterieur LIKE ?
                ORDER BY saison DESC
                LIMIT 15
                """,
                (motif, motif),
            )
        )
        return {"joueurs": joueurs, "equipes": equipes}
    finally:
        connexion.close()


@app.get("/api/prochains_matchs")
def prochains_matchs_api(
    championnat: str = Query(...),
    saison: str = Query(...),
    equipe: str | None = None,
    limite: int = Query(LIMITE_EQUIPE, ge=1, le=20),
):
    verifier_filtres(championnat, saison)
    connexion = ouvrir_base()
    try:
        aujourd_hui = date.today().isoformat()
        programme = charger_programme_saison(connexion, championnat, saison)
        prochains = filtrer_matchs_a_venir(programme, aujourd_hui)
        nom_equipe = ""
        if equipe:
            nom_equipe = resoudre_nom_equipe(limiter_texte(equipe), programme)
        matchs_equipe = []
        if nom_equipe:
            du_club = [
                match
                for match in prochains
                if match["domicile"] == nom_equipe or match["exterieur"] == nom_equipe
            ]
            matchs_equipe = annoter_pour_equipe(du_club[:limite], nom_equipe)
        matchs_ligue = extraire_prochaine_journee(prochains)
        ajouter_logos_programme(connexion, matchs_equipe)
        ajouter_logos_programme(connexion, matchs_ligue)
        return {
            "equipe": nom_equipe,
            "aujourd_hui": aujourd_hui,
            "matchs_equipe": matchs_equipe,
            "matchs_ligue": matchs_ligue,
            "championnat": infos_championnat(championnat),
            "saison": saison,
        }
    finally:
        connexion.close()


@app.get("/api/equipes-analyse")
def equipes_analyse(
    championnat: str = Query(...),
    saison: str = Query(...),
):
    verifier_filtres(championnat, saison)
    connexion = ouvrir_base()
    try:
        noms = lister_equipes_analyse(connexion, championnat, saison)
        equipes = []
        for nom in noms:
            fiche = infos_site_equipe(connexion, nom)
            equipes.append(
                {
                    "equipe": nom,
                    "url_logo": fiche.get("url_logo", ""),
                }
            )
        return {
            "equipes": equipes,
            "championnat": infos_championnat(championnat),
            "saison": saison,
        }
    finally:
        connexion.close()


@app.get("/api/analyse-rencontre")
def analyse_rencontre_api(
    championnat: str = Query(...),
    saison: str = Query(...),
    domicile: str = Query(...),
    exterieur: str = Query(...),
):
    verifier_filtres(championnat, saison)
    nom_domicile = limiter_texte(domicile)
    nom_exterieur = limiter_texte(exterieur)
    connexion = ouvrir_base()
    try:
        try:
            resultat = analyser_rencontre(
                connexion, championnat, saison, nom_domicile, nom_exterieur
            )
        except ValueError as erreur:
            raise HTTPException(400, str(erreur)) from erreur
        for cote in ("domicile", "exterieur"):
            site = infos_site_equipe(connexion, resultat[cote]["nom"])
            resultat[cote]["url_logo"] = site.get("url_logo", "")
        resultat["championnat"] = infos_championnat(championnat)
        return resultat
    finally:
        connexion.close()


COLONNES_MEILLEURS = {
    "buts": "buts",
    "passes": "passes_decisives",
}


@app.get("/api/meilleurs")
def meilleurs_api(
    championnat: str = Query(...),
    saison: str = Query(...),
    type_classement: str = Query(..., alias="type"),
):
    """Top 20 buteurs ou passeurs. Les dribbles n'existent pas chez Understat."""
    verifier_filtres(championnat, saison)
    type_classement = (type_classement or "").strip()
    if type_classement == "dribbles":
        return {
            "type": type_classement,
            "disponible": False,
            "raison": (
                "Understat ne fournit pas les dribbles. "
                "Il faudrait une autre source (par exemple FBref)."
            ),
            "joueurs": [],
            "championnat": infos_championnat(championnat),
            "saison": saison,
        }
    colonne = COLONNES_MEILLEURS.get(type_classement)
    if not colonne:
        raise HTTPException(400, "Type inconnu (buts, passes ou dribbles)")
    connexion = ouvrir_base()
    try:
        joueurs = lignes_dict(
            connexion.execute(
                f"""
                SELECT joueur, equipe, poste, matchs, minutes,
                       buts, passes_decisives, tirs, xg, xa
                FROM joueurs
                WHERE championnat = ? AND saison = ? AND minutes > 0
                ORDER BY {colonne} DESC, minutes DESC
                LIMIT 20
                """,
                (championnat, saison),
            )
        )
        for joueur in joueurs:
            joueur["url_photo"] = photo_en_cache(connexion, joueur["joueur"])
        return {
            "type": type_classement,
            "disponible": True,
            "joueurs": joueurs,
            "championnat": infos_championnat(championnat),
            "saison": saison,
        }
    finally:
        connexion.close()


DOSSIER_PHOTOS.mkdir(parents=True, exist_ok=True)
app.mount("/photos", StaticFiles(directory=str(DOSSIER_PHOTOS)), name="photos")
