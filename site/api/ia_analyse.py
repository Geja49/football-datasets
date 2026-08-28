"""
Couche IA hybride : faits vérifiables + LLM encadré (Phase 3 MVP).

Sans clé LLM : récit enrichi par template (aucune API externe).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import requests

from communaute import charger_fichier_env

PROMPT_SYSTEME = """Tu es un analyste football. Tu rédiges en français.
Tu ne cites QUE les chiffres et faits présents dans le JSON fourni.
N'invente aucune statistique, aucun résultat, aucun joueur.
Si une information manque, dis-le brièvement sans la supposer.
Structure : 2 à 4 paragraphes courts (contexte, forces/faiblesses, scénario probable)."""


def _maintenant_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generer_faits_pour_ia(
    prediction: dict,
    prevision_figee: dict | None = None,
    *,
    championnat: str = "",
    saison: str = "",
    domicile: str = "",
    exterieur: str = "",
    domicile_profil: dict | None = None,
    exterieur_profil: dict | None = None,
    confrontations: dict | None = None,
) -> dict[str, Any]:
    """
    JSON de faits vérifiables uniquement — base pour le LLM ou le template.
    """
    pred = dict(prediction or {})
    if prevision_figee and prevision_figee.get("prediction"):
        pred = {**pred, **(prevision_figee.get("prediction") or {})}

    cartons = pred.get("cartons") or {}
    faits: dict[str, Any] = {
        "championnat": championnat,
        "saison": saison,
        "domicile": domicile,
        "exterieur": exterieur,
        "probas_1x2": {
            "victoire_domicile_pct": pred.get("p_victoire_domicile"),
            "nul_pct": pred.get("p_nul"),
            "victoire_exterieur_pct": pred.get("p_victoire_exterieur"),
        },
        "score_plus_probable": pred.get("score_plus_probable"),
        "probabilite_score_pct": pred.get("probabilite_score"),
        "xg_prevu": {
            "domicile": pred.get("xg_prevu_domicile"),
            "exterieur": pred.get("xg_prevu_exterieur"),
            "total": pred.get("xg_total"),
        },
        "marche_buts": {
            "les_deux_marquent_pct": pred.get("p_les_deux_marquent"),
            "plus_de_2_buts_pct": pred.get("p_plus_de_2_buts"),
        },
        "cartons_prevus": {
            "jaunes_domicile": cartons.get("jaunes_domicile"),
            "jaunes_exterieur": cartons.get("jaunes_exterieur"),
            "jaunes_match": cartons.get("jaunes_match"),
        },
        "elo": pred.get("elo") if isinstance(pred.get("elo"), dict) else None,
        "phrase_elo": pred.get("phrase_elo"),
        "scenarios": [
            {
                "titre": s.get("titre"),
                "texte": s.get("texte"),
                "chiffre": s.get("chiffre"),
                "pct": s.get("pct"),
            }
            for s in (pred.get("scenarios") or [])
            if isinstance(s, dict)
        ],
        "prevision_figee_le": (prevision_figee or {}).get("genere_le"),
        "version_modele": ((prevision_figee or {}).get("version_modele") or {}).get("nom"),
    }

    h2h = confrontations or pred.get("confrontations")
    if isinstance(h2h, dict) and h2h.get("nb"):
        faits["confrontations"] = {
            "nb": h2h.get("nb"),
            "victoires_domicile": h2h.get("victoires_domicile"),
            "nuls": h2h.get("nuls"),
            "victoires_exterieur": h2h.get("victoires_exterieur"),
            "derniers_matchs": [
                {
                    "date": m.get("date"),
                    "score": m.get("score"),
                    "domicile": m.get("domicile"),
                    "exterieur": m.get("exterieur"),
                }
                for m in (h2h.get("matchs") or [])[:3]
                if isinstance(m, dict)
            ],
        }

    for cle, profil, label in (
        ("domicile", domicile_profil, domicile),
        ("exterieur", exterieur_profil, exterieur),
    ):
        if not profil:
            continue
        forme = profil.get("forme") or {}
        faits[f"profil_{cle}"] = {
            "nom": profil.get("nom") or label,
            "forme_5_matchs": forme.get("resume"),
            "buts_pour_5": forme.get("buts_pour"),
            "buts_contre_5": forme.get("buts_contre"),
            "xg_marques": profil.get("xg_marques"),
            "xg_encaisses": profil.get("xg_encaisses"),
            "forces": (profil.get("forces") or [])[:3],
            "faiblesses": (profil.get("faiblesses") or [])[:3],
        }

    return faits


def _llm_desactive() -> bool:
    """Si DESACTIVER_LLM=1, aucun appel API externe même avec CLE_LLM."""
    charger_fichier_env()
    valeur = (os.environ.get("DESACTIVER_LLM") or "").strip().lower()
    return valeur in ("1", "true", "oui", "yes", "on")


def _config_llm() -> dict[str, str]:
    charger_fichier_env()
    return {
        "cle": (os.environ.get("CLE_LLM") or "").strip(),
        "modele": (os.environ.get("MODELE_LLM") or "gpt-4o-mini").strip(),
        "fournisseur": (os.environ.get("FOURNISSEUR_LLM") or "openai").strip().lower(),
        "url_base": (os.environ.get("URL_BASE_LLM") or "").strip(),
    }


def _appeler_llm(faits: dict, config: dict) -> str | None:
    """Appel OpenAI-compatible ou Ollama. Retourne None si échec."""
    if not config.get("cle") and config.get("fournisseur") != "ollama":
        return None

    messages = [
        {"role": "system", "content": PROMPT_SYSTEME},
        {
            "role": "user",
            "content": (
                "Analyse ce match à partir des faits JSON suivants. "
                "Ne cite que ces chiffres.\n\n"
                + json.dumps(faits, ensure_ascii=False, indent=2)
            ),
        },
    ]

    if config["fournisseur"] == "ollama":
        url = config["url_base"] or "http://127.0.0.1:11434/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if config.get("cle"):
            headers["Authorization"] = f"Bearer {config['cle']}"
    else:
        base = config["url_base"] or "https://api.openai.com/v1"
        url = f"{base.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config['cle']}",
            "Content-Type": "application/json",
        }

    corps = {
        "model": config["modele"],
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 800,
    }
    try:
        reponse = requests.post(url, headers=headers, json=corps, timeout=45)
        reponse.raise_for_status()
        data = reponse.json()
        return data["choices"][0]["message"]["content"].strip()
    except (requests.RequestException, KeyError, IndexError, TypeError):
        return None


def _analyse_template(faits: dict) -> str:
    """Récit enrichi sans API externe."""
    dom = faits.get("domicile") or "Domicile"
    ext = faits.get("exterieur") or "Extérieur"
    champ = (faits.get("championnat") or "").strip()
    saison = (faits.get("saison") or "").strip()
    contexte_competition = ""
    if champ and saison:
        contexte_competition = f" — {champ}, saison {saison}"
    elif champ:
        contexte_competition = f" — {champ}"
    elif saison:
        contexte_competition = f" — saison {saison}"

    probas = faits.get("probas_1x2") or {}
    xg = faits.get("xg_prevu") or {}
    score = faits.get("score_plus_probable") or "—"
    p_dom = probas.get("victoire_domicile_pct")
    p_nul = probas.get("nul_pct")
    p_ext = probas.get("victoire_exterieur_pct")

    lignes = [
        f"**{dom}** reçoit **{ext}**{contexte_competition}. "
        f"Le modèle statistique voit le score **{score}** comme le plus fréquent.",
    ]

    if p_dom is not None and p_nul is not None and p_ext is not None:
        lignes.append(
            f"**Probabilités 1X2** : victoire {dom} **{p_dom} %**, nul **{p_nul} %**, "
            f"victoire {ext} **{p_ext} %**."
        )

    if xg.get("domicile") is not None and xg.get("exterieur") is not None:
        lignes.append(
            f"**Occasions attendues (xG)** : **{xg['domicile']}** pour {dom}, "
            f"**{xg['exterieur']}** pour {ext} "
            f"(total **{xg.get('total') or round(float(xg['domicile']) + float(xg['exterieur']), 2)}**)."
        )

    h2h = faits.get("confrontations") or {}
    if h2h.get("nb"):
        lignes.append(
            f"**Confrontations directes** ({h2h['nb']} matchs en compétition) : "
            f"{dom} **{h2h.get('victoires_domicile', 0)}** victoire(s), "
            f"**{h2h.get('nuls', 0)}** nul(s), "
            f"{ext} **{h2h.get('victoires_exterieur', 0)}** victoire(s)."
        )
        derniers = h2h.get("derniers_matchs") or []
        if derniers:
            resumes = []
            for m in derniers[:3]:
                resumes.append(
                    f"{m.get('date', '')} : {m.get('domicile')} {m.get('score')} {m.get('exterieur')}"
                )
            lignes.append("Derniers face-à-face : " + " ; ".join(resumes) + ".")

    for cle in ("profil_domicile", "profil_exterieur"):
        profil = faits.get(cle)
        if not profil:
            continue
        nom = profil.get("nom") or cle
        section: list[str] = []
        if profil.get("forme_5_matchs"):
            section.append(
                f"forme **{profil['forme_5_matchs']}** "
                f"({profil.get('buts_pour_5')} buts pour, {profil.get('buts_contre_5')} contre sur 5 matchs)"
            )
        forces = profil.get("forces") or []
        faiblesses = profil.get("faiblesses") or []
        if forces:
            section.append(f"forces : {', '.join(forces[:2])}")
        if faiblesses:
            section.append(f"faiblesses : {', '.join(faiblesses[:2])}")
        if section:
            lignes.append(f"**{nom}** — " + " ; ".join(section) + ".")

    marche = faits.get("marche_buts") or {}
    if marche.get("les_deux_marquent_pct") is not None:
        lignes.append(
            f"**Marché buts** : les deux équipes marquent dans **{marche['les_deux_marquent_pct']} %** "
            f"des scénarios simulés ; plus de 2 buts dans **{marche.get('plus_de_2_buts_pct')} %**."
        )

    if faits.get("phrase_elo"):
        lignes.append(f"**Force relative (Elo)** : {faits['phrase_elo']}")

    scenarios = faits.get("scenarios") or []
    if scenarios:
        titres = ", ".join(s.get("titre") or "" for s in scenarios[:2] if s.get("titre"))
        if titres:
            lignes.append(f"**Lecture du rythme** : {titres}.")

    return "\n\n".join(lignes)


def generer_analyse_ia(faits: dict, *, forcer_template: bool = True) -> dict[str, str]:
    """
    Produit le texte d'analyse et la source (llm | template).
    Par défaut : template local (aucune API). LLM uniquement si forcer_template=False
    et DESACTIVER_LLM absent.
    """
    if not forcer_template and not _llm_desactive():
        config = _config_llm()
        texte_llm = _appeler_llm(faits, config)
        if texte_llm:
            return {"texte": texte_llm, "source": "llm"}

    return {"texte": _analyse_template(faits), "source": "template"}


def lire_analyse_ia_cachee(connexion, cle_match: str) -> dict | None:
    ligne = connexion.execute(
        "SELECT source, contenu_json, genere_le FROM analyses_ia WHERE cle_match = ?",
        (cle_match,),
    ).fetchone()
    if not ligne:
        return None
    try:
        contenu = json.loads(ligne["contenu_json"] or "{}")
    except json.JSONDecodeError:
        contenu = {"texte": ligne["contenu_json"]}
    return {
        "texte": contenu.get("texte") or "",
        "source": ligne["source"],
        "genere_le": ligne["genere_le"],
        "faits": contenu.get("faits"),
    }


def enregistrer_analyse_ia_cachee(
    connexion,
    cle_match: str,
    texte: str,
    source: str,
    faits: dict | None = None,
) -> None:
    payload = json.dumps({"texte": texte, "faits": faits}, ensure_ascii=False)
    connexion.execute(
        """
        INSERT INTO analyses_ia (cle_match, source, contenu_json, genere_le)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(cle_match) DO UPDATE SET
            source = excluded.source,
            contenu_json = excluded.contenu_json,
            genere_le = excluded.genere_le
        """,
        (cle_match, source, payload, _maintenant_iso()),
    )
    connexion.commit()
