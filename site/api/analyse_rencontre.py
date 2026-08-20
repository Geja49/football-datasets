"""
Analyse statistique d'une rencontre a partir de football.db.

Pas de cotes, pas d'IA externe : forme, xG, forces/faiblesses et
un scenario Poisson (buts independants) commente en francais.
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
NB_SCORES = 5
NB_FORME = 5


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
               buts_domicile, buts_exterieur, resultat
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
    matchs = []
    for ligne in lignes:
        est_domicile = ligne["domicile"] == nom_matchs
        bp = int(ligne["buts_domicile"] if est_domicile else ligne["buts_exterieur"])
        bc = int(ligne["buts_exterieur"] if est_domicile else ligne["buts_domicile"])
        buts_pour += bp
        buts_contre += bc
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
        "matchs": matchs,
    }


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
            }
        )
    plus_probable = meilleurs[0] if meilleurs else {"score": "1-1", "pct": 0}
    return {
        "xg_prevu_domicile": _arrondi(lam_dom),
        "xg_prevu_exterieur": _arrondi(lam_ext),
        "score_plus_probable": plus_probable["score"],
        "probabilite_score": plus_probable["pct"],
        "scores_frequents": meilleurs,
        "p_victoire_domicile": _arrondi(100 * p_victoire_dom / total, 1),
        "p_nul": _arrondi(100 * p_nul / total, 1),
        "p_victoire_exterieur": _arrondi(100 * p_victoire_ext / total, 1),
    }


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
    return (
        f"D'après les xG {ref}, le scénario le plus fréquent est "
        f"{pred['score_plus_probable']} "
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
        donnees_limitees = lim_att or lim_def
        profil = {
            "xg_marques": xg_marques,
            "xg_encaisses": xg_encaisses,
            "tirs_cadres": tirs_cadres,
            "jaunes": jaunes,
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
    }
