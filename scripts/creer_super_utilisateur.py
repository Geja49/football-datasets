"""
Crée ou promeut un compte « super utilisateur » (accès Solo, sans droits admin).

Usage :
  python scripts/creer_super_utilisateur.py
  python scripts/creer_super_utilisateur.py --email "ami@exemple.fr" --pseudo "AmiSolo"
  python scripts/creer_super_utilisateur.py --mot-de-passe "VotreMotDePasse!"
  SUPER_UTILISATEUR_MDP="VotreMotDePasse!" python scripts/creer_super_utilisateur.py

Le mot de passe n'est jamais stocké en clair dans le dépôt : passez-le en
argument ou via SUPER_UTILISATEUR_MDP. Sans mot de passe fourni, un mot de
passe aléatoire est généré et affiché une seule fois.

Pour promouvoir un compte déjà inscrit sans changer le mot de passe :
  python scripts/creer_super_utilisateur.py --email "existant@exemple.fr" --promouvoir
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

EMAIL_DEFAUT = "super@statsfoot.local"
PSEUDO_DEFAUT = "superutilisateur"


def _mot_de_passe_fourni(args: argparse.Namespace) -> str | None:
    if args.promouvoir:
        return None
    if args.mot_de_passe:
        return args.mot_de_passe
    depuis_env = (os.environ.get("SUPER_UTILISATEUR_MDP") or "").strip()
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


def creer_ou_promouvoir(
    email: str,
    pseudo: str,
    mot_de_passe: str | None,
    *,
    promouvoir_seulement: bool,
) -> dict:
    communaute.initialiser_base()
    email = email.strip().lower()
    pseudo = pseudo.strip()
    maintenant = communaute.maintenant_iso()

    connexion = communaute.ouvrir_base()
    try:
        ligne = connexion.execute(
            "SELECT id, pseudo, est_admin, super_utilisateur FROM utilisateurs "
            "WHERE email = ? COLLATE NOCASE",
            (email,),
        ).fetchone()

        if ligne:
            if promouvoir_seulement:
                connexion.execute(
                    """
                    UPDATE utilisateurs
                    SET super_utilisateur = 1,
                        age_confirme = 1,
                        cgu_acceptees = 1
                    WHERE id = ?
                    """,
                    (ligne["id"],),
                )
                action = "promu"
                utilisateur_id = ligne["id"]
            else:
                if not mot_de_passe:
                    raise ValueError("Mot de passe requis hors mode --promouvoir")
                hash_mdp = communaute.contexte_mots_de_passe.hash(mot_de_passe)
                connexion.execute(
                    """
                    UPDATE utilisateurs
                    SET pseudo = ?, mot_de_passe_hash = ?, super_utilisateur = 1,
                        age_confirme = 1, cgu_acceptees = 1
                    WHERE id = ?
                    """,
                    (pseudo, hash_mdp, ligne["id"]),
                )
                action = "mis à jour"
                utilisateur_id = ligne["id"]
        else:
            if promouvoir_seulement:
                raise ValueError(
                    f"Aucun compte avec l'e-mail {email} — créez-le sans --promouvoir "
                    "ou inscrivez-vous d'abord sur le site."
                )
            if not mot_de_passe:
                raise ValueError("Mot de passe requis pour créer un compte")
            if len(mot_de_passe) < communaute.LONGUEUR_MOT_DE_PASSE_MIN:
                raise ValueError(
                    f"Mot de passe trop court "
                    f"(min. {communaute.LONGUEUR_MOT_DE_PASSE_MIN} caractères)."
                )
            hash_mdp = communaute.contexte_mots_de_passe.hash(mot_de_passe)
            conflit_pseudo = connexion.execute(
                "SELECT id FROM utilisateurs WHERE pseudo = ? COLLATE NOCASE AND email != ?",
                (pseudo, email),
            ).fetchone()
            pseudo_final = pseudo if not conflit_pseudo else f"{pseudo}_su"

            curseur = connexion.execute(
                """
                INSERT INTO utilisateurs (
                    email, pseudo, mot_de_passe_hash,
                    est_admin, super_utilisateur, age_confirme, cgu_acceptees, cree_le
                ) VALUES (?, ?, ?, 0, 1, 1, 1, ?)
                """,
                (email, pseudo_final, hash_mdp, maintenant),
            )
            action = "créé"
            utilisateur_id = curseur.lastrowid

        connexion.commit()

        ligne_finale = connexion.execute(
            """
            SELECT id, email, pseudo, est_admin, super_utilisateur
            FROM utilisateurs WHERE id = ?
            """,
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
        "super_utilisateur": bool(ligne_finale["super_utilisateur"]),
    }


def main() -> int:
    parseur = argparse.ArgumentParser(
        description=(
            "Compte super utilisateur (accès Solo) — n'accorde pas les droits admin."
        )
    )
    parseur.add_argument(
        "--email",
        default=EMAIL_DEFAUT,
        help=f"E-mail du compte (défaut : {EMAIL_DEFAUT})",
    )
    parseur.add_argument(
        "--pseudo",
        default=PSEUDO_DEFAUT,
        help=f"Pseudo (défaut : {PSEUDO_DEFAUT})",
    )
    parseur.add_argument(
        "--mot-de-passe",
        help=(
            "Mot de passe en clair (min. 8 caractères). "
            "Sinon SUPER_UTILISATEUR_MDP ou génération aléatoire."
        ),
    )
    parseur.add_argument(
        "--promouvoir",
        action="store_true",
        help="Promeut un compte existant sans modifier le mot de passe.",
    )
    args = parseur.parse_args()

    try:
        mot_de_passe = _mot_de_passe_fourni(args)
        if (
            mot_de_passe is not None
            and len(mot_de_passe) < communaute.LONGUEUR_MOT_DE_PASSE_MIN
        ):
            print(
                f"Erreur : mot de passe trop court "
                f"(min. {communaute.LONGUEUR_MOT_DE_PASSE_MIN} caractères).",
                file=sys.stderr,
            )
            return 1

        resultat = creer_ou_promouvoir(
            args.email,
            args.pseudo,
            mot_de_passe,
            promouvoir_seulement=args.promouvoir,
        )
    except ValueError as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1

    print(f"Compte super utilisateur {resultat['action']} avec succès.")
    print(f"  ID                 : {resultat['id']}")
    print(f"  E-mail             : {resultat['email']}")
    print(f"  Pseudo             : {resultat['pseudo']}")
    print(f"  est_admin          : {resultat['est_admin']}")
    print(f"  super_utilisateur  : {resultat['super_utilisateur']}")
    print()
    print(
        "Ce compte peut ouvrir /solo. La page Modération reste réservée aux admins."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
