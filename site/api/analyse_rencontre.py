"""
Analyse statistique d'une rencontre a partir de football.db.

Forme, xG, forces/faiblesses et scenario Poisson (buts independants)
commentes en francais. Les cotes (si disponibles) sont ajoutees cote
serveur via cotes.lecture_marche_pour_analyse — pas de tipster.
"""

import math

from correspondances import nom_pour_joueurs

NOM_LDC = "Ligue des champions"
LIGUES_NATIONALES = (
    "Premier League",
    "La Liga",
    "Bundesliga",
    "Serie A",
    "Ligue 1",
)

# Saison trop courte (ex. 2026-2027) : on retombe sur la precedente.
SEUIL_MATCHS_SAISON = 8
# En dessous, trop peu pour un profil : on utilise la moyenne du championnat.
SEUIL_MATCHS_PROFIL = 6
# Ecart de 15 % par rapport a la moyenne pour parler de force / faiblesse.
SEUIL_FORCE = 1.15
SEUIL_FAIBLESSE = 0.85
MAX_BUTS = 8
NB_SCORES = 6
NB_FORME = 5
NB_CONFRONTATIONS = 8
# Match ouvert / fermé : xG total par rapport à la moyenne du championnat.
SEUIL_MATCH_OUVERT = 1.15
SEUIL_MATCH_FERME = 0.85
# Cartons : au moins 3 matchs récents avec jaunes/rouges renseignés.
SEUIL_CARTONS_FORME = 3


def saison_precedente(saison):
    debut = int(saison[:4])
    return f"{debut - 1}-{debut}"


def _flottant(valeur):
    if valeur is None:
        return None
    return float(valeur)


def _arrondi(valeur, decimales=2):
    if valeur is None:
        return None
    return round(float(valeur), decimales)


def _noms_xg(connexion, championnat, saison, nom_matchs):
    """Nom football-data -> nom Understat dans matchs_xg."""
    noms = [
        row[0]
        for row in connexion.execute(
            """
            SELECT DISTINCT equipe FROM (
                SELECT domicile AS equipe FROM matchs_xg
                WHERE championnat = ? AND saison = ?
                UNION
                SELECT exterieur FROM matchs_xg
                WHERE championnat = ? AND saison = ?
            )
            """,
            (championnat, saison, championnat, saison),
        )
    ]
    return nom_pour_joueurs(nom_matchs, noms)


def _xg_du_match(connexion, championnat, saison, nom_domicile, nom_exterieur, date):
    """xG Understat du match, avec mapping des noms football-data."""
    nom_d = _noms_xg(connexion, championnat, saison, nom_domicile)
    nom_e = _noms_xg(connexion, championnat, saison, nom_exterieur)
    ligne = connexion.execute(
        """
        SELECT xg_domicile, xg_exterieur
        FROM matchs_xg
        WHERE championnat = ? AND saison = ?
          AND domicile = ? AND exterieur = ?
          AND date = ?
        """,
        (championnat, saison, nom_d, nom_e, date),
    ).fetchone()
    if not ligne:
        ligne = connexion.execute(
            """
            SELECT xg_domicile, xg_exterieur
            FROM matchs_xg
            WHERE championnat = ? AND saison = ?
              AND domicile = ? AND exterieur = ?
            ORDER BY date DESC
            LIMIT 1
            """,
            (championnat, saison, nom_d, nom_e),
        ).fetchone()
    if not ligne:
        return None, None
    return _arrondi(ligne[0]), _arrondi(ligne[1])


def _compter_xg(connexion, championnat, saison, nom_xg):
    ligne = connexion.execute(
        """
        SELECT COUNT(*) FROM matchs_xg
        WHERE championnat = ? AND saison = ?
          AND (domicile = ? OR exterieur = ?)
        """,
        (championnat, saison, nom_xg, nom_xg),
    ).fetchone()
    return int(ligne[0]) if ligne else 0


def _compter_xg_ligue(connexion, championnat, saison):
    ligne = connexion.execute(
        """
        SELECT COUNT(*) FROM matchs_xg
        WHERE championnat = ? AND saison = ?
        """,
        (championnat, saison),
    ).fetchone()
    return int(ligne[0]) if ligne else 0


def choisir_saison_xg(connexion, championnat, saison, nom_matchs):
    """
    Prefere la saison demandee si l'equipe a assez de matchs xG.
    Sinon la saison precedente (cas 2026-2027 trop pauvre).
    """
    precedente = saison_precedente(saison)
    candidats = [saison]
    if precedente != saison:
        candidats.append(precedente)

    meilleur = saison
    meilleur_nb = 0
    nom_retenu = nom_matchs
    for candidature in candidats:
        nom_xg = _noms_xg(connexion, championnat, candidature, nom_matchs)
        nb = _compter_xg(connexion, championnat, candidature, nom_xg)
        assez = nb >= SEUIL_MATCHS_SAISON
        if assez:
            return candidature, nom_xg, nb
        if nb > meilleur_nb:
            meilleur = candidature
            meilleur_nb = nb
            nom_retenu = nom_xg
    return meilleur, nom_retenu, meilleur_nb


def choisir_saison_ligue(connexion, championnat, saison):
    """Moyennes du championnat : saison actuelle si assez de matchs, sinon precedente."""
    if _compter_xg_ligue(connexion, championnat, saison) >= 50:
        return saison
    precedente = saison_precedente(saison)
    if _compter_xg_ligue(connexion, championnat, precedente) > 0:
        return precedente
    if _compter_matchs_ligue(connexion, championnat, saison) >= 50:
        return saison
    if _compter_matchs_ligue(connexion, championnat, precedente) > 0:
        return precedente
    return saison


def _compter_matchs_ligue(connexion, championnat, saison):
    ligne = connexion.execute(
        """
        SELECT COUNT(*) FROM matchs
        WHERE championnat = ? AND saison = ?
          AND buts_domicile IS NOT NULL AND buts_exterieur IS NOT NULL
        """,
        (championnat, saison),
    ).fetchone()
    return int(ligne[0]) if ligne else 0


def _moyennes_xg_ligue(connexion, championnat, saison):
    ligne = connexion.execute(
        """
        SELECT AVG(xg_domicile), AVG(xg_exterieur), COUNT(*)
        FROM matchs_xg
        WHERE championnat = ? AND saison = ?
        """,
        (championnat, saison),
    ).fetchone()
    if int(ligne[2] or 0) > 0:
        return {
            "xg_domicile": _flottant(ligne[0]) or 1.4,
            "xg_exterieur": _flottant(ligne[1]) or 1.1,
            "nb": int(ligne[2] or 0),
        }
    buts = connexion.execute(
        """
        SELECT AVG(buts_domicile), AVG(buts_exterieur), COUNT(*)
        FROM matchs
        WHERE championnat = ? AND saison = ?
          AND buts_domicile IS NOT NULL AND buts_exterieur IS NOT NULL
        """,
        (championnat, saison),
    ).fetchone()
    return {
        "xg_domicile": _flottant(buts[0]) or 1.4,
        "xg_exterieur": _flottant(buts[1]) or 1.1,
        "nb": int(buts[2] or 0),
    }


def _moyennes_matchs_ligue(connexion, championnat, saison):
    ligne = connexion.execute(
        """
        SELECT
            AVG(tirs_cadres_domicile), AVG(tirs_cadres_exterieur),
            AVG(tirs_domicile), AVG(tirs_exterieur),
            AVG(jaunes_domicile), AVG(jaunes_exterieur),
            AVG(rouges_domicile), AVG(rouges_exterieur)
        FROM matchs
        WHERE championnat = ? AND saison = ?
          AND tirs_cadres_domicile IS NOT NULL
        """,
        (championnat, saison),
    ).fetchone()
    return {
        "tirs_cadres_domicile": _flottant(ligne[0]) or 4.5,
        "tirs_cadres_exterieur": _flottant(ligne[1]) or 3.8,
        "tirs_domicile": _flottant(ligne[2]) or 12.0,
        "tirs_exterieur": _flottant(ligne[3]) or 10.0,
        "jaunes_domicile": _flottant(ligne[4]) or 2.0,
        "jaunes_exterieur": _flottant(ligne[5]) or 2.2,
        "rouges_domicile": _flottant(ligne[6]) or 0.1,
        "rouges_exterieur": _flottant(ligne[7]) or 0.1,
    }


def _profil_xg(connexion, championnat, saison, nom_xg, a_domicile):
    if a_domicile:
        ligne = connexion.execute(
            """
            SELECT AVG(xg_domicile), AVG(xg_exterieur), COUNT(*)
            FROM matchs_xg
            WHERE championnat = ? AND saison = ? AND domicile = ?
            """,
            (championnat, saison, nom_xg),
        ).fetchone()
    else:
        ligne = connexion.execute(
            """
            SELECT AVG(xg_exterieur), AVG(xg_domicile), COUNT(*)
            FROM matchs_xg
            WHERE championnat = ? AND saison = ? AND exterieur = ?
            """,
            (championnat, saison, nom_xg),
        ).fetchone()
    return {
        "xg_marques": _flottant(ligne[0]),
        "xg_encaisses": _flottant(ligne[1]),
        "nb": int(ligne[2] or 0),
    }


def _profil_buts(connexion, championnat, saison, nom_matchs, a_domicile):
    """Sans xG : on utilise les buts reels (historique LDC)."""
    if a_domicile:
        ligne = connexion.execute(
            """
            SELECT AVG(buts_domicile), AVG(buts_exterieur), COUNT(*)
            FROM matchs
            WHERE championnat = ? AND saison = ? AND domicile = ?
              AND buts_domicile IS NOT NULL
            """,
            (championnat, saison, nom_matchs),
        ).fetchone()
    else:
        ligne = connexion.execute(
            """
            SELECT AVG(buts_exterieur), AVG(buts_domicile), COUNT(*)
            FROM matchs
            WHERE championnat = ? AND saison = ? AND exterieur = ?
              AND buts_exterieur IS NOT NULL
            """,
            (championnat, saison, nom_matchs),
        ).fetchone()
    return {
        "xg_marques": _flottant(ligne[0]),
        "xg_encaisses": _flottant(ligne[1]),
        "nb": int(ligne[2] or 0),
    }


def xg_depuis_ligue_nationale(connexion, nom_matchs, saison):
    """Club LDC aussi present dans une des 5 ligues : on reprend ses xG."""
    precedente = saison_precedente(saison)
    for ligue in LIGUES_NATIONALES:
        for candidature in (saison, precedente):
            nom_xg = _noms_xg(connexion, ligue, candidature, nom_matchs)
            nb = _compter_xg(connexion, ligue, candidature, nom_xg)
            if nb >= SEUIL_MATCHS_SAISON:
                return ligue, candidature, nom_xg, nb
    return None


def _profil_matchs(connexion, championnat, saison, nom_matchs, a_domicile):
    if a_domicile:
        ligne = connexion.execute(
            """
            SELECT
                AVG(tirs_cadres_domicile), AVG(tirs_domicile),
                AVG(jaunes_domicile), AVG(rouges_domicile), COUNT(*)
            FROM matchs
            WHERE championnat = ? AND saison = ? AND domicile = ?
              AND tirs_cadres_domicile IS NOT NULL
            """,
            (championnat, saison, nom_matchs),
        ).fetchone()
    else:
        ligne = connexion.execute(
            """
            SELECT
                AVG(tirs_cadres_exterieur), AVG(tirs_exterieur),
                AVG(jaunes_exterieur), AVG(rouges_exterieur), COUNT(*)
            FROM matchs
            WHERE championnat = ? AND saison = ? AND exterieur = ?
              AND tirs_cadres_exterieur IS NOT NULL
            """,
            (championnat, saison, nom_matchs),
        ).fetchone()
    return {
        "tirs_cadres": _flottant(ligne[0]),
        "tirs": _flottant(ligne[1]),
        "jaunes": _flottant(ligne[2]),
        "rouges": _flottant(ligne[3]),
        "nb": int(ligne[4] or 0),
    }


def _taux_ou_moyenne(valeur, nb, moyenne):
    """Si trop peu de matchs, on prend la moyenne du championnat."""
    if valeur is None or nb < SEUIL_MATCHS_PROFIL:
        return moyenne, True
    return valeur, False


def forme_recente(connexion, championnat, nom_matchs):
    """5 derniers matchs joues, toutes saisons confondues (plus recent d'abord)."""
    lignes = connexion.execute(
        """
        SELECT date, saison, domicile, exterieur,
               buts_domicile, buts_exterieur, resultat,
               jaunes_domicile, jaunes_exterieur,
               rouges_domicile, rouges_exterieur
        FROM matchs
        WHERE championnat = ?
          AND (domicile = ? OR exterieur = ?)
          AND buts_domicile IS NOT NULL
          AND buts_exterieur IS NOT NULL
        ORDER BY date DESC
        LIMIT ?
        """,
        (championnat, nom_matchs, nom_matchs, NB_FORME),
    ).fetchall()

    serie = []
    buts_pour = 0
    buts_contre = 0
    jaunes = 0
    rouges = 0
    nb_avec_cartons = 0
    matchs = []
    for ligne in lignes:
        est_domicile = ligne["domicile"] == nom_matchs
        bp = int(ligne["buts_domicile"] if est_domicile else ligne["buts_exterieur"])
        bc = int(ligne["buts_exterieur"] if est_domicile else ligne["buts_domicile"])
        buts_pour += bp
        buts_contre += bc
        j = ligne["jaunes_domicile"] if est_domicile else ligne["jaunes_exterieur"]
        r = ligne["rouges_domicile"] if est_domicile else ligne["rouges_exterieur"]
        if j is not None:
            jaunes += int(j)
            rouges += int(r or 0)
            nb_avec_cartons += 1
        if bp > bc:
            issue = "V"
        elif bp < bc:
            issue = "D"
        else:
            issue = "N"
        serie.append(issue)
        matchs.append(
            {
                "date": ligne["date"],
                "saison": ligne["saison"],
                "domicile": ligne["domicile"],
                "exterieur": ligne["exterieur"],
                "score": f"{ligne['buts_domicile']}-{ligne['buts_exterieur']}",
                "issue": issue,
                "jaunes": int(j) if j is not None else None,
                "rouges": int(r) if r is not None else None,
            }
        )
    victoires = serie.count("V")
    nuls = serie.count("N")
    defaites = serie.count("D")
    return {
        "serie": serie,
        "resume": f"{victoires}V {nuls}N {defaites}D" if serie else "aucun match",
        "buts_pour": buts_pour,
        "buts_contre": buts_contre,
        "jaunes": jaunes if nb_avec_cartons else None,
        "rouges": rouges if nb_avec_cartons else None,
        "nb_avec_cartons": nb_avec_cartons,
        "jaunes_par_match": _arrondi(jaunes / nb_avec_cartons, 1) if nb_avec_cartons else None,
        "rouges_par_match": _arrondi(rouges / nb_avec_cartons, 2) if nb_avec_cartons else None,
        "matchs": matchs,
    }


def serie_forme_matchs(matchs, nom_equipe):
    """5 derniers matchs de la liste déjà chargée (plus récent d'abord)."""
    joues = [
        match
        for match in matchs
        if match.get("buts_domicile") is not None
        and match.get("buts_exterieur") is not None
        and (match.get("domicile") == nom_equipe or match.get("exterieur") == nom_equipe)
    ]
    joues.sort(key=lambda m: m.get("date") or "", reverse=True)
    serie = []
    for match in joues[:NB_FORME]:
        est_domicile = match["domicile"] == nom_equipe
        bp = int(match["buts_domicile"] if est_domicile else match["buts_exterieur"])
        bc = int(match["buts_exterieur"] if est_domicile else match["buts_domicile"])
        if bp > bc:
            serie.append("V")
        elif bp < bc:
            serie.append("D")
        else:
            serie.append("N")
    return serie


def _phrases(profil, moyennes, a_domicile, donnees_limitees):
    lieu = "à domicile" if a_domicile else "à l'extérieur"
    suffixe = "domicile" if a_domicile else "exterieur"
    forces = []
    faiblesses = []

    if donnees_limitees:
        return {
            "forces": [
                f"Pas assez de matchs {lieu} pour un profil fiable : "
                "la moyenne du championnat est utilisée pour la projection."
            ],
            "faiblesses": [
                "Échantillon trop petit : pas de faiblesse statistique solide à retenir."
            ],
        }

    xg_m = profil["xg_marques"]
    xg_e = profil["xg_encaisses"]
    moy_m = moyennes["xg_" + suffixe]
    moy_e = moyennes["xg_encaisses_" + suffixe]

    if xg_m >= moy_m * SEUIL_FORCE:
        forces.append(
            f"Attaque {lieu} productive : {xg_m:.2f} xG marqués par match "
            f"(moyenne {moy_m:.2f})."
        )
    elif xg_m <= moy_m * SEUIL_FAIBLESSE:
        faiblesses.append(
            f"Attaque {lieu} en retrait : {xg_m:.2f} xG marqués par match "
            f"(moyenne {moy_m:.2f})."
        )

    if xg_e <= moy_e * SEUIL_FAIBLESSE:
        forces.append(
            f"Défense {lieu} solide : seulement {xg_e:.2f} xG encaissés "
            f"(moyenne {moy_e:.2f})."
        )
    elif xg_e >= moy_e * SEUIL_FORCE:
        faiblesses.append(
            f"Défense {lieu} perméable : {xg_e:.2f} xG encaissés "
            f"(moyenne {moy_e:.2f})."
        )

    tc = profil["tirs_cadres"]
    moy_tc = moyennes["tirs_cadres_" + suffixe]
    if tc >= moy_tc * SEUIL_FORCE:
        forces.append(
            f"Beaucoup de tirs cadrés {lieu} ({tc:.1f} par match, moyenne {moy_tc:.1f})."
        )
    elif tc <= moy_tc * SEUIL_FAIBLESSE:
        faiblesses.append(
            f"Peu de tirs cadrés {lieu} ({tc:.1f} par match, moyenne {moy_tc:.1f})."
        )

    jaunes = profil["jaunes"]
    moy_j = moyennes["jaunes_" + suffixe]
    if jaunes <= moy_j * SEUIL_FAIBLESSE:
        forces.append(
            f"Peu de cartons jaunes {lieu} ({jaunes:.1f} par match, moyenne {moy_j:.1f})."
        )
    elif jaunes >= moy_j * SEUIL_FORCE:
        faiblesses.append(
            f"Beaucoup de cartons jaunes {lieu} ({jaunes:.1f} par match, moyenne {moy_j:.1f})."
        )

    rouges = profil.get("rouges")
    moy_r = moyennes.get("rouges_" + suffixe) or 0.1
    if rouges is not None and rouges >= max(moy_r * SEUIL_FORCE, 0.2):
        faiblesses.append(
            f"Plus de cartons rouges {lieu} ({rouges:.2f} par match, moyenne {moy_r:.2f})."
        )

    if not forces:
        forces.append(
            f"Profil {lieu} proche de la moyenne du championnat sur l'attaque et la défense."
        )
    if not faiblesses:
        faiblesses.append(
            f"Pas de faiblesse marquée {lieu} par rapport à la moyenne du championnat."
        )
    return {"forces": forces, "faiblesses": faiblesses}


def _poisson(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _commentaire_score(buts_dom, buts_ext):
    """Phrase simple pour un score, sans jargon de paris."""
    if buts_dom == buts_ext:
        if buts_dom == 0:
            return "match nul et blanc"
        if buts_dom == 1:
            return "match nul 1-1"
        return f"match nul {buts_dom}-{buts_ext}"
    ecart = abs(buts_dom - buts_ext)
    total = buts_dom + buts_ext
    cote = "à domicile" if buts_dom > buts_ext else "à l'extérieur"
    if ecart >= 3 or (ecart >= 2 and total >= 4):
        return f"large succès {cote}"
    if total <= 2:
        return f"petit succès {cote}"
    return f"succès {cote}"


def _scenario_poisson(lam_dom, lam_ext):
    """Buts independants : grille 0..MAX_BUTS, score modal, 1N2."""
    lam_dom = max(0.15, lam_dom)
    lam_ext = max(0.15, lam_ext)
    p_dom = [_poisson(k, lam_dom) for k in range(MAX_BUTS + 1)]
    p_ext = [_poisson(k, lam_ext) for k in range(MAX_BUTS + 1)]

    cases = []
    p_victoire_dom = 0.0
    p_nul = 0.0
    p_victoire_ext = 0.0
    p_les_deux = 0.0
    p_plus_de_2 = 0.0
    for i, pi in enumerate(p_dom):
        for j, pj in enumerate(p_ext):
            proba = pi * pj
            cases.append((proba, i, j))
            if i > j:
                p_victoire_dom += proba
            elif i == j:
                p_nul += proba
            else:
                p_victoire_ext += proba
            if i > 0 and j > 0:
                p_les_deux += proba
            if i + j >= 3:
                p_plus_de_2 += proba

    total = p_victoire_dom + p_nul + p_victoire_ext
    if total <= 0:
        total = 1.0
    cases.sort(reverse=True)
    meilleurs = []
    for proba, i, j in cases[:NB_SCORES]:
        meilleurs.append(
            {
                "score": f"{i}-{j}",
                "pct": _arrondi(100 * proba / total, 1),
                "commentaire": _commentaire_score(i, j),
            }
        )
    plus_probable = meilleurs[0] if meilleurs else {
        "score": "1-1",
        "pct": 0,
        "commentaire": "match nul 1-1",
    }
    return {
        "xg_prevu_domicile": _arrondi(lam_dom),
        "xg_prevu_exterieur": _arrondi(lam_ext),
        "xg_total": _arrondi(lam_dom + lam_ext),
        "score_plus_probable": plus_probable["score"],
        "probabilite_score": plus_probable["pct"],
        "commentaire_score": plus_probable["commentaire"],
        "scores_frequents": meilleurs,
        "p_victoire_domicile": _arrondi(100 * p_victoire_dom / total, 1),
        "p_nul": _arrondi(100 * p_nul / total, 1),
        "p_victoire_exterieur": _arrondi(100 * p_victoire_ext / total, 1),
        "p_les_deux_marquent": _arrondi(100 * p_les_deux / total, 1),
        "p_plus_de_2_buts": _arrondi(100 * p_plus_de_2 / total, 1),
    }


def _lambda_cartons_equipe(forme, saison_jaunes, saison_rouges, moy_jaunes, moy_rouges):
    """5 derniers matchs si assez de cartons, sinon moyenne de saison, sinon ligue."""
    if (
        forme.get("nb_avec_cartons", 0) >= SEUIL_CARTONS_FORME
        and forme.get("jaunes_par_match") is not None
    ):
        return (
            float(forme["jaunes_par_match"]),
            float(forme.get("rouges_par_match") or 0),
            "5 derniers matchs",
        )
    if saison_jaunes is not None:
        return (
            float(saison_jaunes),
            float(saison_rouges or 0),
            "saison",
        )
    return float(moy_jaunes), float(moy_rouges), "moyenne du championnat"


def _scenario_cartons(lam_j_dom, lam_j_ext, lam_r_dom, lam_r_ext, moy_j_match, sources):
    """Estimation simple : somme des moyennes, Poisson pour un rouge."""
    lam_j = max(0.2, lam_j_dom + lam_j_ext)
    lam_r = max(0.02, lam_r_dom + lam_r_ext)
    p_au_moins_un_rouge = 1.0 - math.exp(-lam_r)
    if lam_j >= moy_j_match * SEUIL_FORCE:
        rythme = "cartonne"
        titre = "Match cartonné"
    elif lam_j <= moy_j_match * SEUIL_FAIBLESSE:
        rythme = "calme"
        titre = "Match calme"
    else:
        rythme = "dans_la_moyenne"
        titre = "Cartons dans la moyenne"
    if sources[0] == sources[1]:
        source = sources[0]
    else:
        source = f"{sources[0]} (domicile), {sources[1]} (extérieur)"
    texte = (
        f"Environ {lam_j:.1f} jaunes attendus "
        f"({lam_j_dom:.1f} à domicile, {lam_j_ext:.1f} à l'extérieur), "
        f"d'après {source}."
    )
    if p_au_moins_un_rouge >= 0.20:
        texte += f" Un rouge n'est pas improbable ({100 * p_au_moins_un_rouge:.0f} %)."
    else:
        texte += f" Un rouge reste peu probable ({100 * p_au_moins_un_rouge:.0f} %)."
    return {
        "jaunes_domicile": _arrondi(lam_j_dom, 1),
        "jaunes_exterieur": _arrondi(lam_j_ext, 1),
        "jaunes_match": _arrondi(lam_j, 1),
        "rouges_domicile": _arrondi(lam_r_dom, 2),
        "rouges_exterieur": _arrondi(lam_r_ext, 2),
        "rouges_match": _arrondi(lam_r, 2),
        "p_au_moins_un_rouge": _arrondi(100 * p_au_moins_un_rouge, 1),
        "moyenne_championnat": _arrondi(moy_j_match, 1),
        "rythme": rythme,
        "titre": titre,
        "source": source,
        "texte": texte,
    }


def _scenarios_detailles(pred, cartons, moy_xg_total):
    """Quatre lectures du match : rythme, buts, les deux marquent, cartons."""
    total_xg = (pred["xg_prevu_domicile"] or 0) + (pred["xg_prevu_exterieur"] or 0)
    moy = moy_xg_total or 2.5
    if total_xg >= moy * SEUIL_MATCH_OUVERT:
        rythme = {
            "cle": "rythme",
            "titre": "Match ouvert",
            "texte": (
                f"Beaucoup d'occasions prévues : {total_xg:.1f} xG au total "
                f"(moyenne du championnat {moy:.1f})."
            ),
            "chiffre": f"{total_xg:.1f} xG",
        }
    elif total_xg <= moy * SEUIL_MATCH_FERME:
        rythme = {
            "cle": "rythme",
            "titre": "Match fermé",
            "texte": (
                f"Peu d'occasions prévues : {total_xg:.1f} xG au total "
                f"(moyenne du championnat {moy:.1f})."
            ),
            "chiffre": f"{total_xg:.1f} xG",
        }
    else:
        rythme = {
            "cle": "rythme",
            "titre": "Rythme dans la moyenne",
            "texte": (
                f"{total_xg:.1f} xG attendus au total, proche de la moyenne "
                f"du championnat ({moy:.1f})."
            ),
            "chiffre": f"{total_xg:.1f} xG",
        }

    p_deux = pred["p_les_deux_marquent"] or 0
    if p_deux >= 50:
        deux = {
            "cle": "deux_equipes",
            "titre": "Les deux équipes marquent",
            "texte": (
                f"Dans {p_deux:.0f} % des scénarios, chaque équipe inscrit "
                "au moins un but."
            ),
            "pct": p_deux,
        }
    else:
        deux = {
            "cle": "deux_equipes",
            "titre": "Pas forcément les deux équipes",
            "texte": (
                f"Dans {100 - p_deux:.0f} % des scénarios, au moins une équipe "
                "ne marque pas."
            ),
            "pct": p_deux,
        }

    p_plus = pred["p_plus_de_2_buts"] or 0
    if p_plus >= 50:
        buts = {
            "cle": "buts",
            "titre": "Plus de 2 buts",
            "texte": (
                f"Le match dépasse 2 buts dans {p_plus:.0f} % des scénarios."
            ),
            "pct": p_plus,
        }
    else:
        buts = {
            "cle": "buts",
            "titre": "2 buts ou moins",
            "texte": (
                f"Le match reste à 2 buts ou moins dans {100 - p_plus:.0f} % "
                "des scénarios."
            ),
            "pct": p_plus,
        }

    cartons_bloc = {
        "cle": "cartons",
        "titre": cartons["titre"],
        "texte": cartons["texte"],
        "chiffre": f"{cartons['jaunes_match']} jaunes",
    }
    return [rythme, deux, buts, cartons_bloc]


def _phrases_concretes(phrases):
    """Écarte les phrases génériques (moyenne, échantillon trop petit)."""
    a_ignorer = (
        "proche de la moyenne",
        "pas de faiblesse",
        "échantillon trop petit",
        "pas assez de matchs",
        "moyenne du championnat est utilisée",
    )
    concretes = []
    for phrase in phrases or []:
        bas = phrase.lower()
        if any(morceau in bas for morceau in a_ignorer):
            continue
        concretes.append(phrase)
    return concretes


def _a_motif(phrases, motifs):
    for phrase in _phrases_concretes(phrases):
        bas = phrase.lower()
        if any(motif in bas for motif in motifs):
            return True
    return False


def _premiere_concrete(phrases):
    concretes = _phrases_concretes(phrases)
    return concretes[0] if concretes else None


def _recit_scenario(nom_dom, nom_ext, domicile, exterieur, pred, cartons):
    """Récit du déroulé : forces contre faiblesses, puis le scénario le plus probable."""
    paragraphes = []

    force_d = _premiere_concrete(domicile.get("forces"))
    faib_e = _premiere_concrete(exterieur.get("faiblesses"))
    force_e = _premiere_concrete(exterieur.get("forces"))
    faib_d = _premiere_concrete(domicile.get("faiblesses"))
    att_d = _a_motif(domicile.get("forces"), ["attaque", "tirs cadrés"])
    def_e_faible = _a_motif(exterieur.get("faiblesses"), ["défense"])
    att_e = _a_motif(exterieur.get("forces"), ["attaque", "tirs cadrés"])
    def_d_faible = _a_motif(domicile.get("faiblesses"), ["défense"])

    if force_d and faib_e:
        suite = ""
        if att_d and def_e_faible:
            suite = f" {nom_dom} devrait donc mettre la pression et chercher les espaces."
        elif att_d:
            suite = f" {nom_dom} peut créer des occasions."
        paragraphes.append(
            f"{nom_dom} à domicile : {force_d} "
            f"En face, {nom_ext} : {faib_e}"
            + suite
        )
    elif force_d:
        paragraphes.append(f"{nom_dom} à domicile : {force_d}")
    elif faib_e:
        paragraphes.append(
            f"{nom_ext} à l'extérieur : {faib_e} "
            f"{nom_dom} peut en profiter pour imposer son rythme."
        )

    if force_e and faib_d:
        suite = ""
        if att_e and def_d_faible:
            suite = (
                f" Les visiteurs peuvent donc inquiéter, surtout si le match s'ouvre."
            )
        paragraphes.append(
            f"{nom_ext} à l'extérieur : {force_e} "
            f"Côté {nom_dom} : {faib_d}"
            + suite
        )
    elif force_e:
        paragraphes.append(f"{nom_ext} à l'extérieur : {force_e}")
    elif faib_d:
        paragraphes.append(
            f"{nom_dom} a un point faible : {faib_d} "
            f"{nom_ext} peut s'y accrocher."
        )

    pression_dom = att_d and def_e_faible
    pression_ext = att_e and def_d_faible
    rythme = None
    for item in pred.get("scenarios") or []:
        if item.get("cle") == "rythme":
            rythme = item
            break
    titre_rythme = (rythme or {}).get("titre") or "Rythme dans la moyenne"
    xg_d = pred.get("xg_prevu_domicile")
    xg_e = pred.get("xg_prevu_exterieur")
    xg_total = pred.get("xg_total") or ((xg_d or 0) + (xg_e or 0))

    if pression_dom and pression_ext:
        pression = (
            "Les deux attaques peuvent faire mal : allers-retours, peu de répit."
        )
    elif pression_dom:
        pression = f"La pression devrait venir surtout de {nom_dom}."
    elif pression_ext:
        pression = (
            f"Même à l'extérieur, {nom_ext} peut inquiéter la défense de {nom_dom}."
        )
    else:
        pression = (
            "Ni l'une ni l'autre n'impose clairement son attaque : "
            "moins d'occasions nettes, match plus contrôlé."
        )

    p_deux = pred.get("p_les_deux_marquent") or 0
    p_plus = pred.get("p_plus_de_2_buts") or 0
    if p_deux >= 50:
        buts = "Les deux équipes ont de bonnes chances de marquer."
    else:
        buts = "Une des deux équipes peut rester muette."
    if p_plus >= 50:
        volume = "Plus de 2 buts est le cas le plus fréquent."
    else:
        volume = "Le score devrait rester à 2 buts ou moins."

    cartons_txt = cartons.get("titre") or "Cartons dans la moyenne"
    jaunes = cartons.get("jaunes_match")
    faute = ""
    if _a_motif(
        (domicile.get("faiblesses") or []) + (exterieur.get("faiblesses") or []),
        ["jaunes", "rouges"],
    ):
        faute = " Sous la pression, les fautes et les cartons peuvent s'accumuler."
    paragraphes.append(
        f"{titre_rythme} ({xg_total:.1f} xG attendus au total) : {pression} "
        f"{buts} {volume} "
        f"{cartons_txt}"
        + (f" (environ {jaunes} jaunes)." if jaunes is not None else ".")
        + faute
    )

    commentaire = pred.get("commentaire_score") or "scénario serré"
    score = pred.get("score_plus_probable") or "1-1"
    p_dom = pred.get("p_victoire_domicile") or 0
    p_ext = pred.get("p_victoire_exterieur") or 0
    if p_dom > p_ext + 8:
        avantage = f"{nom_dom} part avec un léger avantage à domicile"
    elif p_ext > p_dom + 8:
        avantage = f"{nom_ext} peut l'emporter malgré le déplacement"
    else:
        avantage = "aucune équipe ne se détache vraiment"
    if commentaire.startswith("match nul"):
        if avantage.startswith("aucune"):
            fil = (
                f"Le fil le plus probable : un {commentaire} ({score}) "
                f"— {avantage}."
            )
        else:
            fil = (
                f"Le fil le plus probable : un {commentaire} ({score}), "
                f"même si {avantage}."
            )
    else:
        fil = (
            f"Le fil le plus probable : {avantage}, vers un {commentaire} ({score})."
        )
    paragraphes.append(
        f"{fil} {nom_dom} autour de {xg_d} xG, {nom_ext} autour de {xg_e} xG."
    )

    if domicile.get("donnees_limitees") or exterieur.get("donnees_limitees"):
        paragraphes.append(
            "Une équipe a trop peu de matchs : ce récit s'appuie aussi "
            "sur la moyenne du championnat, à prendre avec du recul."
        )

    return paragraphes


def _bilan_match(pred, match_joue):
    """Compare le scénario prévu et le résultat réel."""
    buts_d = match_joue["buts_domicile"]
    buts_e = match_joue["buts_exterieur"]
    total = buts_d + buts_e
    score_reel = f"{buts_d}-{buts_e}"
    score_prevu = pred["score_plus_probable"]
    points = []
    if score_reel == score_prevu:
        points.append(
            f"Le score {score_reel} est exactement celui que le modèle voyait "
            "le plus souvent."
        )
    else:
        points.append(
            f"Score réel {score_reel} ({_commentaire_score(buts_d, buts_e)}) ; "
            f"le plus probable était {score_prevu}."
        )

    if total > 2:
        if (pred.get("p_plus_de_2_buts") or 0) >= 50:
            points.append(
                f"{total} buts : plus de 2 buts, comme le scénario le plus fréquent."
            )
        else:
            points.append(
                f"{total} buts : plus de buts que ce que les xG laissaient attendre."
            )
    else:
        if (pred.get("p_plus_de_2_buts") or 0) < 50:
            points.append(
                f"{total} buts : 2 ou moins, cohérent avec le scénario."
            )
        else:
            points.append(
                f"{total} buts seulement : le match a été plus fermé que prévu."
            )

    les_deux = buts_d > 0 and buts_e > 0
    p_deux = pred.get("p_les_deux_marquent") or 0
    if les_deux:
        if p_deux >= 50:
            points.append("Les deux équipes ont marqué, comme prévu.")
        else:
            points.append(
                "Les deux équipes ont marqué, alors que ce n'était pas "
                "le scénario majoritaire."
            )
    else:
        if p_deux < 50:
            points.append("Au moins une équipe n'a pas marqué, comme prévu.")
        else:
            points.append(
                "Une équipe est restée muette, alors que les deux pouvaient marquer."
            )

    j_d = match_joue.get("jaunes_domicile")
    j_e = match_joue.get("jaunes_exterieur")
    cartons = pred.get("cartons") or {}
    if j_d is not None and j_e is not None:
        jaunes = int(j_d) + int(j_e)
        prevu = cartons.get("jaunes_match")
        r_d = match_joue.get("rouges_domicile")
        r_e = match_joue.get("rouges_exterieur")
        rouges = int(r_d or 0) + int(r_e or 0)
        phrase = f"{jaunes} jaunes"
        if rouges:
            phrase += f" et {rouges} rouge" + ("s" if rouges > 1 else "")
        if prevu is not None:
            phrase += f" (environ {prevu} jaunes attendus"
            if jaunes >= prevu + 2:
                phrase += " : plus cartonné que prévu"
            elif jaunes <= prevu - 2:
                phrase += " : plus calme que prévu"
            phrase += ")"
        phrase += "."
        points.append(phrase)

    return {"points": points}


def _texte_prediction(nom_dom, nom_ext, pred, saisons_xg, limitees):
    utiles = [s for s, limite in zip(saisons_xg, limitees) if s and not limite]
    if not utiles:
        utiles = [s for s in saisons_xg if s]
    saisons = sorted(set(utiles))
    if len(saisons) == 1:
        ref = saisons[0]
    elif saisons:
        ref = " et ".join(saisons)
    else:
        ref = "les matchs en base"
    extra = ""
    if any(limitees):
        extra = " Une équipe a trop peu de matchs : sa projection colle à la moyenne du championnat."
    commentaire = pred.get("commentaire_score") or ""
    detail_score = f" ({commentaire})" if commentaire else ""
    return (
        f"D'après les xG {ref}, le scénario le plus fréquent est "
        f"{pred['score_plus_probable']}{detail_score} "
        f"({pred['p_victoire_domicile']:.0f} % victoire {nom_dom}, "
        f"{pred['p_nul']:.0f} % nul, "
        f"{pred['p_victoire_exterieur']:.0f} % victoire {nom_ext})."
        f"{extra} "
        "Ce n'est pas un pronostic de paris : uniquement un modèle Poisson "
        "sur les statistiques déjà en base."
    )


def _equipe_presente(connexion, championnat, nom):
    ligne = connexion.execute(
        """
        SELECT 1 FROM matchs
        WHERE championnat = ? AND (domicile = ? OR exterieur = ?)
        LIMIT 1
        """,
        (championnat, nom, nom),
    ).fetchone()
    return ligne is not None


def lister_equipes_analyse(connexion, championnat, saison):
    """Clubs de la saison demandee + saison precedente (promus inclus)."""
    precedente = saison_precedente(saison)
    lignes = connexion.execute(
        """
        SELECT DISTINCT nom FROM (
            SELECT domicile AS nom FROM matchs
            WHERE championnat = ? AND saison IN (?, ?)
            UNION
            SELECT exterieur FROM matchs
            WHERE championnat = ? AND saison IN (?, ?)
        )
        ORDER BY nom
        """,
        (championnat, saison, precedente, championnat, saison, precedente),
    ).fetchall()
    return [row[0] for row in lignes]


def confrontations_directes(connexion, championnat, nom_a, nom_b):
    """Matchs A vs B dans cette compétition, toutes saisons."""
    lignes = connexion.execute(
        """
        SELECT date, saison, domicile, exterieur,
               buts_domicile, buts_exterieur
        FROM matchs
        WHERE championnat = ?
          AND (
            (domicile = ? AND exterieur = ?)
            OR (domicile = ? AND exterieur = ?)
          )
          AND buts_domicile IS NOT NULL
          AND buts_exterieur IS NOT NULL
        ORDER BY date DESC
        """,
        (championnat, nom_a, nom_b, nom_b, nom_a),
    ).fetchall()
    victoires_a = 0
    nuls = 0
    victoires_b = 0
    matchs = []
    for ligne in lignes:
        if ligne["domicile"] == nom_a:
            bp_a = int(ligne["buts_domicile"])
            bc_a = int(ligne["buts_exterieur"])
        else:
            bp_a = int(ligne["buts_exterieur"])
            bc_a = int(ligne["buts_domicile"])
        if bp_a > bc_a:
            victoires_a += 1
        elif bp_a < bc_a:
            victoires_b += 1
        else:
            nuls += 1
        matchs.append(
            {
                "date": ligne["date"],
                "saison": ligne["saison"],
                "domicile": ligne["domicile"],
                "exterieur": ligne["exterieur"],
                "buts_domicile": int(ligne["buts_domicile"]),
                "buts_exterieur": int(ligne["buts_exterieur"]),
                "score": f"{int(ligne['buts_domicile'])}-{int(ligne['buts_exterieur'])}",
            }
        )
    return {
        "victoires_domicile": victoires_a,
        "nuls": nuls,
        "victoires_exterieur": victoires_b,
        "nb": len(lignes),
        "matchs": matchs[:NB_CONFRONTATIONS],
    }


def lire_match_joue(connexion, championnat, saison, nom_domicile, nom_exterieur):
    """Fiche du match si le score est déjà en base pour cette saison."""
    ligne = connexion.execute(
        """
        SELECT date, saison, domicile, exterieur,
               buts_domicile, buts_exterieur,
               tirs_domicile, tirs_exterieur,
               tirs_cadres_domicile, tirs_cadres_exterieur,
               jaunes_domicile, jaunes_exterieur,
               rouges_domicile, rouges_exterieur
        FROM matchs
        WHERE championnat = ? AND saison = ?
          AND domicile = ? AND exterieur = ?
          AND buts_domicile IS NOT NULL
          AND buts_exterieur IS NOT NULL
        ORDER BY date DESC
        LIMIT 1
        """,
        (championnat, saison, nom_domicile, nom_exterieur),
    ).fetchone()
    if not ligne:
        return {"joue": False}
    xg_d, xg_e = _xg_du_match(
        connexion, championnat, saison, nom_domicile, nom_exterieur, ligne["date"]
    )
    return {
        "joue": True,
        "date": ligne["date"],
        "saison": ligne["saison"],
        "buts_domicile": int(ligne["buts_domicile"]),
        "buts_exterieur": int(ligne["buts_exterieur"]),
        "tirs_domicile": ligne["tirs_domicile"],
        "tirs_exterieur": ligne["tirs_exterieur"],
        "tirs_cadres_domicile": ligne["tirs_cadres_domicile"],
        "tirs_cadres_exterieur": ligne["tirs_cadres_exterieur"],
        "jaunes_domicile": int(ligne["jaunes_domicile"]) if ligne["jaunes_domicile"] is not None else None,
        "jaunes_exterieur": int(ligne["jaunes_exterieur"]) if ligne["jaunes_exterieur"] is not None else None,
        "rouges_domicile": int(ligne["rouges_domicile"]) if ligne["rouges_domicile"] is not None else None,
        "rouges_exterieur": int(ligne["rouges_exterieur"]) if ligne["rouges_exterieur"] is not None else None,
        "xg_domicile": xg_d,
        "xg_exterieur": xg_e,
    }


def analyser_rencontre(connexion, championnat, saison, nom_domicile, nom_exterieur):
    if nom_domicile == nom_exterieur:
        raise ValueError("Les deux équipes doivent être différentes")
    if not _equipe_presente(connexion, championnat, nom_domicile):
        raise ValueError(f"Équipe introuvable : {nom_domicile}")
    if not _equipe_presente(connexion, championnat, nom_exterieur):
        raise ValueError(f"Équipe introuvable : {nom_exterieur}")

    saison_ligue = choisir_saison_ligue(connexion, championnat, saison)
    moy_xg = _moyennes_xg_ligue(connexion, championnat, saison_ligue)
    moy_matchs = _moyennes_matchs_ligue(connexion, championnat, saison_ligue)
    moyennes = {
        "xg_domicile": moy_xg["xg_domicile"],
        "xg_exterieur": moy_xg["xg_exterieur"],
        "xg_encaisses_domicile": moy_xg["xg_exterieur"],
        "xg_encaisses_exterieur": moy_xg["xg_domicile"],
        **moy_matchs,
    }

    def bloc(nom_matchs, a_domicile):
        champ_stats = championnat
        saison_xg, nom_xg, nb_xg = choisir_saison_xg(
            connexion, championnat, saison, nom_matchs
        )
        xg = _profil_xg(connexion, champ_stats, saison_xg, nom_xg, a_domicile)
        if xg["nb"] < SEUIL_MATCHS_PROFIL:
            xg = _profil_buts(
                connexion, championnat, saison, nom_matchs, a_domicile
            )
            saison_xg = saison
            nom_xg = nom_matchs
            if xg["nb"] < SEUIL_MATCHS_PROFIL:
                precedente = saison_precedente(saison)
                xg_prec = _profil_buts(
                    connexion, championnat, precedente, nom_matchs, a_domicile
                )
                if xg_prec["nb"] > xg["nb"]:
                    xg = xg_prec
                    saison_xg = precedente
        if (
            xg["nb"] < SEUIL_MATCHS_PROFIL
            and championnat == NOM_LDC
        ):
            trouve = xg_depuis_ligue_nationale(connexion, nom_matchs, saison)
            if trouve:
                champ_stats, saison_xg, nom_xg, _nb = trouve
                xg = _profil_xg(
                    connexion, champ_stats, saison_xg, nom_xg, a_domicile
                )
        stats = _profil_matchs(
            connexion, champ_stats, saison_xg, nom_matchs, a_domicile
        )
        suffixe = "domicile" if a_domicile else "exterieur"
        xg_marques, lim_att = _taux_ou_moyenne(
            xg["xg_marques"], xg["nb"], moyennes["xg_" + suffixe]
        )
        xg_encaisses, lim_def = _taux_ou_moyenne(
            xg["xg_encaisses"], xg["nb"], moyennes["xg_encaisses_" + suffixe]
        )
        tirs_cadres, _ = _taux_ou_moyenne(
            stats["tirs_cadres"], stats["nb"], moyennes["tirs_cadres_" + suffixe]
        )
        jaunes, _ = _taux_ou_moyenne(
            stats["jaunes"], stats["nb"], moyennes["jaunes_" + suffixe]
        )
        rouges, _ = _taux_ou_moyenne(
            stats["rouges"], stats["nb"], moyennes["rouges_" + suffixe]
        )
        donnees_limitees = lim_att or lim_def
        profil = {
            "xg_marques": xg_marques,
            "xg_encaisses": xg_encaisses,
            "tirs_cadres": tirs_cadres,
            "jaunes": jaunes,
            "rouges": rouges,
        }
        phrases = _phrases(profil, moyennes, a_domicile, donnees_limitees)
        return {
            "nom": nom_matchs,
            "nom_xg": nom_xg,
            "saison_xg": saison_xg,
            "nb_matchs_xg": xg["nb"],
            "xg_marques": _arrondi(xg["xg_marques"] if xg["xg_marques"] is not None else xg_marques),
            "xg_encaisses": _arrondi(
                xg["xg_encaisses"] if xg["xg_encaisses"] is not None else xg_encaisses
            ),
            "tirs_cadres": _arrondi(stats["tirs_cadres"], 1),
            "jaunes": _arrondi(stats["jaunes"], 1),
            "rouges": _arrondi(stats["rouges"], 2),
            "forme": forme_recente(connexion, championnat, nom_matchs),
            "forces": phrases["forces"],
            "faiblesses": phrases["faiblesses"],
            "donnees_limitees": donnees_limitees,
            "xg_marques_modele": xg_marques,
            "xg_encaisses_modele": xg_encaisses,
        }

    domicile = bloc(nom_domicile, True)
    exterieur = bloc(nom_exterieur, False)

    # xG attendu = attaque relative x defense relative x moyenne du lieu.
    att_dom = domicile["xg_marques_modele"] / moyennes["xg_domicile"]
    def_ext = exterieur["xg_encaisses_modele"] / moyennes["xg_encaisses_exterieur"]
    att_ext = exterieur["xg_marques_modele"] / moyennes["xg_exterieur"]
    def_dom = domicile["xg_encaisses_modele"] / moyennes["xg_encaisses_domicile"]
    lam_dom = att_dom * def_ext * moyennes["xg_domicile"]
    lam_ext = att_ext * def_dom * moyennes["xg_exterieur"]

    pred = _scenario_poisson(lam_dom, lam_ext)

    moy_j_match = moyennes["jaunes_domicile"] + moyennes["jaunes_exterieur"]
    lam_j_dom, lam_r_dom, src_dom = _lambda_cartons_equipe(
        domicile["forme"],
        domicile["jaunes"],
        domicile["rouges"],
        moyennes["jaunes_domicile"],
        moyennes["rouges_domicile"],
    )
    lam_j_ext, lam_r_ext, src_ext = _lambda_cartons_equipe(
        exterieur["forme"],
        exterieur["jaunes"],
        exterieur["rouges"],
        moyennes["jaunes_exterieur"],
        moyennes["rouges_exterieur"],
    )
    cartons = _scenario_cartons(
        lam_j_dom, lam_j_ext, lam_r_dom, lam_r_ext, moy_j_match, [src_dom, src_ext]
    )
    pred["cartons"] = cartons
    pred["scenarios"] = _scenarios_detailles(
        pred, cartons, moyennes["xg_domicile"] + moyennes["xg_exterieur"]
    )
    pred["recit"] = _recit_scenario(
        nom_domicile, nom_exterieur, domicile, exterieur, pred, cartons
    )
    pred["texte"] = _texte_prediction(
        nom_domicile,
        nom_exterieur,
        pred,
        [domicile["saison_xg"], exterieur["saison_xg"]],
        [domicile["donnees_limitees"], exterieur["donnees_limitees"]],
    )
    pred["saison_ligue"] = saison_ligue

    domicile.pop("xg_marques_modele", None)
    domicile.pop("xg_encaisses_modele", None)
    exterieur.pop("xg_marques_modele", None)
    exterieur.pop("xg_encaisses_modele", None)

    match_joue = lire_match_joue(
        connexion, championnat, saison, nom_domicile, nom_exterieur
    )
    if match_joue.get("joue"):
        pred["bilan"] = _bilan_match(pred, match_joue)

    return {
        "championnat": championnat,
        "saison_demandee": saison,
        "saison_ligue": saison_ligue,
        "avertissement": (
            "Scénario statistique calculé à partir des matchs et xG déjà en base. "
            "Ce n'est pas un pronostic de paris."
        ),
        "domicile": domicile,
        "exterieur": exterieur,
        "prediction": pred,
        "confrontations": confrontations_directes(
            connexion, championnat, nom_domicile, nom_exterieur
        ),
        "match_joue": match_joue,
    }
