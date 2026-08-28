"""
Calibrateur automatique 1X2 appris sur l'historique analyses.db.

Entraine une regression logistique legere sur les probabilites brutes du modele
Poisson xG + Elo, avec features optionnelles (xG total, ecart Elo, championnat).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import math
import pickle
import sqlite3
from typing import Any

from calibration import brier_score_1x2, _probas_normalisees

RACINE = Path(__file__).resolve().parents[2]
DOSSIER_MODELES = RACINE / "donnees" / "modeles"
FICHIER_CALIBRATEUR = DOSSIER_MODELES / "calibrateur.pkl"
FICHIER_META = DOSSIER_MODELES / "calibrateur.json"

SEUIL_MIN_MATCHS = 20
NOM_MODELE_BRUT = "poisson-xg-elo-v2"
NOM_MODELE_CALIBRE = "poisson-xg-elo-cal-v3"

_ISSUE_VERS_IDX = {"1": 0, "N": 1, "2": 2}
_IDX_VERS_ISSUE = ("1", "N", "2")

_calibrateur_charge: "Calibrateur1X2 | None" | None = None
_meta_chargee: dict | None = None

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import LabelEncoder

    _SKLEARN_DISPONIBLE = True
except ImportError:
    _SKLEARN_DISPONIBLE = False


def _maintenant_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _softmax(logits: list[float]) -> list[float]:
    max_l = max(logits)
    exps = [math.exp(l - max_l) for l in logits]
    total = sum(exps)
    if total <= 0:
        return [1.0 / 3.0] * 3
    return [e / total for e in exps]


class _RegressionLogistiquePython:
    """Regression logistique multiclasse (softmax) en pur Python."""

    def __init__(self, nb_features: int, nb_classes: int = 3, taux: float = 0.1):
        self.nb_features = nb_features
        self.nb_classes = nb_classes
        self.taux = taux
        self.poids = [[0.0] * nb_features for _ in range(nb_classes)]
        self.biais = [0.0] * nb_classes

    def fit(self, x: list[list[float]], y: list[int], epochs: int = 400) -> None:
        n = len(x)
        if n == 0:
            return
        for _ in range(epochs):
            for i in range(n):
                logits = [
                    sum(self.poids[c][j] * x[i][j] for j in range(self.nb_features))
                    + self.biais[c]
                    for c in range(self.nb_classes)
                ]
                proba = _softmax(logits)
                for c in range(self.nb_classes):
                    erreur = proba[c] - (1.0 if y[i] == c else 0.0)
                    for j in range(self.nb_features):
                        self.poids[c][j] -= self.taux * erreur * x[i][j] / n
                    self.biais[c] -= self.taux * erreur / n

    def predict_proba_ligne(self, ligne: list[float]) -> list[float]:
        logits = [
            sum(self.poids[c][j] * ligne[j] for j in range(self.nb_features))
            + self.biais[c]
            for c in range(self.nb_classes)
        ]
        return _softmax(logits)


class Calibrateur1X2:
    """Modele de calibration 1X2 serialisable."""

    def __init__(self):
        self.championnats: list[str] = []
        self.champ_vers_idx: dict[str, int] = {}
        self.methode = "python"
        self.modele_sklearn = None
        self.modele_python: _RegressionLogistiquePython | None = None
        self.label_encoder = None

    def _encoder_championnat(self, championnat: str | None) -> float:
        if not self.championnats:
            return 0.0
        cle = (championnat or "").strip()
        idx = self.champ_vers_idx.get(cle, -1)
        if idx < 0:
            return 0.0
        return idx / max(1, len(self.championnats) - 1)

    def _vecteur_features(
        self,
        p1: float,
        pn: float,
        p2: float,
        features: dict | None,
    ) -> list[float]:
        p1f, pnf, p2f = _probas_normalisees(p1, pn, p2)
        feats = features or {}
        xg_total = float(feats.get("xg_total_prevu") or 0.0)
        elo_diff = float(feats.get("elo_diff") or 0.0)
        champ = self._encoder_championnat(feats.get("championnat"))
        return [p1f, pnf, p2f, xg_total / 4.0, elo_diff / 200.0, champ]

    def entrainer(self, echantillons: list[dict]) -> None:
        """Entraine sur une liste {p1, pn, p2, issue, features}."""
        championnats = sorted(
            {
                (e.get("features") or {}).get("championnat", "").strip()
                for e in echantillons
                if (e.get("features") or {}).get("championnat")
            }
        )
        self.championnats = championnats
        self.champ_vers_idx = {c: i for i, c in enumerate(championnats)}

        x_mat = [
            self._vecteur_features(e["p1"], e["pn"], e["p2"], e.get("features"))
            for e in echantillons
        ]
        y_idx = [_ISSUE_VERS_IDX[e["issue"]] for e in echantillons]

        if _SKLEARN_DISPONIBLE:
            self.methode = "sklearn"
            self.label_encoder = LabelEncoder()
            self.label_encoder.fit(list(_IDX_VERS_ISSUE))
            self.modele_sklearn = LogisticRegression(
                multi_class="multinomial",
                max_iter=500,
                solver="lbfgs",
            )
            self.modele_sklearn.fit(x_mat, [e["issue"] for e in echantillons])
            self.modele_python = None
        else:
            self.methode = "python"
            self.modele_python = _RegressionLogistiquePython(len(x_mat[0]))
            self.modele_python.fit(x_mat, y_idx)
            self.modele_sklearn = None

    def predire_probas(
        self,
        p1: float,
        pn: float,
        p2: float,
        features: dict | None = None,
    ) -> tuple[float, float, float]:
        ligne = self._vecteur_features(p1, pn, p2, features)
        if self.modele_sklearn is not None:
            proba = self.modele_sklearn.predict_proba([ligne])[0]
            classes = list(self.modele_sklearn.classes_)
            resultat = [0.0, 0.0, 0.0]
            for val, cls in zip(proba, classes):
                resultat[_ISSUE_VERS_IDX[str(cls)]] = float(val)
            p1f, pnf, p2f = resultat
        elif self.modele_python is not None:
            p1f, pnf, p2f = self.modele_python.predict_proba_ligne(ligne)
        else:
            p1f, pnf, p2f = _probas_normalisees(p1, pn, p2)
        total = p1f + pnf + p2f
        if total <= 0:
            return 0.33, 0.34, 0.33
        return p1f / total, pnf / total, p2f / total


def _extraire_probas_brutes(ligne: sqlite3.Row) -> tuple[float, float, float]:
    """Lit les probabilites brutes (avant calibration) depuis une prevision."""
    try:
        payload = json.loads(ligne["payload_json"] or "{}")
    except (json.JSONDecodeError, TypeError):
        payload = {}
    brutes = payload.get("probas_1x2_brutes") or {}
    if brutes:
        return (
            float(brutes.get("p_victoire_domicile", ligne["p_victoire_domicile"])),
            float(brutes.get("p_nul", ligne["p_nul"])),
            float(brutes.get("p_victoire_exterieur", ligne["p_victoire_exterieur"])),
        )
    return (
        float(ligne["p_victoire_domicile"]),
        float(ligne["p_nul"]),
        float(ligne["p_victoire_exterieur"]),
    )


def _extraire_features_ligne(ligne: sqlite3.Row) -> dict:
    xg_d = ligne["xg_prevu_domicile"]
    xg_e = ligne["xg_prevu_exterieur"]
    xg_total = None
    if xg_d is not None and xg_e is not None:
        xg_total = float(xg_d) + float(xg_e)
    elo_diff = None
    try:
        payload = json.loads(ligne["payload_json"] or "{}")
        elo = payload.get("elo") or {}
        if elo.get("differentiel") is not None:
            elo_diff = float(elo["differentiel"])
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return {
        "xg_total_prevu": xg_total,
        "elo_diff": elo_diff,
        "championnat": ligne["championnat"],
    }


def lire_donnees_entrainement(
    connexion: sqlite3.Connection,
    saison: str | None = None,
) -> list[dict]:
    """Charge les paires prevision/resultat honnetes (retroactif=0)."""
    sql = """
        SELECT
            p.p_victoire_domicile, p.p_nul, p.p_victoire_exterieur,
            p.xg_prevu_domicile, p.xg_prevu_exterieur,
            p.championnat, p.payload_json,
            r.issue_reelle
        FROM resultats_analyse r
        JOIN previsions_match p ON p.id = r.prevision_id
        WHERE COALESCE(p.retroactif, 0) = 0
          AND r.issue_reelle IS NOT NULL
          AND p.p_victoire_domicile IS NOT NULL
          AND p.p_nul IS NOT NULL
          AND p.p_victoire_exterieur IS NOT NULL
    """
    params: list = []
    if saison:
        sql += " AND p.saison = ?"
        params.append(saison)
    sql += " ORDER BY r.match_joue_le, p.id"
    lignes = connexion.execute(sql, params).fetchall()
    echantillons = []
    for ligne in lignes:
        p1, pn, p2 = _extraire_probas_brutes(ligne)
        echantillons.append(
            {
                "p1": p1,
                "pn": pn,
                "p2": p2,
                "issue": ligne["issue_reelle"],
                "features": _extraire_features_ligne(ligne),
            }
        )
    return echantillons


def _brier_moyen(echantillons: list[dict], calibrateur: Calibrateur1X2 | None) -> float:
    if not echantillons:
        return 0.0
    total = 0.0
    for e in echantillons:
        if calibrateur is None:
            p1, pn, p2 = _probas_normalisees(e["p1"], e["pn"], e["p2"])
        else:
            p1, pn, p2 = calibrateur.predire_probas(
                e["p1"], e["pn"], e["p2"], e.get("features")
            )
        total += brier_score_1x2(p1, pn, p2, e["issue"])
    return total / len(echantillons)


def entrainer_calibrateur(
    connexion: sqlite3.Connection,
    saison: str | None = None,
    chemin_modele: Path | None = None,
    chemin_meta: Path | None = None,
) -> dict:
    """
    Entraine et sauvegarde le calibrateur si assez de donnees honnetes.
    Retourne un resume (nb matchs, Brier avant/apres, succes).
    """
    global _calibrateur_charge, _meta_chargee

    echantillons = lire_donnees_entrainement(connexion, saison=saison)
    nb = len(echantillons)
    resume: dict[str, Any] = {
        "succes": False,
        "nb_matchs": nb,
        "seuil_min": SEUIL_MIN_MATCHS,
        "saison": saison,
        "brier_avant": None,
        "brier_apres": None,
        "message": "",
    }

    if nb < SEUIL_MIN_MATCHS:
        resume["message"] = (
            f"Pas assez de resultats honnetes ({nb} < {SEUIL_MIN_MATCHS}) : "
            "calibrateur non entraine."
        )
        return resume

    brier_avant = _brier_moyen(echantillons, None)
    calibrateur = Calibrateur1X2()
    calibrateur.entrainer(echantillons)
    brier_apres = _brier_moyen(echantillons, calibrateur)

    fichier_pkl = chemin_modele or FICHIER_CALIBRATEUR
    fichier_json = chemin_meta or FICHIER_META
    fichier_pkl.parent.mkdir(parents=True, exist_ok=True)

    meta = {
        "entraine_le": _maintenant_iso(),
        "nb_matchs": nb,
        "brier_avant": round(brier_avant, 4),
        "brier_apres": round(brier_apres, 4),
        "saison": saison,
        "methode": calibrateur.methode,
        "seuil_min": SEUIL_MIN_MATCHS,
        "version_modele": NOM_MODELE_CALIBRE,
    }

    with open(fichier_pkl, "wb") as f:
        pickle.dump(calibrateur, f)
    fichier_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    _calibrateur_charge = calibrateur
    _meta_chargee = meta

    resume.update(
        {
            "succes": True,
            "brier_avant": meta["brier_avant"],
            "brier_apres": meta["brier_apres"],
            "methode": calibrateur.methode,
            "message": "Calibrateur entraine et sauvegarde.",
        }
    )
    return resume


def charger_calibrateur(
    chemin_modele: Path | None = None,
    forcer_rechargement: bool = False,
) -> Calibrateur1X2 | None:
    """Charge le calibrateur depuis le disque (cache en memoire)."""
    global _calibrateur_charge, _meta_chargee

    if _calibrateur_charge is not None and not forcer_rechargement:
        return _calibrateur_charge

    fichier = chemin_modele or FICHIER_CALIBRATEUR
    if not fichier.is_file():
        _calibrateur_charge = None
        _meta_chargee = None
        return None

    try:
        with open(fichier, "rb") as f:
            _calibrateur_charge = pickle.load(f)
    except (OSError, pickle.UnpicklingError):
        _calibrateur_charge = None
        _meta_chargee = None
        return None

    meta_fichier = fichier.parent / "calibrateur.json"
    if meta_fichier.is_file():
        try:
            _meta_chargee = json.loads(meta_fichier.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            _meta_chargee = None

    return _calibrateur_charge


def calibrateur_actif() -> bool:
    """True si un calibrateur valide est charge ou disponible sur disque."""
    return charger_calibrateur() is not None


def nom_modele_actuel() -> str:
    """Nom de version du modele selon la presence du calibrateur."""
    if calibrateur_actif():
        return NOM_MODELE_CALIBRE
    return NOM_MODELE_BRUT


def infos_calibrateur() -> dict:
    """Metadonnees pour l'API stats-modele."""
    global _meta_chargee
    actif = calibrateur_actif()
    if not actif:
        return {
            "actif": False,
            "nb_matchs_entrainement": 0,
            "seuil_min": SEUIL_MIN_MATCHS,
            "version_modele": NOM_MODELE_BRUT,
        }
    if _meta_chargee is None and FICHIER_META.is_file():
        try:
            _meta_chargee = json.loads(FICHIER_META.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            _meta_chargee = {}
    meta = _meta_chargee or {}
    return {
        "actif": True,
        "nb_matchs_entrainement": meta.get("nb_matchs", 0),
        "seuil_min": meta.get("seuil_min", SEUIL_MIN_MATCHS),
        "brier_avant": meta.get("brier_avant"),
        "brier_apres": meta.get("brier_apres"),
        "entraine_le": meta.get("entraine_le"),
        "methode": meta.get("methode"),
        "version_modele": NOM_MODELE_CALIBRE,
    }


def appliquer_calibrateur(
    p1: float,
    pn: float,
    p2: float,
    features: dict | None = None,
) -> tuple[float, float, float]:
    """
    Ajuste p(1), p(N), p(2) si un calibrateur est disponible.
    Retourne des pourcentages (0-100) dont la somme vaut 100.
    """
    calibrateur = charger_calibrateur()
    if calibrateur is None:
        p1f, pnf, p2f = _probas_normalisees(p1, pn, p2)
    else:
        p1f, pnf, p2f = calibrateur.predire_probas(p1, pn, p2, features)

    return (
        round(100.0 * p1f, 1),
        round(100.0 * pnf, 1),
        round(100.0 * p2f, 1),
    )
