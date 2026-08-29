"""
Crée ou met à jour un compte administrateur de test (dev local).

Usage :
  python scripts/creer_admin_test.py
  python scripts/creer_admin_test.py --mot-de-passe "VotreMotDePasse!"
  ADMIN_TEST_MDP="VotreMotDePasse!" python scripts/creer_admin_test.py

Le mot de passe n'est jamais stocké en clair dans le dépôt : passez-le en
argument ou via la variable d'environnement ADMIN_TEST_MDP. Sans mot de passe
fourni, un mot de passe aléatoire est généré et affiché une seule fois.
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "site" / "api"))

import communaute  # noqa: E402

EMAIL_ADMIN = "admin@statsfoot.local"
PSEUDO_ADMIN = "administrateur"


def _mot_de_passe_fourni(args: argparse.Namespace) -> str:
    if args.mot_de_passe:
        return args.mot_de_passe
    depuis_env = (os.environ.get("ADMIN_TEST_MDP") or "").strip()
    if depuis_env:
        return depuis_env
    genere = secrets.token_urlsafe(12)
    print(
        "Aucun mot de passe fourni — mot de passe généré (notez-le, il ne sera "
        "plus affiché) :",
        genere,
        sep="\n",
    )
    return genere


def creer_ou_mettre_a_jour_admin(mot_de_passe: str) -> dict:
    communaute.initialiser_base()
    hash_mdp = communaute.contexte_mots_de_passe.hash(mot_de_passe)
    maintenant = communaute.maintenant_iso()

    connexion = communaute.ouvrir_base()
    try:
        ligne = connexion.execute(
            "SELECT id, pseudo FROM utilisateurs WHERE email = ? COLLATE NOCASE",
            (EMAIL_ADMIN,),
        ).fetchone()

        if ligne:
            connexion.execute(
                """
                UPDATE utilisateurs
                SET pseudo = ?, mot_de_passe_hash = ?, est_admin = 1,
                    age_confirme = 1, cgu_acceptees = 1
                WHERE id = ?
                """,
                (PSEUDO_ADMIN, hash_mdp, ligne["id"]),
            )
            action = "mis à jour"
            utilisateur_id = ligne["id"]
        else:
            conflit_pseudo = connexion.execute(
                "SELECT id FROM utilisateurs WHERE pseudo = ? COLLATE NOCASE AND email != ?",
                (PSEUDO_ADMIN, EMAIL_ADMIN),
            ).fetchone()
            pseudo = PSEUDO_ADMIN if not conflit_pseudo else "admin"

            curseur = connexion.execute(
                """
                INSERT INTO utilisateurs (
                    email, pseudo, mot_de_passe_hash,
                    est_admin, age_confirme, cgu_acceptees, cree_le
                ) VALUES (?, ?, ?, 1, 1, 1, ?)
                """,
                (EMAIL_ADMIN, pseudo, hash_mdp, maintenant),
            )
            action = "créé"
            utilisateur_id = curseur.lastrowid
        connexion.commit()

        ligne_finale = connexion.execute(
            "SELECT id, email, pseudo, est_admin FROM utilisateurs WHERE id = ?",
            (utilisateur_id,),
        ).fetchone()
    finally:
        connexion.close()

    return {
        "action": action,
        "id": ligne_finale["id"],
        "email": ligne_finale["email"],
        "pseudo": ligne_finale["pseudo"],
        "est_admin": bool(ligne_finale["est_admin"]),
    }


def main() -> int:
    parseur = argparse.ArgumentParser(
        description="Compte admin de test pour la page Solo et la modération."
    )
    parseur.add_argument(
        "--mot-de-passe",
        help="Mot de passe en clair (min. 8 caractères). Sinon ADMIN_TEST_MDP ou génération aléatoire.",
    )
    args = parseur.parse_args()

    mot_de_passe = _mot_de_passe_fourni(args)
    if len(mot_de_passe) < communaute.LONGUEUR_MOT_DE_PASSE_MIN:
        print(
            f"Erreur : mot de passe trop court (min. {communaute.LONGUEUR_MOT_DE_PASSE_MIN} caractères).",
            file=sys.stderr,
        )
        return 1

    resultat = creer_ou_mettre_a_jour_admin(mot_de_passe)
    print(f"Compte admin {resultat['action']} avec succès.")
    print(f"  ID        : {resultat['id']}")
    print(f"  E-mail    : {resultat['email']}")
    print(f"  Pseudo    : {resultat['pseudo']}")
    print(f"  est_admin : {resultat['est_admin']}")
    print()
    print(
        "Conseil : ajoutez dans votre .env local (non versionné) :\n"
        f"  EMAIL_ADMIN_COMMUNAUTE={EMAIL_ADMIN}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
